"""Canonical curriculum structure.

This module is the single source of truth for the curriculum hierarchy that
section 3.0 of the roadmap requires:

    section -> topic -> lesson

It is deliberately plain data with no database dependency, so that:

* the Alembic migration can import it to seed and backfill, and
* the application and tests import the same definitions,

without either one reaching into the other.

Two kinds of identifier are in play, and keeping them apart is the whole point
of this module:

``lesson slug``
    Comes from the markdown filename in ``content/``. It is a foreign key into
    quiz attempts, challenge attempts, recommendations and chat history, so it
    must never change. Restructuring moves lessons *between* topics; it does not
    rename them.

``topic slug``
    The new stable curriculum identifier. Mastery, prerequisites and difficulty
    hang off this, not off the lesson slug, so that a lesson can be reordered,
    merged or split without orphaning learner progress.

Ordering within a topic is by ``position`` and is chosen by prerequisite and
conceptual dependency, not by the original filename number.
"""

from __future__ import annotations

#: The ten top-level sections, in the order specified by the roadmap.
SECTIONS: list[dict[str, object]] = [
    {"slug": "mathematical-foundations", "title": "Mathematical Foundations", "position": 1},
    {"slug": "core-quantum-theory", "title": "Core Quantum Theory", "position": 2},
    {"slug": "intro-quantum-computing", "title": "Introduction to Quantum Computing", "position": 3},
    {"slug": "intro-qiskit", "title": "Introduction to Qiskit", "position": 4},
    {"slug": "quantum-algorithms", "title": "Quantum Algorithms", "position": 5},
    {"slug": "advanced-theory-circuits", "title": "Advanced Quantum Theory and Circuits", "position": 6},
    {"slug": "variational-nisq", "title": "Variational and NISQ Algorithms", "position": 7},
    {"slug": "error-correction", "title": "Quantum Error Correction and Fault Tolerance", "position": 8},
    {"slug": "hardware-ecosystem", "title": "Quantum Hardware and Ecosystem", "position": 9},
    {"slug": "communication-simulation", "title": "Quantum Communication and Simulation", "position": 10},
]

DIFFICULTIES = ("beginner", "intermediate", "advanced")

#: ``required`` blocks progression unless a diagnostic clears the learner.
#: ``recommended`` only produces an advisory warning.
PREREQ_KINDS = ("required", "recommended")

