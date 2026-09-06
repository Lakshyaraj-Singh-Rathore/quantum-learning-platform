from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "quantumlearn",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=settings.celery_soft_time_limit,
    task_time_limit=settings.celery_hard_time_limit,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    # dev-only escape hatch so the platform runs without a broker
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=False,
)
