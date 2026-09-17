"""The noise model must reproduce textbook decoherence, not just "look noisy".

Checks the two things a learner could be taught wrongly:

* the relaxation constraint is T2 <= 2*T1 (NOT T2 <= T1/2, and not T2 <= T1 --
  the region T1 < T2 < 2*T1 is physically legal and must be left alone);
* populations decay as exp(-t/T1) and coherences as exp(-t/T2).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.quantum.ir import CircuitIR
from app.quantum.noise import BASIS_GATES, NoiseParams, build_noise_model


# ------------------------------------------------------------ the T2 <= 2 T1 rule
@pytest.mark.parametrize(
    "t1,t2,expected",
    [
        (50, 30, 30),    # T2 < T1
        (50, 50, 50),    # T2 == T1
        (50, 80, 80),    # T1 < T2 < 2*T1 -- legal, must NOT be clamped
        (50, 100, 100),  # T2 == 2*T1 -- the boundary itself is legal
        (50, 101, 100),  # just over
        (50, 999, 100),  # far over
    ],
)
def test_t2_is_clamped_to_twice_t1(t1, t2, expected):
    clean, _ = NoiseParams(enabled=True, t1_us=t1, t2_us=t2).clamped()
    assert clean.t2_us == pytest.approx(expected)


def test_the_limit_is_not_half_of_t1():
    """A T2 of 0.8*T1 is perfectly physical and must survive untouched."""
    clean, notes = NoiseParams(enabled=True, t1_us=100, t2_us=80).clamped()
    assert clean.t2_us == pytest.approx(80)
    assert notes == []


def test_clamping_explains_itself():
    _, notes = NoiseParams(enabled=True, t1_us=50, t2_us=500).clamped()
    assert notes and "2*T1" in notes[0]


def test_non_positive_times_are_made_safe():
    """Zero or negative times would make Aer raise."""
    clean, _ = NoiseParams(enabled=True, t1_us=0, t2_us=0).clamped()
    assert clean.t1_us > 0
    assert clean.t2_us > 0
    clean, _ = NoiseParams(enabled=True, t1_us=-5, t2_us=-5).clamped()
    assert clean.t1_us > 0
    assert clean.t2_us > 0


@pytest.mark.parametrize(
    "given,expected",
    [(0.02, 0.02), (1.5, 0.015), (-0.2, 0.0), (0.9, 0.5), (100, 0.5)],
)
def test_readout_error_is_normalised(given, expected):
    """Values above 1 are read as percentages; the cap is 0.5 (pure guessing)."""
    clean, _ = NoiseParams(enabled=True, readout_error=given).clamped()
    assert clean.readout_error == pytest.approx(expected)


# ------------------------------------------------------------- decay physics
def _damped(t1: float, t2: float, gate_time: float):
    from qiskit.quantum_info import DensityMatrix, Kraus
    from qiskit_aer.noise import thermal_relaxation_error

    return Kraus(thermal_relaxation_error(t1, t2, gate_time)), DensityMatrix


@pytest.mark.parametrize("t", [5.0, 25.0, 50.0, 100.0])
def test_population_decays_as_exp_minus_t_over_t1(t):
    """Starting in |1>, P(1) must follow exp(-t/T1)."""
    kraus, DensityMatrix = _damped(50.0, 30.0, t)
    rho = DensityMatrix(np.array([[0, 0], [0, 1]], dtype=complex)).evolve(kraus)
    assert float(np.real(rho.data[1, 1])) == pytest.approx(math.exp(-t / 50.0), abs=1e-9)


@pytest.mark.parametrize("t", [5.0, 25.0, 50.0])
def test_coherence_decays_as_exp_minus_t_over_t2(t):
    """Starting in |+>, the XY Bloch length must follow exp(-t/T2)."""
    kraus, DensityMatrix = _damped(50.0, 30.0, t)
    s2 = 1 / math.sqrt(2)
    psi = np.array([s2, s2], dtype=complex)
    rho = DensityMatrix(np.outer(psi, psi.conj())).evolve(kraus)
    assert 2 * abs(rho.data[0, 1]) == pytest.approx(math.exp(-t / 30.0), abs=1e-9)


def test_longer_t1_means_less_decay():
    from qiskit.quantum_info import DensityMatrix, Kraus
    from qiskit_aer.noise import thermal_relaxation_error

    survivals = []
    for t1 in (10.0, 50.0, 250.0):
        kraus = Kraus(thermal_relaxation_error(t1, t1, 20.0))
        rho = DensityMatrix(np.array([[0, 0], [0, 1]], dtype=complex)).evolve(kraus)
        survivals.append(float(np.real(rho.data[1, 1])))
    assert survivals == sorted(survivals)


# --------------------------------------------------------------- attachment
def test_noise_attaches_to_the_expected_gates():
    model, _ = build_noise_model(NoiseParams(enabled=True, readout_error=0.02))
    attached = set(model.noise_instructions)
    for gate in ("h", "x", "y", "rx", "ry", "sx", "id"):
        assert gate in attached, f"{gate} should carry 1q relaxation"
    for gate in ("cx", "cz", "swap"):
        assert gate in attached, f"{gate} should carry 2q relaxation"
    assert "ccx" in attached
    assert "measure" in attached, "readout error should be attached"


def test_virtual_z_gates_carry_no_noise():
    """Z, S, T, RZ and P are frame changes: zero duration, so no relaxation.

    This is deliberate and matches real superconducting hardware, where a
    virtual-Z is applied by shifting the phase of later pulses.
    """
    model, _ = build_noise_model(NoiseParams(enabled=True))
    attached = set(model.noise_instructions)
    for gate in ("z", "s", "sdg", "t", "tdg", "rz", "p"):
        assert gate not in attached, f"{gate} is virtual and should be noiseless"


def test_zero_gate_time_means_no_relaxation():
    model, _ = build_noise_model(
        NoiseParams(
            enabled=True,
            gate_time_1q_us=0.0,
            gate_time_2q_us=0.0,
            gate_time_3q_us=0.0,
            readout_error=0.0,
        )
    )
    assert not set(model.noise_instructions)


def test_basis_gates_keep_gates_undecomposed():
    """One user-facing gate should be roughly one noise event."""
    for gate in ("h", "x", "cx", "ccx", "swap"):
        assert gate in BASIS_GATES


# ------------------------------------------------------- end-to-end via Aer
def test_readout_error_flips_measurements_at_the_requested_rate():
    ir = CircuitIR.from_dict({
        "n_qubits": 1, "n_clbits": 1,
        "ops": [
            {"kind": "gate", "gate": "x", "qubits": [0], "layer": 0},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
        ],
    })
    from app.quantum.backends import qiskit_aer

    params = NoiseParams(
        enabled=True, t1_us=1e9, t2_us=1e9, readout_error=0.2,
        gate_time_1q_us=0.0, gate_time_2q_us=0.0, gate_time_3q_us=0.0,
    )
    counts = qiskit_aer.run(ir, shots=20000, noise=params, seed=5)["counts"]
    flipped = counts.get("0", 0) / sum(counts.values())
    assert flipped == pytest.approx(0.2, abs=0.02)


def test_two_qubit_error_hits_both_qubits_equally():
    """The tensored 2q error must not favour one qubit over the other."""
    from app.quantum.backends import qiskit_aer

    t1, gate_time = 50.0, 10.0
    ir = CircuitIR.from_dict({
        "n_qubits": 2, "n_clbits": 2,
        "ops": [
            {"kind": "gate", "gate": "x", "qubits": [0], "layer": 0},
            {"kind": "gate", "gate": "x", "qubits": [1], "layer": 0},
            {"kind": "gate", "gate": "z", "qubits": [1], "controls": [0], "layer": 1},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
            {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
        ],
    })
    params = NoiseParams(
        enabled=True, t1_us=t1, t2_us=t1, readout_error=0.0,
        gate_time_1q_us=0.0, gate_time_2q_us=gate_time, gate_time_3q_us=0.0,
    )
    counts = qiskit_aer.run(ir, shots=40000, noise=params, seed=9)["counts"]
    total = sum(counts.values())
    survival = math.exp(-gate_time / t1)
    for qubit in (0, 1):
        p1 = sum(v for k, v in counts.items() if k[::-1][qubit] == "1") / total
        assert p1 == pytest.approx(survival, abs=0.02)


def test_noise_moves_the_distribution_away_from_ideal():
    from app.quantum.backends import qiskit_aer

    ir = CircuitIR.from_dict({
        "n_qubits": 2, "n_clbits": 2,
        "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
            {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
        ],
    })
    noisy = qiskit_aer.run(
        ir, shots=8000,
        noise=NoiseParams(enabled=True, t1_us=5, t2_us=5, readout_error=0.05),
        seed=4,
    )["probabilities"]
    # A Bell pair can only give 00 or 11 without noise; noise must populate
    # the forbidden outcomes.
    leaked = noisy.get("01", 0.0) + noisy.get("10", 0.0)
    assert leaked > 0.01
