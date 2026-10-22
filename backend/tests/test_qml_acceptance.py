"""The nine QNN acceptance criteria, demonstrated end to end on one real run.

The master prompt is explicit that a circuit which merely runs and returns
measurements does not count. Each test below is named for the criterion it
discharges, and all of them share a single genuinely trained model so the
evidence comes from one coherent run rather than nine unrelated fixtures.

Nothing here is mocked — real circuits, real gradients, real optimisation.
"""

from __future__ import annotations

import time

import numpy as np
import pytest

from app.quantum.qml_lab import evaluator, limits, trainer
from app.quantum.qml_lab.datasets import build_dataset
from app.quantum.qml_lab.models import (
    CircuitConfig,
    DatasetConfig,
    QmlExperimentConfig,
    TrainingConfig,
)
from app.quantum.qml_lab.persistence import load_model, save_model
from app.quantum.qml_lab.vqc import VQC

CONFIG = QmlExperimentConfig(
    dataset=DatasetConfig(name="moons", n_samples=80, noise=0.1, test_fraction=0.3),
    circuit=CircuitConfig(n_qubits=2, n_layers=2, rotation="Y", entanglement="ring"),
    training=TrainingConfig(epochs=10, batch_size=8, learning_rate=0.25, diff_method="backprop"),
    seed=7,
)


@pytest.fixture(scope="module")
def trained():
    """One real training run, shared by every criterion below."""
    rng = np.random.default_rng(CONFIG.seed)
    dataset = build_dataset(CONFIG.dataset, rng)
    model = VQC(CONFIG.circuit, dataset.n_features, CONFIG.training.diff_method)
    start = model.initialise(rng)

    began = time.perf_counter()
    outcome = trainer.train(model, dataset, CONFIG.training, rng, start)
    wall_clock = time.perf_counter() - began

    return {
        "dataset": dataset,
        "model": model,
        "start": start,
        "outcome": outcome,
        "wall_clock": wall_clock,
    }


# -- 1 ---------------------------------------------------------------------


def test_criterion_1_a_valid_parameterised_circuit_executes(trained):
    model, params = trained["model"], trained["outcome"].params
    drawing = model.draw(trained["dataset"].x_train[0], params)

    assert "RY" in drawing and "RZ" in drawing, "ansatz rotations missing from the rendered circuit"
    assert params.circuit_weights.shape == (2, 2, 2)
    assert params.theta.size == limits.n_parameters(2, 2) + 1

    value = float(model.expectation(trained["dataset"].x_train[0], params.theta))
    assert -1.0 <= value <= 1.0


# -- 2 ---------------------------------------------------------------------


def test_criterion_2_predictions_are_derived_from_measurements(trained):
    model, params = trained["model"], trained["outcome"].params
    x = trained["dataset"].x_test

    measured = np.array([float(model.expectation(row, params.theta)) for row in x])
    decisions = np.asarray(model.decision_values(x, params.theta), dtype=float)

    # The decision value is the measurement plus the classical bias, nothing else.
    assert np.allclose(decisions, measured + params.bias)
    # And the hard label is the sign of that measurement-derived quantity.
    assert np.array_equal(model.predict(x, params), (decisions > 0).astype(int))


# -- 3 ---------------------------------------------------------------------


def test_criterion_3_the_training_loss_is_real_and_decreases(trained):
    history = trained["outcome"].history
    assert len(history) == CONFIG.training.epochs

    first, last = history[0].train_loss, history[-1].train_loss
    assert np.isfinite(first) and np.isfinite(last)
    assert last < first, f"loss did not improve: {first:.4f} -> {last:.4f}"

    # The reported loss is the optimised quantity, recomputed independently here.
    model, params, dataset = trained["model"], trained["outcome"].params, trained["dataset"]
    recomputed = float(
        trainer.square_loss(
            np.asarray(model.decision_values(dataset.x_train, params.theta), dtype=float),
            trainer.to_pm1(dataset.y_train),
        )
    )
    assert recomputed == pytest.approx(last, abs=1e-9)


def test_criterion_3b_the_model_learns_rather_than_merely_running(trained):
    """Accuracy must clear chance — a circuit that runs is not a classifier."""
    outcome, dataset, model = trained["outcome"], trained["dataset"], trained["model"]

    final_train = outcome.history[-1].train_accuracy
    assert final_train >= 0.75, f"train accuracy {final_train:.3f} is too close to chance"

    test_accuracy = float(np.mean(model.predict(dataset.x_test, outcome.params) == dataset.y_test))
    assert test_accuracy >= 0.70, f"test accuracy {test_accuracy:.3f} is too close to chance"


