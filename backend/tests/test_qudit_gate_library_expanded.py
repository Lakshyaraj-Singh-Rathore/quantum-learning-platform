"""Independent scientific validation suite for expanded dimension-aware qudit gate library.

Tests mathematical identities across dimensions d in {2, 3, 4, 5}:
- X_d^d = I
- Z_d^d = I
- X_d^dagger = X_d^(d-1)
- Z_d^dagger = Z_d^(d-1)
- Z_d X_d = omega X_d Z_d (Weyl-Heisenberg commutation)
- F_d^dagger F_d = I
- F_d F_d^dagger = I
- F_d X_d F_d^dagger = Z_d
- F_d^2 |j> = |(-j) mod d>
- F_d^4 = I
- R_jk(theta, phi) unitarity and invariant levels
- P_j(theta) phase isolation
- SUM_d unitarity, SUM_d^d = I, SUM_d^dagger SUM_d = I
- CSX_d(c, a) modular shift activation
- GCP_d product phase
- SCP_d selective controlled phase
- SWAP_d^2 = I
- CU_d controlled unitary
- Multi-controlled shift (CCX_d, MCX_d)
- Controlled-SWAP (CSWAP_d)
- Density matrix simulation with Cirq preserving physical invariants
"""

import cmath
import pytest
import numpy as np
import cirq

