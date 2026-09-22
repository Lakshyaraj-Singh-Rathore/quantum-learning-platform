"""Every gate, checked against its textbook unitary.

The rest of the suite tests circuits and pipelines; this file tests the gates
themselves. If a single matrix is wrong the platform teaches wrong physics
while every integration test still passes, so each gate is compared to a
closed-form matrix written out by hand here rather than taken from Qiskit.

Comparisons are up to a global phase, which is unobservable.
"""

from __future__ import annotations

import numpy as np
import pytest
from qiskit.quantum_info import Operator, Statevector

from app.quantum.ir import GATE_PARAMS, GATE_SET, CircuitIR
from app.quantum.normalize import to_qiskit

S2 = 1 / np.sqrt(2)

#: Closed-form matrices, written independently of the implementation.
TEXTBOOK: dict[str, np.ndarray] = {
    "h": np.array([[S2, S2], [S2, -S2]], dtype=complex),
    "x": np.array([[0, 1], [1, 0]], dtype=complex),
    "y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "z": np.array([[1, 0], [0, -1]], dtype=complex),
    "id": np.eye(2, dtype=complex),
    "s": np.array([[1, 0], [0, 1j]], dtype=complex),
    "sdg": np.array([[1, 0], [0, -1j]], dtype=complex),
    "t": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex),
    "tdg": np.array([[1, 0], [0, np.exp(-1j * np.pi / 4)]], dtype=complex),
    "sx": 0.5 * np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], dtype=complex),
}


def unitary_of(gate: str, params: list[str] | None = None,
               qubits: list[int] | None = None, n_qubits: int = 1,
               controls: list[int] | None = None) -> np.ndarray:
    op: dict = {"kind": "gate", "gate": gate,
                "qubits": qubits or [0], "layer": 0}
    if params:
        op["params"] = params
    if controls:
        op["controls"] = controls
    ir = CircuitIR.from_dict(
        {"n_qubits": n_qubits, "n_clbits": n_qubits, "ops": [op]}
    )
    return Operator(to_qiskit(ir, include_measurements=False)).data


def same_up_to_phase(a: np.ndarray, b: np.ndarray, tol: float = 1e-10) -> bool:
    """A global phase is unobservable, so compare modulo one."""
    index = np.unravel_index(np.argmax(np.abs(b)), b.shape)
    if abs(b[index]) < tol or abs(a[index]) < tol:
        return bool(np.allclose(a, b, atol=tol))
    return bool(np.allclose(a * (b[index] / a[index]), b, atol=tol))


# ------------------------------------------------------------------ unitarity
@pytest.mark.parametrize("gate", sorted(GATE_SET))
def test_every_gate_is_unitary(gate):
    params = ["pi/3"] * GATE_PARAMS.get(gate, 0)
    n_qubits = 2 if gate == "swap" else 1
    qubits = [0, 1] if gate == "swap" else [0]
    matrix = unitary_of(gate, params, qubits, n_qubits)
    identity = np.eye(matrix.shape[0])
    assert np.allclose(matrix.conj().T @ matrix, identity, atol=1e-10)


# ------------------------------------------------------- fixed-matrix gates
@pytest.mark.parametrize("gate", sorted(TEXTBOOK))
def test_gate_matches_its_textbook_matrix(gate):
    assert same_up_to_phase(unitary_of(gate), TEXTBOOK[gate]), gate


# ----------------------------------------------------------------- rotations
@pytest.mark.parametrize("gate,pauli", [
    ("rx", np.array([[0, 1], [1, 0]], dtype=complex)),
    ("ry", np.array([[0, -1j], [1j, 0]], dtype=complex)),
    ("rz", np.array([[1, 0], [0, -1]], dtype=complex)),
])
@pytest.mark.parametrize("theta", [0.0, np.pi / 4, np.pi / 2, np.pi, 2 * np.pi])
def test_rotation_equals_exp_minus_i_theta_pauli_over_two(gate, pauli, theta):
    got = unitary_of(gate, [str(theta)])
    want = np.cos(theta / 2) * np.eye(2) - 1j * np.sin(theta / 2) * pauli
    assert same_up_to_phase(got, want)


