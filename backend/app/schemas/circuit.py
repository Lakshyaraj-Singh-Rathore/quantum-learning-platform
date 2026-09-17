from typing import Any, Optional

from pydantic import BaseModel, Field


class CircuitIn(BaseModel):
    name: str = "untitled"
    circuit_ir: dict[str, Any]
    description: str = ""


class CircuitOut(BaseModel):
    id: int
    name: str
    description: str
    circuit_ir: dict[str, Any]
    qasm3: str
    is_dynamic: bool


class QasmIn(BaseModel):
    qasm3: str
    name: str = "imported"


class InspectIn(BaseModel):
    circuit_ir: dict[str, Any]
    backend: Optional[str] = None
    shots: Optional[int] = None


class CodeLabIn(BaseModel):
    """A learner-written program to be compiled into a circuit."""

    code: str
    framework: str = "qiskit"


class CodeLabGenerateIn(BaseModel):
    """A natural-language request for Code Lab source code."""

    prompt: str = Field(min_length=1, max_length=2_000)
    framework: str = "qiskit"
