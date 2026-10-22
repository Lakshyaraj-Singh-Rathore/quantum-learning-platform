"""Schema strictness and resource limits for the QML Lab.

The headline test here is :func:`test_flat_payload_is_rejected_loudly`. The
Noise Lab next door accepts a flat payload and silently returns a plausible
wrong answer; this suite exists to guarantee the QML schema never acquires
that behaviour.
"""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from app.quantum.qml_lab import limits
from app.quantum.qml_lab.errors import QmlLimitExceededError
from app.quantum.qml_lab.models import (
    CircuitConfig,
    DatasetConfig,
    QmlExperimentConfig,
    TrainingConfig,
)
from app.quantum.noise_lab.models import NoiseConfig


def test_defaults_match_the_documented_limit_table():
    config = QmlExperimentConfig()
    assert config.circuit.n_qubits == limits.DEFAULT_QUBITS == 4
    assert config.circuit.n_layers == limits.DEFAULT_LAYERS == 2
    assert config.dataset.n_samples == limits.DEFAULT_SAMPLES == 200
    assert config.training.epochs == limits.DEFAULT_EPOCHS == 20
    assert config.training.batch_size == limits.DEFAULT_BATCH_SIZE == 16


def test_maxima_match_the_documented_limit_table():
    assert (limits.MAX_QUBITS, limits.MAX_LAYERS) == (8, 4)
    assert (limits.MAX_SAMPLES, limits.MAX_EPOCHS, limits.MAX_BATCH_SIZE) == (1000, 100, 32)
    assert limits.MAX_CONCURRENT_JOBS == 1
    assert limits.DENSITY_MATRIX_MAX_QUBITS < limits.MAX_QUBITS


def test_flat_payload_is_rejected_loudly():
    """A wrong-shaped config must raise, not quietly fall back to defaults.

    This is the QML Lab's answer to the Noise Lab trap: there, posting
    ``{"depolarizing": 0.35}`` returns a noiseless result that looks real.
    """
    with pytest.raises(ValidationError):
        QmlExperimentConfig.model_validate({"n_qubits": 4, "epochs": 10, "dataset_name": "moons"})


def test_the_noise_lab_contrast_is_real_not_folklore():
    """Pin the behaviour this schema is defending against.

    Read-only: it asserts what the Noise Lab currently does, and changes
    nothing there. If the Noise Lab is ever tightened this test fails, and the
    rationale above should be updated rather than left as a stale story.
    """
    silently_accepted = NoiseConfig(depolarizing=0.35, amplitude_damping=0.1, t1=50.0)
    groups = silently_accepted.model_dump()
    enabled = [v["enabled"] for v in groups.values() if isinstance(v, dict) and "enabled" in v]

    assert enabled, "expected the Noise Lab config to expose enabled flags"
    assert all(flag is False for flag in enabled), (
        "the Noise Lab silently ignores a flat payload and returns every group disabled; "
        "the QML schema forbids extras precisely so it cannot do this"
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"dataset": {"name": "moons", "unexpected": 1}},
        {"circuit": {"n_qubits": 2, "depth": 3}},
        {"training": {"epochs": 5, "optimiser": "adam"}},
        {"seed": 1, "extra_top_level": True},
    ],
)
def test_unknown_fields_are_refused_at_every_level(payload):
    with pytest.raises(ValidationError):
        QmlExperimentConfig.model_validate(payload)


@pytest.mark.parametrize(
    "group, field, value",
    [
        (CircuitConfig, "n_qubits", 9),
        (CircuitConfig, "n_qubits", 0),
        (CircuitConfig, "n_layers", 5),
        (DatasetConfig, "n_samples", 1001),
        (DatasetConfig, "n_samples", 19),
        (DatasetConfig, "test_fraction", 0.6),
        (TrainingConfig, "epochs", 101),
        (TrainingConfig, "batch_size", 33),
        (TrainingConfig, "learning_rate", 0.0),
    ],
)
def test_out_of_range_values_are_refused(group, field, value):
    with pytest.raises(ValidationError):
        group(**{field: value})


@pytest.mark.parametrize("name", ["moons", "circles", "iris_binary"])
def test_supported_datasets_validate(name):
    assert DatasetConfig(name=name).name == name


def test_unsupported_dataset_is_refused():
    with pytest.raises(ValidationError):
        DatasetConfig(name="mnist")


def test_unsupported_diff_method_is_refused():
    with pytest.raises(ValidationError):
        TrainingConfig(diff_method="adjoint")


def test_enforce_passes_a_valid_config():
    limits.enforce(QmlExperimentConfig())


