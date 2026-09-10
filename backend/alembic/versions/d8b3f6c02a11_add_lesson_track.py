"""Add lessons.track

Splits the Learn section into a theory track and a hands-on circuit track.
Existing rows default to "theory"; the value is re-derived from each markdown
file's ``<!-- track: ... -->`` marker on the next content ingestion.

Revision ID: d8b3f6c02a11
Revises: c7a2e4d19b30
Create Date: 2026-09-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8b3f6c02a11"
down_revision: Union[str, None] = "c7a2e4d19b30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    if not _has_column("lessons", "track"):
        op.add_column(
            "lessons",
            sa.Column(
                "track", sa.String(length=20), nullable=False, server_default="theory"
            ),
        )


def downgrade() -> None:
    if _has_column("lessons", "track"):
        op.drop_column("lessons", "track")
