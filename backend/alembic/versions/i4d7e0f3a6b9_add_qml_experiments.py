"""Add qml_experiments and qml_epoch_metrics for the Quantum ML Lab.

Purely additive: two new tables, no existing table altered, dropped or
renamed. The feature that reads them is behind ``qml_enabled``, which is off
by default, so applying this migration changes nothing observable until the
flag is turned on.

``downgrade`` drops both tables and nothing else, which is exact because
neither existed before this revision. It has been run, not merely written --
see docs/qml/phase-2-report.md for the pasted output of
``upgrade head`` -> ``downgrade -1`` -> ``upgrade head``.

Shape notes (§2A.1):

``qml_experiments``
    The document: config and result are JSON blobs, following
    ``simulation_jobs``.

``qml_epoch_metrics``
    The time series: append-only rows, so publishing an epoch is an INSERT
    rather than a read-modify-write of a growing JSON column that SQLAlchemy
    would not notice had changed. ``uq_qml_epoch_metrics_experiment_epoch``
    makes a redelivered task (``task_acks_late=True``) harmless.

Revision ID: i4d7e0f3a6b9
Revises: h3c6d9e2f5a8
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.database import JSONType

revision: str = "i4d7e0f3a6b9"
down_revision: Union[str, None] = "h3c6d9e2f5a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "qml_experiments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("run_hash", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("config", JSONType, nullable=False),
        sa.Column("result", JSONType, nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=128), nullable=True),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("model_path", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_qml_experiments_id", "qml_experiments", ["id"])
    op.create_index("ix_qml_experiments_user_id", "qml_experiments", ["user_id"])
    op.create_index("ix_qml_experiments_status", "qml_experiments", ["status"])
    op.create_index("ix_qml_experiments_run_hash", "qml_experiments", ["run_hash"])

    op.create_table(
        "qml_epoch_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "experiment_id",
            sa.Integer(),
            sa.ForeignKey("qml_experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("train_loss", sa.Float(), nullable=False),
        sa.Column("train_accuracy", sa.Float(), nullable=False),
        sa.Column("test_loss", sa.Float(), nullable=True),
        sa.Column("test_accuracy", sa.Float(), nullable=True),
        sa.Column("elapsed_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.UniqueConstraint(
            "experiment_id", "epoch", name="uq_qml_epoch_metrics_experiment_epoch"
        ),
    )
    op.create_index("ix_qml_epoch_metrics_id", "qml_epoch_metrics", ["id"])
    op.create_index("ix_qml_epoch_metrics_experiment_id", "qml_epoch_metrics", ["experiment_id"])


def downgrade() -> None:
    # Child first: qml_epoch_metrics holds the foreign key.
    op.drop_index("ix_qml_epoch_metrics_experiment_id", table_name="qml_epoch_metrics")
    op.drop_index("ix_qml_epoch_metrics_id", table_name="qml_epoch_metrics")
    op.drop_table("qml_epoch_metrics")

    op.drop_index("ix_qml_experiments_run_hash", table_name="qml_experiments")
    op.drop_index("ix_qml_experiments_status", table_name="qml_experiments")
    op.drop_index("ix_qml_experiments_user_id", table_name="qml_experiments")
    op.drop_index("ix_qml_experiments_id", table_name="qml_experiments")
    op.drop_table("qml_experiments")
