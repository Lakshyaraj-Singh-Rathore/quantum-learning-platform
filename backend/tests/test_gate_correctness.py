"""Ground-truth checks for every gate, CNOT orientation and entanglement.

A user reported that CNOT and entanglement were wrong. They were not -- the
bug was in visualisation -- but nothing in the suite actually pinned the gate
unitaries to textbook matrices, so the claim could not be refuted from the
tests alone. These lock that down.

Comparisons are up to a global phase, which is physically unobservable and
which the rx/ry/rz basis transpilation legitimately introduces.
"""

from __future__ import annotations

import numpy as np
import pytest
from qiskit.quantum_info import Operator, Statevector

from app.quantum.ir import CircuitIR
from app.quantum.normalize import to_qiskit

SQRT2 = 1 / np.sqrt(2)

SINGLE_QUBIT = {
    "h": np.array([[SQRT2, SQRT2], [SQRT2, -SQRT2]], dtype=complex),
    "x": np.array([[0, 1], [1, 0]], dtype=complex),
    "y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "z": np.array([[1, 0], [0, -1]], dtype=complex),
    "s": np.array([[1, 0], [0, 1j]], dtype=complex),
    "sdg": np.array([[1, 0], [0, -1j]], dtype=complex),
    "t": np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex),
    "tdg": np.array([[1, 0], [0, np.exp(-1j * np.pi / 4)]], dtype=complex),
    "sx": 0.5 * np.array([[1 + 1j, 1 - 1j], [1 - 1j, 1 + 1j]], dtype=complex),
}

THETA = 0.7
ROTATIONS = {
    "rx": np.array(
        [
            [np.cos(THETA / 2), -1j * np.sin(THETA / 2)],
            [-1j * np.sin(THETA / 2), np.cos(THETA / 2)],
        ]
    ),
    "ry": np.array(
        [
            [np.cos(THETA / 2), -np.sin(THETA / 2)],
            [np.sin(THETA / 2), np.cos(THETA / 2)],
        ],
        dtype=complex,
    ),
    "rz": np.array(
        [[np.exp(-1j * THETA / 2), 0], [0, np.exp(1j * THETA / 2)]], dtype=complex
    ),
    "p": np.array([[1, 0], [0, np.exp(1j * THETA)]], dtype=complex),
}


def _ir(ops: list[dict], n_qubits: int) -> CircuitIR:
    return CircuitIR.model_validate(
        {"n_qubits": n_qubits, "n_clbits": n_qubits, "ops": ops}
    )


def _equal_up_to_phase(actual: np.ndarray, expected: np.ndarray) -> bool:
    phase = None
    for i in range(expected.shape[0]):
        for j in range(expected.shape[1]):
            if abs(expected[i, j]) > 1e-9:
                phase = actual[i, j] / expected[i, j]
                break
        if phase is not None:
            break
    if phase is None or abs(abs(phase) - 1.0) > 1e-9:
        return False
    return bool(np.allclose(actual, phase * expected, atol=1e-9))


@pytest.mark.parametrize("gate,expected", sorted(SINGLE_QUBIT.items()))
def test_single_qubit_gate_matches_textbook_matrix(gate, expected):
    circuit = to_qiskit(_ir([{"kind": "gate", "gate": gate, "qubits": [0]}], 1))
    assert _equal_up_to_phase(Operator(circuit).data, expected)


@pytest.mark.parametrize("gate,expected", sorted(ROTATIONS.items()))
def test_rotation_gate_matches_textbook_matrix(gate, expected):
    circuit = to_qiskit(
        _ir(
            [
                {
                    "kind": "gate",
                    "gate": gate,
                    "qubits": [0],
                    "params": [{"expr": str(THETA), "value": THETA}],
                }
            ],
            1,
        )
    )
    assert _equal_up_to_phase(Operator(circuit).data, expected)


def test_cnot_uses_little_endian_control_target():
    """CNOT(control=q0, target=q1) must map |q1=0,q0=1> -> |q1=1,q0=1>.

    In Qiskit's little-endian convention the basis index is q0 + 2*q1, so the
    correct permutation swaps indices 1 and 3 and leaves 0 and 2 fixed.
    """
    circuit = to_qiskit(
        _ir([{"kind": "gate", "gate": "x", "qubits": [1], "controls": [0]}], 2)
    )
    actual = np.round(Operator(circuit).data.real).astype(int)
    expected = np.eye(4, dtype=int)[:, [0, 3, 2, 1]]
    assert np.array_equal(actual, expected)


def test_cnot_is_directional():
    """Swapping control and target must give a different operator."""
    forward = Operator(
        to_qiskit(_ir([{"kind": "gate", "gate": "x", "qubits": [1], "controls": [0]}], 2))
    ).data
    reverse = Operator(
        to_qiskit(_ir([{"kind": "gate", "gate": "x", "qubits": [0], "controls": [1]}], 2))
    ).data
    assert not np.allclose(forward, reverse)


def test_bell_state_is_correct_and_entangled():
    circuit = to_qiskit(
        _ir(
            [
                {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
                {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
            ],
            2,
        )
    )
    amplitudes = Statevector.from_instruction(circuit).data
    assert np.allclose(np.abs(amplitudes), [SQRT2, 0.0, 0.0, SQRT2], atol=1e-9)

    # Both single-qubit reduced states must be maximally mixed.
    tensor = amplitudes.reshape(2, 2)
    for axis in (0, 1):
        moved = np.moveaxis(tensor, axis, 0).reshape(2, -1)
        rho = moved @ moved.conj().T
        assert np.allclose(rho, 0.5 * np.eye(2), atol=1e-9)
        assert abs(float(np.real(np.trace(rho @ rho))) - 0.5) < 1e-9


def test_ghz_and_toffoli():
    ghz = to_qiskit(
        _ir(
            [
                {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
                {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
                {"kind": "gate", "gate": "x", "qubits": [2], "controls": [1], "layer": 2},
            ],
            3,
        )
    )
    amps = Statevector.from_instruction(ghz).data
    assert abs(abs(amps[0]) - SQRT2) < 1e-9
    assert abs(abs(amps[7]) - SQRT2) < 1e-9

    toffoli = to_qiskit(
        _ir(
            [
                {"kind": "gate", "gate": "x", "qubits": [0], "layer": 0},
                {"kind": "gate", "gate": "x", "qubits": [1], "layer": 0},
                {
                    "kind": "gate",
                    "gate": "x",
                    "qubits": [2],
                    "controls": [0, 1],
                    "layer": 1,
                },
            ],
            3,
        )
    )
    assert abs(abs(Statevector.from_instruction(toffoli).data[7]) - 1.0) < 1e-9


def test_swap_moves_the_excitation():
    circuit = to_qiskit(
        _ir(
            [
                {"kind": "gate", "gate": "x", "qubits": [0], "layer": 0},
                {"kind": "gate", "gate": "swap", "qubits": [0, 1], "layer": 1},
            ],
            2,
        )
    )
    amplitudes = Statevector.from_instruction(circuit).data
    # |q0=1> (index 1) must become |q1=1> (index 2)
    assert abs(abs(amplitudes[2]) - 1.0) < 1e-9
