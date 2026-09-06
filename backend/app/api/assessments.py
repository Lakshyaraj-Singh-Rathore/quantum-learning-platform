"""Quizzes, coding challenges, autograded submissions and lesson listing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.assessment import (
    AutogradeResult,
    ChallengeAttempt,
    CodingChallenge,
    Quiz,
    QuizAttempt,
    QuizQuestion,
)
from app.models.content import Lesson
from app.models.job import SimulationJob
from app.models.user import User
from app.quantum.inspect import compute_run_hash, inspect_circuit
from app.quantum.ir import CircuitIR
from app.quantum.qasm3_codec import to_qasm3
from app.schemas.assessment import (
    ChallengeAttemptOut,
    ChallengeOut,
    ChallengeSubmitIn,
    QuizOut,
    QuizResultOut,
    QuizSubmitIn,
)
from app.services import recommendations
from app.services.autograder import finalize_attempt
from app.workers.tasks import resolve_backend, run_simulation

router = APIRouter(tags=["assessments"])


# --------------------------------------------------------------------------- #
# Lessons
# --------------------------------------------------------------------------- #
@router.get("/lessons")
def list_lessons(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.scalars(select(Lesson).order_by(Lesson.order_index)).all()
    return [
        {"slug": r.slug, "title": r.title, "tags": r.tags or [], "order_index": r.order_index}
        for r in rows
    ]


@router.get("/lessons/{slug}")
def get_lesson(slug: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    lesson = db.scalar(select(Lesson).where(Lesson.slug == slug))
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")
    path = Path(lesson.path)
    if not path.exists():
        path = Path(get_settings().content_dir) / f"{slug}.md"
    content = path.read_text(encoding="utf-8") if path.exists() else "_Lesson content missing._"
    return {"slug": lesson.slug, "title": lesson.title, "tags": lesson.tags or [], "content": content}


# --------------------------------------------------------------------------- #
# Quizzes
# --------------------------------------------------------------------------- #
@router.get("/quizzes", response_model=list[QuizOut])
def list_quizzes(db: Session = Depends(get_db)) -> list[QuizOut]:
    out: list[QuizOut] = []
    for quiz in db.scalars(select(Quiz).order_by(Quiz.id)).all():
        questions = db.scalars(
            select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id).order_by(QuizQuestion.id)
        ).all()
        out.append(
            QuizOut(
                id=quiz.id,
                slug=quiz.slug,
                title=quiz.title,
                tags=quiz.tags or [],
                # answers are never sent to the client
                questions=[
                    {
                        "id": q.id,
                        "prompt": q.prompt,
                        "qtype": q.qtype,
                        "options": q.options or [],
                        "tags": q.tags or [],
                    }
                    for q in questions
                ],
            )
        )
    return out


@router.post("/quizzes/{slug}/submit", response_model=QuizResultOut)
def submit_quiz(
    slug: str,
    payload: QuizSubmitIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> QuizResultOut:
    quiz = db.scalar(select(Quiz).where(Quiz.slug == slug))
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = db.scalars(select(QuizQuestion).where(QuizQuestion.quiz_id == quiz.id)).all()
    score = 0.0
    feedback: list[dict[str, Any]] = []

    for question in questions:
        given = (payload.answers.get(str(question.id)) or "").strip()
        correct = _matches(given, question.answer, question.qtype)
        score += 1.0 if correct else 0.0
        feedback.append(
            {
                "question_id": question.id,
                "prompt": question.prompt,
                "your_answer": given,
                "correct_answer": question.answer,
                "correct": correct,
                "explanation": question.explanation,
            }
        )

    max_score = float(len(questions))
    percentage = (score / max_score * 100.0) if max_score else 0.0

    db.add(
        QuizAttempt(
            quiz_id=quiz.id,
            user_id=user.id,
            answers=payload.answers,
            score=score,
            max_score=max_score,
        )
    )
    db.commit()
    recommendations.update_mastery_from_quiz(db, user.id, quiz, percentage)

    return QuizResultOut(
        score=score, max_score=max_score, percentage=round(percentage, 1), feedback=feedback
    )


def _matches(given: str, expected: str, qtype: str) -> bool:
    if not given:
        return False
    if qtype == "mcq":
        return given.strip().lower() == expected.strip().lower()
    normalize = lambda s: " ".join(s.lower().split())  # noqa: E731
    accepted = [normalize(a) for a in expected.split("|")]
    return normalize(given) in accepted


# --------------------------------------------------------------------------- #
# Coding challenges
# --------------------------------------------------------------------------- #
@router.get("/challenges", response_model=list[ChallengeOut])
def list_challenges(db: Session = Depends(get_db)) -> list[ChallengeOut]:
    return [
        ChallengeOut(
            id=c.id,
            slug=c.slug,
            title=c.title,
            prompt=c.prompt,
            allowed_gates=c.allowed_gates or [],
            constraints=c.constraints or {},
            tags=c.tags or [],
            is_dynamic=bool(c.is_dynamic),
        )
        for c in db.scalars(select(CodingChallenge).order_by(CodingChallenge.id)).all()
    ]


@router.post("/challenges/{slug}/submit", response_model=ChallengeAttemptOut)
def submit_challenge(
    slug: str,
    payload: ChallengeSubmitIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChallengeAttemptOut:
    challenge = db.scalar(select(CodingChallenge).where(CodingChallenge.slug == slug))
    if challenge is None:
        raise HTTPException(status_code=404, detail="Challenge not found")

    try:
        ir = CircuitIR.from_dict(payload.circuit_ir)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Invalid circuit: {exc}") from exc

    report = inspect_circuit(ir, "auto", payload.shots)
    if not report["ok"]:
        raise HTTPException(status_code=422, detail={"errors": report["errors"]})

    shots = int((challenge.target or {}).get("shots") or payload.shots)
    engine, _ = resolve_backend(ir, "auto", "auto")

    job = SimulationJob(
        user_id=user.id,
        status="queued",
        backend="auto",
        mode="auto",
        shots=shots,
        circuit_ir=ir.to_dict(),
        qasm3=to_qasm3(ir),
        run_hash=compute_run_hash(ir.to_dict(), engine, shots, "auto"),
    )
    db.add(job)
    db.flush()

    attempt = ChallengeAttempt(
        challenge_id=challenge.id,
        user_id=user.id,
        circuit_ir=ir.to_dict(),
        job_id=job.id,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    try:
        run_simulation.apply_async(args=[job.id])
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.error = f"Could not enqueue job: {exc}"
        db.commit()

    return ChallengeAttemptOut(
        attempt_id=attempt.id, job_id=job.id, status="queued", feedback="Simulation queued."
    )


@router.get("/attempts/{attempt_id}", response_model=ChallengeAttemptOut)
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ChallengeAttemptOut:
    attempt = db.get(ChallengeAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Attempt not found")
    if attempt.user_id != user.id and user.role not in {"instructor", "admin"}:
        raise HTTPException(status_code=403, detail="Not your attempt")

    job = db.get(SimulationJob, attempt.job_id) if attempt.job_id else None
    if job is not None and job.status in {"queued", "running"}:
        return ChallengeAttemptOut(
            attempt_id=attempt.id,
            job_id=attempt.job_id,
            status=job.status,
            feedback="Simulation in progress...",
        )

    graded = db.scalar(
        select(AutogradeResult)
        .where(AutogradeResult.attempt_id == attempt.id)
        .order_by(desc(AutogradeResult.id))
        .limit(1)
    )
    if graded is None:
        outcome = finalize_attempt(db, attempt.id)
        return ChallengeAttemptOut(
            attempt_id=attempt.id,
            job_id=attempt.job_id,
            status=outcome.get("status", "graded"),
            passed=bool(outcome.get("passed")),
            score=float(outcome.get("score") or 0.0),
            feedback=str(outcome.get("feedback") or ""),
            details=outcome.get("details") or {},
        )

    return ChallengeAttemptOut(
        attempt_id=attempt.id,
        job_id=attempt.job_id,
        status="graded",
        passed=bool(attempt.passed),
        score=float(attempt.score),
        feedback=attempt.feedback,
        details=graded.details or {},
    )
