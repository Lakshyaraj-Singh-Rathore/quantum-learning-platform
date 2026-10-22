"""Continuous-target datasets and the regression training loop.

Kept separate from :mod:`.datasets` and :mod:`.trainer` rather than bolted on
with flags. The classification split is *stratified* — it balances classes
across train and test — and that operation is meaningless for a continuous
target. Reusing it by passing a discretised label would be a quiet way to get
a split that looks fine and is subtly wrong.

Everything leakage-sensitive follows the same order the classifier uses:
generate → split → **fit both scalers on the training split alone** →
transform. The feature scaler maps into ``[0, π]`` for the angle encoder and
the target scaler maps into ``[-1, 1]`` for ``<Z₀>`` (§2C.4).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from pennylane import numpy as pnp

from app.quantum.qml_lab import limits
from app.quantum.qml_lab.datasets import ANGLE_MAX, ANGLE_MIN, MinMaxScaler
from app.quantum.qml_lab.errors import QmlCancelledError, QmlDatasetError
from app.quantum.qml_lab.models import (
    ProgressEvent,
    RegressionEpochRecord,
    TrainingConfig,
)
from app.quantum.qml_lab.regression import (
    QuantumRegressor,
    RegressionParameters,
    TargetScaler,
    mse_loss,
    r2_score,
)

ProgressCallback = Callable[[ProgressEvent], None]
CancelCallback = Callable[[], bool]

#: Datasets with a continuous target. **Re-exported, not redefined** -- the
#: single registry is ``limits.REGRESSION_DATASETS``. Phase 5 defined this
#: tuple here while ``models.DatasetName`` was hand-written elsewhere, and the
#: two drifted immediately: describe() advertised these names and the schema
#: rejected them.
REGRESSION_DATASETS: tuple[str, ...] = limits.REGRESSION_DATASETS


@dataclass(frozen=True)
class RegressionDataset:
    """A fitted, split, scaled regression dataset.

    ``y_train``/``y_test`` are in the **user's units**; ``y_train_scaled``
    and ``y_test_scaled`` are the ``[-1, 1]`` versions the circuit trains
    against. Both are carried so every reported metric can be computed in
    real units without re-deriving them, and so a test can assert the two
    are consistent.
    """

    name: str
    x_train: np.ndarray
    y_train: np.ndarray
    x_test: np.ndarray
    y_test: np.ndarray
    y_train_scaled: np.ndarray
    y_test_scaled: np.ndarray
    scaler: MinMaxScaler
    target_scaler: TargetScaler
    feature_names: tuple[str, ...]
    #: Features in their original units, before angle scaling. Carried so a
    #: prediction-vs-input plot can use real x values, and so the leakage
    #: test can assert the scaler's bounds came from the training split
    #: *exactly* rather than inferring it from clipping behaviour.
    x_train_raw: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))
    x_test_raw: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))

    @property
    def n_features(self) -> int:
        return int(self.x_train.shape[1])

    def summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "n_train": int(self.x_train.shape[0]),
            "n_test": int(self.x_test.shape[0]),
            "n_features": self.n_features,
            "target_range_train": [
                float(np.min(self.y_train)),
                float(np.max(self.y_train)),
            ],
            "target_range_test": [float(np.min(self.y_test)), float(np.max(self.y_test))],
            "target_scaler": self.target_scaler.to_dict(),
            "feature_names": list(self.feature_names),
        }


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


#: Angle-frequency each dataset demands of the circuit, and the reason it is
#: not the same number as the frequency in the formula.
#:
#: The feature scaler maps the raw domain ``[-π, π]`` onto the encoder's
#: ``[0, π]``, i.e. ``x = 2a - π``. That substitution **doubles** every
#: frequency: ``sin(x) → -sin(2a)``, ``cos(2x) → cos(4a)``. A re-uploading
#: circuit reaches angle-frequencies up to ``n_layers``, and ``MAX_LAYERS``
#: is 4 — so a target written as ``cos(3x)`` would need frequency 6 and is
#: *unreachable at every configuration the schema permits*. It would train
#: to a flat line and read as a broken model rather than an impossible ask.
#:
#: These numbers are therefore a budget, not trivia, and
#: ``test_every_regression_dataset_is_inside_the_frequency_budget`` fails the
#: build if a dataset is ever added that breaks it.
REQUIRED_ANGLE_FREQUENCY: dict[str, int] = {
    "sine": 2,
    "damped_cosine": 4,
    "linear_mix": 1,
}


def make_sine(n_samples: int, noise: float, rng: np.random.Generator):
    """``y = sin(x)``. Angle-frequency 2, so ``n_layers >= 2`` can fit it."""
    x = rng.uniform(-np.pi, np.pi, size=(n_samples, 1))
    y = np.sin(x[:, 0]) + rng.normal(scale=noise, size=n_samples)
    return x, y, ("x",)


def make_damped_cosine(n_samples: int, noise: float, rng: np.random.Generator):
    """``y = exp(-|x|/2)·cos(2x)``. Angle-frequency 4 — the hardest target that
    fits inside ``MAX_LAYERS``, and a genuine test of the re-uploading depth."""
    x = rng.uniform(-np.pi, np.pi, size=(n_samples, 1))
    y = np.exp(-np.abs(x[:, 0]) / 2.0) * np.cos(2.0 * x[:, 0])
    y = y + rng.normal(scale=noise, size=n_samples)
    return x, y, ("x",)


def make_linear_mix(n_samples: int, noise: float, rng: np.random.Generator):
    """``y = 1.5·x₁ − 0.8·x₂``. Two features, and linear on purpose.

    A regression task a ridge baseline should solve almost exactly. It is the
    control: if the quantum regressor cannot match the classical model here,
    the problem is the model, not the data.
    """
    x = rng.uniform(-1.0, 1.0, size=(n_samples, 2))
    y = 1.5 * x[:, 0] - 0.8 * x[:, 1] + rng.normal(scale=noise, size=n_samples)
    return x, y, ("x1", "x2")


def build_regression_dataset(
    name: str,
    n_samples: int,
    noise: float,
    test_fraction: float,
    rng: np.random.Generator,
) -> RegressionDataset:
    """Generate, split and scale a continuous-target dataset.

    The split is a plain shuffled split, not a stratified one: there are no
    classes to balance. Both scalers are fitted on the training split only.
    """
    if name == "sine":
        x, y, feature_names = make_sine(n_samples, noise, rng)
    elif name == "damped_cosine":
        x, y, feature_names = make_damped_cosine(n_samples, noise, rng)
    elif name == "linear_mix":
        x, y, feature_names = make_linear_mix(n_samples, noise, rng)
    else:
        raise QmlDatasetError(
            f"unknown regression dataset {name!r}; expected one of "
            f"{', '.join(REGRESSION_DATASETS)}"
        )

    n = int(x.shape[0])
    n_test = int(round(n * test_fraction))
    if n_test < 1 or n_test >= n:
        raise QmlDatasetError(
            f"test_fraction={test_fraction} leaves {n_test} test rows out of {n}; "
            f"choose a fraction that yields at least one row in each split"
        )

    order = rng.permutation(n)
    test_idx, train_idx = order[:n_test], order[n_test:]

    x_train_raw, x_test_raw = x[train_idx], x[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    scaler = MinMaxScaler.fit(x_train_raw)
    target_scaler = TargetScaler().fit(y_train)

    return RegressionDataset(
        name=name,
        x_train=scaler.transform(x_train_raw),
        y_train=y_train,
        x_test=scaler.transform(x_test_raw),
        y_test=y_test,
        x_train_raw=x_train_raw,
        x_test_raw=x_test_raw,
        y_train_scaled=target_scaler.transform(y_train),
        y_test_scaled=target_scaler.transform(y_test),
        scaler=scaler,
        target_scaler=target_scaler,
        feature_names=feature_names,
    )


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


@dataclass
class RegressionOutcome:
    """Everything a caller needs after a regression run."""

    status: str  # "completed" | "cancelled" | "timed_out"
    params: RegressionParameters
    history: list[RegressionEpochRecord] = field(default_factory=list)
    epochs_completed: int = 0
    duration_seconds: float = 0.0
    cancelled_at_epoch: int | None = None
    cancelled_at_batch: int | None = None

    @property
    def interrupted(self) -> bool:
        return self.status in {"cancelled", "timed_out"}


def _evaluate_split(model: QuantumRegressor, theta: np.ndarray, x: np.ndarray, y_scaled: np.ndarray):
    """MSE and R², both in scaled units, for one split."""
    predictions = np.asarray(model.decision_values(x, theta), dtype=float)
    loss = float(np.mean((predictions - np.asarray(y_scaled, dtype=float)) ** 2))
    return loss, r2_score(y_scaled, predictions)


def train_regression(
    model: QuantumRegressor,
    dataset: RegressionDataset,
    config: TrainingConfig,
    rng: np.random.Generator,
    initial: RegressionParameters,
    *,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
    deadline_seconds: float | None = None,
) -> RegressionOutcome:
    """Adam on MSE, with the same cancel and deadline discipline as the classifier.

    Cancellation is checked **before** each batch and the deadline is tested
    first when both fire, exactly as :func:`app.quantum.qml_lab.trainer.train`
    does — a second, subtly different interruption policy in the same product
    would be its own kind of defect.
    """
    import pennylane as qml

    started = time.perf_counter()
    theta = pnp.array(np.array(initial.theta, dtype=float), requires_grad=True)

    x_train = dataset.x_train
    y_train = np.asarray(dataset.y_train_scaled, dtype=float)
    n_train = int(x_train.shape[0])
    batch_size = min(config.batch_size, n_train)
    total_batches = max(1, int(np.ceil(n_train / batch_size)))

    moment_1 = np.zeros_like(np.asarray(theta, dtype=float))
    moment_2 = np.zeros_like(moment_1)
    step = 0

    history: list[RegressionEpochRecord] = []
    epochs_completed = 0
    cancelled_at_epoch: int | None = None
    cancelled_at_batch: int | None = None
    stop_reason: dict[str, str | None] = {"value": None}

    def _cancelled() -> bool:
        if deadline_seconds is not None and (time.perf_counter() - started) >= deadline_seconds:
            stop_reason["value"] = "timed_out"
            return True
        if should_cancel is not None and bool(should_cancel()):
            stop_reason["value"] = "cancelled"
            return True
        return False

    def _emit(event: ProgressEvent) -> None:
        if on_progress is not None:
            on_progress(event)

    def cost(parameters, batch_x, batch_y):
        return mse_loss(model.decision_values(batch_x, parameters), batch_y)

    gradient_of = qml.grad(cost, argnums=0)

    try:
        for epoch in range(1, config.epochs + 1):
            order = rng.permutation(n_train)

            for batch_index in range(total_batches):
                if _cancelled():
                    cancelled_at_epoch, cancelled_at_batch = epoch, batch_index
                    raise QmlCancelledError

                slice_ = order[batch_index * batch_size : (batch_index + 1) * batch_size]
                if slice_.size == 0:
                    continue

                gradient = np.asarray(
                    gradient_of(theta, x_train[slice_], y_train[slice_]), dtype=float
                )

                step += 1
                moment_1 = 0.9 * moment_1 + 0.1 * gradient
                moment_2 = 0.999 * moment_2 + 0.001 * np.square(gradient)
                corrected_1 = moment_1 / (1.0 - 0.9**step)
                corrected_2 = moment_2 / (1.0 - 0.999**step)
                updated = np.asarray(theta, dtype=float) - config.learning_rate * corrected_1 / (
                    np.sqrt(corrected_2) + 1e-8
                )
                theta = pnp.array(updated, requires_grad=True)

                _emit(
                    ProgressEvent(
                        epoch=epoch,
                        total_epochs=config.epochs,
                        batch=batch_index + 1,
                        total_batches=total_batches,
                        message="batch",
                    )
                )

            flat = np.asarray(theta, dtype=float)
            train_loss, train_r2 = _evaluate_split(model, flat, dataset.x_train, dataset.y_train_scaled)
            test_loss, test_r2 = _evaluate_split(model, flat, dataset.x_test, dataset.y_test_scaled)

            history.append(
                RegressionEpochRecord(
                    epoch=epoch,
                    train_loss=train_loss,
                    train_r2=train_r2,
                    test_loss=test_loss,
                    test_r2=test_r2,
                    elapsed_seconds=time.perf_counter() - started,
                )
            )
            epochs_completed = epoch

            _emit(
                ProgressEvent(
                    epoch=epoch,
                    total_epochs=config.epochs,
                    batch=total_batches,
                    total_batches=total_batches,
                    train_loss=train_loss,
                    message="epoch",
                )
            )

        status = "completed"
    except QmlCancelledError:
        status = stop_reason["value"] or "cancelled"

    final = RegressionParameters(
        theta=np.asarray(theta, dtype=float),
        n_qubits=initial.n_qubits,
        n_layers=initial.n_layers,
    )

    return RegressionOutcome(
        status=status,
        params=final,
        history=history,
        epochs_completed=epochs_completed,
        duration_seconds=time.perf_counter() - started,
        cancelled_at_epoch=cancelled_at_epoch,
        cancelled_at_batch=cancelled_at_batch,
    )


# ---------------------------------------------------------------------------
# Classical baseline (the "baseline polish" half of Phase 5)
# ---------------------------------------------------------------------------


@dataclass
class RidgeBaseline:
    """L2-regularised linear regression, solved in closed form.

    The classification baseline is a real trained logistic regression; the
    regression side needs the same honesty. Ridge has an exact solution,
    ``(XᵀX + λI)⁻¹Xᵀy``, so there is no optimiser to tune and no excuse for a
    weak comparison — on ``linear_mix`` it should be near-perfect, which makes
    it a genuine bar rather than a strawman.

    No sklearn (§1A): this is ``numpy.linalg.solve`` on a matrix built here.
    """

    l2: float = 1e-3
    coefficients: np.ndarray | None = None
    intercept: float = 0.0

    def fit(self, x: np.ndarray, y: np.ndarray) -> "RidgeBaseline":
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n_features = x.shape[1]

        design = np.hstack([x, np.ones((x.shape[0], 1))])
        penalty = self.l2 * np.eye(n_features + 1)
        # The intercept is not penalised: shrinking it biases predictions
        # toward zero rather than toward the target's mean.
        penalty[-1, -1] = 0.0

        solution = np.linalg.solve(design.T @ design + penalty, design.T @ y)
        self.coefficients = solution[:-1]
        self.intercept = float(solution[-1])
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        if self.coefficients is None:
            raise QmlDatasetError("RidgeBaseline.predict called before fit")
        return np.asarray(x, dtype=float) @ self.coefficients + self.intercept
