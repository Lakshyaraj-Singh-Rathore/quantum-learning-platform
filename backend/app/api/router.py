from fastapi import APIRouter

from app.config import get_settings

from app.api import (
    ai,
    assessments,
    auth,
    circuits,
    curriculum,
    dashboard,
    jobs,
    noise_lab,
    qml_lab,
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

# Feature-flagged. With qml_enabled false the router is never mounted, so
# every /qml/* path is absent and answers 404 -- the flag's guarantee is that
# the application behaves exactly as it did before the feature existed.
if get_settings().qml_enabled:
    api_router.include_router(qml_lab.router)

__all__ = ["api_router"]
