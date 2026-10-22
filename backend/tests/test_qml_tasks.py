"""Worker-side tests: per-task time limits, re-validation, cancellation, timeout.

The headline test here is the time-limit isolation one. The global Celery
limits are 8s soft / 15s hard, and ``app/workers/tasks.py:96`` derives the
qBraid remote-wait budget from the soft one -- so raising the globals to suit
a minutes-long training run would silently change unrelated behaviour. The
QML task therefore carries its own limits on its decorator, and the test
asserts BOTH directions: the QML task got the long ones, and nothing else
did.
"""

from __future__ import annotations

import time

import pytest

from app.config import get_settings
from app.database import SessionLocal
from app.models.qml import (
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    TIMED_OUT,
    QmlEpochMetric,
    QmlExperiment,
)
from app.services import qml_lab as service
from app.workers.celery_app import celery_app
from app.workers.qml_tasks import run_qml_experiment
from app.workers.tasks import run_simulation


def tiny_config(**overrides):
    config = {
        "seed": 7,
        "dataset": {"name": "moons", "n_samples": 40, "noise": 0.1, "test_fraction": 0.3},
        "circuit": {"n_qubits": 2, "n_layers": 1, "rotation": "Y", "entanglement": "ring"},
        "training": {"epochs": 2, "batch_size": 16, "learning_rate": 0.1, "diff_method": "backprop"},
    }
    config.update(overrides)
    return config


@pytest.fixture
def experiment_row(client, tmp_path, monkeypatch):
    """A queued experiment owned by a real user, with artifacts in tmp_path."""
    monkeypatch.setattr(service, "artifact_root", lambda: tmp_path)
    db = SessionLocal()
    try:
        from app.models.user import User

        user_id = db.query(User.id).first()[0]
        row = QmlExperiment(
            user_id=user_id, status="queued", config=tiny_config(), run_hash="worker-test-hash"
        )
        db.add(row)
        db.commit()
        row_id = row.id
    finally:
        db.close()

    yield row_id

    db = SessionLocal()
    try:
        row = db.get(QmlExperiment, row_id)
        if row is not None:
            db.delete(row)
            db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Per-task time-limit isolation -- both directions
# ---------------------------------------------------------------------------


def test_qml_task_carries_its_own_long_limits():
    settings = get_settings()
    assert run_qml_experiment.soft_time_limit == settings.qml_task_soft_time_limit == 900
    assert run_qml_experiment.time_limit == settings.qml_task_hard_time_limit == 1200


def test_global_celery_limits_were_not_raised():
    """The other direction: the QML feature must not have loosened the globals."""
    settings = get_settings()
    assert settings.celery_soft_time_limit == 8
    assert settings.celery_hard_time_limit == 15
    assert celery_app.conf.task_soft_time_limit == 8
    assert celery_app.conf.task_time_limit == 15


def test_run_simulation_still_inherits_the_short_global_limits():
    """run_simulation has no per-task override, so it gets conf's 8/15."""
    assert run_simulation.soft_time_limit is None
    assert run_simulation.time_limit is None
    effective_soft = run_simulation.soft_time_limit or celery_app.conf.task_soft_time_limit
    effective_hard = run_simulation.time_limit or celery_app.conf.task_time_limit
    assert (effective_soft, effective_hard) == (8, 15)


def test_the_two_tasks_have_genuinely_different_budgets():
    qml_soft = run_qml_experiment.soft_time_limit
    sim_soft = run_simulation.soft_time_limit or celery_app.conf.task_soft_time_limit
    assert qml_soft > sim_soft * 100, f"qml={qml_soft}s sim={sim_soft}s -- isolation is the point"


def test_the_qml_task_is_registered_with_the_worker():
    """include=[...] in celery_app.py, so a real worker picks the module up."""
    assert "app.workers.qml_tasks.run_qml_experiment" in celery_app.tasks


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def test_task_runs_an_experiment_to_completion(experiment_row):
    result = run_qml_experiment.apply(args=[experiment_row]).get()
    assert result["status"] == "completed"

    db = SessionLocal()
    try:
        row = db.get(QmlExperiment, experiment_row)
        assert row.status == "completed"
        assert row.status in TERMINAL_STATUSES
        assert row.error is None
        assert row.started_at is not None and row.finished_at is not None
        assert len(row.epochs) == 2
        assert [e.epoch for e in row.epochs] == [1, 2]
        assert row.epochs[0].train_loss > 0
        assert row.result["evaluation"]["accuracy"] >= 0.0
        assert row.model_path is not None
    finally:
        db.close()


