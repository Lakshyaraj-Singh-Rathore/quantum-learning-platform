"""Verified educational presets for Qudit Lab (Beta).

All presets execute genuine density-matrix circuits in Google Cirq.
"""

from __future__ import annotations

from typing import Any
from app.quantum.qudit_lab.models import (
    DephasingNoiseConfig,
    DepolarizingNoiseConfig,
    QuditCircuit,
    QuditNoiseConfig,
    QuditOp,
    QuditWire,
)


def get_single_qudit_shift_preset(dimension: int = 3) -> dict[str, Any]:
    """Preset 1: Single-qudit cyclic basis shift X_d."""
    circuit = QuditCircuit(
        id="preset-shift",
        name=f"Cyclic Shift X_{dimension}",
        dimension=dimension,
        wires=[QuditWire(id="q0", index=0, dimension=dimension, initial_state=0)],
        ops=[
            QuditOp(id="op-1", gate="x", targets=[0], controls=[], dimension=dimension),
        ],
    )
    return {
        "id": "preset-shift",
        "title": f"Cyclic Basis Shift (X_{dimension})",
        "category": "Foundations",
        "dimension": dimension,
        "description": f"Applies generalized shift gate X_{dimension} to state |0⟩, demonstrating cyclic level increment |0⟩ → |1⟩.",
        "circuit": circuit.model_dump(),
        "noise": None,
    }


def get_fourier_superposition_preset(dimension: int = 3) -> dict[str, Any]:
    """Preset 2: Generalized Fourier superposition F_d."""
    circuit = QuditCircuit(
        id="preset-fourier",
        name=f"Fourier Superposition F_{dimension}",
        dimension=dimension,
        wires=[QuditWire(id="q0", index=0, dimension=dimension, initial_state=0)],
        ops=[
            QuditOp(id="op-1", gate="f", targets=[0], controls=[], dimension=dimension),
        ],
    )
    return {
        "id": "preset-fourier",
        "title": f"Fourier Superposition (F_{dimension})",
        "category": "Superposition",
        "dimension": dimension,
        "description": f"Applies generalized Fourier transform F_{dimension} to |0⟩, creating an exact equal superposition across all {dimension} levels with uniform probability 1/{dimension}.",
        "circuit": circuit.model_dump(),
        "noise": None,
    }


def get_phase_experiment_preset(dimension: int = 3) -> dict[str, Any]:
    """Preset 3: Phase gate experiment with F_d and Z_d."""
    circuit = QuditCircuit(
        id="preset-phase",
        name=f"Phase Interference (Z_{dimension})",
        dimension=dimension,
        wires=[QuditWire(id="q0", index=0, dimension=dimension, initial_state=0)],
        ops=[
            QuditOp(id="op-1", gate="f", targets=[0], controls=[], dimension=dimension),
            QuditOp(id="op-2", gate="z", targets=[0], controls=[], dimension=dimension),
        ],
    )
    return {
        "id": "preset-phase",
        "title": f"Phase Gate Experiment (Z_{dimension})",
        "category": "Interference",
        "dimension": dimension,
        "description": f"Creates a superposition with F_{dimension}, then applies Z_{dimension} phase factors ω^j = exp(2πi j / {dimension}). Notice the diagonal populations remain equal, while the off-diagonal density matrix coherences rotate in phase!",
        "circuit": circuit.model_dump(),
        "noise": None,
    }


def get_entanglement_preset(dimension: int = 3) -> dict[str, Any]:
    """Preset 4: Two-qudit maximally entangled state |Phi_d> = (1/sqrt(d)) sum |j, j>."""
    circuit = QuditCircuit(
        id="preset-entanglement",
        name=f"Maximally Entangled Qudits |Φ_{dimension}⟩",
        dimension=dimension,
        wires=[
            QuditWire(id="q0", index=0, dimension=dimension, initial_state=0, label="Control"),
            QuditWire(id="q1", index=1, dimension=dimension, initial_state=0, label="Target"),
        ],
        ops=[
            QuditOp(id="op-1", gate="f", targets=[0], controls=[], dimension=dimension),
            QuditOp(id="op-2", gate="sum", targets=[1], controls=[0], dimension=dimension),
        ],
    )
    return {
        "id": "preset-entanglement",
        "title": f"Two-Qudit Bell State (|Φ_{dimension}⟩)",
        "category": "Entanglement",
        "dimension": dimension,
        "description": f"Prepares the canonical maximally entangled generalized Bell state |Φ_{dimension}⟩ = (1/√{dimension}) ∑ |j, j⟩. The combined density matrix is pure (purity γ = 1), while each individual qudit subsystem is maximally mixed (purity γ = 1/{dimension}).",
        "circuit": circuit.model_dump(),
        "noise": None,
    }


def get_noise_mixedness_preset(dimension: int = 3) -> dict[str, Any]:
    """Preset 5: Decoherence & mixedness under generalized depolarizing channel."""
    circuit = QuditCircuit(
        id="preset-noise",
        name=f"Decoherence & Mixed States ({dimension}-level)",
        dimension=dimension,
        wires=[QuditWire(id="q0", index=0, dimension=dimension, initial_state=0)],
        ops=[
            QuditOp(id="op-1", gate="f", targets=[0], controls=[], dimension=dimension),
        ],
    )
    noise = QuditNoiseConfig(
        depolarizing=DepolarizingNoiseConfig(enabled=True, p=0.35),
        dephasing=DephasingNoiseConfig(enabled=True, gamma=0.25),
    )
    return {
        "id": "preset-noise",
        "title": f"Noise & Mixed States ({dimension}-level)",
        "category": "Open Systems",
        "dimension": dimension,
        "description": f"Applies generalized depolarizing (p=0.35) and dephasing (γ=0.25) channels to a Fourier superposition. Observe the suppression of off-diagonal coherence and the drop in state purity γ < 1.",
        "circuit": circuit.model_dump(),
        "noise": noise.model_dump(),
    }


