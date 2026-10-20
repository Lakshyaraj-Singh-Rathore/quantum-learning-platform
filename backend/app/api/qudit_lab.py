"""FastAPI endpoints for Qudit Lab (Beta)."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user
from app.models.user import User
from app.quantum.qudit_lab import (
    DIMENSION_MAX_QUDITS,
    EXPANDED_MAX_QUDITS,
    GATE_CATALOGUE,
    CircuitValidationReport,
    MatrixSliceRequest,
    MatrixSliceResponse,
    QuditCircuit,
    SimulationRequest,
    SimulationResult,
    get_all_qudit_presets,
    simulate_qudit_circuit,
    slice_density_matrix,
    validate_qudit_circuit,
)

router = APIRouter(prefix="/qudit", tags=["qudit_lab"])


@router.get("/limits")
def get_resource_limits() -> dict[str, Any]:
    """Returns configured per-dimension safety caps, memory budgets, and scaling formulas."""
    return {
        "safe_limits": DIMENSION_MAX_QUDITS,
        "expanded_limits": EXPANDED_MAX_QUDITS,
        "supported_dimensions": [2, 3, 4, 5],
        "default_budget_bytes": 2 * 1024 * 1024 * 1024,
        "memory_formula": "M = 16 * D^2 bytes (complex128, D = product(d_i))",
        "description": "Initial safety limits are enforced on the backend to guarantee stable execution on standard host environments.",
    }


@router.get("/catalogue")
def get_gate_catalogue() -> list[dict[str, Any]]:
    """Returns the verified dimension-aware qudit gate catalogue."""
    return GATE_CATALOGUE


@router.get("/presets")
def get_presets(dimension: int = Query(default=3, ge=2, le=5)) -> list[dict[str, Any]]:
    """Returns verified educational presets tailored to dimension d."""
    return get_all_qudit_presets(dimension)


@router.post("/validate", response_model=CircuitValidationReport)
def validate_circuit_endpoint(circuit: QuditCircuit) -> CircuitValidationReport:
    """Validates circuit topology, gate operand compatibility, and memory budget before execution."""
    return validate_qudit_circuit(circuit)


@router.post("/simulate", response_model=SimulationResult)
def simulate_circuit_endpoint(
    payload: SimulationRequest,
    user: User = Depends(get_current_user),
) -> SimulationResult:
    """Executes genuine density-matrix simulation throughout circuit execution."""
    # Backend safety validation
    validation = validate_qudit_circuit(payload.circuit)
    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail=f"Circuit validation rejected: {'; '.join(validation.errors)}"
        )

    try:
        return simulate_qudit_circuit(payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Qudit simulation error: {exc}") from exc


@router.post("/slice", response_model=MatrixSliceResponse)
def get_matrix_slice_endpoint(
    payload: MatrixSliceRequest,
    user: User = Depends(get_current_user),
) -> MatrixSliceResponse:
    """Retrieves a 2D slice of the density matrix for large Hilbert space visualizations."""
    validation = validate_qudit_circuit(payload.circuit)
    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail=f"Circuit validation rejected: {'; '.join(validation.errors)}"
        )

    try:
        return slice_density_matrix(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Density matrix slice error: {exc}") from exc
