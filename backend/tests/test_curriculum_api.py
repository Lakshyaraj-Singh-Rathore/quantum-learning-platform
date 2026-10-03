"""Tests for the curriculum service and its HTTP endpoints."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.curriculum import SECTIONS, TOPICS, all_prerequisites
from app.main import app
from app.models.content import Lesson
from app.models.curriculum import CurriculumSection, CurriculumTopic, TopicPrerequisite
from app.models.mastery import UserMastery
from app.models.user import User
from app.services.curriculum_service import (
    MASTERY_THRESHOLD,
    build_curriculum,
    evaluate_prerequisites,
    prerequisites_for,
    recommended_next,
    topic_mastery,
)


def _upsert(db: Session, model, slug: str, **fields):
    """Get-or-create by slug.

    ``db.merge`` cannot be used here: these rows are keyed by slug but the
    primary key is an integer id, so a transient object has no id to match on
    and merge falls through to INSERT, tripping the unique constraint.
    """
    row = db.scalar(select(model).where(model.slug == slug))
    if row is None:
        row = model(slug=slug, **fields)
        db.add(row)
        db.flush()
        return row
    for key, value in fields.items():
        setattr(row, key, value)
    db.flush()
    return row


@pytest.fixture()
def seeded(db: Session) -> Session:
    """Seed the curriculum hierarchy that the migration would have created."""
    for section in SECTIONS:
        _upsert(
            db,
            CurriculumSection,
            str(section["slug"]),
            title=str(section["title"]),
            position=int(section["position"]),
        )
    for topic in TOPICS:
        _upsert(
            db,
            CurriculumTopic,
            str(topic["slug"]),
            title=str(topic["title"]),
            section_slug=str(topic["section"]),
            position=int(topic["position"]),
            difficulty=str(topic["difficulty"]),
            summary=str(topic["summary"]),
            learning_objectives=list(topic["objectives"]),
        )

    db.query(TopicPrerequisite).delete()
    db.flush()
    for topic_slug, prereq, kind in all_prerequisites():
        db.add(
            TopicPrerequisite(topic_slug=topic_slug, prerequisite_slug=prereq, kind=kind)
        )

    for topic in TOPICS:
        for index, lesson_slug in enumerate(topic["lessons"]):
            lesson = db.scalar(select(Lesson).where(Lesson.slug == lesson_slug))
            if lesson is None:
                lesson = Lesson(slug=str(lesson_slug), title=str(lesson_slug), path="x.md")
                db.add(lesson)
                db.flush()
            lesson.topic_slug = str(topic["slug"])
            lesson.position = index
            lesson.difficulty = str(topic["difficulty"])
    db.commit()
    yield db
    # Leave the shared test database usable for other suites.
    db.query(TopicPrerequisite).delete()
    db.query(CurriculumTopic).delete()
    db.query(CurriculumSection).delete()
    db.commit()


@pytest.fixture()
def db():
    """A session bound to the same engine the app uses.

    Ensures the schema exists first. Tests that never request ``client`` do not
    start the app, and ``create_all`` only runs on startup, so without this the
    curriculum tables would be missing for service-level tests.
    """
    from app.database import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _user(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash="x", display_name="T", role="student")
        db.add(user)
        db.flush()
    return user


# --------------------------------------------------------------------------- #
# Service: mastery reading
# --------------------------------------------------------------------------- #


def test_mastery_reads_stamped_topic_slug(seeded: Session):
    user = _user(seeded, "stamped@example.com")
    seeded.add(
        UserMastery(user_id=user.id, tag="entanglement", topic_slug="entanglement",
                    score=0.8, attempts=2)
    )
    seeded.commit()
    m = topic_mastery(seeded, user.id)
    assert m["entanglement"]["score"] == pytest.approx(0.8)
    assert m["entanglement"]["attempts"] == 2


def test_mastery_falls_back_to_legacy_tag(seeded: Session):
    """A row written before the migration has no topic_slug. It must still
    count, otherwise existing progress disappears on upgrade."""
    user = _user(seeded, "legacy@example.com")
    seeded.add(UserMastery(user_id=user.id, tag="decoherence", score=0.5, attempts=1))
    seeded.commit()
    m = topic_mastery(seeded, user.id)
    assert m["quantum-noise"]["score"] == pytest.approx(0.5)


def test_mastery_ignores_unmappable_tags_without_dropping_them(seeded: Session):
    user = _user(seeded, "unmapped@example.com")
    seeded.add(UserMastery(user_id=user.id, tag="no-such-tag", score=0.9, attempts=4))
    seeded.commit()
    assert topic_mastery(seeded, user.id) == {}
    # The row survives; it is just not counted.
    assert seeded.scalar(
        select(UserMastery).where(UserMastery.tag == "no-such-tag")
    ).score == pytest.approx(0.9)


def test_mastery_averages_multiple_rows_for_one_topic(seeded: Session):
    user = _user(seeded, "avg@example.com")
    seeded.add(UserMastery(user_id=user.id, tag="noise", topic_slug="quantum-noise",
                           score=1.0, attempts=1))
    seeded.add(UserMastery(user_id=user.id, tag="decoherence", topic_slug="quantum-noise",
                           score=0.0, attempts=1))
    seeded.commit()
    assert topic_mastery(seeded, user.id)["quantum-noise"]["score"] == pytest.approx(0.5)


# --------------------------------------------------------------------------- #
# Service: prerequisite evaluation
# --------------------------------------------------------------------------- #


def test_required_prerequisite_blocks_but_recommended_does_not(seeded: Session):
    prereqs = prerequisites_for(seeded)
    # vqe-qaoa: quantum-noise required, grover recommended.
    blocked = evaluate_prerequisites("vqe-qaoa", prereqs, {})
    assert blocked["ready"] is False
    assert "quantum-noise" in blocked["missing_required"]
    assert "grover" in blocked["missing_recommended"]

    # Only the required one satisfied: still advisory, not ready.
    partial = evaluate_prerequisites(
        "vqe-qaoa", prereqs, {"quantum-noise": {"score": 0.9}}
    )
    assert partial["ready"] is True
    assert partial["advisory"] is True

    # Both satisfied.
    full = evaluate_prerequisites(
        "vqe-qaoa",
        prereqs,
        {"quantum-noise": {"score": 0.9}, "grover": {"score": 0.9}},
    )
    assert full["ready"] is True
    assert full["advisory"] is False


def test_mastery_threshold_is_the_gate(seeded: Session):
    prereqs = prerequisites_for(seeded)
    just_under = evaluate_prerequisites(
        "vqe-qaoa", prereqs, {"quantum-noise": {"score": MASTERY_THRESHOLD - 0.01}}
    )
    just_over = evaluate_prerequisites(
        "vqe-qaoa", prereqs, {"quantum-noise": {"score": MASTERY_THRESHOLD}}
    )
    assert just_under["ready"] is False
    assert just_over["ready"] is True


def test_topic_with_no_prerequisites_is_ready(seeded: Session):
    prereqs = prerequisites_for(seeded)
    assert evaluate_prerequisites("classical-vs-qubit", prereqs, {})["ready"] is True


# --------------------------------------------------------------------------- #
# Service: hierarchy assembly
# --------------------------------------------------------------------------- #


def test_anonymous_gets_structure_with_no_locks(seeded: Session):
    """A visitor has no history, so nothing may be gated: gating them would
    make the curriculum a dead end."""
    tree = build_curriculum(seeded, None)
    assert tree["sections"]
    for section in tree["sections"]:
        for topic in section["topics"]:
            assert topic["mastery"] == 0.0
            assert topic["completed"] is False
            assert topic["status"]["ready"] is True


def test_empty_sections_are_omitted(seeded: Session):
    """Seven of ten sections have no content yet. Emitting them would put
    unopenable entries in the learner's navigation."""
    tree = build_curriculum(seeded, None)
    slugs = {s["slug"] for s in tree["sections"]}
    assert "mathematical-foundations" not in slugs
    assert "error-correction" not in slugs
    assert slugs == {
        "core-quantum-theory",
        "intro-quantum-computing",
        "quantum-algorithms",
        "advanced-theory-circuits",
        "variational-nisq",
    }