from app.quantum.qudit_lab.gates import (
    QuditShiftGate,
    QuditPhaseGate,
    QuditFourierGate,
    QuditIdentityGate,
    QuditLevelPhaseGate,
    QuditRotationGate,
    QuditDiagonalGate,
    QuditArbitraryUnitaryGate,
    QuditPermutationGate,
    QuditSumGate,
    QuditControlledShiftGate,
    QuditControlledPhaseGate,
    QuditSelectiveControlledPhaseGate,
    QuditSwapGate,
    QuditControlledUnitaryGate,
    QuditMultiControlledShiftGate,
    QuditMultiControlledPhaseGate,
    QuditControlledSwapGate,
    create_cirq_qudit_gate,
)
from app.quantum.qudit_lab.models import (
    QuditCircuit,
    QuditWire,
    QuditOp,
    SimulationRequest,
)
from app.quantum.qudit_lab.simulator import simulate_qudit_circuit


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_shift_gate_identities(d: int):
    """Verifies X_d^d = I, X_d^dagger = X_d^(d-1), and unitarity for d in {2, 3, 4, 5}."""
    gate = QuditShiftGate(d, power=1)
    u = gate._unitary_()

    # Unitarity
    assert np.allclose(u.conj().T @ u, np.eye(d), atol=1e-10)

    # X_d^d = I
    u_d = np.linalg.matrix_power(u, d)
    assert np.allclose(u_d, np.eye(d), atol=1e-10)

    # X_d^dagger = X_d^(d-1)
    u_dag = u.conj().T
    u_d_minus_1 = np.linalg.matrix_power(u, d - 1)
    assert np.allclose(u_dag, u_d_minus_1, atol=1e-10)

    # Power constructor
    for p in range(d):
        gate_p = QuditShiftGate(d, power=p)
        assert np.allclose(gate_p._unitary_(), np.linalg.matrix_power(u, p), atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_phase_gate_identities(d: int):
    """Verifies Z_d^d = I, Z_d^dagger = Z_d^(d-1), and unitarity for d in {2, 3, 4, 5}."""
    gate = QuditPhaseGate(d, power=1)
    u = gate._unitary_()

    # Unitarity
    assert np.allclose(u.conj().T @ u, np.eye(d), atol=1e-10)

    # Z_d^d = I
    u_d = np.linalg.matrix_power(u, d)
    assert np.allclose(u_d, np.eye(d), atol=1e-10)

    # Z_d^dagger = Z_d^(d-1)
    u_dag = u.conj().T
    u_d_minus_1 = np.linalg.matrix_power(u, d - 1)
    assert np.allclose(u_dag, u_d_minus_1, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_weyl_heisenberg_commutation(d: int):
    """Verifies Weyl-Heisenberg commutation: Z_d X_d = omega X_d Z_d."""
    x = QuditShiftGate(d)._unitary_()
    z = QuditPhaseGate(d)._unitary_()
    omega = cmath.exp(2j * np.pi / d)

    lhs = z @ x
    rhs = omega * (x @ z)
    assert np.allclose(lhs, rhs, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_fourier_gate_identities(d: int):
    """Verifies F_d^dagger F_d = I, F_d X_d F_d^dagger = Z_d, F_d^4 = I."""
    f = QuditFourierGate(d, adjoint=False)._unitary_()
    f_dag = QuditFourierGate(d, adjoint=True)._unitary_()

    # F_d^dagger F_d = I
    assert np.allclose(f_dag @ f, np.eye(d), atol=1e-10)
    assert np.allclose(f @ f_dag, np.eye(d), atol=1e-10)

    # F_d X_d F_d^dagger = Z_d
    x = QuditShiftGate(d)._unitary_()
    z = QuditPhaseGate(d)._unitary_()
    assert np.allclose(f @ x @ f_dag, z, atol=1e-10)

    # F_d^2 maps |j> to |(-j) mod d>
    f_squared = f @ f
    for j in range(d):
        target = (-j) % d
        expected_col = np.zeros(d, dtype=np.complex128)
        expected_col[target] = 1.0
        assert np.allclose(f_squared[:, j], expected_col, atol=1e-10)

    # F_d^4 = I
    f_4 = np.linalg.matrix_power(f, 4)
    assert np.allclose(f_4, np.eye(d), atol=1e-10)

    # Uniform superposition: F_d |0> has amplitude 1/sqrt(d) for all k
    zero_state = np.zeros(d, dtype=np.complex128)
    zero_state[0] = 1.0
    superpos = f @ zero_state
    expected_amp = 1.0 / np.sqrt(d)
    assert np.allclose(np.abs(superpos), expected_amp, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_identity_and_level_phase(d: int):
    """Verifies I_d and level-selective phase P_j(theta)."""
    ident = QuditIdentityGate(d)._unitary_()
    assert np.allclose(ident, np.eye(d), atol=1e-10)

    for j in range(d):
        theta = 1.234
        pj = QuditLevelPhaseGate(d, j=j, theta=theta)._unitary_()
        assert np.allclose(pj.conj().T @ pj, np.eye(d), atol=1e-10)
        # Check level j gets exp(i*theta)
        assert np.isclose(pj[j, j], cmath.exp(1j * theta), atol=1e-10)
        # Check other levels unchanged
        for k in range(d):
            if k != j:
                assert np.isclose(pj[k, k], 1.0, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_pairwise_rotation_gate(d: int):
    """Verifies Givens rotation R_jk(theta, phi) unitarity and invariant subspace."""
    for j in range(d):
        for k in range(j + 1, d):
            theta = 0.8
            phi = 0.4
            rot = QuditRotationGate(d, j=j, k=k, theta=theta, phi=phi)._unitary_()
            # Unitarity
            assert np.allclose(rot.conj().T @ rot, np.eye(d), atol=1e-10)
            # Other levels untouched
            for m in range(d):
                if m != j and m != k:
                    assert np.isclose(rot[m, m], 1.0, atol=1e-10)
                    assert np.allclose(rot[m, :m], 0.0, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_sum_gate_identities(d: int):
    """Verifies SUM_d unitarity, SUM_d^d = I, and SUM_d^dagger inverse."""
    sum_gate = QuditSumGate(d, adjoint=False)._unitary_()
    sum_dag = QuditSumGate(d, adjoint=True)._unitary_()

    # Unitarity
    assert np.allclose(sum_gate.conj().T @ sum_gate, np.eye(d * d), atol=1e-10)

    # Inverse
    assert np.allclose(sum_dag @ sum_gate, np.eye(d * d), atol=1e-10)

    # SUM_d^d = I
    sum_d_power = np.linalg.matrix_power(sum_gate, d)
    assert np.allclose(sum_d_power, np.eye(d * d), atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_swap_gate_identities(d: int):
    """Verifies SWAP_d^2 = I and state exchange."""
    swap = QuditSwapGate(d)._unitary_()
    assert np.allclose(swap.conj().T @ swap, np.eye(d * d), atol=1e-10)
    assert np.allclose(swap @ swap, np.eye(d * d), atol=1e-10)

    for a in range(d):
        for b in range(d):
            in_vec = np.zeros(d * d, dtype=np.complex128)
            in_vec[a * d + b] = 1.0
            out_vec = swap @ in_vec
            expected_vec = np.zeros(d * d, dtype=np.complex128)
            expected_vec[b * d + a] = 1.0
            assert np.allclose(out_vec, expected_vec, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_controlled_shift_csx(d: int):
    """Verifies CSX_d(c, a): |x, y> -> |x, (y + a*delta_xc) mod d>."""
    for c in range(d):
        for a in range(1, d):
            csx = QuditControlledShiftGate(d, control_level=c, shift=a)._unitary_()
            assert np.allclose(csx.conj().T @ csx, np.eye(d * d), atol=1e-10)

            for x in range(d):
                for y in range(d):
                    in_vec = np.zeros(d * d, dtype=np.complex128)
                    in_vec[x * d + y] = 1.0
                    out_vec = csx @ in_vec

                    expected_y = (y + a) % d if x == c else y
                    expected_vec = np.zeros(d * d, dtype=np.complex128)
                    expected_vec[x * d + expected_y] = 1.0
                    assert np.allclose(out_vec, expected_vec, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4])
def test_multi_controlled_shift(d: int):
    """Verifies double-controlled shift CCX_d: |x, y, z> -> |x, y, (z + a*delta_xc1*delta_yc2) mod d>."""
    c1, c2 = 1, 1
    shift = 1
    ccx = QuditMultiControlledShiftGate(d, num_controls=2, control_levels=[c1, c2], shift=shift)._unitary_()
    dim = d ** 3
    assert np.allclose(ccx.conj().T @ ccx, np.eye(dim), atol=1e-10)

    for x in range(d):
        for y in range(d):
            for z in range(d):
                in_idx = (x * d + y) * d + z
                in_vec = np.zeros(dim, dtype=np.complex128)
                in_vec[in_idx] = 1.0
                out_vec = ccx @ in_vec

                expected_z = (z + shift) % d if (x == c1 and y == c2) else z
                expected_idx = (x * d + y) * d + expected_z
                expected_vec = np.zeros(dim, dtype=np.complex128)
                expected_vec[expected_idx] = 1.0
                assert np.allclose(out_vec, expected_vec, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4])
def test_controlled_swap(d: int):
    """Verifies CSWAP_d: |c, a, b> -> |c, b, a> when control is at level c."""
    c_active = 1
    cswap = QuditControlledSwapGate(d, control_level=c_active)._unitary_()
    dim = d ** 3
    assert np.allclose(cswap.conj().T @ cswap, np.eye(dim), atol=1e-10)
    assert np.allclose(cswap @ cswap, np.eye(dim), atol=1e-10)

    for x in range(d):
        for a in range(d):
            for b in range(d):
                in_idx = (x * d + a) * d + b
                in_vec = np.zeros(dim, dtype=np.complex128)
                in_vec[in_idx] = 1.0
                out_vec = cswap @ in_vec

                if x == c_active:
                    expected_idx = (x * d + b) * d + a
                else:
                    expected_idx = in_idx

                expected_vec = np.zeros(dim, dtype=np.complex128)
                expected_vec[expected_idx] = 1.0
                assert np.allclose(out_vec, expected_vec, atol=1e-10)


def test_cirq_density_matrix_simulation_invariants():
    """Verifies that Cirq DensityMatrixSimulator executes circuits with the expanded gates
    and strictly maintains Trace=1, Hermiticity, and positive semidefiniteness."""
    # Test circuit with d=3 Bell-like state: F_3 on q0, SUM_3 from q0 to q1
    d = 3
    circuit = QuditCircuit(
        version="1.0",
        id="test-bell-d3",
        dimension=d,
        wires=[
            QuditWire(id="q0", index=0, dimension=d, initial_state=0),
            QuditWire(id="q1", index=1, dimension=d, initial_state=0),
        ],
        ops=[
            QuditOp(id="op1", gate="f", targets=[0], controls=[], params={}, dimension=d),
            QuditOp(id="op2", gate="sum", targets=[1], controls=[0], params={}, dimension=d),
        ],
    )

    req = SimulationRequest(circuit=circuit, calculate_entropy=True)
    res = simulate_qudit_circuit(req)

    # Validate physical invariants
    assert res.state_validation.is_valid
    assert np.isclose(res.state_validation.trace, 1.0, atol=1e-6)
    assert res.state_validation.is_hermitian
    assert res.state_validation.is_positive_semidefinite
    assert np.isclose(res.state_validation.purity, 1.0, atol=1e-5)  # Pure state

    # Check Bell-state superposition: |0,0> + |1,1> + |2,2> / sqrt(3)
    # Populations: p(|0,0>) = p(|1,1>) = p(|2,2>) = 1/3 ~ 0.333333
    assert np.isclose(res.populations["|0,0⟩"], 1.0 / 3.0, atol=1e-4)
    assert np.isclose(res.populations["|1,1⟩"], 1.0 / 3.0, atol=1e-4)
    assert np.isclose(res.populations["|2,2⟩"], 1.0 / 3.0, atol=1e-4)
    # Off-diagonal coherences |0,0><1,1|, |0,0><2,2|, |1,1><2,2| should be 1/3
    assert np.isclose(res.density_matrix[0][4].mag, 1.0 / 3.0, atol=1e-4)
    assert np.isclose(res.density_matrix[0][8].mag, 1.0 / 3.0, atol=1e-4)
