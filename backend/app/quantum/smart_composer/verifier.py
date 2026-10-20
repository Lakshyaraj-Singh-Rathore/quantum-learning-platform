"""Independent Layered Circuit Equivalence Verification Engine.

Enforces rigorous separation between:
1. Unitary operator equivalence via numerical matrix verification up to global phase
   within configured tolerance atol (numerical verification, not a formal mathematical proof).
2. Reference state-preparation equivalence (valid only for specified reference input |0>).
3. Exact Born-rule probability distribution comparison (analytical computational basis state probabilities;
   distinguished from finite-shot empirical sampling; explicitly NOT universal operator or state equivalence).
4. Finite-shot empirical sampling distribution comparison (subject to statistical shot noise).
5. Inductive rule certification for registers exceeding exact simulation thresholds.
"""

from __future__ import annotations

import math
import numpy as np

from qiskit.quantum_info import Operator, Statevector

from app.quantum.ir import CircuitIR
from app.quantum.normalize import strip_measurements, to_qiskit
from app.quantum.smart_composer.models import (
    VerificationReport,
    VerificationStatus,
    VerificationTier,
)


def compute_global_phase_difference(u1: np.ndarray, u2: np.ndarray) -> float | None:
    """Extract global phase difference phi in radians where U2 = e^(i phi) * U1."""
    flat_idx = int(np.argmax(np.abs(u1)))
    val1 = u1.ravel()[flat_idx]
    val2 = u2.ravel()[flat_idx]
    if abs(val1) < 1e-10:
        return None
    ratio = val2 / val1
    return float(np.angle(ratio))


def verify_operator_equivalence(
    original_ir: CircuitIR,
    candidate_ir: CircuitIR,
    tolerance: float = 1e-7,
) -> VerificationReport:
    """Tier A: Unitary operator equivalence check up to global phase within numerical tolerance.
    
    Constructs full unitary matrices for both circuits (stripping terminal measurements).
    Performs numerical operator verification across the Hilbert space within configured tolerance.
    Note: Evaluated with finite numerical precision (atol); does not constitute a formal symbolic proof.
    """
    n_qubits = original_ir.n_qubits
    try:
        circ1 = strip_measurements(to_qiskit(original_ir, include_measurements=False))
        circ2 = strip_measurements(to_qiskit(candidate_ir, include_measurements=False))

        op1 = Operator(circ1)
        op2 = Operator(circ2)

        is_equiv = bool(op1.equiv(op2, atol=tolerance))
        phase_diff = compute_global_phase_difference(op1.data, op2.data)

        if is_equiv:
            return VerificationReport(
                status=VerificationStatus.VERIFIED,
                tier=VerificationTier.TIER_A_UNITARY,
                tolerance=tolerance,
                global_phase_difference_rad=round(phase_diff, 5) if phase_diff is not None else 0.0,
                details=f"Numerical Unitary Operator Equivalence verified within tolerance {tolerance} "
                        f"(dim=2^{n_qubits}={2**n_qubits}). "
                        f"Global phase difference: {round(phase_diff or 0.0, 4)} rad. Valid across all input states within numerical tolerance.",
                is_equivalent=True,
                is_universal_proof=True,
                evidential_strength="numerical_operator_verification",
            )
        else:
            diff_matrix = np.abs(op1.data - op2.data)
            max_diff = float(np.max(diff_matrix))
            return VerificationReport(
                status=VerificationStatus.EQUIVALENCE_FAILED,
                tier=VerificationTier.TIER_A_UNITARY,
                tolerance=tolerance,
                details=f"Unitary operators differ! Max matrix entry difference = {max_diff:.4e} > {tolerance}",
                is_equivalent=False,
                is_universal_proof=True,
                evidential_strength="numerical_operator_verification",
            )
    except Exception as exc:
        return VerificationReport(
            status=VerificationStatus.UNVERIFIED,
            tier=VerificationTier.TIER_A_UNITARY,
            tolerance=tolerance,
            details=f"Operator construction failed: {exc}",
            is_equivalent=False,
            is_universal_proof=False,
            evidential_strength="numerical_operator_verification",
        )


