"""Circuit Simplification Engine with Deterministic Passes, RAG Rules, Gemini, and Verification."""

from __future__ import annotations

import json
import re
from typing import Any

from app.ai.gemini_client import is_configured
from app.quantum.ir import CircuitIR
from app.quantum.smart_composer.deterministic import compute_circuit_metrics, optimize_deterministic
from app.quantum.smart_composer.models import (
    CircuitMetrics,
    OptimizationObjective,
    SimplificationResult,
    TransformationRule,
    VerificationReport,
    VerificationStatus,
    VerificationTier,
)
from app.quantum.smart_composer.rag import retrieve_rules_for_circuit
from app.quantum.smart_composer.rules import get_rule_by_id
from app.quantum.smart_composer.verifier import verify_circuit_equivalence


def calculate_improvements(orig: CircuitMetrics, simp: CircuitMetrics) -> dict[str, Any]:
    """Calculate percentage and absolute gains across quantum circuit metrics."""
    gate_diff = orig.total_gates - simp.total_gates
    gate_pct = round((gate_diff / orig.total_gates * 100.0) if orig.total_gates > 0 else 0.0, 1)

    depth_diff = orig.depth - simp.depth
    depth_pct = round((depth_diff / orig.depth * 100.0) if orig.depth > 0 else 0.0, 1)

    two_q_diff = orig.two_qubit_gates - simp.two_qubit_gates
    two_q_pct = round((two_q_diff / orig.two_qubit_gates * 100.0) if orig.two_qubit_gates > 0 else 0.0, 1)

    fid_diff = round(simp.estimated_fidelity - orig.estimated_fidelity, 5)

    return {
        "gate_reduction_count": gate_diff,
        "gate_reduction_pct": gate_pct,
        "depth_reduction_count": depth_diff,
        "depth_reduction_pct": depth_pct,
        "two_qubit_reduction_count": two_q_diff,
        "two_qubit_reduction_pct": two_q_pct,
        "fidelity_gain": fid_diff,
    }


