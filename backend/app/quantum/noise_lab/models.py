"""Data models and schemas for Quantum Noise Lab."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


class SupportLevel(str, Enum):
    NATIVE = "native"
    CUSTOM = "custom"
    APPROXIMATE = "approximate"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"


class NoiseCategory(str, Enum):
    DECOHERENCE = "decoherence"
    STOCHASTIC = "stochastic"
    COHERENT = "coherent"
    READOUT = "readout"
    CORRELATED = "correlated"
    HARDWARE = "hardware"


class SimulationMethod(str, Enum):
    AUTOMATIC = "automatic"
    DENSITY_MATRIX = "density_matrix"
    STATEVECTOR = "statevector"
    STABILIZER = "stabilizer"
    MATRIX_PRODUCT_STATE = "matrix_product_state"


class DecoherenceParams(BaseModel):
    """Energy relaxation (T1) and dephasing (T2, T_phi) parameters."""
    enabled: bool = False
    t1_us: float = Field(default=50.0, description="T1 relaxation time in microseconds")
    t2_us: float = Field(default=30.0, description="T2 dephasing time in microseconds")
    t_phi_us: float | None = Field(default=None, description="Derived pure dephasing time in microseconds")
    gate_time_1q_us: float = Field(default=0.03, ge=0.0, description="Single-qubit gate duration (us)")
    gate_time_2q_us: float = Field(default=0.30, ge=0.0, description="Two-qubit gate duration (us)")
    gate_time_3q_us: float = Field(default=1.00, ge=0.0, description="Three-qubit gate duration (us)")
    excited_state_pop: float = Field(default=0.0, ge=0.0, le=0.5, description="Thermal equilibrium population P1")

    @model_validator(mode="after")
    def compute_t_phi(self) -> "DecoherenceParams":
        if self.t1_us > 0 and self.t2_us > 0:
            # 1/T2 = 1/(2*T1) + 1/T_phi => 1/T_phi = 1/T2 - 1/(2*T1)
            rate_2 = 1.0 / self.t2_us
            rate_1_half = 1.0 / (2.0 * self.t1_us)
            diff = rate_2 - rate_1_half
            if diff > 1e-12:
                self.t_phi_us = round(1.0 / diff, 4)
            elif abs(diff) <= 1e-12:
                self.t_phi_us = 1e9  # infinite (no pure dephasing)
            else:
                self.t_phi_us = None  # unphysical (T2 > 2*T1)
        return self


class StochasticParams(BaseModel):
    """Standard stochastic quantum error channels."""
    enabled: bool = False
    depolarizing_1q: float = Field(default=0.0, ge=0.0, le=1.0, description="1Q depolarizing probability")
    depolarizing_2q: float = Field(default=0.0, ge=0.0, le=1.0, description="2Q depolarizing probability")
    bit_flip: float = Field(default=0.0, ge=0.0, le=1.0, description="Bit flip (Pauli X) error probability")
    phase_flip: float = Field(default=0.0, ge=0.0, le=1.0, description="Phase flip (Pauli Z) error probability")
    bit_phase_flip: float = Field(default=0.0, ge=0.0, le=1.0, description="Bit-phase flip (Pauli Y) error probability")
    reset_error: float = Field(default=0.0, ge=0.0, le=1.0, description="Reset excitation error probability")


class CoherentParams(BaseModel):
    """Systematic coherent unitary calibration errors."""
    enabled: bool = False
    over_rotation_1q_rad: float = Field(default=0.0, description="1Q rotation angle calibration offset (radians)")
    over_rotation_2q_rad: float = Field(default=0.0, description="2Q rotation angle calibration offset (radians)")
    phase_offset_rad: float = Field(default=0.0, description="Z-axis phase calibration offset (radians)")


class ReadoutParams(BaseModel):
    """State preparation and measurement (SPAM) / Readout confusion errors."""
    enabled: bool = False
    prob_1_given_0: float = Field(default=0.01, ge=0.0, le=1.0, description="P(measure 1 | prepared 0)")
    prob_0_given_1: float = Field(default=0.02, ge=0.0, le=1.0, description="P(measure 0 | prepared 1)")


class CorrelatedParams(BaseModel):
    """Multi-qubit correlated errors and crosstalk."""
    enabled: bool = False
    zz_crosstalk_strength: float = Field(default=0.0, ge=0.0, le=1.0, description="Residual ZZ interaction coupling strength")
    correlated_depolarizing_2q: float = Field(default=0.0, ge=0.0, le=1.0, description="Correlated 2-qubit depolarizing rate")


class NoiseConfig(BaseModel):
    """Complete composable noise configuration for simulation experiments."""
    name: str = Field(default="custom_noise", description="Descriptive profile or preset name")
    description: str = Field(default="", description="Educational notes or physical description")
    decoherence: DecoherenceParams = Field(default_factory=DecoherenceParams)
    stochastic: StochasticParams = Field(default_factory=StochasticParams)
    coherent: CoherentParams = Field(default_factory=CoherentParams)
    readout: ReadoutParams = Field(default_factory=ReadoutParams)
    correlated: CorrelatedParams = Field(default_factory=CorrelatedParams)
    simulation_method: SimulationMethod = Field(default=SimulationMethod.AUTOMATIC)

    def is_active(self) -> bool:
        return (
            (self.decoherence.enabled and (self.decoherence.t1_us > 0 or self.decoherence.t2_us > 0))
            or (self.stochastic.enabled and (
                self.stochastic.depolarizing_1q > 0
                or self.stochastic.depolarizing_2q > 0
                or self.stochastic.bit_flip > 0
                or self.stochastic.phase_flip > 0
                or self.stochastic.bit_phase_flip > 0
                or self.stochastic.reset_error > 0
            ))
            or (self.coherent.enabled and (
                abs(self.coherent.over_rotation_1q_rad) > 1e-9
                or abs(self.coherent.over_rotation_2q_rad) > 1e-9
                or abs(self.coherent.phase_offset_rad) > 1e-9
            ))
            or (self.readout.enabled and (self.readout.prob_1_given_0 > 0 or self.readout.prob_0_given_1 > 0))
            or (self.correlated.enabled and (
                self.correlated.zz_crosstalk_strength > 0
                or self.correlated.correlated_depolarizing_2q > 0
            ))
        )


class ValidationReport(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    physical_checks: dict[str, Any] = Field(default_factory=dict)


class NoiseMetrics(BaseModel):
    fidelity: float | None = Field(default=None, description="State fidelity between ideal and noisy states")
    purity: float | None = Field(default=None, description="Purity Tr(rho^2) of the output density matrix")
    trace_distance: float | None = Field(default=None, description="Trace distance between ideal and noisy density matrices")
    total_variation_distance: float = Field(default=0.0, description="Total variation distance between measurement probability distributions")
    entropy_bits: float | None = Field(default=None, description="Von Neumann entropy S(rho) in bits")
    is_exact_density_matrix: bool = Field(default=False, description="True if state fidelity was computed analytically from density matrix")


class NoiseSimulationResult(BaseModel):
    circuit_name: str
    n_qubits: int
    shots: int
    ideal_counts: dict[str, int]
    noisy_counts: dict[str, int]
    ideal_probabilities: dict[str, float]
    noisy_probabilities: dict[str, float]
    metrics: NoiseMetrics
    applied_channels: list[str]
    warnings: list[str]
    method_used: str
    density_matrix_sample: list[list[dict[str, float]]] | None = None  # 2x2 or 4x4 matrix representation for UI
