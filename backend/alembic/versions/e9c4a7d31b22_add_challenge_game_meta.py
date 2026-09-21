"""Add coding_challenges.game_meta

A Quantum Games level is an ordinary CodingChallenge with this column
populated, so the games reuse the existing attempt, job and grading pipeline
rather than introducing a parallel schema that would drift out of sync.

Revision ID: e9c4a7d31b22
Revises: d8b3f6c02a11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e9c4a7d31b22"
down_revision: Union[str, None] = "d8b3f6c02a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    # JSONB on Postgres, plain JSON on SQLite (used by the test suite).
    json_type = (
        sa.dialects.postgresql.JSONB()
        if bind.dialect.name == "postgresql"
        else sa.JSON()
    )
    op.add_column(
        "coding_challenges",
        sa.Column("game_meta", json_type, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("coding_challenges", "game_meta")
