"""Learner progress and instructor analytics (role-gated)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_roles
from app.models.assessment import (
    AutogradeResult,
    ChallengeAttempt,
    CodingChallenge,
    Quiz,
    QuizAttempt,
)
from app.models.job import SimulationJob
from app.models.mastery import UserMastery
from app.models.user import User
from app.schemas.dashboard import InstructorOverviewOut, LearnerProgressOut
from app.services import recommendations

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/me", response_model=LearnerProgressOut)
def my_progress(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> LearnerProgressOut:
    return LearnerProgressOut(**recommendations.learner_progress(db, user.id))


@router.get("/recommendations")
def my_recommendations(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict[str, Any]]:
    items = recommendations.recommend(db, user.id)
    recommendations.store_recommendations(db, user.id, items)
    return items


@router.get("/instructor", response_model=InstructorOverviewOut)
def instructor_overview(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("instructor", "admin")),
) -> InstructorOverviewOut:
    total_students = (
        db.scalar(select(func.count()).select_from(User).where(User.role == "student")) or 0
    )
    total_jobs = db.scalar(select(func.count()).select_from(SimulationJob)) or 0

    # ---- quiz completion
    quiz_rows: list[dict[str, Any]] = []
    for quiz in db.scalars(select(Quiz).order_by(Quiz.id)).all():
        attempts = db.scalars(select(QuizAttempt).where(QuizAttempt.quiz_id == quiz.id)).all()
        learners = {a.user_id for a in attempts}
        percentages = [a.score / a.max_score * 100.0 for a in attempts if a.max_score]
        quiz_rows.append(
            {
                "slug": quiz.slug,
                "title": quiz.title,
                "attempts": len(attempts),
                "unique_students": len(learners),
                "completion_rate": round(len(learners) / total_students * 100, 1)
                if total_students
                else 0.0,
                "average_percentage": round(sum(percentages) / len(percentages), 1)
                if percentages
                else 0.0,
            }
        )

    # ---- challenge completion
    challenge_rows: list[dict[str, Any]] = []
    for challenge in db.scalars(select(CodingChallenge).order_by(CodingChallenge.id)).all():
        attempts = db.scalars(
            select(ChallengeAttempt).where(ChallengeAttempt.challenge_id == challenge.id)
        ).all()
        learners = {a.user_id for a in attempts}
        passers = {a.user_id for a in attempts if a.passed}
        challenge_rows.append(
            {
                "slug": challenge.slug,
                "title": challenge.title,
                "attempts": len(attempts),
                "unique_students": len(learners),
                "passed": len(passers),
                "pass_rate": round(len(passers) / len(learners) * 100, 1) if learners else 0.0,
                "completion_rate": round(len(learners) / total_students * 100, 1)
                if total_students
                else 0.0,
            }
        )

    # ---- common errors from failed autogrades and failed jobs
    error_counter: dict[str, int] = {}
    for row in db.scalars(select(AutogradeResult).order_by(AutogradeResult.id.desc()).limit(500)).all():
        for problem in (row.details or {}).get("constraint_problems", []) or []:
            error_counter[problem] = error_counter.get(problem, 0) + 1
        note = (row.details or {}).get("behaviour_note")
        if note and "distance" in note.lower():
            key = "Output distribution does not match the target"
            error_counter[key] = error_counter.get(key, 0) + 1
    for job in db.scalars(
        select(SimulationJob)
        .where(SimulationJob.status == "failed")
        .order_by(SimulationJob.id.desc())
        .limit(200)
    ).all():
        message = (job.error or "unknown error").split("\n")[0][:160]
        error_counter[message] = error_counter.get(message, 0) + 1

    common_errors = [
        {"error": key, "count": value}
        for key, value in sorted(error_counter.items(), key=lambda kv: kv[1], reverse=True)[:10]
    ]

    # ---- weakest concepts across the cohort
    tag_rows = db.execute(
        select(UserMastery.tag, func.avg(UserMastery.score), func.count())
        .group_by(UserMastery.tag)
        .order_by(func.avg(UserMastery.score))
    ).all()
    weakest_tags = [
        {"tag": tag, "average_score": round(float(avg), 3), "learners": int(count)}
        for tag, avg, count in tag_rows[:8]
    ]

    # ---- leaderboard
    board = db.execute(
        select(
            ChallengeAttempt.user_id,
            func.count(func.distinct(ChallengeAttempt.challenge_id)).filter(
                ChallengeAttempt.passed.is_(True)
            ),
        )
        .group_by(ChallengeAttempt.user_id)
        .order_by(
            func.count(func.distinct(ChallengeAttempt.challenge_id))
            .filter(ChallengeAttempt.passed.is_(True))
            .desc()
        )
        .limit(10)
    ).all()
    leaderboard: list[dict[str, Any]] = []
    for user_id, passed in board:
        learner = db.get(User, user_id)
        leaderboard.append(
            {
                "user": learner.display_name or learner.email if learner else f"user {user_id}",
                "challenges_passed": int(passed or 0),
            }
        )

    return InstructorOverviewOut(
        total_students=total_students,
        total_jobs=total_jobs,
        quiz_completion=quiz_rows,
        challenge_completion=challenge_rows,
        common_errors=common_errors,
        weakest_tags=weakest_tags,
        leaderboard=leaderboard,
    )


@router.get("/students")
def student_list(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("instructor", "admin")),
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for student in db.scalars(select(User).where(User.role == "student").order_by(User.id)).all():
        progress = recommendations.learner_progress(db, student.id)
        out.append(
            {
                "id": student.id,
                "email": student.email,
                "display_name": student.display_name,
                "quizzes_taken": progress["quizzes_taken"],
                "challenges_passed": progress["challenges_passed"],
                "average_quiz_percentage": progress["average_quiz_percentage"],
            }
        )
    return out
