from typing import Any, Optional

from pydantic import BaseModel


class QuizOut(BaseModel):
    id: int
    slug: str
    title: str
    tags: list[str] = []
    questions: list[dict[str, Any]] = []


class QuizSubmitIn(BaseModel):
    answers: dict[str, str]


class QuizResultOut(BaseModel):
    score: float
    max_score: float
    percentage: float
    feedback: list[dict[str, Any]] = []


class ChallengeOut(BaseModel):
    id: int
    slug: str
    title: str
    prompt: str
    allowed_gates: list[str] = []
    constraints: dict[str, Any] = {}
    tags: list[str] = []
    is_dynamic: bool = False


class ChallengeSubmitIn(BaseModel):
    circuit_ir: dict[str, Any]
    shots: int = 1024


class ChallengeAttemptOut(BaseModel):
    attempt_id: int
    job_id: Optional[int] = None
    status: str
    passed: bool = False
    score: float = 0.0
    feedback: str = ""
    details: dict[str, Any] = {}
