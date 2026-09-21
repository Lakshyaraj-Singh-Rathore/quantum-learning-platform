"""Quantum Games level definitions.

A level is an ordinary :class:`CodingChallenge` with ``game_meta`` populated,
so levels flow through the existing submit -> job -> autograde pipeline with no
parallel schema. ``game_meta.grader`` selects an extra grading mode in
:mod:`app.services.game_graders`; levels without one are graded exactly like
any other challenge.
"""

from __future__ import annotations

from typing import Any

S2 = 0.7071067811865476


def _state(pairs: dict[int, complex], n: int) -> list[list[float]]:
    """Dense [[re, im], ...] statevector from a sparse {index: amplitude} map."""
    vec = [[0.0, 0.0] for _ in range(2**n)]
    for index, amp in pairs.items():
        vec[index] = [float(amp.real), float(amp.imag)]
    return vec


#: Bell Builder. Four levels, one per Bell state. The two that differ only by a
#: relative phase are graded on fidelity, because their histograms are
#: identical -- which is exactly the lesson.
BELL_LEVELS: list[dict[str, Any]] = [
    {
        "slug": "game-bell-phi-plus",
        "title": "Bell Builder 1: |Φ+⟩",
        "prompt": (
            "Build the Bell state (|00⟩ + |11⟩)/√2.\n\n"
            "Put qubit 0 into superposition, then entangle it with qubit 1. "
            "Measuring should give only 00 and 11, each about half the time."
        ),
        "allowed_gates": ["h", "x", "cx"],
        "target": {"type": "state", "statevector": _state({0: S2 + 0j, 3: S2 + 0j}, 2), "tolerance": 0.05},
        "constraints": {"max_qubits": 2, "max_depth": 4, "required_gates": ["h"]},
        "tags": ["entanglement", "bell-states", "superposition"],
        "game_meta": {"game_id": "bell_builder", "level": 1, "efficiency": 0.15, "par_gates": 2},
    },
    {
        "slug": "game-bell-phi-minus",
        "title": "Bell Builder 2: |Φ−⟩",
        "prompt": (
            "Build (|00⟩ − |11⟩)/√2.\n\n"
            "The histogram is identical to level 1: still only 00 and 11. The "
            "difference is a relative phase, so this level is graded on state "
            "fidelity. A Z somewhere will do it."
        ),
        "allowed_gates": ["h", "x", "z", "cx"],
        "target": {"type": "state", "statevector": _state({0: S2 + 0j, 3: -S2 + 0j}, 2), "tolerance": 0.05},
        "constraints": {"max_qubits": 2, "max_depth": 5, "required_gates": ["h"]},
        "tags": ["entanglement", "bell-states", "phase"],
        "game_meta": {"game_id": "bell_builder", "level": 2, "efficiency": 0.15, "par_gates": 3},
    },
    {
        "slug": "game-bell-psi-plus",
        "title": "Bell Builder 3: |Ψ+⟩",
        "prompt": (
            "Build (|01⟩ + |10⟩)/√2.\n\n"
            "This time the qubits always disagree. Start from level 1 and flip "
            "one of them."
        ),
        "allowed_gates": ["h", "x", "cx"],
        "target": {"type": "state", "statevector": _state({1: S2 + 0j, 2: S2 + 0j}, 2), "tolerance": 0.05},
        "constraints": {"max_qubits": 2, "max_depth": 5, "required_gates": ["h", "x"]},
        "tags": ["entanglement", "bell-states"],
        "game_meta": {"game_id": "bell_builder", "level": 3, "efficiency": 0.15, "par_gates": 3},
    },
    {
        "slug": "game-bell-psi-minus",
        "title": "Bell Builder 4: |Ψ−⟩",
        "prompt": (
            "Build (|01⟩ − |10⟩)/√2, the singlet state.\n\n"
            "Anti-correlated like level 3, with a relative phase like level 2. "
            "Graded on fidelity."
        ),
        "allowed_gates": ["h", "x", "z", "cx"],
        "target": {"type": "state", "statevector": _state({1: S2 + 0j, 2: -S2 + 0j}, 2), "tolerance": 0.05},
        "constraints": {"max_qubits": 2, "max_depth": 6, "required_gates": ["h", "x"]},
        "tags": ["entanglement", "bell-states", "phase"],
        "game_meta": {"game_id": "bell_builder", "level": 4, "efficiency": 0.15, "par_gates": 4},
    },
]