def verify_state_preparation_equivalence(
    original_ir: CircuitIR,
    candidate_ir: CircuitIR,
    tolerance: float = 1e-7,
) -> VerificationReport:
    """Tier B: Pure statevector fidelity equivalence from reference |0> state.
    
    Evaluates fidelity |<psi1|psi2>|^2 starting strictly from |0...0>.
    NOTE: Proves equivalence for state preparation tasks, but does NOT prove
    universal operator equivalence for arbitrary input superpositions.
    """
    try:
        circ1 = strip_measurements(to_qiskit(original_ir, include_measurements=False))
        circ2 = strip_measurements(to_qiskit(candidate_ir, include_measurements=False))

        sv1 = Statevector.from_instruction(circ1).data
        sv2 = Statevector.from_instruction(circ2).data

        inner_prod = np.vdot(sv1, sv2)
        fidelity = float(abs(inner_prod) ** 2)

        if abs(1.0 - fidelity) <= tolerance:
            return VerificationReport(
                status=VerificationStatus.STATE_PREPARATION_VERIFIED,
                tier=VerificationTier.TIER_B_STATE,
                tolerance=tolerance,
                fidelity=round(fidelity, 7),
                details=f"Statevector fidelity equivalence verified: F = {fidelity:.7f} (>= 1 - {tolerance}) from |0>.",
                is_equivalent=True,
                is_universal_proof=False,
                evidential_strength="reference_state_preparation",
            )
        else:
            return VerificationReport(
                status=VerificationStatus.EQUIVALENCE_FAILED,
                tier=VerificationTier.TIER_B_STATE,
                tolerance=tolerance,
                fidelity=round(fidelity, 7),
                details=f"Statevector fidelity drop: F = {fidelity:.7f} < 1 - {tolerance} from |0>.",
                is_equivalent=False,
                is_universal_proof=False,
                evidential_strength="reference_state_preparation",
            )
    except Exception as exc:
        return VerificationReport(
            status=VerificationStatus.UNVERIFIED,
            tier=VerificationTier.TIER_B_STATE,
            tolerance=tolerance,
            details=f"Statevector simulation failed: {exc}",
            is_equivalent=False,
            is_universal_proof=False,
            evidential_strength="reference_state_preparation",
        )


def verify_measurement_distribution(
    original_ir: CircuitIR,
    candidate_ir: CircuitIR,
    tolerance: float = 1e-5,
) -> VerificationReport:
    """Tier C: Computational basis exact Born-rule measurement probability distribution check.
    
    Computes Total Variation Distance (TVD) between analytical Born-rule probabilities.
    Distinguished from finite-shot empirical sampling (which is subject to statistical shot noise).
    CRITICAL: Passing this check confirms identical output probabilities in the Z-basis from |0>,
    but does NOT prove operator or state equivalence. Orthogonal states (e.g. |+> and |->)
    have identical 50/50 computational measurement distributions.
    """
    try:
        circ1 = strip_measurements(to_qiskit(original_ir, include_measurements=False))
        circ2 = strip_measurements(to_qiskit(candidate_ir, include_measurements=False))

        sv1 = Statevector.from_instruction(circ1)
        sv2 = Statevector.from_instruction(circ2)

        p1 = sv1.probabilities_dict()
        p2 = sv2.probabilities_dict()

        all_keys = set(p1.keys()) | set(p2.keys())
        tvd = 0.5 * sum(abs(p1.get(k, 0.0) - p2.get(k, 0.0)) for k in all_keys)

        if tvd <= tolerance:
            return VerificationReport(
                status=VerificationStatus.DISTRIBUTION_MATCH,
                tier=VerificationTier.TIER_C_MEASUREMENT,
                tolerance=tolerance,
                tvd=round(tvd, 7),
                details=f"Exact Born-rule probability distributions match in computational basis (TVD = {tvd:.4e}). "
                        "Note: Validates exact analytical probabilities from reference input |0>, distinct from "
                        "finite-shot empirical sampling; this does NOT establish universal operator or state equivalence "
                        "(e.g. orthogonal states |+> and |-> share identical computational measurement distributions).",
                is_equivalent=False,  # Not a universal operator equivalence
                is_universal_proof=False,
                evidential_strength="exact_born_rule_distribution",
            )
        else:
            return VerificationReport(
                status=VerificationStatus.EQUIVALENCE_FAILED,
                tier=VerificationTier.TIER_C_MEASUREMENT,
                tolerance=tolerance,
                tvd=round(tvd, 7),
                details=f"Exact Born-rule probability distribution mismatch (TVD = {tvd:.4e} > {tolerance})",
                is_equivalent=False,
                is_universal_proof=False,
                evidential_strength="exact_born_rule_distribution",
            )
    except Exception as exc:
        return VerificationReport(
            status=VerificationStatus.UNVERIFIED,
            tier=VerificationTier.TIER_C_MEASUREMENT,
            tolerance=tolerance,
            details=f"Born-rule distribution simulation failed: {exc}",
            is_equivalent=False,
            is_universal_proof=False,
            evidential_strength="exact_born_rule_distribution",
        )


