"""Add the curriculum hierarchy and attach existing lessons to it

Introduces the section -> topic -> lesson structure required by roadmap
section 3.0, and migrates the thirteen existing lessons and all existing
mastery rows onto it.

Design notes that matter for anyone reading this later:

* Every change is additive. No column is dropped, no row is deleted, and no
  stored score is recomputed. ``lessons.order_index`` and ``user_mastery.tag``
  keep their values so that anything not yet migrated keeps working.

* ``lessons.topic_slug`` is nullable. A lesson the curriculum does not claim
  remains a valid lesson; it is simply outside the hierarchy. This is what
  lets content land in the repo before the curriculum assigns it a home.

* ``user_mastery.topic_slug`` is backfilled only where the legacy tag maps
  unambiguously onto a topic (see ``curriculum.LEGACY_TAG_TO_TOPIC``). Rows
  whose tag has no mapping are left NULL rather than guessed at or dropped --
  they remain readable as prior progress. Nothing here fabricates mastery.

Revision ID: f1a2b3c4d5e6
Revises: e9c4a7d31b22
Create Date: 2026-10-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.curriculum import (
    LEGACY_TAG_TO_TOPIC,
    SECTIONS,
    TOPICS,
    all_prerequisites,
)

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e9c4a7d31b22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return table in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    # -- new tables ------------------------------------------------------- #
    if not _has_table("curriculum_sections"):
        op.create_table(
            "curriculum_sections",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=80), unique=True),
            sa.Column("title", sa.String(length=200)),
            sa.Column("position", sa.Integer(), default=0),
            sa.Column("summary", sa.Text(), default=""),
        )

    if not _has_table("curriculum_topics"):
        op.create_table(
            "curriculum_topics",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=80), unique=True),
            sa.Column("title", sa.String(length=200)),
            sa.Column("section_slug", sa.String(length=80), index=True),
            sa.Column("position", sa.Integer(), default=0),
            sa.Column("difficulty", sa.String(length=20), default="beginner"),
            sa.Column("summary", sa.Text(), default=""),
            sa.Column("learning_objectives", sa.Text(), default="[]"),
            sa.ForeignKeyConstraint(["section_slug"], ["curriculum_sections.slug"]),
        )

    if not _has_table("topic_prerequisites"):
        op.create_table(
            "topic_prerequisites",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("topic_slug", sa.String(length=80), index=True),
            sa.Column("prerequisite_slug", sa.String(length=80), index=True),
            sa.Column("kind", sa.String(length=20), default="required"),
            sa.ForeignKeyConstraint(["topic_slug"], ["curriculum_topics.slug"]),
            sa.ForeignKeyConstraint(["prerequisite_slug"], ["curriculum_topics.slug"]),
        )

    # -- new columns ------------------------------------------------------ #
    if not _has_column("lessons", "topic_slug"):
        op.add_column("lessons", sa.Column("topic_slug", sa.String(length=80), nullable=True))
    if not _has_column("lessons", "position"):
        op.add_column("lessons", sa.Column("position", sa.Integer(), nullable=True))
    if not _has_column("lessons", "difficulty"):
        op.add_column("lessons", sa.Column("difficulty", sa.String(length=20), nullable=True))
    if not _has_column("lessons", "learning_objectives"):
        op.add_column("lessons", sa.Column("learning_objectives", sa.Text(), nullable=True))
    if not _has_column("user_mastery", "topic_slug"):
        op.add_column("user_mastery", sa.Column("topic_slug", sa.String(length=80), nullable=True))

    # -- seed sections ---------------------------------------------------- #
    # Idempotent: keyed on slug, so a re-run updates rather than duplicates.
    for section in SECTIONS:
        bind.execute(
            sa.text(
                """
                INSERT INTO curriculum_sections (slug, title, position, summary)
                VALUES (:slug, :title, :position, '')
                ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title,
                                                position = EXCLUDED.position
                """
            ),
            dict(section),
        )

    # -- seed topics ------------------------------------------------------ #
    import json

    for topic in TOPICS:
        bind.execute(
            sa.text(
                """
                INSERT INTO curriculum_topics
                    (slug, title, section_slug, position, difficulty, summary,
                     learning_objectives)
                VALUES (:slug, :title, :section, :position, :difficulty, :summary,
                        :objectives)
                ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title,
                                                section_slug = EXCLUDED.section_slug,
                                                position = EXCLUDED.position,
                                                difficulty = EXCLUDED.difficulty,
                                                summary = EXCLUDED.summary,
                                                learning_objectives = EXCLUDED.learning_objectives
                """
            ),
            {
                "slug": topic["slug"],
                "title": topic["title"],
                "section": topic["section"],
                "position": topic["position"],
                "difficulty": topic["difficulty"],
                "summary": topic["summary"],
                "objectives": json.dumps(topic["objectives"]),
            },
        )

    # -- seed prerequisite edges ------------------------------------------ #
    bind.execute(sa.text("DELETE FROM topic_prerequisites"))
    for topic_slug, prereq_slug, kind in all_prerequisites():
        bind.execute(
            sa.text(
                """
                INSERT INTO topic_prerequisites (topic_slug, prerequisite_slug, kind)
                VALUES (:topic, :prereq, :kind)
                """
            ),
            {"topic": topic_slug, "prereq": prereq_slug, "kind": kind},
        )

    # -- attach existing lessons ------------------------------------------ #
    # Position is the index within the topic's lesson list, so it reflects
    # conceptual order rather than the filename number.
    for topic in TOPICS:
        for index, lesson_slug in enumerate(topic["lessons"]):
            bind.execute(
                sa.text(
                    """
                    UPDATE lessons
                       SET topic_slug = :topic,
                           position = :position,
                           difficulty = :difficulty,
                           learning_objectives = COALESCE(learning_objectives, '[]')
                     WHERE slug = :lesson
                    """
                ),
                {
                    "topic": topic["slug"],
                    "position": index,
                    "difficulty": topic["difficulty"],
                    "lesson": lesson_slug,
                },
            )

    # -- migrate mastery rows onto stable topic identifiers --------------- #
    # Only rows whose tag has an unambiguous mapping are stamped. Each UPDATE
    # sets topic_slug and nothing else: score, attempts and updated_at are
    # left exactly as they were, so no learner's history is rewritten.
    for tag, topic_slug in LEGACY_TAG_TO_TOPIC.items():
        bind.execute(
            sa.text(
                "UPDATE user_mastery SET topic_slug = :topic WHERE tag = :tag"
            ),
            {"topic": topic_slug, "tag": tag},
        )


def downgrade() -> None:
    # Reverse order: drop the columns first, then the tables.
    for table, column in (
        ("user_mastery", "topic_slug"),
        ("lessons", "learning_objectives"),
        ("lessons", "difficulty"),
        ("lessons", "position"),
        ("lessons", "topic_slug"),
    ):
        if _has_column(table, column):
            with op.batch_alter_table(table) as batch:
                batch.drop_column(column)

    for table in ("topic_prerequisites", "curriculum_topics", "curriculum_sections"):
        if _has_table(table):
            op.drop_table(table)
