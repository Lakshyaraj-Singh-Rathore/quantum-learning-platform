"""Comprehensive test suite for Smart Composer (Generation & Simplification)."""

from __future__ import annotations

import math
import pytest

from app.quantum.ir import CircuitIR, Op, Param
from app.quantum.smart_composer import (
    GenerationTaskSpec,
    OptimizationObjective,
    TRANSFORMATION_RULES,
    VerificationStatus,
    VerificationTier,
    compute_circuit_metrics,
    generate,
    get_all_rules,
    optimize_deterministic,
    simplify,
    verify_circuit_equivalence,
    verify_operator_equivalence,
    verify_state_preparation_equivalence,
    verify_measurement_distribution,
    verify_finite_shot_sampling,
)


# ------------------------------------------------------------------- Rule Library
def test_rule_registry_contains_all_verified_rules():
    rules = get_all_rules()
    assert len(rules) >= 8
    rule_ids = {r.id for r in rules}
    assert {
        "R01_INV_CANCEL",
        "R02_ROT_MERGE",
        "R03_PAULI_PUSH",
        "R04_HADAMARD_CONJ",
        "R05_SWAP_SYNTH",
        "R06_PHASE_CONSOL",
        "R07_REDUNDANT_GATE",
        "R08_TWO_QUBIT_CANCEL",
    } <= rule_ids


# ------------------------------------------------------------------- Equivalence Verifier
def test_tier_a_unitary_equivalence_on_inverse_hadamards():
    orig = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="h", qubits=[0], layer=0),
        Op(kind="gate", gate="h", qubits=[0], layer=1),
    ])
    empty = CircuitIR(n_qubits=1, n_clbits=1, ops=[])

    report = verify_circuit_equivalence(orig, empty)
    assert report.is_equivalent
    assert report.status == VerificationStatus.VERIFIED
    assert report.tier == VerificationTier.TIER_A_UNITARY


def test_tier_a_unitary_detects_intentional_inequivalence():
    orig = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="h", qubits=[0], layer=0),
    ])
    faulty = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="x", qubits=[0], layer=0),
    ])

    report = verify_circuit_equivalence(orig, faulty)
    assert not report.is_equivalent
    assert report.status == VerificationStatus.EQUIVALENCE_FAILED
    assert "differ" in report.details.lower()


def test_tier_a_unitary_handles_global_phase_invariance():
    # Z and e^(i pi) Z differs only by global phase -1 = e^(i pi)
    # Rz(2 pi) is -I, which is equivalent to identity up to global phase
    circ1 = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="rz", qubits=[0], params=[Param.from_expr(f"{2 * math.pi}")], layer=0),
    ])
    empty = CircuitIR(n_qubits=1, n_clbits=1, ops=[])

    report = verify_circuit_equivalence(circ1, empty)
    assert report.is_equivalent
    assert report.status == VerificationStatus.VERIFIED


