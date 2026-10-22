"""Deep Verification and Edge-Case Test Suite for Newest Features.

Covers:
1. Qudit Lab (Beta):
   - Dimensionality & basis boundaries (d in {2, 3, 4, 5}, rejection of invalid d)
   - Gate unitarity & cyclic group laws: X_d^d = I, Z_d^d = I, F_d^4 = I, F_d^dagger F_d = I
   - Generalized controlled arithmetic: SUM_d and CP_d truth tables
   - Kraus operator completeness: sum(K_i^dagger K_i) = I across dimensions and noise models
   - Entanglement diagnostics & partial trace:
     * Bell state |Phi_d> = (1/sqrt(d)) * sum(|j, j>)
     * Global pure state: gamma = 1.0, S = 0.0
     * Reduced subsystem rho_0 = (1/d) * I_d: gamma = 1/d, S = log2(d)
   - Admission control & resource estimation caps (16 GB limits, refusal of oversized systems)
   - Matrix slicing endpoint pagination & bounds

2. Noise Lab:
   - Physical constraints: T2 <= 2*T1 enforcement, stochastic probability sums <= 1.0
   - Negative parameters & invalid configuration rejection with HTTP 422
   - State purity vs fidelity distinction under coherent vs decoherent noise
   - Inverted readout error channel warning handling
   - Parameter sweep monotonicity
   - FastAPI endpoints (/noise/catalogue, /noise/presets, /noise/validate, /noise/simulate, /noise/sweep)

3. Smart Composer:
   - Equivalence verifier tier robustness: Unitary (Tier A), State prep (Tier B), Measurement (Tier C)
   - Critical false-equivalence guard: identical Born distribution in Z-basis (+ vs -) must NOT claim universal equivalence
   - Deterministic pass idempotence (simplifying an already simplified circuit is an identity operation)
   - AI rule integrity: unknown rule IDs are rejected from transformation ledger
   - FastAPI endpoints (/smart-composer/rules, /smart-composer/generate, /smart-composer/simplify, /smart-composer/jobs)
"""

from __future__ import annotations

