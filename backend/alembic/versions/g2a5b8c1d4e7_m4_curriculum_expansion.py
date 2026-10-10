"""M4 curriculum expansion: 54 approved topics, prerequisites and rationales

Adds the topic architecture approved at ``c8f7144`` (Gate 1) to the database:
54 new topics, their lesson associations, their prerequisite edges, and a
``rationale`` column so every edge records why it exists.

Why a new revision rather than a registry edit
----------------------------------------------
``app/curriculum.py`` is read by migrations, tests and scripts. Nothing syncs
it into the database at runtime, so adding topics to the registry changes
nothing for a running service until a migration inserts the rows. This is that
migration.

What is added
-------------
``topic_prerequisites.rationale``
    A prerequisite edge was previously just ``(topic, prereq, kind)``. The
    approved architecture justifies every edge, and a reviewer cannot accept
    or reject an unjustified dependency. Existing rows keep an empty string
    rather than a fabricated reason.

54 topics
    Inserted with ``status = 'draft'``. Draft topics are registered but hidden
    from learner navigation, so a topic can be authored against without
    putting an unopenable module in the UI. Each is published individually by
    a later revision once its lesson exists and validates.

Prerequisite edges and lesson associations
    Upserted from the registry, so the migration is idempotent.

Data safety
-----------
Purely additive on upgrade. No existing row is modified except that
prerequisite rows gain a rationale (previously absent, never populated) and
are otherwise left as they were. No table is dropped, no column removed, no
identifier renamed. The 17 pre-existing topic ids are untouched: they are
upserted to the same values they already hold.

On downgrade the 54 topics are removed again. If any learner has earned
mastery against one of them, the downgrade refuses rather than deleting
learner data: it raises with the count so the operator can decide.

Dialects
--------
Upserts use ``ON CONFLICT`` throughout. The SQLite-only upsert variant is
avoided deliberately: it fails outright on PostgreSQL, which is the
production dialect. Parameters used in both a typeless SELECT list and a
WHERE comparison against a varchar column are explicitly CAST, because
PostgreSQL otherwise raises AmbiguousParameter.

Revision ID: g2a5b8c1d4e7
Revises: a2b3c4d5e6f7
Create Date: 2026-10-10
"""

from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import bindparam

from app.curriculum import (
    NAMESPACES,
    TOPICS,
    all_lesson_topics,
    all_prerequisites_with_rationale,
)

revision: str = "g2a5b8c1d4e7"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


#: The 17 topics that existed before this revision. Everything else in the
#: registry was added by M4 and is therefore removable on downgrade. Recorded
#: explicitly so the downgrade never has to guess which rows it created.
PRE_M4_TOPIC_IDS = frozenset(
    {
        "core.measurement_theory",
        "core.quantum_interference",
        "core.quantum_channels",
        "qc.qubits",
        "qc.superposition",
        "qc.basic_gates",
        "qc.bell_states",
        "qc.entanglement",
        "qiskit.sampler",
        "qiskit.quantum_noise",
        "algo.deutsch_jozsa",
        "algo.grover",
        "adv.dynamic_circuits",
        "adv.quantum_universality",
        "nisq.vqe",
        "nisq.qaoa",
        "nisq.parameterized_circuits",
    }
)


def _m4_topic_ids() -> list[str]:
    """Topics this revision adds: everything in the registry that is not pre-M4."""
    return sorted(str(t["id"]) for t in TOPICS if str(t["id"]) not in PRE_M4_TOPIC_IDS)


def _has_table(table: str) -> bool:
    return table in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def _section_for(namespace: str) -> str:
    return NAMESPACES[namespace][0]