def test_identical_measurement_distribution_does_not_prove_state_or_operator_equivalence():
    # Construct |+> (H on |0>) and |-> (X then H on |0>).
    # In computational Z-basis, BOTH states have exact 50% |0> and 50% |1> outcomes!
    plus_ir = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="h", qubits=[0], layer=0),
        Op(kind="measure", qubits=[0], clbits=[0], layer=1),
    ])
    minus_ir = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="x", qubits=[0], layer=0),
        Op(kind="gate", gate="h", qubits=[0], layer=1),
        Op(kind="measure", qubits=[0], clbits=[0], layer=2),
    ])

    # 1. Exact Born-rule measurement distribution comparison confirms TVD == 0.0,
    # BUT must NOT report universal circuit equivalence!
    dist_rep = verify_measurement_distribution(plus_ir, minus_ir)
    assert dist_rep.tvd == pytest.approx(0.0, abs=1e-5)
    assert dist_rep.status == VerificationStatus.DISTRIBUTION_MATCH
    assert dist_rep.is_universal_proof is False
    assert dist_rep.is_equivalent is False  # Must not claim universal equivalence!
    assert dist_rep.evidential_strength == "exact_born_rule_distribution"

    # 1b. Finite-shot empirical sampling comparison (distinct from exact Born-rule calculation)
    finite_rep = verify_finite_shot_sampling(plus_ir, minus_ir, shots=1024, tolerance=0.1)
    assert finite_rep.status == VerificationStatus.DISTRIBUTION_MATCH
    assert finite_rep.is_equivalent is False
    assert finite_rep.is_universal_proof is False
    assert finite_rep.evidential_strength == "finite_shot_sampling"

    # 2. Operator equivalence: H != H·X (differs by Z operation, not global phase)
    op_rep = verify_operator_equivalence(plus_ir, minus_ir)
    assert op_rep.is_equivalent is False
    assert op_rep.status == VerificationStatus.EQUIVALENCE_FAILED
    assert op_rep.is_universal_proof is True
    assert op_rep.evidential_strength == "numerical_operator_verification"

    # 3. State preparation equivalence: |+> and |-> are orthogonal (<+|- > = 0)
    state_rep = verify_state_preparation_equivalence(plus_ir, minus_ir)
    assert state_rep.is_equivalent is False
    assert state_rep.fidelity == pytest.approx(0.0, abs=1e-5)
    assert state_rep.evidential_strength == "reference_state_preparation"

    # 4. Master verifier correctly concludes circuits are NOT equivalent
    master_rep = verify_circuit_equivalence(plus_ir, minus_ir)
    assert master_rep.is_equivalent is False


# ------------------------------------------------------------------- Deterministic Passes
def test_adjacent_inverse_pair_cancellation():
    circuit = CircuitIR(n_qubits=2, n_clbits=2, ops=[
        Op(kind="gate", gate="h", qubits=[0], layer=0),
        Op(kind="gate", gate="h", qubits=[0], layer=1),
        Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=2),
        Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=3),
    ])
    simplified, notes = optimize_deterministic(circuit)
    assert len(simplified.ops) == 0
    assert any("h" in n.lower() for n in notes)
    assert any("x" in n.lower() or "cx" in n.lower() for n in notes)


def test_parametric_rotation_merging():
    circuit = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="rx", qubits=[0], params=[Param.from_expr("0.3")], layer=0),
        Op(kind="gate", gate="rx", qubits=[0], params=[Param.from_expr("0.5")], layer=1),
    ])
    simplified, notes = optimize_deterministic(circuit)
    assert len(simplified.ops) == 1
    assert simplified.ops[0].gate == "rx"
    assert simplified.ops[0].params[0].value == pytest.approx(0.8)


def test_parametric_rotation_cancellation_to_identity():
    circuit = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="rz", qubits=[0], params=[Param.from_expr("0.7")], layer=0),
        Op(kind="gate", gate="rz", qubits=[0], params=[Param.from_expr("-0.7")], layer=1),
    ])
    simplified, notes = optimize_deterministic(circuit)
    assert len(simplified.ops) == 0


def test_clifford_phase_consolidation():
    # S · S = Z
    circuit = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="s", qubits=[0], layer=0),
        Op(kind="gate", gate="s", qubits=[0], layer=1),
    ])
    simplified, notes = optimize_deterministic(circuit)
    assert len(simplified.ops) == 1
    assert simplified.ops[0].gate == "z"


# ------------------------------------------------------------------- AI Circuit Generator
def test_generate_bell_state_circuit():
    task = GenerationTaskSpec(prompt="Prepare Bell state |Phi+>")
    result = generate(task)
    assert result.circuit["n_qubits"] == 2
    assert len(result.circuit["ops"]) >= 2
    assert any("Bell State Born Rule" in p for p in result.passed_tests)


def test_generate_ghz_state_circuit():
    task = GenerationTaskSpec(prompt="Create 3-qubit GHZ state")
    result = generate(task)
    assert result.circuit["n_qubits"] == 3
    assert any("GHZ State Born Rule" in p for p in result.passed_tests)


def test_generate_grover_search_circuit():
    task = GenerationTaskSpec(prompt="Grover search algorithm for target |11>")
    result = generate(task)
    assert any("Grover Oracle Target" in p for p in result.passed_tests)


