"""Tag-based mastery tracking and personalized next-step recommendations."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import (
    ChallengeAttempt,
    CodingChallenge,
    Quiz,
    QuizAttempt,
)
from app.models.content import Lesson
from app.models.mastery import Recommendation, UserMastery

#: exponential moving average weight for new evidence
ALPHA = 0.4
WEAK_THRESHOLD = 0.6


def _bump(db: Session, user_id: int, tag: str, outcome: float) -> None:
    row = db.scalar(
        select(UserMastery).where(UserMastery.user_id == user_id, UserMastery.tag == tag)
    )
    if row is None:
        row = UserMastery(user_id=user_id, tag=tag, score=outcome, attempts=1)
        db.add(row)
        return
    row.score = (1 - ALPHA) * float(row.score) + ALPHA * float(outcome)
    row.attempts = int(row.attempts) + 1


def update_mastery_from_quiz(db: Session, user_id: int, quiz: Quiz, percentage: float) -> None:
    tags = list(quiz.tags or []) or ["general"]
    for tag in tags:
        _bump(db, user_id, tag, max(0.0, min(1.0, percentage / 100.0)))
    db.commit()


def update_mastery_from_challenge(
    db: Session, user_id: int, challenge: CodingChallenge, passed: bool
) -> None:
    tags = list(challenge.tags or []) or ["general"]
    for tag in tags:
        _bump(db, user_id, tag, 1.0 if passed else 0.0)
    db.commit()


def mastery_map(db: Session, user_id: int) -> dict[str, dict[str, Any]]:
    rows = db.scalars(select(UserMastery).where(UserMastery.user_id == user_id)).all()
    return {
        r.tag: {"tag": r.tag, "score": round(float(r.score), 3), "attempts": int(r.attempts)}
        for r in rows
    }


def weakest_tags(db: Session, user_id: int, limit: int = 3) -> list[dict[str, Any]]:
    values = list(mastery_map(db, user_id).values())
    values.sort(key=lambda item: item["score"])
    return [v for v in values if v["score"] < WEAK_THRESHOLD][:limit]


def recommend(db: Session, user_id: int, limit: int = 4) -> list[dict[str, Any]]:
    """Suggest lessons/challenges targeting the learner's weakest concepts."""
    mastery = mastery_map(db, user_id)
    weak = [item["tag"] for item in weakest_tags(db, user_id, limit=3)]

    attempted = {
        row.challenge_id
        for row in db.scalars(
            select(ChallengeAttempt).where(ChallengeAttempt.user_id == user_id)
        ).all()
    }
    passed = {
        row.challenge_id
        for row in db.scalars(
            select(ChallengeAttempt).where(
                ChallengeAttempt.user_id == user_id, ChallengeAttempt.passed.is_(True)
            )
        ).all()
    }

    out: list[dict[str, Any]] = []

    # 1. lessons covering weak tags
    if weak:
        for lesson in db.scalars(select(Lesson).order_by(Lesson.order_index)).all():
            overlap = set(lesson.tags or []) & set(weak)
            if overlap:
                out.append(
                    {
                        "kind": "lesson",
                        "slug": lesson.slug,
                        "title": lesson.title,
                        "reason": f"Strengthen: {', '.join(sorted(overlap))}",
                    }
                )

    # 2. unpassed challenges, weak-tag ones first
    challenges = db.scalars(select(CodingChallenge)).all()
    challenges.sort(
        key=lambda c: (
            c.id in passed,
            -len(set(c.tags or []) & set(weak)),
            c.id in attempted,
        )
    )
    for challenge in challenges:
        if challenge.id in passed:
            continue
        overlap = set(challenge.tags or []) & set(weak)
        out.append(
            {
                "kind": "challenge",
                "slug": challenge.slug,
                "title": challenge.title,
                "reason": (
                    f"Practice: {', '.join(sorted(overlap))}"
                    if overlap
                    else ("Retry this challenge" if challenge.id in attempted else "Try next")
                ),
            }
        )

    # 3. cold start: no activity at all
    if not mastery and not out:
        for lesson in db.scalars(select(Lesson).order_by(Lesson.order_index).limit(2)).all():
            out.append(
                {
                    "kind": "lesson",
                    "slug": lesson.slug,
                    "title": lesson.title,
                    "reason": "Start here",
                }
            )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in out:
        key = (item["kind"], item["slug"])
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped[:limit]


def store_recommendations(db: Session, user_id: int, items: list[dict[str, Any]]) -> None:
    for stale in db.scalars(
        select(Recommendation).where(Recommendation.user_id == user_id)
    ).all():
        db.delete(stale)
    for item in items:
        db.add(
            Recommendation(
                user_id=user_id, kind=item["kind"], slug=item["slug"], reason=item["reason"]
            )
        )
    db.commit()


def learner_progress(db: Session, user_id: int) -> dict[str, Any]:
    quiz_attempts = db.scalars(
        select(QuizAttempt).where(QuizAttempt.user_id == user_id)
    ).all()
    challenge_attempts = db.scalars(
        select(ChallengeAttempt).where(ChallengeAttempt.user_id == user_id)
    ).all()

    percentages = [
        (a.score / a.max_score * 100.0) for a in quiz_attempts if a.max_score
    ]
    return {
        "user_id": user_id,
        "quizzes_taken": len({a.quiz_id for a in quiz_attempts}),
        "challenges_attempted": len({a.challenge_id for a in challenge_attempts}),
        "challenges_passed": len({a.challenge_id for a in challenge_attempts if a.passed}),
        "average_quiz_percentage": round(sum(percentages) / len(percentages), 1)
        if percentages
        else 0.0,
        "mastery": sorted(mastery_map(db, user_id).values(), key=lambda m: m["tag"]),
        "recommendations": recommend(db, user_id),
    }


__all__ = [
    "update_mastery_from_quiz",
    "update_mastery_from_challenge",
    "recommend",
    "learner_progress",
    "mastery_map",
    "weakest_tags",
    "store_recommendations",
]
