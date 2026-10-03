"""Reading the curriculum hierarchy, with progress and prerequisite state.

Kept separate from the API layer so the rules below can be tested without
standing up the app, and so the eventual UI and the recommendations service
share one implementation of "is this learner ready for this topic".
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.content import Lesson
from app.models.curriculum import (
    CurriculumSection,
    CurriculumTopic,
    LessonTopic,
    TopicMastery,
    TopicPrerequisite,
)

#: Mastery at or above this counts as having covered a topic.
MASTERY_THRESHOLD = 0.6


def topic_mastery(db: Session, user_id: int) -> dict[str, dict[str, float]]:
    """Return ``{topic_id: {score, attempts}}`` for a learner.

    Reads the dedicated ``topic_mastery`` table, which the migration populated
    from legacy tag rows. Only rows with status ``mapped`` or ``verified``
    count; ``legacy_only`` rows are preserved for audit but never counted and
    never satisfy a prerequisite.

    Unmapped legacy tags remain in ``user_mastery`` and are readable there.
    Nothing here derives mastery from lesson text.
    """
    rows = db.scalars(
        select(TopicMastery).where(
            TopicMastery.user_id == user_id,
            TopicMastery.status.in_(("mapped", "verified")),
        )
    ).all()

    totals: dict[str, list[float]] = {}
    attempts: dict[str, int] = {}
    for row in rows:
        totals.setdefault(row.topic_id, []).append(float(row.mastery_level))
        evidence = row.evidence or {}
        attempts[row.topic_id] = attempts.get(row.topic_id, 0) + int(
            evidence.get("attempts") or 0
        )

    return {
        topic: {
            "score": round(sum(scores) / len(scores), 3),
            "attempts": attempts.get(topic, 0),
        }
        for topic, scores in totals.items()
    }


def prerequisites_for(db: Session) -> dict[str, list[dict[str, str]]]:
    """Return ``{topic_slug: [{slug, kind}, ...]}`` from the dependency graph."""
    edges = db.scalars(select(TopicPrerequisite)).all()
    out: dict[str, list[dict[str, str]]] = {}
    for edge in edges:
        out.setdefault(edge.topic_id, []).append(
            {"slug": edge.prerequisite_id, "kind": edge.kind}
        )
    return out


def evaluate_prerequisites(
    topic_slug: str,
    prereqs: dict[str, list[dict[str, str]]],
    mastery: dict[str, dict[str, float]],
) -> dict[str, object]:
    """Decide whether a learner is ready for a topic.

    Returns the unmet prerequisites split by kind, plus a readiness flag.
    ``required`` unmet prerequisites block; ``recommended`` ones only warn.
    Diagnostic-based skipping is out of scope here -- it needs an assessment
    record to point at -- but the split is what the UI needs to offer it.
    """
    required_missing: list[str] = []
    recommended_missing: list[str] = []

    for edge in prereqs.get(topic_slug, []):
        score = mastery.get(edge["slug"], {}).get("score", 0.0)
        if score >= MASTERY_THRESHOLD:
            continue
        if edge["kind"] == "required":
            required_missing.append(edge["slug"])
        else:
            recommended_missing.append(edge["slug"])

    return {
        "ready": not required_missing,
        "missing_required": required_missing,
        "missing_recommended": recommended_missing,
        "advisory": bool(recommended_missing) and not required_missing,
    }


def build_curriculum(db: Session, user_id: int | None) -> dict[str, object]:
    """Assemble the full section -> topic -> lesson hierarchy.

    Works for anonymous learners: with no ``user_id`` every topic reports no
    progress and nothing is locked, because gating a visitor on progress they
    have not had a chance to make would just be a dead end.
    """
    mastery = topic_mastery(db, user_id) if user_id is not None else {}
    prereqs = prerequisites_for(db)

    sections = db.scalars(
        select(CurriculumSection).order_by(CurriculumSection.position)
    ).all()
    topics = db.scalars(
        select(CurriculumTopic).order_by(CurriculumTopic.position)
    ).all()
    lessons = db.scalars(select(Lesson).order_by(Lesson.position)).all()
    lesson_meta = {lesson.slug: lesson for lesson in lessons}

    links = db.scalars(
        select(LessonTopic).order_by(LessonTopic.is_primary.desc(), LessonTopic.id)
    ).all()

    lessons_by_topic: dict[str, list[dict[str, object]]] = {}
    for link in links:
        lesson = lesson_meta.get(link.lesson_slug)
        if lesson is None:
            continue
        lessons_by_topic.setdefault(link.topic_id, []).append(
            {
                "slug": lesson.slug,
                "title": lesson.title,
                "track": lesson.track,
                "position": lesson.position,
                "is_primary": bool(link.is_primary),
                "confidence": link.confidence,
            }
        )

    sections_out: list[dict[str, object]] = []
    for section in sections:
        topics_out: list[dict[str, object]] = []
        for topic in topics:
            if topic.section_slug != section.slug:
                continue
            # Prerequisite gating is only meaningful once there is mastery to
            # gate on. For an anonymous visitor every required edge is "unmet"
            # by definition, and reporting that would lock most of the
            # curriculum behind data the visitor has not had a chance to
            # produce. So: no gating, but the declared edges are still returned
            # so the dependency structure stays visible for browsing.
            if user_id is None:
                status = {
                    "ready": True,
                    "missing_required": [],
                    "missing_recommended": [],
                    "advisory": False,
                    "unevaluated": True,
                }
            else:
                status = evaluate_prerequisites(topic.id, prereqs, mastery)
            score = mastery.get(topic.id, {}).get("score", 0.0)
            topics_out.append(
                {
                    "slug": topic.id,
                    "title": topic.title,
                    "position": topic.position,
                    "difficulty": topic.difficulty,
                    "summary": topic.description,
                    "objectives": topic.learning_objectives or [],
                    "mastery": score,
                    "attempts": mastery.get(topic.id, {}).get("attempts", 0),
                    "completed": score >= MASTERY_THRESHOLD,
                    "prerequisites": prereqs.get(topic.id, []),
                    "status": status,
                    "lessons": lessons_by_topic.get(topic.id, []),
                }
            )
        # A section with no topics yet is not rendered. The roadmap forbids
        # inaccessible modules, and seven of ten sections have no content.
        if not topics_out:
            continue
        sections_out.append(
            {
                "slug": section.slug,
                "title": section.title,
                "position": section.position,
                "topics": topics_out,
            }
        )

    total = sum(len(s["topics"]) for s in sections_out)  # type: ignore[arg-type]
    completed = sum(
        1 for s in sections_out for t in s["topics"] if t["completed"]  # type: ignore[index]
    )

    return {
        "sections": sections_out,
        "progress": {
            "topics_total": total,
            "topics_completed": completed,
            "percent": round(100.0 * completed / total, 1) if total else 0.0,
        },
    }


def recommended_next(db: Session, user_id: int, limit: int = 3) -> list[dict[str, object]]:
    """Suggest the next topics in dependency order.

    Prefers topics whose required prerequisites are met and that are not yet
    complete, starting from the earliest section. Falls back to topics that are
    merely missing recommended background, so a learner who has finished
    everything available still gets somewhere to go rather than an empty list.
    """
    hierarchy = build_curriculum(db, user_id)
    ready: list[dict[str, object]] = []
    advisory: list[dict[str, object]] = []

    for section in hierarchy["sections"]:  # type: ignore[index]
        for topic in section["topics"]:  # type: ignore[index]
            if topic["completed"]:  # type: ignore[index]
                continue
            entry = {
                "slug": topic["slug"],  # type: ignore[index]
                "title": topic["title"],  # type: ignore[index]
                "section": section["slug"],  # type: ignore[index]
                "difficulty": topic["difficulty"],  # type: ignore[index]
                "missing_required": topic["status"]["missing_required"],  # type: ignore[index]
            }
            if topic["status"]["ready"]:  # type: ignore[index]
                ready.append(entry)
            else:
                advisory.append(entry)

    return (ready + advisory)[:limit]
