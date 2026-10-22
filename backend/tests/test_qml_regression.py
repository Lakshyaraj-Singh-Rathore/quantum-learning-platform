"""Regression algorithm: metrics, target scaling, leakage, and capacity.

The metric tests use values computed by hand rather than by a second
implementation — a test that recomputes MAE with the same numpy expression as
the implementation proves only that numpy is deterministic.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.quantum.qml_lab import limits
from app.quantum.qml_lab.datasets import ANGLE_MAX, ANGLE_MIN
from app.quantum.qml_lab.errors import QmlConfigError, QmlDatasetError
from app.quantum.qml_lab.models import CircuitConfig, RegressionResult, TrainingConfig
from app.quantum.qml_lab.regression import (
    QuantumRegressor,
    TargetScaler,
    evaluate_regression,
    mae,
    mse_loss,
    r2_score,
    rmse,
)
from app.quantum.qml_lab.regression_data import (
    REGRESSION_DATASETS,
    REQUIRED_ANGLE_FREQUENCY,
    RidgeBaseline,
    build_regression_dataset,
    train_regression,
)

# ---------------------------------------------------------------------------
# Metrics, against hand-computed values
# ---------------------------------------------------------------------------


def test_mae_matches_a_hand_computed_value():
    y_true = np.array([1.0, 2.0, 3.0, 4.0])
    y_pred = np.array([1.5, 1.0, 3.0, 6.0])
    # |0.5| + |1.0| + |0.0| + |2.0| = 3.5, over 4 = 0.875
    assert mae(y_true, y_pred) == pytest.approx(0.875)


def test_rmse_matches_a_hand_computed_value():
    y_true = np.array([1.0, 2.0, 3.0, 4.0])
    y_pred = np.array([1.5, 1.0, 3.0, 6.0])
    # (0.25 + 1.0 + 0.0 + 4.0) / 4 = 1.3125; sqrt = 1.1456439...
    assert rmse(y_true, y_pred) == pytest.approx(np.sqrt(1.3125))


def test_rmse_is_never_smaller_than_mae():
    """A power-mean inequality that any correct pair must satisfy."""
    rng = np.random.default_rng(7)
    for _ in range(20):
        a, b = rng.normal(size=30), rng.normal(size=30)
        assert rmse(a, b) >= mae(a, b) - 1e-12


def test_r2_matches_a_hand_computed_value():
    y_true = np.array([1.0, 2.0, 3.0, 4.0])
    y_pred = np.array([1.5, 1.0, 3.0, 6.0])
    # SS_res = 5.25; mean = 2.5; SS_tot = 2.25+0.25+0.25+2.25 = 5.0
    assert r2_score(y_true, y_pred) == pytest.approx(1.0 - 5.25 / 5.0)


def test_r2_is_exactly_one_for_a_perfect_fit():
    y = np.array([3.0, -1.0, 7.5, 2.25])
    assert r2_score(y, y.copy()) == pytest.approx(1.0)


def test_r2_is_zero_for_the_mean_predictor():
    """Predicting the mean is the definition of the R² = 0 reference point."""
    y = np.array([1.0, 2.0, 3.0, 10.0])
    assert r2_score(y, np.full_like(y, y.mean())) == pytest.approx(0.0)


def test_r2_goes_negative_for_a_predictor_worse_than_the_mean():
    y = np.array([1.0, 2.0, 3.0])
    assert r2_score(y, np.array([100.0, 100.0, 100.0])) < 0.0


def test_r2_never_returns_nan_on_a_constant_target():
    """Zero variance makes R² undefined; it must not leak ``nan`` into JSON.

    Mirrors ``precision_recall_f1``'s documented convention of returning a
    real number for a degenerate input instead of propagating nan.
    """
    constant = np.array([5.0, 5.0, 5.0])
    exact = r2_score(constant, constant.copy())
    wrong = r2_score(constant, np.array([5.0, 6.0, 5.0]))
    assert not np.isnan(exact) and not np.isnan(wrong)
    assert exact == pytest.approx(1.0)
    assert wrong == pytest.approx(0.0)


@pytest.mark.parametrize("metric", [mae, rmse, r2_score])
def test_metrics_reject_mismatched_shapes(metric):
    with pytest.raises(ValueError):
        metric(np.zeros(4), np.zeros(5))


def test_evaluate_regression_returns_the_regression_type_with_no_class_metrics():
    """§2C.4: separate types, not a classification result with None fields."""
    result = evaluate_regression(np.array([1.0, 2.0]), np.array([1.0, 3.0]))
    assert isinstance(result, RegressionResult)
    assert result.n_samples == 2
    for forbidden in ("accuracy", "precision", "recall", "f1", "confusion_matrix"):
        assert not hasattr(result, forbidden), (
            f"{forbidden} is undefined for regression; a null here invites a UI "
            f"rendering 0, which reads as 'scored zero'"
        )


# ---------------------------------------------------------------------------
# Target scaling
# ---------------------------------------------------------------------------


def test_target_scaler_maps_the_training_range_onto_exactly_minus_one_to_one():
    scaler = TargetScaler().fit(np.array([10.0, 20.0, 30.0, 40.0]))
    scaled = scaler.transform(np.array([10.0, 25.0, 40.0]))
    assert scaled[0] == pytest.approx(-1.0)
    assert scaled[1] == pytest.approx(0.0)
    assert scaled[2] == pytest.approx(1.0)


def test_target_scaler_round_trips():
    rng = np.random.default_rng(3)
    y = rng.normal(loc=12.0, scale=4.0, size=50)
    scaler = TargetScaler().fit(y)
    assert np.allclose(scaler.inverse_transform(scaler.transform(y)), y, atol=1e-12)


def test_target_scaler_refuses_to_transform_before_fit():
    with pytest.raises(QmlConfigError):
        TargetScaler().transform(np.array([1.0]))
    with pytest.raises(QmlConfigError):
        TargetScaler().inverse_transform(np.array([1.0]))


def test_target_scaler_survives_a_constant_target_without_dividing_by_zero():
    scaler = TargetScaler().fit(np.array([7.0, 7.0, 7.0]))
    out = scaler.transform(np.array([7.0, 7.0]))
    assert np.all(np.isfinite(out))


# ---------------------------------------------------------------------------
# Datasets and the §1A leakage assertion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", REGRESSION_DATASETS)
def test_every_regression_dataset_builds_and_splits(name):
    rng = np.random.default_rng(11)
    data = build_regression_dataset(name, 80, 0.05, 0.25, rng)
    assert data.x_train.shape[0] == 60
    assert data.x_test.shape[0] == 20
    assert data.y_train.shape == (60,)
    assert data.y_test.shape == (20,)


def test_unknown_regression_dataset_raises_rather_than_falling_back():
    with pytest.raises(QmlDatasetError, match="unknown regression dataset"):
        build_regression_dataset("moons", 40, 0.05, 0.25, np.random.default_rng(0))


def test_a_classification_dataset_name_is_not_silently_accepted():
    """``moons`` exists in the other registry; the two must not blur together."""
    for name in ("moons", "circles", "iris_binary"):
        with pytest.raises(QmlDatasetError):
            build_regression_dataset(name, 40, 0.05, 0.25, np.random.default_rng(0))


@pytest.mark.parametrize("name", REGRESSION_DATASETS)
def test_feature_scaler_is_fitted_on_train_only(name):
    """§1A leakage assertion, features.

    The training split must occupy the encoder range exactly; the test split
    is transformed by the *training* scaler and so may fall outside it. If the
    test split were also pinned to [0, π] the scaler saw it during fitting.
    """
    rng = np.random.default_rng(5)
    data = build_regression_dataset(name, 200, 0.05, 0.3, rng)

    assert data.x_train.min() == pytest.approx(ANGLE_MIN)
    assert data.x_train.max() == pytest.approx(ANGLE_MAX)

    # Exact, not inferential: the fitted bounds ARE the training split's raw
    # bounds. Had the scaler seen the test split, these would differ.
    assert np.array_equal(data.scaler.data_min, data.x_train_raw.min(axis=0))
    assert np.array_equal(data.scaler.data_max, data.x_train_raw.max(axis=0))

    full = np.vstack([data.x_train_raw, data.x_test_raw])
    assert np.all(data.scaler.data_min >= full.min(axis=0))
    assert np.all(data.scaler.data_max <= full.max(axis=0))


@pytest.mark.parametrize("name", REGRESSION_DATASETS)
def test_target_scaler_is_fitted_on_train_only(name):
    """§1A leakage assertion, **targets** — the half unique to regression.

    ``y_train`` must span exactly [-1, 1] after scaling. The test targets are
    mapped with the training scaler, so their scaled range is whatever it is;
    forcing it to [-1, 1] would mean the test maxima had been used to fit.
    """
    rng = np.random.default_rng(5)
    data = build_regression_dataset(name, 200, 0.05, 0.3, rng)

    assert data.y_train_scaled.min() == pytest.approx(-1.0)
    assert data.y_train_scaled.max() == pytest.approx(1.0)
    assert data.target_scaler.y_min == pytest.approx(float(np.min(data.y_train)))
    assert data.target_scaler.y_max == pytest.approx(float(np.max(data.y_train)))
    # the scaler must not have seen the test split at all
    assert data.target_scaler.y_min <= float(np.min(data.y_train))
    assert data.target_scaler.y_max >= float(np.max(data.y_train))


def test_scaled_targets_are_consistent_with_the_raw_targets():
    rng = np.random.default_rng(9)
    data = build_regression_dataset("sine", 120, 0.0, 0.25, rng)
    assert np.allclose(
        data.target_scaler.inverse_transform(data.y_test_scaled), data.y_test, atol=1e-12
    )


def test_a_split_that_would_empty_a_side_is_rejected():
    with pytest.raises(QmlDatasetError, match="test rows"):
        build_regression_dataset("sine", 20, 0.05, 0.001, np.random.default_rng(0))


def test_regression_datasets_are_reproducible_from_a_seed():
    a = build_regression_dataset("sine", 60, 0.1, 0.25, np.random.default_rng(42))
    b = build_regression_dataset("sine", 60, 0.1, 0.25, np.random.default_rng(42))
    assert np.array_equal(a.x_train, b.x_train)
    assert np.array_equal(a.y_test, b.y_test)


def test_every_regression_dataset_is_inside_the_frequency_budget():
    """A target the circuit cannot represent at any legal config is a bug.

    The scaler maps [-π, π] onto [0, π], doubling every frequency, and a
    re-uploading circuit reaches angle-frequency ``n_layers`` at most. A
    dataset needing more than ``MAX_LAYERS`` trains to a flat line and looks
    like a broken model rather than an impossible request.
    """
    assert set(REQUIRED_ANGLE_FREQUENCY) == set(REGRESSION_DATASETS)
    for name, needed in REQUIRED_ANGLE_FREQUENCY.items():
        assert needed <= limits.MAX_LAYERS, (
            f"{name} needs angle-frequency {needed} but MAX_LAYERS is "
            f"{limits.MAX_LAYERS}, so no permitted configuration can fit it"
        )


# ---------------------------------------------------------------------------
# Capacity: the re-uploading claim, measured
# ---------------------------------------------------------------------------


def test_reuploading_widens_the_frequency_spectrum():
    """The justification for re-uploading being the default, as a measurement.

    Sweep the encoded angle, FFT ``<Z₀>``, and compare frequency-2 power with
    and without re-uploading at identical parameters. Single encoding puts the
    model's accessible spectrum at {0, ±1}; frequency-2 power there is
    numerical noise.
    """
    rng = np.random.default_rng(0)
    config = CircuitConfig(n_qubits=4, n_layers=3)
    theta = np.concatenate([rng.normal(0.0, 1.0, size=limits.n_parameters(4, 3)), [0.0]])
    xs = np.linspace(0.0, 2.0 * np.pi, 128).reshape(-1, 1)

    def frequency_power(reuploading: bool) -> np.ndarray:
        model = QuantumRegressor(config, n_features=1, data_reuploading=reuploading)
        values = np.asarray(model.decision_values(xs, theta), dtype=float)
        return np.abs(np.fft.rfft(values)) / len(values)

    without, with_ = frequency_power(False), frequency_power(True)

    assert without[2] < 0.005, "single encoding should have no real frequency-2 content"
    assert with_[2] > 10.0 * without[2], (
        f"re-uploading must open frequency 2: {with_[2]:.5f} vs {without[2]:.5f}"
    )


def test_reuploading_is_on_by_default_and_reported():
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=1)
    assert model.data_reuploading is True
    described = model.describe()
    assert described["data_reuploading"] is True
    assert described["max_frequency"] == 2
    assert described["algorithm"] == "quantum_regression"
    assert described["loss"] == "mse"


# ---------------------------------------------------------------------------
# Model behaviour
# ---------------------------------------------------------------------------


def test_decision_values_are_continuous_and_not_thresholded():
    """A regressor that quietly returns ±1 is a classifier wearing a hat."""
    rng = np.random.default_rng(2)
    data = build_regression_dataset("sine", 60, 0.05, 0.25, rng)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=1)
    values = model.predict_scaled(data.x_test, model.initialise(rng))
    assert not np.all(np.isin(np.unique(np.round(values, 9)), (-1.0, 0.0, 1.0)))
    assert len(np.unique(np.round(values, 6))) > 2


def test_predictions_are_returned_in_the_users_units():
    """MAE must be reportable in the target's units, not scaled ones."""
    rng = np.random.default_rng(4)
    data = build_regression_dataset("linear_mix", 80, 0.0, 0.25, rng)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=2)
    params = model.initialise(rng)

    scaled = model.predict_scaled(data.x_test, params)
    real = model.predict(data.x_test, params, data.target_scaler)
    assert np.allclose(real, data.target_scaler.inverse_transform(scaled), atol=1e-12)
    # the raw circuit output cannot exceed |1| + |bias=0|
    assert np.max(np.abs(scaled)) <= 1.0 + 1e-9


