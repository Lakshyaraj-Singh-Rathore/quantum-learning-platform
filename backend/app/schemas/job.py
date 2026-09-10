from typing import Any, Optional

from pydantic import BaseModel, Field


class NoiseIn(BaseModel):
    """T1/T2/readout knobs. Teaching parameters, not device calibration."""

    enabled: bool = False
    t1_us: float = Field(default=50.0, gt=0, le=10_000)
    t2_us: float = Field(default=30.0, gt=0, le=20_000)
    readout_error: float = Field(default=0.02, ge=0.0, le=0.5)
    gate_time_1q_us: float = Field(default=0.10, ge=0.0, le=100.0)
    gate_time_2q_us: float = Field(default=0.40, ge=0.0, le=100.0)
    gate_time_3q_us: float = Field(default=1.00, ge=0.0, le=100.0)


class JobCreate(BaseModel):
    circuit_ir: dict[str, Any]
    backend: str = "qiskit_aer"
    shots: int = Field(default=1024, ge=1, le=8192)
    mode: str = "auto"  # auto|static|dynamic
    noise: Optional[NoiseIn] = None


class JobOut(BaseModel):
    id: int
    status: str
    backend: str
    mode: str
    shots: int
    error: Optional[str] = None


class JobResultOut(BaseModel):
    id: int
    status: str
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
