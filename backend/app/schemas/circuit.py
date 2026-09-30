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


class CodeLabCheckIn(BaseModel):
    """Source to run the static Code Lab checks against.

    Deliberately the same two fields as CodeLabIn: the new React UI asks the
    server to check code with the rules the Streamlit page runs locally, so
    there is one implementation of those rules rather than a Python one and a
    TypeScript one that can disagree.
    """

    code: str
    framework: str = "qiskit"


class CodeLabIn(BaseModel):
    """A learner-written program to be compiled into a circuit."""

    code: str
    framework: str = "qiskit"


class CodeLabGenerateIn(BaseModel):
    """A natural-language request for Code Lab source code."""

    prompt: str = Field(min_length=1, max_length=2_000)
    framework: str = "qiskit"