#: Every topic that currently has content. Topics with no lessons yet are
#: intentionally absent: adding a topic here before lessons exist would put an
#: empty entry in the learner's navigation, which the roadmap explicitly
#: forbids ("no ... inaccessible modules").
TOPICS: list[dict[str, object]] = [
    # -- 2. Core Quantum Theory ------------------------------------------- #
    {
        "slug": "measurement",
        "title": "Measurement",
        "section": "core-quantum-theory",
        "position": 1,
        "difficulty": "beginner",
        "summary": "How a quantum state becomes a classical outcome, and why the "
                   "Born rule ties probabilities to squared amplitudes.",
        "objectives": [
            "State the measurement postulate",
            "Compute outcome probabilities from amplitudes",
            "Distinguish amplitude from probability",
        ],
        "lessons": ["04_measurement"],
        "prerequisites": [("qubits", "required")],
    },
    {
        "slug": "quantum-noise",
        "title": "Quantum Noise and Decoherence",
        "section": "core-quantum-theory",
        "position": 2,
        "difficulty": "intermediate",
        "summary": "Decoherence, depolarizing and damping channels, T1/T2, readout "
                   "error, and how noise degrades a result as circuits deepen.",
        "objectives": [
            "Describe decoherence, depolarizing, amplitude and phase damping",
            "Relate T1 and T2 to circuit depth limits",
            "Compare ideal and noisy measurement histograms",
        ],
        "lessons": ["09_quantum_noise"],
        "prerequisites": [("measurement", "required")],
    },
    # -- 3. Introduction to Quantum Computing ------------------------------ #
    {
        "slug": "classical-vs-qubit",
        "title": "Classical Bits versus Qubits",
        "section": "intro-quantum-computing",
        "position": 1,
        "difficulty": "beginner",
        "summary": "What a qubit is, how it differs from a bit, and how physical "
                   "implementations realize one.",
        "objectives": [
            "Contrast a classical bit with a qubit",
            "Name physical qubit implementations",
        ],
        "lessons": ["13_classical_bit_vs_qubit"],
        "prerequisites": [],
    },
    {
        "slug": "qubits",
        "title": "Qubits and the Bloch Sphere",
        "section": "intro-quantum-computing",
        "position": 2,
        "difficulty": "beginner",
        "summary": "Basis states, general single-qubit states, normalization and "
                   "the Bloch sphere picture.",
        "objectives": [
            "Write a general single-qubit state",
            "Verify normalization",
            "Locate a state on the Bloch sphere",
        ],
        "lessons": ["01_qubits"],
        "prerequisites": [("classical-vs-qubit", "required")],
    },
    {
        "slug": "quantum-gates",
        "title": "Quantum Gates",
        "section": "intro-quantum-computing",
        "position": 3,
        "difficulty": "beginner",
        "summary": "Pauli, Hadamard, phase and rotation gates, controlled gates, "
                   "unitarity and reversibility.",
        "objectives": [
            "Recall the matrix of the common single-qubit gates",
            "Apply a gate to a state by matrix multiplication",
            "Explain why quantum gates are unitary and reversible",
        ],
        # Concept first, then the hands-on bootcamp. Both lessons are kept: the
        # bootcamp's exercises are the only practice material on this topic.
        "lessons": ["02_gates", "10_gates_bootcamp"],
        "prerequisites": [("qubits", "required")],
    },
    {
        "slug": "bell-states",
        "title": "Bell States",
        "section": "intro-quantum-computing",
        "position": 4,
        "difficulty": "intermediate",
        "summary": "Building the four Bell states with H and CNOT, and the "
                   "correlations their measurements show.",
        "objectives": [
            "Derive each Bell state from a product state",
            "Predict correlated measurement outcomes",
            "Explain why entanglement does not permit faster-than-light signalling",
        ],
        "lessons": ["11_bell_states"],
        "prerequisites": [("quantum-gates", "required")],
    },
    {
        "slug": "entanglement",
        "title": "Entanglement",
        "section": "intro-quantum-computing",
        "position": 5,
        "difficulty": "intermediate",
        "summary": "Entanglement as non-separability, why it cannot be created by "
                   "local operations, and how it is detected.",
        "objectives": [
            "Test a two-qubit state for separability",
            "Explain why local operations cannot create entanglement",
        ],
        # Taught after the concrete Bell-state example rather than eight lessons
        # before it, which was the previous filename-derived order.
        "lessons": ["03_entanglement"],
        "prerequisites": [("bell-states", "required")],
    },
    # -- 5. Quantum Algorithms --------------------------------------------- #
    {
        "slug": "deutsch-jozsa",
        "title": "Deutsch-Jozsa Algorithm",
        "section": "quantum-algorithms",
        "position": 1,
        "difficulty": "intermediate",
        "summary": "The constant-versus-balanced promise, phase kickback, and one "
                   "query where a classical machine needs many.",
        "objectives": [
            "Explain the constant/balanced promise",
            "Trace phase kickback through the oracle",
            "State the algorithm's limitations",
        ],
        "lessons": ["05_deutsch_jozsa"],
        "prerequisites": [("quantum-gates", "required")],
    },
    {
        "slug": "grover",
        "title": "Grover's Search",
        "section": "quantum-algorithms",
        "position": 2,
        "difficulty": "intermediate",
        "summary": "Amplitude amplification, the diffusion operator, the optimal "
                   "iteration count and what happens when you overshoot.",
        "objectives": [
            "Construct an oracle and a diffusion operator",
            "Compute the optimal iteration count",
            "Describe the effect of over-rotating",
        ],
        "lessons": ["06_grover"],
        "prerequisites": [("deutsch-jozsa", "required")],
    },
    # -- 6. Advanced Quantum Theory and Circuits --------------------------- #
    {
        "slug": "control-flow",
        "title": "Classical Control Flow in Circuits",
        "section": "advanced-theory-circuits",
        "position": 1,
        "difficulty": "intermediate",
        "summary": "Conditioning quantum operations on measurement results, and "
                   "the classical register conventions that make it work.",
        "objectives": [
            "Apply an operation conditioned on a measurement result",
            "Account for classical bit ordering",
        ],
        "lessons": ["12_control_flow"],
        "prerequisites": [("quantum-gates", "required"), ("measurement", "required")],
    },
    {
        "slug": "dynamic-circuits",
        "title": "Dynamic Circuits",
        "section": "advanced-theory-circuits",
        "position": 2,
        "difficulty": "advanced",
        "summary": "Mid-circuit measurement with feed-forward, loops and resets, "
                   "and what dynamic circuits cost on real hardware.",
        "objectives": [
            "Build a circuit with mid-circuit measurement and feed-forward",
            "Explain the latency cost of dynamic circuits",
        ],
        "lessons": ["08_dynamic_circuits"],
        "prerequisites": [("control-flow", "required")],
    },
    # -- 7. Variational and NISQ Algorithms -------------------------------- #
    {
        "slug": "vqe-qaoa",
        "title": "VQE and QAOA",
        "section": "variational-nisq",
        "position": 1,
        "difficulty": "advanced",
        "summary": "Parameterized circuits, the classical optimizer loop, and why "
                   "these algorithms are built for noisy devices.",
        "objectives": [
            "Describe the variational loop",
            "Explain why VQE suits NISQ hardware",
        ],
        "lessons": ["07_vqe_qaoa"],
        # Noise first. VQE's entire motivation is device noise, so the previous
        # filename order, which put it before the noise lesson, inverted the
        # dependency.
        "prerequisites": [("quantum-noise", "required"), ("grover", "recommended")],
    },
]

