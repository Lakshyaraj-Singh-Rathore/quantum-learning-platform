"""Add regression metrics to qml_epoch_metrics, and relax train_accuracy.

Revision ID: j5e8f1a4b7c2
Revises: i4d7e0f3a6b9

Why this is needed
------------------
`qml_epoch_metrics` is typed columns, not JSON, and `train_accuracy` was
`nullable=False` with **no default**. A regression epoch has no accuracy, so
with the column as it stood a regression run could only either fail on
insert or store a lie.

Why R2 is NOT stored in train_accuracy
--------------------------------------
That would be the cheap fix and it is wrong. R-squared **can be negative** --
Phase 5 measured `sin(2x)` at R2 = +0.104 while a linear baseline reached
+0.208, and a worse-than-mean model scores below zero. A column every
consumer reads as a `[0, 1]` accuracy would then hold `-0.4`, and a chart
labelled "accuracy" would render `0.328` for a regression run. The D-033 test
guards the Pydantic model, not the column, so it would keep passing while the
stored data was nonsense.

The names match `HISTORY_KEYS_BY_TASK`
--------------------------------------
`describe()` already promises `train_r2` / `test_r2` for the regression task.
Any other column name would make the capability document lie a second time,
which is the exact failure this phase exists to close.

What is given up
----------------
`train_accuracy` being NOT NULL was a real safety property: a classification
epoch that failed to compute accuracy failed loudly instead of silently
storing `0.0`. Relaxing it makes "NULL vs 0.0" a live hazard, so this
migration ships with a round-trip test asserting a persisted regression epoch
has `train_accuracy IS NULL` -- not `0.0` -- and that the result JSON carries
no accuracy key anywhere.

SQLite note: `batch_alter_table` is required because SQLite cannot ALTER a
column's nullability in place; Alembic rebuilds the table instead.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j5e8f1a4b7c2"
down_revision: Union[str, None] = "i4d7e0f3a6b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("qml_epoch_metrics") as batch:
        batch.add_column(sa.Column("train_r2", sa.Float(), nullable=True))
        batch.add_column(sa.Column("test_r2", sa.Float(), nullable=True))
        batch.alter_column("train_accuracy", existing_type=sa.Float(), nullable=True)


def downgrade() -> None:
    # Rows written by a regression run have train_accuracy NULL and cannot
    # satisfy the old NOT NULL constraint, so they are removed rather than
    # backfilled with a fabricated 0.0 -- which is the precise lie this
    # migration exists to prevent.
    op.execute("DELETE FROM qml_epoch_metrics WHERE train_accuracy IS NULL")
    with op.batch_alter_table("qml_epoch_metrics") as batch:
        batch.alter_column("train_accuracy", existing_type=sa.Float(), nullable=False)
        batch.drop_column("test_r2")
        batch.drop_column("train_r2")
