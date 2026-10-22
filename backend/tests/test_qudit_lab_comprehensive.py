"""Comprehensive test suite for Qudit Lab (Beta).

Verifies:
- All dimensions d in {2, 3, 4, 5}
- Cirq DensityMatrixSimulator execution
- Gate unitarity: X_d^d = I, Z_d^d = I, F_d^dagger F_d = I, SUM_d, CP_d, SWAP_d, R_jk
- Kraus operator completeness & mixed-state generation
- Physical invariants: Trace=1, Hermiticity, Positivity, Purity, Entropy
- Maximally entangled state |Phi_d> and partial trace / reduced states
- Off-diagonal coherence distinguishing phase states
- Resource limits and safety validation
- FastAPI endpoints
"""

from __future__ import annotations

import math
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.quantum.qudit_lab.gates import (
    GATE_CATALOGUE,
    QuditControlledPhaseGate,
    QuditFourierGate,
    QuditPhaseGate,
    QuditRotationGate,
    QuditShiftGate,
    QuditSumGate,
    QuditSwapGate,
    create_cirq_qudit_gate,
)
from app.quantum.qudit_lab.metrics import (
    compute_reduced_density_matrix,
    generate_basis_labels,
    validate_density_matrix,
)
from app.quantum.qudit_lab.models import (
    DephasingNoiseConfig,
    DepolarizingNoiseConfig,
    MatrixSliceRequest,
    QuditCircuit,
    QuditNoiseConfig,
    QuditOp,
    QuditWire,
    RelaxationNoiseConfig,
    SimulationRequest,
)
from app.quantum.qudit_lab.noise import (
    QuditDephasingChannel,
    QuditDepolarizingChannel,
    QuditRelaxationChannel,
)
from app.quantum.qudit_lab.presets import get_all_qudit_presets
from app.quantum.qudit_lab.simulator import simulate_qudit_circuit, slice_density_matrix
from app.quantum.qudit_lab.validator import (
    DIMENSION_MAX_QUDITS,
    estimate_resources,
    validate_qudit_circuit,
)


# ==============================================================================
# 1. Gate Unitarity and Identity Tests across all d in {2, 3, 4, 5}
# ==============================================================================

