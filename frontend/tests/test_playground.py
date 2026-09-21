"""Interactive playground maths, pinned to analytic values.

The playground computes states locally so sliders feel instant, which means
its maths is a second implementation of physics the platform already gets
right elsewhere. These tests keep the two in agreement: every state is
cross-checked against ``lib.viz``'s Bloch helpers, which are themselves
verified against Pauli traces.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import playground as pg, viz  # noqa: E402

S2 = pg.SQRT1_2


# ----------------------------------------------------------------- landmarks
@pytest.mark.parametrize("name", list(pg.LANDMARKS))
def test_landmark_angles_round_trip(name):
    theta, phi = pg.LANDMARKS[name]
    state = pg.state_from_angles(theta, phi)
    theta_back, phi_back = pg.bloch_angles_of(state)
    assert theta_back == pytest.approx(theta, abs=1e-6)
    # phi is undefined at the poles, where sin(theta/2) is 0 or the state is real.
    if theta not in (0.0, 180.0):
        assert phi_back == pytest.approx(phi, abs=1e-6)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("|0⟩", (0, 0, 1)),
        ("|1⟩", (0, 0, -1)),
        ("|+⟩", (1, 0, 0)),
        ("|−⟩", (-1, 0, 0)),
        ("|+i⟩", (0, 1, 0)),
        ("|−i⟩", (0, -1, 0)),
    ],
)
def test_landmarks_match_the_verified_bloch_helper(name, expected):
    """The playground must agree with viz.py, not invent its own geometry."""
    theta, phi = pg.LANDMARKS[name]
    state = pg.state_from_angles(theta, phi)
    rho = np.outer(state, state.conj())
    assert np.allclose(viz.bloch_vector(rho), expected, atol=1e-12)


def test_states_are_normalised():
    for theta in (0, 37, 90, 143, 180):
        for phi in (0, 90, 210, 359):
            state = pg.state_from_angles(theta, phi)
            assert np.linalg.norm(state) == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------- amplitudes
def test_amplitudes_are_renormalised():
    state = pg.state_from_amplitudes(3.0, 4.0)
    assert np.linalg.norm(state) == pytest.approx(1.0)
    p0, p1 = pg.probabilities(state)
    assert p0 == pytest.approx(0.36)
    assert p1 == pytest.approx(0.64)


def test_zero_amplitudes_fall_back_to_ground_state():
    """Both sliders at zero must not produce a divide-by-zero."""
    state = pg.state_from_amplitudes(0.0, 0.0)
    assert pg.probabilities(state) == (pytest.approx(1.0), pytest.approx(0.0))


def test_probabilities_always_sum_to_one():
    for alpha in (-1.0, -0.3, 0.0, 0.5, 1.0):
        for beta in (-1.0, 0.2, 1.0):
            p0, p1 = pg.probabilities(pg.state_from_amplitudes(alpha, beta))
            assert p0 + p1 == pytest.approx(1.0, abs=1e-12)


def test_opposite_amplitudes_give_equal_probabilities():
    """The heart of 'amplitude is not probability'."""
    plus = pg.probabilities(pg.state_from_amplitudes(S2, S2))
    minus = pg.probabilities(pg.state_from_amplitudes(S2, -S2))
    assert plus == pytest.approx(minus)


# --------------------------------------------------------------------- gates
def test_h_on_zero_is_plus():
    state = pg.apply_gates(pg.state_from_angles(0, 0), ["H"])
    assert np.allclose(state, [S2, S2], atol=1e-12)


def test_h_on_plus_is_zero():
    """The lesson's punchline: the relative phase becomes measurable."""
    state = pg.apply_gates(pg.state_from_angles(90, 0), ["H"])
    assert np.allclose(state, [1.0, 0.0], atol=1e-12)


def test_h_on_minus_is_one():
    state = pg.apply_gates(pg.state_from_angles(90, 180), ["H"])
    assert np.allclose(np.abs(state), [0.0, 1.0], atol=1e-12)


def test_h_is_its_own_inverse():
    start = pg.state_from_angles(53, 29)
    assert np.allclose(pg.apply_gates(start, ["H", "H"]), start, atol=1e-12)


def test_x_flips_the_basis_states():
    assert np.allclose(pg.apply_gates(np.array([1, 0], dtype=complex), ["X"]), [0, 1])
    assert np.allclose(pg.apply_gates(np.array([0, 1], dtype=complex), ["X"]), [1, 0])


