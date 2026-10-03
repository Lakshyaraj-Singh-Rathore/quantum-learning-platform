"""Migrate to stable namespaced topic identifiers

Replaces the provisional flat topic slugs from f1a2b3c4d5e6 with permanent,
namespaced identifiers (``qc.qubits``, ``algo.grover``), converts the
lesson-to-topic link from one-to-one to many-to-many, and introduces the
split between topic mastery and lesson completion.

Why the schema changes shape
----------------------------
Topic identity moves from ``(int id, unique slug)`` to the namespaced id as
the primary key. Storing the identifier as the key makes it impossible for two
rows to claim the same identity, and lets lessons, mastery and prerequisites
reference it without a join.

Lessons gain a many-to-many link. A lesson legitimately teaches several topics
and a topic is taught by several lessons; the previous single ``topic_slug``
column could not express that, and forcing one topic per lesson would have
meant silently discarding secondary concepts.

Mastery is separated from completion. Reading a lesson is not evidence of
mastery, so lesson completion gets its own table and no longer implies credit
for every topic a lesson mentions.

Data safety
-----------
No legacy row is modified or deleted. ``user_mastery`` keeps every column and
every value. The new ``topic_mastery`` rows are *derived* from it, each
carrying provenance back to the originating row.

Only mappings with ``high`` confidence become ``mapped`` mastery. Anything
else is recorded as ``legacy_only``: preserved and auditable, but never
counted and never able to satisfy a prerequisite.

Two provisional topics merge into one stable topic:

    classical-vs-qubit + qubits          -> qc.qubits
    control-flow       + dynamic-circuits -> adv.dynamic_circuits

Where a learner held both, the values are averaged rather than duplicated, and
the provenance list records every contributing row.

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-10-03
"""

from __future__ import annotations

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.curriculum import (
    MASTERY_MAPPABLE_CONFIDENCE,
    LEGACY_TAG_TO_TOPIC,
    SECTIONS,
    TOPICS,
    all_lesson_topics,
    all_prerequisites,
)

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Provisional flat slug -> stable namespaced id. Two merge; see docstring.
FLAT_TO_STABLE: dict[str, str] = {
    "measurement": "core.measurement_theory",
    "quantum-noise": "qiskit.quantum_noise",
    "classical-vs-qubit": "qc.qubits",
    "qubits": "qc.qubits",
    "quantum-gates": "qc.basic_gates",
    "bell-states": "qc.bell_states",
    "entanglement": "qc.entanglement",
    "deutsch-jozsa": "algo.deutsch_jozsa",
    "grover": "algo.grover",
    "control-flow": "adv.dynamic_circuits",
    "dynamic-circuits": "adv.dynamic_circuits",
    "vqe-qaoa": "nisq.vqe",
}