def test_the_output_bias_shifts_every_prediction_by_exactly_its_own_amount():
    """The bias inits to zero, so it is invisible unless set explicitly.

    This is the hole mutant H3 exposed in the hybrid: a parameter that starts
    at 0.0 passes every test that uses the default initialisation.
    """
    rng = np.random.default_rng(6)
    data = build_regression_dataset("sine", 40, 0.0, 0.25, rng)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=1)
    params = model.initialise(rng)

    base = model.predict_scaled(data.x_test, params)
    shifted = params.copy()
    shifted.theta[-1] = 0.37
    moved = model.predict_scaled(data.x_test, shifted)

    assert np.allclose(moved - base, 0.37, atol=1e-9)


def test_mse_loss_matches_a_hand_computed_value():
    predictions = np.array([0.5, -0.5, 1.0])
    targets = np.array([0.0, 0.0, 0.0])
    # (0.25 + 0.25 + 1.0) / 3 = 0.5
    assert float(mse_loss(predictions, targets)) == pytest.approx(0.5)


def test_regression_parameters_expose_the_circuit_block_without_the_bias():
    rng = np.random.default_rng(8)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=1)
    params = model.initialise(rng)
    assert params.theta.shape == (limits.n_parameters(4, 2) + 1,)
    assert params.circuit_weights.shape == (2, 4, 2)
    assert params.bias == pytest.approx(0.0)


