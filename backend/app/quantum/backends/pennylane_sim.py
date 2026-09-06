"""PennyLane static simulation backend (default.qubit).

Runs arbitrary static circuits by converting the normalized Qiskit circuit with
``qml.from_qiskit``. PennyLane orders basis states with wire 0 as the MOST
significant bit, so bitstrings are reversed into the Qiskit convention.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from app.quantum.backends.base import BackendError, Timer, make_result, statevector_to_json
from app.quantum.ir import CircuitIR
from app.quantum.normalize import measured_qubit_map, normalize, strip_barriers, strip_measurements

NAME = "pennylane"


def run(ir: CircuitIR, shots: int = 1024, *, seed: Optional[int] = None) -> dict:
    try:
        import pennylane as qml
    except ImportError as exc:  # pragma: no cover
        raise BackendError("pennylane is not installed") from exc

    warnings: list[str] = []
    normalized = strip_barriers(strip_measurements(normalize(ir)))
    n = ir.n_qubits

    try:
        loaded = qml.from_qiskit(normalized)
    except Exception as exc:  # noqa: BLE001
        raise BackendError(f"PennyLane could not import the circuit: {exc}") from exc

    dev = qml.device("default.qubit", wires=n)

    @qml.qnode(dev)
    def probs_node():
        loaded(wires=range(n))
        return qml.probs(wires=range(n))

    @qml.qnode(dev)
    def state_node():
        loaded(wires=range(n))
        return qml.state()

    with Timer() as timer:
        probs = np.asarray(probs_node(), dtype=float)

    statevector = None
    try:
        statevector = statevector_to_json(_to_qiskit_order(np.asarray(state_node()), n))
    except Exception:  # noqa: BLE001
        warnings.append("Statevector unavailable for this circuit.")

    measured = measured_qubit_map(ir)
    if not measured:
        measured = {q: q for q in range(n)}
        warnings.append("No measurements in circuit; measured all qubits automatically.")

    rng = np.random.default_rng(seed)
    probs = np.clip(probs, 0.0, None)
    probs = probs / probs.sum() if probs.sum() else np.full(probs.size, 1.0 / probs.size)
    draws = rng.choice(probs.size, size=shots, p=probs)

    counts: dict[str, int] = {}
    for index, freq in zip(*np.unique(draws, return_counts=True)):
        # PennyLane: wire 0 is the leftmost character
        pl_bits = format(int(index), f"0{n}b")
        register = ["0"] * ir.n_clbits
        for qubit, clbit in measured.items():
            register[clbit] = pl_bits[qubit]
        bitstring = "".join(reversed(register))  # qubit 0 -> rightmost
        counts[bitstring] = counts.get(bitstring, 0) + int(freq)

    return make_result(
        backend=NAME,
        counts=counts,
        shots=shots,
        n_qubits=n,
        runtime=timer.seconds,
        statevector=statevector,
        warnings=warnings,
        metadata={"mode": "static", "device": "default.qubit"},
    )


def _to_qiskit_order(state: np.ndarray, n_qubits: int) -> np.ndarray:
    data = np.asarray(state, dtype=complex)
    if n_qubits <= 1:
        return data
    return data.reshape([2] * n_qubits).transpose(list(range(n_qubits))[::-1]).ravel()


__all__ = ["run", "NAME"]
