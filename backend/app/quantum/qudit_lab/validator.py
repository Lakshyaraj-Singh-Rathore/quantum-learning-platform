"""Resource policy, admission control, and circuit validator for Qudit Lab (Beta)."""

from __future__ import annotations

import math
from app.quantum.qudit_lab.models import (
    CircuitValidationReport,
    QuditCircuit,
    ResourceEstimate,
)

# Initial conservative caps for 16 GB development environment
DIMENSION_MAX_QUDITS: dict[int, int] = {
    2: 10,  # 2^10 = 1024, raw rho ~ 16 MiB
    3: 6,   # 3^6 = 729,   raw rho ~ 8.1 MiB
    4: 5,   # 4^5 = 1024,  raw rho ~ 16 MiB
    5: 4,   # 5^4 = 625,   raw rho ~ 6.0 MiB
}

# Expanded caps for benchmarking / advanced mode (disabled by default)
EXPANDED_MAX_QUDITS: dict[int, int] = {
    2: 12,
    3: 7,
    4: 6,
    5: 5,
}

PEAK_MEMORY_MULTIPLIER: float = 6.0
DEFAULT_BUDGET_BYTES: int = 2 * 1024 * 1024 * 1024  # 2 GiB
MAX_CIRCUIT_OPERATIONS: int = 150


def estimate_resources(
    dimensions: list[int],
    budget_bytes: int = DEFAULT_BUDGET_BYTES,
) -> ResourceEstimate:
    """Calculates exact Hilbert space dimension, raw density matrix size, and estimated peak memory."""
    if not dimensions:
        return ResourceEstimate(
            dimensions=[],
            total_dim=0,
            raw_density_matrix_bytes=0,
            estimated_peak_bytes=0,
            within_budget=True,
            budget_bytes=budget_bytes,
            max_qudits_allowed=0,
            message="Empty circuit",
        )

    total_dim = math.prod(dimensions)
    raw_bytes = 16 * (total_dim ** 2)  # complex128: 16 bytes per element
    estimated_peak = int(raw_bytes * PEAK_MEMORY_MULTIPLIER)

    # Reference max qudits for the primary dimension
    primary_dim = dimensions[0] if dimensions else 3
    max_qudits = DIMENSION_MAX_QUDITS.get(primary_dim, 4)

    within_budget = estimated_peak <= budget_bytes
    msg = (
        f"Hilbert dim D={total_dim}, Raw ρ={raw_bytes / (1024 * 1024):.2f} MiB, "
        f"Est. Peak={estimated_peak / (1024 * 1024):.2f} MiB (Budget: {budget_bytes / (1024 * 1024):.0f} MiB)"
    )

    return ResourceEstimate(
        dimensions=dimensions,
        total_dim=total_dim,
        raw_density_matrix_bytes=raw_bytes,
        estimated_peak_bytes=estimated_peak,
        within_budget=within_budget,
        budget_bytes=budget_bytes,
        max_qudits_allowed=max_qudits,
        message=msg,
    )


def validate_qudit_circuit(
    circuit: QuditCircuit,
    budget_bytes: int = DEFAULT_BUDGET_BYTES,
) -> CircuitValidationReport:
    """Validates circuit topology, gate operand compatibility, dimension rules, and resource limits."""
    errors: list[str] = []
    warnings: list[str] = []

    if not circuit.wires:
        return CircuitValidationReport(
            valid=False,
            errors=["Circuit has no wires. Add at least one qudit wire."],
            warnings=[],
            resource_estimate=None,
        )

    # Validate wires
    dims: list[int] = []
    seen_indices: set[int] = set()
    wire_dims: dict[int, int] = {}

    for w in circuit.wires:
        if w.dimension not in (2, 3, 4, 5):
            errors.append(f"Wire {w.id} has invalid dimension {w.dimension}. Supported: 2, 3, 4, 5.")
        if w.index in seen_indices:
            errors.append(f"Duplicate wire index {w.index} on wire {w.id}.")
        seen_indices.add(w.index)
        wire_dims[w.index] = w.dimension
        dims.append(w.dimension)

        if not (0 <= w.initial_state < w.dimension):
            errors.append(
                f"Wire {w.id} initial state |{w.initial_state}> exceeds dimension {w.dimension}. Must be 0..{w.dimension - 1}."
            )

    # Validate qudit count against limits
    primary_dim = circuit.dimension
    max_allowed = DIMENSION_MAX_QUDITS.get(primary_dim, 4)
    if len(circuit.wires) > max_allowed:
        errors.append(
            f"Circuit has {len(circuit.wires)} qudits at dimension d={primary_dim}, "
            f"which exceeds the safety limit of {max_allowed} systems."
        )

    # Resource estimate
    resource = estimate_resources(dims, budget_bytes=budget_bytes)
    if not resource.within_budget:
        errors.append(
            f"Estimated peak memory ({resource.estimated_peak_bytes / (1024 * 1024):.1f} MiB) "
            f"exceeds server safety budget ({resource.budget_bytes / (1024 * 1024):.1f} MiB)."
        )

    # Validate operations
    if len(circuit.ops) > MAX_CIRCUIT_OPERATIONS:
        errors.append(
            f"Operation count ({len(circuit.ops)}) exceeds maximum permitted ({MAX_CIRCUIT_OPERATIONS})."
        )

    for op in circuit.ops:
        # Check target index bounds
        for t in op.targets:
            if t not in wire_dims:
                errors.append(f"Operation {op.id} ({op.gate}) references non-existent target wire index {t}.")
            elif wire_dims[t] != op.dimension:
                errors.append(
                    f"Operation {op.id} ({op.gate}) dimension {op.dimension} does not match target wire dimension {wire_dims[t]}."
                )

        # Check control index bounds
        for c in op.controls:
            if c not in wire_dims:
                errors.append(f"Operation {op.id} ({op.gate}) references non-existent control wire index {c}.")
            elif wire_dims[c] != op.dimension:
                errors.append(
                    f"Operation {op.id} ({op.gate}) dimension {op.dimension} does not match control wire dimension {wire_dims[c]}."
                )

        # Disallow self-controlling gates
        overlap = set(op.targets).intersection(set(op.controls))
        if overlap:
            errors.append(f"Operation {op.id} ({op.gate}) has overlapping target and control wires: {overlap}.")

        # Gate-specific validation
        g = op.gate.lower().strip()
        if g in ("sum", "cp", "swap"):
            all_wires = op.controls + op.targets
            if len(all_wires) != 2:
                errors.append(f"2-qudit gate {op.gate} requires exactly 2 operands, got {len(all_wires)}.")
            elif len(all_wires) == 2 and wire_dims.get(all_wires[0]) != wire_dims.get(all_wires[1]):
                errors.append(
                    f"2-qudit gate {op.gate} requires matching dimensions on both wires, got {wire_dims.get(all_wires[0])} and {wire_dims.get(all_wires[1])}."
                )
        elif g in ("r_jk", "rot", "r"):
            j = int(op.params.get("j", 0))
            k = int(op.params.get("k", 1))
            dim = op.dimension
            if not (0 <= j < k < dim):
                errors.append(
                    f"Rotation gate {op.id} has invalid levels j={j}, k={k} for dimension {dim}. Must satisfy 0 <= j < k < {dim}."
                )

    return CircuitValidationReport(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        resource_estimate=resource,
    )