# ------------------------------------------------------------------- Full Simplifier Pipeline
def test_full_simplification_pipeline_accepts_valid_reduction():
    # Circuit with deliberate redundancy:
    # H(0), H(0), X(1) controlled by 0, X(1) controlled by 0, Ry(0.4), Ry(0.6)
    redundant_circuit = CircuitIR(n_qubits=2, n_clbits=2, ops=[
        Op(kind="gate", gate="h", qubits=[0], layer=0),
        Op(kind="gate", gate="h", qubits=[0], layer=1),
        Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=2),
        Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=3),
        Op(kind="gate", gate="ry", qubits=[0], params=[Param.from_expr("0.4")], layer=4),
        Op(kind="gate", gate="ry", qubits=[0], params=[Param.from_expr("0.6")], layer=5),
    ])

    result = simplify(redundant_circuit, objective=OptimizationObjective.MIN_GATES)

    assert result.accepted is True
    assert result.verification.is_equivalent is True
    assert result.simplified_metrics.total_gates == 1  # Only Ry(1.0) survives!
    assert result.original_metrics.total_gates == 6
    assert result.improvements["gate_reduction_count"] == 5
    assert len(result.applied_rules) >= 2


def test_full_simplifier_preserves_already_optimal_circuit():
    # Canonical Bell state cannot be reduced without losing entanglement
    bell = CircuitIR(n_qubits=2, n_clbits=2, ops=[
        Op(kind="gate", gate="h", qubits=[0], layer=0),
        Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=1),
    ])

    result = simplify(bell, objective=OptimizationObjective.MIN_GATES)

    assert result.accepted is False
    assert result.verification.is_equivalent is True
    assert result.simplified_metrics.total_gates == 2
    assert "already optimal" in result.explanation.lower()


def test_simplifier_rejects_shorter_but_inequivalent_candidate():
    # Circuit with 2 gates that is NOT equivalent to empty circuit
    circuit = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="h", qubits=[0], layer=0),
        Op(kind="gate", gate="x", qubits=[0], layer=1),
    ])
    # Empty circuit is shorter (0 gates vs 2 gates), but inequivalent
    empty = CircuitIR(n_qubits=1, n_clbits=1, ops=[])
    ver = verify_circuit_equivalence(circuit, empty)
    assert ver.is_equivalent is False
    assert ver.status == VerificationStatus.EQUIVALENCE_FAILED


def test_simplifier_rejects_non_improving_transformation():
    # X gate cannot be simplified further; an identity rewrite that keeps 1 gate must be rejected
    single_x = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="x", qubits=[0], layer=0),
    ])
    res = simplify(single_x, objective=OptimizationObjective.MIN_GATES)
    assert res.accepted is False
    assert res.simplified_metrics.total_gates == 1


def test_simplifier_rejects_and_warns_on_unrecognized_ai_rule_ids():
    from app.quantum.smart_composer.simplifier import simplify_circuit
    circuit = CircuitIR(n_qubits=1, n_clbits=1, ops=[
        Op(kind="gate", gate="h", qubits=[0], layer=0),
        Op(kind="gate", gate="h", qubits=[0], layer=1),
    ])
    # The simplifier only includes verified rules from the registry
    res = simplify_circuit(circuit, objective=OptimizationObjective.MIN_GATES)
    applied_ids = {r.id for r in res.applied_rules}
    assert "R99_HALLUCINATED_RULE" not in applied_ids



# ------------------------------------------------------------------- API Endpoints
def test_smart_composer_rules_endpoint(client):
    res = client.get("/smart-composer/rules")
    assert res.status_code == 200
    assert len(res.json()) >= 8


def test_smart_composer_generate_endpoint(client, student_headers):
    payload = {"prompt": "Prepare Bell state |Phi+>"}
    res = client.post("/smart-composer/generate", json=payload, headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["metrics"]["n_qubits"] == 2
    assert len(data["passed_tests"]) > 0


def test_smart_composer_simplify_endpoint(client, student_headers):
    circ = {
        "n_qubits": 1,
        "n_clbits": 1,
        "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 1},
        ],
    }
    res = client.post(
        "/smart-composer/simplify",
        json={"circuit_ir": circ, "objective": "min_gates"},
        headers=student_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["accepted"] is True
    assert data["verification"]["is_equivalent"] is True
    assert data["simplified_metrics"]["total_gates"] == 0
