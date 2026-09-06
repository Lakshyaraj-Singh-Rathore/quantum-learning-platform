"""Deterministic tools exposed to the AI tutor.

Hard rule: there is NO simulation tool. The assistant can read results that
already exist in Postgres, inspect circuits and generate code, but it can never
launch a simulation job.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.job import SimulationJob
from app.models.user import User
from app.quantum import codegen_cirq, codegen_qiskit
from app.quantum.inspect import inspect_circuit, summarize_circuit
from app.quantum.ir import CircuitIR
from app.quantum.qasm3_codec import to_qasm3

#: Names the model is allowed to call.
ALLOWED_TOOLS = [
    "get_simulation_result",
    "inspect_circuit",
    "summarize_circuit",
    "generate_code_qiskit",
    "generate_code_cirq",
]

#: Explicitly forbidden - documented so the restriction is auditable.
FORBIDDEN_TOOLS = ["run_simulation", "submit_job", "execute_circuit"]


class ToolError(ValueError):
    pass


def get_simulation_result(db: Session, user: User, job_id: int) -> dict[str, Any]:
    """Read-only access to an existing simulation result."""
    job = db.get(SimulationJob, job_id)
    if job is None:
        raise ToolError(f"job {job_id} not found")
    if job.user_id != user.id and user.role not in {"instructor", "admin"}:
        raise ToolError("you do not have access to that job")
    return {
        "job_id": job.id,
        "status": job.status,
        "backend": job.backend,
        "shots": job.shots,
        "error": job.error,
        "result": job.result,
    }


def tool_inspect_circuit(circuit_ir: dict[str, Any], backend: str | None = None) -> dict[str, Any]:
    return inspect_circuit(_ir(circuit_ir), backend)


def tool_summarize_circuit(circuit_ir: dict[str, Any]) -> dict[str, Any]:
    ir = _ir(circuit_ir)
    summary = summarize_circuit(ir)
    summary["qasm3"] = to_qasm3(ir)
    return summary


def generate_code_qiskit(circuit_ir: dict[str, Any], shots: int = 1024) -> dict[str, Any]:
    ir = _ir(circuit_ir)
    return {
        "framework": "qiskit",
        "code": codegen_qiskit.generate(ir, shots),
        "is_dynamic": ir.is_dynamic(),
        "ops": _ops_ast(ir),
        "summary": summarize_circuit(ir),
        "notes": (
            ["Dynamic circuit: uses Qiskit control-flow builders."]
            if ir.is_dynamic()
            else ["Static circuit: runs directly on AerSimulator."]
        ),
    }


def generate_code_cirq(circuit_ir: dict[str, Any], shots: int = 1024) -> dict[str, Any]:
    ir = _ir(circuit_ir)
    dynamic = ir.is_dynamic()
    return {
        "framework": "cirq",
        "code": codegen_cirq.generate(ir, shots),
        "is_dynamic": dynamic,
        "ops": _ops_ast(ir),
        "summary": summarize_circuit(ir),
        "notes": (
            [
                "Dynamic circuit: Cirq has no native runtime control flow, so the "
                "export includes a Python driver implementing if/else, for and while."
            ]
            if dynamic
            else ["Static circuit: pure Cirq circuit."]
        ),
    }


def _ir(circuit_ir: dict[str, Any]) -> CircuitIR:
    try:
        return CircuitIR.from_dict(circuit_ir)
    except Exception as exc:  # noqa: BLE001
        raise ToolError(f"invalid circuit: {exc}") from exc


def _ops_ast(ir: CircuitIR) -> list[dict[str, Any]]:
    """Normalized op list returned alongside generated code for validation."""
    out: list[dict[str, Any]] = []

    def walk(ops: list[Any], depth: int) -> None:
        for op in ops:
            out.append(
                {
                    "kind": op.kind,
                    "gate": op.gate,
                    "qubits": op.qubits,
                    "controls": op.controls,
                    "clbits": op.clbits,
                    "params": [p.expr for p in op.params],
                    "layer": op.layer,
                    "depth": depth,
                    "condition": op.condition.describe() if op.condition else None,
                    "label": op.label(),
                }
            )
            walk(op.body, depth + 1)
            walk(op.else_body, depth + 1)

    walk(sorted(ir.ops, key=lambda o: o.layer), 0)
    return out


__all__ = [
    "ALLOWED_TOOLS",
    "FORBIDDEN_TOOLS",
    "ToolError",
    "get_simulation_result",
    "tool_inspect_circuit",
    "tool_summarize_circuit",
    "generate_code_qiskit",
    "generate_code_cirq",
]