def verify_finite_shot_sampling(
    original_ir: CircuitIR,
    candidate_ir: CircuitIR,
    shots: int = 1024,
    tolerance: float = 0.05,
    seed: int = 42,
) -> VerificationReport:
    """Tier C-empirical: Finite-shot empirical sampling distribution comparison.
    
    Explicitly samples from output distributions using finite shots subject to multinomial shot noise.
    Distinct from analytical Born-rule probability calculations.
    """
    try:
        circ1 = strip_measurements(to_qiskit(original_ir, include_measurements=False))
        circ2 = strip_measurements(to_qiskit(candidate_ir, include_measurements=False))

        sv1 = Statevector.from_instruction(circ1)
        sv2 = Statevector.from_instruction(circ2)

        rng = np.random.default_rng(seed)
        probs1 = sv1.probabilities()
        probs2 = sv2.probabilities()

        samples1 = rng.multinomial(shots, probs1)
        samples2 = rng.multinomial(shots, probs2)

        freqs1 = samples1 / shots
        freqs2 = samples2 / shots
        tvd = 0.5 * float(np.sum(np.abs(freqs1 - freqs2)))

        if tvd <= tolerance:
            return VerificationReport(
                status=VerificationStatus.DISTRIBUTION_MATCH,
                tier=VerificationTier.TIER_C_MEASUREMENT,
                tolerance=tolerance,
                tvd=round(tvd, 5),
                details=f"Finite-shot empirical sampling distributions match (shots={shots}, TVD={tvd:.4f} <= {tolerance}). "
                        "Note: Subject to finite sampling variance and shot noise; does NOT prove operator equivalence.",
                is_equivalent=False,
                is_universal_proof=False,
                evidential_strength="finite_shot_sampling",
            )
        else:
            return VerificationReport(
                status=VerificationStatus.EQUIVALENCE_FAILED,
                tier=VerificationTier.TIER_C_MEASUREMENT,
                tolerance=tolerance,
                tvd=round(tvd, 5),
                details=f"Finite-shot sampling TVD exceeded tolerance (shots={shots}, TVD={tvd:.4f} > {tolerance}).",
                is_equivalent=False,
                is_universal_proof=False,
                evidential_strength="finite_shot_sampling",
            )
    except Exception as exc:
        return VerificationReport(
            status=VerificationStatus.UNVERIFIED,
            tier=VerificationTier.TIER_C_MEASUREMENT,
            tolerance=tolerance,
            details=f"Finite-shot sampling failed: {exc}",
            is_equivalent=False,
            is_universal_proof=False,
            evidential_strength="finite_shot_sampling",
        )


def verify_circuit_equivalence(
    original_ir: CircuitIR,
    candidate_ir: CircuitIR,
    tolerance: float = 1e-7,
) -> VerificationReport:
    """Master equivalence verification pipeline for compiler simplification.
    
    1. Rejects structural qubit mismatches.
    2. Rejects dynamic non-unitary circuits.
    3. Runs exact Tier A unitary check for N <= 8.
    4. Runs statevector Tier B check for 8 < N <= 14.
    5. Returns Tier D certified rule requirement for N > 14.
    """
    if original_ir.n_qubits != candidate_ir.n_qubits:
        return VerificationReport(
            status=VerificationStatus.EQUIVALENCE_FAILED,
            tier=VerificationTier.TIER_A_UNITARY,
            details=f"Qubit count mismatch: original has {original_ir.n_qubits}, candidate has {candidate_ir.n_qubits}",
            is_equivalent=False,
            is_universal_proof=True,
        )

    if original_ir.is_dynamic() or candidate_ir.is_dynamic():
        return VerificationReport(
            status=VerificationStatus.UNSUPPORTED_DYNAMIC,
            tier=VerificationTier.TIER_A_UNITARY,
            details="Dynamic circuits with mid-circuit feedback or conditional loops cannot be verified with static unitary operators.",
            is_equivalent=False,
            is_universal_proof=False,
        )

    n_qubits = original_ir.n_qubits

    # 1. Tier A: Exact Unitary Operator Equivalence (N <= 8 qubits)
    if n_qubits <= 8:
        rep = verify_operator_equivalence(original_ir, candidate_ir, tolerance=tolerance)
        if rep.status != VerificationStatus.UNVERIFIED:
            return rep

    # 2. Tier B: Pure Statevector Equivalence (8 < N <= 14 qubits)
    if n_qubits <= 14:
        rep = verify_state_preparation_equivalence(original_ir, candidate_ir, tolerance=tolerance)
        if rep.status != VerificationStatus.UNVERIFIED:
            return rep

    # 3. Tier D: Large circuits require certified rewrite proofs
    return VerificationReport(
        status=VerificationStatus.UNVERIFIED,
        tier=VerificationTier.TIER_D_RULE_CERTIFIED,
        details="Registers > 14 qubits exceed unitary simulation memory limits; equivalence must be certified by verified rule chain.",
        is_equivalent=False,
        is_universal_proof=False,
        evidential_strength="certified_rule_rewrites",
    )
