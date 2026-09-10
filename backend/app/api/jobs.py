"""Simulation job submission, status, results and exports."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.deps import get_current_user
from app.models.job import SimulationJob
from app.models.user import User
from app.quantum import codegen_cirq, codegen_qiskit
from app.quantum.backends import qbraid_sim
from app.quantum.inspect import compute_run_hash, inspect_circuit
from app.quantum.ir import CircuitIR
from app.quantum.qasm3_codec import from_qasm3, to_qasm3
from app.schemas.circuit import InspectIn, QasmIn
from app.schemas.job import JobCreate, JobOut, JobResultOut
from app.workers.tasks import resolve_backend, run_simulation

router = APIRouter(tags=["jobs"])


def _load_ir(data: dict[str, Any]) -> CircuitIR:
    try:
        return CircuitIR.from_dict(data)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Invalid circuit: {exc}") from exc


@router.get("/backends")
def list_backends() -> dict[str, Any]:
    """Backend catalogue with availability, for the UI selector."""
    available, reason = qbraid_sim.is_available()
    settings = get_settings()
    return {
        "backends": [
            {
                "id": "qiskit_aer",
                "label": "Qiskit Aer",
                "supports": ["static"],
                "available": True,
                "reason": "",
            },
            {
                "id": "cirq",
                "label": "Cirq",
                "supports": ["static"],
                "available": True,
                "reason": "",
            },
            {
                "id": "pennylane",
                "label": "PennyLane (default.qubit)",
                "supports": ["static"],
                "available": True,
                "reason": "",
            },
            {
                "id": "qbraid",
                "label": "qBraid",
                "supports": ["static"],
                "available": available,
                "reason": reason,
            },
            {
                "id": "qiskit_dynamic",
                "label": "Qiskit Dynamic Engine",
                "supports": ["dynamic"],
                "available": True,
                "reason": "",
            },
        ],
        "limits": {
            "max_dynamic_qubits": settings.max_dynamic_qubits,
            "max_dynamic_shots": settings.max_dynamic_shots,
            "while_cap": settings.while_cap,
        },
    }


@router.post("/inspect")
def inspect(payload: InspectIn, user: User = Depends(get_current_user)) -> dict[str, Any]:
    ir = _load_ir(payload.circuit_ir)
    return inspect_circuit(ir, payload.backend, payload.shots)


@router.post("/jobs", response_model=JobOut, status_code=201)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobOut:
    ir = _load_ir(payload.circuit_ir)

    report = inspect_circuit(ir, payload.backend, payload.shots)
    if not report["ok"]:
        raise HTTPException(status_code=422, detail={"errors": report["errors"]})

    engine, _notes = resolve_backend(ir, payload.backend, payload.mode)
    noise_dict = (
        payload.noise.model_dump()
        if payload.noise is not None and payload.noise.enabled
        else None
    )
    if noise_dict is not None and engine != "qiskit_aer":
        raise HTTPException(
            status_code=422,
            detail={
                "errors": [
                    "The noise model is only implemented for the Qiskit Aer backend. "
                    f"Select Qiskit Aer, or turn noise off to run on '{engine}'."
                ]
            },
        )
    run_hash = compute_run_hash(
        ir.to_dict(), engine, payload.shots, payload.mode, noise_dict
    )

    cached = db.scalar(
        select(SimulationJob)
        .where(
            SimulationJob.run_hash == run_hash,
            SimulationJob.user_id == user.id,
            SimulationJob.status == "completed",
        )
        .order_by(desc(SimulationJob.id))
        .limit(1)
    )
    if cached is not None:
        return JobOut(
            id=cached.id,
            status=cached.status,
            backend=cached.backend,
            mode=cached.mode,
            shots=cached.shots,
        )

    job = SimulationJob(
        user_id=user.id,
        status="queued",
        backend=payload.backend,
        mode=payload.mode,
        shots=payload.shots,
        circuit_ir=ir.to_dict(),
        noise=noise_dict,
        qasm3=to_qasm3(ir),
        run_hash=run_hash,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        run_simulation.apply_async(args=[job.id])
    except Exception as exc:  # noqa: BLE001 - broker down
        job.status = "failed"
        job.error = f"Could not enqueue job: {exc}"
        db.commit()

    return JobOut(
        id=job.id,
        status=job.status,
        backend=job.backend,
        mode=job.mode,
        shots=job.shots,
        error=job.error,
    )


def _get_job(job_id: int, db: Session, user: User) -> SimulationJob:
    job = db.get(SimulationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.user_id != user.id and user.role not in {"instructor", "admin"}:
        raise HTTPException(status_code=403, detail="Not your job")
    return job


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    limit: int = 20,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[JobOut]:
    rows = db.scalars(
        select(SimulationJob)
        .where(SimulationJob.user_id == user.id)
        .order_by(desc(SimulationJob.id))
        .limit(min(limit, 100))
    ).all()
    return [
        JobOut(
            id=j.id, status=j.status, backend=j.backend, mode=j.mode, shots=j.shots, error=j.error
        )
        for j in rows
    ]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> JobOut:
    job = _get_job(job_id, db, user)
    return JobOut(
        id=job.id,
        status=job.status,
        backend=job.backend,
        mode=job.mode,
        shots=job.shots,
        error=job.error,
    )


@router.get("/jobs/{job_id}/result", response_model=JobResultOut)
def get_job_result(
    job_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> JobResultOut:
    job = _get_job(job_id, db, user)
    return JobResultOut(id=job.id, status=job.status, result=job.result, error=job.error)


# --------------------------------------------------------------------------- #
# QASM3 + exports
# --------------------------------------------------------------------------- #
@router.post("/qasm/export", response_class=PlainTextResponse)
def export_qasm(payload: InspectIn, user: User = Depends(get_current_user)) -> str:
    return to_qasm3(_load_ir(payload.circuit_ir))


@router.post("/qasm/import")
def import_qasm(payload: QasmIn, user: User = Depends(get_current_user)) -> dict[str, Any]:
    try:
        ir = from_qasm3(payload.qasm3, payload.name)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Could not parse QASM3: {exc}") from exc
    return {"circuit_ir": ir.to_dict(), "is_dynamic": ir.is_dynamic()}


@router.post("/export/{framework}", response_class=PlainTextResponse)
def export_code(
    framework: str, payload: InspectIn, user: User = Depends(get_current_user)
) -> str:
    ir = _load_ir(payload.circuit_ir)
    shots = payload.shots or 1024
    if framework == "qiskit":
        return codegen_qiskit.generate(ir, shots)
    if framework == "cirq":
        return codegen_cirq.generate(ir, shots)
    if framework == "qasm3":
        return to_qasm3(ir)
    raise HTTPException(status_code=400, detail="framework must be qiskit, cirq or qasm3")