# -- 4 ---------------------------------------------------------------------


def test_criterion_4_gradients_come_from_a_supported_method(trained):
    """Both supported methods produce a real, non-zero gradient and agree.

    The detailed 1e-9 agreement check lives in ``test_qml_gradients.py``; this
    confirms the trained configuration itself is differentiable both ways.
    """
    from pennylane import grad as qml_grad
    from pennylane import numpy as pnp

    dataset, start = trained["dataset"], trained["start"]

    def gradient_with(method: str) -> np.ndarray:
        model = VQC(CONFIG.circuit, dataset.n_features, method)

        def cost(theta):
            return trainer.square_loss(
                model.decision_values(dataset.x_train[:8], theta), trainer.to_pm1(dataset.y_train[:8])
            )

        return np.asarray(qml_grad(cost, argnums=0)(pnp.array(start.theta, requires_grad=True)), dtype=float)

    backprop = gradient_with("backprop")
    shift = gradient_with("parameter-shift")

    assert np.linalg.norm(backprop) > 1e-6
    assert np.max(np.abs(backprop - shift)) < 1e-9


# -- 5 ---------------------------------------------------------------------


def test_criterion_5_parameters_are_updated(trained):
    start, final = trained["start"].theta, trained["outcome"].params.theta

    assert start.shape == final.shape
    assert not np.array_equal(start, final)
    assert np.linalg.norm(final - start) > 1e-3
    # More than one parameter moved — not just the bias riding the threshold.
    assert int(np.count_nonzero(np.abs(final - start) > 1e-6)) >= 3


# -- 6 ---------------------------------------------------------------------


def test_criterion_6_the_run_completes_within_its_limits(trained):
    outcome = trained["outcome"]

    assert outcome.status == "completed"
    assert outcome.epochs_completed == CONFIG.training.epochs

    limits.enforce(CONFIG)
    assert CONFIG.circuit.n_qubits <= limits.MAX_QUBITS
    assert CONFIG.training.epochs <= limits.MAX_EPOCHS

    # Comfortably inside the per-task soft limit proposed for Phase 2 (900 s).
    assert trained["wall_clock"] < 300, f"run took {trained['wall_clock']:.1f}s"


# -- 7 and 8 ---------------------------------------------------------------


def test_criterion_7_and_8_save_reload_and_identical_predictions(trained, tmp_path):
    model, params, dataset = trained["model"], trained["outcome"].params, trained["dataset"]

    before_proba = model.predict_proba(dataset.x_test, params)
    before_labels = model.predict(dataset.x_test, params)

    save_model(tmp_path, 1, CONFIG, params, metrics={"test_accuracy": float(np.mean(before_labels == dataset.y_test))})
    reloaded = load_model(tmp_path, 1)

    rebuilt = VQC(reloaded.config.circuit, dataset.n_features, reloaded.config.training.diff_method)
    after_proba = rebuilt.predict_proba(dataset.x_test, reloaded.params)
    after_labels = rebuilt.predict(dataset.x_test, reloaded.params)

    assert np.array_equal(before_proba, after_proba), "probabilities differ after reload"
    assert np.array_equal(before_labels, after_labels), "labels differ after reload"
    assert reloaded.config == CONFIG


# -- 9 ---------------------------------------------------------------------


def test_criterion_9_the_evaluation_is_coherent(trained):
    """The reported metrics must agree with the predictions they summarise."""
    model, params, dataset = trained["model"], trained["outcome"].params, trained["dataset"]
    predictions = model.predict(dataset.x_test, params)

    result = evaluator.evaluate(dataset.y_test, predictions)
    matrix = np.array(result.confusion_matrix)

    assert result.n_samples == dataset.y_test.size
    assert matrix.sum() == dataset.y_test.size
    assert result.accuracy == pytest.approx(float(np.mean(predictions == dataset.y_test)))
    assert (matrix[0][0] + matrix[1][1]) / matrix.sum() == pytest.approx(result.accuracy)


def test_the_whole_run_is_reproducible_from_the_seed_alone():
    """Two independent runs of the same config must agree bit-for-bit."""

    def run() -> np.ndarray:
        rng = np.random.default_rng(CONFIG.seed)
        dataset = build_dataset(CONFIG.dataset, rng)
        model = VQC(CONFIG.circuit, dataset.n_features, CONFIG.training.diff_method)
        start = model.initialise(rng)
        short = TrainingConfig(epochs=2, batch_size=8, learning_rate=0.25, diff_method="backprop")
        return trainer.train(model, dataset, short, rng, start).params.theta

    assert np.array_equal(run(), run())