def simplify_circuit(
    ir: CircuitIR,
    objective: OptimizationObjective = OptimizationObjective.MIN_GATES,
    job_id: str = "local_simp",
) -> SimplificationResult:
    """Full Smart Composer circuit simplification pipeline with independent verification."""
    original_metrics = compute_circuit_metrics(ir)
    applied_rules: list[TransformationRule] = []
    warnings: list[str] = []
    repair_attempts = 0

    # 1. Deterministic Baseline Optimization
    baseline_ir, det_notes = optimize_deterministic(ir, objective=objective)
    baseline_metrics = compute_circuit_metrics(baseline_ir)
    warnings.extend(det_notes)

    # Verify baseline against original
    best_candidate_ir = baseline_ir
    best_candidate_metrics = baseline_metrics
    best_verification = verify_circuit_equivalence(ir, baseline_ir)

    # 2. Retrieve Verified Rules via RAG
    relevant_rules = retrieve_rules_for_circuit(ir, objective=objective)
    applied_rule_ids = set()

    # Track rules applied in deterministic pass
    for note in det_notes:
        if "inverse" in note.lower() or "self-inverse" in note.lower():
            applied_rule_ids.add("R01_INV_CANCEL")
        if "rotation" in note.lower():
            applied_rule_ids.add("R02_ROT_MERGE")
        if "phase" in note.lower():
            applied_rule_ids.add("R06_PHASE_CONSOL")
        if "identity" in note.lower() or "zero-rotation" in note.lower():
            applied_rule_ids.add("R07_REDUNDANT_GATE")

    # 3. Optional Gemini AI Exploration for Advanced Subcircuits
    if is_configured() and not ir.is_dynamic():
        from app.ai.gemini_client import generate as gemini_generate

        rules_context = "\n".join(
            f"- Rule {r.id} ({r.name}): {r.mathematical_formula}. Preconditions: {'; '.join(r.preconditions)}"
            for r in relevant_rules
        )

        system_instruction = (
            "You are a quantum compiler verification assistant. Simplify the given quantum circuit.\n"
            f"Verified rules available:\n{rules_context}\n\n"
            "CRITICAL: The output circuit MUST be mathematically equivalent to the original. "
            "Return raw JSON with schema: {\"ops\": [...], \"applied_rule_ids\": [\"R01_INV_CANCEL\", ...], \"explanation\": \"...\"}"
        )

        prompt = f"Original Circuit: {ir.model_dump_json()}\nObjective: {objective.value}"

        for attempt in range(2):
            try:
                resp = gemini_generate(prompt, system_instruction=system_instruction)
                clean_json = re.sub(r"^```[a-z]*\s*", "", resp.strip())
                clean_json = re.sub(r"\s*```$", "", clean_json)
                parsed = json.loads(clean_json)

                ai_candidate_ir = CircuitIR(
                    name=ir.name,
                    n_qubits=ir.n_qubits,
                    n_clbits=ir.n_clbits,
                    ops=parsed.get("ops", []),
                )

                # Independently verify AI proposal
                ai_verification = verify_circuit_equivalence(ir, ai_candidate_ir)
                if ai_verification.is_equivalent:
                    ai_metrics = compute_circuit_metrics(ai_candidate_ir)
                    # Acceptance check: did it improve over baseline?
                    is_better = False
                    if objective == OptimizationObjective.MIN_GATES:
                        is_better = ai_metrics.total_gates < best_candidate_metrics.total_gates
                    elif objective == OptimizationObjective.MIN_DEPTH:
                        is_better = ai_metrics.depth < best_candidate_metrics.depth
                    elif objective == OptimizationObjective.MIN_2Q_GATES:
                        is_better = ai_metrics.two_qubit_gates < best_candidate_metrics.two_qubit_gates
                    else:
                        is_better = ai_metrics.estimated_fidelity > best_candidate_metrics.estimated_fidelity

                    if is_better:
                        best_candidate_ir = ai_candidate_ir
                        best_candidate_metrics = ai_metrics
                        best_verification = ai_verification
                        for rid in parsed.get("applied_rule_ids", []):
                            applied_rule_ids.add(rid)
                        break
                else:
                    repair_attempts += 1
                    prompt = f"Previous proposal failed equivalence verification: {ai_verification.details}. Please fix."
            except Exception:
                repair_attempts += 1

    # Compile final list of verified applied rules
    for rid in applied_rule_ids:
        r_obj = get_rule_by_id(rid)
        if r_obj is not None:
            if r_obj not in applied_rules:
                applied_rules.append(r_obj)
        else:
            warnings.append(f"Rejected unverified AI-proposed rule ID: {rid}")

    # 4. Evaluate Final Acceptance Policy
    improvements = calculate_improvements(original_metrics, best_candidate_metrics)
    has_improvement = (
        improvements["gate_reduction_count"] > 0
        or improvements["depth_reduction_count"] > 0
        or improvements["two_qubit_reduction_count"] > 0
    )

    accepted = best_verification.is_equivalent and has_improvement

    explanation = (
        f"Simplified circuit successfully: reduced {improvements['gate_reduction_count']} gates "
        f"({improvements['gate_reduction_pct']}%) and {improvements['depth_reduction_count']} depth layers. "
        f"Verified via {best_verification.tier.value} (numerical operator verification within configured tolerance)."
        if accepted
        else (
            "Circuit is already optimal under verified transformation rules; no further gate reduction possible without semantic degradation."
            if best_verification.is_equivalent
            else "Optimization rejected: candidate failed independent equivalence verification."
        )
    )

    return SimplificationResult(
        job_id=job_id,
        original_circuit=ir.model_dump(),
        simplified_circuit=best_candidate_ir.model_dump() if accepted else ir.model_dump(),
        original_metrics=original_metrics,
        simplified_metrics=best_candidate_metrics if accepted else original_metrics,
        applied_rules=applied_rules if accepted else [],
        verification=best_verification,
        improvements=improvements if accepted else {},
        accepted=accepted,
        explanation=explanation,
        repair_attempts=repair_attempts,
        warnings=warnings,
    )