#: Multi-Control Challenge. Graded on the full truth table, so a circuit that
#: happens to produce the right histogram for one input still fails.
MULTI_CONTROL_LEVELS: list[dict[str, Any]] = [
    {
        "slug": "game-vault-1",
        "title": "Open the Vault 1: one control",
        "prompt": (
            "Flip the target qubit (q1) exactly when the control qubit (q0) is 1, "
            "and leave the control unchanged.\n\n"
            "Every one of the 4 basis inputs is checked, so this must work as "
            "logic, not just for one case."
        ),
        "allowed_gates": ["x", "cx"],
        "target": {"type": "counts", "counts": {}},
        "constraints": {"max_qubits": 2, "max_depth": 3},
        "tags": ["multi-control", "cnot", "logic"],
        "game_meta": {
            "game_id": "multi_control", "level": 1,
            "grader": "truth_table", "n_controls": 1,
        },
    },
    {
        "slug": "game-vault-2",
        "title": "Open the Vault 2: two controls (Toffoli)",
        "prompt": (
            "Flip q2 only when BOTH q0 and q1 are 1. All 8 basis inputs are "
            "checked.\n\n"
            "This is the quantum AND gate. A single CNOT will not pass."
        ),
        "allowed_gates": ["x", "cx", "ccx", "mcx"],
        "target": {"type": "counts", "counts": {}},
        "constraints": {"max_qubits": 3, "max_depth": 4},
        "tags": ["multi-control", "toffoli", "logic"],
        "game_meta": {
            "game_id": "multi_control", "level": 2,
            "grader": "truth_table", "n_controls": 2,
        },
    },
    {
        "slug": "game-vault-3",
        "title": "Open the Vault 3: three controls (MCX)",
        "prompt": (
            "Flip q3 only when q0, q1 and q2 are all 1. All 16 basis inputs are "
            "checked.\n\n"
            "Drop the gate on the target, then click each control in the same "
            "column."
        ),
        "allowed_gates": ["x", "cx", "ccx", "mcx"],
        "target": {"type": "counts", "counts": {}},
        "constraints": {"max_qubits": 4, "max_depth": 5},
        "tags": ["multi-control", "mcx", "logic"],
        "game_meta": {
            "game_id": "multi_control", "level": 3,
            "grader": "truth_table", "n_controls": 3,
        },
    },
]


#: Find the Bug. Each level ships a broken circuit; the learner repairs it
#: within an edit budget.
_BROKEN_BELL = {
    "name": "broken-bell",
    "n_qubits": 2,
    "n_clbits": 2,
    "ops": [
        # Bug: X instead of H, so there is no superposition to entangle.
        {"kind": "gate", "gate": "x", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
    ],
}

_BROKEN_PHASE = {
    "name": "broken-phase",
    "n_qubits": 1,
    "n_clbits": 1,
    "ops": [
        # Bug: the second H is missing, so the phase never turns into a
        # measurable difference and the histogram looks 50/50 either way.
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "z", "qubits": [0], "layer": 1},
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
    ],
}

