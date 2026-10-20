from fastapi import APIRouter

from app.api import (
    ai,
    assessments,
    auth,
    circuits,
    curriculum,
    dashboard,
    jobs,
    noise_lab,
    qudit_lab,
    smart_composer,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(circuits.router)
api_router.include_router(ai.router)
api_router.include_router(assessments.router)
api_router.include_router(curriculum.router)
api_router.include_router(dashboard.router)
api_router.include_router(noise_lab.router)
api_router.include_router(smart_composer.router)
api_router.include_router(qudit_lab.router)

__all__ = ["api_router"]