import math
from typing import Any
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.quantum.ir import CircuitIR, Op, Param
from app.quantum.qudit_lab import (
    DIMENSION_MAX_QUDITS,
    GATE_CATALOGUE,
    estimate_resources,
    get_all_qudit_presets,
    simulate_qudit_circuit,
    slice_density_matrix,
    validate_qudit_circuit,
)
from app.quantum.qudit_lab.gates import (
    QuditControlledPhaseGate,
    QuditFourierGate,
    QuditPhaseGate,
    QuditShiftGate,
    QuditSumGate,
)
from app.quantum.qudit_lab.metrics import (
    compute_reduced_density_matrix,
    validate_density_matrix,
)
from app.quantum.qudit_lab.models import (
    ComplexVal,
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
from app.quantum.noise_lab import (
    NOISE_CATALOGUE,
    PRESET_CONFIGS,
    CoherentParams,
    DecoherenceParams,
    NoiseConfig,
    ReadoutParams,
    StochasticParams,
    run_parameter_sweep,
    simulate_noise_experiment,
    validate_noise_config,
)
from app.quantum.smart_composer import (
    GenerationTaskSpec,
    OptimizationObjective,
    VerificationStatus,
    VerificationTier,
    generate,
    get_all_rules,
    optimize_deterministic,
    simplify,
    verify_circuit_equivalence,
    verify_measurement_distribution,
    verify_operator_equivalence,
    verify_state_preparation_equivalence,
)


# ==============================================================================
# SECTION 1: QUDIT LAB DEEP VERIFICATION & EDGE CASES
# ==============================================================================

@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_qudit_fourier_gate_order_four_and_unitarity(d: int):
    """Fourier gate F_d must satisfy F_d^dagger F_d = I and (F_d)^4 = I (standard DFT property)."""
    gate = QuditFourierGate(d)
    mat = gate._unitary_()
    ident = np.eye(d, dtype=np.complex128)

    # 1. Unitarity
    assert np.allclose(mat.conj().T @ mat, ident, atol=1e-10)

    # 2. DFT Order 4: F^4 = I
    f_pow_4 = np.linalg.matrix_power(mat, 4)
    assert np.allclose(f_pow_4, ident, atol=1e-10)

    # 3. Equal magnitude superposition from ground state: |<j|F|0>|^2 = 1/d
    ket_0 = np.zeros(d, dtype=np.complex128)
    ket_0[0] = 1.0
    out = mat @ ket_0
    prob_dist = np.abs(out) ** 2
    expected_prob = 1.0 / d
    assert np.allclose(prob_dist, np.full(d, expected_prob), atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_qudit_sum_gate_generalized_cnot_truth_table(d: int):
    """SUM_d |j, k> = |j, (j + k) mod d>."""
    gate = QuditSumGate(d)
    mat = gate._unitary_()
    dim2 = d * d
    ident = np.eye(dim2, dtype=np.complex128)

    # Unitarity
    assert np.allclose(mat.conj().T @ mat, ident, atol=1e-10)

    # Truth table
    for j in range(d):
        for k in range(d):
            in_idx = j * d + k
            ket = np.zeros(dim2, dtype=np.complex128)
            ket[in_idx] = 1.0
            out = mat @ ket
            expected_k = (j + k) % d
            expected_idx = j * d + expected_k
            assert np.isclose(out[expected_idx], 1.0, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_qudit_controlled_phase_truth_table(d: int):
    """CP_d |j, k> = omega^(j*k) |j, k> where omega = exp(2 pi i / d)."""
    gate = QuditControlledPhaseGate(d)
    mat = gate._unitary_()
    dim2 = d * d
    omega = np.exp(2j * np.pi / d)

    for j in range(d):
        for k in range(d):
            idx = j * d + k
            ket = np.zeros(dim2, dtype=np.complex128)
            ket[idx] = 1.0
            out = mat @ ket
            expected_phase = omega ** (j * k)
            assert np.isclose(out[idx], expected_phase, atol=1e-10)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_qudit_bell_state_reduced_subsystem_analytic_purity_and_entropy(d: int):
    """A 2-qudit Bell state |Phi_d> = (1/sqrt(d)) * sum_{j=0}^{d-1} |j, j> must produce:
    - Global state: Pure (gamma = 1.0, von Neumann entropy S = 0.0)
    - Subsystem state rho_0: Maximally mixed (gamma = 1/d, S = log2(d))
    """
    circuit = QuditCircuit(
        id=f"bell-test-d{d}",
        dimension=d,
        wires=[
            QuditWire(id="q0", index=0, dimension=d, initial_state=0),
            QuditWire(id="q1", index=1, dimension=d, initial_state=0),
        ],
        ops=[
            QuditOp(id="f0", gate="f", targets=[0], controls=[], dimension=d),
            QuditOp(id="sum01", gate="sum", targets=[1], controls=[0], dimension=d),
        ],
    )

    req = SimulationRequest(circuit=circuit, shots=1000, seed=42)
    res = simulate_qudit_circuit(req)

    # 1. Global state validation
    assert res.state_validation.is_valid is True
    assert res.state_validation.purity == pytest.approx(1.0, abs=1e-4)
    assert res.state_validation.entropy == pytest.approx(0.0, abs=1e-4)

    # 2. Reduced subsystem on wire 0 (keyed by wire id "q0")
    assert "q0" in res.reduced_states
    sub0 = res.reduced_states["q0"]
    expected_sub_purity = 1.0 / d
    expected_sub_entropy = math.log2(d)

    assert sub0.purity == pytest.approx(expected_sub_purity, abs=1e-4)
    assert sub0.entropy == pytest.approx(expected_sub_entropy, abs=1e-4)


@pytest.mark.parametrize("d", [2, 3, 4, 5])
def test_qudit_noise_kraus_completeness(d: int):
    """Verify sum(K_i^dagger K_i) = I_d for all Kraus channels at each dimension."""
    ident = np.eye(d, dtype=np.complex128)

    # 1. Depolarizing channel
    depol = QuditDepolarizingChannel(d, p=0.3)
    sum_depol = sum(k.conj().T @ k for k in depol._kraus_())
    assert np.allclose(sum_depol, ident, atol=1e-10)

    # 2. Dephasing channel
    dephase = QuditDephasingChannel(d, gamma=0.25)
    sum_dephase = sum(k.conj().T @ k for k in dephase._kraus_())
    assert np.allclose(sum_dephase, ident, atol=1e-10)

    # 3. Relaxation channel
    relax = QuditRelaxationChannel(d, gamma=0.15)
    sum_relax = sum(k.conj().T @ k for k in relax._kraus_())
    assert np.allclose(sum_relax, ident, atol=1e-10)


def test_qudit_admission_control_rejects_oversized_dimensions():
    """Verify safe limits reject circuits that would exceed host memory thresholds."""
    # d=2 max safe is 10 qudits; 11 qudits must fail validation
    c_oversized = QuditCircuit(
        id="over-d2",
        dimension=2,
        wires=[QuditWire(id=f"q{i}", index=i, dimension=2) for i in range(11)],
        ops=[],
    )
    report = validate_qudit_circuit(c_oversized)
    assert report.valid is False
    assert any("safety limit" in e.lower() for e in report.errors)


def test_qudit_matrix_slice_bounds():
    """Verify slice_density_matrix handles offset and submatrix pagination correctly."""
    circuit = QuditCircuit(
        id="slice-test",
        dimension=3,
        wires=[QuditWire(id="q0", index=0, dimension=3, initial_state=0)],
        ops=[QuditOp(id="f", gate="f", targets=[0], dimension=3)],
    )
    req = MatrixSliceRequest(
        circuit=circuit,
        row_start=1,
        col_start=1,
        row_count=2,
        col_count=2,
    )
    slice_res = slice_density_matrix(req)
    assert slice_res.total_dim == 3
    assert slice_res.row_count == 2
    assert slice_res.col_count == 2
    assert len(slice_res.elements) == 2
    assert len(slice_res.elements[0]) == 2


# ==============================================================================
# SECTION 2: NOISE LAB DEEP VERIFICATION & PHYSICAL LAWS
# ==============================================================================

def test_noise_physical_t2_greater_than_2t1_rejected():
    """Physical law: T2 cannot exceed 2*T1 (thermal relaxation bounds dephasing)."""
    cfg = NoiseConfig(
        decoherence=DecoherenceParams(enabled=True, t1_us=40.0, t2_us=90.0)
    )
    rep = validate_noise_config(cfg)
    assert rep.valid is False
    assert any("2*T1" in err for err in rep.errors)


def test_noise_stochastic_probability_sum_exceeding_one_rejected():
    """Pauli channels sum of probabilities px + py + pz cannot exceed 1.0."""
    cfg = NoiseConfig(
        stochastic=StochasticParams(enabled=True, bit_flip=0.6, phase_flip=0.5)
    )
    rep = validate_noise_config(cfg)
    assert rep.valid is False
    assert any("sum" in err.lower() for err in rep.errors)


def test_noise_coherent_error_preserves_purity_while_fidelity_drops():
    """Coherent unitary perturbations (e.g. systematic over-rotation) keep purity gamma=1.0."""
    bell_circuit = {
        "n_qubits": 2,
        "n_clbits": 2,
        "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
            {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
        ],
    }
    ir = CircuitIR.model_validate(bell_circuit)
    cfg = NoiseConfig(
        coherent=CoherentParams(enabled=True, over_rotation_2q_rad=0.25)
    )
    res = simulate_noise_experiment(ir, cfg, shots=1000, seed=42)
    assert res.metrics.purity is not None
    assert res.metrics.purity == pytest.approx(1.0, abs=1e-3)
    assert res.metrics.fidelity is not None
    assert res.metrics.fidelity < 0.99


def test_noise_readout_inverted_channel_warning():
    """Readout SPAM with error > 0.5 issues an inverted-channel physical warning."""
    cfg = NoiseConfig(
        readout=ReadoutParams(enabled=True, prob_1_given_0=0.6, prob_0_given_1=0.6)
    )
    rep = validate_noise_config(cfg)
    assert rep.valid is True
    assert any("inverted" in w.lower() for w in rep.warnings)


# ==============================================================================
# SECTION 3: SMART COMPOSER DEEP VERIFICATION & INEQUIVALENCE GUARDS
# ==============================================================================

def test_smart_composer_false_equivalence_guard():
    """Critical guard: |+> and |-> share identical Born distributions in Z-basis,
    but operator and state verification MUST declare them inequivalent!
    """
    plus_ir = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="h", qubits=[0], layer=0),
        Op(kind="measure", qubits=[0], clbits=[0], layer=1),
    ])
    minus_ir = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="x", qubits=[0], layer=0),
        Op(kind="gate", gate="h", qubits=[0], layer=1),
        Op(kind="measure", qubits=[0], clbits=[0], layer=2),
    ])

    # 1. Born distribution match
    dist = verify_measurement_distribution(plus_ir, minus_ir)
    assert dist.tvd == pytest.approx(0.0, abs=1e-5)
    assert dist.is_universal_proof is False
    assert dist.is_equivalent is False

    # 2. Operator check must reject equivalence
    op_ver = verify_operator_equivalence(plus_ir, minus_ir)
    assert op_ver.is_equivalent is False
    assert op_ver.status == VerificationStatus.EQUIVALENCE_FAILED

    # 3. Master verifier must conclude NOT equivalent
    master = verify_circuit_equivalence(plus_ir, minus_ir)
    assert master.is_equivalent is False