def test_z_leaves_probabilities_alone_but_changes_the_state():
    plus = pg.state_from_angles(90, 0)
    after = pg.apply_gates(plus, ["Z"])
    assert pg.probabilities(after) == pytest.approx(pg.probabilities(plus))
    assert not np.allclose(after, plus)


def test_t_gate_is_an_eighth_turn():
    after = pg.apply_gates(pg.state_from_angles(90, 0), ["T"])
    _, phi = pg.bloch_angles_of(after)
    assert phi == pytest.approx(45.0, abs=1e-6)


def test_gates_apply_left_to_right():
    """Order matters: the list reads like a circuit wire."""
    start = pg.state_from_angles(0, 0)
    assert not np.allclose(
        pg.apply_gates(start, ["H", "Z"]), pg.apply_gates(start, ["Z", "H"])
    )


def test_unknown_gate_is_rejected():
    with pytest.raises(ValueError):
        pg.apply_gates(pg.state_from_angles(0, 0), ["NOPE"])


# -------------------------------------------------------------- interference
def test_destructive_interference_cancels_exactly():
    result = pg.interference(S2, -S2)
    assert result["amplitude"] == pytest.approx(0.0, abs=1e-12)
    assert result["probability"] == pytest.approx(0.0, abs=1e-12)


def test_classical_paths_can_never_cancel():
    """The whole point: classically the same two paths give a non-zero total."""
    result = pg.interference(S2, -S2)
    assert result["classical"] == pytest.approx(1.0)
    assert result["classical"] > result["probability"]


def test_constructive_interference_beats_classical():
    result = pg.interference(S2, S2)
    assert result["probability"] == pytest.approx(2.0)
    assert result["probability"] > result["classical"]


# ----------------------------------------------------------------- sampling
def test_sampling_returns_the_requested_number_of_shots():
    counts = pg.sample(pg.state_from_angles(90, 0), 1024, seed=1)
    assert counts["0"] + counts["1"] == 1024


def test_sampling_is_close_to_but_not_exactly_the_theory():
    """Students must see sampling error, not a suspiciously perfect 50/50."""
    counts = pg.sample(pg.state_from_angles(90, 0), 1024, seed=3)
    fraction = counts["0"] / 1024
    assert 0.4 < fraction < 0.6


def test_deterministic_states_never_waver():
    assert pg.sample(pg.state_from_angles(0, 0), 500, seed=2) == {"0": 500, "1": 0}
    assert pg.sample(pg.state_from_angles(180, 0), 500, seed=2) == {"0": 0, "1": 500}


def test_sampling_is_reproducible_with_a_seed():
    a = pg.sample(pg.state_from_angles(70, 0), 256, seed=9)
    b = pg.sample(pg.state_from_angles(70, 0), 256, seed=9)
    assert a == b


# ------------------------------------------------------------ viz interop
def test_as_result_is_readable_by_viz():
    """The playground reuses verified renderers instead of drawing its own."""
    result = pg.as_result(pg.state_from_angles(90, 45))
    amplitudes = viz._amplitudes(result)
    assert amplitudes is not None and amplitudes.size == 2


@pytest.mark.parametrize("theta,phi", [(0, 0), (90, 0), (90, 180), (180, 0), (37, 211)])
def test_every_viz_panel_accepts_a_playground_state(theta, phi):
    result = pg.as_result(pg.state_from_angles(theta, phi))
    for name in ("bloch_sphere", "phase_disk", "statevector_ket", "amplitude_table"):
        getattr(viz, name)(result)  # must not raise


# ------------------------------------------------------------- explainers
def test_state_space_doubles_per_qubit():
    rows = pg.state_space_rows(10)
    assert rows[0]["states"] == 2
    assert rows[-1]["states"] == 1024
    for earlier, later in zip(rows, rows[1:]):
        assert later["states"] == earlier["states"] * 2


def test_bit_ordering_marks_qubit_zero_as_rightmost():
    rows = pg.bitstring_table(0b001, 3)
    rightmost = [row for row in rows if row["rightmost"]]
    assert len(rightmost) == 1
    assert rightmost[0]["qubit"] == "q0"
    assert rightmost[0]["value"] == 1


def test_bit_ordering_reads_the_string_correctly():
    rows = pg.bitstring_table(0b101, 3)
    values = {row["qubit"]: row["value"] for row in rows}
    assert values == {"q2": 1, "q1": 0, "q0": 1}


def test_ket_string_formats_real_and_complex_amplitudes():
    assert "0.707|0⟩" in pg.ket_string(pg.state_from_angles(90, 0))
    assert "i" in pg.ket_string(pg.state_from_angles(90, 90))
