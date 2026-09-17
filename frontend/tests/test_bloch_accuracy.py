"""The Bloch sphere must be quantitatively correct, not just plausible.

The arrow's direction encodes the qubit's phase, so an error here teaches the
wrong physics silently. These tests pin the maths against analytic values:

* the Bloch vector is read as (Tr(rho X), Tr(rho Y), Tr(rho Z));
* the partial trace respects Qiskit's ordering, where qubit 0 is the least
  significant amplitude index;
* the reported theta/phi match the textbook spherical convention.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import viz  # noqa: E402

S2 = 1 / math.sqrt(2)

# The six cardinal states and their exact Bloch vectors.
CARDINALS = {
    "|0>": ([1, 0], (0, 0, 1), 0, 0),
    "|1>": ([0, 1], (0, 0, -1), 180, 0),
    "|+>": ([S2, S2], (1, 0, 0), 90, 0),
    "|->": ([S2, -S2], (-1, 0, 0), 90, 180),
    "|+i>": ([S2, 1j * S2], (0, 1, 0), 90, 90),
    "|-i>": ([S2, -1j * S2], (0, -1, 0), 90, 270),
}


def _rho(state) -> np.ndarray:
    psi = np.array(state, dtype=complex)
    return np.outer(psi, psi.conj())


@pytest.mark.parametrize("name", list(CARDINALS))
def test_cardinal_states_have_exact_bloch_vectors(name):
    state, expected, _, _ = CARDINALS[name]
    got = viz.bloch_vector(_rho(state))
    assert np.allclose(got, expected, atol=1e-12), f"{name}: {got} != {expected}"


@pytest.mark.parametrize("name", list(CARDINALS))
def test_cardinal_states_have_exact_angles(name):
    state, _, theta, phi = CARDINALS[name]
    x, y, z = viz.bloch_vector(_rho(state))
    got_theta, got_phi = viz.bloch_angles(x, y, z)
    assert got_theta == pytest.approx(theta, abs=1e-9)
    assert got_phi == pytest.approx(phi, abs=1e-9)


def test_bloch_vector_matches_pauli_traces():
    """Cross-check against an independent computation for a random state."""
    rng = np.random.default_rng(7)
    for _ in range(25):
        psi = rng.normal(size=2) + 1j * rng.normal(size=2)
        psi /= np.linalg.norm(psi)
        rho = np.outer(psi, psi.conj())
        sx = np.array([[0, 1], [1, 0]], dtype=complex)
        sy = np.array([[0, -1j], [1j, 0]], dtype=complex)
        sz = np.array([[1, 0], [0, -1]], dtype=complex)
        expected = [float(np.real(np.trace(rho @ s))) for s in (sx, sy, sz)]
        assert np.allclose(viz.bloch_vector(rho), expected, atol=1e-12)


def test_pure_states_reach_the_surface():
    rng = np.random.default_rng(11)
    for _ in range(25):
        psi = rng.normal(size=2) + 1j * rng.normal(size=2)
        psi /= np.linalg.norm(psi)
        x, y, z = viz.bloch_vector(np.outer(psi, psi.conj()))
        assert math.sqrt(x * x + y * y + z * z) == pytest.approx(1.0, abs=1e-9)


def test_t_gate_phase_shows_as_45_degrees():
    """T on |+> is a pi/4 rotation about Z: the arrow must sit at phi = 45."""
    psi = [S2, S2 * np.exp(1j * math.pi / 4)]
    x, y, z = viz.bloch_vector(_rho(psi))
    theta, phi = viz.bloch_angles(x, y, z)
    assert theta == pytest.approx(90.0, abs=1e-9)
    assert phi == pytest.approx(45.0, abs=1e-9)


# --------------------------------------------------- partial trace / ordering
def test_qubit_zero_is_the_least_significant_index():
    """|01> in Qiskit order means qubit 0 is |1> and qubit 1 is |0>."""
    amps = np.zeros(4, dtype=complex)
    amps[1] = 1.0
    q0 = viz.bloch_vector(viz.reduced_density_matrix(amps, 2, 0))
    q1 = viz.bloch_vector(viz.reduced_density_matrix(amps, 2, 1))
    assert np.allclose(q0, (0, 0, -1), atol=1e-12)
    assert np.allclose(q1, (0, 0, 1), atol=1e-12)


def test_product_state_separates_correctly():
    """qubit 0 in |+>, qubit 1 in |0>."""
    amps = np.array([S2, S2, 0, 0], dtype=complex)
    q0 = viz.bloch_vector(viz.reduced_density_matrix(amps, 2, 0))
    q1 = viz.bloch_vector(viz.reduced_density_matrix(amps, 2, 1))
    assert np.allclose(q0, (1, 0, 0), atol=1e-12)
    assert np.allclose(q1, (0, 0, 1), atol=1e-12)


def test_three_qubit_ordering():
    """q0=|+i>, q1=|0>, q2=|1>, built with kron in little-endian order."""
    q0 = np.array([S2, 1j * S2])
    q1 = np.array([1, 0])
    q2 = np.array([0, 1])
    amps = np.kron(q2, np.kron(q1, q0))
    got = [
        viz.bloch_vector(viz.reduced_density_matrix(amps, 3, q)) for q in range(3)
    ]
    assert np.allclose(got[0], (0, 1, 0), atol=1e-12)
    assert np.allclose(got[1], (0, 0, 1), atol=1e-12)
    assert np.allclose(got[2], (0, 0, -1), atol=1e-12)


def test_bell_state_qubits_are_maximally_mixed():
    """Entangled qubits have no Bloch vector of their own: r must be zero."""
    amps = np.array([S2, 0, 0, S2], dtype=complex)
    for qubit in (0, 1):
        x, y, z = viz.bloch_vector(viz.reduced_density_matrix(amps, 2, qubit))
        assert math.sqrt(x * x + y * y + z * z) == pytest.approx(0.0, abs=1e-12)


def test_partial_entanglement_gives_a_short_arrow():
    """cos|00> + sin|11>: arrow length is the single-qubit purity measure."""
    angle = math.pi / 6
    amps = np.array([math.cos(angle), 0, 0, math.sin(angle)], dtype=complex)
    x, y, z = viz.bloch_vector(viz.reduced_density_matrix(amps, 2, 0))
    length = math.sqrt(x * x + y * y + z * z)
    assert length == pytest.approx(abs(math.cos(2 * angle)), abs=1e-9)
    assert 0.0 < length < 1.0


def test_reduced_density_matrix_is_a_valid_state():
    """Trace one, Hermitian, positive semi-definite."""
    rng = np.random.default_rng(3)
    amps = rng.normal(size=8) + 1j * rng.normal(size=8)
    amps /= np.linalg.norm(amps)
    for qubit in range(3):
        rho = viz.reduced_density_matrix(amps, 3, qubit)
        assert np.trace(rho).real == pytest.approx(1.0, abs=1e-12)
        assert np.allclose(rho, rho.conj().T, atol=1e-12)
        assert np.linalg.eigvalsh(rho).min() > -1e-12


def test_zero_vector_angles_are_nan_not_an_exception():
    theta, phi = viz.bloch_angles(0.0, 0.0, 0.0)
    assert math.isnan(theta) and math.isnan(phi)


def test_angles_are_clamped_against_rounding():
    """z/|r| can drift just past 1.0 and make acos raise."""
    theta, _ = viz.bloch_angles(0.0, 0.0, 1.0 + 1e-15)
    assert theta == pytest.approx(0.0, abs=1e-6)
