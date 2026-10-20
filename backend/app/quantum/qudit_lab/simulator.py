"""Cirq-backed Density Matrix Simulation Engine for Qudit Lab (Beta).

Executes genuine density-matrix simulation throughout circuit execution (rho' = U rho U^dagger, rho' = sum K_i rho K_i^dagger).
"""

from __future__ import annotations

import math
import time
from typing import Any
import cirq
import numpy as np

from app.quantum.qudit_lab.gates import create_cirq_qudit_gate
from app.quantum.qudit_lab.metrics import (
    generate_basis_labels,
    get_reduced_state_summary,
    matrix_to_complex_grid,
    validate_density_matrix,
)
from app.quantum.qudit_lab.models import (
    ComplexVal,
    MatrixSliceRequest,
    MatrixSliceResponse,
    QuditCircuit,
    QuditNoiseConfig,
    SimulationRequest,
    SimulationResult,
)
from app.quantum.qudit_lab.noise import get_qudit_noise_operations
from app.quantum.qudit_lab.validator import estimate_resources, validate_qudit_circuit


def compute_basis_index(wire_states: list[int], dimensions: list[int]) -> int:
    """Computes lexicographic computational basis index from wire basis states."""
    idx = 0
    stride = 1
    for state, dim in zip(reversed(wire_states), reversed(dimensions)):
        idx += state * stride
        stride *= dim
    return idx


def build_cirq_circuit(
    circuit: QuditCircuit,
    noise_config: QuditNoiseConfig | None = None,
) -> tuple[cirq.Circuit, list[cirq.Qid], int, list[int]]:
    """Constructs a dimension-aware Cirq circuit from canonical QuditCircuit representation."""
    sorted_wires = sorted(circuit.wires, key=lambda w: w.index)
    qid_map: dict[int, cirq.Qid] = {}
    dimensions: list[int] = []
    wire_states: list[int] = []

    for w in sorted_wires:
        qid = cirq.NamedQid(f"q{w.index}", dimension=w.dimension)
        qid_map[w.index] = qid
        dimensions.append(w.dimension)
        wire_states.append(w.initial_state)

    initial_basis_idx = compute_basis_index(wire_states, dimensions)
    qubit_order = [qid_map[w.index] for w in sorted_wires]

    cirq_ops: list[cirq.Operation] = []

    for op in circuit.ops:
        gate_name = op.gate.lower().strip()
        if gate_name == "measure":
            # For exact density-matrix simulation, measurements are handled as projections or presentation
            continue

        cirq_gate = create_cirq_qudit_gate(op.gate, op.dimension, op.params)

        if op.controls:
            # Multi-qudit operation with explicit control(s) and target(s)
            involved_qids = [qid_map[c] for c in op.controls] + [qid_map[t] for t in op.targets]
            cirq_ops.append(cirq_gate(*involved_qids))
        elif len(op.targets) > 1:
            involved_qids = [qid_map[t] for t in op.targets]
            cirq_ops.append(cirq_gate(*involved_qids))
        else:
            cirq_ops.append(cirq_gate(qid_map[op.targets[0]]))

        # If noise is enabled, apply noise channels to the involved qudits
        if noise_config and noise_config.is_active():
            all_involved_indices = op.controls + op.targets
            for idx in all_involved_indices:
                cirq_ops.extend(get_qudit_noise_operations(qid_map[idx], noise_config))

    # If noise is enabled and there were no ops (e.g. idle circuit), apply noise to all wires
    if noise_config and noise_config.is_active() and not circuit.ops:
        for qid in qubit_order:
            cirq_ops.extend(get_qudit_noise_operations(qid, noise_config))

    cirq_circuit = cirq.Circuit(cirq_ops)
    return cirq_circuit, qubit_order, initial_basis_idx, dimensions


