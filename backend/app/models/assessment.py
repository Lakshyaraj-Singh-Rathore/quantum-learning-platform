from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func

from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, JSONType


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    tags: Mapped[list] = mapped_column(JSONType, default=list)


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    qtype: Mapped[str] = mapped_column(String(32), default="mcq")  # mcq|short
    options: Mapped[list] = mapped_column(JSONType, default=list)
    answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list] = mapped_column(JSONType, default=list)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    answers: Mapped[dict] = mapped_column(JSONType, default=dict)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    max_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CodingChallenge(Base):
    __tablename__ = "coding_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    prompt: Mapped[str] = mapped_column(Text)
    allowed_gates: Mapped[list] = mapped_column(JSONType, default=list)
    target: Mapped[dict] = mapped_column(JSONType, default=dict)  # counts or state
    constraints: Mapped[dict] = mapped_column(JSONType, default=dict)
    tags: Mapped[list] = mapped_column(JSONType, default=list)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, default=False)


class ChallengeAttempt(Base):
    __tablename__ = "challenge_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("coding_challenges.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    circuit_ir: Mapped[dict] = mapped_column(JSONType)
    job_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AutogradeResult(Base):
    __tablename__ = "autograde_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("challenge_attempts.id"), index=True)
    details: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
