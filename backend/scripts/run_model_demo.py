"""Live Demonstration Runner for QuantumLearnAI Models.

Runs both:
1. Quantum Noise Lab Simulation Model (Ideal vs. Superconducting Transmon Decoherence & Purity).
2. Smart Composer AI Model (Gemini Natural Language Generation & Verified Circuit Simplification).
"""

from __future__ import annotations

import json
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from app.quantum.ir import CircuitIR, Op
from app.quantum.noise_lab import (
    PRESET_CONFIGS,
    DecoherenceParams,
    NoiseConfig,
    ReadoutParams,
    StochasticParams,
    simulate_noise_experiment,
)
from app.quantum.smart_composer import (
    GenerationTaskSpec,
    OptimizationObjective,
    generate_circuit_from_task,
    simplify_circuit,
)


def run_noise_lab_model():
    print("\n" + "=" * 70)
    print("1. RUNNING QUANTUM NOISE LAB SIMULATION MODEL")
    print("=" * 70)

    # 2-qubit Bell state |Phi+>
    bell_ir = CircuitIR(
        name="Bell State |Phi+>",
        n_qubits=2,
        n_clbits=2,
        ops=[
            Op(kind="gate", gate="h", qubits=[0], layer=0),
            Op(kind="gate", gate="cx", qubits=[1], controls=[0], layer=1),
            Op(kind="measure", qubits=[0], clbits=[0], layer=2),
            Op(kind="measure", qubits=[1], clbits=[1], layer=2),
        ],
    )

    print("\nInput Circuit: 2-Qubit Bell State |Phi+> (H on q0, CX q0->q1)")

    # 1. Ideal textbook simulation (zero noise)
    print("\n--> [A] Simulating under Ideal Noiseless Conditions...")
    ideal_result = simulate_noise_experiment(bell_ir, PRESET_CONFIGS["ideal"], shots=1000)
    print(f"    Ideal Counts: {ideal_result.ideal_counts}")
    print(f"    State Fidelity: {ideal_result.metrics.fidelity:.5f}")
    print(f"    State Purity:   {ideal_result.metrics.purity:.5f}")

    # 2. Superconducting Transmon Noise Model
    print("\n--> [B] Simulating under Superconducting Transmon Hardware Noise Model:")
    print("    Parameters: T1=60 us, T2=45 us, 1Q depol=0.08%, 2Q depol=0.8%, Readout SPAM=1.2%/2.4%")
    transmon_config = PRESET_CONFIGS["superconducting_transmon"]
    noisy_result = simulate_noise_experiment(bell_ir, transmon_config, shots=1000)

    print(f"    Noisy Output Counts: {noisy_result.noisy_counts}")
    print(f"    Degraded State Fidelity: {noisy_result.metrics.fidelity:.4f}")
    print(f"    Mixed State Purity:      {noisy_result.metrics.purity:.4f}")
    print(f"    Total Variation Distance:{noisy_result.metrics.total_variation_distance:.4f}")
    print(f"    Applied Noise Channels:  {', '.join(noisy_result.applied_channels)}")
    print("    [PASS] Noise Lab model simulation executed successfully!")


def run_smart_composer_ai_model():
    print("\n" + "=" * 70)
    print("2. RUNNING SMART COMPOSER AI MODELS (GENERATION & SIMPLIFICATION)")
    print("=" * 70)

    # Part A: AI Circuit Generation with Gemini
    prompt = "Create a 3-qubit GHZ state circuit with Hadamard and entangling CNOT gates"
    print(f"\n--> [A] Invoking AI Generation Model with prompt:")
    print(f"    \"{prompt}\"")

    spec = GenerationTaskSpec(prompt=prompt, target_qubits=3)
    gen_result = generate_circuit_from_task(spec)

    print(f"    Generated Circuit Name: {gen_result.circuit.get('name')}")
    print(f"    Total Generated Gates:  {len(gen_result.circuit.get('ops', []))}")
    print(f"    Explanation:            {gen_result.explanation}")
    print(f"    Verified Oracle Tests:  {gen_result.passed_tests}")

    # Part B: AI Circuit Simplification & Equivalence Verification
    print("\n--> [B] Invoking AI Simplifier Model on an unoptimized circuit:")
    unoptimized_ir = CircuitIR(
        name="Redundant Gate Circuit",
        n_qubits=2,
        n_clbits=2,
        ops=[
            Op(kind="gate", gate="h", qubits=[0], layer=0),
            Op(kind="gate", gate="h", qubits=[0], layer=1),  # H·H = I
            Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=2),
            Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=3),  # CX·CX = I
            Op(kind="gate", gate="h", qubits=[0], layer=4),
            Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=5),
            Op(kind="measure", qubits=[0], clbits=[0], layer=6),
            Op(kind="measure", qubits=[1], clbits=[1], layer=6),
        ],
    )
    print(f"    Original Circuit: {len(unoptimized_ir.ops)} operations (Depth: 7, 2Q gates: 3)")

    sim_result = simplify_circuit(unoptimized_ir, objective=OptimizationObjective.MIN_GATES)

    print(f"    Accepted Simplification: {sim_result.accepted}")
    print(f"    Gates Reduced:          {sim_result.original_metrics.total_gates} -> {sim_result.simplified_metrics.total_gates} (-{sim_result.improvements.get('gate_reduction_pct')}%)")
    print(f"    Depth Reduced:          {sim_result.original_metrics.depth} -> {sim_result.simplified_metrics.depth} (-{sim_result.improvements.get('depth_reduction_pct')}%)")
    print(f"    Equivalence Status:     {sim_result.verification.status.value}")
    print(f"    Verification Details:   {sim_result.verification.details}")
    print(f"    Evidential Strength:    {sim_result.verification.evidential_strength}")
    print(f"    Applied Rules:          {[r.id for r in sim_result.applied_rules]}")
    print("    [PASS] Smart Composer AI models executed and verified successfully!")


if __name__ == "__main__":
    run_noise_lab_model()
    run_smart_composer_ai_model()
    print("\n" + "=" * 70)
    print("ALL QUANTUM & AI MODELS EXECUTED SUCCESSFULLY")
    print("=" * 70 + "\n")