FIND_BUG_LEVELS: list[dict[str, Any]] = [
    {
        "slug": "game-bug-bell",
        "title": "Find the Bug 1: the Bell pair that never entangles",
        "prompt": (
            "This circuit is supposed to produce (|00⟩ + |11⟩)/√2, but it always "
            "gives 11.\n\n"
            "Load the starter circuit, find the single wrong gate, and fix it. "
            "Budget: 1 edit."
        ),
        "allowed_gates": ["h", "x", "z", "cx"],
        "target": {"type": "state", "statevector": _state({0: S2 + 0j, 3: S2 + 0j}, 2), "tolerance": 0.05},
        "constraints": {"max_qubits": 2, "max_depth": 4},
        "tags": ["debugging", "entanglement", "bell-states"],
        "game_meta": {
            "game_id": "find_bug", "level": 1,
            "grader": "find_bug", "starter_ir": _BROKEN_BELL, "max_edits": 1,
        },
    },
    {
        "slug": "game-bug-phase",
        "title": "Find the Bug 2: the phase that does nothing",
        "prompt": (
            "This circuit should always measure 1, but it gives a 50/50 split.\n\n"
            "The Z gate is correct. Something after it is missing: a phase is "
            "invisible until you interfere it back. Budget: 1 edit."
        ),
        "allowed_gates": ["h", "x", "z", "s", "t"],
        "target": {"type": "counts", "counts": {"1": 1.0}, "tolerance": 0.1},
        "constraints": {"max_qubits": 1, "max_depth": 5},
        "tags": ["debugging", "phase", "interference"],
        "game_meta": {
            "game_id": "find_bug", "level": 2,
            "grader": "find_bug", "starter_ir": _BROKEN_PHASE, "max_edits": 1,
        },
    },
]


#: Shot Detective. One high-shot run is subsampled to show the whole
#: convergence curve, so a level costs a single simulation.
SHOT_DETECTIVE_LEVELS: list[dict[str, Any]] = [
    {
        "slug": "game-shots-bell",
        "title": "Shot Detective 1: how many shots for a Bell pair?",
        "prompt": (
            "Build a Bell pair, then find the SMALLEST shot count whose "
            "histogram lands within 0.05 of the true 50/50 distribution.\n\n"
            "Fewer shots scores higher, but miss the tolerance and you score "
            "nothing. Run, read the convergence curve, then try again lower."
        ),
        "allowed_gates": ["h", "x", "cx"],
        "target": {"type": "counts", "counts": {"00": 0.5, "11": 0.5}, "tolerance": 0.05},
        "constraints": {"max_qubits": 2, "max_depth": 4, "required_gates": ["h"]},
        "tags": ["sampling", "statistics", "measurement"],
        "game_meta": {
            "game_id": "shot_detective", "level": 1,
            "grader": "shot_detective",
            "ideal": {"00": 0.5, "11": 0.5},
            "epsilon": 0.05,
        },
    },
]


GAME_LEVELS: list[dict[str, Any]] = (
    BELL_LEVELS + MULTI_CONTROL_LEVELS + FIND_BUG_LEVELS + SHOT_DETECTIVE_LEVELS
)

GAMES: dict[str, dict[str, Any]] = {
    "bell_builder": {
        "title": "Bell Builder",
        "blurb": "Build all four Bell states and learn why phase is invisible on a histogram.",
        "icon": "🔗",
        "concepts": ["entanglement", "phase", "superposition"],
    },
    "multi_control": {
        "title": "Open the Vault",
        "blurb": "Multi-controlled gates, graded over the full truth table.",
        "icon": "🔐",
        "concepts": ["cnot", "toffoli", "mcx"],
    },
    "find_bug": {
        "title": "Find the Bug",
        "blurb": "Repair a broken circuit in as few edits as possible.",
        "icon": "🐛",
        "concepts": ["debugging", "phase", "interference"],
    },
    "shot_detective": {
        "title": "Shot Detective",
        "blurb": "Discover how many shots a distribution actually needs.",
        "icon": "🎲",
        "concepts": ["sampling", "statistics"],
    },
}


__all__ = ["GAME_LEVELS", "GAMES", "BELL_LEVELS", "MULTI_CONTROL_LEVELS",
           "FIND_BUG_LEVELS", "SHOT_DETECTIVE_LEVELS"]
