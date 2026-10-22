"""QML Lab HTTP API.

This router is only mounted when ``settings.qml_enabled`` is true
(``app/api/router.py``), so with the flag off every path below is absent and
answers 404 -- which is the feature flag's whole guarantee.

Conventions copied from ``app/api/jobs.py`` rather than invented: 422 with
``{"errors": [...]}`` for validation, ``get_current_user`` for auth,
``404`` then ``403 "Not your job"`` for ownership (``jobs.py:200-206``), and
the ``run_hash`` cache lookup for duplicate submissions.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.qml import TERMINAL_STATUSES, QmlExperiment
from app.models.user import User
from app.quantum.qml_lab import limits
from app.quantum.qml_lab.errors import QmlLabError, QmlLimitExceededError
from app.quantum.qml_lab.models import QmlExperimentConfig
from app.services import qml_lab as service
from app.workers.qml_tasks import run_qml_experiment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qml", tags=["qml"])


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------


class ExperimentOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    status: str
    config: dict[str, Any]
    error: str | None = None
    cached: bool = False


class ExperimentDetail(ExperimentOut):
    history: list[dict[str, Any]] = Field(default_factory=list)
    result: dict[str, Any] | None = None
    epochs_recorded: int = 0


class InferenceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: list[list[float]] = Field(min_length=1, max_length=256)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _to_out(row: QmlExperiment, *, cached: bool = False) -> ExperimentOut:
    return ExperimentOut(
        id=row.id,
        status=row.status,
        config=row.config,
        error=row.error,
        cached=cached,
    )


def _get_experiment(experiment_id: int, db: Session, user: User) -> QmlExperiment:
    """Ownership check mirroring ``api/jobs.py:200-206`` exactly."""
    row = db.get(QmlExperiment, experiment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if row.user_id != user.id and user.role not in {"instructor", "admin"}:
        raise HTTPException(status_code=403, detail="Not your job")
    return row


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------


@router.get("/features")
def features(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Tells the browser the feature is on.

    Reaching this at all means the router was mounted, so the flag is true.
    With the flag off the path does not exist and the client sees 404, which
    is how the UI decides whether to show the nav entry -- an environment
    flip, not a rebuild.
    """
    return {"qml_enabled": True}