#: Maps a legacy mastery ``tag`` onto the topic it evidences.
#:
#: Mastery rows are written from the *authored* tags on quizzes and coding
#: challenges (see ``services/recommendations.update_mastery_from_quiz``), not
#: from the keyword-inferred tags on lessons. The authored vocabulary is small
#: and unambiguous, so the mapping below is a real one rather than a guess.
#:
#: Tags that map to nothing are left unmapped on purpose. Dropping them would
#: silently discard learner history; leaving ``topic_slug`` NULL keeps the row
#: readable as prior progress without pretending it measures a specific topic.
LEGACY_TAG_TO_TOPIC: dict[str, str] = {
    "qubit": "qubits",
    "gates": "quantum-gates",
    "measurement": "measurement",
    "entanglement": "entanglement",
    "noise": "quantum-noise",
    "decoherence": "quantum-noise",
    "grover": "grover",
    "algorithms": "grover",
    "dynamic": "dynamic-circuits",
}


def lessons_by_topic() -> dict[str, list[str]]:
    """Return ``{topic_slug: [lesson_slug, ...]}`` in authored order."""
    return {str(t["slug"]): list(t["lessons"]) for t in TOPICS}  # type: ignore[arg-type]


def topic_for_lesson(lesson_slug: str) -> str | None:
    """Return the topic slug that owns ``lesson_slug``, or None if unmapped."""
    for topic in TOPICS:
        if lesson_slug in topic["lessons"]:  # type: ignore[operator]
            return str(topic["slug"])
    return None


def all_prerequisites() -> list[tuple[str, str, str]]:
    """Return ``(topic_slug, prerequisite_slug, kind)`` triples."""
    out: list[tuple[str, str, str]] = []
    for topic in TOPICS:
        for prereq, kind in topic["prerequisites"]:  # type: ignore[misc]
            out.append((str(topic["slug"]), str(prereq), str(kind)))
    return out


def validate() -> list[str]:
    """Return a list of structural problems. Empty means the data is coherent.

    Checked by the test suite so that a bad edit cannot reach a migration.
    """
    problems: list[str] = []
    section_slugs = {s["slug"] for s in SECTIONS}
    topic_slugs = {t["slug"] for t in TOPICS}

    for topic in TOPICS:
        slug = str(topic["slug"])
        if topic["section"] not in section_slugs:
            problems.append(f"topic {slug}: unknown section {topic['section']}")
        if topic["difficulty"] not in DIFFICULTIES:
            problems.append(f"topic {slug}: bad difficulty {topic['difficulty']}")
        if not topic["lessons"]:
            problems.append(f"topic {slug}: no lessons")
        for prereq, kind in topic["prerequisites"]:  # type: ignore[misc]
            if prereq not in topic_slugs:
                problems.append(f"topic {slug}: unknown prerequisite {prereq}")
            if prereq == slug:
                problems.append(f"topic {slug}: prereq on itself")
            if kind not in PREREQ_KINDS:
                problems.append(f"topic {slug}: bad prereq kind {kind}")

    seen: dict[str, str] = {}
    for topic in TOPICS:
        for lesson in topic["lessons"]:  # type: ignore[union-attr]
            if lesson in seen:
                problems.append(
                    f"lesson {lesson}: claimed by both {seen[lesson]} and {topic['slug']}"
                )
            seen[str(lesson)] = str(topic["slug"])

    # A cycle would make the dependency graph unresolvable for path generation.
    for slug in _cycle_members({str(t["slug"]): [p for p, _ in t["prerequisites"]]  # type: ignore[misc]
                                for t in TOPICS}):
        problems.append(f"topic {slug}: part of a prerequisite cycle")

    return problems


def _cycle_members(graph: dict[str, list[str]]) -> list[str]:
    """Return topic slugs that lie on a cycle, via iterative DFS."""
    members: list[str] = []
    state: dict[str, int] = {}  # 0 unvisited, 1 on stack, 2 done

    for root in graph:
        if state.get(root, 0) != 0:
            continue
        stack: list[tuple[str, int]] = [(root, 0)]
        path: list[str] = []
        while stack:
            node, step = stack.pop()
            if step == 0:
                if state.get(node, 0) == 1:
                    if node in path:
                        members.extend(path[path.index(node):])
                    continue
                if state.get(node, 0) == 2:
                    continue
                state[node] = 1
                path.append(node)
                stack.append((node, 1))
                for nxt in reversed(graph.get(node, [])):
                    stack.append((nxt, 0))
            else:
                state[node] = 2
                if path and path[-1] == node:
                    path.pop()
    return sorted(set(members))
