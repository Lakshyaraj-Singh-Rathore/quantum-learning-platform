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


def get_all_qudit_presets(dimension: int = 3) -> list[dict[str, Any]]:
    """Returns the complete set of educational presets configured for dimension d."""
    dim = max(2, min(5, dimension))
    return [
        get_single_qudit_shift_preset(dim),
        get_fourier_superposition_preset(dim),
        get_phase_experiment_preset(dim),
        get_entanglement_preset(dim),
        get_noise_mixedness_preset(dim),
    ]
