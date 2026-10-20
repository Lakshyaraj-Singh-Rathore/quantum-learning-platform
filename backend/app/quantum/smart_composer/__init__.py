"""Quantum Smart Composer Subsystem."""

from app.quantum.smart_composer.deterministic import compute_circuit_hash, compute_circuit_metrics, optimize_deterministic
from app.quantum.smart_composer.generator import generate_circuit_from_task
from app.quantum.smart_composer.models import (
    CircuitMetrics,
    GenerationResult,
    GenerationTaskSpec,
    OptimizationObjective,
    SimplificationResult,
    SimplificationStage,
    TransformationRule,
    VerificationReport,
    VerificationStatus,
    VerificationTier,
)
from app.quantum.smart_composer.rules import TRANSFORMATION_RULES, get_rule_by_id
from app.quantum.smart_composer.service import generate, get_all_rules, get_job_status, simplify
from app.quantum.smart_composer.simplifier import simplify_circuit
from app.quantum.smart_composer.verifier import (
    verify_circuit_equivalence,
    verify_operator_equivalence,
    verify_state_preparation_equivalence,
    verify_measurement_distribution,
    verify_finite_shot_sampling,
)

__all__ = [
    "CircuitMetrics",
    "GenerationResult",
    "GenerationTaskSpec",
    "OptimizationObjective",
    "SimplificationResult",
    "SimplificationStage",
    "TransformationRule",
    "VerificationReport",
    "VerificationStatus",
    "VerificationTier",
    "TRANSFORMATION_RULES",
    "get_rule_by_id",
    "get_all_rules",
    "compute_circuit_hash",
    "compute_circuit_metrics",
    "optimize_deterministic",
    "verify_circuit_equivalence",
    "verify_operator_equivalence",
    "verify_state_preparation_equivalence",
    "verify_measurement_distribution",
    "verify_finite_shot_sampling",
    "generate_circuit_from_task",
    "simplify_circuit",
    "generate",
    "simplify",
    "get_job_status",
]