def test_draw_renders_the_reuploading_structure():
    rng = np.random.default_rng(1)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=3), n_features=1)
    params = model.initialise(rng)
    drawing = model.draw(np.array([0.5]), params)
    # three encoding blocks, one per layer
    assert drawing.count("RY") >= 3
    assert "<Z>" in drawing


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def test_training_reduces_loss_and_improves_r2():
    rng = np.random.default_rng(1234)
    data = build_regression_dataset("linear_mix", 90, 0.03, 0.3, rng)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=2)
    outcome = train_regression(
        model,
        data,
        TrainingConfig(epochs=12, batch_size=16, learning_rate=0.1),
        rng,
        model.initialise(rng),
    )
    assert outcome.status == "completed"
    assert outcome.epochs_completed == 12
    assert len(outcome.history) == 12
    assert outcome.history[-1].train_loss < outcome.history[0].train_loss
    assert outcome.history[-1].train_r2 > outcome.history[0].train_r2


def test_training_history_records_the_regression_type_not_accuracy():
    rng = np.random.default_rng(13)
    data = build_regression_dataset("sine", 40, 0.05, 0.25, rng)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=1)
    outcome = train_regression(
        model,
        data,
        TrainingConfig(epochs=2, batch_size=16, learning_rate=0.1),
        rng,
        model.initialise(rng),
    )
    record = outcome.history[0]
    assert hasattr(record, "train_r2") and hasattr(record, "test_r2")
    for forbidden in ("train_accuracy", "test_accuracy"):
        assert not hasattr(record, forbidden)