def test_enforce_catches_a_config_that_bypassed_the_schema():
    """The worker re-check must catch a row written under looser limits.

    ``model_construct`` skips validation, which is exactly what loading a
    stored config with an outdated shape would do.
    """
    config = QmlExperimentConfig()
    config.circuit = CircuitConfig.model_construct(n_qubits=64, n_layers=99, rotation="Y", entanglement="ring")

    violations = limits.check(config)
    assert any("n_qubits=64" in v for v in violations)
    assert any("n_layers=99" in v for v in violations)

    with pytest.raises(QmlLimitExceededError) as excinfo:
        limits.enforce(config)
    assert excinfo.value.violations == violations


def test_parameter_count_is_two_rotations_per_qubit_per_layer():
    assert limits.n_parameters(4, 2) == 16
    assert limits.n_parameters(2, 1) == 4


def test_cost_estimate_reflects_the_parameter_shift_penalty():
    backprop = QmlExperimentConfig.model_validate(
        {"training": {"diff_method": "backprop"}, "circuit": {"n_qubits": 4, "n_layers": 2}}
    )
    shift = QmlExperimentConfig.model_validate(
        {"training": {"diff_method": "parameter-shift"}, "circuit": {"n_qubits": 4, "n_layers": 2}}
    )

    cheap = limits.estimate_cost(backprop)
    dear = limits.estimate_cost(shift)

    assert cheap["executions_per_sample"] == 1
    assert dear["executions_per_sample"] == 1 + 2 * 16
    assert dear["circuit_executions"] > cheap["circuit_executions"]
    assert cheap["state_vector_amplitudes"] == 16


def test_limit_table_is_exposed_for_the_ui():
    """Phase 2 serves this so the UI cannot drift from the server's numbers."""
    assert limits.LIMITS["n_qubits"]["max"] == limits.MAX_QUBITS
    assert limits.LIMITS["epochs"]["max"] == limits.MAX_EPOCHS
    assert limits.LIMITS["batch_size"]["default"] == limits.DEFAULT_BATCH_SIZE


# ---------------------------------------------------------------------------
# D-028: the evaluation term is per epoch, not once.
# ---------------------------------------------------------------------------


def _cost_config(*, epochs: int, n_samples: int, diff_method: str = "backprop"):
    return QmlExperimentConfig.model_validate(
        {
            "dataset": {"name": "moons", "n_samples": n_samples, "test_fraction": 0.3},
            "circuit": {"n_qubits": 2, "n_layers": 1},
            "training": {"epochs": epochs, "batch_size": 16, "diff_method": diff_method},
        }
    )


def test_estimate_cost_charges_evaluation_once_per_epoch():
    """The exact shortfall D-028 describes: ``(epochs - 1) * n_samples``.

    The superseded implementation used ``eval_execs = n_samples`` — one pass
    "at the end". ``trainer.train`` scores both splits every epoch, so the old
    number was short by this much. Asserting the gap explicitly means the bug
    cannot reappear as a silent off-by-one-epoch.
    """
    epochs, n_samples = 7, 80
    cfg = _cost_config(epochs=epochs, n_samples=n_samples)
    cost = limits.estimate_cost(cfg)

    assert cost["evaluation_executions"] == epochs * n_samples

    superseded = cost["training_executions"] + n_samples
    assert cost["circuit_executions"] - superseded == (epochs - 1) * n_samples


def test_estimate_cost_matches_a_real_training_run():
    """Count a real run with ``qml.Tracker`` and demand exact agreement.

    No mocked qnode and no stubbed gradient: this drives the shipped trainer
    over a real dataset and compares the estimator against the simulator's own
    execution counter. Before D-028 this measured 306 against a claimed 186.
    """
    import pennylane as qml

    from app.quantum.qml_lab.datasets import build_dataset
    from app.quantum.qml_lab.trainer import train
    from app.quantum.qml_lab.vqc import VQC

    for diff_method in ("backprop", "parameter-shift"):
        cfg = _cost_config(epochs=3, n_samples=60, diff_method=diff_method)
        rng = np.random.default_rng(cfg.seed)
        data = build_dataset(cfg.dataset, rng)
        model = VQC(cfg.circuit, n_features=data.x_train.shape[1], diff_method=diff_method)

        with qml.Tracker(model.device) as tracker:
            train(model, data, cfg.training, rng, model.initialise(rng))

        measured = int(tracker.totals["executions"])
        assert measured == limits.estimate_cost(cfg)["circuit_executions"], (
            f"{diff_method}: estimator and qml.Tracker disagree"
        )
