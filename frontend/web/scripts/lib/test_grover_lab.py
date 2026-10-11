"""Grover's algorithm, checked against the closed form.

The module exists to teach amplitude amplification, so the simulation has to be
genuinely right: a demo that shows plausible-looking bars computed from
invented percentages would teach the wrong thing convincingly.

Every probability is cross-checked against
``sin^2((2k+1) * asin(1/sqrt(N)))``, derived independently of the
implementation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import grover_lab as gl  # noqa: E402


# ------------------------------------------------------------------- parsing
@pytest.mark.parametrize("text,n,expected", [
    ("101101", 6, 0b101101),
    ("000000", 6, 0),
    ("111111", 6, 63),
    ("1", 1, 1),
    ("0", 1, 0),
    ("101", 3, 5),
])
def test_valid_passwords_parse(text, n, expected):
    index, error = gl.parse_password(text, n)
    assert error == ""
    assert index == expected


@pytest.mark.parametrize("text,n", [("10110", 6), ("1011010", 6), ("", 6)])
def test_wrong_length_is_rejected(text, n):
    index, error = gl.parse_password(text, n)
    assert index is None and error


@pytest.mark.parametrize("text", ["hello", "1x1", "12", "abc"])
def test_non_binary_is_rejected(text):
    index, error = gl.parse_password(text, 3)
    assert index is None
    assert "0 and 1" in error or "binary" in error


def test_whitespace_is_tolerated():
    assert gl.parse_password("1 0 1 1 0 1", 6)[0] == 0b101101


# ------------------------------------------------------------- iteration count
@pytest.mark.parametrize("n,expected", [(2, 1), (3, 2), (4, 3), (5, 4), (6, 6)])
def test_optimal_iterations_is_pi_over_four_root_n(n, expected):
    """NOT sqrt(N). For N=64 the optimum is 6, not 8."""
    assert gl.optimal_iterations(n) == expected


def test_optimal_is_the_first_peak():
    """Grover is periodic: the state keeps rotating and later peaks recur.

    What matters is that the formula lands on the FIRST maximum -- you want
    the answer with the fewest oracle queries, not a later revolution.
    """
    for n in range(2, 7):
        optimal = gl.optimal_iterations(n)
        probabilities = [gl.analytic_probability(n, k) for k in range(optimal + 2)]
        first_peak = max(range(len(probabilities)), key=probabilities.__getitem__)
        assert first_peak == optimal, f"n={n}: peak at {first_peak}, formula {optimal}"
        # And it is a genuine local maximum, not a plateau.
        assert probabilities[optimal] > probabilities[optimal - 1]
        assert probabilities[optimal] > probabilities[optimal + 1]


def test_overshooting_reduces_the_probability():
    """The lesson the module teaches with its over-rotation toggle."""
    optimal = gl.optimal_iterations(6)
    at_best = gl.analytic_probability(6, optimal)
    beyond = gl.analytic_probability(6, optimal + 2)
    assert beyond < at_best
    # The commonly quoted "sqrt(64) = 8" is materially worse than the truth.
    assert gl.analytic_probability(6, 8) < at_best - 0.2


# ---------------------------------------------------------------- simulation
def test_uniform_state_is_normalised_and_equal():
    state = gl.uniform_state(6)
    assert len(state) == 64
    assert np.allclose(np.abs(state) ** 2, 1 / 64)
    assert np.sum(np.abs(state) ** 2) == pytest.approx(1.0)


def test_oracle_flips_only_the_target_phase():
    state = gl.uniform_state(4)
    flipped = gl.apply_oracle(state, 5)
    assert flipped[5] == pytest.approx(-state[5])
    for index in range(16):
        if index != 5:
            assert flipped[index] == pytest.approx(state[index])


def test_oracle_does_not_change_any_probability():
    """A phase flip is invisible to measurement. That is the whole trick."""
    state = gl.uniform_state(5)
    flipped = gl.apply_oracle(state, 9)
    assert np.allclose(np.abs(state) ** 2, np.abs(flipped) ** 2)


def test_diffusion_preserves_the_norm():
    state = gl.apply_oracle(gl.uniform_state(5), 3)
    out = gl.apply_diffusion(state)
    assert np.sum(np.abs(out) ** 2) == pytest.approx(1.0)


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6])
def test_simulation_matches_the_closed_form(n):
    target = min(2**n - 1, 0b101101)
    frames = gl.run(n, target, gl.optimal_iterations(n))
    for frame in frames:
        expected = gl.analytic_probability(n, frame["iteration"])
        assert frame["target_probability"] == pytest.approx(expected, abs=1e-12)


def test_probability_rises_monotonically_up_to_the_optimum():
    frames = gl.run(6, 0b101101, gl.optimal_iterations(6))
    probabilities = [f["target_probability"] for f in frames]
    assert probabilities == sorted(probabilities)
    assert probabilities[0] == pytest.approx(1 / 64)
    assert probabilities[-1] > 0.99


def test_every_frame_stays_normalised():
    for frame in gl.run(6, 17, 6):
        assert float(np.sum(frame["probabilities"])) == pytest.approx(1.0)


def test_two_qubit_search_is_exact():
    """N=4 is the special case where one iteration gives certainty."""
    frames = gl.run(2, 3, 1)
    assert frames[-1]["target_probability"] == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize("target", [0, 1, 31, 45, 63])
def test_any_target_is_amplified(target):
    frames = gl.run(6, target, gl.optimal_iterations(6))
    final = frames[-1]["probabilities"]
    assert int(np.argmax(final)) == target
    assert final[target] > 0.99


# --------------------------------------------------------------- measurement
def test_measurement_returns_the_requested_shots():
    frames = gl.run(6, 45, 6)
    counts = gl.measure(frames[-1]["amplitudes"], 500, seed=1)
    assert sum(counts.values()) == 500


def test_measurement_usually_finds_an_amplified_target():
    frames = gl.run(6, 45, 6)
    counts = gl.measure(frames[-1]["amplitudes"], 1000, seed=2)
    assert counts.get(45, 0) / 1000 > 0.95


def test_measurement_before_amplification_is_near_random():
    counts = gl.measure(gl.uniform_state(6), 1000, seed=3)
    assert counts.get(45, 0) / 1000 < 0.1


def test_measurement_is_reproducible():
    state = gl.run(5, 7, 4)[-1]["amplitudes"]
    assert gl.measure(state, 200, seed=8) == gl.measure(state, 200, seed=8)


# ------------------------------------------------------------- comparison
def test_classical_costs_are_reported_honestly():
    costs = gl.classical_attempts(6, 45)
    assert costs["worst_case"] == 64
    assert costs["average_case"] == 32
    assert costs["checked_to_find"] == 46  # scanning 0..45 in order


def test_label_pads_to_the_qubit_count():
    assert gl.label(5, 6) == "000101"
    assert gl.label(0, 3) == "000"
    assert gl.label(63, 6) == "111111"


def test_module_is_capped_at_six_qubits():
    """A visualisation, not a cracker."""
    assert gl.MAX_QUBITS == 6