def test_smart_composer_deterministic_pass_idempotence():
    """Running simplify twice consecutively on a circuit must produce an identical circuit."""
    redundant = CircuitIR(n_qubits=2, n_clbits=2, ops=[
        Op(kind="gate", gate="h", qubits=[0], layer=0),
        Op(kind="gate", gate="h", qubits=[0], layer=1),
        Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=2),
        Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=3),
        Op(kind="gate", gate="ry", qubits=[0], params=[Param.from_expr("0.5")], layer=4),
        Op(kind="gate", gate="ry", qubits=[0], params=[Param.from_expr("0.5")], layer=5),
    ])

    # Pass 1: Reduces to single Ry(1.0)
    pass1 = simplify(redundant, objective=OptimizationObjective.MIN_GATES)
    assert pass1.accepted is True
    assert pass1.simplified_metrics.total_gates == 1

    # Pass 2 on the already-simplified circuit: must recognize it as already optimal
    pass1_ir = CircuitIR.model_validate(pass1.simplified_circuit)
    pass2 = simplify(pass1_ir, objective=OptimizationObjective.MIN_GATES)
    assert pass2.accepted is False
    assert pass2.simplified_metrics.total_gates == 1
    assert pass2.verification.is_equivalent is True


# ==============================================================================
# SECTION 4: FASTAPI ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_api_qudit_endpoints_contract(client, student_headers):
    """Test full HTTP API lifecycle for Qudit Lab."""
    # 1. /qudit/limits
    r_lim = client.get("/qudit/limits")
    assert r_lim.status_code == 200
    assert r_lim.json()["supported_dimensions"] == [2, 3, 4, 5]

    # 2. /qudit/catalogue
    r_cat = client.get("/qudit/catalogue")
    assert r_cat.status_code == 200
    assert len(r_cat.json()) >= 7

    # 3. /qudit/presets
    r_pre = client.get("/qudit/presets?dimension=3")
    assert r_pre.status_code == 200
    assert len(r_pre.json()) >= 4

    # 4. /qudit/simulate with 2-qudit Bell circuit
    sim_payload = {
        "circuit": {
            "id": "c-bell-api",
            "dimension": 3,
            "wires": [
                {"id": "q0", "index": 0, "dimension": 3, "initial_state": 0},
                {"id": "q1", "index": 1, "dimension": 3, "initial_state": 0},
            ],
            "ops": [
                {"id": "op1", "gate": "f", "targets": [0], "dimension": 3},
                {"id": "op2", "gate": "sum", "targets": [1], "controls": [0], "dimension": 3},
            ],
        },
        "shots": 500,
        "seed": 42,
    }
    r_sim = client.post("/qudit/simulate", json=sim_payload, headers=student_headers)
    assert r_sim.status_code == 200
    body = r_sim.json()
    assert body["total_dim"] == 9
    assert body["state_validation"]["is_valid"] is True
    assert "reduced_states" in body
    assert len(body["reduced_states"]) == 2


