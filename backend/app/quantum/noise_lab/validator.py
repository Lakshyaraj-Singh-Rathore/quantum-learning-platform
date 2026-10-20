"""Parameter validation and physics consistency engine for Noise Lab."""

from __future__ import annotations

from typing import Any
from app.quantum.noise_lab.models import NoiseConfig, ValidationReport, SimulationMethod


def validate_noise_config(config: NoiseConfig, circuit_qubits: int | None = None) -> ValidationReport:
    """Rigorous physical parameter validation for quantum noise channels.
    
    Validates:
    1. Decoherence bound: T2 <= 2*T1 (derived from 1/T2 = 1/(2*T1) + 1/T_phi).
    2. Finite positive relaxation times.
    3. Proper probability domains [0, 1] and completeness.
    4. Matrix sanity for readout confusion.
    5. Gate time non-negativity.
    6. Qubit count constraints.
    """
    errors: list[str] = []
    warnings: list[str] = []
    physical_checks: dict[str, Any] = {}

    # 1. Decoherence & Relaxation Validation
    d = config.decoherence
    if d.enabled:
        if d.t1_us <= 0:
            errors.append(f"T1 relaxation time must be strictly positive (got {d.t1_us} µs).")
        if d.t2_us <= 0:
            errors.append(f"T2 dephasing time must be strictly positive (got {d.t2_us} µs).")

        if d.t1_us > 0 and d.t2_us > 0:
            physical_max_t2 = 2.0 * d.t1_us
            if d.t2_us > physical_max_t2 + 1e-6:
                errors.append(
                    f"Physical decoherence bound violated: T2 ({d.t2_us:.4g} µs) > 2*T1 ({physical_max_t2:.4g} µs). "
                    "Under the Markovian relaxation relationship 1/T2 = 1/(2*T1) + 1/T_phi, pure dephasing rate "
                    "1/T_phi must be non-negative, meaning T2 cannot physically exceed 2*T1."
                )
            else:
                physical_checks["t2_within_physical_bound"] = True
                physical_checks["t_phi_us"] = d.t_phi_us

        if d.gate_time_1q_us < 0 or d.gate_time_2q_us < 0 or d.gate_time_3q_us < 0:
            errors.append("Gate durations cannot be negative.")

        if d.excited_state_pop < 0 or d.excited_state_pop > 0.5:
            errors.append(f"Excited state population P1 must be in [0, 0.5] (got {d.excited_state_pop}).")

    # 2. Stochastic Error Channels
    s = config.stochastic
    if s.enabled:
        stochastic_fields = [
            ("depolarizing_1q", s.depolarizing_1q),
            ("depolarizing_2q", s.depolarizing_2q),
            ("bit_flip", s.bit_flip),
            ("phase_flip", s.phase_flip),
            ("bit_phase_flip", s.bit_phase_flip),
            ("reset_error", s.reset_error),
        ]
        for name, val in stochastic_fields:
            if val < 0.0 or val > 1.0:
                errors.append(f"{name} probability must be in [0.0, 1.0] (got {val}).")

        pauli_sum = s.bit_flip + s.phase_flip + s.bit_phase_flip
        if pauli_sum > 1.0 + 1e-9:
            errors.append(
                f"Combined Pauli error probabilities sum to {pauli_sum:.4g} > 1.0. "
                "Px + Py + Pz must not exceed unity."
            )
        else:
            physical_checks["pauli_identity_prob"] = round(1.0 - pauli_sum, 6)

    # 3. Coherent Errors
    c = config.coherent
    if c.enabled:
        if abs(c.over_rotation_1q_rad) > 3.14159:
            warnings.append(
                f"Large 1Q over-rotation angle ({c.over_rotation_1q_rad:.3g} rad); "
                "typical calibration errors are << 0.2 rad."
            )
        if abs(c.over_rotation_2q_rad) > 3.14159:
            warnings.append(
                f"Large 2Q over-rotation angle ({c.over_rotation_2q_rad:.3g} rad); "
                "typical calibration errors are << 0.2 rad."
            )

    # 4. Readout Errors
    r = config.readout
    if r.enabled:
        if r.prob_1_given_0 < 0.0 or r.prob_1_given_0 > 1.0:
            errors.append(f"P(1|0) readout confusion must be in [0.0, 1.0] (got {r.prob_1_given_0}).")
        elif r.prob_1_given_0 > 0.5:
            warnings.append(
                f"P(1|0) readout confusion ({r.prob_1_given_0}) > 0.5 represents an inverted measurement channel. "
                "While mathematically valid in Aer, in physical devices this indicates inverted bit labeling."
            )

        if r.prob_0_given_1 < 0.0 or r.prob_0_given_1 > 1.0:
            errors.append(f"P(0|1) readout confusion must be in [0.0, 1.0] (got {r.prob_0_given_1}).")
        elif r.prob_0_given_1 > 0.5:
            warnings.append(
                f"P(0|1) readout confusion ({r.prob_0_given_1}) > 0.5 represents an inverted measurement channel. "
                "While mathematically valid in Aer, in physical devices this indicates inverted bit labeling."
            )
        
        matrix = [
            [1.0 - r.prob_1_given_0, r.prob_1_given_0],
            [r.prob_0_given_1, 1.0 - r.prob_0_given_1]
        ]
        physical_checks["readout_matrix"] = matrix

    # 5. Correlated Errors
    corr = config.correlated
    if corr.enabled:
        if corr.zz_crosstalk_strength < 0.0 or corr.zz_crosstalk_strength > 1.0:
            errors.append("ZZ crosstalk coupling strength must be in [0.0, 1.0].")
        if corr.correlated_depolarizing_2q < 0.0 or corr.correlated_depolarizing_2q > 1.0:
            errors.append("Correlated 2Q depolarizing rate must be in [0.0, 1.0].")

    # 6. Circuit Constraints
    if circuit_qubits is not None:
        if circuit_qubits < 1:
            errors.append("Circuit must have at least 1 qubit.")
        if circuit_qubits > 20:
            errors.append(f"Circuit qubit count ({circuit_qubits}) exceeds platform static limit of 20 qubits.")

    # 7. Simulation Method Compatibility
    if config.simulation_method == SimulationMethod.STABILIZER:
        if config.coherent.enabled and (
            abs(config.coherent.over_rotation_1q_rad) > 1e-6
            or abs(config.coherent.over_rotation_2q_rad) > 1e-6
        ):
            errors.append("Stabilizer simulation method does not support continuous coherent non-Clifford rotations.")
        if config.decoherence.enabled and (config.decoherence.t1_us > 0 or config.decoherence.t2_us > 0):
            warnings.append(
                "Stabilizer simulator approximates non-Clifford amplitude damping via Pauli twirling / sampling."
            )

    return ValidationReport(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        physical_checks=physical_checks,
    )