@pytest.mark.parametrize("lam", [0.0, np.pi / 4, np.pi / 2, np.pi])
def test_phase_gate_is_diag_one_exp_i_lambda(lam):
    want = np.array([[1, 0], [0, np.exp(1j * lam)]], dtype=complex)
    assert same_up_to_phase(unitary_of("p", [str(lam)]), want)


# --------------------------------------------------------- gate identities
def test_s_is_a_quarter_turn_and_t_an_eighth():
    assert same_up_to_phase(unitary_of("s"), unitary_of("p", [str(np.pi / 2)]))
    assert same_up_to_phase(unitary_of("t"), unitary_of("p", [str(np.pi / 4)]))
    assert same_up_to_phase(unitary_of("z"), unitary_of("p", [str(np.pi)]))


def test_squares_compose_correctly():
    assert same_up_to_phase(unitary_of("s") @ unitary_of("s"), unitary_of("z"))
    assert same_up_to_phase(unitary_of("t") @ unitary_of("t"), unitary_of("s"))
    assert same_up_to_phase(unitary_of("sx") @ unitary_of("sx"), unitary_of("x"))


def test_daggers_are_conjugate_transposes():
    assert np.allclose(unitary_of("sdg"), unitary_of("s").conj().T)
    assert np.allclose(unitary_of("tdg"), unitary_of("t").conj().T)


def test_self_inverse_gates():
    for gate in ("h", "x", "y", "z"):
        assert same_up_to_phase(unitary_of(gate) @ unitary_of(gate), np.eye(2)), gate


def test_pauli_product_is_i_times_identity():
    product = unitary_of("x") @ unitary_of("y") @ unitary_of("z")
    assert same_up_to_phase(product, np.eye(2))


# ------------------------------------------------------------------- swap
def test_swap_exchanges_the_two_qubits():
    want = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]],
                    dtype=complex)
    got = unitary_of("swap", qubits=[0, 1], n_qubits=2)
    assert np.allclose(got, want)
    assert np.allclose(got @ got, np.eye(4))


# --------------------------------------------------------- controlled gates
def _truth_table(gate: str, controls: list[int], target: int, n_qubits: int):
    circuit = to_qiskit(
        CircuitIR.from_dict({"n_qubits": n_qubits, "n_clbits": n_qubits, "ops": [
            {"kind": "gate", "gate": gate, "qubits": [target],
             "controls": controls, "layer": 0}]}),
        include_measurements=False,
    )
    rows = []
    for value in range(2 ** n_qubits):
        evolved = Statevector.from_int(value, dims=2 ** n_qubits).evolve(circuit)
        out = int(np.argmax(np.abs(evolved.data) ** 2))
        rows.append(([(value >> k) & 1 for k in range(n_qubits)],
                     [(out >> k) & 1 for k in range(n_qubits)]))
    return rows


@pytest.mark.parametrize("n_controls", [1, 2, 3])
def test_multi_controlled_x_flips_only_when_all_controls_are_one(n_controls):
    controls = list(range(n_controls))
    target = n_controls
    for in_bits, out_bits in _truth_table("x", controls, target, n_controls + 1):
        all_set = all(in_bits[c] == 1 for c in controls)
        assert out_bits[target] == in_bits[target] ^ (1 if all_set else 0)
        for c in controls:
            assert out_bits[c] == in_bits[c], "controls must be preserved"


def test_cnot_matrix_uses_qiskit_bit_order():
    """Control 0, target 1: |01> -> |11> in Qiskit's little-endian order."""
    want = np.zeros((4, 4), dtype=complex)
    want[0, 0] = want[1, 3] = want[2, 2] = want[3, 1] = 1
    assert np.allclose(unitary_of("x", qubits=[1], controls=[0], n_qubits=2), want)


