"""Seeded datasets and the feature scaler, implemented with numpy only.

`scikit-learn` is deliberately absent from ``requirements.txt`` and is not
being added (DECISIONS.md D-014), so the generators, the stratified split and
the scaler are hand-written here. Hand-rolling removes the safety net of a
well-tested reference, which is why every claim this module makes — shape,
class balance, separability, reproducibility, and above all that the scaler
sees only the training split — is asserted in ``tests/test_qml_datasets.py``.

Two design rules:

* **Fail loudly.** A request that cannot be honoured exactly raises
  :class:`QmlDatasetError`. Silently returning fewer samples than asked for
  would cap achievable accuracy invisibly.
* **One generator.** Every random draw comes from the single ``rng`` passed
  in, so the whole pipeline is reproducible from one seed.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.quantum.qml_lab.errors import QmlDatasetError
from app.quantum.qml_lab.models import DatasetConfig

#: Bundled copy of Fisher's Iris measurements (1936), a public-domain dataset.
#: Vendored from the scikit-learn wheel's ``sklearn/datasets/data/iris.csv``
#: (sha256 f13ffa8f…d1449, 150 rows) so the dataset is authentic without
#: taking scikit-learn as a dependency. Provenance is recorded in
#: docs/qml/DECISIONS.md D-015.
_IRIS_CSV = Path(__file__).parent / "data" / "iris.csv"

#: Angle encoding is 2π-periodic, so features are mapped into [0, π]. Using the
#: full [0, 2π] would make the extremes of the range wrap onto each other.
ANGLE_MIN = 0.0
ANGLE_MAX = float(np.pi)


@dataclass(frozen=True)
class MinMaxScaler:
    """Maps each feature onto ``[ANGLE_MIN, ANGLE_MAX]``.

    Fitted on the training split **only**. ``transform`` clips, because test
    points legitimately fall outside the training range and an unclipped angle
    beyond π would wrap around the Bloch sphere and alias onto a different
    state.
    """

    data_min: np.ndarray
    data_max: np.ndarray

    @classmethod
    def fit(cls, x: np.ndarray) -> "MinMaxScaler":
        if x.ndim != 2 or x.shape[0] == 0:
            raise QmlDatasetError(f"scaler needs a non-empty 2-D array, got shape {x.shape}")
        return cls(data_min=np.asarray(x.min(axis=0), dtype=float), data_max=np.asarray(x.max(axis=0), dtype=float))

    def transform(self, x: np.ndarray) -> np.ndarray:
        span = self.data_max - self.data_min
        # A constant feature has zero span; map it to the middle of the range
        # rather than dividing by zero.
        safe = np.where(span == 0.0, 1.0, span)
        unit = (np.asarray(x, dtype=float) - self.data_min) / safe
        unit = np.where(span == 0.0, 0.5, unit)
        return np.clip(unit, 0.0, 1.0) * (ANGLE_MAX - ANGLE_MIN) + ANGLE_MIN

    def to_dict(self) -> dict[str, list[float]]:
        return {"data_min": self.data_min.tolist(), "data_max": self.data_max.tolist()}


@dataclass(frozen=True)
class Dataset:
    """A fitted, split, scaled dataset ready for the encoder."""

    name: str
    x_train: np.ndarray
    y_train: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray
    scaler: MinMaxScaler
    feature_names: tuple[str, ...]

    @property
    def n_features(self) -> int:
        return int(self.x_train.shape[1])

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "n_train": int(self.x_train.shape[0]),
            "n_test": int(self.x_test.shape[0]),
            "n_features": self.n_features,
            "train_class_balance": _balance(self.y_train),
            "test_class_balance": _balance(self.y_test),
            "feature_names": list(self.feature_names),
        }


def _balance(y: np.ndarray) -> dict[str, int]:
    return {"0": int(np.sum(y == 0)), "1": int(np.sum(y == 1))}


# --------------------------------------------------------------------------
# Generators
# --------------------------------------------------------------------------


def make_moons(n_samples: int, noise: float, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """Two interleaving half-circles — the standard non-linearly-separable toy.

    Class 0 is the upper arc, class 1 the lower arc shifted right and down.
    Closed-form, so no reference implementation is needed.
    """
    n_out = n_samples // 2
    n_in = n_samples - n_out

    theta_out = np.linspace(0.0, np.pi, n_out)
    theta_in = np.linspace(0.0, np.pi, n_in)

    outer = np.stack([np.cos(theta_out), np.sin(theta_out)], axis=1)
    inner = np.stack([1.0 - np.cos(theta_in), 0.5 - np.sin(theta_in)], axis=1)

    x = np.vstack([outer, inner])
    y = np.hstack([np.zeros(n_out, dtype=int), np.ones(n_in, dtype=int)])

    if noise > 0.0:
        x = x + rng.normal(loc=0.0, scale=noise, size=x.shape)
    return x, y


def make_circles(
    n_samples: int, noise: float, rng: np.random.Generator, factor: float = 0.5
) -> tuple[np.ndarray, np.ndarray]:
    """A small circle inside a large one — separable only by radius."""
    if not 0.0 < factor < 1.0:
        raise QmlDatasetError(f"circles factor must be in (0, 1), got {factor}")

    n_out = n_samples // 2
    n_in = n_samples - n_out

    theta_out = np.linspace(0.0, 2.0 * np.pi, n_out, endpoint=False)
    theta_in = np.linspace(0.0, 2.0 * np.pi, n_in, endpoint=False)

    outer = np.stack([np.cos(theta_out), np.sin(theta_out)], axis=1)
    inner = factor * np.stack([np.cos(theta_in), np.sin(theta_in)], axis=1)

    x = np.vstack([outer, inner])
    y = np.hstack([np.zeros(n_out, dtype=int), np.ones(n_in, dtype=int)])

    if noise > 0.0:
        x = x + rng.normal(loc=0.0, scale=noise, size=x.shape)
    return x, y


def load_iris_binary(n_samples: int, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, tuple[str, ...]]:
    """Setosa (0) vs versicolor (1) from the bundled Iris file.

    Only 100 of the 150 rows belong to these two classes. Asking for more
    raises rather than quietly returning 100 — see the module docstring.
    """
    rows = _read_iris()
    mask = rows[:, 4] < 2  # drop virginica
    x_all = rows[mask][:, :4]
    y_all = rows[mask][:, 4].astype(int)

    available = int(x_all.shape[0])
    if n_samples > available:
        raise QmlDatasetError(
            f"iris_binary has only {available} samples across its two classes, "
            f"but {n_samples} were requested; lower dataset.n_samples to {available} or less"
        )

    if n_samples < available:
        # Subsample without disturbing the class balance.
        idx = _stratified_subsample(y_all, n_samples, rng)
        x_all, y_all = x_all[idx], y_all[idx]

    names = ("sepal length (cm)", "sepal width (cm)", "petal length (cm)", "petal width (cm)")
    return x_all, y_all, names


def _read_iris() -> np.ndarray:
    if not _IRIS_CSV.is_file():  # pragma: no cover - packaging guard
        raise QmlDatasetError(f"bundled iris data is missing at {_IRIS_CSV}")
    with _IRIS_CSV.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        expected_rows = int(header[0])
        values = [[float(cell) for cell in row] for row in reader if row]
    data = np.asarray(values, dtype=float)
    if data.shape != (expected_rows, 5):
        raise QmlDatasetError(f"bundled iris data is malformed: expected ({expected_rows}, 5), got {data.shape}")
    return data


def _stratified_subsample(y: np.ndarray, n_samples: int, rng: np.random.Generator) -> np.ndarray:
    """Pick ``n_samples`` indices keeping each class's share as even as possible."""
    classes = np.unique(y)
    per_class = n_samples // len(classes)
    remainder = n_samples - per_class * len(classes)

    chosen: list[np.ndarray] = []
    for position, cls in enumerate(classes):
        members = np.flatnonzero(y == cls)
        take = per_class + (1 if position < remainder else 0)
        if take > members.size:
            raise QmlDatasetError(f"class {cls} has {members.size} samples, cannot take {take}")
        chosen.append(rng.choice(members, size=take, replace=False))
    return np.sort(np.concatenate(chosen))


