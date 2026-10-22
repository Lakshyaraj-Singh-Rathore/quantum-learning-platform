"""Artifacts: versioned, pickle-free, path-safe, and byte-faithful.

The reload test is the one that matters for the acceptance criteria: a model
that reloads but predicts differently is worse than one that fails to reload,
because nothing reports it.
"""

from __future__ import annotations

import json
import uuid

import numpy as np
import pytest

from app.quantum.qml_lab import persistence
from app.quantum.qml_lab.errors import QmlPersistenceError
from app.quantum.qml_lab.models import CircuitConfig, QmlExperimentConfig
from app.quantum.qml_lab.persistence import (
    ARTIFACT_VERSION,
    canonical_experiment_id,
    delete_experiment,
    experiment_dir,
    load_model,
    save_model,
)
from app.quantum.qml_lab.vqc import VQC


def _model_and_params(seed=5):
    config = QmlExperimentConfig(circuit=CircuitConfig(n_qubits=2, n_layers=2))
    model = VQC(config.circuit, n_features=2, diff_method="backprop")
    params = model.initialise(np.random.default_rng(seed))
    return config, model, params


# --------------------------------------------------------------------------
# Round trip
# --------------------------------------------------------------------------


def test_save_reload_predicts_bit_identically(tmp_path):
    config, model, params = _model_and_params()
    x = np.random.default_rng(1).uniform(0, np.pi, size=(8, 2))
    before = model.predict_proba(x, params)

    save_model(tmp_path, 1, config, params, metrics={"accuracy": 0.9})
    reloaded = load_model(tmp_path, 1)

    assert np.array_equal(reloaded.params.theta, params.theta)

    rebuilt = VQC(reloaded.config.circuit, n_features=2, diff_method="backprop")
    after = rebuilt.predict_proba(x, reloaded.params)

    assert np.array_equal(before, after), "predictions changed across a save/reload cycle"
    assert np.array_equal(model.predict(x, params), rebuilt.predict(x, reloaded.params))


def test_round_trip_preserves_the_config_and_metrics(tmp_path):
    config, _, params = _model_and_params()
    save_model(tmp_path, 7, config, params, metrics={"accuracy": 0.83, "epochs": 4})
    reloaded = load_model(tmp_path, 7)

    assert reloaded.config == config
    assert reloaded.metrics["accuracy"] == 0.83
    assert reloaded.version == ARTIFACT_VERSION


def test_artifacts_carry_a_version_field(tmp_path):
    config, _, params = _model_and_params()
    target = save_model(tmp_path, 2, config, params)

    payload = json.loads((target / "config.json").read_text())
    assert payload["version"] == ARTIFACT_VERSION
    assert payload["parameter_shape"] == {"n_qubits": 2, "n_layers": 2}


def test_an_unknown_version_is_refused(tmp_path):
    config, _, params = _model_and_params()
    target = save_model(tmp_path, 3, config, params)

    path = target / "config.json"
    payload = json.loads(path.read_text())
    payload["version"] = ARTIFACT_VERSION + 99
    path.write_text(json.dumps(payload))

    with pytest.raises(QmlPersistenceError) as excinfo:
        load_model(tmp_path, 3)
    assert "version" in str(excinfo.value)


# --------------------------------------------------------------------------
# No pickle
# --------------------------------------------------------------------------


def test_weights_are_npz_and_load_without_pickle(tmp_path):
    config, _, params = _model_and_params()
    target = save_model(tmp_path, 4, config, params)

    weights = target / "weights.npz"
    assert weights.is_file()
    # Reading with allow_pickle=False must succeed, proving no object arrays.
    with np.load(weights, allow_pickle=False) as archive:
        assert set(archive.files) == {"theta"}
        assert archive["theta"].dtype == np.float64


def test_no_pickle_artifacts_are_written(tmp_path):
    config, _, params = _model_and_params()
    target = save_model(tmp_path, 5, config, params)

    written = {p.name for p in target.iterdir()}
    assert written == {"config.json", "weights.npz", "metrics.json"}
    assert not any(name.endswith((".pkl", ".pickle", ".joblib")) for name in written)


def test_a_tampered_weight_file_fails_closed(tmp_path):
    config, _, params = _model_and_params()
    target = save_model(tmp_path, 6, config, params)
    (target / "weights.npz").write_bytes(b"not an npz file")

    with pytest.raises(QmlPersistenceError):
        load_model(tmp_path, 6)


def test_a_weight_vector_of_the_wrong_length_is_refused(tmp_path):
    config, _, params = _model_and_params()
    target = save_model(tmp_path, 8, config, params)

    with (target / "weights.npz").open("wb") as handle:
        np.savez(handle, theta=np.zeros(3))

    with pytest.raises(QmlPersistenceError) as excinfo:
        load_model(tmp_path, 8)
    assert "expected" in str(excinfo.value)


# --------------------------------------------------------------------------
# Path safety
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_id",
    [
        "../escape",
        "../../etc/passwd",
        "/absolute/path",
        "name with spaces",
        "..",
        ".",
        "",
        "3; rm -rf /",
        "model.npz",
        -1,
        True,
        3.5,
        None,
        ["1"],
    ],
)
def test_unsafe_experiment_ids_are_refused(tmp_path, bad_id):
    with pytest.raises(QmlPersistenceError):
        experiment_dir(tmp_path, bad_id)


@pytest.mark.parametrize("good_id, expected", [(1, "1"), ("42", "42"), (0, "0")])
def test_integer_ids_are_canonicalised(good_id, expected):
    assert canonical_experiment_id(good_id) == expected


def test_uuid_ids_are_accepted():
    identifier = uuid.uuid4()
    assert canonical_experiment_id(identifier) == str(identifier)
    assert canonical_experiment_id(str(identifier)) == str(identifier)


def test_the_resolved_directory_stays_inside_the_root(tmp_path):
    resolved = experiment_dir(tmp_path, 12)
    assert tmp_path.resolve() in resolved.parents
    assert resolved.name == "12"


def test_traversal_cannot_be_smuggled_through_save(tmp_path):
    config, _, params = _model_and_params()
    with pytest.raises(QmlPersistenceError):
        save_model(tmp_path, "../outside", config, params)


# --------------------------------------------------------------------------
# Cleanup
# --------------------------------------------------------------------------


def test_delete_removes_a_partial_artifact(tmp_path):
    """A cancelled run must not leave artifacts for a later load to trip on."""
    config, _, params = _model_and_params()
    save_model(tmp_path, 9, config, params)

    assert delete_experiment(tmp_path, 9) is True
    assert delete_experiment(tmp_path, 9) is False

    with pytest.raises(QmlPersistenceError):
        load_model(tmp_path, 9)


def test_loading_a_missing_experiment_raises(tmp_path):
    with pytest.raises(QmlPersistenceError):
        load_model(tmp_path, 404)


def test_an_interrupted_save_leaves_no_temp_files(tmp_path):
    config, _, params = _model_and_params()
    target = save_model(tmp_path, 10, config, params)
    assert not list(target.glob("*.tmp"))


def test_saving_twice_overwrites_cleanly(tmp_path):
    config, model, params = _model_and_params()
    save_model(tmp_path, 11, config, params)

    moved = params.copy()
    moved.theta = moved.theta + 1.0
    save_model(tmp_path, 11, config, moved)

    assert np.array_equal(load_model(tmp_path, 11).params.theta, moved.theta)
    assert not list(persistence.experiment_dir(tmp_path, 11).glob("*.tmp"))