def test_reversed_cnot_is_a_different_gate():
    forward = unitary_of("x", qubits=[1], controls=[0], n_qubits=2)
    reverse = unitary_of("x", qubits=[0], controls=[1], n_qubits=2)
    assert not np.allclose(forward, reverse)


def test_controlled_z_is_symmetric():
    """CZ is the one controlled gate where control and target are equivalent."""
    forward = unitary_of("z", qubits=[1], controls=[0], n_qubits=2)
    reverse = unitary_of("z", qubits=[0], controls=[1], n_qubits=2)
    assert np.allclose(forward, reverse)


# ------------------------------------------------------- known-answer tests
def _probabilities(ir: CircuitIR, shots: int = 8000) -> dict[str, float]:
    from app.quantum.backends import qiskit_aer

    result = qiskit_aer.run(ir, shots=shots, seed=13)
    return {k: v / shots for k, v in result["counts"].items() if v / shots > 0.01}


def _circuit(n: int, ops: list[dict]) -> CircuitIR:
    return CircuitIR.from_dict({"n_qubits": n, "n_clbits": n, "ops": ops})


def _gate(g, q, layer, **kw):
    return {"kind": "gate", "gate": g, "qubits": q, "layer": layer, **kw}


def _measure(q, layer):
    return {"kind": "measure", "qubits": [q], "clbits": [q], "layer": layer}


def test_bell_state():
    probs = _probabilities(_circuit(2, [
        _gate("h", [0], 0), _gate("x", [1], 1, controls=[0]),
        _measure(0, 2), _measure(1, 2)]))
    assert set(probs) == {"00", "11"}
    assert probs["00"] == pytest.approx(0.5, abs=0.05)


def test_ghz_state():
    probs = _probabilities(_circuit(3, [
        _gate("h", [0], 0), _gate("x", [1], 1, controls=[0]),
        _gate("x", [2], 2, controls=[0]),
        _measure(0, 3), _measure(1, 3), _measure(2, 3)]))
    assert set(probs) == {"000", "111"}


def test_deutsch_jozsa_distinguishes_constant_from_balanced():
    balanced = _probabilities(_circuit(2, [
        _gate("x", [1], 0), _gate("h", [0], 1), _gate("h", [1], 1),
        _gate("x", [1], 2, controls=[0]), _gate("h", [0], 3), _measure(0, 4)]))
    constant = _probabilities(_circuit(2, [
        _gate("x", [1], 0), _gate("h", [0], 1), _gate("h", [1], 1),
        _gate("h", [0], 3), _measure(0, 4)]))
    assert max(balanced, key=balanced.get)[-1] == "1"
    assert max(constant, key=constant.get)[-1] == "0"


def test_grover_finds_the_marked_state_with_certainty():
    """Two qubits, one iteration: the marked state is found exactly."""
    probs = _probabilities(_circuit(2, [
        _gate("h", [0], 0), _gate("h", [1], 0),
        _gate("z", [1], 1, controls=[0]),
        _gate("h", [0], 2), _gate("h", [1], 2),
        _gate("x", [0], 3), _gate("x", [1], 3),
        _gate("z", [1], 4, controls=[0]),
        _gate("x", [0], 5), _gate("x", [1], 5),
        _gate("h", [0], 6), _gate("h", [1], 6),
        _measure(0, 7), _measure(1, 7)]))
    assert probs.get("11", 0) > 0.97


def test_h_z_h_equals_x():
    """Phase becomes measurable only after interfering it back."""
    probs = _probabilities(_circuit(1, [
        _gate("h", [0], 0), _gate("z", [0], 1), _gate("h", [0], 2),
        _measure(0, 3)]))
    assert probs.get("1", 0) > 0.97