def test_training_is_reproducible_from_a_seed():
    def run():
        rng = np.random.default_rng(99)
        data = build_regression_dataset("sine", 40, 0.05, 0.25, rng)
        model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=1)
        outcome = train_regression(
            model,
            data,
            TrainingConfig(epochs=3, batch_size=16, learning_rate=0.1),
            rng,
            model.initialise(rng),
        )
        return outcome.params.theta

    assert np.allclose(run(), run(), atol=1e-12)


def test_training_honours_cancellation():
    rng = np.random.default_rng(21)
    data = build_regression_dataset("sine", 40, 0.05, 0.25, rng)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=1)
    outcome = train_regression(
        model,
        data,
        TrainingConfig(epochs=10, batch_size=16, learning_rate=0.1),
        rng,
        model.initialise(rng),
        should_cancel=lambda: True,
    )
    assert outcome.status == "cancelled"
    assert outcome.interrupted
    assert outcome.cancelled_at_epoch == 1
    assert outcome.epochs_completed == 0


def test_training_honours_a_deadline_and_reports_timed_out_not_cancelled():
    """The two interruption reasons must stay distinguishable."""
    rng = np.random.default_rng(22)
    data = build_regression_dataset("sine", 40, 0.05, 0.25, rng)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=1)
    outcome = train_regression(
        model,
        data,
        TrainingConfig(epochs=10, batch_size=16, learning_rate=0.1),
        rng,
        model.initialise(rng),
        deadline_seconds=0.0,
    )
    assert outcome.status == "timed_out"
    assert outcome.interrupted


