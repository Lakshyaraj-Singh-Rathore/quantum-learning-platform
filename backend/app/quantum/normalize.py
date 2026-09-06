"""IR -> Qiskit -> portable basis pipeline.

``append_op_to_qiskit`` is the single source of truth for turning an IR op into
Qiskit instructions; both the static normalization path and the dynamic
statevector engine use it so controlled gates behave identically everywhere.
"""

from __future__ import annotations

from typing import Any

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import (
    HGate,
    IGate,
    PhaseGate,
    RXGate,
    RYGate,
    RZGate,
    SdgGate,
    SGate,
    SwapGate,
    SXGate,
    TdgGate,
    TGate,
    XGate,
    YGate,
    ZGate,
)

from app.quantum.ir import CircuitIR, Op

#: Portable basis every non-Qiskit backend can consume.
PORTABLE_BASIS = ["rx", "ry", "rz", "cx"]

GATE_CLASSES: dict[str, Any] = {
    "h": HGate,
    "x": XGate,
    "y": YGate,
    "z": ZGate,
    "id": IGate,
    "s": SGate,
    "sdg": SdgGate,
    "t": TGate,
    "tdg": TdgGate,
    "sx": SXGate,
    "swap": SwapGate,
    "p": PhaseGate,
    "rx": RXGate,
    "ry": RYGate,
    "rz": RZGate,
}


class NormalizeError(ValueError):
    pass


def append_op_to_qiskit(circ: QuantumCircuit, op: Op) -> None:
    """Append a single leaf IR op to a Qiskit circuit (controls included)."""
    if op.kind == "barrier":
        circ.barrier(*(op.qubits or []))
        return
    if op.kind == "reset":
        for q in op.qubits:
            circ.reset(q)
        return
    if op.kind == "measure":
        q = op.qubits[0]
        c = op.clbits[0] if op.clbits else q
        circ.measure(q, c)
        return
    if op.kind != "gate":
        raise NormalizeError(f"cannot append control-flow op '{op.kind}' directly")

    name = op.gate or "id"
    params = [p.value for p in op.params]

    # multi-controlled X has a dedicated efficient Qiskit builder
    if name == "x" and len(op.controls) >= 1:
        if len(op.controls) == 1:
            circ.cx(op.controls[0], op.qubits[0])
        elif len(op.controls) == 2:
            circ.ccx(op.controls[0], op.controls[1], op.qubits[0])
        else:
            circ.mcx(list(op.controls), op.qubits[0])
        return

    cls = GATE_CLASSES.get(name)
    if cls is None:
        raise NormalizeError(f"unsupported gate: {name}")
    gate = cls(*params)
    if op.controls:
        gate = gate.control(len(op.controls))
        circ.append(gate, list(op.controls) + list(op.qubits))
    else:
        circ.append(gate, list(op.qubits))


def to_qiskit(ir: CircuitIR, include_measurements: bool = True) -> QuantumCircuit:
    """Build a Qiskit circuit from a *static* IR (control flow is rejected)."""
    circ = QuantumCircuit(ir.n_qubits, ir.n_clbits, name=ir.name)
    for op in sorted(ir.ops, key=lambda o: o.layer):
        if op.kind in {"if", "while"}:
            raise NormalizeError(
                "runtime control flow cannot be compiled statically; "
                "use the Qiskit dynamic engine"
            )
        _append_recursive(circ, op, include_measurements)
    return circ


def _append_recursive(circ: QuantumCircuit, op: Op, include_measurements: bool) -> None:
    if op.kind == "for":
        for _ in range(op.loop_n or 0):
            for child in op.body:
                _append_recursive(circ, child, include_measurements)
        return
    if op.kind == "box":
        for child in op.body:
            _append_recursive(circ, child, include_measurements)
        return
    if op.kind == "measure" and not include_measurements:
        return
    append_op_to_qiskit(circ, op)


def strip_barriers(circ: QuantumCircuit) -> QuantumCircuit:
    out = QuantumCircuit(circ.num_qubits, circ.num_clbits, name=circ.name)
    for inst in circ.data:
        if inst.operation.name == "barrier":
            continue
        out.append(inst.operation, inst.qubits, inst.clbits)
    return out


def strip_measurements(circ: QuantumCircuit) -> QuantumCircuit:
    out = QuantumCircuit(circ.num_qubits, circ.num_clbits, name=circ.name)
    for inst in circ.data:
        if inst.operation.name in {"measure", "barrier", "reset"}:
            continue
        out.append(inst.operation, inst.qubits, inst.clbits)
    return out


def normalize(ir: CircuitIR, basis: list[str] | None = None) -> QuantumCircuit:
    """IR -> Qiskit -> transpiled to the portable basis for cross-backend use."""
    circ = to_qiskit(ir, include_measurements=True)
    return transpile(circ, basis_gates=basis or PORTABLE_BASIS, optimization_level=1)


def measured_qubit_map(ir: CircuitIR) -> dict[int, int]:
    """qubit -> classical bit, using the last measurement of each qubit."""
    mapping: dict[int, int] = {}
    for op in sorted(ir.ops, key=lambda o: o.layer):
        if op.kind == "measure" and op.qubits:
            mapping[op.qubits[0]] = op.clbits[0] if op.clbits else op.qubits[0]
    return mapping


__all__ = [
    "to_qiskit",
    "normalize",
    "append_op_to_qiskit",
    "strip_barriers",
    "strip_measurements",
    "measured_qubit_map",
    "PORTABLE_BASIS",
    "NormalizeError",
]