def upgrade() -> None:
    bind = op.get_bind()

    # -- prerequisite edges gain a rationale -------------------------------- #
    # server_default backfills existing rows with '' so the column can be
    # NOT NULL without inventing a reason for an edge that never had one.
    if _has_table("topic_prerequisites") and not _has_column(
        "topic_prerequisites", "rationale"
    ):
        op.add_column(
            "topic_prerequisites",
            sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        )

    # -- topics ------------------------------------------------------------- #
    # Upserted from the registry, matching the convention in a2b3c4d5e6f7: the
    # registry is authoritative and this statement is idempotent.
    for topic in TOPICS:
        bind.execute(
            sa.text(
                """
                INSERT INTO curriculum_topics
                    (id, title, namespace, module, section_slug, position,
                     difficulty, description, learning_objectives, status,
                     revision, assessments, visualizations)
                VALUES (:id, :title, :namespace, :module, :section, :position,
                        :difficulty, :description, :objectives, :status,
                        :revision, :assessments, :visualizations)
                ON CONFLICT (id) DO UPDATE SET title = EXCLUDED.title,
                                              namespace = EXCLUDED.namespace,
                                              module = EXCLUDED.module,
                                              section_slug = EXCLUDED.section_slug,
                                              position = EXCLUDED.position,
                                              difficulty = EXCLUDED.difficulty,
                                              description = EXCLUDED.description,
                                              learning_objectives = EXCLUDED.learning_objectives,
                                              status = EXCLUDED.status,
                                              assessments = EXCLUDED.assessments,
                                              visualizations = EXCLUDED.visualizations
                """
            ),
            {
                "id": str(topic["id"]),
                "title": str(topic["title"]),
                "namespace": str(topic["namespace"]),
                "module": str(topic["module"]),
                "section": _section_for(str(topic["namespace"])),
                "position": int(topic["position"]),  # type: ignore[arg-type]
                "difficulty": str(topic["difficulty"]),
                "description": str(topic["description"]),
                "objectives": json.dumps(topic["objectives"]),
                "status": str(topic["status"]),
                "revision": 1,
                "assessments": json.dumps(topic["assessments"]),
                "visualizations": json.dumps(topic["visualizations"]),
            },
        )

    # -- prerequisite edges, now carrying the rationale --------------------- #
    # Every topic referenced by an edge exists by this point: the loop above
    # inserted the new ones and a2b3c4d5e6f7 inserted the originals.
    for topic_id, prereq_id, kind, rationale in all_prerequisites_with_rationale():
        bind.execute(
            sa.text(
                """
                INSERT INTO topic_prerequisites (topic_id, prerequisite_id, kind, rationale)
                VALUES (CAST(:t AS VARCHAR), CAST(:p AS VARCHAR),
                        CAST(:k AS VARCHAR), CAST(:r AS VARCHAR))
                ON CONFLICT (topic_id, prerequisite_id)
                DO UPDATE SET kind = EXCLUDED.kind,
                              rationale = EXCLUDED.rationale
                """
            ),
            {"t": topic_id, "p": prereq_id, "k": kind, "r": rationale},
        )

    # -- lesson <-> topic associations -------------------------------------- #
    # Draft topics point at lessons that do not exist yet. lesson_topics has no
    # foreign key to lessons, and both the hierarchy builder and the topic
    # detail endpoint skip slugs with no matching lesson row, so these are
    # inert until the content is authored.
    for lesson_slug, topic_id, confidence, is_primary in all_lesson_topics():
        bind.execute(
            sa.text(
                """
                INSERT INTO lesson_topics (lesson_slug, topic_id, confidence, is_primary)
                VALUES (CAST(:l AS VARCHAR), CAST(:t AS VARCHAR),
                        CAST(:c AS VARCHAR), :p)
                ON CONFLICT (lesson_slug, topic_id)
                DO UPDATE SET confidence = EXCLUDED.confidence,
                              is_primary = EXCLUDED.is_primary
                """
            ),
            {
                "l": lesson_slug,
                "t": topic_id,
                "c": confidence,
                "p": 1 if is_primary else 0,
            },
        )


def downgrade() -> None:
    """Remove the M4 expansion, restoring the 17-topic curriculum.

    Refuses to run if a learner has earned mastery against any topic this
    revision added. Deleting those topics would cascade away real learner
    history, so the choice is left to an operator who can see the count.
    """
    bind = op.get_bind()
    new_ids = _m4_topic_ids()
    if not new_ids:
        return

    if _has_table("topic_mastery"):
        stmt = sa.text("SELECT COUNT(*) FROM topic_mastery WHERE topic_id IN :ids")
        stmt = stmt.bindparams(bindparam("ids", expanding=True))
        held = bind.execute(stmt, {"ids": new_ids}).scalar() or 0
        if held:
            raise RuntimeError(
                f"refusing to downgrade: {held} topic_mastery row(s) reference "
                f"M4 topics. Removing them would delete learner history. Migrate "
                f"or archive those rows first."
            )

    # Edges first: they reference topics from both sides.
    if _has_table("topic_prerequisites"):
        del_edges = sa.text(
            "DELETE FROM topic_prerequisites WHERE topic_id IN :ids"
            " OR prerequisite_id IN :ids"
        )
        del_edges = del_edges.bindparams(bindparam("ids", expanding=True))
        bind.execute(del_edges, {"ids": new_ids})

    if _has_table("lesson_topics"):
        del_links = sa.text("DELETE FROM lesson_topics WHERE topic_id IN :ids")
        del_links = del_links.bindparams(bindparam("ids", expanding=True))
        bind.execute(del_links, {"ids": new_ids})

    if _has_table("curriculum_topics"):
        del_topics = sa.text("DELETE FROM curriculum_topics WHERE id IN :ids")
        del_topics = del_topics.bindparams(bindparam("ids", expanding=True))
        bind.execute(del_topics, {"ids": new_ids})

    # Drop the rationale column last, once no M4 row depends on it. SQLite
    # needs batch mode to drop a column.
    if _has_column("topic_prerequisites", "rationale"):
        with op.batch_alter_table("topic_prerequisites") as batch:
            batch.drop_column("rationale")
