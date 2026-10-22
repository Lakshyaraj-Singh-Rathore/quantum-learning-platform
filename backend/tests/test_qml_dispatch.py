"""The capability document and the execution path must agree.

This file exists because Phase 5 shipped a `/qml/describe` that advertised
three algorithms and three regression datasets the backend could not actually
run: `DatasetConfig` 422-rejected `sine`, and `services.run` built a `VQC`
regardless of `config.algorithm`. Every layer in between — the schema, the
limits table, the capability document — accepted the selection and then
silently trained something else.

That is worse than a missing feature: it is a wrong answer that looks like a
right one. These are the invariants that make it impossible again. They were
written to **fail** against the pre-dispatch backend and are the acceptance
criteria for §2D.
"""

from __future__ import annotations

import typing

import numpy as np
import pytest

from app.quantum.qml_lab import algorithms, datasets, limits
from app.quantum.qml_lab.models import DatasetConfig, QmlExperimentConfig
from app.services.qml_lab import describe


def _advertised_datasets() -> set[str]:
    names: set[str] = set()
    for entry in describe()["algorithms"]:
        names.update(d["name"] for d in entry["datasets"])
    return names


# ---------------------------------------------------------------------------
# The capability document cannot advertise what the schema rejects
# ---------------------------------------------------------------------------


def test_every_advertised_dataset_is_accepted_by_the_schema():
    """The headline invariant.

    Fixing this by deleting the regression datasets from ``describe()`` would
    hide the gap and force the capability contract to be edited twice, so it
    is explicitly not the remedy.
    """
    rejected: list[tuple[str, str]] = []
    for name in sorted(_advertised_datasets()):
        try:
            DatasetConfig(name=name, n_samples=60, noise=0.05, test_fraction=0.3)
        except Exception as exc:  # noqa: BLE001 - the point is to report, not to classify
            rejected.append((name, type(exc).__name__))

    assert not rejected, (
        f"/qml/describe advertises datasets the schema rejects: {rejected}. "
        f"A client built to 'drive everything from /qml/describe' would render "
        f"these and get a 422 on every run."
    )


def test_the_dataset_literal_and_the_registry_cannot_drift():
    """One registry. Hand-editing two lists is how the frozen-dict drift happened."""
    literal_names = set(typing.get_args(DatasetConfig.model_fields["name"].annotation))
    assert literal_names == set(datasets.ALL_DATASETS), (
        f"DatasetConfig Literal {sorted(literal_names)} disagrees with the registry "
        f"{sorted(datasets.ALL_DATASETS)}"
    )


def test_every_advertised_dataset_can_actually_be_built():
    """Accepted by the schema is not the same as buildable by the builder."""
    rng = np.random.default_rng(0)
    for name in sorted(_advertised_datasets()):
        config = DatasetConfig(name=name, n_samples=60, noise=0.05, test_fraction=0.3)
        built = algorithms.build_dataset_for_task(
            config, datasets.task_for_dataset(name), np.random.default_rng(0)
        )
        assert built.x_train.shape[0] > 0, f"{name} built an empty training split"
        assert built.n_features >= 1
    del rng


# ---------------------------------------------------------------------------
# Every advertised algorithm must be dispatchable
# ---------------------------------------------------------------------------


def test_every_advertised_algorithm_has_a_task():
    advertised = {entry["name"] for entry in describe()["algorithms"]}
    assert advertised == set(algorithms.TASK_BY_ALGORITHM)
    assert advertised == set(limits.ALGORITHMS)


def test_describe_task_matches_the_dispatch_table():
    """The capability document must not claim a task the dispatcher disagrees with."""
    for entry in describe()["algorithms"]:
        assert entry["task"] == algorithms.task_for(entry["name"]), (
            f"describe() says {entry['name']} is {entry['task']} but the dispatcher "
            f"says {algorithms.task_for(entry['name'])}"
        )