@router.get("/describe")
def describe(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Limits, datasets and defaults, so the UI cannot drift from the server."""
    return service.describe()


@router.post("/experiments", response_model=ExperimentOut, status_code=201)
def create_experiment(
    payload: QmlExperimentConfig,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExperimentOut:
    """Validate, de-duplicate, enforce the concurrency cap, and enqueue.

    ``payload`` is the engine's own config model, so FastAPI rejects an
    unknown field with 422 before anything here runs -- the schema forbids
    extras precisely so a wrong-shaped request cannot be silently accepted.
    """
    try:
        limits.enforce(payload)
    except QmlLimitExceededError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.violations}) from exc

    # Dataset feasibility is checked up front rather than failing inside the
    # worker two seconds later: iris_binary caps at 100 samples, and the
    # encoder needs one wire per feature.
    try:
        probe = service.datasets.build_dataset(payload.dataset, np.random.default_rng(payload.seed))
        if probe.n_features > payload.circuit.n_qubits:
            raise HTTPException(
                status_code=422,
                detail={
                    "errors": [
                        f"dataset '{payload.dataset.name}' has {probe.n_features} features but the "
                        f"circuit has {payload.circuit.n_qubits} qubits; raise n_qubits to at least "
                        f"{probe.n_features}"
                    ]
                },
            )
    except QmlLabError as exc:
        raise HTTPException(status_code=422, detail={"errors": [str(exc)]}) from exc

    run_hash = service.compute_config_hash(payload)

    cached = service.find_cached(db, user.id, run_hash)
    if cached is not None:
        return _to_out(cached, cached=True)

    # Concurrency is scoped globally: the protected resource is the single
    # worker slot, not a per-user quota. The dedicated `qml` queue is the
    # structural guarantee; this check exists to explain the wait instead of
    # leaving the user staring at a queued row.
    active = service.find_active(db)
    if active is not None:
        mine = active.user_id == user.id
        whose = "Your experiment" if mine else "Another experiment"
        raise HTTPException(
            status_code=409,
            detail={
                "errors": [
                    f"{whose} ({active.id}) is still {active.status}. "
                    f"Only {limits.MAX_CONCURRENT_JOBS} training job may run at a time; "
                    "cancel it or wait for it to finish."
                ]
            },
        )

    experiment = QmlExperiment(
        user_id=user.id,
        status="queued",
        config=payload.model_dump(mode="json"),
        run_hash=run_hash,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    try:
        async_result = run_qml_experiment.apply_async(args=[experiment.id])
        experiment.celery_task_id = getattr(async_result, "id", None)
        db.commit()
    except Exception as exc:  # noqa: BLE001 - broker down; same handling as jobs.py
        experiment.status = "failed"
        experiment.error = f"Could not enqueue experiment: {exc}"
        db.commit()

    db.refresh(experiment)
    return _to_out(experiment)


@router.get("/experiments", response_model=list[ExperimentOut])
def list_experiments(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ExperimentOut]:
    rows = db.scalars(
        select(QmlExperiment)
        .where(QmlExperiment.user_id == user.id)
        .order_by(QmlExperiment.id.desc())
        .limit(limit)
    ).all()
    return [_to_out(row) for row in rows]


@router.get("/experiments/{experiment_id}", response_model=ExperimentDetail)
def get_experiment(
    experiment_id: int,
    after_epoch: int = Query(0, ge=0, description="Return only epochs greater than this"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExperimentDetail:
    """Status plus epoch history -- what the training dashboard polls.

    ``after_epoch`` makes polling incremental: the dashboard sends the last
    epoch it has, and gets back only what is new.
    """
    row = _get_experiment(experiment_id, db, user)
    history = service.load_history(db, row.id, after_epoch=after_epoch)
    return ExperimentDetail(
        id=row.id,
        status=row.status,
        config=row.config,
        error=row.error,
        history=history,
        result=row.result,
        epochs_recorded=len(row.epochs),
    )


@router.get("/experiments/{experiment_id}/result")
def get_result(
    experiment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    row = _get_experiment(experiment_id, db, user)
    if row.status not in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={"errors": [f"Experiment is {row.status}, not finished"]},
        )
    return {
        "id": row.id,
        "status": row.status,
        "result": row.result,
        "history": service.load_history(db, row.id),
        "error": row.error,
    }


@router.post("/experiments/{experiment_id}/cancel", response_model=ExperimentOut)
def cancel_experiment(
    experiment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ExperimentOut:
    """Request cooperative cancellation.

    Sets a flag the trainer reads between minibatches; it does not revoke the
    Celery task, because killing a worker mid-write cannot run cleanup.

    Idempotent: cancelling an already-cancelling experiment is 200, not an
    error. A terminal experiment is 409 -- there is nothing left to stop, and
    silently returning 200 would tell the user a lie.
    """
    row = _get_experiment(experiment_id, db, user)

    if row.status in TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={"errors": [f"Experiment {row.id} already finished with status '{row.status}'"]},
        )

    if not row.cancel_requested:
        row.cancel_requested = True
        db.commit()
        db.refresh(row)

    return _to_out(row)


@router.post("/experiments/{experiment_id}/inference")
def inference(
    experiment_id: int,
    payload: InferenceIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Predict on new points using the saved artifact."""
    row = _get_experiment(experiment_id, db, user)
    if row.status != "completed":
        raise HTTPException(
            status_code=409,
            detail={"errors": [f"Experiment is {row.status}; inference needs a completed experiment"]},
        )

    try:
        return service.run_inference(row, payload.features)
    except (QmlLabError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"errors": [str(exc)]}) from exc
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=409,
            detail={"errors": [f"Saved model for experiment {row.id} is missing: {exc}"]},
        ) from exc