def simulate_qudit_circuit(request: SimulationRequest) -> SimulationResult:
    """Executes genuine density-matrix simulation for a QuditCircuit."""
    start_time = time.perf_counter()

    # 1. Validation and Admission Control
    validation = validate_qudit_circuit(request.circuit)
    if not validation.valid:
        raise ValueError(f"Circuit validation failed: {'; '.join(validation.errors)}")

    resource = validation.resource_estimate or estimate_resources([w.dimension for w in request.circuit.wires])
    total_dim = resource.total_dim

    # 2. Build Cirq circuit
    cirq_circuit, qubit_order, init_idx, dimensions = build_cirq_circuit(
        request.circuit,
        noise_config=request.noise,
    )

    # 3. Simulate with genuine DensityMatrixSimulator (complex128)
    simulator = cirq.DensityMatrixSimulator(dtype=np.complex128)
    sim_result = simulator.simulate(
        cirq_circuit,
        qubit_order=qubit_order,
        initial_state=init_idx,
    )

    rho = sim_result.final_density_matrix
    if rho.dtype != np.complex128:
        rho = rho.astype(np.complex128)

    # 4. Density-matrix validation
    state_val = validate_density_matrix(rho, total_dim, calculate_entropy=request.calculate_entropy)

    # 5. Extract basis labels, populations, coherences and probabilities
    basis_labels = generate_basis_labels(dimensions)

    populations: dict[str, float] = {}
    probabilities_list: list[float] = []

    for idx, label in enumerate(basis_labels):
        pop = float(np.real(rho[idx, idx]))
        clamped_pop = max(0.0, pop)
        populations[label] = round(clamped_pop, 6)
        probabilities_list.append(clamped_pop)

    # Normalize probabilities for sampling
    prob_sum = sum(probabilities_list)
    if prob_sum > 0:
        normalized_probs = [p / prob_sum for p in probabilities_list]
    else:
        normalized_probs = [1.0 / total_dim] * total_dim

    probabilities_dict = {
        basis_labels[i]: round(normalized_probs[i], 6) for i in range(total_dim)
    }

    # Off-diagonal coherences (top 20 most prominent)
    coherences: dict[str, float] = {}
    for r in range(min(total_dim, 16)):
        for c in range(r + 1, min(total_dim, 16)):
            mag = float(np.abs(rho[r, c]))
            if mag > 1e-4:
                coherences[f"{basis_labels[r]}—{basis_labels[c]}"] = round(mag, 6)

    # 6. Seeded shot sampling
    samples: dict[str, int] | None = None
    if request.shots and request.shots > 0:
        rng = np.random.default_rng(request.seed)
        sampled_indices = rng.choice(total_dim, size=request.shots, p=normalized_probs)
        counts = np.bincount(sampled_indices, minlength=total_dim)
        samples = {basis_labels[i]: int(counts[i]) for i in range(total_dim) if counts[i] > 0}

    # 7. Density matrix serialization
    full_density_matrix: list[list[ComplexVal]] | None = None
    truncated = False
    if total_dim <= request.density_matrix_max_dim:
        full_density_matrix = matrix_to_complex_grid(rho)
    else:
        truncated = True

    # 8. Reduced density matrices for each qudit wire
    reduced_states: dict[str, Any] = {}
    for w in sorted(request.circuit.wires, key=lambda x: x.index):
        reduced_states[w.id] = get_reduced_state_summary(rho, dimensions, w.index)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return SimulationResult(
        circuit_id=request.circuit.id,
        dimension=request.circuit.dimension,
        n_qudits=len(request.circuit.wires),
        total_dim=total_dim,
        basis_labels=basis_labels,
        populations=populations,
        coherences=coherences,
        probabilities=probabilities_dict,
        samples=samples,
        state_validation=state_val,
        density_matrix=full_density_matrix,
        density_matrix_truncated=truncated,
        reduced_states=reduced_states,
        execution_time_ms=round(elapsed_ms, 2),
        memory_estimate_bytes=resource.raw_density_matrix_bytes,
        noisy=bool(request.noise and request.noise.is_active()),
        warnings=validation.warnings + state_val.diagnostics,
    )


def slice_density_matrix(request: MatrixSliceRequest) -> MatrixSliceResponse:
    """Extracts a paginated 2D sub-matrix slice of a large density matrix without sending the full array."""
    sim_req = SimulationRequest(
        circuit=request.circuit,
        noise=request.noise,
        shots=None,
        calculate_entropy=False,
        density_matrix_max_dim=0,
    )

    cirq_circuit, qubit_order, init_idx, dimensions = build_cirq_circuit(
        sim_req.circuit,
        noise_config=sim_req.noise,
    )
    simulator = cirq.DensityMatrixSimulator(dtype=np.complex128)
    sim_result = simulator.simulate(cirq_circuit, qubit_order=qubit_order, initial_state=init_idx)
    rho = sim_result.final_density_matrix

    total_dim = math.prod(dimensions)
    basis_labels = generate_basis_labels(dimensions)

    r_start = max(0, min(request.row_start, total_dim - 1))
    r_end = min(r_start + request.row_count, total_dim)
    c_start = max(0, min(request.col_start, total_dim - 1))
    c_end = min(c_start + request.col_count, total_dim)

    sub_mat = rho[r_start:r_end, c_start:c_end]
    elements = matrix_to_complex_grid(sub_mat)

    return MatrixSliceResponse(
        total_dim=total_dim,
        row_start=r_start,
        row_count=r_end - r_start,
        col_start=c_start,
        col_count=c_end - c_start,
        basis_rows=basis_labels[r_start:r_end],
        basis_cols=basis_labels[c_start:c_end],
        elements=elements,
    )
