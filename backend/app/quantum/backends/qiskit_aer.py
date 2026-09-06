"""Qiskit Aer static simulation backend."""

from __future__ import annotations

from typing import Optional

from qiskit import transpile
from qiskit.quantum_info import Statevector

from app.quantum.backends.base import BackendError, Timer, make_result, statevector_to_json
from app.quantum.ir import CircuitIR
from app.quantum.normalize import strip_measurements, to_qiskit

NAME = "qiskit_aer"


def run(ir: CircuitIR, shots: int = 1024, *, seed: Optional[int] = None) -> dict:
    try:
        from qiskit_aer import AerSimulator
    except ImportError as exc:  # pragma: no cover
        raise BackendError("qiskit-aer is not installed") from exc

    circ = to_qiskit(ir, include_measurements=True)
    warnings: list[str] = []

    if not ir.has_measurements():
        circ.measure_all(add_bits=False) if circ.num_clbits >= circ.num_qubits else None
        for q in range(min(circ.num_qubits, circ.num_clbits)):
            circ.measure(q, q)
        warnings.append("No measurements in circuit; measured all qubits automatically.")

    sim = AerSimulator()
    with Timer() as timer:
        compiled = transpile(circ, sim)
        job = sim.run(compiled, shots=shots, seed_simulator=seed)
        counts = job.result().get_counts()

    counts = {k.replace(" ", ""): int(v) for k, v in counts.items()}

    statevector = None
    try:
        pure = strip_measurements(to_qiskit(ir, include_measurements=False))
        statevector = statevector_to_json(Statevector.from_instruction(pure).data)
    except Exception:  # noqa: BLE001 - reset/mid-measure make this undefined
        warnings.append("Statevector unavailable (circuit is not purely unitary).")

    return make_result(
        backend=NAME,
        counts=counts,
        shots=shots,
        n_qubits=ir.n_qubits,
        runtime=timer.seconds,
        statevector=statevector,
        warnings=warnings,
        metadata={"mode": "static"},
    )


__all__ = ["run", "NAME"]
