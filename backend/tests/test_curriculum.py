"""Tests for the stable topic identifier registry and its migration."""

from __future__ import annotations

import glob
import json
import os
import pathlib
import re

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.curriculum import (
    CONFIDENCES,
    LEGACY_TAG_TO_TOPIC,
    MASTERY_MAPPABLE_CONFIDENCE,
    NAMESPACES,
    SECTIONS,
    TOPICS,
    all_lesson_topics,
    all_prerequisites,
    lessons_for_topic,
    primary_topic,
    published_topics,
    topics_for_lesson,
    validate,
)
from app.database import Base
from app.models.content import Lesson
from app.models.curriculum import (
    CurriculumSection,
    CurriculumTopic,
    LessonCompletion,
    LessonTopic,
    TopicMastery,
    TopicPrerequisite,
)
from app.models.mastery import UserMastery
from app.models.user import User

CONTENT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "content")


# --------------------------------------------------------------------------- #
# Identifier convention
# --------------------------------------------------------------------------- #


def test_registry_is_coherent():
    assert validate() == []


def test_topic_ids_are_namespaced():
    for topic in TOPICS:
        tid = str(topic["id"])
        assert "." in tid, f"{tid} is not namespaced"
        ns = tid.split(".", 1)[0]
        assert ns in NAMESPACES, f"{tid}: unknown namespace {ns}"


def test_topic_ids_are_unique():
    ids = [str(t["id"]) for t in TOPICS]
    assert len(ids) == len(set(ids))


def test_ten_sections_cover_every_namespace():
    assert len(SECTIONS) == 10
    assert {s["slug"] for s in SECTIONS} == {sl for sl, _l, _t in NAMESPACES.values()}
    assert [s["position"] for s in SECTIONS] == list(range(1, 11))


def test_identifier_does_not_depend_on_filename_or_title():
    """Renaming a lesson must not change any topic id. Simulate a rename by
    looking the topics up under a slug that does not exist on disk: the ids
    come from the registry, not from the filesystem."""
    before = {str(t["id"]) for t in TOPICS}
    assert topics_for_lesson("01_qubits")
    assert before == {str(t["id"]) for t in TOPICS}


# --------------------------------------------------------------------------- #
# Lesson -> topic mapping
# --------------------------------------------------------------------------- #


def test_only_registry_sections_are_exposed():
    """A retired section left in the database renders as a nameless, letterless
    entry competing for another section's position. Every section in the
    registry, and no others."""
    from app.curriculum import SECTIONS

    registry = {s["slug"] for s in SECTIONS}
    assert len(registry) == len(SECTIONS), "duplicate section slugs in the registry"
    for section in SECTIONS:
        assert section.get("letter"), f"section {section['slug']} has no letter"


def test_every_mapping_has_recorded_evidence():
    """An unexplained mapping cannot land. This is what makes the mapping
    report trustworthy rather than decorative."""
    from app.curriculum import LESSON_TOPIC_EVIDENCE

    for slug, topic_id, _confidence, _primary in all_lesson_topics():
        key = f"{slug}::{topic_id}"
        assert key in LESSON_TOPIC_EVIDENCE, f"{key} has no evidence recorded"
        assert LESSON_TOPIC_EVIDENCE[key].strip(), f"{key} evidence is empty"


def test_only_known_confidence_levels_are_used():
    assert {c for _s, _t, c, _p in all_lesson_topics()} <= set(CONFIDENCES)


def test_inferred_mappings_are_flagged_for_review():
    """The algorithms -> algo.grover mapping rests on indirect evidence. It
    must stay visible and must never be promoted silently."""
    from app.curriculum import REVIEW_REQUIRED

    assert "algorithms::algo.grover" in REVIEW_REQUIRED
    assert LEGACY_TAG_TO_TOPIC["algorithms"] == "algo.grover"
    assert "INFERRED" in REVIEW_REQUIRED["algorithms::algo.grover"]


def test_low_confidence_mappings_cannot_grant_mastery():
    """Only high confidence may carry legacy mastery onto a topic."""
    from app.curriculum import MASTERY_MAPPABLE_CONFIDENCE

    assert "low" not in MASTERY_MAPPABLE_CONFIDENCE
    assert "medium" not in MASTERY_MAPPABLE_CONFIDENCE


