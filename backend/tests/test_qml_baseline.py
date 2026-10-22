"""The classical baseline must be a genuinely trained model.

If the baseline were a constant or majority-class predictor, the
quantum-vs-classical comparison in the Phase 3 results view would be
meaningless — the QNN would win for free. These tests make that failure mode
impossible to ship silently.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.quantum.qml_lab.baseline import LogisticRegressionBaseline, _sigmoid, run_baseline
from app.quantum.qml_lab.datasets import build_dataset
from app.quantum.qml_lab.models import DatasetConfig


def _separable(n=120, seed=3):
    """Two well-separated Gaussian blobs — a linear model should nearly ace this."""
    rng = np.random.default_rng(seed)
    half = n // 2
    negative = rng.normal(loc=[-2.0, -2.0], scale=0.5, size=(half, 2))
    positive = rng.normal(loc=[2.0, 2.0], scale=0.5, size=(n - half, 2))
    x = np.vstack([negative, positive])
    y = np.hstack([np.zeros(half, dtype=int), np.ones(n - half, dtype=int)])
    return x, y


def test_it_clears_an_accuracy_floor_on_linearly_separable_data():
    x, y = _separable()
    model = LogisticRegressionBaseline().fit(x, y, np.random.default_rng(0))

    assert model.converged is True
    assert float(np.mean(model.predict(x) == y)) >= 0.95


def test_coefficients_move_from_their_initialisation():
    """A stub that returns its starting weights would pass an accuracy check
    on an easy dataset by luck; it cannot pass this."""
    x, y = _separable()
    model = LogisticRegressionBaseline().fit(x, y, np.random.default_rng(0))

    assert model.coefficients is not None
    assert model.initial_coefficients is not None
    assert model.coefficient_shift() > 0.5
    assert not np.allclose(model.coefficients, model.initial_coefficients)


def test_it_is_not_a_constant_predictor():
    x, y = _separable()
    model = LogisticRegressionBaseline().fit(x, y, np.random.default_rng(0))

    predictions = model.predict(x)
    assert set(np.unique(predictions)) == {0, 1}

    probabilities = model.predict_proba(x)
    assert probabilities.min() < 0.25 and probabilities.max() > 0.75


def test_the_decision_boundary_points_the_right_way():
    """Coefficients must be positive when class 1 sits at larger coordinates."""
    x, y = _separable()
    model = LogisticRegressionBaseline().fit(x, y, np.random.default_rng(0))
    assert np.all(model.coefficients > 0)


def test_it_struggles_where_it_should_struggle():
    """On moons, a linear model must not look perfect.

    This is what makes the comparison informative: if the baseline scored
    100% here there would be nothing for a quantum model to demonstrate.
    """
    dataset = build_dataset(DatasetConfig(name="moons", n_samples=200, noise=0.1), np.random.default_rng(4))
    model = LogisticRegressionBaseline().fit(dataset.x_train, dataset.y_train, np.random.default_rng(0))
    accuracy = float(np.mean(model.predict(dataset.x_test) == dataset.y_test))
    assert accuracy < 0.98


def test_predicting_before_fitting_is_refused():
    with pytest.raises(ValueError):
        LogisticRegressionBaseline().predict(np.zeros((2, 2)))


def test_same_seed_reproduces_the_same_fit():
    x, y = _separable()
    first = LogisticRegressionBaseline().fit(x, y, np.random.default_rng(13))
    second = LogisticRegressionBaseline().fit(x, y, np.random.default_rng(13))
    assert np.allclose(first.coefficients, second.coefficients)
    assert first.intercept == pytest.approx(second.intercept)


def test_sigmoid_is_stable_at_both_extremes():
    """The naive form overflows for large negative input."""
    values = _sigmoid(np.array([-1000.0, -1.0, 0.0, 1.0, 1000.0]))
    assert np.all(np.isfinite(values))
    assert values[0] == pytest.approx(0.0, abs=1e-12)
    assert values[2] == pytest.approx(0.5)
    assert values[4] == pytest.approx(1.0, abs=1e-12)


def test_run_baseline_reports_both_splits():
    dataset = build_dataset(DatasetConfig(name="circles", n_samples=120), np.random.default_rng(6))
    result = run_baseline(
        dataset.x_train, dataset.y_train, dataset.x_test, dataset.y_test, np.random.default_rng(0)
    )

    assert result.model == "logistic_regression_l2"
    assert 0.0 <= result.train_accuracy <= 1.0
    assert 0.0 <= result.test_accuracy <= 1.0
    assert result.n_parameters == dataset.n_features + 1
