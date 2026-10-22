"""Dispatch through the real database and worker path, not just the engine.

§2D.2 requires a round trip: run a regression experiment through the actual
persistence path and assert the stored epoch row has `train_accuracy` **NULL,
not 0.0**. Relaxing that column's NOT NULL was a real loss of a safety
property, and this is what replaces it.
"""

from __future__ import annotations

import json

import pytest

from app.database import SessionLocal
from app.models.qml import QmlEpochMetric, QmlExperiment
from app.services import qml_lab as service


def _config(algorithm: str, dataset: str, **circuit):
    base = {"n_qubits": 4, "n_layers": 2, "rotation": "Y", "entanglement": "ring"}
    base.update(circuit)
    return {
        "seed": 7,
        "algorithm": algorithm,
        "dataset": {"name": dataset, "n_samples": 40, "noise": 0.05, "test_fraction": 0.3},
        "circuit": base,
        "training": {
            "epochs": 1 if algorithm == "quantum_kernel" else 2,
            "batch_size": 16,
            "learning_rate": 0.1,
            "diff_method": "backprop",
        },
    }


def _queue(db, config: dict, tag: str) -> int:
    from app.models.user import User

    user_id = db.query(User.id).first()[0]
    row = QmlExperiment(user_id=user_id, status="queued", config=config, run_hash=tag)
    db.add(row)
    db.commit()
    return row.id


@pytest.fixture
def artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "artifact_root", lambda: tmp_path)
    return tmp_path


@pytest.mark.parametrize(
    "algorithm,dataset,extra",
    [
        ("vqc", "moons", {}),
        ("hybrid_qnn", "moons", {"n_hidden": 2}),
        ("quantum_regression", "sine", {}),
        ("quantum_kernel", "moons", {}),
    ],
)
def test_each_algorithm_reaches_a_terminal_status_through_the_service(
    client, artifacts, algorithm, dataset, extra
):
    """§2D.3's gate: a real run, through the real path, to a terminal state."""
    db = SessionLocal()
    try:
        experiment_id = _queue(db, _config(algorithm, dataset, **extra), f"disp-{algorithm}")
    finally:
        db.close()

    db = SessionLocal()
    try:
        outcome = service.execute_experiment(db, experiment_id)
    finally:
        db.close()
    assert outcome["status"] == "completed", outcome

    db = SessionLocal()
    try:
        row = db.get(QmlExperiment, experiment_id)
        assert row.status == "completed"
        assert row.result["algorithm"] == algorithm
        assert row.result["task"] == ("regression" if algorithm == "quantum_regression" else "classification")
        assert row.model_path is not None
    finally:
        db.close()


def test_a_regression_epoch_row_stores_null_accuracy_not_zero(client, artifacts):
    """The safety property that replaces the dropped NOT NULL constraint.

    0.0 would render as "scored zero" on any chart that reads the column, and
    would be indistinguishable from a genuinely terrible classifier.
    """
    db = SessionLocal()
    try:
        experiment_id = _queue(db, _config("quantum_regression", "sine"), "disp-reg-null")
    finally:
        db.close()

    _execute(experiment_id)

    db = SessionLocal()
    try:
        rows = (
            db.query(QmlEpochMetric)
            .filter(QmlEpochMetric.experiment_id == experiment_id)
            .order_by(QmlEpochMetric.epoch)
            .all()
        )
        assert rows, "regression run recorded no epochs"
        for row in rows:
            assert row.train_accuracy is None, (
                f"epoch {row.epoch} stored train_accuracy={row.train_accuracy!r}; "
                f"NULL is required, 0.0 is a lie"
            )
            assert row.test_accuracy is None
            assert row.train_r2 is not None, "regression epoch must record R2"
            assert row.train_loss is not None
    finally:
        db.close()


