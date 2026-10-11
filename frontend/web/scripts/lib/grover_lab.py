"""Grover's search, simulated exactly, for the Quantum Password Search module.

This is a real state-vector simulation: 2**n complex amplitudes, a genuine
oracle phase flip and a genuine diffusion operator. Nothing is faked or
animated from invented percentages, because the whole point of the module is
that the learner watches the actual amplitude amplification.

Two things the module is careful about, because both are commonly taught
wrongly:

* Grover does **not** check candidates one at a time. It marks the target with
  a phase and amplifies its amplitude.
* The optimal iteration count is ``floor(pi/4 * sqrt(N))``, not ``sqrt(N)``.
  For N = 64 that is 6, reaching 99.66%. Running the "sqrt(64) = 8" iterations
  that people often quote OVER-rotates and drops the success probability to
  71.8%. O(sqrt(N)) is the query *complexity*, not the iteration count.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

#: Deliberately small. This is a visualisation, not a cracker: 6 qubits is
#: 64 states, which fits on screen and simulates instantly.
MAX_QUBITS = 6
MIN_QUBITS = 1


def parse_password(text: str, n_qubits: int) -> tuple[int | None, str]:
    """Read a binary string into a target index.

    Returns ``(index, error)``. The password only ever exists as an integer
    inside this simulation; nothing is sent anywhere.
    """
    cleaned = "".join(text.split())
    if not cleaned:
        return None, "Enter a binary password, for example 101101."
    if any(ch not in "01" for ch in cleaned):
        return None, "Only the digits 0 and 1 are allowed."
    if len(cleaned) != n_qubits:
        return None, (
            f"This is a {n_qubits}-qubit search, so the password needs exactly "
            f"{n_qubits} bit{'s' if n_qubits != 1 else ''} (you gave {len(cleaned)})."
        )
    return int(cleaned, 2), ""


def optimal_iterations(n_qubits: int) -> int:
    """floor(pi/4 * sqrt(N)), the iteration count that maximises success.

    Not sqrt(N). Overshooting rotates the state past the target and the
    success probability falls again, which the module shows explicitly.
    """
    n_states = 2**n_qubits
    return max(1, int(math.floor(math.pi / 4 * math.sqrt(n_states))))


def uniform_state(n_qubits: int) -> np.ndarray:
    """Hadamard on every qubit: equal amplitude 1/sqrt(N) everywhere."""
    n_states = 2**n_qubits
    return np.full(n_states, 1.0 / math.sqrt(n_states), dtype=complex)


def apply_oracle(state: np.ndarray, target: int) -> np.ndarray:
    """Flip the phase of the marked state, and nothing else.

    The oracle recognises the target; it does not reveal it. That distinction
    is the honest framing of what Grover assumes.
    """
    out = state.copy()
    out[target] *= -1
    return out


def apply_diffusion(state: np.ndarray) -> np.ndarray:
    """Inversion about the mean: 2|s><s| - I."""
    mean = state.mean()
    return 2.0 * mean - state


def run(n_qubits: int, target: int, iterations: int) -> list[dict[str, Any]]:
    """Simulate Grover step by step, recording the state after each stage.

    Returns one entry per iteration plus the initial state, each with the full
    probability vector so the UI can draw real bars rather than a cartoon.
    """
    state = uniform_state(n_qubits)
    frames = [{
        "iteration": 0,
        "stage": "superposition",
        "probabilities": np.abs(state) ** 2,
        "target_probability": float(abs(state[target]) ** 2),
        "amplitudes": state.copy(),
    }]

    for step in range(1, iterations + 1):
        state = apply_diffusion(apply_oracle(state, target))
        frames.append({
            "iteration": step,
            "stage": "amplified",
            "probabilities": np.abs(state) ** 2,
            "target_probability": float(abs(state[target]) ** 2),
            "amplitudes": state.copy(),
        })
    return frames


def analytic_probability(n_qubits: int, iteration: int) -> float:
    """sin^2((2k+1) * asin(1/sqrt(N))) -- the closed form, for cross-checking."""
    n_states = 2**n_qubits
    theta = math.asin(1.0 / math.sqrt(n_states))
    return float(math.sin((2 * iteration + 1) * theta) ** 2)


def measure(state: np.ndarray, shots: int, seed: int | None = None) -> dict[int, int]:
    """Sample the state, so the learner sees a probabilistic result."""
    probabilities = np.abs(state) ** 2
    probabilities = probabilities / probabilities.sum()
    rng = np.random.default_rng(seed)
    draws = rng.choice(len(probabilities), size=int(shots), p=probabilities)
    counts: dict[int, int] = {}
    for value in draws:
        counts[int(value)] = counts.get(int(value), 0) + 1
    return counts


def classical_attempts(n_qubits: int, target: int) -> dict[str, int]:
    """What a sequential search costs, for the comparison panel."""
    n_states = 2**n_qubits
    return {
        "checked_to_find": target + 1,   # scanning 0, 1, 2, ... in order
        "worst_case": n_states,
        "average_case": (n_states + 1) // 2,
    }


def label(index: int, n_qubits: int) -> str:
    return format(index, f"0{n_qubits}b")


__all__ = [
    "MAX_QUBITS", "MIN_QUBITS", "parse_password", "optimal_iterations",
    "uniform_state", "apply_oracle", "apply_diffusion", "run",
    "analytic_probability", "measure", "classical_attempts", "label",
]
