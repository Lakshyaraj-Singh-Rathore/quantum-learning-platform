from fastapi import APIRouter

from app.api import ai, assessments, auth, circuits, dashboard, jobs

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(jobs.router)
api_router.include_router(circuits.router)
api_router.include_router(ai.router)
api_router.include_router(assessments.router)
api_router.include_router(dashboard.router)

__all__ = ["api_router"]