def get_level_phase_preset(dimension: int = 3) -> dict[str, Any]:
    """Preset 6: Level-selective phase P_j(θ)."""
    target_j = 1
    circuit = QuditCircuit(
        id="preset-level-phase",
        name=f"Level Phase P_{target_j}(π/2)",
        dimension=dimension,
        wires=[QuditWire(id="q0", index=0, dimension=dimension, initial_state=0)],
        ops=[
            QuditOp(id="op-1", gate="f", targets=[0], controls=[], dimension=dimension),
            QuditOp(id="op-2", gate="p_j", targets=[0], controls=[], params={"j": target_j, "theta": 1.570796}, dimension=dimension),
        ],
    )
    return {
        "id": "preset-level-phase",
        "title": f"Level-Selective Phase P_{target_j}(θ)",
        "category": "Phase",
        "dimension": dimension,
        "description": f"Prepares a Fourier superposition across all {dimension} levels, then selectively shifts the complex phase of basis level |{target_j}⟩ by θ = π/2 without altering populations or other basis levels.",
        "circuit": circuit.model_dump(),
        "noise": None,
    }


def get_pairwise_rotation_preset(dimension: int = 3) -> dict[str, Any]:
    """Preset 7: Pairwise Givens rotation R_jk(θ, φ)."""
    j, k = 0, 1
    circuit = QuditCircuit(
        id="preset-pairwise-rotation",
        name=f"Pairwise Rotation R_{j}{k}(π/2)",
        dimension=dimension,
        wires=[QuditWire(id="q0", index=0, dimension=dimension, initial_state=0)],
        ops=[
            QuditOp(id="op-1", gate="r_jk", targets=[0], controls=[], params={"j": j, "k": k, "theta": 1.570796, "phi": 0.0}, dimension=dimension),
        ],
    )
    return {
        "id": "preset-pairwise-rotation",
        "title": f"Pairwise Givens Rotation R_{j}{k}(θ, φ)",
        "category": "Rotations",
        "dimension": dimension,
        "description": f"Applies a continuous SU(2) sub-block Givens rotation between levels |{j}⟩ and |{k}⟩ with angle θ = π/2 and relative phase φ = 0, leaving all other qudit levels untouched.",
        "circuit": circuit.model_dump(),
        "noise": None,
    }


def get_swap_preset(dimension: int = 3) -> dict[str, Any]:
    """Preset 8: Qudit SWAP_d operation."""
    circuit = QuditCircuit(
        id="preset-swap",
        name=f"Qudit SWAP_{dimension}",
        dimension=dimension,
        wires=[
            QuditWire(id="q0", index=0, dimension=dimension, initial_state=1, label="q0 (|1⟩)"),
            QuditWire(id="q1", index=1, dimension=dimension, initial_state=0, label="q1 (|0⟩)"),
        ],
        ops=[
            QuditOp(id="op-1", gate="swap", targets=[0, 1], controls=[], dimension=dimension),
        ],
    )
    return {
        "id": "preset-swap",
        "title": f"Two-Qudit SWAP (SWAP_{dimension})",
        "category": "Two-Qudit",
        "dimension": dimension,
        "description": f"Exchanges states |a, b⟩ → |b, a⟩ between two {dimension}-level qudits. In this demonstration, wire q0 begins in state |1⟩ and wire q1 begins in |0⟩; SWAP exchanges them into |0, 1⟩.",
        "circuit": circuit.model_dump(),
        "noise": None,
    }


def get_csx_preset(dimension: int = 3) -> dict[str, Any]:
    """Preset 9: Controlled Modular Shift CSX_d(c, a)."""
    circuit = QuditCircuit(
        id="preset-csx",
        name=f"Controlled Shift CSX_{dimension}",
        dimension=dimension,
        wires=[
            QuditWire(id="q0", index=0, dimension=dimension, initial_state=1, label="Control (|1⟩)"),
            QuditWire(id="q1", index=1, dimension=dimension, initial_state=0, label="Target (|0⟩)"),
        ],
        ops=[
            QuditOp(id="op-1", gate="csx", targets=[1], controls=[0], params={"c": 1, "a": 1}, dimension=dimension),
        ],
    )
    return {
        "id": "preset-csx",
        "title": f"Controlled Modular Shift (CSX_{dimension})",
        "category": "Two-Qudit",
        "dimension": dimension,
        "description": f"Applies modular shift |x, y⟩ → |x, (y + a) mod {dimension}⟩ if and only if the control qudit is in activated level c = 1.",
        "circuit": circuit.model_dump(),
        "noise": None,
    }


def get_all_qudit_presets(dimension: int = 3) -> list[dict[str, Any]]:
    """Returns the complete set of educational presets configured for dimension d."""
    dim = max(2, min(5, dimension))
    return [
        get_single_qudit_shift_preset(dim),
        get_fourier_superposition_preset(dim),
        get_phase_experiment_preset(dim),
        get_level_phase_preset(dim),
        get_pairwise_rotation_preset(dim),
        get_entanglement_preset(dim),
        get_swap_preset(dim),
        get_csx_preset(dim),
        get_noise_mixedness_preset(dim),
    ]
