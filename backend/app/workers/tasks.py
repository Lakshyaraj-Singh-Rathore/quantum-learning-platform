"""Celery simulation tasks."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from celery.exceptions import SoftTimeLimitExceeded

from app.config import get_settings
from app.database import SessionLocal
from app.models.job import SimulationJob
from app.quantum.backends import cirq_sim, dynamic_qiskit, pennylane_sim, qbraid_sim, qiskit_aer
from app.quantum.backends.base import BackendError, BackendUnavailable
from app.quantum.ir import CircuitIR
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

STATIC_RUNNERS = {
    "qiskit_aer": qiskit_aer.run,
    "cirq": cirq_sim.run,
    "pennylane": pennylane_sim.run,
    "qbraid": qbraid_sim.run,
}


def resolve_backend(ir: CircuitIR, backend: str, mode: str) -> tuple[str, list[str]]:
    """Pick the engine that will actually execute this circuit."""
    notes: list[str] = []
    dynamic = ir.is_dynamic() if mode == "auto" else mode == "dynamic"

    if dynamic:
        if backend not in {"qiskit_dynamic", "auto", "qiskit_aer"}:
            notes.append(
                f"Backend '{backend}' cannot execute runtime control flow; "
                "routed to the Qiskit dynamic engine."
            )
        return "qiskit_dynamic", notes

    if backend in {"auto", "qiskit_dynamic"}:
        return "qiskit_aer", notes
    if backend not in STATIC_RUNNERS:
        raise BackendError(f"unknown backend '{backend}'")
    return backend, notes


@celery_app.task(bind=True, name="app.workers.tasks.run_simulation")
def run_simulation(self, job_id: int) -> dict:
    db = SessionLocal()
    try:
        job = db.get(SimulationJob, job_id)
        if job is None:
            return {"error": f"job {job_id} not found"}

        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.celery_task_id = self.request.id
        db.commit()

        try:
            ir = CircuitIR.from_dict(job.circuit_ir)
            engine, notes = resolve_backend(ir, job.backend, job.mode)

            if engine == "qiskit_dynamic":
                result = dynamic_qiskit.run(ir, shots=job.shots)
            else:
                result = STATIC_RUNNERS[engine](ir, shots=job.shots)

            if notes:
                result["metadata"]["warnings"] = list(result["metadata"]["warnings"]) + notes
            result["metadata"]["requested_backend"] = job.backend
            result["metadata"]["engine"] = engine

            job.result = result
            job.status = "completed"
            job.error = None
        except SoftTimeLimitExceeded:
            job.status = "failed"
            job.error = (
                "Simulation exceeded the time limit. Reduce qubits, shots or loop iterations."
            )
        except BackendUnavailable as exc:
            job.status = "failed"
            job.error = str(exc)
        except BackendError as exc:
            job.status = "failed"
            job.error = str(exc)
        except Exception as exc:  # noqa: BLE001
            log.exception("simulation job %s failed", job_id)
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"

        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        return {"job_id": job_id, "status": job.status}
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.autograde_attempt")
def autograde_attempt(attempt_id: int) -> dict:
    """Grade a challenge attempt once its simulation job has finished."""
    from app.services.autograder import finalize_attempt

    db = SessionLocal()
    try:
        return finalize_attempt(db, attempt_id)
    finally:
        db.close()


__all__ = ["run_simulation", "autograde_attempt", "resolve_backend"]