@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_shift_gate_properties(d: int):
    """Test X_d unitarity, basis mapping, and X_d^d = I."""
    gate = QuditShiftGate(d)
    mat = gate._unitary_()

    # Shape
    assert mat.shape == (d, d)

    # Unitarity: U^dagger U = I
    ident = np.eye(d, dtype=np.complex128)
    assert np.allclose(mat.conj().T @ mat, ident, atol=1e-10)

    # Cyclic property: X_d^d = I
    x_pow_d = np.linalg.matrix_power(mat, d)
    assert np.allclose(x_pow_d, ident, atol=1e-10)

    # Basis action: X_d |j> = |(j+1) mod d>
    for j in range(d):
        ket = np.zeros(d, dtype=np.complex128)
        ket[j] = 1.0
        out = mat @ ket
        expected_target = (j + 1) % d
        assert np.isclose(out[expected_target], 1.0)
        assert np.isclose(np.sum(np.abs(out)), 1.0)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_phase_gate_properties(d: int):
    """Test Z_d unitarity, basis mapping, and Z_d^d = I."""
    gate = QuditPhaseGate(d)
    mat = gate._unitary_()

    assert mat.shape == (d, d)
    ident = np.eye(d, dtype=np.complex128)
    assert np.allclose(mat.conj().T @ mat, ident, atol=1e-10)

    # Z_d^d = I
    z_pow_d = np.linalg.matrix_power(mat, d)
    assert np.allclose(z_pow_d, ident, atol=1e-10)

    # Phase on |0> is 1, on |1> is exp(2pi i / d)
    assert np.isclose(mat[0, 0], 1.0)
    expected_omega = np.exp(2j * np.pi / d)
    assert np.isclose(mat[1, 1], expected_omega)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_fourier_gate_properties(d: int):
    """Test F_d unitarity and equal superposition creation."""
    gate = QuditFourierGate(d)
    mat = gate._unitary_()

    assert mat.shape == (d, d)
    ident = np.eye(d, dtype=np.complex128)
    assert np.allclose(mat.conj().T @ mat, ident, atol=1e-10)

    # Action on |0>: (1/sqrt(d)) * sum |k>
    ket0 = np.zeros(d, dtype=np.complex128)
    ket0[0] = 1.0
    out0 = mat @ ket0

    probs = np.abs(out0) ** 2
    expected_prob = 1.0 / d
    assert np.allclose(probs, expected_prob, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_sum_gate_properties(d: int):
    """Test SUM_d unitarity and modular addition |a, b> -> |a, (a+b) mod d>."""
    gate = QuditSumGate(d)
    mat = gate._unitary_()

    assert mat.shape == (d * d, d * d)
    ident = np.eye(d * d, dtype=np.complex128)
    assert np.allclose(mat.conj().T @ mat, ident, atol=1e-10)

    for a in range(d):
        for b in range(d):
            in_state = np.zeros(d * d, dtype=np.complex128)
            in_idx = a * d + b
            in_state[in_idx] = 1.0

            out_state = mat @ in_state
            out_b = (a + b) % d
            expected_idx = a * d + out_b
            assert np.isclose(out_state[expected_idx], 1.0)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_cp_and_swap_gates(d: int):
    """Test CP_d and SWAP_d unitarity."""
    cp_gate = QuditControlledPhaseGate(d)
    cp_mat = cp_gate._unitary_()
    assert cp_mat.shape == (d * d, d * d)
    ident = np.eye(d * d, dtype=np.complex128)
    assert np.allclose(cp_mat.conj().T @ cp_mat, ident, atol=1e-10)

    swap_gate = QuditSwapGate(d)
    swap_mat = swap_gate._unitary_()
    assert swap_mat.shape == (d * d, d * d)
    assert np.allclose(swap_mat.conj().T @ swap_mat, ident, atol=1e-10)

    # SWAP^2 = I
    assert np.allclose(swap_mat @ swap_mat, ident, atol=1e-10)


def test_rotation_gate_unitarity():
    """Test subspace rotation gate R_jk(theta, phi)."""
    rot = QuditRotationGate(dimension=4, j=1, k=3, theta=np.pi / 3, phi=0.4)
    mat = rot._unitary_()
    assert mat.shape == (4, 4)
    ident = np.eye(4, dtype=np.complex128)
    assert np.allclose(mat.conj().T @ mat, ident, atol=1e-10)
    # Subspace 0 and 2 should be unaffected (identity)
    assert np.isclose(mat[0, 0], 1.0)
    assert np.isclose(mat[2, 2], 1.0)


# ==============================================================================
# 2. Kraus Noise Channel Completeness across all d in {2, 3, 4, 5}
# ==============================================================================

@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_kraus_completeness_depolarizing(d: int):
    """Check sum K_i^dagger K_i = I for generalized depolarizing channel."""
    p = 0.4
    channel = QuditDepolarizingChannel(d, p)
    kraus = channel._kraus_()

    ident = np.eye(d, dtype=np.complex128)
    sum_k_dag_k = sum(k.conj().T @ k for k in kraus)
    assert np.allclose(sum_k_dag_k, ident, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_kraus_completeness_dephasing(d: int):
    """Check sum K_i^dagger K_i = I for generalized dephasing channel."""
    gamma = 0.3
    channel = QuditDephasingChannel(d, gamma)
    kraus = channel._kraus_()

    ident = np.eye(d, dtype=np.complex128)
    sum_k_dag_k = sum(k.conj().T @ k for k in kraus)
    assert np.allclose(sum_k_dag_k, ident, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_kraus_completeness_relaxation(d: int):
    """Check sum K_i^dagger K_i = I for multi-level relaxation channel."""
    gamma = 0.5
    channel = QuditRelaxationChannel(d, gamma)
    kraus = channel._kraus_()

    ident = np.eye(d, dtype=np.complex128)
    sum_k_dag_k = sum(k.conj().T @ k for k in kraus)
    assert np.allclose(sum_k_dag_k, ident, atol=1e-10)


# ==============================================================================
# 3. Density-Matrix Simulation & Physical Invariant Verification
# ==============================================================================

@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_engine_single_qudit_superposition(d: int):
    """Simulate F_d on single qudit, verify density matrix shape, trace, hermiticity, and purity."""
    circuit = QuditCircuit(
        id=f"test-f-{d}",
        dimension=d,
        wires=[QuditWire(id="q0", index=0, dimension=d, initial_state=0)],
        ops=[QuditOp(id="op1", gate="f", targets=[0], controls=[], dimension=d)],
    )

    req = SimulationRequest(circuit=circuit, shots=1000, seed=42)
    res = simulate_qudit_circuit(req)

    # Verification
    assert res.total_dim == d
    assert res.state_validation.is_valid
    assert np.isclose(res.state_validation.trace, 1.0, atol=1e-5)
    assert res.state_validation.is_hermitian
    assert res.state_validation.is_positive_semidefinite
    assert np.isclose(res.state_validation.purity, 1.0, atol=1e-4)

    # All probabilities should be exactly 1/d
    expected_prob = 1.0 / d
    for prob in res.probabilities.values():
        assert np.isclose(prob, expected_prob, atol=1e-4)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_generalized_bell_entanglement(d: int):
    """Prepare |Phi_d> = (1/sqrt(d)) sum |j, j>, verify purity=1 and reduced state purity=1/d."""
    circuit = QuditCircuit(
        id=f"bell-{d}",
        dimension=d,
        wires=[
            QuditWire(id="q0", index=0, dimension=d, initial_state=0),
            QuditWire(id="q1", index=1, dimension=d, initial_state=0),
        ],
        ops=[
            QuditOp(id="op1", gate="f", targets=[0], controls=[], dimension=d),
            QuditOp(id="op2", gate="sum", targets=[1], controls=[0], dimension=d),
        ],
    )

    req = SimulationRequest(circuit=circuit, shots=1000, seed=42)
    res = simulate_qudit_circuit(req)

    assert res.total_dim == d * d
    assert res.state_validation.is_valid
    # Overall 2-qudit state is pure
    assert np.isclose(res.state_validation.purity, 1.0, atol=1e-4)

    # Populations should be 1/d for all |j, j> states, and 0 for |j, k> (j != k)
    for j in range(d):
        for k in range(d):
            label = f"|{j},{k}⟩"
            expected = 1.0 / d if j == k else 0.0
            assert np.isclose(res.populations.get(label, 0.0), expected, atol=1e-4)

    # Partial trace: reduced state on wire 0 must be maximally mixed with purity 1/d
    red_q0 = res.reduced_states["q0"]
    assert np.isclose(red_q0.purity, 1.0 / d, atol=1e-4)
    expected_entropy = math.log2(d)
    assert np.isclose(red_q0.entropy, expected_entropy, atol=1e-4)


def test_mixed_state_from_noise():
    """Verify that applying depolarizing noise drops purity below 1.0 (mixed state)."""
    d = 3
    circuit = QuditCircuit(
        id="test-noise-purity",
        dimension=d,
        wires=[QuditWire(id="q0", index=0, dimension=d, initial_state=0)],
        ops=[QuditOp(id="op1", gate="f", targets=[0], controls=[], dimension=d)],
    )

    noise = QuditNoiseConfig(depolarizing=DepolarizingNoiseConfig(enabled=True, p=0.4))
    req = SimulationRequest(circuit=circuit, noise=noise, shots=500, seed=42)
    res = simulate_qudit_circuit(req)

    assert res.noisy is True
    assert res.state_validation.is_valid
    # For p=0.4 on qutrit pure state, analytical purity is (1-p + p/3)^2 + 2*(p/3)^2
    # = (0.6 + 0.1333)^2 + 2*(0.1333)^2 = 0.5377 + 0.0355 = 0.5733
    assert res.state_validation.purity < 0.95
    assert np.isclose(res.state_validation.purity, 0.5733, atol=1e-2)
    assert res.state_validation.entropy > 0.5


@pytest.mark.parametrize("d", [2, 3, 4, 5])
@pytest.mark.parametrize("p", [0.0, 0.10, 0.35, 0.70, 1.0])
def test_depolarizing_channel_analytical_oracle(d: int, p: float):
    """Deterministic regression test: verifies that simulated density-matrix purity matches
    the independent analytical oracle Tr(E(rho)^2) = (1-p)^2 + 2p(1-p)/d + p^2/d
    across all supported dimensions d in {2,3,4,5} and error probabilities p in {0, 0.1, 0.35, 0.7, 1.0}.

    Assesses:
    - Trace preservation: Tr(E(rho)) = 1.0
    - Hermiticity: E(rho) = E(rho)^dagger
    - Positivity: lambda_min >= 0
    - Numerical purity match against independent theoretical oracle
    - Extremal behavior at p=0 (pure state) and p=1 (maximally mixed state (1/d)*I)
    - Specific benchmark points: d=3, p=0.35 -> 0.6150 and d=5, p=0.10 -> 0.8480
    """
    circuit = QuditCircuit(
        id=f"test-depol-oracle-{d}-{p}",
        dimension=d,
        wires=[QuditWire(id="q0", index=0, dimension=d, initial_state=0)],
        ops=[QuditOp(id="op1", gate="f", targets=[0], controls=[], dimension=d)],
    )

    noise = QuditNoiseConfig(depolarizing=DepolarizingNoiseConfig(enabled=True, p=p))
    req = SimulationRequest(circuit=circuit, noise=noise, calculate_entropy=True)
    res = simulate_qudit_circuit(req)

    # 1. Physical invariants
    assert res.state_validation.is_valid
    assert np.isclose(res.state_validation.trace, 1.0, atol=1e-6)
    assert res.state_validation.is_hermitian
    assert res.state_validation.is_positive_semidefinite

    # 2. Independent analytical purity oracle: Tr(E(rho)^2) = (1-p)^2 + 2p(1-p)/d + p^2/d
    expected_purity = (1.0 - p) ** 2 + 2.0 * p * (1.0 - p) / d + (p ** 2) / d
    assert np.isclose(res.state_validation.purity, expected_purity, atol=1e-5), (
        f"Purity mismatch for d={d}, p={p}: measured={res.state_validation.purity}, expected={expected_purity}"
    )

    # 3. Extremal and benchmark assertions
    if p == 0.0:
        assert np.isclose(res.state_validation.purity, 1.0, atol=1e-5)
        assert res.state_validation.entropy is not None
        assert np.isclose(res.state_validation.entropy, 0.0, atol=1e-4)
    elif p == 1.0:
        # Maximally mixed state: rho = (1/d)*I, purity = 1/d, entropy = log2(d)
        assert np.isclose(res.state_validation.purity, 1.0 / d, atol=1e-5)
        expected_entropy = math.log2(d)
        assert res.state_validation.entropy is not None
        assert np.isclose(res.state_validation.entropy, expected_entropy, atol=1e-4)
        for label, prob in res.probabilities.items():
            assert np.isclose(prob, 1.0 / d, atol=1e-4)
    elif d == 3 and p == 0.35:
        # Explicit verification: qutrit with p=0.35 yields Tr(rho^2) = 0.6150
        assert np.isclose(res.state_validation.purity, 0.6150, atol=1e-4)
    elif d == 5 and p == 0.10:
        # Explicit verification: 5-level with p=0.10 yields Tr(rho^2) = 0.8480
        assert np.isclose(res.state_validation.purity, 0.8480, atol=1e-4)


def test_phase_coherence_distinction():
    """Prove that computational-basis populations can be identical while off-diagonal coherences differ."""
    d = 3
    # Circuit A: |+> state prepared with F_3
    circ_a = QuditCircuit(
        id="circ-a",
        dimension=d,
        wires=[QuditWire(id="q0", index=0, dimension=d, initial_state=0)],
        ops=[QuditOp(id="op1", gate="f", targets=[0], controls=[], dimension=d)],
    )
    # Circuit B: |+> followed by phase gate Z_3
    circ_b = QuditCircuit(
        id="circ-b",
        dimension=d,
        wires=[QuditWire(id="q0", index=0, dimension=d, initial_state=0)],
        ops=[
            QuditOp(id="op1", gate="f", targets=[0], controls=[], dimension=d),
            QuditOp(id="op2", gate="z", targets=[0], controls=[], dimension=d),
        ],
    )

    res_a = simulate_qudit_circuit(SimulationRequest(circuit=circ_a))
    res_b = simulate_qudit_circuit(SimulationRequest(circuit=circ_b))

    # Diagonal populations are identical: all 1/3
    for label in res_a.populations:
        assert np.isclose(res_a.populations[label], res_b.populations[label], atol=1e-5)

    # But off-diagonal density matrix elements differ in phase!
    rho_a = np.array([[c.real + 1j * c.imag for c in row] for row in res_a.density_matrix])
    rho_b = np.array([[c.real + 1j * c.imag for c in row] for row in res_b.density_matrix])

    # Element (0, 1) has changed phase
    assert not np.isclose(rho_a[0, 1], rho_b[0, 1], atol=1e-4)


# ==============================================================================
# 4. Resource Limits & Validator Tests
# ==============================================================================

def test_resource_limits_rejection():
    """Verify that exceeding qudit limit for a dimension is safely rejected."""
    # d=3 max allowed is 6 qudits. Requesting 7 qudits must fail.
    oversized_wires = [QuditWire(id=f"q{i}", index=i, dimension=3, initial_state=0) for i in range(7)]
    circuit = QuditCircuit(
        id="oversized",
        dimension=3,
        wires=oversized_wires,
        ops=[],
    )

    report = validate_qudit_circuit(circuit)
    assert not report.valid
    assert any("exceeds the safety limit" in err for err in report.errors)


def test_resource_estimator_values():
    """Verify raw density matrix bytes formula: 16 * D^2."""
    dims = [3, 3]  # D = 9, D^2 = 81, bytes = 81 * 16 = 1296
    est = estimate_resources(dims)
    assert est.total_dim == 9
    assert est.raw_density_matrix_bytes == 1296
    assert est.within_budget


# ==============================================================================
# 5. FastAPI Endpoints Integration
# ==============================================================================

def test_api_limits_endpoint(client):
    """GET /qudit/limits returns safe caps and supported dimensions."""
    resp = client.get("/qudit/limits")
    assert resp.status_code == 200
    data = resp.json()
    assert data["supported_dimensions"] == [2, 3, 4, 5]
    assert data["safe_limits"]["3"] == 6
    assert data["safe_limits"]["5"] == 4


def test_api_catalogue_endpoint(client):
    """GET /qudit/catalogue returns gate catalogue."""
    resp = client.get("/qudit/catalogue")
    assert resp.status_code == 200
    gates = resp.json()
    gate_ids = [g["id"] for g in gates]
    assert "x" in gate_ids
    assert "z" in gate_ids
    assert "f" in gate_ids
    assert "sum" in gate_ids
    assert "cp" in gate_ids
    assert "swap" in gate_ids
    assert "r_jk" in gate_ids


def test_api_presets_endpoint(client):
    """GET /qudit/presets returns educational presets."""
    resp = client.get("/qudit/presets?dimension=3")
    assert resp.status_code == 200
    presets = resp.json()
    assert len(presets) >= 5
    titles = [p["title"] for p in presets]
    assert any("Shift" in t for t in titles)
    assert any("Bell State" in t for t in titles)


def test_api_validate_endpoint(client):
    """POST /qudit/validate validates circuit topology."""
    circuit = {
        "id": "c1",
        "dimension": 3,
        "wires": [{"id": "q0", "index": 0, "dimension": 3, "initial_state": 0}],
        "ops": [{"id": "op1", "gate": "x", "targets": [0], "controls": [], "dimension": 3}],
    }
    resp = client.post("/qudit/validate", json=circuit)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert data["resource_estimate"]["total_dim"] == 3


def test_api_simulation_endpoint(client, student_headers):
    """POST /qudit/simulate executes genuine density matrix simulation."""
    payload = {
        "circuit": {
            "id": "c-test-api",
            "dimension": 3,
            "wires": [{"id": "q0", "index": 0, "dimension": 3, "initial_state": 0}],
            "ops": [{"id": "op1", "gate": "f", "targets": [0], "controls": [], "dimension": 3}],
        },
        "shots": 500,
        "seed": 42,
    }
    resp = client.post("/qudit/simulate", json=payload, headers=student_headers)
    assert resp.status_code == 200
    assert resp.json()["total_dim"] == 3
    assert resp.json()["state_validation"]["is_valid"] is True
    assert resp.json()["state_validation"]["is_positive_semidefinite"] is True