@pytest.mark.parametrize("algorithm", sorted(limits.ALGORITHMS))
def test_every_algorithm_builds_its_own_engine_not_a_vqc(algorithm):
    """The defect this phase exists to fix.

    Before dispatch, ``services.run`` built a ``VQC`` for every algorithm, so
    selecting ``quantum_regression`` trained a classifier and returned
    accuracy. This asserts each algorithm maps to a *distinct* engine type.
    """
    config = _config_for(algorithm)
    dataset = algorithms.build_dataset_for_task(
        config.dataset, algorithms.task_for(algorithm), np.random.default_rng(0)
    )
    model = algorithms.build_model(config, dataset.n_features)
    assert type(model).__name__ == algorithms.ENGINE_BY_ALGORITHM[algorithm], (
        f"{algorithm} built {type(model).__name__}"
    )


def test_the_four_algorithms_do_not_all_build_the_same_engine():
    """A guard against a dispatcher that returns VQC for everything."""
    engines = set(algorithms.ENGINE_BY_ALGORITHM.values())
    assert len(engines) == 4, f"expected four distinct engines, got {engines}"


# ---------------------------------------------------------------------------
# Task/dataset compatibility is enforced, not assumed
# ---------------------------------------------------------------------------


def test_a_regression_algorithm_rejects_a_classification_dataset():
    with pytest.raises(Exception):
        QmlExperimentConfig.model_validate(
            {
                "algorithm": "quantum_regression",
                "dataset": {"name": "moons", "n_samples": 60, "noise": 0.05, "test_fraction": 0.3},
                "circuit": {"n_qubits": 4, "n_layers": 2},
                "training": {"epochs": 2, "batch_size": 16, "learning_rate": 0.1},
            }
        )


@pytest.mark.parametrize("algorithm", ["vqc", "hybrid_qnn", "quantum_kernel"])
def test_a_classification_algorithm_rejects_a_regression_dataset(algorithm):
    with pytest.raises(Exception):
        QmlExperimentConfig.model_validate(
            {
                "algorithm": algorithm,
                "dataset": {"name": "sine", "n_samples": 60, "noise": 0.05, "test_fraction": 0.3},
                "circuit": {"n_qubits": 4, "n_layers": 2},
                "training": {"epochs": 2, "batch_size": 16, "learning_rate": 0.1},
            }
        )


def _config_for(algorithm: str) -> QmlExperimentConfig:
    """A minimal valid config for one algorithm, using its own default dataset."""
    task = algorithms.task_for(algorithm)
    dataset_name = "sine" if task == "regression" else "moons"
    payload: dict = {
        "algorithm": algorithm,
        "dataset": {
            "name": dataset_name,
            "n_samples": 60,
            "noise": 0.05,
            "test_fraction": 0.3,
        },
        "circuit": {"n_qubits": 4, "n_layers": 2},
        "training": {
            "epochs": 1 if algorithm == "quantum_kernel" else 2,
            "batch_size": 16,
            "learning_rate": 0.1,
        },
    }
    if algorithm == "hybrid_qnn":
        payload["circuit"]["n_hidden"] = 3
    return QmlExperimentConfig.model_validate(payload)


# ---------------------------------------------------------------------------
# Each algorithm runs end to end and produces its own task's metrics
# ---------------------------------------------------------------------------


def _run(algorithm: str, epochs: int = 2):
    config = _config_for(algorithm)
    if epochs != 2 and algorithm != "quantum_kernel":
        config.training.epochs = epochs
    rng = np.random.default_rng(1234)
    dataset = algorithms.build_dataset_for_config(config, rng)
    return config, dataset, algorithms.run_algorithm(config, dataset, rng)


@pytest.mark.parametrize("algorithm", sorted(limits.ALGORITHMS))
def test_every_algorithm_completes_and_reports_its_own_task(algorithm):
    config, _dataset, outcome = _run(algorithm)
    assert outcome.status == "completed"
    assert outcome.task == algorithms.task_for(algorithm)
    assert outcome.result["task"] == outcome.task
    assert outcome.result["algorithm"] == algorithm


