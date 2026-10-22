from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "quantumlearn",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks", "app.workers.qml_tasks"],
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
    # QML training runs for minutes; simulation jobs run for seconds. Routing
    # them to a dedicated queue is what structurally prevents a training job
    # from occupying a prefork slot that short jobs need, and lets the QML
    # worker be started with --concurrency=1 -- the concurrency guarantee the
    # pre-dispatch 409 only explains. NOTE: a worker must consume this queue
    # (`-Q qml --concurrency=1`); docker-compose.yml's worker consumes the
    # default queue only, so enabling qml_enabled also means running a QML
    # worker. Documented in docs/qml/phase-2-report.md.
    task_routes={"app.workers.qml_tasks.*": {"queue": "qml"}},
    # dev-only escape hatch so the platform runs without a broker
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=False,
)
