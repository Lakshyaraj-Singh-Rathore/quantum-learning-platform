"""FastAPI endpoints for Smart Composer (Generation & Simplification)."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import get_current_user
from app.models.user import User
from app.quantum.ir import CircuitIR
from app.quantum.smart_composer import (
    GenerationResult,
    GenerationTaskSpec,
    OptimizationObjective,
    SimplificationResult,
    TransformationRule,
    generate,
    get_all_rules,
    get_job_status,
    simplify,
)

router = APIRouter(prefix="/smart-composer", tags=["smart_composer"])


class SimplifyRequest(BaseModel):
    circuit_ir: dict[str, Any]
    objective: OptimizationObjective = Field(default=OptimizationObjective.MIN_GATES)


@router.get("/rules", response_model=list[TransformationRule])
def list_rules() -> list[TransformationRule]:
    """Return all curated, mathematically verified transformation rules."""
    return get_all_rules()


@router.post("/generate", response_model=GenerationResult)
def generate_circuit(
    task: GenerationTaskSpec,
    user: User = Depends(get_current_user),
) -> GenerationResult:
    """Generate a quantum circuit from a natural-language task with oracle verification and bounded repair."""
    try:
        return generate(task)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Circuit generation failed: {exc}") from exc


@router.post("/simplify", response_model=SimplificationResult)
def simplify_circuit_endpoint(
    payload: SimplifyRequest,
    user: User = Depends(get_current_user),
) -> SimplificationResult:
    """Analyze and simplify an existing circuit with RAG rules, Qiskit passes, and independent verification."""
    try:
        ir = CircuitIR.model_validate(payload.circuit_ir)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid circuit IR: {exc}") from exc

    try:
        return simplify(ir, objective=payload.objective)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Circuit simplification failed: {exc}") from exc


@router.get("/jobs/{job_id}")
def check_job(
    job_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Check asynchronous or background simplification job status."""
    status = get_job_status(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return status
