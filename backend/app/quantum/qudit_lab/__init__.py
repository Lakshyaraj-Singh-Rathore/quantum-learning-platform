"""Qudit Lab (Beta) quantum simulation package."""

from app.quantum.qudit_lab.gates import GATE_CATALOGUE, create_cirq_qudit_gate
from app.quantum.qudit_lab.models import (
    CircuitValidationReport,
    ComplexVal,
    DephasingNoiseConfig,
    DepolarizingNoiseConfig,
    MatrixSliceRequest,
    MatrixSliceResponse,
    QuditCircuit,
    QuditNoiseConfig,
    QuditOp,
    QuditWire,
    RelaxationNoiseConfig,
    ResourceEstimate,
    SimulationRequest,
    SimulationResult,
    StateValidation,
)
from app.quantum.qudit_lab.presets import get_all_qudit_presets
from app.quantum.qudit_lab.simulator import (
    build_cirq_circuit,
    simulate_qudit_circuit,
    slice_density_matrix,
)
from app.quantum.qudit_lab.validator import (
    DIMENSION_MAX_QUDITS,
    EXPANDED_MAX_QUDITS,
    estimate_resources,
    validate_qudit_circuit,
)

__all__ = [
    "CircuitValidationReport",
    "ComplexVal",
    "DephasingNoiseConfig",
    "DepolarizingNoiseConfig",
    "DIMENSION_MAX_QUDITS",
    "EXPANDED_MAX_QUDITS",
    "GATE_CATALOGUE",
    "MatrixSliceRequest",
    "MatrixSliceResponse",
    "QuditCircuit",
    "QuditNoiseConfig",
    "QuditOp",
    "QuditWire",
    "RelaxationNoiseConfig",
    "ResourceEstimate",
    "SimulationRequest",
    "SimulationResult",
    "StateValidation",
    "build_cirq_circuit",
    "create_cirq_qudit_gate",
    "estimate_resources",
    "get_all_qudit_presets",
    "simulate_qudit_circuit",
    "slice_density_matrix",
    "validate_qudit_circuit",
]
