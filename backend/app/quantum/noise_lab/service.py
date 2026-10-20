"""Simulation execution service for Quantum Noise Lab experiments."""

from __future__ import annotations

import copy
from typing import Any
import numpy as np

from qiskit import transpile
from qiskit.quantum_info import Statevector

from app.quantum.backends.base import guard_static_size
from app.quantum.ir import CircuitIR
from app.quantum.noise_lab.factory import build_noise_model
from app.quantum.noise_lab.metrics import calculate_metrics
from app.quantum.noise_lab.models import (
    NoiseConfig,
    NoiseMetrics,
    NoiseSimulationResult,
    SimulationMethod,
)
from app.quantum.normalize import strip_measurements, to_qiskit


def _probs_from_counts(counts: dict[str, int], total_shots: int) -> dict[str, float]:
    total = total_shots or sum(counts.values()) or 1
    return {k: round(v / total, 6) for k, v in sorted(counts.items())}


def simulate_noise_experiment(
    ir: CircuitIR,
    config: NoiseConfig,
    shots: int = 1024,
    seed: int | None = 42,
) -> NoiseSimulationResult:
    """Execute both ideal and noisy simulation with exact quantum metric extraction."""
    from qiskit_aer import AerSimulator

    guard_static_size(ir, backend="qiskit_aer")
    n_qubits = ir.n_qubits
    warnings: list[str] = []

    # 1. Prepare Ideal Statevector Reference
    pure_circ = strip_measurements(to_qiskit(ir, include_measurements=False))
    ideal_sv = None
    try:
        ideal_sv = Statevector.from_instruction(pure_circ).data
    except Exception as exc:
        warnings.append(f"Ideal statevector could not be computed analytically: {exc}")

    # 2. Build Noise Model
    noise_model = None
    applied_channels: list[str] = []
    if config.is_active():
        noise_model, notes = build_noise_model(config, n_qubits=n_qubits)
        warnings.extend(notes)
        applied_channels = [n for n in notes if "applied:" in n.lower() or "active" in n.lower()]

    # 3. Transpile Circuit with Measurements
    measure_circ = to_qiskit(ir, include_measurements=True)
    if not ir.has_measurements():
        for q in range(min(measure_circ.num_qubits, measure_circ.num_clbits)):
            measure_circ.measure(q, q)
        warnings.append("No explicit measurements found; measured all qubits automatically.")

    # 4. Ideal Simulation Execution
    ideal_sim = AerSimulator()
    compiled_ideal = transpile(measure_circ, ideal_sim)
    ideal_job = ideal_sim.run(compiled_ideal, shots=shots, seed_simulator=seed)
    raw_ideal_counts = ideal_job.result().get_counts()
    ideal_counts = {
        k.replace(" ", "").zfill(measure_circ.num_clbits): int(v)
        for k, v in raw_ideal_counts.items()
    }
    ideal_probs = _probs_from_counts(ideal_counts, shots)

    # 5. Noisy Simulation Execution
    noisy_sim_method = "density_matrix" if (n_qubits <= 10 and config.simulation_method != SimulationMethod.STABILIZER) else "automatic"
    if config.simulation_method == SimulationMethod.STABILIZER:
        noisy_sim_method = "stabilizer"

    noisy_sim = AerSimulator(noise_model=noise_model, method=noisy_sim_method) if noise_model else AerSimulator()
    compiled_noisy = transpile(measure_circ, noisy_sim)
    noisy_job = noisy_sim.run(compiled_noisy, shots=shots, seed_simulator=seed)
    raw_noisy_counts = noisy_job.result().get_counts()
    noisy_counts = {
        k.replace(" ", "").zfill(measure_circ.num_clbits): int(v)
        for k, v in raw_noisy_counts.items()
    }
    noisy_probs = _probs_from_counts(noisy_counts, shots)

    # 6. Extract Density Matrix for Analytical Metrics (when n_qubits <= 8)
    noisy_rho: np.ndarray | None = None
    if n_qubits <= 8 and noisy_sim_method == "density_matrix":
        try:
            from qiskit_aer import AerSimulator
            density_circ = strip_measurements(to_qiskit(ir, include_measurements=False))
            density_circ.save_density_matrix()
            rho_sim = AerSimulator(noise_model=noise_model, method="density_matrix")
            rho_compiled = transpile(density_circ, rho_sim)
            rho_job = rho_sim.run(rho_compiled, shots=1, seed_simulator=seed)
            noisy_rho = rho_job.result().data()["density_matrix"].data
        except Exception as dm_err:
            warnings.append(f"Density matrix computation skipped: {dm_err}")

    # 7. Calculate Scientific Quantum Metrics
    metrics = calculate_metrics(
        ideal_statevector=ideal_sv,
        noisy_density_matrix=noisy_rho,
        ideal_probs=ideal_probs,
        noisy_probs=noisy_probs,
    )

    # 8. Sample Density Matrix Representation (for visualizer)
    dm_sample = None
    if noisy_rho is not None:
        dim = min(4, noisy_rho.shape[0])
        dm_sample = []
        for i in range(dim):
            row = []
            for j in range(dim):
                val = noisy_rho[i, j]
                row.append({"real": round(float(np.real(val)), 4), "imag": round(float(np.imag(val)), 4)})
            dm_sample.append(row)

    return NoiseSimulationResult(
        circuit_name=ir.name or "Quantum Circuit",
        n_qubits=n_qubits,
        shots=shots,
        ideal_counts=ideal_counts,
        noisy_counts=noisy_counts,
        ideal_probabilities=ideal_probs,
        noisy_probabilities=noisy_probs,
        metrics=metrics,
        applied_channels=applied_channels,
        warnings=warnings,
        method_used=noisy_sim_method,
        density_matrix_sample=dm_sample,
    )


def run_parameter_sweep(
    ir: CircuitIR,
    base_config: NoiseConfig,
    param_path: str,
    start_val: float,
    end_val: float,
    steps: int = 8,
    shots: int = 512,
) -> list[dict[str, Any]]:
    """Perform a controlled parameter sweep (e.g. fidelity vs T1 or depolarizing rate)."""
    steps = max(2, min(steps, 20))
    values = np.linspace(start_val, end_val, steps).tolist()
    results: list[dict[str, Any]] = []

    for val in values:
        cfg = copy.deepcopy(base_config)
        
        # Inject parameter along the dotted path
        parts = param_path.split(".")
        target: Any = cfg
        for part in parts[:-1]:
            target = getattr(target, part)
        setattr(target, parts[-1], float(val))

        # Ensure the channel is enabled when sweeping it
        if hasattr(target, "enabled"):
            target.enabled = True

        try:
            sim_res = simulate_noise_experiment(ir, cfg, shots=shots, seed=42)
            results.append({
                "value": round(float(val), 5),
                "fidelity": sim_res.metrics.fidelity,
                "purity": sim_res.metrics.purity,
                "tvd": sim_res.metrics.total_variation_distance,
                "trace_distance": sim_res.metrics.trace_distance,
            })
        except Exception as exc:
            results.append({
                "value": round(float(val), 5),
                "error": str(exc)
            })

    return results
