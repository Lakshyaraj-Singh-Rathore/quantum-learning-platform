"""Curated Library of Verified Quantum Circuit Simplification Rules."""

from __future__ import annotations

from app.quantum.smart_composer.models import TransformationRule

TRANSFORMATION_RULES: list[TransformationRule] = [
    TransformationRule(
        id="R01_INV_CANCEL",
        name="Adjacent Inverse Cancellation",
        category="cancellation",
        mathematical_formula="U · U† = I  (e.g., H·H = I, X·X = I, CX·CX = I)",
        description="Consecutive operations that are self-inverse or mutually inverse act as identity and are completely eliminated.",
        preconditions=[
            "Operations act on the exact same target and control qubits.",
            "No intervening non-commuting operations exist between the two gates.",
        ],
        applicable_gates=["h", "x", "y", "z", "s", "sdg", "t", "tdg", "cx", "cz", "swap"],
        verified=True,
    ),
    TransformationRule(
        id="R02_ROT_MERGE",
        name="Parametric Rotation Merging",
        category="consolidation",
        mathematical_formula="R_a(θ₁) · R_a(θ₂) = R_a(θ₁ + θ₂)",
        description="Consecutive rotations about the same spatial axis (X, Y, or Z/Phase) on the same qubit combine into a single rotation by the sum of their angles.",
        preconditions=[
            "Rotations share the identical axis (e.g. both Rx, both Ry, or both Rz/P).",
            "Act on the identical qubit operand.",
            "If θ₁ + θ₂ ≡ 0 (mod 2π), the gate collapses to identity and is removed.",
        ],
        applicable_gates=["rx", "ry", "rz", "p"],
        verified=True,
    ),
    TransformationRule(
        id="R03_PAULI_PUSH",
        name="Commutation & Pauli Push",
        category="commutation",
        mathematical_formula="[R_z(θ), CX_{ctrl}] = 0,  [R_x(θ), CX_{targ}] = 0",
        description="Commutes single-qubit gates past two-qubit entanglers when their operators share an eigenbasis, enabling downstream cancellation.",
        preconditions=[
            "Z-basis rotations (Z, S, T, Rz, P) commute past CNOT controls.",
            "X-basis rotations (X, Rx) commute past CNOT targets.",
            "Target and control roles must not be swapped.",
        ],
        applicable_gates=["z", "s", "t", "rz", "p", "x", "rx", "cx"],
        verified=True,
    ),
    TransformationRule(
        id="R04_HADAMARD_CONJ",
        name="Hadamard Basis Conjugation",
        category="synthesis",
        mathematical_formula="H · X · H = Z,  H · Z · H = X,  (H⊗H) · CX(c,t) · (H⊗H) = CX(t,c)",
        description="Converts between X and Z bases through Hadamard conjugation, including the reversed CNOT identity.",
        preconditions=[
            "Hadamard gates surround the target gate symmetrically.",
            "Reversed CNOT requires Hadamards on both control and target wires.",
        ],
        applicable_gates=["h", "x", "z", "cx"],
        verified=True,
    ),
    TransformationRule(
        id="R05_SWAP_SYNTH",
        name="SWAP Resynthesis / Elimination",
        category="synthesis",
        mathematical_formula="SWAP(a,b) = CX(a,b) · CX(b,a) · CX(a,b)",
        description="Rewrites SWAP operations into canonical 3-CNOT cascades or absorbs virtual wire permutations.",
        preconditions=[
            "Qubits a and b are distinct.",
            "Opposing CNOT orientations alternate correctly.",
        ],
        applicable_gates=["swap", "cx"],
        verified=True,
    ),
    TransformationRule(
        id="R06_PHASE_CONSOL",
        name="Clifford Phase Consolidation",
        category="consolidation",
        mathematical_formula="T · T = S,  S · S = Z,  T⁴ = Z",
        description="Fuses multiple non-Clifford T gates into standard Clifford S and Z operations.",
        preconditions=[
            "Adjacent phase gates on the same qubit wire.",
        ],
        applicable_gates=["t", "s", "z", "tdg", "sdg"],
        verified=True,
    ),
    TransformationRule(
        id="R07_REDUNDANT_GATE",
        name="Trivial Identity Elimination",
        category="cancellation",
        mathematical_formula="R(0) = I,  P(0) = I,  ID = I",
        description="Eliminates zero-angle rotations, explicit Identity gates, and no-op instructions.",
        preconditions=[
            "Rotation angle parameter evaluates to 0.0 mod 2π within 1e-9 tolerance.",
        ],
        applicable_gates=["id", "rx", "ry", "rz", "p"],
        verified=True,
    ),
    TransformationRule(
        id="R08_TWO_QUBIT_CANCEL",
        name="Two-Qubit CNOT Cancellation Across Commutation",
        category="cancellation",
        mathematical_formula="CX(c,t) · [commuting ops] · CX(c,t) = [commuting ops]",
        description="Cancels separated identical CNOT gates when all intervening operations commute with both control and target.",
        preconditions=[
            "Identical control and target assignments.",
            "All intermediate operations on wire c commute with Z.",
            "All intermediate operations on wire t commute with X.",
        ],
        applicable_gates=["cx", "cz", "rz", "rx"],
        verified=True,
    ),
]

RULE_REGISTRY: dict[str, TransformationRule] = {r.id: r for r in TRANSFORMATION_RULES}


def get_rule_by_id(rule_id: str) -> TransformationRule | None:
    return RULE_REGISTRY.get(rule_id)
