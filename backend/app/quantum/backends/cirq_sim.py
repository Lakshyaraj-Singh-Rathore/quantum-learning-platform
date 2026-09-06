"""Cirq static simulation backend.

Consumes the portable transpiled Qiskit circuit (rx, ry, rz, cx) and rebuilds
it in Cirq so both engines execute the exact same normalized program.
"""

from __future__ import annotations

from typing import Optional

from app.quantum.backends.base import BackendError, Timer, make_result, statevector_to_json
from app.quantum.ir import CircuitIR
from app.quantum.normalize import measured_qubit_map, normalize

NAME = "cirq"


def qiskit_to_cirq(circ, n_qubits: int):
    """Convert a transpiled Qiskit circuit into a Cirq circuit (no measures)."""
    import cirq

    qubits = cirq.LineQubit.range(n_qubits)
    out = cirq.Circuit()
    index = {q: i for i, q in enumerate(circ.qubits)}

    for inst in circ.data:
        name = inst.operation.name
        targets = [qubits[index[q]] for q in inst.qubits]
        params = [float(p) for p in inst.operation.params]
        if name in {"measure", "barrier"}:
            continue
        if name == "rx":
            out.append(cirq.rx(params[0]).on(targets[0]))
        elif name == "ry":
            out.append(cirq.ry(params[0]).on(targets[0]))
        elif name == "rz":
            out.append(cirq.rz(params[0]).on(targets[0]))
        elif name == "cx":
            out.append(cirq.CNOT(targets[0], targets[1]))
        elif name in {"id", "delay"}:
            out.append(cirq.I(targets[0]))
        elif name == "reset":
            out.append(cirq.ResetChannel().on(targets[0]))
        elif name == "global_phase":
            continue
        else:
            raise BackendError(f"gate '{name}' is not in the portable basis for Cirq")
    return out, qubits


def run(ir: CircuitIR, shots: int = 1024, *, seed: Optional[int] = None) -> dict:
    try:
        import cirq
    except ImportError as exc:  # pragma: no cover
        raise BackendError("cirq is not installed") from exc

    warnings: list[str] = []
    normalized = normalize(ir)
    circuit, qubits = qiskit_to_cirq(normalized, ir.n_qubits)

    statevector = None
    try:
        final = cirq.Simulator(seed=seed).simulate(circuit)
        statevector = statevector_to_json(_to_qiskit_order(final.final_state_vector, ir.n_qubits))
    except Exception:  # noqa: BLE001
        warnings.append("Statevector unavailable for this circuit.")

    measured = measured_qubit_map(ir)
    if not measured:
        measured = {q: q for q in range(ir.n_qubits)}
        warnings.append("No measurements in circuit; measured all qubits automatically.")

    sampled = sorted(measured)
    circuit.append(cirq.measure(*[qubits[q] for q in sampled], key="m"))

    with Timer() as timer:
        result = cirq.Simulator(seed=seed).run(circuit, repetitions=shots)

    counts: dict[str, int] = {}
    n_clbits = ir.n_clbits
    for key, freq in result.histogram(key="m").items():
        # cirq packs the first measured qubit as the MOST significant bit
        bits = format(int(key), f"0{len(sampled)}b")
        register = ["0"] * n_clbits
        for position, qubit in enumerate(sampled):
            register[measured[qubit]] = bits[position]
        bitstring = "".join(reversed(register))  # qubit 0 -> rightmost
        counts[bitstring] = counts.get(bitstring, 0) + int(freq)

    return make_result(
        backend=NAME,
        counts=counts,
        shots=shots,
        n_qubits=ir.n_qubits,
        runtime=timer.seconds,
        statevector=statevector,
        warnings=warnings,
        metadata={"mode": "static", "normalized_basis": "rx,ry,rz,cx"},
    )


def _to_qiskit_order(state, n_qubits: int):
    """Cirq orders amplitudes with LineQubit(0) as the most significant bit."""
    import numpy as np

    data = np.asarray(state, dtype=complex)
    if n_qubits <= 1:
        return data
    return data.reshape([2] * n_qubits).transpose(list(range(n_qubits))[::-1]).ravel()


__all__ = ["run", "NAME", "qiskit_to_cirq"]
