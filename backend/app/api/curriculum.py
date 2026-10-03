"""Curriculum hierarchy endpoints.

The hierarchy is readable without authentication so that a visitor can browse
the curriculum before signing up. Progress-dependent fields simply report zero
for anonymous callers; nothing is locked for them, because gating a visitor on
progress they have not had a chance to make would be a dead end rather than a
learning path.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import bearer
from app.models.curriculum import CurriculumTopic
from app.security import decode_token
from app.services.curriculum_service import (
    build_curriculum,
    evaluate_prerequisites,
    prerequisites_for,
    recommended_next,
    topic_mastery,
)
from app.models.user import User

router = APIRouter(prefix="/curriculum", tags=["curriculum"])


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User | None:
    """Resolve the caller if there is a valid token, else None.

    An invalid or expired token is treated as anonymous rather than rejected.
    A visitor holding a stale token should still be able to read the public
    curriculum; only endpoints that act on their data require a real user.
    """
    if creds is None or not creds.credentials:
        return None
    try:
        payload = decode_token(creds.credentials)
        user_id = payload.get("sub")
    except Exception:  # noqa: BLE001
        return None
    if not user_id:
        return None
    user = db.get(User, int(user_id))
    return user if user is not None and user.is_active else None


def _lessons_for_topic(db: Session, topic_id: str) -> list[dict]:
    """Lessons for a topic, primary first then authored order.

    The topic detail response needs these so the UI can offer start/continue
    without fetching the whole tree.
    """
    from app.models.content import Lesson as _Lesson
    from app.models.curriculum import LessonTopic

    links = db.scalars(
        select(LessonTopic)
        .where(LessonTopic.topic_id == topic_id)
        .order_by(LessonTopic.is_primary.desc(), LessonTopic.id)
    ).all()
    out: list[dict] = []
    for link in links:
        lesson = db.scalar(select(_Lesson).where(_Lesson.slug == link.lesson_slug))
        if lesson is None:
            continue
        out.append({
            "slug": lesson.slug,
            "title": lesson.title,
            "track": lesson.track,
            "position": lesson.position,
            "is_primary": bool(link.is_primary),
            "confidence": link.confidence,
        })
    return out


@router.get("")
def get_curriculum(
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """Full section -> topic -> lesson hierarchy with the caller's progress."""
    return build_curriculum(db, user.id if user else None)


@router.get("/next")
def get_next(
    user: User = Depends(get_optional_user),
    db: Session = Depends(get_db),
    limit: int = 3,
) -> list[dict]:
    """Recommended next topics, in dependency order."""
    if user is None:
        # No history, so recommendation can only follow the curriculum order.
        hierarchy = build_curriculum(db, None)
        out: list[dict] = []
        for section in hierarchy["sections"]:
            for topic in section["topics"]:
                out.append(
                    {
                        "slug": topic["slug"],
                        "title": topic["title"],
                        "section": section["slug"],
                        "difficulty": topic["difficulty"],
                        "missing_required": topic["status"]["missing_required"],
                        # Additive: resume must open a lesson, and a topic id
                        # alone cannot say which one.
                        "lesson_slug": (
                            topic["lessons"][0]["slug"] if topic.get("lessons") else None
                        ),
                    }
                )
        return out[: max(0, min(limit, 10))]
    return recommended_next(db, user.id, max(0, min(limit, 10)))


@router.get("/topics/{topic_id}")
def get_topic(
    topic_id: str,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> dict:
    """One topic: its lessons, prerequisites and readiness for this learner."""
    topic = db.scalar(select(CurriculumTopic).where(CurriculumTopic.id == topic_id))
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")

    prereqs = prerequisites_for(db)
    if user is None:
        # No mastery to evaluate against: report the declared edges without
        # claiming they are unmet. See build_curriculum for the rationale.
        mastery = {}
        status = {
            "ready": True,
            "missing_required": [],
            "missing_recommended": [],
            "advisory": False,
            "unevaluated": True,
        }
    else:
        mastery = topic_mastery(db, user.id)
        status = evaluate_prerequisites(topic_id, prereqs, mastery)

    return {
        "slug": topic.id,
        "title": topic.title,
        "section_slug": topic.section_slug,
        "difficulty": topic.difficulty,
        "summary": topic.description,
        "objectives": topic.learning_objectives or [],
        "prerequisites": prereqs.get(topic_id, []),
        "status": status,
        "mastery": mastery.get(topic_id, {}).get("score", 0.0),
        "lessons": _lessons_for_topic(db, topic_id),
    }
