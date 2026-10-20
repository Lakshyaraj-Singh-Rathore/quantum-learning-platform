"""Data models and schemas for Smart Composer (Generation & Simplification)."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class OptimizationObjective(str, Enum):
    MIN_GATES = "min_gates"
    MIN_DEPTH = "min_depth"
    MIN_2Q_GATES = "min_2q_gates"
    BASIS_SYNTHESIS = "basis_synthesis"
    NOISE_AWARE = "noise_aware"


class VerificationTier(str, Enum):
    TIER_A_UNITARY = "tier_a_unitary"           # Numerical Operator.equiv() within configured tolerance atol
    TIER_B_STATE = "tier_b_state"               # Pure statevector fidelity >= 1 - atol from reference |0>
    TIER_C_MEASUREMENT = "tier_c_measurement"   # Output distribution TVD <= atol (exact Born-rule or sampling)
    TIER_D_RULE_CERTIFIED = "tier_d_certified"   # Inductive equivalence via chain of verified rewrite rules


class VerificationStatus(str, Enum):
    VERIFIED = "verified"                               # Numerical unitary operator equivalence verified up to global phase
    STATE_PREPARATION_VERIFIED = "state_prep_verified"   # Output state matches reference from |0>
    DISTRIBUTION_MATCH = "distribution_match"           # Computational basis distribution matches (empirical/Born-rule, NOT universal operator equivalence)
    EQUIVALENCE_FAILED = "equivalence_failed"           # Inequivalent
    UNVERIFIED = "unverified"                           # Incomplete or resource limited
    TIMEOUT = "timeout"
    UNSUPPORTED_DYNAMIC = "unsupported_dynamic"


class SimplificationStage(str, Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    DETERMINISTIC_BASELINE = "deterministic_baseline"
    RETRIEVING_RULES = "retrieving_rules"
    GENERATING_PROPOSALS = "generating_proposals"
    VERIFYING_EQUIVALENCE = "verifying_equivalence"
    REPAIRING = "repairing"
    EVALUATING_ACCEPTANCE = "evaluating_acceptance"
    COMPLETED = "completed"
    FAILED = "failed"


class CircuitMetrics(BaseModel):
    n_qubits: int
    total_gates: int
    depth: int
    two_qubit_gates: int
    gate_counts: dict[str, int] = Field(default_factory=dict)
    estimated_fidelity: float = Field(default=1.0, description="Estimated circuit fidelity under standard depolarizing rates")
    circuit_hash: str = Field(default="", description="Stable SHA-256 hash of the circuit operations")


class TransformationRule(BaseModel):
    id: str
    name: str
    category: str
    mathematical_formula: str
    description: str
    preconditions: list[str] = Field(default_factory=list)
    applicable_gates: list[str] = Field(default_factory=list)
    verified: bool = True


class VerificationReport(BaseModel):
    status: VerificationStatus
    tier: VerificationTier
    tolerance: float = 1e-7
    global_phase_difference_rad: float | None = None
    fidelity: float | None = None
    tvd: float | None = None
    details: str = ""
    is_equivalent: bool = False
    is_universal_proof: bool = False
    evidential_strength: str = "numerical_operator_verification"


class SimplificationResult(BaseModel):
    job_id: str
    original_circuit: dict[str, Any]
    simplified_circuit: dict[str, Any]
    original_metrics: CircuitMetrics
    simplified_metrics: CircuitMetrics
    applied_rules: list[TransformationRule] = Field(default_factory=list)
    verification: VerificationReport
    improvements: dict[str, Any] = Field(default_factory=dict)
    accepted: bool
    explanation: str
    repair_attempts: int = 0
    warnings: list[str] = Field(default_factory=list)


class GenerationTaskSpec(BaseModel):
    prompt: str = Field(description="Natural language instruction for circuit generation")
    target_qubits: int | None = Field(default=None, ge=1, le=20)
    allowed_gates: list[str] | None = None
    max_depth: int | None = None
    desired_state: str | None = None  # e.g. "bell", "ghz", "w", "superposition"


class GenerationResult(BaseModel):
    circuit: dict[str, Any]
    metrics: CircuitMetrics
    task_spec: GenerationTaskSpec
    passed_tests: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    repair_attempts: int = 0
    explanation: str = ""
