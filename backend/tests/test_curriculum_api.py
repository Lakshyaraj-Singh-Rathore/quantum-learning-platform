"""Tests for the curriculum service and its HTTP endpoints.

Targets the stable namespaced topic identifiers and the split between
topic mastery and lesson completion.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.curriculum import (
    MASTERY_MAPPABLE_CONFIDENCE,
    NAMESPACES,
    SECTIONS,
    TOPICS,
    all_lesson_topics,
    all_prerequisites,
)
from app.main import app
from app.models.content import Lesson
from app.models.curriculum import (
    CurriculumSection,
    CurriculumTopic,
    LessonCompletion,
    LessonTopic,
    TopicMastery,
    TopicPrerequisite,
)
from app.models.user import User
from app.security import create_access_token
from app.services.curriculum_service import (
    MASTERY_THRESHOLD,
    build_curriculum,
    evaluate_prerequisites,
    prerequisites_for,
    recommended_next,
    topic_mastery,
)


@pytest.fixture()
def db():
    """A session bound to the same engine the app uses.

    Ensures the schema exists first: tests that never request ``client`` do not
    start the app, and ``create_all`` only runs on startup.
    """
    from app.database import SessionLocal, init_db

    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _seed_registry(db: Session) -> None:
    for section in SECTIONS:
        _upsert(
            db,
            CurriculumSection,
            "slug",
            str(section["slug"]),
            letter=str(section["letter"]),
            title=str(section["title"]),
            position=int(section["position"]),
        )
    for topic in TOPICS:
        _upsert(
            db,
            CurriculumTopic,
            "id",
            str(topic["id"]),
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
    db.query(LessonTopic).delete()
    db.query(TopicPrerequisite).delete()
    db.flush()
    for topic_id, prereq, kind in all_prerequisites():
        db.add(TopicPrerequisite(topic_id=topic_id, prerequisite_id=prereq, kind=kind))
    for slug, topic_id, confidence, is_primary in all_lesson_topics():
        lesson = db.scalar(select(Lesson).where(Lesson.slug == slug))
        if lesson is None:
            lesson = Lesson(slug=slug, title=slug, path="x.md")
            db.add(lesson)
            db.flush()
        db.add(
            LessonTopic(
                lesson_slug=slug,
                topic_id=topic_id,
                confidence=confidence,
                is_primary=1 if is_primary else 0,
            )
        )
    db.commit()


def _upsert(db: Session, model, pk_field: str, pk: str, **fields):
    """Get-or-create by an explicit key column.

    The primary key is not uniform across these models: CurriculumSection uses
    an integer ``id`` while CurriculumTopic uses the namespaced id string as
    its primary key. So the lookup column is passed in rather than inferred.
    """
    row = db.scalar(select(model).where(getattr(model, pk_field) == pk))
    if row is None:
        row = model(**{pk_field: pk}, **fields)
        db.add(row)
        db.flush()
        return row
    for key, value in fields.items():
        setattr(row, key, value)
    db.flush()
    return row


@pytest.fixture()
def seeded(db: Session) -> Session:
    _seed_registry(db)
    yield db
    db.query(TopicMastery).delete()
    db.query(LessonCompletion).delete()
    db.commit()


def _user(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash="x", display_name="T", role="student")
        db.add(user)
        db.flush()
        db.commit()
    return user


# --------------------------------------------------------------------------- #
# Mastery reading
# --------------------------------------------------------------------------- #


def test_mastery_counts_mapped_and_verified(seeded: Session):
    user = _user(seeded, "mv@example.com")
    seeded.add(
        TopicMastery(user_id=user.id, topic_id="qc.entanglement",
                     mastery_level=0.8, status="mapped", source="migration")
    )
    seeded.add(
        TopicMastery(user_id=user.id, topic_id="qc.qubits",
                     mastery_level=1.0, status="verified", source="quiz:basics")
    )
    seeded.commit()
    m = topic_mastery(seeded, user.id)
    assert m["qc.entanglement"]["score"] == pytest.approx(0.8)
    assert m["qc.qubits"]["score"] == pytest.approx(1.0)


def test_malformed_evidence_does_not_take_down_the_page(seeded: Session):
    """Regression: one row whose evidence is a JSON string rather than an
    object raised AttributeError inside topic_mastery, which returned a 500
    for /curriculum for every learner. An odd value must cost an attempt
    count, not the page.
    """
    from app.services.curriculum_service import _evidence_attempts

    # Direct unit checks on the coercion helper.
    assert _evidence_attempts(None) == 0
    assert _evidence_attempts("not json") == 0
    assert _evidence_attempts(42) == 0
    assert _evidence_attempts({"attempts": 3}) == 3
    assert _evidence_attempts('{"attempts": 5}') == 5
    assert _evidence_attempts({"attempts": None}) == 0

    # And end to end through the service, with a string-typed row present.
    user = _user(seeded, "malformed@example.com")
    seeded.add(TopicMastery(
        user_id=user.id, topic_id="qc.qubits", mastery_level=0.9,
        status="verified", source="quiz:basics", evidence='{"attempts": 2}',
    ))
    seeded.add(TopicMastery(
        user_id=user.id, topic_id="qc.entanglement", mastery_level=0.7,
        status="verified", source="quiz:other", evidence={"attempts": 4},
    ))
    seeded.commit()
    m = topic_mastery(seeded, user.id)
    # Both rows still count; neither crashes.
    assert m["qc.qubits"]["score"] == pytest.approx(0.9)
    assert m["qc.entanglement"]["score"] == pytest.approx(0.7)


def test_legacy_only_mastery_is_preserved_but_not_counted(seeded: Session):
    """An ambiguous legacy record must not silently satisfy a prerequisite."""
    user = _user(seeded, "lo@example.com")
    seeded.add(
        TopicMastery(user_id=user.id, topic_id="qiskit.quantum_noise",
                     mastery_level=1.0, status="legacy_only", source="migration")
    )
    seeded.commit()
    assert topic_mastery(seeded, user.id) == {}
    # Still in the table for audit.
    assert seeded.scalar(select(TopicMastery).where(
        TopicMastery.status == "legacy_only")) is not None


def test_confidence_gate_only_allows_high(seeded: Session):
    assert MASTERY_MAPPABLE_CONFIDENCE == ("high",)


# --------------------------------------------------------------------------- #
# Prerequisites
# --------------------------------------------------------------------------- #


def test_required_blocks_recommended_warns(seeded: Session):
    prereqs = prerequisites_for(seeded)
    blocked = evaluate_prerequisites("nisq.vqe", prereqs, {})
    assert blocked["ready"] is False
    assert "qiskit.quantum_noise" in blocked["missing_required"]
    assert "algo.grover" in blocked["missing_recommended"]

    partial = evaluate_prerequisites(
        "nisq.vqe", prereqs, {"qiskit.quantum_noise": {"score": 0.9}}
    )
    assert partial["ready"] is True and partial["advisory"] is True


def test_threshold_is_the_gate(seeded: Session):
    prereqs = prerequisites_for(seeded)
    under = evaluate_prerequisites(
        "nisq.vqe", prereqs, {"qiskit.quantum_noise": {"score": MASTERY_THRESHOLD - 0.01}}
    )
    over = evaluate_prerequisites(
        "nisq.vqe", prereqs, {"qiskit.quantum_noise": {"score": MASTERY_THRESHOLD}}
    )
    assert under["ready"] is False and over["ready"] is True


def test_legacy_only_does_not_unlock(seeded: Session):
    """Regression guard: the whole point of the status split."""
    from app.services.curriculum_service import topic_mastery as _tm

    user = _user(seeded, "unlock@example.com")
    seeded.add(
        TopicMastery(user_id=user.id, topic_id="qiskit.quantum_noise",
                     mastery_level=1.0, status="legacy_only", source="migration")
    )
    seeded.commit()
    prereqs = prerequisites_for(seeded)
    status = evaluate_prerequisites("nisq.vqe", prereqs, _tm(seeded, user.id))
    assert status["ready"] is False


# --------------------------------------------------------------------------- #
# Hierarchy
# --------------------------------------------------------------------------- #


def test_anonymous_is_never_gated(seeded: Session):
    tree = build_curriculum(seeded, None)
    for section in tree["sections"]:
        for topic in section["topics"]:
            assert topic["mastery"] == 0.0
            assert topic["status"]["ready"] is True


def test_only_published_topics_reach_learners(seeded: Session):
    tree = build_curriculum(seeded, None)
    published = {str(t["id"]) for t in TOPICS if t["status"] == "published"}
    shown = {t["slug"] for s in tree["sections"] for t in s["topics"]}
    assert shown == published


def test_empty_sections_omitted(seeded: Session):
    tree = build_curriculum(seeded, None)
    slugs = {s["slug"] for s in tree["sections"]}
    assert "mathematical-foundations" not in slugs
    assert "error-correction" not in slugs


def test_ordering(seeded: Session):
    tree = build_curriculum(seeded, None)
    assert [s["position"] for s in tree["sections"]] == sorted(
        s["position"] for s in tree["sections"]
    )
    for section in tree["sections"]:
        pos = [t["position"] for t in section["topics"]]
        assert pos == sorted(pos)


def test_lesson_appears_under_every_topic_it_teaches(seeded: Session):
    """Many-to-many: a lesson teaching several topics is reachable from each."""
    tree = build_curriculum(seeded, None)
    by_id = {t["slug"]: t for s in tree["sections"] for t in s["topics"]}
    assert "01_qubits" in [l["slug"] for l in by_id["qc.qubits"]["lessons"]]
    assert "01_qubits" in [l["slug"] for l in by_id["qc.superposition"]["lessons"]]
    assert [l["slug"] for l in by_id["qc.basic_gates"]["lessons"]] == [
        "02_gates",
        "10_gates_bootcamp",
    ]


def test_no_duplicate_lessons_within_a_topic(seeded: Session):
    tree = build_curriculum(seeded, None)
    for section in tree["sections"]:
        for topic in section["topics"]:
            slugs = [l["slug"] for l in topic["lessons"]]
            assert len(slugs) == len(set(slugs)), f"{topic['slug']} duplicates a lesson"


def test_recommended_next(seeded: Session):
    user = _user(seeded, "nx@example.com")
    seeded.add(
        TopicMastery(user_id=user.id, topic_id="qc.qubits",
                     mastery_level=1.0, status="verified", source="quiz:basics")
    )
    seeded.commit()
    slugs = [n["slug"] for n in recommended_next(seeded, user.id, limit=3)]
    assert "qc.qubits" not in slugs
    assert slugs


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #


def test_get_curriculum_anonymous(client, seeded):
    r = client.get("/curriculum")
    assert r.status_code == 200
    assert r.json()["sections"]


def test_topic_404(client, seeded):
    assert client.get("/curriculum/topics/nope.nope").status_code == 404


def test_topic_detail_namespaced_id(client, seeded):
    r = client.get("/curriculum/topics/nisq.vqe")
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "nisq.vqe"
    kinds = {p["slug"]: p["kind"] for p in body["prerequisites"]}
    assert kinds["qiskit.quantum_noise"] == "required"
    assert kinds["algo.grover"] == "recommended"
    assert body["status"]["ready"] is True  # anonymous: not gated
    assert body["status"]["unevaluated"] is True


def test_topic_detail_gates_authenticated_learner(client, seeded, db: Session):
    user = _user(db, "gate2@example.com")
    db.commit()
    token = create_access_token(str(user.id), user.role)
    r = client.get(
        "/curriculum/topics/nisq.vqe", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["status"]["ready"] is False
    assert "qiskit.quantum_noise" in r.json()["status"]["missing_required"]


def test_topic_detail_includes_lessons_in_sequence(client, seeded):
    """Additive field: the detail view shows lessons without a second call."""
    r = client.get("/curriculum/topics/qc.basic_gates")
    assert r.status_code == 200
    lessons = r.json()["lessons"]
    assert [l["slug"] for l in lessons] == ["02_gates", "10_gates_bootcamp"]
    # Primary first, and the primary flag is exposed.
    assert lessons[0]["is_primary"] is True


def test_topic_detail_lessons_empty_for_topic_without_lessons(client, seeded):
    """A published topic always has lessons today; assert the field exists and
    is a list so a future content-less topic degrades rather than 500s."""
    r = client.get("/curriculum/topics/nisq.vqe")
    assert r.status_code == 200
    assert isinstance(r.json()["lessons"], list)


def test_next_exposes_a_resume_lesson_slug(client, seeded):
    """Resume must open a lesson, so /next has to say which one."""
    body = client.get("/curriculum/next").json()
    assert body
    for entry in body:
        assert "lesson_slug" in entry
    # Every returned topic has content today, so a real slug is expected.
    assert all(e["lesson_slug"] for e in body)


def test_next_lesson_slug_points_at_a_real_lesson(client, seeded):
    slugs = {l["slug"] for l in client.get("/lessons").json()}
    for entry in client.get("/curriculum/next").json():
        if entry["lesson_slug"]:
            assert entry["lesson_slug"] in slugs, f"{entry['lesson_slug']} is not a lesson"


def test_next_endpoint(client, seeded):
    assert client.get("/curriculum/next").status_code == 200
    assert len(client.get("/curriculum/next?limit=2").json()) <= 2
