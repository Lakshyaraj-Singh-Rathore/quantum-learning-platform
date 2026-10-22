"""Pydantic models and schemas for Qudit Lab (Beta)."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class QuditWire(BaseModel):
    """A quantum wire with an explicit local dimension d >= 2."""
    id: str = Field(description="Unique wire identifier, e.g. 'q0'")
    index: int = Field(ge=0, description="0-indexed position in circuit")
    dimension: int = Field(ge=2, le=5, description="Local Hilbert-space dimension d in {2, 3, 4, 5}")
    initial_state: int = Field(default=0, ge=0, description="Initial computational basis level |j> in {0, ..., d-1}")
    label: str | None = Field(default=None, description="Optional display label")


class QuditOp(BaseModel):
    """An operation acting on one or more qudits."""
    id: str = Field(description="Unique operation instance ID")
    gate: str = Field(description="Gate type, e.g. 'x', 'z', 'f', 'sum', 'cp', 'swap', 'r_jk', 'measure'")
    targets: list[int] = Field(description="Target qudit indices")
    controls: list[int] = Field(default_factory=list, description="Control qudit indices")
    params: dict[str, Any] = Field(default_factory=dict, description="Gate parameters, e.g. theta, phi, j, k, power, levels")
    dimension: int = Field(ge=2, le=5, description="Local dimension the gate is acting on")


class DepolarizingNoiseConfig(BaseModel):
    enabled: bool = False
    p: float = Field(default=0.05, ge=0.0, le=1.0, description="Depolarizing error probability")


class DephasingNoiseConfig(BaseModel):
    enabled: bool = False
    gamma: float = Field(default=0.05, ge=0.0, le=1.0, description="Coherence damping factor")


class RelaxationNoiseConfig(BaseModel):
    enabled: bool = False
    gamma: float = Field(default=0.05, ge=0.0, le=1.0, description="Multi-level relaxation decay probability")


class QuditNoiseConfig(BaseModel):
    """Noise configuration for qudit density-matrix simulation."""
    depolarizing: DepolarizingNoiseConfig = Field(default_factory=DepolarizingNoiseConfig)
    dephasing: DephasingNoiseConfig = Field(default_factory=DephasingNoiseConfig)
    relaxation: RelaxationNoiseConfig = Field(default_factory=RelaxationNoiseConfig)

    def is_active(self) -> bool:
        return (
            (self.depolarizing.enabled and self.depolarizing.p > 0.0)
            or (self.dephasing.enabled and self.dephasing.gamma > 0.0)
            or (self.relaxation.enabled and self.relaxation.gamma > 0.0)
        )


class QuditCircuit(BaseModel):
    """Canonical versioned QuditCircuit representation."""
    version: str = "1.0"
    id: str = Field(default="qudit-circuit-1", description="Circuit identifier")
    name: str = Field(default="Qudit Experiment", description="Circuit name")
    dimension: int = Field(default=3, ge=2, le=5, description="Global dimension for uniform circuits")
    wires: list[QuditWire] = Field(default_factory=list)
    ops: list[QuditOp] = Field(default_factory=list)


class ResourceEstimate(BaseModel):
    """Memory and execution resource estimates."""
    dimensions: list[int]
    total_dim: int
    raw_density_matrix_bytes: int
    estimated_peak_bytes: int
    within_budget: bool
    budget_bytes: int
    max_qudits_allowed: int
    message: str


class CircuitValidationReport(BaseModel):
    """Result of static circuit validation."""
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    resource_estimate: ResourceEstimate | None = None


class ComplexVal(BaseModel):
    real: float
    imag: float
    mag: float
    phase: float


class StateValidation(BaseModel):
    """Quantum physical invariant check for density matrix."""
    is_valid: bool
    trace: float
    trace_residual: float
    hermiticity_residual: float
    is_hermitian: bool
    min_eigenvalue: float
    is_positive_semidefinite: bool
    purity: float
    entropy: float | None = None
    diagnostics: list[str] = Field(default_factory=list)


class ReducedStateResult(BaseModel):
    """Reduced density matrix for a subsystem."""
    wire_index: int
    dimension: int
    density_matrix: list[list[ComplexVal]]
    purity: float
    entropy: float | None
    populations: list[float]


class SimulationRequest(BaseModel):
    """Request to execute a qudit density-matrix simulation."""
    circuit: QuditCircuit
    noise: QuditNoiseConfig | None = None
    shots: int | None = Field(default=1024, ge=1, le=10000)
    seed: int | None = Field(default=42)
    calculate_entropy: bool = True
    density_matrix_max_dim: int = Field(default=64, description="Max Hilbert space dimension to serialize full matrix")


class SimulationResult(BaseModel):
    """Comprehensive result of density-matrix execution."""
    circuit_id: str
    dimension: int
    n_qudits: int
    total_dim: int
    basis_labels: list[str]
    populations: dict[str, float]
    coherences: dict[str, float]
    probabilities: dict[str, float]
    samples: dict[str, int] | None = None
    state_validation: StateValidation
    density_matrix: list[list[ComplexVal]] | None = None
    density_matrix_truncated: bool = False
    reduced_states: dict[str, ReducedStateResult] = Field(default_factory=dict)
    execution_time_ms: float
    memory_estimate_bytes: int
    noisy: bool
    warnings: list[str] = Field(default_factory=list)


class MatrixSliceRequest(BaseModel):
    circuit: QuditCircuit
    noise: QuditNoiseConfig | None = None
    row_start: int = 0
    row_count: int = 16
    col_start: int = 0
    col_count: int = 16


class MatrixSliceResponse(BaseModel):
    total_dim: int
    row_start: int
    row_count: int
    col_start: int
    col_count: int
    basis_rows: list[str]
    basis_cols: list[str]
    elements: list[list[ComplexVal]]
