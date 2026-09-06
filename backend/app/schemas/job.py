from typing import Any, Optional

from pydantic import BaseModel, Field


class JobCreate(BaseModel):
    circuit_ir: dict[str, Any]
    backend: str = "qiskit_aer"
    shots: int = Field(default=1024, ge=1, le=8192)
    mode: str = "auto"  # auto|static|dynamic


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
