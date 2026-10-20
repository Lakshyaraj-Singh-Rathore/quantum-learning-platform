"""Retrieval-Augmented Generation (RAG) module for Quantum Circuit Transformation Rules."""

from __future__ import annotations

from app.quantum.ir import CircuitIR
from app.quantum.smart_composer.models import OptimizationObjective, TransformationRule
from app.quantum.smart_composer.rules import TRANSFORMATION_RULES, get_rule_by_id


def retrieve_rules_for_circuit(
    ir: CircuitIR,
    objective: OptimizationObjective = OptimizationObjective.MIN_GATES,
) -> list[TransformationRule]:
    """Retrieve verified transformation rules matching the circuit's gates and optimization opportunities."""
    active_gates = set()
    has_two_qubit = False
    adjacent_candidates = False

    last_gate_on_wire: dict[int, str] = {}
    for op in ir.walk():
        if op.kind == "gate":
            name = (op.gate or "").lower()
            active_gates.add(name)
            if op.controls or len(op.qubits) > 1:
                has_two_qubit = True
            
            # Check adjacent gate types on wire
            for q in op.involved_qubits():
                if q in last_gate_on_wire:
                    adjacent_candidates = True
                last_gate_on_wire[q] = name

    matched_rules: list[TransformationRule] = []

    # R01: Inverse Cancellation
    if adjacent_candidates or has_two_qubit:
        matched_rules.append(get_rule_by_id("R01_INV_CANCEL"))

    # R02: Parametric Rotation Merging
    if active_gates & {"rx", "ry", "rz", "p"}:
        matched_rules.append(get_rule_by_id("R02_ROT_MERGE"))

    # R03: Commutation & Pauli Push
    if has_two_qubit and (active_gates & {"x", "z", "rx", "rz", "p", "s", "t"}):
        matched_rules.append(get_rule_by_id("R03_PAULI_PUSH"))

    # R04: Hadamard Basis Conjugation
    if "h" in active_gates and (active_gates & {"x", "z", "cx"}):
        matched_rules.append(get_rule_by_id("R04_HADAMARD_CONJ"))

    # R05: SWAP Synthesis
    if "swap" in active_gates:
        matched_rules.append(get_rule_by_id("R05_SWAP_SYNTH"))

    # R06: Clifford Phase Consolidation
    if active_gates & {"t", "s", "tdg", "sdg"}:
        matched_rules.append(get_rule_by_id("R06_PHASE_CONSOL"))

    # R07: Trivial Identity / Zero-rotation removal
    matched_rules.append(get_rule_by_id("R07_REDUNDANT_GATE"))

    # R08: Two-qubit cancellation across commutation
    if has_two_qubit:
        matched_rules.append(get_rule_by_id("R08_TWO_QUBIT_CANCEL"))

    # Filter any Nones
    return [r for r in matched_rules if r is not None]