def test_progress_events_are_emitted_for_batches_and_epochs():
    rng = np.random.default_rng(23)
    data = build_regression_dataset("sine", 40, 0.05, 0.25, rng)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=2), n_features=1)
    seen: list[str] = []
    train_regression(
        model,
        data,
        TrainingConfig(epochs=2, batch_size=16, learning_rate=0.1),
        rng,
        model.initialise(rng),
        on_progress=lambda event: seen.append(event.message),
    )
    assert "batch" in seen and "epoch" in seen
    assert seen.count("epoch") == 2


# ---------------------------------------------------------------------------
# Ridge baseline (the comparison bar)
# ---------------------------------------------------------------------------


def test_ridge_recovers_known_coefficients_on_noiseless_linear_data():
    """``y = 1.5·x₁ − 0.8·x₂`` with no noise; ridge should find exactly that."""
    rng = np.random.default_rng(31)
    x = rng.uniform(-1.0, 1.0, size=(400, 2))
    y = 1.5 * x[:, 0] - 0.8 * x[:, 1] + 2.0

    model = RidgeBaseline(l2=1e-8).fit(x, y)
    assert model.coefficients[0] == pytest.approx(1.5, abs=1e-4)
    assert model.coefficients[1] == pytest.approx(-0.8, abs=1e-4)
    assert model.intercept == pytest.approx(2.0, abs=1e-4)


def test_ridge_does_not_penalise_the_intercept():
    """A penalised intercept biases predictions toward 0 rather than the mean."""
    rng = np.random.default_rng(32)
    x = rng.uniform(-1.0, 1.0, size=(200, 2))
    y = np.full(200, 50.0)

    model = RidgeBaseline(l2=10.0).fit(x, y)
    assert model.intercept == pytest.approx(50.0, abs=1e-6)


def test_ridge_shrinks_coefficients_as_l2_grows():
    rng = np.random.default_rng(33)
    x = rng.uniform(-1.0, 1.0, size=(100, 2))
    y = 3.0 * x[:, 0]
    weak = RidgeBaseline(l2=1e-6).fit(x, y)
    strong = RidgeBaseline(l2=100.0).fit(x, y)
    assert np.linalg.norm(strong.coefficients) < np.linalg.norm(weak.coefficients)


def test_ridge_refuses_to_predict_before_fit():
    with pytest.raises(QmlDatasetError):
        RidgeBaseline().predict(np.zeros((2, 2)))


def test_ridge_is_a_genuine_bar_on_the_linear_control():
    """``linear_mix`` exists so the baseline is strong, not a strawman."""
    rng = np.random.default_rng(34)
    data = build_regression_dataset("linear_mix", 200, 0.02, 0.3, rng)
    model = RidgeBaseline().fit(data.x_train, data.y_train)
    result = evaluate_regression(data.y_test, model.predict(data.x_test))
    assert result.r2 > 0.95, f"ridge should nearly solve a linear target, got {result.r2}"


def test_quantum_regressor_beats_the_mean_predictor_on_a_nonlinear_target():
    """The minimum bar: positive R² means it learned something real."""
    rng = np.random.default_rng(1234)
    data = build_regression_dataset("sine", 120, 0.03, 0.3, rng)
    model = QuantumRegressor(CircuitConfig(n_qubits=4, n_layers=3), n_features=1)
    outcome = train_regression(
        model,
        data,
        TrainingConfig(epochs=25, batch_size=16, learning_rate=0.1),
        rng,
        model.initialise(rng),
    )
    result = evaluate_regression(
        data.y_test, model.predict(data.x_test, outcome.params, data.target_scaler)
    )
    assert result.r2 > 0.5, f"expected a real fit on sin(x), got R²={result.r2}"