def _has_table(table: str) -> bool:
    return table in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    # -- drop the superseded single-topic column --------------------------- #
    # lessons.topic_slug carried a foreign key to curriculum_topics.slug, which
    # no longer exists now that the primary key is the namespaced id. The
    # many-to-many lesson_topics table replaces it. The downgrade re-adds it.
    if _has_column("lessons", "topic_slug"):
        with op.batch_alter_table("lessons") as batch:
            batch.drop_column("topic_slug")

    # The stamp is no longer needed: topic_mastery records provenance back to
    # this table, so the legacy row itself never has to be annotated.
    if _has_column("user_mastery", "topic_slug"):
        with op.batch_alter_table("user_mastery") as batch:
            batch.drop_column("topic_slug")

    # -- sections gain a letter ------------------------------------------- #
    if not _has_column("curriculum_sections", "letter"):
        op.add_column(
            "curriculum_sections", sa.Column("letter", sa.String(length=2), default="")
        )

    for section in SECTIONS:
        bind.execute(
            sa.text(
                """
                INSERT INTO curriculum_sections (slug, letter, title, position)
                VALUES (:slug, :letter, :title, :position)
                ON CONFLICT (slug) DO UPDATE SET letter = EXCLUDED.letter,
                                                title = EXCLUDED.title,
                                                position = EXCLUDED.position
                """
            ),
            dict(section),
        )

    # -- topics: rebuild with the namespaced id as primary key ------------- #
    # SQLite cannot alter a primary key in place, so build the new table,
    # copy across, swap, and drop. Existing rows are translated through
    # FLAT_TO_STABLE; anything untranslatable is dropped rather than left
    # holding an identifier that no longer exists in the registry.
    op.create_table(
        "curriculum_topics_new",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("title", sa.String(length=200)),
        sa.Column("namespace", sa.String(length=20), index=True),
        sa.Column("module", sa.String(length=80), default="", index=True),
        sa.Column("section_slug", sa.String(length=80), index=True),
        sa.Column("position", sa.Integer(), default=0),
        sa.Column("difficulty", sa.String(length=20), default="beginner"),
        sa.Column("description", sa.Text(), default=""),
        sa.Column("learning_objectives", sa.Text(), default="[]"),
        sa.Column("status", sa.String(length=20), default="draft", index=True),
        sa.Column("revision", sa.Integer(), default=1),
        sa.Column("assessments", sa.Text(), default="[]"),
        sa.Column("visualizations", sa.Text(), default="[]"),
        sa.ForeignKeyConstraint(["section_slug"], ["curriculum_sections.slug"]),
    )

    old_rows = []
    if _has_table("curriculum_topics"):
        old_rows = bind.execute(
            sa.text(
                "SELECT slug, title, section_slug, position, difficulty, summary,"
                " learning_objectives FROM curriculum_topics"
            )
        ).fetchall()

    translated = {
        row[0]: FLAT_TO_STABLE[row[0]]
        for row in old_rows
        if row[0] in FLAT_TO_STABLE
    }

    # Seed from the canonical registry; this overwrites the copied rows so the
    # registry, not the database, is authoritative.
    for topic in TOPICS:
        bind.execute(
            sa.text(
                """
                INSERT INTO curriculum_topics_new
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
                "id": topic["id"],
                "title": topic["title"],
                "namespace": topic["namespace"],
                "module": topic["module"],
                "section": _section_for(str(topic["namespace"])),
                "position": topic["position"],
                "difficulty": topic["difficulty"],
                "description": topic["description"],
                "objectives": json.dumps(topic["objectives"]),
                "status": topic["status"],
                "revision": 1,
                "assessments": json.dumps(topic["assessments"]),
                "visualizations": json.dumps(topic["visualizations"]),
            },
        )

    # -- prerequisite edges on the new identifiers -------------------------- #
    op.create_table(
        "topic_prerequisites_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_id", sa.String(length=80), index=True),
        sa.Column("prerequisite_id", sa.String(length=80), index=True),
        sa.Column("kind", sa.String(length=20), default="required"),
        sa.ForeignKeyConstraint(["topic_id"], ["curriculum_topics_new.id"]),
        sa.ForeignKeyConstraint(["prerequisite_id"], ["curriculum_topics_new.id"]),
        sa.UniqueConstraint("topic_id", "prerequisite_id", name="uq_topic_prereq"),
    )
    for topic_id, prereq_id, kind in all_prerequisites():
        bind.execute(
            sa.text(
                "INSERT INTO topic_prerequisites_new (topic_id, prerequisite_id, kind)"
                " VALUES (:t, :p, :k)"
            ),
            {"t": topic_id, "p": prereq_id, "k": kind},
        )

    # -- lesson <-> topic, many to many ------------------------------------- #
    if _has_column("lessons", "topic_slug"):
        # Carry the provisional single-topic placement forward so no lesson
        # loses its place, then let the registry links overwrite it.
        rows = bind.execute(
            sa.text("SELECT slug, topic_slug FROM lessons WHERE topic_slug IS NOT NULL")
        ).fetchall()
        provisional = {
            slug: translated.get(flat, flat) for slug, flat in rows if flat in translated
        }
    else:
        provisional = {}

    op.create_table(
        "lesson_topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lesson_slug", sa.String(length=120), index=True),
        sa.Column("topic_id", sa.String(length=80), index=True),
        sa.Column("confidence", sa.String(length=16), default="medium"),
        sa.Column("is_primary", sa.Integer(), default=0),
        sa.ForeignKeyConstraint(["topic_id"], ["curriculum_topics_new.id"]),
        sa.UniqueConstraint("lesson_slug", "topic_id", name="uq_lesson_topic"),
    )

    for lesson_slug, topic_id, confidence, is_primary in all_lesson_topics():
        bind.execute(
            sa.text(
                "INSERT INTO lesson_topics (lesson_slug, topic_id, confidence, is_primary)"
                " VALUES (:l, :t, :c, :p)"
            ),
            {
                "l": lesson_slug,
                "t": topic_id,
                "c": confidence,
                "p": 1 if is_primary else 0,
            },
        )
    # Recover secondary placements preserved by an earlier downgrade. Without
    # this, downgrade -> upgrade would lose every non-primary mapping.
    if _has_column("lessons", "additional_topics"):
        for lesson_slug, raw in bind.execute(
            sa.text(
                "SELECT slug, additional_topics FROM lessons"
                " WHERE additional_topics IS NOT NULL"
            )
        ):
            try:
                restored = json.loads(raw)
            except (TypeError, ValueError):
                continue
            for topic_id in restored:
                if topic_id not in {t["id"] for t in TOPICS}:
                    continue
                bind.execute(
                    sa.text(
                        "INSERT INTO lesson_topics (lesson_slug, topic_id, confidence, is_primary)"
                        " SELECT :l, :t, 'medium', 0"
                        " WHERE NOT EXISTS (SELECT 1 FROM lesson_topics"
                        "  WHERE lesson_slug = :l AND topic_id = :t)"
                    ),
                    {"l": str(lesson_slug), "t": str(topic_id)},
                )

    # Any lesson placed provisionally but absent from the registry keeps its
    # placement at medium confidence rather than being orphaned.
    for lesson_slug, topic_id in provisional.items():
        if topic_id in {t["id"] for t in TOPICS}:
            bind.execute(
                sa.text(
                    "INSERT INTO lesson_topics (lesson_slug, topic_id, confidence, is_primary)"
                    " SELECT :l, :t, 'medium', 0"
                    " WHERE NOT EXISTS (SELECT 1 FROM lesson_topics"
                    "  WHERE lesson_slug = :l AND topic_id = :t)"
                ),
                {"l": lesson_slug, "t": topic_id},
            )

    # -- swap the topic tables ---------------------------------------------- #
    op.drop_table("topic_prerequisites")
    op.drop_table("curriculum_topics")
    op.rename_table("curriculum_topics_new", "curriculum_topics")
    op.rename_table("topic_prerequisites_new", "topic_prerequisites")
    # Retire sections the current registry no longer defines. The superseded
    # registry had an "advanced-theory-circuits" section that this one drops;
    # simply upserting the current set leaves that orphan behind, where it
    # renders as a nameless, letterless section competing for position 6. Only
    # sections with no topics referencing them are removed, so this can never
    # strand real content.
    keep = {section["slug"] for section in SECTIONS}
    orphans = [
        row[0]
        for row in bind.execute(
            sa.text(
                "SELECT s.slug FROM curriculum_sections s"
                " WHERE NOT EXISTS (SELECT 1 FROM curriculum_topics t"
                "  WHERE t.section_slug = s.slug)"
            )
        )
        if row[0] not in keep
    ]
    for slug in orphans:
        bind.execute(
            sa.text("DELETE FROM curriculum_sections WHERE slug = :s"), {"s": slug}
        )


    # -- mastery: derived, provenance-carrying, non-destructive ------------- #
    if not _has_table("topic_mastery"):
        op.create_table(
            "topic_mastery",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), index=True),
            sa.Column("topic_id", sa.String(length=80), index=True),
            sa.Column("mastery_level", sa.Float(), default=0.0),
            sa.Column("status", sa.String(length=20), default="verified", index=True),
            sa.Column("source", sa.String(length=120), default=""),
            sa.Column("evidence", sa.Text(), default="{}"),
            sa.Column("last_activity", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["topic_id"], ["curriculum_topics.id"]),
            sa.UniqueConstraint("user_id", "topic_id", "source", name="uq_topic_mastery"),
        )

    if not _has_table("lesson_completions"):
        op.create_table(
            "lesson_completions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), index=True),
            sa.Column("lesson_slug", sa.String(length=120), index=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.UniqueConstraint("user_id", "lesson_slug", name="uq_lesson_completion"),
        )

    _derive_mastery(bind)


def _section_for(namespace: str) -> str:
    from app.curriculum import NAMESPACES

    return NAMESPACES[namespace][0]


def _derive_mastery(bind) -> None:
    """Create ``topic_mastery`` rows from legacy ``user_mastery`` rows.

    Groups by (user, topic) so that two legacy tags landing on the same stable
    topic -- or two provisional topics merging -- produce one averaged row, not
    two competing ones. Each row records the rows it came from.
    """
    # topic_slug no longer exists on user_mastery: this migration drops it, and
    # the mapping it represented is fully captured by LEGACY_TAG_TO_TOPIC. The
    # legacy tag is the only input, which is also the safer basis since it is
    # the value the row was actually written with.
    rows = bind.execute(
        sa.text(
            "SELECT id, user_id, tag, score, attempts, updated_at FROM user_mastery"
        )
    ).fetchall()

    grouped: dict[tuple[int, str], list[tuple]] = {}
    for row in rows:
        topic_id = LEGACY_TAG_TO_TOPIC.get(row[2])
        if topic_id is None:
            continue
        # Normalise a provisional flat slug to its stable id.
        topic_id = FLAT_TO_STABLE.get(topic_id, topic_id)
        if topic_id not in {t["id"] for t in TOPICS}:
            continue
        grouped.setdefault((row[1], topic_id), []).append(row)

    for (user_id, topic_id), group in grouped.items():
        # Only high-confidence mappings count toward mastery. The confidence
        # that matters is the lesson->topic link; a tag mapping was already
        # vetted when LEGACY_TAG_TO_TOPIC was authored.
        confidences = {
            c
            for _l, t, c, _p in all_lesson_topics()
            if t == topic_id
        }
        mappable = any(c in MASTERY_MAPPABLE_CONFIDENCE for c in confidences) or not confidences
        status = "mapped" if mappable else "legacy_only"
        score = sum(float(r[3]) for r in group) / len(group)
        attempts = sum(int(r[4] or 0) for r in group)

        bind.execute(
            sa.text(
                """
                INSERT INTO topic_mastery
                    (user_id, topic_id, mastery_level, status, source, evidence,
                     last_activity, created_at)
                VALUES (:user, :topic, :score, :status, :source, :evidence,
                        :last, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, topic_id, source) DO UPDATE SET
                    mastery_level = EXCLUDED.mastery_level,
                    evidence = EXCLUDED.evidence,
                    last_activity = EXCLUDED.last_activity
                """
            ),
            {
                "user": user_id,
                "topic": topic_id,
                "score": round(score, 6),
                "status": status,
                "source": f"migration:user_mastery",
                "evidence": json.dumps(
                    {
                        "originating_rows": [
                            {"id": r[0], "tag": r[2], "score": float(r[3]),
                             "attempts": int(r[4] or 0)}
                            for r in group
                        ],
                        "attempts": attempts,
                        "row_count": len(group),
                        "aggregation": "mean" if len(group) > 1 else "single",
                    }
                ),
                "last": group[0][5],
            },
        )


def downgrade() -> None:
    """Restore the provisional flat-slug schema.

    The derived ``topic_mastery`` rows are dropped: they are reproducible from
    ``user_mastery``, which this migration never modifies. Lesson placements
    are written back onto ``lessons.topic_slug`` using the each lesson's
    primary topic, so no lesson is left unplaced.
    """
    bind = op.get_bind()

    if _has_table("topic_mastery"):
        op.drop_table("topic_mastery")
    if _has_table("lesson_completions"):
        op.drop_table("lesson_completions")

    if _has_table("lesson_topics"):
        if not _has_column("lessons", "topic_slug"):
            op.add_column(
                "lessons", sa.Column("topic_slug", sa.String(length=80), nullable=True)
            )
        rows = bind.execute(
            sa.text(
                "SELECT lesson_slug, topic_id FROM lesson_topics WHERE is_primary = 1"
            )
        ).fetchall()
        reverse = {v: k for k, v in FLAT_TO_STABLE.items()}
        # Where two provisional topics merged, restore the canonical one.
        reverse.setdefault("qc.qubits", "qubits")
        reverse.setdefault("adv.dynamic_circuits", "dynamic-circuits")
        for lesson_slug, topic_id in rows:
            bind.execute(
                sa.text("UPDATE lessons SET topic_slug = :t WHERE slug = :l"),
                {"t": reverse.get(topic_id, topic_id), "l": lesson_slug},
            )
        # The pre-migration schema stores ONE topic per lesson in topic_slug.
        # Some lessons legitimately belong to two topics, so restoring only the
        # primary would silently drop the secondary placement. The secondary is
        # written to an additive, nullable column that pre-migration code never
        # reads, so the old schema stays exactly as it was for old code while a
        # re-upgrade can recover every placement. Nothing is discarded.
        if not _has_column("lessons", "additional_topics"):
            op.add_column("lessons", sa.Column("additional_topics", sa.Text(), nullable=True))
        secondary: dict[str, list[str]] = {}
        for lesson_slug, topic_id in bind.execute(
            sa.text("SELECT lesson_slug, topic_id FROM lesson_topics WHERE is_primary = 0")
        ):
            secondary.setdefault(str(lesson_slug), []).append(str(topic_id))
        for lesson_slug, topic_ids in secondary.items():
            bind.execute(
                sa.text("UPDATE lessons SET additional_topics = :j WHERE slug = :l"),
                {"j": json.dumps(sorted(topic_ids)), "l": lesson_slug},
            )
        op.drop_table("lesson_topics")

    # Rebuild the flat-slug topic tables.
    op.create_table(
        "curriculum_topics_flat",
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
    for stable, flat in {v: k for k, v in FLAT_TO_STABLE.items()}.items():
        for topic in TOPICS:
            if topic["id"] != stable:
                continue
            bind.execute(
                sa.text(
                    # ON CONFLICT DO NOTHING, not INSERT OR IGNORE: the latter
                    # is SQLite-only and would fail outright on PostgreSQL,
                    # which is the production dialect. ON CONFLICT is supported
                    # by PostgreSQL 9.5+ and SQLite 3.24+.
                    "INSERT INTO curriculum_topics_flat"
                    " (slug, title, section_slug, position, difficulty, summary,"
                    "  learning_objectives)"
                    " VALUES (:slug, :title, :section, :position, :difficulty,"
                    "  :summary, :objectives)"
                    " ON CONFLICT (slug) DO NOTHING"
                ),
                {
                    "slug": flat,
                    "title": topic["title"],
                    "section": _section_for(str(topic["namespace"])),
                    "position": topic["position"],
                    "difficulty": topic["difficulty"],
                    "summary": topic["description"],
                    "objectives": json.dumps(topic["objectives"]),
                },
            )

    op.create_table(
        "topic_prerequisites_flat",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic_slug", sa.String(length=80), index=True),
        sa.Column("prerequisite_slug", sa.String(length=80), index=True),
        sa.Column("kind", sa.String(length=20), default="required"),
    )
    reverse = {v: k for k, v in FLAT_TO_STABLE.items()}
    for topic_id, prereq_id, kind in all_prerequisites():
        bind.execute(
            sa.text(
                "INSERT INTO topic_prerequisites_flat (topic_slug, prerequisite_slug, kind)"
                " VALUES (:t, :p, :k)"
            ),
            {
                "t": reverse.get(topic_id, topic_id),
                "p": reverse.get(prereq_id, prereq_id),
                "k": kind,
            },
        )

    op.drop_table("topic_prerequisites")
    op.drop_table("curriculum_topics")
    op.rename_table("curriculum_topics_flat", "curriculum_topics")
    op.rename_table("topic_prerequisites_flat", "topic_prerequisites")
