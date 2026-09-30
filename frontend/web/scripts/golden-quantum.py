"""Regenerate the golden numbers the TypeScript result maths is checked against.

    python scripts/golden-quantum.py > test-fixtures/quantum-golden.json

Run it from the backend virtualenv (numpy lives there):

    ../../../.venv-ql/bin/python scripts/golden-quantum.py

The circuits here are the ones a learner actually meets first (Bell, GHZ, a
superposition with a phase) plus a pseudo-random state that exercises
non-trivial reduced density matrices. Every value is derived with the SAME
formulas frontend/lib/viz.py uses, so the fixture is the numpy truth and
scripts/golden-quantum.mts is the check that the port agrees.
"""

from __future__ import annotations

import json
import math

import numpy as np

np.random.seed(20250930)

CASES: list[tuple[str, np.ndarray]] = []


def normalise(vector: np.ndarray) -> np.ndarray:
    return vector / np.linalg.norm(vector)


# Bell state (|00> + |11>)/sqrt(2): maximally entangled, each qubit maximally mixed.
bell = np.zeros(4, dtype=complex)
bell[0] = 1 / np.sqrt(2)
bell[3] = 1 / np.sqrt(2)
CASES.append(("bell", bell))

# GHZ on three qubits.
ghz = np.zeros(8, dtype=complex)
ghz[0] = 1 / np.sqrt(2)
ghz[7] = 1 / np.sqrt(2)
CASES.append(("ghz3", ghz))

# Two qubits, both in superposition but separable: |++>.
plus_plus = np.full(4, 0.5, dtype=complex)
CASES.append(("plus_plus", plus_plus))

# A single qubit with a relative phase: (|0> + i|1>)/sqrt(2).
phase_qubit = np.array([1, 1j], dtype=complex) / np.sqrt(2)
CASES.append(("phase_qubit", phase_qubit))

# Three qubits, amplitudes and phases everywhere: exercises partial traces.
random3 = normalise(np.random.normal(size=8) + 1j * np.random.normal(size=8))
CASES.append(("random3", random3))

# Four qubits, to catch an off-by-one in bit ordering (qubit 0 is the LSB).
random4 = normalise(np.random.normal(size=16) + 1j * np.random.normal(size=16))
CASES.append(("random4", random4))


def reduced_density_matrix(amplitudes: np.ndarray, n_qubits: int, qubit: int) -> np.ndarray:
    tensor = amplitudes.reshape([2] * n_qubits)
    axis = n_qubits - 1 - qubit
    moved = np.moveaxis(tensor, axis, 0).reshape(2, -1)
    return moved @ moved.conj().T


def bloch_vector(rho: np.ndarray) -> tuple[float, float, float]:
    x = np.array([[0, 1], [1, 0]], dtype=complex)
    y = np.array([[0, -1j], [1j, 0]], dtype=complex)
    z = np.array([[1, 0], [0, -1]], dtype=complex)
    return (
        float(np.real(np.trace(rho @ x))),
        float(np.real(np.trace(rho @ y))),
        float(np.real(np.trace(rho @ z))),
    )


def entropy(rho: np.ndarray) -> float:
    values = np.linalg.eigvalsh(rho)
    return float(-sum(v * math.log2(v) for v in values if v > 1e-12))


def purity(rho: np.ndarray) -> float:
    values = np.linalg.eigvalsh(rho)
    return float(sum(v * v for v in values))


def relative_phases(amplitudes: np.ndarray) -> list[float]:
    populated = np.flatnonzero(np.abs(amplitudes) ** 2 > 1e-12)
    base = np.angle(amplitudes[populated[0]]) if populated.size else 0.0
    out = (np.angle(amplitudes) - base) % (2 * np.pi)
    return [float(v) for v in out]


cases = []
for name, amplitudes in CASES:
    n_qubits = int(round(math.log2(len(amplitudes))))
    per_qubit = []
    for qubit in range(n_qubits):
        rho = reduced_density_matrix(amplitudes, n_qubits, qubit)
        x, y, z = bloch_vector(rho)
        length = math.sqrt(x * x + y * y + z * z)
        theta = math.degrees(math.acos(max(-1.0, min(1.0, z / length)))) if length > 1e-12 else None
        phi = math.degrees(math.atan2(y, x)) % 360.0 if length > 1e-12 else None
        per_qubit.append(
            {
                "qubit": qubit,
                "x": x,
                "y": y,
                "z": z,
                "theta": theta,
                "phi": phi,
                "entropy": entropy(rho),
                "purity": purity(rho),
            }
        )

    rho_full = np.outer(amplitudes, amplitudes.conj())
    cases.append(
        {
            "name": name,
            "n_qubits": n_qubits,
            "statevector": [[float(a.real), float(a.imag)] for a in amplitudes],
            "probabilities": [float(abs(a) ** 2) for a in amplitudes],
            "relative_phases": relative_phases(amplitudes),
            "per_qubit": per_qubit,
            "purity": purity(rho_full),
        }
    )

print(json.dumps({"cases": cases}, indent=2))
