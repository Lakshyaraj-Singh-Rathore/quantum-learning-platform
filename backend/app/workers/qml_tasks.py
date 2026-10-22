"""Celery task for QML Lab experiments.

In its own module rather than appended to ``app/workers/tasks.py``: §4 prefers
it, and it keeps the diff off a hot file that every simulation run touches.

**The time limits here are per-task and nothing else changes.** The globals in
``app/config.py`` — ``celery_soft_time_limit = 8`` and
``celery_hard_time_limit = 15`` — are applied to *every* task by
``celery_app.py:20-21``, and ``app/workers/tasks.py:96`` derives the qBraid
remote-wait budget from the soft one. Raising the global to suit a
minutes-long training run would silently extend the wait on a paid remote
queue. So the longer budget is attached to this decorator only, and
``tests/test_qml_tasks.py`` proves both directions: this task gets the long
limit, and ``run_simulation`` still gets 8/15.
"""

from __future__ import annotations

import logging

from celery.exceptions import SoftTimeLimitExceeded

from app.config import get_settings
from app.database import SessionLocal
from app.models.qml import TIMED_OUT
from app.services import qml_lab as service
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_settings = get_settings()


@celery_app.task(
    bind=True,
    name="app.workers.qml_tasks.run_qml_experiment",
    soft_time_limit=_settings.qml_task_soft_time_limit,
    time_limit=_settings.qml_task_hard_time_limit,
)
def run_qml_experiment(self, experiment_id: int) -> dict:
    """Train one experiment and record its terminal state."""
    db = SessionLocal()
    try:
        # The engine stops itself a little before Celery would interrupt it,
        # so a timed-out run can still write its partial history and a useful
        # message. Mirrors the margin at app/workers/tasks.py:96.
        return service.execute_experiment(
            db,
            experiment_id,
            celery_task_id=getattr(self.request, "id", None),
            deadline_seconds=service.training_deadline_seconds(),
        )
    except SoftTimeLimitExceeded:
        # Reached only if the cooperative deadline did not fire first -- for
        # example if one circuit evaluation overran the whole margin. Without
        # this the row would stay `running` forever and hold the single
        # concurrency slot.
        logger.warning("QML experiment %s hit the Celery soft time limit", experiment_id)
        return service.force_terminal(
            db,
            experiment_id,
            TIMED_OUT,
            "Training was stopped by the worker time limit before it could finish.",
        )
    finally:
        db.close()
