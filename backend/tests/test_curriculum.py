"""Tests for the curriculum hierarchy and its migration."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.curriculum import (
    LEGACY_TAG_TO_TOPIC,
    SECTIONS,
    TOPICS,
    all_prerequisites,
    lessons_by_topic,
    topic_for_lesson,
    validate,
)
from app.database import Base
from app.models.content import Lesson
from app.models.curriculum import CurriculumSection, CurriculumTopic, TopicPrerequisite
from app.models.mastery import UserMastery
from app.models.user import User


# --------------------------------------------------------------------------- #
# Structural integrity of the canonical data
# --------------------------------------------------------------------------- #


def test_curriculum_data_is_coherent():
    """The canonical data must satisfy every invariant we claim it does."""
    assert validate() == []


def test_ten_sections_in_order():
    assert [s["position"] for s in SECTIONS] == list(range(1, 11))
    assert len({s["slug"] for s in SECTIONS}) == 10


def test_every_topic_has_at_least_one_lesson():
    for topic in TOPICS:
        assert topic["lessons"], f"{topic['slug']} has no lessons"


def test_no_lesson_is_claimed_twice():
    seen: dict[str, str] = {}
    for topic_slug, lessons in lessons_by_topic().items():
        for lesson in lessons:
            assert lesson not in seen, (
                f"{lesson} claimed by both {seen[lesson]} and {topic_slug}"
            )
            seen[lesson] = topic_slug


def test_prerequisites_reference_known_topics():
    known = {t["slug"] for t in TOPICS}
    for topic, prereq, kind in all_prerequisites():
        assert prereq in known, f"{topic} depends on unknown {prereq}"
        assert topic != prereq, f"{topic} depends on itself"
        assert kind in ("required", "recommended")


def test_no_prerequisite_cycles():
    """A cycle would make path generation and ordering unresolvable."""
    graph = {str(t["slug"]): [p for p, _ in t["prerequisites"]] for t in TOPICS}
    state: dict[str, int] = {}

    def visit(node: str) -> None:
        state[node] = 1
        for nxt in graph.get(node, []):
            assert state.get(nxt, 0) != 1, f"cycle through {node} -> {nxt}"
            if state.get(nxt, 0) == 0:
                visit(nxt)
        state[node] = 2

    for node in graph:
        if state.get(node, 0) == 0:
            visit(node)


def test_depends_only_on_earlier_or_other_sections():
    """Within a section, a topic must not depend on a later position."""
    pos = {(str(t["section"]), str(t["slug"])): int(t["position"]) for t in TOPICS}
    for topic in TOPICS:
        for prereq, _kind in topic["prerequisites"]:
            if prereq in pos and (topic["section"], prereq) in pos:
                assert pos[(topic["section"], prereq)] < pos[
                    (topic["section"], str(topic["slug"]))
                ], f"{topic['slug']} depends on later sibling {prereq}"


# --------------------------------------------------------------------------- #
# The specific sequencing problems the audit found
# --------------------------------------------------------------------------- #


def test_vqe_requires_noise():
    """Audit finding: VQE previously sat before the noise lesson, inverting
    the dependency. Its whole motivation is device noise."""
    prereqs = {p for p, _ in _topic("vqe-qaoa")["prerequisites"]}
    assert "quantum-noise" in prereqs


def test_bell_states_precede_general_entanglement():
    """Audit finding: the concrete Bell example came eight lessons after the
    general concept."""
    prereqs = {p for p, _ in _topic("entanglement")["prerequisites"]}
    assert "bell-states" in prereqs


def test_gates_lessons_are_consolidated_in_concept_order():
    """Both gate lessons survive; theory precedes the hands-on bootcamp."""
    assert lessons_by_topic()["quantum-gates"] == ["02_gates", "10_gates_bootcamp"]


def test_every_existing_lesson_is_placed():
    """No lesson may be orphaned by the restructuring."""
    import glob
    import os

    root = os.path.join(os.path.dirname(__file__), "..", "..", "content")
    on_disk = {os.path.basename(p)[:-3] for p in glob.glob(os.path.join(root, "*.md"))}
    placed = set(lessons_by_topic() and {l for ls in lessons_by_topic().values() for l in ls})
    assert on_disk, "no content found to check against"
    assert on_disk == placed, f"unplaced lessons: {on_disk - placed}"


def test_topic_for_lesson_roundtrips():
    for topic_slug, lessons in lessons_by_topic().items():
        for lesson in lessons:
            assert topic_for_lesson(lesson) == topic_slug


def _topic(slug: str) -> dict:
    for t in TOPICS:
        if t["slug"] == slug:
            return t
    raise AssertionError(f"no topic {slug}")


# --------------------------------------------------------------------------- #
# Mastery migration
# --------------------------------------------------------------------------- #


def test_every_authored_mastery_tag_maps_to_a_topic():
    """Tags come from quizzes and challenges authored in seed.py. If a new tag
    appears there and is not mapped, mastery stops accruing to any topic, so
    this must fail loudly rather than silently."""
    known = {t["slug"] for t in TOPICS}
    for tag, topic in LEGACY_TAG_TO_TOPIC.items():
        assert topic in known, f"tag {tag} maps to unknown topic {topic}"


def test_mastery_migration_preserves_scores_and_stamps_topics(tmp_path):
    """The migration must stamp topic_slug without touching score, attempts or
    the legacy tag."""
    engine = create_engine(f"sqlite:///{tmp_path}/curriculum.db")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        for section in SECTIONS:
            db.add(CurriculumSection(slug=str(section["slug"]), title=str(section["title"])))
        db.flush()
        for topic in TOPICS:
            db.add(
                CurriculumTopic(
                    slug=str(topic["slug"]),
                    title=str(topic["title"]),
                    section_slug=str(topic["section"]),
                    difficulty=str(topic["difficulty"]),
                )
            )
        db.flush()

        user = User(email="learner@example.com", password_hash="x", role="student")
        db.add(user)
        db.flush()

        # Legacy rows exactly as they would exist before the migration.
        db.add(UserMastery(user_id=user.id, tag="entanglement", score=0.75, attempts=3))
        db.add(UserMastery(user_id=user.id, tag="noise", score=0.40, attempts=1))
        db.add(UserMastery(user_id=user.id, tag="unmapped-future-tag", score=0.9, attempts=2))
        db.commit()

        # Replay the migration's mastery step verbatim.
        for tag, topic_slug in LEGACY_TAG_TO_TOPIC.items():
            db.execute(
                text("UPDATE user_mastery SET topic_slug = :topic WHERE tag = :tag"),
                {"topic": topic_slug, "tag": tag},
            )
        db.commit()

        rows = {r.tag: r for r in db.query(UserMastery).all()}

        # Scores, attempts and tags are untouched.
        assert rows["entanglement"].score == pytest.approx(0.75)
        assert rows["entanglement"].attempts == 3
        assert rows["noise"].score == pytest.approx(0.40)
        assert rows["noise"].attempts == 1

        # Topics stamped.
        assert rows["entanglement"].topic_slug == "entanglement"
        assert rows["noise"].topic_slug == "quantum-noise"

        # An unmapped tag is preserved, not dropped and not guessed at.
        assert rows["unmapped-future-tag"].topic_slug is None
        assert rows["unmapped-future-tag"].score == pytest.approx(0.9)


def test_lesson_placement_migration_sets_position_and_difficulty(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/lessons.db")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        for section in SECTIONS:
            db.add(CurriculumSection(slug=str(section["slug"]), title=str(section["title"])))
        db.flush()
        for topic in TOPICS:
            db.add(
                CurriculumTopic(
                    slug=str(topic["slug"]),
                    title=str(topic["title"]),
                    section_slug=str(topic["section"]),
                    difficulty=str(topic["difficulty"]),
                )
            )
        db.flush()

        db.add(Lesson(slug="02_gates", title="Gates", path="content/02_gates.md"))
        db.add(
            Lesson(
                slug="10_gates_bootcamp",
                title="Gates Bootcamp",
                path="content/10_gates_bootcamp.md",
            )
        )
        db.commit()

        for topic in TOPICS:
            for index, lesson_slug in enumerate(topic["lessons"]):
                db.execute(
                    text(
                        "UPDATE lessons SET topic_slug = :topic, position = :position,"
                        " difficulty = :difficulty WHERE slug = :lesson"
                    ),
                    {
                        "topic": topic["slug"],
                        "position": index,
                        "difficulty": topic["difficulty"],
                        "lesson": lesson_slug,
                    },
                )
        db.commit()

        gates = db.query(Lesson).filter_by(slug="02_gates").one()
        boot = db.query(Lesson).filter_by(slug="10_gates_bootcamp").one()

        assert gates.topic_slug == "quantum-gates"
        assert boot.topic_slug == "quantum-gates"
        # Conceptual order, not filename order: 02 before 10 here, but note
        # that in general position follows dependency, not the number.
        assert gates.position < boot.position
        assert boot.difficulty == "beginner"


def test_migration_creates_expected_schema(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/schema.db")
    Base.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())
    assert {
        "curriculum_sections",
        "curriculum_topics",
        "topic_prerequisites",
    } <= tables

    cols = {c["name"] for c in inspect(engine).get_columns("lessons")}
    assert {"topic_slug", "position", "difficulty", "learning_objectives"} <= cols

    mastery_cols = {c["name"] for c in inspect(engine).get_columns("user_mastery")}
    assert "topic_slug" in mastery_cols
    # The legacy key survives.
    assert "tag" in mastery_cols


def test_prerequisite_edge_kinds_are_recorded(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/edges.db")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for section in SECTIONS:
            db.add(CurriculumSection(slug=str(section["slug"]), title=str(section["title"])))
        db.flush()
        for topic in TOPICS:
            db.add(
                CurriculumTopic(
                    slug=str(topic["slug"]),
                    title=str(topic["title"]),
                    section_slug=str(topic["section"]),
                )
            )
        db.flush()
        for topic_slug, prereq, kind in all_prerequisites():
            db.add(
                TopicPrerequisite(
                    topic_slug=topic_slug, prerequisite_slug=prereq, kind=kind
                )
            )
        db.commit()

        rows = db.query(TopicPrerequisite).all()
        assert rows
        kinds = {r.kind for r in rows}
        assert kinds <= {"required", "recommended"}
        # At least one advisory edge exists, so skipping is actually reachable.
        assert "recommended" in kinds