def test_sections_and_topics_are_ordered(seeded: Session):
    tree = build_curriculum(seeded, None)
    positions = [s["position"] for s in tree["sections"]]
    assert positions == sorted(positions)
    for section in tree["sections"]:
        tpos = [t["position"] for t in section["topics"]]
        assert tpos == sorted(tpos)


def test_lessons_appear_under_their_topic(seeded: Session):
    tree = build_curriculum(seeded, None)
    by_slug = {
        t["slug"]: t for s in tree["sections"] for t in s["topics"]
    }
    assert [l["slug"] for l in by_slug["quantum-gates"]["lessons"]] == [
        "02_gates",
        "10_gates_bootcamp",
    ]
    assert [l["slug"] for l in by_slug["vqe-qaoa"]["lessons"]] == ["07_vqe_qaoa"]


def test_progress_percent_reflects_mastery(seeded: Session):
    user = _user(seeded, "pct@example.com")
    tree_before = build_curriculum(seeded, user.id)
    assert tree_before["progress"]["topics_completed"] == 0

    seeded.add(UserMastery(user_id=user.id, tag="qubit", topic_slug="qubits",
                           score=1.0, attempts=1))
    seeded.commit()
    tree_after = build_curriculum(seeded, user.id)
    assert tree_after["progress"]["topics_completed"] == 1
    assert tree_after["progress"]["percent"] > 0