def test_regression_results_carry_no_classification_metric_anywhere():
    """§2C.4 at the result layer, checked over the whole nested payload."""
    import json

    _config, _dataset, outcome = _run("quantum_regression")
    blob = json.dumps(outcome.result)
    for banned in ("accuracy", "precision", "recall", "confusion_matrix"):
        assert banned not in blob, f"regression result leaked {banned!r}: {blob[:400]}"
    assert set(outcome.result["evaluation"]) == {"mae", "rmse", "r2", "n_samples"}


def test_classification_results_carry_no_regression_metric():
    _config, _dataset, outcome = _run("vqc")
    assert "mae" not in outcome.result["evaluation"]
    assert "r2" not in outcome.result["evaluation"]
    assert "accuracy" in outcome.result["evaluation"]


def test_the_kernel_writes_no_epochs_rather_than_a_synthetic_one():
    """§2D.1.5: do not manufacture an epoch to satisfy a persistence path."""
    _config, _dataset, outcome = _run("quantum_kernel")
    assert outcome.history == []
    assert outcome.epochs_completed == 0
    assert outcome.result["epochs_completed"] == 0
    assert outcome.result["final_train_accuracy"] is None


def test_the_kernel_reports_an_honest_progress_contract():
    config = _config_for("quantum_kernel")
    rng = np.random.default_rng(0)
    dataset = algorithms.build_dataset_for_config(config, rng)
    seen: list[str] = []
    algorithms.run_algorithm(config, dataset, rng, on_progress=lambda e: seen.append(e.message))
    assert "kernel:gram" in seen and "kernel:solve" in seen
    assert not any(m == "epoch" for m in seen), "kernel must not emit epoch events"


def test_kernel_result_labels_itself_lssvm_and_bounds_the_gram_preview():
    _config, _dataset, outcome = _run("quantum_kernel")
    kernel = outcome.result["kernel"]
    assert kernel["classifier"] == "LSSVM"
    preview = kernel["gram_preview"]
    assert preview["size"] <= algorithms.GRAM_PREVIEW_MAX
    assert len(preview["values"]) == preview["size"]
    assert preview["values"][0][0] == pytest.approx(1.0), "unit diagonal"


def test_regression_history_records_r2_and_never_accuracy():
    _config, _dataset, outcome = _run("quantum_regression")
    record = outcome.history[0]
    assert hasattr(record, "train_r2")
    assert not hasattr(record, "train_accuracy")


def test_hybrid_and_vqc_produce_different_results_on_the_same_data():
    """Proof the dispatcher actually swapped the engine.

    If dispatch silently returned a VQC for the hybrid, the two runs would
    agree exactly -- same seed, same dataset, same trainer.
    """
    _c1, _d1, vqc_outcome = _run("vqc")
    _c2, _d2, hybrid_outcome = _run("hybrid_qnn")
    assert (
        vqc_outcome.result["evaluation"] != hybrid_outcome.result["evaluation"]
        or vqc_outcome.result["circuit"] != hybrid_outcome.result["circuit"]
    )
    assert hybrid_outcome.result["circuit"]["algorithm"] == "hybrid_qnn"


# ---------------------------------------------------------------------------
# Persistence round-trips, one per artifact kind
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("algorithm", sorted(limits.ALGORITHMS))
def test_every_artifact_round_trips_through_disk(tmp_path, algorithm):
    from app.quantum.qml_lab.persistence import load_model, save_model

    config, _dataset, outcome = _run(algorithm)
    save_model(tmp_path, 1, config, outcome.artifact, metrics={"task": outcome.task})
    loaded = load_model(tmp_path, 1)

    assert loaded.config.algorithm == algorithm
    assert type(loaded.params).__name__ == _ARTIFACT_TYPE[algorithm]


_ARTIFACT_TYPE = {
    "vqc": "Parameters",
    "hybrid_qnn": "HybridParameters",
    "quantum_regression": "RegressionParameters",
    "quantum_kernel": "LSSVMFit",
}