def test_worker_rejects_a_stored_row_that_breaks_the_schema(experiment_row):
    """The worker does not trust the JSON blob in the database.

    A row edited out of band (or written by an older, looser version) must be
    re-validated, not fed straight to the engine.
    """
    db = SessionLocal()
    try:
        row = db.get(QmlExperiment, experiment_row)
        row.config = tiny_config(
            circuit={"n_qubits": 64, "n_layers": 1, "rotation": "Y", "entanglement": "ring"}
        )
        db.commit()
    finally:
        db.close()

    result = run_qml_experiment.apply(args=[experiment_row]).get()
    assert result["status"] == "failed"

    db = SessionLocal()
    try:
        row = db.get(QmlExperiment, experiment_row)
        assert row.status == "failed"
        assert row.error.startswith("ValidationError:")
        assert "n_qubits" in row.error
    finally:
        db.close()


def test_worker_reenforces_limits_that_tightened_after_the_row_was_queued(experiment_row, monkeypatch):
    """The scenario limits.enforce actually exists for.

    limits.check() currently mirrors the schema's own field bounds, so a
    config that violates it cannot normally get past Pydantic first -- which
    means a test using an over-large n_qubits proves nothing about
    limits.enforce (it is caught by the schema either way; verified by
    mutation). Tightening the limit at runtime is the one case that separates
    them: the stored config is still schema-valid, but no longer allowed.
    """
    from app.quantum.qml_lab import limits

    monkeypatch.setattr(limits, "MAX_QUBITS", 1)

    result = run_qml_experiment.apply(args=[experiment_row]).get()
    assert result["status"] == "failed"

    db = SessionLocal()
    try:
        row = db.get(QmlExperiment, experiment_row)
        assert row.status == "failed"
        assert row.error.startswith("QmlLimitExceededError:"), row.error
        assert "n_qubits=2 exceeds the limit of 1" in row.error
    finally:
        db.close()


def test_a_missing_row_does_not_raise(client):
    """A deleted experiment must not crash the worker."""
    assert run_qml_experiment.apply(args=[999_999]).get()["status"] == "missing"


# ---------------------------------------------------------------------------
# Cooperative cancellation and the wall-clock deadline
# ---------------------------------------------------------------------------


def test_cancel_flag_stops_the_run_and_records_cancelled(experiment_row):
    db = SessionLocal()
    try:
        db.get(QmlExperiment, experiment_row).cancel_requested = True
        db.commit()
    finally:
        db.close()

    result = run_qml_experiment.apply(args=[experiment_row]).get()
    assert result["status"] == "cancelled"

    db = SessionLocal()
    try:
        row = db.get(QmlExperiment, experiment_row)
        assert row.status == "cancelled"
        assert row.error is None, "a user cancelling is not an error"
        assert row.finished_at is not None
        assert row.model_path is None
    finally:
        db.close()


def test_timeout_is_reported_as_timed_out_not_cancelled_or_failed(experiment_row):
    """The cooperative deadline fires and is diagnosed distinctly.

    timed_out is its own status: it tells the user to shrink the config,
    which is advice neither 'failed' nor 'cancelled' conveys.
    """
    db = SessionLocal()
    try:
        result = service.execute_experiment(db, experiment_row, deadline_seconds=0.0001)
    finally:
        db.close()
    assert result["status"] == TIMED_OUT

    db = SessionLocal()
    try:
        row = db.get(QmlExperiment, experiment_row)
        assert row.status == TIMED_OUT
        assert row.status in TERMINAL_STATUSES and row.status not in ACTIVE_STATUSES
        assert "time budget" in row.error
        assert row.result["interrupted"] is True
        assert row.model_path is None, "a half-trained model must not be saved"
    finally:
        db.close()