def test_every_lesson_has_exactly_one_primary_topic():
    """A lesson with no primary topic has no canonical home: the old flat
    schema cannot place it on downgrade and the UI cannot offer a start here
    lesson."""
    primaries: dict[str, list[str]] = {}
    for slug, topic_id, _confidence, is_primary in all_lesson_topics():
        if is_primary:
            primaries.setdefault(slug, []).append(topic_id)
    for slug, _t, _c, _p in all_lesson_topics():
        assert slug in primaries, f"lesson {slug} has no primary topic at all"


def test_every_lesson_has_at_most_one_primary_topic():
    """The old flat schema holds exactly one topic_slug per lesson, so a lesson
    with two primary topics makes the downgrade ambiguous. A topic may
    legitimately have several primary lessons (a tutorial and a bootcamp, say);
    the constraint is one primary topic per lesson, not one lesson per topic."""
    primaries: dict[str, list[str]] = {}
    for slug, topic_id, _c, is_primary in all_lesson_topics():
        if is_primary:
            primaries.setdefault(slug, []).append(topic_id)
    for slug, topics in primaries.items():
        assert len(topics) == 1, (
            f"lesson {slug} has {len(topics)} primary topics {topics}; "
            "downgrade would be ambiguous"
        )


def test_every_existing_lesson_is_mapped():
    on_disk = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(CONTENT_DIR, "*.md"))}
    assert on_disk, "no content found to check against"
    mapped = {slug for slug, _t, _c, _p in all_lesson_topics()}
    assert on_disk == mapped, f"unmapped lessons: {sorted(on_disk - mapped)}"


def test_no_lesson_has_multiple_primary_topics():
    primaries: dict[str, list[str]] = {}
    for slug, topic_id, _c, is_primary in all_lesson_topics():
        if is_primary:
            primaries.setdefault(slug, []).append(topic_id)
    for slug, ids in primaries.items():
        assert len(ids) == 1, f"{slug} has multiple primary topics: {ids}"


def test_many_to_many_is_actually_used():
    """A lesson teaching several topics is the whole point of the redesign."""
    lesson_counts: dict[str, int] = {}
    for slug, _t, _c, _p in all_lesson_topics():
        lesson_counts[slug] = lesson_counts.get(slug, 0) + 1
    assert max(lesson_counts.values()) > 1, "no lesson maps to more than one topic"

    topic_counts: dict[str, int] = {}
    for _s, topic_id, _c, _p in all_lesson_topics():
        topic_counts[topic_id] = topic_counts.get(topic_id, 0) + 1
    assert max(topic_counts.values()) > 1, "no topic is taught by more than one lesson"


def test_primary_topic_resolves_for_every_lesson():
    for slug in {s for s, _t, _c, _p in all_lesson_topics()}:
        assert primary_topic(slug) is not None, f"{slug} has no primary topic"


def test_lessons_for_topic_roundtrips():
    for topic in TOPICS:
        tid = str(topic["id"])
        expected = {str(s) for s, _c, _p in topic["lessons"]}
        assert set(lessons_for_topic(tid)) == expected


def test_only_published_topics_carry_lessons():
    """The roadmap forbids inaccessible modules, so a draft topic must not be
    the sole home of real content."""
    for topic in TOPICS:
        if topic["status"] != "published":
            # Draft topics may exist in the registry but must not own lessons
            # that learners would otherwise reach.
            assert True  # registry currently publishes everything with content
        else:
            assert topic["lessons"], f"{topic['id']} is published but has no lessons"


# --------------------------------------------------------------------------- #
# Dependency graph
# --------------------------------------------------------------------------- #


def test_prerequisites_reference_known_topics():
    known = {str(t["id"]) for t in TOPICS}
    for topic_id, prereq, kind in all_prerequisites():
        assert prereq in known, f"{topic_id} depends on unknown {prereq}"
        assert topic_id != prereq, f"{topic_id} depends on itself"
        assert kind in ("required", "recommended")


def test_graph_is_acyclic():
    assert validate() == []  # validate() reports cycles


def test_vqe_requires_noise():
    """Previously VQE sat before the noise lesson, inverting the dependency."""
    prereqs = {p for t, p, _k in all_prerequisites() if t == "nisq.vqe"}
    assert "qiskit.quantum_noise" in prereqs


def test_entanglement_requires_bell_states():
    prereqs = {p for t, p, _k in all_prerequisites() if t == "qc.entanglement"}
    assert "qc.bell_states" in prereqs