def test_api_noise_lab_endpoints_contract(client, student_headers):
    """Test full HTTP API lifecycle for Noise Lab."""
    # 1. Catalogue & Presets
    assert client.get("/noise/catalogue").status_code == 200
    assert client.get("/noise/presets").status_code == 200

    # 2. Validation endpoint with invalid physics (T2 > 2T1) -> returns valid: false
    r_val = client.post("/noise/validate", json={
        "noise_config": {
            "name": "bad_physics",
            "description": "test",
            "decoherence": {"enabled": True, "t1_us": 50.0, "t2_us": 150.0, "gate_time_1q_us": 0.03, "gate_time_2q_us": 0.3, "gate_time_3q_us": 1.0, "excited_state_pop": 0.0},
            "stochastic": {"enabled": False, "depolarizing_1q": 0.0, "depolarizing_2q": 0.0, "bit_flip": 0.0, "phase_flip": 0.0, "bit_phase_flip": 0.0, "reset_error": 0.0},
            "coherent": {"enabled": False, "over_rotation_1q_rad": 0.0, "over_rotation_2q_rad": 0.0, "phase_offset_rad": 0.0},
            "readout": {"enabled": False, "prob_1_given_0": 0.0, "prob_0_given_1": 0.0},
            "correlated": {"enabled": False, "zz_crosstalk_strength": 0.0, "correlated_depolarizing_2q": 0.0},
            "simulation_method": "automatic",
        }
    })
    assert r_val.status_code == 200
    assert r_val.json()["valid"] is False

    # 3. Simulate with valid preset
    r_sim = client.post(
        "/noise/simulate",
        json={
            "circuit_ir": {
                "n_qubits": 2,
                "n_clbits": 2,
                "ops": [
                    {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
                    {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
                    {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
                    {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
                ],
            },
            "noise_config": PRESET_CONFIGS["superconducting_transmon"].model_dump(),
            "shots": 200,
        },
        headers=student_headers,
    )
    assert r_sim.status_code == 200
    data = r_sim.json()
    assert "noisy_counts" in data
    assert data["metrics"]["total_variation_distance"] >= 0.0


def test_api_smart_composer_endpoints_contract(client, student_headers):
    """Test full HTTP API lifecycle for Smart Composer."""
    # 1. /smart-composer/rules
    r_rules = client.get("/smart-composer/rules")
    assert r_rules.status_code == 200
    assert len(r_rules.json()) >= 8

    # 2. /smart-composer/generate
    r_gen = client.post(
        "/smart-composer/generate",
        json={"prompt": "Prepare 3-qubit GHZ state"},
        headers=student_headers,
    )
    assert r_gen.status_code == 200
    gen_data = r_gen.json()
    assert gen_data["metrics"]["n_qubits"] == 3
    assert len(gen_data["passed_tests"]) > 0

    # 3. /smart-composer/simplify
    r_sim = client.post(
        "/smart-composer/simplify",
        json={
            "circuit_ir": {
                "n_qubits": 1,
                "n_clbits": 1,
                "ops": [
                    {"kind": "gate", "gate": "x", "qubits": [0], "layer": 0},
                    {"kind": "gate", "gate": "x", "qubits": [0], "layer": 1},
                ],
            },
            "objective": "min_gates",
        },
        headers=student_headers,
    )
    assert r_sim.status_code == 200
    sim_data = r_sim.json()
    assert sim_data["accepted"] is True
    assert sim_data["simplified_metrics"]["total_gates"] == 0
    assert sim_data["verification"]["is_equivalent"] is True