# --------------------------------------------------------------------------
# Split + assembly
# --------------------------------------------------------------------------


def stratified_split(
    x: np.ndarray, y: np.ndarray, test_fraction: float, rng: np.random.Generator
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Split preserving each class's proportion, with at least one test sample per class.

    Stratification matters here: with an unstratified split a small dataset can
    put every member of one class in train, and the reported test accuracy
    then measures nothing.
    """
    train_idx: list[np.ndarray] = []
    test_idx: list[np.ndarray] = []

    for cls in np.unique(y):
        members = np.flatnonzero(y == cls)
        shuffled = rng.permutation(members)
        n_test = int(round(len(shuffled) * test_fraction))
        n_test = max(1, min(n_test, len(shuffled) - 1))
        test_idx.append(shuffled[:n_test])
        train_idx.append(shuffled[n_test:])

    tr = np.sort(np.concatenate(train_idx))
    te = np.sort(np.concatenate(test_idx))
    return x[tr], y[tr], x[te], y[te]


def build_dataset(config: DatasetConfig, rng: np.random.Generator) -> Dataset:
    """Generate, split and scale a dataset from ``config``.

    Order matters and is fixed: generate → split → **fit the scaler on the
    training split alone** → transform both splits. Fitting before the split,
    or on the concatenation, leaks the test distribution into training and
    inflates every number downstream.
    """
    feature_names: tuple[str, ...]

    if config.name == "moons":
        x, y = make_moons(config.n_samples, config.noise, rng)
        feature_names = ("x1", "x2")
    elif config.name == "circles":
        x, y = make_circles(config.n_samples, config.noise, rng)
        feature_names = ("x1", "x2")
    elif config.name == "iris_binary":
        x, y, feature_names = load_iris_binary(config.n_samples, rng)
    else:  # pragma: no cover - Literal in the schema makes this unreachable
        raise QmlDatasetError(f"unknown dataset {config.name!r}")

    x_train_raw, y_train, x_test_raw, y_test = stratified_split(x, y, config.test_fraction, rng)

    scaler = MinMaxScaler.fit(x_train_raw)
    return Dataset(
        name=config.name,
        x_train=scaler.transform(x_train_raw),
        y_train=y_train,
        x_test=scaler.transform(x_test_raw),
        y_test=y_test,
        scaler=scaler,
        feature_names=feature_names,
    )


#: Per-dataset ceilings the UI needs in order to bound its inputs. ``None``
#: means the generator is parametric and the global MAX_SAMPLES applies.
DATASET_MAX_SAMPLES: dict[str, int | None] = {
    "moons": None,
    "circles": None,
    "iris_binary": 100,
}
