"""Pure single-qubit state maths for the interactive lessons.

Everything here is deliberately backend-free. The Quantum Playground changes
state on every slider drag, and a round-trip to FastAPI per drag would make it
feel dead; a full recompute here costs about 6 microseconds.

This module owns no drawing. Rendering goes through ``lib.viz``, whose Bloch,
phase-disk and histogram helpers are already verified against analytic physics,
so the playground cannot drift away from the rest of the platform.

Convention matches the platform: a qubit is

    |psi> = cos(theta/2)|0> + e^(i*phi) sin(theta/2)|1>

with theta measured from +Z (so |0> is theta = 0) and phi anticlockwise from
+X. Qiskit bit ordering applies elsewhere: qubit 0 is the rightmost character
of a bitstring.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

SQRT1_2 = 1.0 / math.sqrt(2.0)

#: Single-qubit gates the playground can apply. Restricted to the ones the
#: introductory lessons actually use; the Composer covers the full set.
GATES: dict[str, np.ndarray] = {
    "H": np.array([[SQRT1_2, SQRT1_2], [SQRT1_2, -SQRT1_2]], dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.array([[1, 0], [0, -1]], dtype=complex),
    "S": np.array([[1, 0], [0, 1j]], dtype=complex),
    "T": np.array([[1, 0], [0, np.exp(1j * math.pi / 4)]], dtype=complex),
}

GATE_HELP: dict[str, str] = {
    "H": "Hadamard — turns |0⟩ into an equal superposition",
    "X": "Pauli-X — the quantum NOT, flips |0⟩ and |1⟩",
    "Y": "Pauli-Y — a flip plus a phase",
    "Z": "Pauli-Z — leaves |0⟩ alone, negates |1⟩",
    "S": "Phase — a quarter turn about Z",
    "T": "T — an eighth turn about Z",
}

#: The six cardinal states, as (theta, phi) in degrees.
LANDMARKS: dict[str, tuple[float, float]] = {
    "|0⟩": (0.0, 0.0),
    "|1⟩": (180.0, 0.0),
    "|+⟩": (90.0, 0.0),
    "|−⟩": (90.0, 180.0),
    "|+i⟩": (90.0, 90.0),
    "|−i⟩": (90.0, 270.0),
}


def state_from_angles(theta_deg: float, phi_deg: float) -> np.ndarray:
    """Build |psi> from Bloch angles in degrees."""
    theta = math.radians(theta_deg)
    phi = math.radians(phi_deg)
    alpha = math.cos(theta / 2.0)
    beta = complex(math.cos(phi), math.sin(phi)) * math.sin(theta / 2.0)
    return np.array([alpha, beta], dtype=complex)


def state_from_amplitudes(alpha: float, beta: float) -> np.ndarray:
    """Normalise a pair of real amplitudes into a valid state.

    Sliders let a learner pick any two numbers, but |alpha|^2 + |beta|^2 must
    equal 1. Renormalising quietly is the honest move: it keeps the state
    physical while letting the ratio the learner chose survive.
    """
    vector = np.array([alpha, beta], dtype=complex)
    norm = float(np.linalg.norm(vector))
    if norm < 1e-12:
        return np.array([1.0, 0.0], dtype=complex)
    return vector / norm


def apply_gates(state: np.ndarray, gates: list[str]) -> np.ndarray:
    """Apply gates left to right, the order they appear on a circuit wire."""
    out = np.asarray(state, dtype=complex)
    for name in gates:
        matrix = GATES.get(name.upper())
        if matrix is None:
            raise ValueError(f"unknown gate {name!r}")
        out = matrix @ out
    return out


def probabilities(state: np.ndarray) -> tuple[float, float]:
    """Born rule: probability is the squared magnitude of the amplitude."""
    return float(abs(state[0]) ** 2), float(abs(state[1]) ** 2)


def bloch_angles_of(state: np.ndarray) -> tuple[float, float]:
    """Recover (theta, phi) in degrees from a state vector.

    Global phase is divided out first, because it is unobservable and would
    otherwise make phi meaningless.
    """
    alpha, beta = complex(state[0]), complex(state[1])
    if abs(alpha) > 1e-12:
        phase = alpha / abs(alpha)
        alpha, beta = alpha / phase, beta / phase
    theta = 2.0 * math.acos(max(-1.0, min(1.0, abs(alpha))))
    phi = math.atan2(beta.imag, beta.real) if abs(beta) > 1e-12 else 0.0
    return math.degrees(theta), math.degrees(phi) % 360.0


def ket_string(state: np.ndarray, places: int = 3) -> str:
    """Human-readable |psi> = a|0> + b|1>, with complex parts only when real."""

    def fmt(value: complex) -> str:
        if abs(value.imag) < 1e-9:
            return f"{value.real:.{places}f}"
        if abs(value.real) < 1e-9:
            return f"{value.imag:.{places}f}i"
        sign = "+" if value.imag >= 0 else "−"
        return f"({value.real:.{places}f} {sign} {abs(value.imag):.{places}f}i)"

    return f"{fmt(complex(state[0]))}|0⟩ + {fmt(complex(state[1]))}|1⟩"


def as_result(state: np.ndarray) -> dict[str, Any]:
    """Wrap a state in the result envelope ``lib.viz`` expects.

    Lets the playground reuse the already-verified Bloch sphere, phase disk and
    amplitude table instead of drawing its own and risking a different answer.
    """
    p0, p1 = probabilities(state)
    return {
        "counts": {},
        "probabilities": {"0": p0, "1": p1},
        "statevector": [[float(z.real), float(z.imag)] for z in state],
        "metadata": {"n_qubits": 1, "shots": 0, "backend": "playground"},
    }


def sample(state: np.ndarray, shots: int, seed: int | None = None) -> dict[str, int]:
    """Sample measurement outcomes, so learners see sampling error first-hand.

    A student who only ever sees exact 50/50 never learns that 1024 shots give
    roughly 512, not exactly 512.
    """
    p0, _ = probabilities(state)
    rng = np.random.default_rng(seed)
    ones = int(rng.binomial(int(shots), 1.0 - p0))
    return {"0": int(shots) - ones, "1": ones}


def collapse(state: np.ndarray, rng: np.random.Generator | None = None) -> tuple[int, np.ndarray]:
    """Measure once. Returns the outcome and the state left behind.

    This is the part a histogram cannot teach: measurement is destructive. The
    superposition does not survive, and the post-measurement state is the basis
    state that was observed, so measuring again gives the same answer forever.
    Only a reset restores the qubit.
    """
    p0, _ = probabilities(state)
    generator = rng if rng is not None else np.random.default_rng()
    outcome = 0 if generator.random() < p0 else 1
    collapsed = np.array([1.0, 0.0], dtype=complex) if outcome == 0 else np.array(
        [0.0, 1.0], dtype=complex
    )
    return outcome, collapsed


def interference(amp_a: float, amp_b: float) -> dict[str, float]:
    """Two paths meeting at one outcome.

    The heart of the lesson: amplitudes add first, and only then are squared.
    Two paths of +0.707 and −0.707 cancel exactly, which is impossible for
    classical probabilities, since those can never be negative.
    """
    total = amp_a + amp_b
    return {
        "amplitude": total,
        "probability": total * total,
        "classical": amp_a * amp_a + amp_b * amp_b,
    }


def state_space_rows(max_qubits: int = 10) -> list[dict[str, Any]]:
    """Rows for the 2**n growth demo."""
    rows = []
    for n in range(1, max_qubits + 1):
        states = 2**n
        rows.append(
            {
                "qubits": n,
                "states": states,
                # 16 bytes per complex128 amplitude.
                "megabytes": states * 16 / 1e6,
            }
        )
    return rows


def bitstring_table(value: int, n_qubits: int) -> list[dict[str, Any]]:
    """Explain Qiskit bit ordering, where qubit 0 is the RIGHTMOST character.

    This trips up nearly every beginner, and silently: a circuit can be right
    while the bitstring is read backwards.
    """
    bits = format(value, f"0{n_qubits}b")
    rows = []
    for position, char in enumerate(bits):
        qubit = n_qubits - 1 - position
        rows.append(
            {
                "qubit": f"q{qubit}",
                "value": int(char),
                "position": f"char {position} (from the left)",
                "rightmost": qubit == 0,
            }
        )
    return rows


__all__ = [
    "GATES",
    "GATE_HELP",
    "LANDMARKS",
    "SQRT1_2",
    "state_from_angles",
    "state_from_amplitudes",
    "apply_gates",
    "probabilities",
    "bloch_angles_of",
    "ket_string",
    "as_result",
    "sample",
    "collapse",
    "interference",
    "state_space_rows",
    "bitstring_table",
]
