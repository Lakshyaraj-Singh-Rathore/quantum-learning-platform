from typing import Any

from pydantic import BaseModel


class LearnerProgressOut(BaseModel):
    user_id: int
    quizzes_taken: int
    challenges_attempted: int
    challenges_passed: int
    average_quiz_percentage: float
    mastery: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []


class InstructorOverviewOut(BaseModel):
    total_students: int
    total_jobs: int
    quiz_completion: list[dict[str, Any]] = []
    challenge_completion: list[dict[str, Any]] = []
    common_errors: list[dict[str, Any]] = []
    weakest_tags: list[dict[str, Any]] = []
    leaderboard: list[dict[str, Any]] = []