def test_the_engine_deadline_sits_strictly_below_the_celery_soft_limit():
    """So the cooperative path always wins.

    If the two were equal, Celery's SIGALRM could arrive first and the user
    would get a SoftTimeLimitExceeded traceback instead of a readable
    timed_out with partial history.
    """
    settings = get_settings()
    deadline = service.training_deadline_seconds()
    assert 0 < deadline < settings.qml_task_soft_time_limit < settings.qml_task_hard_time_limit
    assert settings.qml_task_soft_time_limit - deadline == service.TIMEOUT_MARGIN_SECONDS


def test_cancel_poller_sees_a_flag_set_by_another_session(experiment_row):
    """The identity-map trap: without expiring the attribute, the worker's
    session would keep returning the value it loaded when the task began."""
    worker_db = SessionLocal()
    try:
        poller = service.CancelPoller(worker_db, experiment_row)
        # The strong reference matters: SQLAlchemy's identity map is weak, so
        # a discarded object is collected and the next get() silently
        # re-queries -- which would make this test pass even without the
        # expire. execute_experiment holds `experiment` for the whole run, so
        # the test must hold one too or it proves nothing.
        held = worker_db.get(QmlExperiment, experiment_row)
        assert held is not None
        assert poller() is False

        api_db = SessionLocal()
        try:
            api_db.get(QmlExperiment, experiment_row).cancel_requested = True
            api_db.commit()
        finally:
            api_db.close()

        time.sleep(service.CANCEL_POLL_INTERVAL_SECONDS + 0.05)
        assert held.cancel_requested is False, "precondition: the held copy is stale"
        assert poller() is True, "the worker never observed the API's update"
    finally:
        worker_db.close()


def test_cancel_poller_is_sticky_once_it_fires(experiment_row):
    """The trainer polls every batch; the answer must not flap back."""
    db = SessionLocal()
    try:
        row = db.get(QmlExperiment, experiment_row)
        row.cancel_requested = True
        db.commit()

        poller = service.CancelPoller(db, experiment_row)
        time.sleep(service.CANCEL_POLL_INTERVAL_SECONDS + 0.05)
        assert poller() is True

        row.cancel_requested = False
        db.commit()
        assert poller() is True, "a fired cancel must stay fired"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Redelivery safety -- task_acks_late=True makes Celery at-least-once
# ---------------------------------------------------------------------------


def test_a_redelivered_epoch_does_not_duplicate(experiment_row):
    """UniqueConstraint(experiment_id, epoch) absorbs the replay."""
    from app.quantum.qml_lab.models import EpochRecord

    record = EpochRecord(
        epoch=1,
        train_loss=0.5,
        train_accuracy=0.6,
        test_loss=0.55,
        test_accuracy=0.58,
        elapsed_seconds=1.0,
    )
    db = SessionLocal()
    try:
        assert service.record_epoch(db, experiment_row, record) is True
        assert service.record_epoch(db, experiment_row, record) is False, "replay must be refused"

        rows = db.query(QmlEpochMetric).filter_by(experiment_id=experiment_row).all()
        assert len(rows) == 1, f"epoch duplicated {len(rows)} times"
        assert rows[0].train_loss == 0.5
    finally:
        db.close()


def test_rerunning_a_whole_task_does_not_duplicate_history(experiment_row):
    """The end-to-end version: the entire task redelivered."""
    first = run_qml_experiment.apply(args=[experiment_row]).get()
    assert first["status"] == "completed"

    db = SessionLocal()
    try:
        after_first = db.query(QmlEpochMetric).filter_by(experiment_id=experiment_row).count()
    finally:
        db.close()

    run_qml_experiment.apply(args=[experiment_row]).get()

    db = SessionLocal()
    try:
        after_second = db.query(QmlEpochMetric).filter_by(experiment_id=experiment_row).count()
        assert after_second == after_first == 2, f"{after_first} -> {after_second}"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Queue routing -- the structural half of the concurrency guarantee
# ---------------------------------------------------------------------------


def test_qml_tasks_are_routed_to_their_own_queue():
    route = celery_app.amqp.router.route({}, "app.workers.qml_tasks.run_qml_experiment")
    assert route["queue"].name == "qml"


def test_simulation_tasks_still_use_the_default_queue():
    """The other direction: routing QML away must not move anything else."""
    route = celery_app.amqp.router.route({}, "app.workers.tasks.run_simulation")
    assert route["queue"].name == "celery"
