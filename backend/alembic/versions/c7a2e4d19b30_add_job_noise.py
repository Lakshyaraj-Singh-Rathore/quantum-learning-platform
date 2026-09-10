"""Add simulation_jobs.noise

Stores the T1/T2/readout parameters a run was submitted with, so a noisy
result can be reproduced and audited. Nullable: existing rows were all
noiseless runs.

Revision ID: c7a2e4d19b30
Revises: b5f10b499a50
Create Date: 2026-09-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7a2e4d19b30"
down_revision: Union[str, None] = "b5f10b499a50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    """JSONB on Postgres, plain JSON elsewhere (SQLite in tests)."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("simulation_jobs", "noise"):
        op.add_column(
            "simulation_jobs", sa.Column("noise", _json_type(), nullable=True)
        )


def downgrade() -> None:
    if _has_column("simulation_jobs", "noise"):
        op.drop_column("simulation_jobs", "noise")
