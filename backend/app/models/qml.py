"""ORM models for the Quantum ML Lab.

Two tables, per the shape settled in §2A.1 of the vision document:

``qml_experiments``
    The document. Config and final result are JSON blobs because they are
    write-once/read-many, which is exactly how ``SimulationJob`` treats
    ``circuit_ir``, ``noise`` and ``result``.

``qml_epoch_metrics``
    The time series. Append-only rows rather than a growing JSON column,
    because SQLAlchemy does not detect in-place mutation of a JSON value:
    appending to a list and committing persists nothing unless the attribute
    is reassigned or flagged, and the symptom -- a progress bar that never
    moves -- reads like a frontend bug. Rows also make polling incremental
    (``WHERE epoch > :seen``) and let ``UniqueConstraint(experiment_id,
    epoch)`` absorb a redelivered task, which matters because
    ``celery_app.py`` sets ``task_acks_late=True`` and Celery is therefore
    at-least-once.
"""

from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base, JSONType

#: The experiment state machine. ``timed_out`` is deliberately distinct from
#: ``failed``: exhausting a wall-clock budget is a resource outcome the user
#: can act on by shrinking the config, whereas ``failed`` means the engine
#: broke. Collapsing them would throw away the one piece of advice worth
#: giving. ``cancelled`` is a user action and not an error at all.
QUEUED = "queued"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"
CANCELLED = "cancelled"
TIMED_OUT = "timed_out"

#: Nothing further will happen to an experiment in one of these states.
TERMINAL_STATUSES = frozenset({COMPLETED, FAILED, CANCELLED, TIMED_OUT})
#: Occupies the single worker slot: counted by the concurrency guard.
ACTIVE_STATUSES = frozenset({QUEUED, RUNNING})
#: Stopped early but not broken -- partial history is meaningful.
INTERRUPTED_STATUSES = frozenset({CANCELLED, TIMED_OUT})

ALL_STATUSES = ACTIVE_STATUSES | TERMINAL_STATUSES


class QmlExperiment(Base):
    """One QML training run, mirroring ``SimulationJob``'s conventions."""

    __tablename__ = "qml_experiments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String(32), nullable=False, default=QUEUED, index=True)

    #: Canonical SHA-256 of the config, for the duplicate-submission guard.
    #: Same mechanism as ``SimulationJob.run_hash`` (models/job.py:22) and the
    #: cache lookup at api/jobs.py:154-170 -- not a new idempotency system.
    run_hash = Column(String(64), nullable=False, default="", index=True)

    config = Column(JSONType, nullable=False)
    result = Column(JSONType, nullable=True)
    error = Column(Text, nullable=True)

    celery_task_id = Column(String(128), nullable=True)

    #: Cooperative cancellation. Its own column so the API's cancel is a
    #: single-column UPDATE and the worker's per-batch poll is a
    #: single-column read -- neither has to touch the JSON blobs.
    cancel_requested = Column(Boolean, nullable=False, default=False, server_default="0")

    #: Filesystem path of the saved model (JSON + .npz). Built only from
    #: ``qml_artifact_dir`` and the integer primary key, never from
    #: user-supplied text.
    model_path = Column(String(512), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    epochs = relationship(
        "QmlEpochMetric",
        back_populates="experiment",
        cascade="all, delete-orphan",
        order_by="QmlEpochMetric.epoch",
    )

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<QmlExperiment id={self.id} status={self.status!r}>"


class QmlEpochMetric(Base):
    """One epoch of one experiment's training history."""

    __tablename__ = "qml_epoch_metrics"
    __table_args__ = (
        # Redelivery safety. task_acks_late=True means a task that dies after
        # writing epoch 7 can be redelivered and write epoch 7 again; the
        # constraint turns that into a detectable conflict the worker skips
        # instead of a silently duplicated chart point.
        UniqueConstraint("experiment_id", "epoch", name="uq_qml_epoch_metrics_experiment_epoch"),
    )

    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(
        Integer,
        ForeignKey("qml_experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    epoch = Column(Integer, nullable=False)
    train_loss = Column(Float, nullable=False)
    train_accuracy = Column(Float, nullable=False)

    #: Named for the held-out split the engine actually evaluates
    #: (``Dataset.x_test``), rather than "val", so the column and
    #: ``EpochRecord`` cannot drift apart. Phase 1 has no third split.
    test_loss = Column(Float, nullable=True)
    test_accuracy = Column(Float, nullable=True)

    elapsed_seconds = Column(Float, nullable=False, default=0.0)

    experiment = relationship("QmlExperiment", back_populates="epochs")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<QmlEpochMetric exp={self.experiment_id} epoch={self.epoch}>"
