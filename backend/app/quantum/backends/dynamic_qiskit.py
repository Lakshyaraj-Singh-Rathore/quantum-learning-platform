"""Qiskit-based dynamic execution engine.

Runs circuits with runtime classical feedback shot-by-shot over a Qiskit
``Statevector``: gates evolve the state, measurements sample and collapse it,
and if/else, for and while blocks are evaluated against live classical bits.

Safety rails: max qubits, max shots and a hard while-loop iteration cap.
"""

from __future__ import annotations

import random
from typing import Optional

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from app.config import get_settings
from app.quantum.backends.base import BackendError, Timer, make_result, statevector_to_json
from app.quantum.ir import CircuitIR, Op
from app.quantum.normalize import append_op_to_qiskit

NAME = "qiskit_dynamic"


class WhileCapExceeded(BackendError):
    """Raised when a while loop hits the hard iteration cap."""


class DynamicLimitError(BackendError):
    pass


class _ShotState:
    __slots__ = ("sv", "cbits", "n_qubits", "while_hits", "rng")

    def __init__(self, n_qubits: int, n_clbits: int, rng: random.Random) -> None:
        self.sv = Statevector.from_int(0, dims=2**n_qubits)
        self.cbits = [0] * n_clbits
        self.n_qubits = n_qubits
        self.while_hits = 0
        self.rng = rng


def run(
    ir: CircuitIR,
    shots: int = 1024,
    *,
    seed: Optional[int] = None,
    strict_while_cap: bool = False,
) -> dict:
    """Execute a dynamic circuit and return the standardized result JSON."""
    settings = get_settings()

    if ir.n_qubits > settings.max_dynamic_qubits:
        raise DynamicLimitError(
            f"Dynamic execution is limited to {settings.max_dynamic_qubits} qubits "
            f"(circuit uses {ir.n_qubits})."
        )
    if shots > settings.max_dynamic_shots:
        raise DynamicLimitError(
            f"Dynamic execution is limited to {settings.max_dynamic_shots} shots (got {shots})."
        )

    rng = random.Random(seed)
    counts: dict[str, int] = {}
    warnings: list[str] = ["Dynamic circuit executed via the Qiskit dynamic engine."]
    cap_hits = 0
    last_state: Optional[Statevector] = None

    with Timer() as timer:
        for _ in range(shots):
            state = _ShotState(ir.n_qubits, ir.n_clbits, rng)
            try:
                _exec_ops(sorted(ir.ops, key=lambda o: o.layer), state, settings.while_cap)
            except WhileCapExceeded:
                cap_hits += 1
                if strict_while_cap:
                    raise
            last_state = state.sv
            key = "".join(str(state.cbits[i]) for i in reversed(range(ir.n_clbits)))
            counts[key] = counts.get(key, 0) + 1

    if cap_hits:
        warnings.append(
            f"While-loop iteration cap ({settings.while_cap}) reached in {cap_hits}/{shots} shot(s);"
            " those shots were truncated."
        )

    statevector = None
    if shots == 1 and last_state is not None:
        statevector = statevector_to_json(last_state.data)

    return make_result(
        backend=NAME,
        counts=counts,
        shots=shots,
        n_qubits=ir.n_qubits,
        runtime=timer.seconds,
        statevector=statevector,
        warnings=warnings,
        metadata={
            "mode": "dynamic",
            "while_cap": settings.while_cap,
            "while_cap_hits": cap_hits,
        },
    )


def _exec_ops(ops: list[Op], state: _ShotState, while_cap: int) -> None:
    for op in ops:
        _exec_op(op, state, while_cap)


def _exec_op(op: Op, state: _ShotState, while_cap: int) -> None:  # noqa: C901 - interpreter
    kind = op.kind

    if kind == "barrier":
        return

    if kind == "gate":
        if op.condition is not None and not op.condition.evaluate(state.cbits):
            return
        state.sv = state.sv.evolve(_single_op_circuit(op, state.n_qubits))
        return

    if kind == "measure":
        qubit = op.qubits[0]
        clbit = op.clbits[0] if op.clbits else qubit
        outcome, state.sv = _measure_qubit(state.sv, qubit, state.n_qubits, state.rng)
        state.cbits[clbit] = outcome
        return

    if kind == "reset":
        for qubit in op.qubits:
            outcome, state.sv = _measure_qubit(state.sv, qubit, state.n_qubits, state.rng)
            if outcome == 1:
                flip = QuantumCircuit(state.n_qubits)
                flip.x(qubit)
                state.sv = state.sv.evolve(flip)
        return

    if kind == "if":
        taken = op.condition.evaluate(state.cbits) if op.condition else True
        _exec_ops(op.body if taken else op.else_body, state, while_cap)
        return

    if kind == "for":
        for _ in range(op.loop_n or 0):
            _exec_ops(op.body, state, while_cap)
        return

    if kind == "while":
        iterations = 0
        while op.condition is None or op.condition.evaluate(state.cbits):
            if iterations >= while_cap:
                raise WhileCapExceeded(
                    f"while loop exceeded the hard cap of {while_cap} iterations"
                )
            _exec_ops(op.body, state, while_cap)
            iterations += 1
        return

    if kind == "box":
        _exec_ops(op.body, state, while_cap)
        return

    raise BackendError(f"unsupported op kind in dynamic engine: {kind}")


def _single_op_circuit(op: Op, n_qubits: int) -> QuantumCircuit:
    circ = QuantumCircuit(n_qubits)
    append_op_to_qiskit(circ, op)
    return circ


def _measure_qubit(
    sv: Statevector, qubit: int, n_qubits: int, rng: random.Random
) -> tuple[int, Statevector]:
    """Sample one qubit and collapse the state (Qiskit little-endian order)."""
    probs = sv.probabilities([qubit])
    p1 = float(probs[1]) if len(probs) > 1 else 0.0
    outcome = 1 if rng.random() < p1 else 0

    data = np.asarray(sv.data, dtype=complex).copy()
    mask = 1 << qubit
    for index in range(data.size):
        if ((index & mask) >> qubit) != outcome:
            data[index] = 0.0
    norm = float(np.linalg.norm(data))
    if norm == 0.0:  # numerical fallback: the other branch was actually taken
        outcome = 1 - outcome
        data = np.asarray(sv.data, dtype=complex).copy()
        for index in range(data.size):
            if ((index & mask) >> qubit) != outcome:
                data[index] = 0.0
        norm = float(np.linalg.norm(data)) or 1.0
    return outcome, Statevector(data / norm)


__all__ = ["run", "NAME", "WhileCapExceeded", "DynamicLimitError"]
