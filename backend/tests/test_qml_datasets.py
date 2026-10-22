"""Datasets, the stratified split and the scaler.

These are hand-written with numpy because scikit-learn is deliberately not a
dependency, so nothing here can lean on a trusted reference implementation.
Every property the rest of the engine assumes is therefore asserted: shape,
class balance, separability, bit-for-bit reproducibility, and above all that
the scaler never sees the test split.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest

from app.quantum.qml_lab import datasets
from app.quantum.qml_lab.datasets import ANGLE_MAX, ANGLE_MIN, MinMaxScaler, build_dataset
from app.quantum.qml_lab.errors import QmlDatasetError
from app.quantum.qml_lab.models import DatasetConfig


def _rng(seed: int = 11) -> np.random.Generator:
    return np.random.default_rng(seed)


# --------------------------------------------------------------------------
# Generators
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["moons", "circles", "iris_binary"])
def test_shape_and_balance(name):
    n = 100 if name == "iris_binary" else 120
    dataset = build_dataset(DatasetConfig(name=name, n_samples=n, test_fraction=0.3), _rng())

    assert dataset.x_train.shape[0] + dataset.x_test.shape[0] == n
    assert dataset.x_train.shape[1] == dataset.n_features
    assert dataset.y_train.shape[0] == dataset.x_train.shape[0]

    for split in (dataset.y_train, dataset.y_test):
        assert set(np.unique(split)).issubset({0, 1})
        # Stratification means neither split may collapse to one class.
        assert 0 < int(np.sum(split == 1)) < split.size


def test_moons_and_circles_have_two_features_iris_has_four():
    assert build_dataset(DatasetConfig(name="moons", n_samples=40), _rng()).n_features == 2
    assert build_dataset(DatasetConfig(name="circles", n_samples=40), _rng()).n_features == 2
    assert build_dataset(DatasetConfig(name="iris_binary", n_samples=40), _rng()).n_features == 4


def test_circles_are_separable_by_radius():
    """The claim 'circles is separable' is checked, not assumed.

    A malformed generator silently caps achievable accuracy and makes the
    model look bad for a reason that has nothing to do with the model.
    """
    x, y = datasets.make_circles(200, noise=0.0, rng=_rng())
    radius = np.linalg.norm(x, axis=1)
    assert radius[y == 1].max() < radius[y == 0].min()


def test_moons_are_not_linearly_separable_but_are_separable():
    """Moons must be hard for a line and easy for a curve.

    If a single feature threshold could split it, the dataset would not be
    testing anything the classical baseline cannot already do.
    """
    x, y = datasets.make_moons(200, noise=0.0, rng=_rng())

    for feature in range(x.shape[1]):
        column = x[:, feature]
        best = max(
            float(np.mean((column > threshold).astype(int) == y)) for threshold in np.linspace(column.min(), column.max(), 60)
        )
        best = max(best, 1.0 - best)
        assert best < 0.95, f"feature {feature} alone separates moons at {best:.2f}"

    # ...but the two classes do occupy different regions.
    assert np.linalg.norm(x[y == 0].mean(axis=0) - x[y == 1].mean(axis=0)) > 0.5


def test_noise_widens_the_spread():
    clean, _ = datasets.make_moons(200, noise=0.0, rng=_rng())
    noisy, _ = datasets.make_moons(200, noise=0.3, rng=_rng())
    assert noisy.std(axis=0).mean() > clean.std(axis=0).mean()


# --------------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["moons", "circles", "iris_binary"])
def test_same_seed_reproduces_bit_for_bit(name):
    config = DatasetConfig(name=name, n_samples=100 if name == "iris_binary" else 120)
    first = build_dataset(config, np.random.default_rng(99))
    second = build_dataset(config, np.random.default_rng(99))

    for attribute in ("x_train", "y_train", "x_test", "y_test"):
        left, right = getattr(first, attribute), getattr(second, attribute)
        assert hashlib.sha256(np.ascontiguousarray(left)).hexdigest() == hashlib.sha256(
            np.ascontiguousarray(right)
        ).hexdigest()


def test_different_seeds_produce_different_draws():
    config = DatasetConfig(name="moons", n_samples=120, noise=0.2)
    first = build_dataset(config, np.random.default_rng(1))
    second = build_dataset(config, np.random.default_rng(2))
    assert not np.array_equal(first.x_train, second.x_train)


# --------------------------------------------------------------------------
# The scaler — leakage is the failure mode that matters
# --------------------------------------------------------------------------


def test_scaler_statistics_come_from_the_train_split_only():
    """The single easiest thing to get subtly wrong, asserted directly.

    The fitted range must equal the *training* split's range and differ from
    the full dataset's, otherwise test-set information has leaked into
    training and every downstream number is inflated.
    """
    config = DatasetConfig(name="moons", n_samples=200, noise=0.25, test_fraction=0.3)
    rng = np.random.default_rng(5)

    # Rebuild the raw pipeline with the same seed to recover the pre-scaling
    # arrays, so the comparison is against the real splits rather than a proxy.
    replay = np.random.default_rng(5)
    x_raw, y_raw = datasets.make_moons(config.n_samples, config.noise, replay)
    x_train_raw, _, x_test_raw, _ = datasets.stratified_split(x_raw, y_raw, config.test_fraction, replay)

    dataset = build_dataset(config, rng)

    assert np.allclose(dataset.scaler.data_min, x_train_raw.min(axis=0))
    assert np.allclose(dataset.scaler.data_max, x_train_raw.max(axis=0))

    full_min = np.minimum(x_train_raw.min(axis=0), x_test_raw.min(axis=0))
    full_max = np.maximum(x_train_raw.max(axis=0), x_test_raw.max(axis=0))
    assert not (np.allclose(dataset.scaler.data_min, full_min) and np.allclose(dataset.scaler.data_max, full_max)), (
        "scaler statistics match the FULL dataset — the test split leaked into the fit"
    )


def test_train_split_spans_the_angle_range_exactly():
    dataset = build_dataset(DatasetConfig(name="moons", n_samples=200), _rng())
    assert np.allclose(dataset.x_train.min(axis=0), ANGLE_MIN)
    assert np.allclose(dataset.x_train.max(axis=0), ANGLE_MAX)


def test_test_split_is_clipped_into_the_angle_range():
    """Test points outside the training range must clip, not wrap.

    An angle beyond π would alias onto a different state on the Bloch sphere,
    so an unclipped outlier silently becomes a different input.
    """
    dataset = build_dataset(DatasetConfig(name="moons", n_samples=200, noise=0.4), _rng())
    assert dataset.x_test.min() >= ANGLE_MIN
    assert dataset.x_test.max() <= ANGLE_MAX


def test_scaler_handles_a_constant_feature_without_dividing_by_zero():
    scaler = MinMaxScaler.fit(np.array([[1.0, 5.0], [1.0, 7.0]]))
    out = scaler.transform(np.array([[1.0, 6.0]]))
    assert np.isfinite(out).all()
    assert out[0][0] == pytest.approx((ANGLE_MAX - ANGLE_MIN) * 0.5)


def test_scaler_rejects_an_empty_fit():
    with pytest.raises(QmlDatasetError):
        MinMaxScaler.fit(np.empty((0, 2)))


# --------------------------------------------------------------------------
# Loud failures
# --------------------------------------------------------------------------


def test_iris_refuses_more_samples_than_it_has():
    """Clamping silently would cap accuracy invisibly; raising is the contract."""
    with pytest.raises(QmlDatasetError) as excinfo:
        build_dataset(DatasetConfig(name="iris_binary", n_samples=200), _rng())
    assert "100" in str(excinfo.value)


def test_iris_subsample_keeps_the_class_balance():
    dataset = build_dataset(DatasetConfig(name="iris_binary", n_samples=40, test_fraction=0.3), _rng())
    total = np.concatenate([dataset.y_train, dataset.y_test])
    assert total.size == 40
    assert int(np.sum(total == 0)) == int(np.sum(total == 1)) == 20


def test_iris_excludes_virginica():
    """Only setosa and versicolor; the third class must be dropped, not merged."""
    x, y, names = datasets.load_iris_binary(100, _rng())
    assert x.shape == (100, 4)
    assert set(np.unique(y)) == {0, 1}
    assert len(names) == 4


def test_bundled_iris_file_is_the_authentic_150_row_dataset():
    """Guard the vendored data against truncation or accidental edits."""
    raw = datasets._IRIS_CSV.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "f13ffa8fdd56fd8e6c8d16d4081a3fbd3114bcd0aae4256c43205169cd9d1449"

    rows = datasets._read_iris()
    assert rows.shape == (150, 5)
    assert sorted(np.unique(rows[:, 4]).tolist()) == [0.0, 1.0, 2.0]


def test_circles_factor_is_validated():
    with pytest.raises(QmlDatasetError):
        datasets.make_circles(50, 0.1, _rng(), factor=1.5)


def test_split_never_empties_a_class():
    """Even at the smallest allowed size, both splits keep both classes."""
    dataset = build_dataset(DatasetConfig(name="moons", n_samples=20, test_fraction=0.1), _rng())
    assert set(np.unique(dataset.y_train)) == {0, 1}
    assert set(np.unique(dataset.y_test)) == {0, 1}


def test_dataset_max_samples_table_matches_reality():
    assert datasets.DATASET_MAX_SAMPLES["iris_binary"] == 100
    assert datasets.DATASET_MAX_SAMPLES["moons"] is None