def test_a_classification_epoch_row_still_stores_accuracy(client, artifacts):
    """Relaxing the constraint must not let a classifier silently skip it."""
    db = SessionLocal()
    try:
        experiment_id = _queue(db, _config("vqc", "moons"), "disp-cls-acc")
    finally:
        db.close()

    _execute(experiment_id)

    db = SessionLocal()
    try:
        rows = db.query(QmlEpochMetric).filter(
            QmlEpochMetric.experiment_id == experiment_id
        ).all()
        assert rows
        for row in rows:
            assert row.train_accuracy is not None
            assert row.train_r2 is None, "a classification epoch has no R2"
    finally:
        db.close()


def test_the_persisted_regression_result_contains_no_accuracy_key_anywhere(client, artifacts):
    db = SessionLocal()
    try:
        experiment_id = _queue(db, _config("quantum_regression", "sine"), "disp-reg-json")
    finally:
        db.close()

    _execute(experiment_id)

    db = SessionLocal()
    try:
        blob = json.dumps(db.get(QmlExperiment, experiment_id).result)
    finally:
        db.close()

    for banned in ("accuracy", "precision", "recall", "confusion_matrix"):
        assert banned not in blob, f"persisted regression result leaked {banned!r}"


def test_the_kernel_persists_zero_epoch_rows(client, artifacts):
    db = SessionLocal()
    try:
        experiment_id = _queue(db, _config("quantum_kernel", "moons"), "disp-kernel-epochs")
    finally:
        db.close()

    _execute(experiment_id)

    db = SessionLocal()
    try:
        count = (
            db.query(QmlEpochMetric)
            .filter(QmlEpochMetric.experiment_id == experiment_id)
            .count()
        )
    finally:
        db.close()

    assert count == 0, f"kernel wrote {count} synthetic epoch row(s)"


# ---------------------------------------------------------------------------
# Inference: one contract, no zeroed field for a task that lacks it
# ---------------------------------------------------------------------------


def _execute(experiment_id: int):
    db = SessionLocal()
    try:
        return service.execute_experiment(db, experiment_id)
    finally:
        db.close()


def _infer(experiment_id: int, features):
    db = SessionLocal()
    try:
        return service.run_inference(db.get(QmlExperiment, experiment_id), features)
    finally:
        db.close()


def _run_then_infer(client, config: dict, tag: str, features):
    db = SessionLocal()
    try:
        experiment_id = _queue(db, config, tag)
    finally:
        db.close()
    _execute(experiment_id)
    return _infer(experiment_id, features)


def test_regression_inference_returns_values_in_user_units_not_probabilities(
    client, artifacts
):
    payload = _run_then_infer(
        client, _config("quantum_regression", "sine"), "inf-reg", [[0.5], [-1.0]]
    )
    assert payload["task"] == "regression"
    assert "values" in payload and len(payload["values"]) == 2
    assert "probabilities" not in payload, "a regression prediction is not a probability"
    assert "predictions" not in payload, "no zeroed classification field"
    low, high = payload["target_range"]
    assert low < high


def test_classification_inference_still_returns_probabilities(client, artifacts):
    payload = _run_then_infer(client, _config("vqc", "moons"), "inf-vqc", [[0.1, 0.2]])
    assert payload["task"] == "classification"
    assert "probabilities" in payload and "predictions" in payload
    assert "values" not in payload


def test_kernel_inference_reports_a_margin_not_a_probability(client, artifacts):
    payload = _run_then_infer(client, _config("quantum_kernel", "moons"), "inf-kern", [[0.1, 0.2]])
    assert payload["task"] == "classification"
    assert "decision_values" in payload, "an LSSVM margin must not be called a probability"
    assert "probabilities" not in payload
    assert set(payload["predictions"]) <= {0, 1}


def test_regression_inference_reuses_the_stored_scaler_rather_than_refitting(
    client, artifacts
):
    """Refitting on whatever rows inference sees would change every unit."""
    config = _config("quantum_regression", "sine")
    db = SessionLocal()
    try:
        experiment_id = _queue(db, config, "inf-reg-scaler")
    finally:
        db.close()
    _execute(experiment_id)

    one = _infer(experiment_id, [[0.5]])
    many = _infer(experiment_id, [[0.5], [0.9], [-2.0], [2.0]])

    assert one["values"][0] == pytest.approx(many["values"][0], abs=1e-12)
    assert one["target_range"] == many["target_range"]