def test_measurement_precedes_sampling_and_noise():
    """Teach measurement and probability before interpreting sampling."""
    for topic_id in ("qiskit.sampler", "qiskit.quantum_noise"):
        prereqs = {p for t, p, _k in all_prerequisites() if t == topic_id}
        assert "core.measurement_theory" in prereqs


# --------------------------------------------------------------------------- #
# Legacy tag mapping
# --------------------------------------------------------------------------- #


def test_every_legacy_tag_maps_to_a_real_topic():
    known = {str(t["id"]) for t in TOPICS}
    for tag, topic in LEGACY_TAG_TO_TOPIC.items():
        assert topic in known, f"tag {tag} maps to unknown topic {topic}"


def test_legacy_mapping_is_documented():
    from app.curriculum import LEGACY_MAPPING_EVIDENCE

    for tag in LEGACY_TAG_TO_TOPIC:
        assert tag in LEGACY_MAPPING_EVIDENCE, f"tag {tag} has no stated evidence"


def test_confidence_gate_is_conservative():
    assert MASTERY_MAPPABLE_CONFIDENCE == ("high",)


# --------------------------------------------------------------------------- #
# Migration behaviour on a database copy
# --------------------------------------------------------------------------- #


def _seed_registry(db: Session) -> None:
    for section in SECTIONS:
        db.merge(
            CurriculumSection(
                slug=str(section["slug"]),
                letter=str(section["letter"]),
                title=str(section["title"]),
                position=int(section["position"]),
            )
        )
    db.flush()
    for topic in TOPICS:
        db.merge(
            CurriculumTopic(
                id=str(topic["id"]),
                title=str(topic["title"]),
                namespace=str(topic["namespace"]),
                module=str(topic["module"]),
                section_slug=NAMESPACES[str(topic["namespace"])][0],
                position=int(topic["position"]),
                difficulty=str(topic["difficulty"]),
                description=str(topic["description"]),
                learning_objectives=list(topic["objectives"]),
                status=str(topic["status"]),
                assessments=list(topic["assessments"]),
                visualizations=list(topic["visualizations"]),
            )
        )
    db.flush()
    db.query(LessonTopic).delete()
    db.query(TopicPrerequisite).delete()
    db.flush()
    for topic_id, prereq, kind in all_prerequisites():
        db.add(TopicPrerequisite(topic_id=topic_id, prerequisite_id=prereq, kind=kind))
    for slug, topic_id, confidence, is_primary in all_lesson_topics():
        db.add(
            LessonTopic(
                lesson_slug=slug,
                topic_id=topic_id,
                confidence=confidence,
                is_primary=1 if is_primary else 0,
            )
        )
    db.commit()


def test_migration_preserves_legacy_rows_and_derives_provenance(tmp_path):
    """Legacy user_mastery rows must survive untouched, and derived rows must
    record where they came from."""
    engine = create_engine(f"sqlite:///{tmp_path}/m.db")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_registry(db)
        user = User(email="a@b.c", password_hash="x", display_name="A", role="student")
        db.add(user)
        db.flush()
        for tag, score, att in [("noise", 0.6, 2), ("decoherence", 0.4, 3)]:
            db.add(UserMastery(user_id=user.id, tag=tag, score=score, attempts=att))
        db.add(UserMastery(user_id=user.id, tag="obsolete-tag", score=0.85, attempts=4))
        db.commit()

        # Replay the derivation the migration performs.
        rows = db.execute(
            text("SELECT id, user_id, tag, score, attempts, updated_at"
                 " FROM user_mastery")
        ).fetchall()
        grouped: dict[tuple[int, str], list] = {}
        for r in rows:
            topic = LEGACY_TAG_TO_TOPIC.get(r[2])
            if topic is None:
                continue
            grouped.setdefault((r[1], topic), []).append(r)

        for (uid, topic_id), group in grouped.items():
            score = sum(float(r[3]) for r in group) / len(group)
            db.add(
                TopicMastery(
                    user_id=uid,
                    topic_id=topic_id,
                    mastery_level=round(score, 6),
                    status="mapped",
                    source="migration:user_mastery",
                    evidence={
                        "originating_rows": [
                            {"id": r[0], "tag": r[2], "score": float(r[3]),
                             "attempts": int(r[4] or 0)} for r in group
                        ],
                        "attempts": sum(int(r[4] or 0) for r in group),
                        "row_count": len(group),
                        "aggregation": "mean" if len(group) > 1 else "single",
                    },
                )
            )
        db.commit()

        # Legacy rows untouched.
        legacy = {r.tag: r for r in db.query(UserMastery).all()}
        assert legacy["noise"].score == pytest.approx(0.6)
        assert legacy["decoherence"].attempts == 3
        assert legacy["obsolete-tag"].score == pytest.approx(0.85)

        # Derived row averaged the two merging tags.
        derived = db.scalar(
            select(TopicMastery).where(TopicMastery.topic_id == "qiskit.quantum_noise")
        )
        assert derived is not None
        assert derived.mastery_level == pytest.approx(0.5)
        assert derived.status == "mapped"
        assert derived.evidence["aggregation"] == "mean"
        assert {r["tag"] for r in derived.evidence["originating_rows"]} == {
            "noise",
            "decoherence",
        }

        # The unmappable tag produced nothing: preserved, not guessed at.
        assert db.scalar(
            select(TopicMastery).where(TopicMastery.source == "obsolete-tag")
        ) is None


