"""Configurable T1 / T2 / readout noise model for the Aer backend.

These are **simulation parameters you choose**, not calibration data pulled
from any real device. They reproduce the *kind* of errors a superconducting
chip shows -- amplitude damping (T1), dephasing (T2) and misreported bits
(readout) -- so a student can see why a textbook-perfect circuit degrades.

Virtual-Z gates (z, s, sdg, t, tdg, rz, p) are treated as zero-duration and
pick up no thermal error, which matches how hardware implements them: as a
frame change in software rather than an extra microwave pulse.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Instructions that correspond to a real pulse and therefore accumulate T1/T2.
PULSE_1Q = ("h", "x", "y", "rx", "ry", "sx", "id", "u", "u2", "u3")
PULSE_2Q = ("cx", "cz", "swap")
PULSE_3Q = ("ccx",)

#: Kept un-decomposed so that one user-facing gate is roughly one noise event.
BASIS_GATES = [
    "h", "x", "y", "z", "s", "sdg", "t", "tdg",
    "rx", "ry", "rz", "id", "sx", "p", "u", "u1", "u2", "u3",
    "cx", "cz", "swap", "ccx",
    "measure", "reset", "barrier", "delay",
]


@dataclass
class NoiseParams:
    """Noise knobs. All times in microseconds."""

    enabled: bool = False
    t1_us: float = 50.0
    t2_us: float = 30.0
    readout_error: float = 0.02
    gate_time_1q_us: float = 0.10
    gate_time_2q_us: float = 0.40
    gate_time_3q_us: float = 1.00

    def clamped(self) -> tuple["NoiseParams", list[str]]:
        """Return physically valid parameters plus notes on what was changed.

        Physics constrains T2 <= 2*T1; Aer raises if that is violated, so we
        clamp and say so rather than failing the student's run.
        """
        notes: list[str] = []
        t1 = max(float(self.t1_us), 1e-6)
        t2 = max(float(self.t2_us), 1e-6)
        if t2 > 2.0 * t1:
            t2 = 2.0 * t1
            notes.append(f"T2 clamped to 2*T1 = {t2:.4g} us (physical limit).")

        readout = float(self.readout_error)
        if readout > 1.0:  # someone passed a percentage
            notes.append(f"Readout {readout} interpreted as {readout / 100:.2%}.")
            readout = readout / 100.0
        readout = min(0.5, max(0.0, readout))

        return (
            NoiseParams(
                enabled=bool(self.enabled),
                t1_us=t1,
                t2_us=t2,
                readout_error=readout,
                gate_time_1q_us=max(float(self.gate_time_1q_us), 0.0),
                gate_time_2q_us=max(float(self.gate_time_2q_us), 0.0),
                gate_time_3q_us=max(float(self.gate_time_3q_us), 0.0),
            ),
            notes,
        )


def _tensor(error, copies: int):
    out = error
    for _ in range(copies - 1):
        nxt = error.copy() if hasattr(error, "copy") else error
        out = out.tensor(nxt) if hasattr(out, "tensor") else out.expand(nxt)
    return out


def _attach(model, error, gates) -> None:
    for gate in gates:
        try:
            model.add_all_qubit_quantum_error(
                error.copy() if hasattr(error, "copy") else error, [gate]
            )
        except Exception:  # noqa: BLE001 - gate simply not in this Aer build
            continue


def build_noise_model(params: NoiseParams, include_readout: bool = True):
    """Build an Aer NoiseModel. Returns (model, notes)."""
    try:
        from qiskit_aer.noise import (
            NoiseModel,
            ReadoutError,
            thermal_relaxation_error,
        )
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("qiskit-aer is required for noise simulation") from exc

    clean, notes = params.clamped()
    model = NoiseModel()

    if clean.gate_time_1q_us > 0:
        _attach(
            model,
            thermal_relaxation_error(clean.t1_us, clean.t2_us, clean.gate_time_1q_us),
            PULSE_1Q,
        )
    if clean.gate_time_2q_us > 0:
        base = thermal_relaxation_error(clean.t1_us, clean.t2_us, clean.gate_time_2q_us)
        _attach(model, _tensor(base, 2), PULSE_2Q)
    if clean.gate_time_3q_us > 0:
        base = thermal_relaxation_error(clean.t1_us, clean.t2_us, clean.gate_time_3q_us)
        _attach(model, _tensor(base, 3), PULSE_3Q)

    if include_readout and clean.readout_error > 0:
        rate = clean.readout_error
        try:
            model.add_all_qubit_readout_error(
                ReadoutError([[1.0 - rate, rate], [rate, 1.0 - rate]])
            )
        except Exception as exc:  # noqa: BLE001
            notes.append(f"Readout error not attached: {exc}")

    return model, notes


def total_variation(p: dict[str, float], q: dict[str, float]) -> float:
    """Total variation distance between two probability dicts."""
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def entanglement_entropy(amplitudes, n_qubits: int) -> tuple[float, float | None]:
    """Max single-qubit von Neumann entropy in bits, plus 2-qubit concurrence.

    Entropy 0 means separable; 1 means the qubit is maximally entangled with
    the rest of the register.
    """
    import numpy as np

    data = np.asarray(amplitudes, dtype=complex).ravel()
    if n_qubits < 2 or data.size != 2**n_qubits:
        return 0.0, None

    tensor = data.reshape([2] * n_qubits)
    best = 0.0
    for qubit in range(n_qubits):
        axis = n_qubits - 1 - qubit
        moved = np.moveaxis(tensor, axis, 0).reshape(2, -1)
        rho = moved @ moved.conj().T
        eigenvalues = np.clip(np.real(np.linalg.eigvalsh(rho)), 0.0, 1.0)
        nonzero = eigenvalues[eigenvalues > 1e-12]
        entropy = float(-np.sum(nonzero * np.log2(nonzero))) if nonzero.size else 0.0
        best = max(best, min(1.0, entropy))

    concurrence = None
    if n_qubits == 2:
        sigma_y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        yy = np.kron(sigma_y, sigma_y)
        rho = np.outer(data, data.conj())
        product = rho @ (yy @ rho.conj() @ yy)
        eigenvalues = np.sort(
            np.sqrt(np.clip(np.real(np.linalg.eigvals(product)), 0.0, None))
        )[::-1]
        concurrence = float(
            min(1.0, max(0.0, eigenvalues[0] - eigenvalues[1:].sum()))
        )

    return best, concurrence


__all__ = [
    "NoiseParams",
    "build_noise_model",
    "total_variation",
    "entanglement_entropy",
    "BASIS_GATES",
]
