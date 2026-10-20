"""FastAPI endpoints for Quantum Noise Lab."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import get_current_user
from app.models.user import User
from app.quantum.ir import CircuitIR
from app.quantum.noise_lab import (
    NOISE_CATALOGUE,
    PRESET_CONFIGS,
    NoiseConfig,
    NoiseSimulationResult,
    ValidationReport,
    run_parameter_sweep,
    simulate_noise_experiment,
    validate_noise_config,
)

router = APIRouter(prefix="/noise", tags=["noise_lab"])


class NoiseValidateRequest(BaseModel):
    noise_config: NoiseConfig
    circuit_qubits: int | None = None


class NoiseSimulateRequest(BaseModel):
    circuit_ir: dict[str, Any]
    noise_config: NoiseConfig
    shots: int = Field(default=1024, ge=1, le=10000)
    seed: int | None = Field(default=42)


class NoiseSweepRequest(BaseModel):
    circuit_ir: dict[str, Any]
    noise_config: NoiseConfig
    param_path: str = Field(description="Dotted path e.g. 'decoherence.t1_us' or 'stochastic.depolarizing_2q'")
    start_val: float
    end_val: float
    steps: int = Field(default=8, ge=2, le=20)
    shots: int = Field(default=512, ge=1, le=4096)


@router.get("/catalogue")
def get_noise_catalogue() -> list[dict[str, Any]]:
    """Return the comprehensive quantum noise mechanism catalogue."""
    return NOISE_CATALOGUE


@router.get("/presets")
def get_noise_presets() -> dict[str, Any]:
    """Return pedagogical and hardware-inspired noise configuration presets."""
    return {k: v.model_dump() for k, v in PRESET_CONFIGS.items()}


@router.post("/validate", response_model=ValidationReport)
def validate_noise(payload: NoiseValidateRequest) -> ValidationReport:
    """Validate a noise configuration against quantum physical laws."""
    return validate_noise_config(payload.noise_config, circuit_qubits=payload.circuit_qubits)


@router.post("/simulate", response_model=NoiseSimulationResult)
def run_noise_simulation(
    payload: NoiseSimulateRequest,
    user: User = Depends(get_current_user),
) -> NoiseSimulationResult:
    """Simulate a circuit under ideal vs noisy conditions and compute quantum state metrics."""
    try:
        ir = CircuitIR.model_validate(payload.circuit_ir)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid circuit IR: {exc}") from exc

    validation = validate_noise_config(payload.noise_config, circuit_qubits=ir.n_qubits)
    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid noise configuration: {'; '.join(validation.errors)}"
        )

    try:
        return simulate_noise_experiment(
            ir=ir,
            config=payload.noise_config,
            shots=payload.shots,
            seed=payload.seed,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Noise simulation error: {exc}") from exc


@router.post("/sweep")
def run_noise_sweep(
    payload: NoiseSweepRequest,
    user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Run an automated parameter sweep over a specified noise parameter."""
    try:
        ir = CircuitIR.model_validate(payload.circuit_ir)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid circuit IR: {exc}") from exc

    try:
        return run_parameter_sweep(
            ir=ir,
            base_config=payload.noise_config,
            param_path=payload.param_path,
            start_val=payload.start_val,
            end_val=payload.end_val,
            steps=payload.steps,
            shots=payload.shots,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parameter sweep error: {exc}") from exc