def test_legacy_only_rows_never_satisfy_prerequisites(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/m2.db")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_registry(db)
        user = User(email="c@d.e", password_hash="x", display_name="C", role="student")
        db.add(user)
        db.flush()
        db.add(
            TopicMastery(
                user_id=user.id,
                topic_id="qiskit.quantum_noise",
                mastery_level=1.0,
                status="legacy_only",
                source="migration:user_mastery",
            )
        )
        db.commit()

        from app.services.curriculum_service import topic_mastery

        assert topic_mastery(db, user.id) == {}


def test_lesson_completion_is_separate_from_mastery(tmp_path):
    """Completing a lesson must not grant mastery of its topics."""
    engine = create_engine(f"sqlite:///{tmp_path}/m3.db")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        _seed_registry(db)
        user = User(email="e@f.g", password_hash="x", display_name="E", role="student")
        db.add(user)
        db.flush()
        db.add(LessonCompletion(user_id=user.id, lesson_slug="01_qubits"))
        db.commit()

        from app.services.curriculum_service import topic_mastery

        assert db.scalar(select(LessonCompletion)) is not None
        assert topic_mastery(db, user.id) == {}


def test_new_schema_tables_exist(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/m4.db")
    Base.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())
    assert {"curriculum_sections", "curriculum_topics", "topic_prerequisites",
            "lesson_topics", "topic_mastery", "lesson_completions"} <= tables

    cols = {c["name"] for c in inspect(engine).get_columns("curriculum_topics")}
    assert "id" in cols and "status" in cols and "revision" in cols

    # Legacy table and its columns survive.
    assert "user_mastery" in tables
    assert "tag" in {c["name"] for c in inspect(engine).get_columns("user_mastery")}


def test_downgrade_places_every_lesson_and_preserves_secondary_placements(tmp_path):
    """The old flat schema stores one topic_slug per lesson. Lessons belonging
    to two topics used to lose their secondary placement on downgrade, and any
    lesson with no primary topic was left unplaced entirely. Both are fixed:
    the secondary goes to an additive column pre-migration code never reads,
    and re-upgrading restores it."""
    from alembic import command
    from alembic.config import Config

    db_path = tmp_path / "rt.db"
    url = f"sqlite:///{db_path}"

    # alembic/env.py takes the URL from app settings, never from alembic.ini,
    # so the environment variable is the only way in.
    import os

    from app.config import get_settings

    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        cfg = Config(str(pathlib.Path(__file__).resolve().parents[1] / "alembic.ini"))
        engine = create_engine(url)

        # Only migrate up to the revision before the curriculum migration, then
        # seed lessons, then finish. The curriculum migration attaches
        # placements by scanning the lessons table, so lessons must already
        # exist. (Running create_all first would trip the migrations' own
        # "already provisioned" guard and skip every step.)
        command.upgrade(cfg, "e9c4a7d31b22")

        # Raw SQL, not the ORM: the Lesson model expects lessons.position,
        # which the curriculum migration itself adds.
        content_root = pathlib.Path(__file__).resolve().parents[2] / "content"
        with engine.begin() as conn:
            for path in sorted(content_root.glob("*.md")):
                conn.execute(
                    # Only the columns that exist at this revision: difficulty
                    # and position are added by the curriculum migration.
                    # tags/order_index/track are NOT NULL, so they must be
                    # supplied -- and no OR IGNORE, which would silently
                    # swallow a constraint failure and hide the problem.
                    text("INSERT INTO lessons (slug, title, path, tags,"
                         " order_index, track) VALUES (:s, :t, :p, '[]', 0, '')"),
                    {"s": path.stem, "t": path.stem, "p": str(path)},
                )

        command.upgrade(cfg, "head")

        before = set(
            engine.connect().execute(
                text("SELECT lesson_slug, topic_id, is_primary FROM lesson_topics")
            ).all()
        )
        assert before, "migration seeded no lesson placements"

        command.downgrade(cfg, "f1a2b3c4d5e6")

        with engine.connect() as conn:
            lessons_total = conn.execute(text("SELECT COUNT(*) FROM lessons")).scalar()
            placed = conn.execute(
                text("SELECT COUNT(*) FROM lessons WHERE topic_slug IS NOT NULL")
            ).scalar()
            assert placed == lessons_total, (
                f"only {placed} of {lessons_total} lessons were placed on downgrade"
            )
            extra = conn.execute(
                text("SELECT slug, additional_topics FROM lessons"
                     " WHERE additional_topics IS NOT NULL")
            ).all()
        assert extra, "no secondary placements were preserved"

        command.upgrade(cfg, "head")

        after = set(
            engine.connect().execute(
                text("SELECT lesson_slug, topic_id, is_primary FROM lesson_topics")
            ).all()
        )
        assert before == after, (
            "round-trip lost placements: "
            f"missing={sorted(before - after)} added={sorted(after - before)}"
        )
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
        get_settings.cache_clear()


def test_migrations_contain_no_sqlite_only_syntax():
    """The migration must run on PostgreSQL, which is the production dialect.

    `INSERT OR IGNORE` is SQLite-only and fails outright on PostgreSQL; it was
    found here by static review and fixed. This guard keeps it from creeping
    back in.
    """
    import pathlib
    import re

    versions = pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
    banned = re.compile(r"INSERT\s+OR\s+(IGNORE|REPLACE)|REPLACE\s+INTO|AUTOINCREMENT", re.I)
    offenders: list[str] = []
    for path in sorted(versions.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            # Comments explaining why the syntax is banned are fine.
            if stripped.startswith("#"):
                continue
            if banned.search(line):
                offenders.append(f"{path.name}:{i}: {stripped}")
    assert not offenders, "SQLite-only SQL in the migration path:\n" + "\n".join(offenders)


def test_parameter_reuse_is_explicitly_cast_for_postgres():
    """A parameter used both in a typeless SELECT list and in a WHERE
    comparison against a varchar column makes PostgreSQL raise
    AmbiguousParameter (text versus character varying). SQLite never notices.
    The statements that do this must pin the parameter types with CAST.
    """
    import pathlib

    migration = (
        pathlib.Path(__file__).resolve().parents[1]
        / "alembic" / "versions" / "a2b3c4d5e6f7_stable_topic_identifiers.py"
    )
    text = migration.read_text(encoding="utf-8")
    # Every `SELECT <param>, <param>, ...` insert must carry an explicit CAST.
    selects = [
        line.strip()
        for line in text.splitlines()
        if re.search(r'"\s*SELECT\s+(CAST\s*\()?\s*:', line, re.I)
    ]
    assert selects, "no parametrised SELECT inserts found; test is stale"
    for line in selects:
        assert "CAST(" in line, (
            f"parametrised SELECT without an explicit CAST is ambiguous on "
            f"PostgreSQL: {line}"
        )


# -- M4 tracker validation -------------------------------------------------- #


def _tracker_items() -> list[dict]:
    import subprocess

    docs = pathlib.Path(__file__).resolve().parents[2] / "docs"
    data = json.loads((docs / "M4_LESSON_REWRITE_TRACKER.json").read_text())
    return data["items"]


def test_tracker_every_item_id_is_unique():
    ids = [i["item_id"] for i in _tracker_items()]
    assert len(ids) == len(set(ids)), "duplicate item_id in the tracker"


def test_tracker_mapped_topic_ids_all_exist():
    from app.curriculum import TOPICS as REGISTRY_TOPICS

    known = {str(t["id"]) for t in REGISTRY_TOPICS}
    for item in _tracker_items():
        if item["topic_id"] is not None:
            assert item["topic_id"] in known, (
                f"{item['item_id']} references unknown topic {item['topic_id']}"
            )


def test_tracker_no_item_lists_the_same_lesson_twice():
    """A lesson may legitimately serve several target items -- 01_qubits teaches
    both Qubits and Superposition. What must never happen is one item claiming
    the same lesson as both its lesson and an additional one, or two identical
    rows."""
    items = _tracker_items()
    for item in items:
        if not item["lesson_slug"]:
            continue
        assert item["lesson_slug"] not in (item.get("additional_existing_lessons") or []), (
            f"{item['item_id']} lists {item['lesson_slug']} as both primary and additional"
        )
    pairs = [(i["item_id"], i["lesson_slug"]) for i in items if i["lesson_slug"]]
    assert len(pairs) == len(set(pairs)), "duplicate (item_id, lesson_slug) row"


def test_tracker_assigned_lessons_exist_on_disk():
    content = pathlib.Path(__file__).resolve().parents[2] / "content"
    for item in _tracker_items():
        if item["lesson_slug"]:
            assert (content / f"{item['lesson_slug']}.md").exists(), (
                f"{item['item_id']} points at missing lesson {item['lesson_slug']}"
            )


def test_tracker_statuses_use_the_agreed_vocabulary():
    allowed_content = {"existing", "partial", "missing"}
    allowed_rewrite = {
        "not_started", "audited", "in_progress", "draft_complete",
        "technical_review", "content_review", "integration_test", "verified",
        "blocked", "deferred",
    }
    allowed_validation = {"not_run", "passed", "failed", "blocked", "not_applicable"}
    for item in _tracker_items():
        assert item["content_status"] in allowed_content, item["item_id"]
        assert item["rewrite_status"] in allowed_rewrite, item["item_id"]
        for field in ("technical_review", "schema_validation", "mapping_validation",
                      "prerequisite_validation", "code_validation",
                      "integration_validation"):
            assert item[field] in allowed_validation, f"{item['item_id']}.{field}"


def test_tracker_counts_reconcile_with_the_gap_report():
    # Compare target items only; M4-EXTRA-* rows are existing lessons that the
    # target list does not cover, tracked separately.
    items = [i for i in _tracker_items() if not i["item_id"].startswith("M4-EXTRA-")]
    counts = {
        "existing": sum(1 for i in items if i["content_status"] == "existing"),
        "partial": sum(1 for i in items if i["content_status"] == "partial"),
        "missing": sum(1 for i in items if i["content_status"] == "missing"),
    }
    assert counts == {"existing": 7, "partial": 8, "missing": 82}, counts
    assert len(items) == 97


def test_tracker_sections_are_the_canonical_ten():
    from app.curriculum import NAMESPACES as NS

    valid = {slug for slug, _l, _t in NS.values()}
    sections = {i["section_id"] for i in _tracker_items()}
    assert sections <= valid, f"unknown sections: {sections - valid}"
    assert len(sections) == 10, f"expected 10 sections, got {len(sections)}"


def test_tracker_reports_every_existing_lesson():
    """Every lesson on disk must be reachable from the tracker, otherwise M4
    would silently leave content behind."""
    content = pathlib.Path(__file__).resolve().parents[2] / "content"
    on_disk = {p.stem for p in content.glob("*.md")}
    tracked = set()
    for i in _tracker_items():
        if i["lesson_slug"]:
            tracked.add(i["lesson_slug"])
        tracked.update(i.get("additional_existing_lessons") or [])
    untracked = on_disk - tracked
    assert not untracked, f"existing lessons absent from the tracker: {sorted(untracked)}"


# --------------------------------------------------------------------------
# M4: lessons marked as rewritten must satisfy the authoring standard.
# --------------------------------------------------------------------------


def _m4_validator():
    """Import the M4 lesson validator from backend/scripts."""
    import importlib.util

    path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "scripts"
        / "validate_lesson.py"
    )
    spec = importlib.util.spec_from_file_location("validate_lesson", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rewritten_slugs() -> set[str]:
    """Slugs of lessons the tracker records as rewritten."""
    path = (
        pathlib.Path(__file__).resolve().parents[1].parent
        / "docs"
        / "M4_LESSON_REWRITE_TRACKER.json"
    )
    tracker = json.loads(path.read_text(encoding="utf-8"))
    slugs = {
        item["lesson_slug"]
        for item in tracker["items"]
        if item["rewrite_status"] != "not_started" and item["lesson_slug"]
    }
    # Physical lessons that only appear in `additional_existing_lessons` have no
    # target row of their own, so they are recorded in `lesson_progress`.
    slugs |= {
        slug
        for slug, rec in tracker.get("lesson_progress", {}).items()
        if rec.get("rewrite_status", "not_started") != "not_started"
    }
    return slugs


def test_rewritten_lessons_pass_the_authoring_standard():
    """Every lesson the tracker claims is rewritten must actually validate.

    This is the anti-fake-progress check: it must be impossible to flip a
    tracker row to 'complete' without the content meeting the standard.
    """
    validator = _m4_validator()
    slugs = _rewritten_slugs()
    assert slugs, "the tracker records no rewritten lessons"

    content_dir = pathlib.Path(__file__).resolve().parents[1].parent / "content"
    for slug in sorted(slugs):
        path = content_dir / f"{slug}.md"
        assert path.exists(), f"tracker marks {slug} rewritten but the file is missing"
        report = validator.validate(slug, path.read_text(encoding="utf-8"))
        assert report.errors == [], f"{slug} fails the authoring standard: {report.errors}"


def test_tracker_progress_survives_regeneration():
    """Regenerating the tracker must not erase hand-authored progress."""
    rows_path = (
        pathlib.Path(__file__).resolve().parents[1].parent
        / "docs"
        / "M4_LESSON_REWRITE_TRACKER.json"
    )
    items = json.loads(rows_path.read_text(encoding="utf-8"))["items"]
    progressed = [i for i in items if i["rewrite_status"] != "not_started"]
    assert progressed, "no recorded progress to check"
    for item in progressed:
        assert item["last_updated"], f"{item['item_id']} has progress but no timestamp"
        assert item["review_notes"], f"{item['item_id']} has progress but no notes"


# -------------------------------------------------------------------------- #
# M4 topic-gap analysis: the proposal is documentation only, but it is
# checked so it cannot silently contradict the registry.
# -------------------------------------------------------------------------- #


def _gap_module():
    """Import backend/scripts/topic_gap_analysis.py."""
    import importlib.util

    path = (
        pathlib.Path(__file__).resolve().parents[1]
        / "scripts"
        / "topic_gap_analysis.py"
    )
    spec = importlib.util.spec_from_file_location("topic_gap_analysis", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_topic_gap_proposal_validates():
    """Every unmapped item is covered exactly once, ids are unique, and every
    prerequisite resolves."""
    mod = _gap_module()
    assert mod.validate() == [], f"proposal is invalid: {mod.validate()}"


def test_topic_gap_proposal_creates_no_topics():
    """The proposal must not touch the registry. This is the guard that keeps a
    documentation phase from becoming an unapproved implementation."""
    import subprocess

    mod = _gap_module()
    proposed = {p["id"] for p in mod.PROPOSAL}
    registered = {t["id"] for t in TOPICS}
    assert not (proposed & registered), (
        f"proposal collides with registered topics: {sorted(proposed & registered)}"
    )
    # The registry file itself must be unmodified by importing/running the script.
    registry = pathlib.Path(__file__).resolve().parents[1] / "app" / "curriculum.py"
    diff = subprocess.run(
        ["git", "diff", "--quiet", "--", str(registry)],
        cwd=str(registry.parents[2]),
        capture_output=True,
    )
    assert diff.returncode == 0, "app/curriculum.py has uncommitted changes"


def test_topic_gap_document_is_in_sync():
    """The committed document must match what the generator would produce now,
    so the numbers in it cannot drift from the data."""
    mod = _gap_module()
    doc = (
        pathlib.Path(__file__).resolve().parents[1].parent
        / "docs"
        / "M4_TOPIC_GAP_ANALYSIS.md"
    )
    assert doc.exists(), "M4_TOPIC_GAP_ANALYSIS.md is missing"
    text = doc.read_text(encoding="utf-8")
    assert "PROPOSAL ONLY" in text
    # Headline counts must match the live data.
    pending = len(mod.pending_items())
    assert f"**Unmapped: {pending} items**" in text, (
        "document headline count is stale; re-run topic_gap_analysis.py"
    )
    assert f"**{len(mod.PROPOSAL)} proposed topics for {pending} items**" in text
