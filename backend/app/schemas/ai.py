from typing import Any, Optional

from pydantic import BaseModel


class ChatIn(BaseModel):
    message: str
    circuit_ir: Optional[dict[str, Any]] = None
    job_id: Optional[int] = None
    history: list[dict[str, str]] = []


class ChatOut(BaseModel):
    reply: str
    citations: list[dict[str, Any]] = []
    tools_used: list[str] = []


class CodeGenIn(BaseModel):
    circuit_ir: dict[str, Any]
    framework: str = "qiskit"  # qiskit|cirq
    shots: int = 1024
    explain: bool = False


class CodeGenOut(BaseModel):
    framework: str
    code: str
    is_dynamic: bool
    ops: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    explanation: str = ""
    notes: list[str] = []