def test_a_hybrid_artifact_does_not_load_back_as_vqc_parameters(tmp_path):
    """The silent-nonsense case hybrid.py warns about, at the storage layer."""
    from app.quantum.qml_lab.persistence import load_model, save_model
    from app.quantum.qml_lab.vqc import Parameters

    config, _dataset, outcome = _run("hybrid_qnn")
    save_model(tmp_path, 2, config, outcome.artifact)
    loaded = load_model(tmp_path, 2)
    assert not isinstance(loaded.params, Parameters)
    assert loaded.params.n_hidden == config.circuit.n_hidden


def test_the_regression_target_scaler_survives_the_round_trip(tmp_path):
    """Inference must reload the train-fitted scaler, never refit it."""
    from app.quantum.qml_lab.persistence import load_model, save_model

    config, dataset, outcome = _run("quantum_regression")
    save_model(tmp_path, 3, config, outcome.artifact)
    loaded = load_model(tmp_path, 3)

    assert loaded.target_scaler is not None
    assert loaded.target_scaler.y_min == pytest.approx(dataset.target_scaler.y_min)
    assert loaded.target_scaler.y_max == pytest.approx(dataset.target_scaler.y_max)
    assert loaded.target_scaler.fitted is True


def test_the_kernel_artifact_carries_its_training_set(tmp_path):
    """An LSSVM has no weight vector; the support set *is* part of the model."""
    from app.quantum.qml_lab.persistence import load_model, save_model

    config, dataset, outcome = _run("quantum_kernel")
    save_model(tmp_path, 4, config, outcome.artifact)
    loaded = load_model(tmp_path, 4)

    assert loaded.support_x is not None
    assert loaded.support_x.shape == dataset.x_train.shape
    assert loaded.params.alpha.size == dataset.x_train.shape[0]


def test_a_pre_dispatch_artifact_without_a_kind_still_loads(tmp_path):
    """Artifacts written before this phase have no ``artifact_kind`` key."""
    import json

    from app.quantum.qml_lab.persistence import load_model, save_model
    from app.quantum.qml_lab.vqc import Parameters

    config, _dataset, outcome = _run("vqc")
    save_model(tmp_path, 5, config, outcome.artifact)

    config_path = tmp_path / "5" / "config.json"
    payload = json.loads(config_path.read_text())
    del payload["artifact_kind"]
    config_path.write_text(json.dumps(payload))

    assert isinstance(load_model(tmp_path, 5).params, Parameters)


def test_the_trainer_returns_the_parameter_type_it_was_given():
    """Regression guard for a latent Phase 5 defect.

    ``trainer.train`` rebuilt its result as ``vqc.Parameters`` regardless of
    the type passed in. The hybrid *trained* correctly -- the trainer is
    duck-typed on ``decision_values`` -- but handed back a type whose
    ``circuit_weights`` reads ``theta[:-1]`` and reshapes a hybrid vector's
    classical block into silent nonsense. ``hybrid.py`` calls that mistake
    "impossible rather than merely documented"; the trainer was undoing it.

    Phase 5's tests missed it because they only compared ``params.theta``
    numerically, which is identical either way.
    """
    from app.quantum.qml_lab import trainer
    from app.quantum.qml_lab.hybrid import HybridParameters

    config = _config_for("hybrid_qnn")
    rng = np.random.default_rng(0)
    dataset = algorithms.build_dataset_for_config(config, rng)
    model = algorithms.build_model(config, dataset.n_features)
    initial = model.initialise(rng)

    outcome = trainer.train(model, dataset, config.training, rng, initial)

    assert isinstance(outcome.params, HybridParameters), (
        f"trainer returned {type(outcome.params).__name__}, losing the hybrid's "
        f"classical/quantum split"
    )
    assert outcome.params.n_hidden == initial.n_hidden
    assert outcome.params.n_features == initial.n_features
    # and the classical block must still read back as the classical block
    assert outcome.params.classical_weights.shape == (
        initial.n_features,
        initial.n_hidden,
    )