def test_recommended_next_prefers_ready_topics(seeded: Session):
    user = _user(seeded, "next@example.com")
    seeded.add(UserMastery(user_id=user.id, tag="qubit", topic_slug="qubits",
                           score=1.0, attempts=1))
    seeded.commit()
    nxt = recommended_next(seeded, user.id, limit=3)
    slugs = [n["slug"] for n in nxt]
    assert "qubits" not in slugs  # already complete
    assert nxt


def test_recommended_next_never_empty_for_a_fresh_learner(seeded: Session):
    user = _user(seeded, "fresh@example.com")
    assert recommended_next(seeded, user.id, limit=3)


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #


def test_get_curriculum_is_readable_anonymously(client, seeded):
    r = client.get("/curriculum")
    assert r.status_code == 200
    body = r.json()
    assert body["sections"]
    assert "progress" in body


def test_get_curriculum_rejects_unknown_topic(client, seeded):
    assert client.get("/curriculum/topics/not-a-topic").status_code == 404


def test_topic_detail_exposes_prerequisites(client, seeded):
    r = client.get("/curriculum/topics/vqe-qaoa")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "vqe-qaoa"
    kinds = {p["slug"]: p["kind"] for p in body["prerequisites"]}
    assert kinds["quantum-noise"] == "required"
    assert kinds["grover"] == "recommended"
    # Anonymous: the declared edges are visible, but nothing is gated, because
    # there is no mastery to gate on.
    assert body["status"]["ready"] is True
    assert body["status"]["unevaluated"] is True


def test_topic_detail_gates_an_authenticated_learner(client, seeded, db: Session):
    """The anonymous exemption must not leak to a learner with real history.

    This is the counterpart to test_topic_detail_exposes_prerequisites: an
    anonymous visitor is never gated, but a learner who has not covered
    quantum-noise genuinely should be.
    """
    user = _user(db, "gated@example.com")
    db.commit()
    from app.security import create_access_token

    token = create_access_token(str(user.id), user.role)
    r = client.get(
        "/curriculum/topics/vqe-qaoa", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"]["ready"] is False
    assert "quantum-noise" in body["status"]["missing_required"]
    assert "grover" in body["status"]["missing_recommended"]


def test_next_endpoint_works_anonymously(client, seeded):
    r = client.get("/curriculum/next")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_next_endpoint_respects_limit(client, seeded):
    assert len(client.get("/curriculum/next?limit=2").json()) <= 2


def test_no_duplicate_lessons_across_topics(client, seeded):
    """A lesson claimed by two topics would appear twice in navigation."""
    body = client.get("/curriculum").json()
    seen = [l["slug"] for s in body["sections"] for t in s["topics"] for l in t["lessons"]]
    assert len(seen) == len(set(seen))
