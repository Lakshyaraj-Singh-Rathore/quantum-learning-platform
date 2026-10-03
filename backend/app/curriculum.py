"""Canonical curriculum registry.

This module is the single source of truth for the curriculum hierarchy:

    section -> module -> topic -> lesson

It is deliberately plain data with no database dependency, so the migration,
the application and the tests all read the same definitions.

Stable topic identifiers
------------------------
Topic IDs are namespaced, human-readable and permanent:

    <namespace>.<topic>

===========  ====================================  ==========================
Namespace    Curriculum section                    Section letter
===========  ====================================  ==========================
``math.``    Mathematical Foundations               A
``core.``    Core Quantum Theory                    B
``qc.``      Introduction to Quantum Computing      C
``qiskit.``  Introduction to Qiskit                 D
``algo.``    Quantum Algorithms                     E
``adv.``     Advanced Gates and Circuits            F
``nisq.``    Variational and NISQ Algorithms        G
``qec.``     Error Correction and Fault Tolerance   H
``hw.``      Quantum Hardware and Ecosystem         I
``comm.``    Quantum Communication and Simulation   J
===========  ====================================  ==========================

An identifier depends on nothing that can drift: not the lesson filename, not
the title, not the prose, not the position in the curriculum. A lesson may be
renamed, moved, split or merged and its topic IDs do not change.

Two other identifiers are in play and must not be confused with topic IDs:

``lesson slug``
    From the markdown filename in ``content/``. A foreign key into quiz
    attempts, challenge attempts, recommendations and chat history.

``tag``
    Keyword-inferred from lesson prose (``infer_tags``) or hand-authored on
    quizzes and challenges. Tags are search metadata and legacy
    classification only. They never grant topic mastery on their own.
"""

from __future__ import annotations

#: Namespace -> (section slug, section letter, title)
NAMESPACES: dict[str, tuple[str, str, str]] = {
    "math": ("mathematical-foundations", "A", "Mathematical Foundations"),
    "core": ("core-quantum-theory", "B", "Core Quantum Theory"),
    "qc": ("intro-quantum-computing", "C", "Introduction to Quantum Computing"),
    "qiskit": ("intro-qiskit", "D", "Introduction to Qiskit"),
    "algo": ("quantum-algorithms", "E", "Quantum Algorithms"),
    "adv": ("advanced-gates-circuits", "F", "Advanced Gates and Circuits"),
    "nisq": ("variational-nisq", "G", "Variational and NISQ Algorithms"),
    "qec": ("error-correction", "H", "Error Correction and Fault Tolerance"),
    "hw": ("hardware-ecosystem", "I", "Quantum Hardware and Ecosystem"),
    "comm": ("communication-simulation", "J", "Quantum Communication and Simulation"),
}

SECTIONS: list[dict[str, object]] = [
    {"slug": slug, "letter": letter, "title": title, "position": i}
    for i, (ns, (slug, letter, title)) in enumerate(NAMESPACES.items(), start=1)
]

DIFFICULTIES = ("beginner", "intermediate", "advanced")
PREREQ_KINDS = ("required", "recommended")

#: Publication status. Only ``published`` topics appear to learners; anything
#: else is registered but hidden, so a topic under authoring is visible to the
#: registry without putting an unopenable entry in navigation.
PUBLICATION_STATUSES = ("draft", "review", "published", "retired")

#: Confidence in a lesson -> topic mapping. Drives whether legacy mastery may
#: be mapped onto the topic (see MASTERY_MAPPABLE_CONFIDENCE).
CONFIDENCES = ("high", "medium", "low")

#: Only these confidences are strong enough to map *existing* mastery records
#: onto a topic. Lower ones stay legacy-only.
MASTERY_MAPPABLE_CONFIDENCE = ("high",)


# --------------------------------------------------------------------------- #
# Topics
# --------------------------------------------------------------------------- #
# ``lessons`` entries are ``(lesson_slug, confidence, is_primary)``. A lesson
# may carry several topics; exactly one should be primary.
#
# Topics are declared for the whole target curriculum so the registry is
# complete, but ``status`` is ``draft`` unless content exists. Draft topics are
# never shown in navigation -- the roadmap forbids inaccessible modules.

TOPICS: list[dict[str, object]] = [
    # ---- C. Introduction to Quantum Computing ---------------------------- #
    {
        "id": "qc.qubits",
        "title": "Qubits",
        "namespace": "qc",
        "module": "intro-quantum-computing",
        "position": 1,
        "difficulty": "beginner",
        "status": "published",
        "description": (
            "Classical bits versus quantum bits, basis states, the general "
            "single-qubit state, normalization and the Bloch sphere."
        ),
        "objectives": [
            "Contrast a classical bit with a qubit",
            "Write a general single-qubit state and verify normalization",
            "Locate a state on the Bloch sphere",
        ],
        "lessons": [
            ("13_classical_bit_vs_qubit", "high", False),
            ("01_qubits", "high", True),
        ],
        "prerequisites": [],
        "assessments": ["basics"],
        "visualizations": ["bloch", "bit_vs_qubit", "build_a_qubit"],
    },
    {
        "id": "qc.superposition",
        "title": "Superposition",
        "namespace": "qc",
        "module": "intro-quantum-computing",
        "position": 2,
        "difficulty": "beginner",
        "status": "published",
        "description": (
            "Linear combinations of basis states, relative versus global phase, "
            "and why amplitudes are not probabilities."
        ),
        "objectives": [
            "Express a state as a linear combination of basis states",
            "Distinguish relative from global phase",
            "Explain why amplitude differs from probability",
        ],
        "lessons": [("01_qubits", "medium", False)],
        "prerequisites": [("qc.qubits", "required")],
        "assessments": ["basics"],
        "visualizations": ["bloch", "build_a_qubit"],
    },
    {
        "id": "qc.basic_gates",
        "title": "Basic Quantum Gates",
        "namespace": "qc",
        "module": "intro-quantum-computing",
        "position": 3,
        "difficulty": "beginner",
        "status": "published",
        "description": (
            "Pauli, Hadamard, phase and rotation gates, controlled gates, "
            "unitarity and reversibility."
        ),
        "objectives": [
            "Recall the matrix of each common single-qubit gate",
            "Apply a gate to a state by matrix multiplication",
            "Explain why quantum gates are unitary and reversible",
        ],
        "lessons": [
            ("02_gates", "high", True),
            ("10_gates_bootcamp", "high", True),
        ],
        "prerequisites": [("qc.qubits", "required")],
        "assessments": ["basics"],
        "visualizations": ["gates", "circuit_lab", "bloch"],
    },
    {
        "id": "qc.bell_states",
        "title": "Bell States",
        "namespace": "qc",
        "module": "intro-quantum-computing",
        "position": 4,
        "difficulty": "intermediate",
        "status": "published",
        "description": (
            "The four Bell states, how H and CNOT build them, and the "
            "correlations their measurements show."
        ),
        "objectives": [
            "Derive each Bell state from a product state",
            "Predict correlated measurement outcomes",
            "Explain why entanglement does not permit faster-than-light signalling",
        ],
        "lessons": [("11_bell_states", "high", True)],
        "prerequisites": [("qc.basic_gates", "required")],
        "assessments": ["bell-states-quiz"],
        "visualizations": ["plus_minus", "state_space", "circuit_lab"],
    },
    {
        "id": "qc.entanglement",
        "title": "Entanglement",
        "namespace": "qc",
        "module": "intro-quantum-computing",
        "position": 5,
        "difficulty": "intermediate",
        "status": "published",
        "description": (
            "Entanglement as non-separability, why local operations cannot "
            "create it, and how the platform detects it."
        ),
        "objectives": [
            "Test a two-qubit state for separability",
            "Explain why local operations cannot create entanglement",
        ],
        # Taught after the concrete Bell-state example rather than eight
        # lessons before it, which was the filename-derived order.
        "lessons": [
            ("03_entanglement", "high", True),
            ("11_bell_states", "high", False),
        ],
        "prerequisites": [("qc.bell_states", "required")],
        "assessments": ["entanglement-measurement", "bell-states-quiz"],
        "visualizations": ["state_space"],
    },

    # ---- B. Core Quantum Theory ------------------------------------------ #
    {
        "id": "core.measurement_theory",
        "title": "Measurement Theory",
        "namespace": "core",
        "module": "core-quantum-theory",
        "position": 1,
        "difficulty": "beginner",
        "status": "published",
        "description": (
            "The measurement postulate, shots, sampling and the Born rule. "
            "Terminal versus mid-circuit measurement."
        ),
        "objectives": [
            "State the measurement postulate",
            "Compute outcome probabilities from amplitudes",
            "Distinguish terminal from mid-circuit measurement",
        ],
        "lessons": [("04_measurement", "high", True)],
        "prerequisites": [("qc.qubits", "required")],
        "assessments": ["entanglement-measurement"],
        "visualizations": ["measure", "bit_order"],
    },
    {
        "id": "core.quantum_interference",
        "title": "Quantum Interference",
        "namespace": "core",
        "module": "core-quantum-theory",
        "position": 2,
        "difficulty": "intermediate",
        "status": "published",
        "description": (
            "Amplitudes cancelling and reinforcing: phase kickback, the "
            "hidden-coin experiment, and interference as the engine behind "
            "the algorithms."
        ),
        "objectives": [
            "Predict when amplitudes cancel versus reinforce",
            "Explain phase kickback",
        ],
        "lessons": [
            ("13_classical_bit_vs_qubit", "high", False),
            ("05_deutsch_jozsa", "medium", False),
            ("06_grover", "medium", False),
        ],
        "prerequisites": [("core.measurement_theory", "required")],
        "assessments": [],
        "visualizations": ["interference"],
    },
    {
        "id": "core.quantum_channels",
        "title": "Quantum Channels",
        "namespace": "core",
        "module": "core-quantum-theory",
        "position": 3,
        "difficulty": "intermediate",
        "status": "published",
        "description": (
            "Depolarizing, amplitude-damping and phase-damping channels, and "
            "how they act on a state."
        ),
        "objectives": [
            "Describe the standard noise channels",
            "Predict a channel's effect on a Bloch vector",
        ],
        "lessons": [("09_quantum_noise", "high", False)],
        "prerequisites": [("core.measurement_theory", "required")],
        "assessments": ["quantum-noise"],
        "visualizations": [],
    },

    # ---- D. Introduction to Qiskit --------------------------------------- #
    {
        "id": "qiskit.sampler",
        "title": "Sampler",
        "namespace": "qiskit",
        "module": "intro-qiskit",
        "position": 1,
        "difficulty": "beginner",
        "status": "published",
        "description": (
            "Measurement counts, shot noise, statistical convergence and the "
            "limits of finite-shot measurement."
        ),
        "objectives": [
            "Execute a circuit with a chosen shot count",
            "Compare estimated and exact probabilities",
        ],
        "lessons": [("04_measurement", "medium", False)],
        "prerequisites": [("core.measurement_theory", "required")],
        "assessments": [],
        "visualizations": ["measure", "bit_order"],
    },
    {
        "id": "qiskit.quantum_noise",
        "title": "Quantum Noise",
        "namespace": "qiskit",
        "module": "intro-qiskit",
        "position": 2,
        "difficulty": "intermediate",
        "status": "published",
        "description": (
            "Decoherence, T1 and T2, readout error, and how noise degrades a "
            "result as circuits deepen."
        ),
        "objectives": [
            "Relate T1 and T2 to circuit depth limits",
            "Compare ideal and noisy measurement histograms",
        ],
        "lessons": [("09_quantum_noise", "high", True)],
        "prerequisites": [("core.measurement_theory", "required")],
        "assessments": ["quantum-noise"],
        "visualizations": [],
    },

    # ---- E. Quantum Algorithms ------------------------------------------- #
    {
        "id": "algo.deutsch_jozsa",
        "title": "Deutsch-Jozsa Algorithm",
        "namespace": "algo",
        "module": "quantum-algorithms",
        "position": 1,
        "difficulty": "intermediate",
        "status": "published",
        "description": (
            "The constant-versus-balanced promise, phase kickback, and one "
            "query where a classical machine needs many."
        ),
        "objectives": [
            "Explain the constant/balanced promise",
            "Trace phase kickback through the oracle",
            "State the algorithm's limitations",
        ],
        "lessons": [("05_deutsch_jozsa", "high", True)],
        "prerequisites": [("qc.basic_gates", "required")],
        "assessments": [],
        "visualizations": ["interference", "circuit_lab"],
    },
    {
        "id": "algo.grover",
        "title": "Grover's Search",
        "namespace": "algo",
        "module": "quantum-algorithms",
        "position": 2,
        "difficulty": "intermediate",
        "status": "published",
        "description": (
            "Amplitude amplification, the diffusion operator, optimal "
            "iteration count and the effect of over-rotating."
        ),
        "objectives": [
            "Construct an oracle and a diffusion operator",
            "Compute the optimal iteration count",
            "Describe the effect of over-rotating",
        ],
        "lessons": [("06_grover", "high", True)],
        "prerequisites": [("algo.deutsch_jozsa", "required")],
        "assessments": ["grover"],
        "visualizations": ["interference", "circuit_lab"],
    },

    # ---- F. Advanced Gates and Circuits ---------------------------------- #
    {
        "id": "adv.dynamic_circuits",
        "title": "Dynamic Circuits and Classical Control Flow",
        "namespace": "adv",
        "module": "advanced-gates-circuits",
        "position": 1,
        "difficulty": "advanced",
        "status": "published",
        "description": (
            "Mid-circuit measurement with feed-forward, if/for/while/box "
            "constructs, and what dynamic circuits cost on real hardware."
        ),
        "objectives": [
            "Build a circuit with mid-circuit measurement and feed-forward",
            "Explain the latency cost of dynamic circuits",
        ],
        "lessons": [
            ("12_control_flow", "high", True),
            ("08_dynamic_circuits", "high", True),
            ("04_measurement", "medium", False),
        ],
        "prerequisites": [
            ("qc.basic_gates", "required"),
            ("core.measurement_theory", "required"),
        ],
        "assessments": [],
        "visualizations": ["bit_order", "circuit_lab"],
    },
    {
        "id": "adv.quantum_universality",
        "title": "Quantum Universality",
        "namespace": "adv",
        "module": "advanced-gates-circuits",
        "position": 2,
        "difficulty": "advanced",
        "status": "published",
        "description": (
            "Universal gate sets, transpilation onto a native basis, and why "
            "the composer's palette is not the hardware's gate set."
        ),
        "objectives": ["Explain what makes a gate set universal"],
        "lessons": [("02_gates", "medium", False)],
        "prerequisites": [("qc.basic_gates", "required")],
        "assessments": [],
        "visualizations": ["circuit_lab"],
    },

    # ---- G. Variational and NISQ Algorithms ------------------------------ #
    {
        "id": "nisq.vqe",
        "title": "Variational Quantum Eigensolver",
        "namespace": "nisq",
        "module": "variational-nisq",
        "position": 1,
        "difficulty": "advanced",
        "status": "published",
        "description": (
            "The hybrid quantum-classical loop, ansatz choice, and why VQE "
            "suits noisy devices."
        ),
        "objectives": [
            "Describe the variational loop",
            "Explain why VQE suits NISQ hardware",
        ],
        "lessons": [("07_vqe_qaoa", "high", True)],
        # Noise first. VQE's entire motivation is device noise, so the
        # filename order, which put it before the noise lesson, inverted the
        # dependency.
        "prerequisites": [
            ("qiskit.quantum_noise", "required"),
            ("algo.grover", "recommended"),
        ],
        "assessments": [],
        "visualizations": ["circuit_lab"],
    },
    {
        "id": "nisq.qaoa",
        "title": "QAOA and Approximation Ratios",
        "namespace": "nisq",
        "module": "variational-nisq",
        "position": 2,
        "difficulty": "advanced",
        "status": "published",
        "description": (
            "The alternating operator ansatz, approximation ratios and how "
            "QAOA quality varies with depth."
        ),
        "objectives": ["Explain the QAOA ansatz and approximation ratio"],
        "lessons": [("07_vqe_qaoa", "high", False)],
        "prerequisites": [("nisq.vqe", "required")],
        "assessments": [],
        "visualizations": ["circuit_lab"],
    },
    {
        "id": "nisq.parameterized_circuits",
        "title": "Parameterized Circuits and Ansatz Construction",
        "namespace": "nisq",
        "module": "variational-nisq",
        "position": 3,
        "difficulty": "advanced",
        "status": "published",
        "description": (
            "Building parameterized circuits, choosing an ansatz, and the "
            "barren-plateau problem in deep ansatze."
        ),
        "objectives": [
            "Construct a parameterized circuit",
            "Explain what a barren plateau is and when it appears",
        ],
        "lessons": [("07_vqe_qaoa", "medium", False)],
        "prerequisites": [("nisq.vqe", "required")],
        "assessments": [],
        "visualizations": ["circuit_lab"],
    },
]


# --------------------------------------------------------------------------- #
# Legacy tag -> stable topic mapping
# --------------------------------------------------------------------------- #
# Mastery rows are written from the *authored* tags on quizzes and coding
# challenges (services/recommendations.py), not from lesson prose. The authored
# vocabulary is small and coherent, so these mappings are real rather than
# guesses. Each is annotated with the evidence that justifies it.
#
# A tag that maps to nothing is left unmapped on purpose: the row is preserved
# as legacy-only rather than deleted or guessed at.

LEGACY_TAG_TO_TOPIC: dict[str, str] = {
    "qubit": "qc.qubits",
    "gates": "qc.basic_gates",
    "measurement": "core.measurement_theory",
    "entanglement": "qc.entanglement",
    "noise": "qiskit.quantum_noise",
    "decoherence": "qiskit.quantum_noise",
    "grover": "algo.grover",
    "algorithms": "algo.grover",
    "dynamic": "adv.dynamic_circuits",
}

#: Why each legacy mapping is considered safe enough to carry mastery.
LEGACY_MAPPING_EVIDENCE: dict[str, str] = {
    "qubit": "Quiz 'basics' is authored tags ['qubit','gates']; its questions are "
             "on qubit states and measurement probabilities.",
    "gates": "Quiz 'basics' covers gate matrices; challenge tags use 'gates' for "
             "gate-construction tasks.",
    "measurement": "Quiz 'entanglement-measurement' is authored "
                   "['entanglement','measurement'].",
    "entanglement": "Quizzes 'entanglement-measurement' and 'bell-states-quiz'.",
    "noise": "Quiz 'quantum-noise' is authored ['noise','decoherence'].",
    "decoherence": "Same quiz as 'noise'; the two co-occur on every row.",
    "grover": "Quiz 'grover' is authored ['grover','algorithms'].",
    "algorithms": "Co-occurs with 'grover' on the same authored quiz; no other "
                  "algorithms quiz exists yet, so 'algorithms' can only have "
                  "come from Grover.",
    "dynamic": "Challenges on dynamic-circuit construction.",
}


# --------------------------------------------------------------------------- #
# Accessors
# --------------------------------------------------------------------------- #


def topics_for_lesson(lesson_slug: str) -> list[tuple[str, str, bool]]:
    """Return ``[(topic_id, confidence, is_primary), ...]`` for a lesson."""
    out: list[tuple[str, str, bool]] = []
    for topic in TOPICS:
        for slug, confidence, primary in topic["lessons"]:  # type: ignore[misc]
            if slug == lesson_slug:
                out.append((str(topic["id"]), str(confidence), bool(primary)))
    return out


def primary_topic(lesson_slug: str) -> str | None:
    for topic_id, _conf, primary in topics_for_lesson(lesson_slug):
        if primary:
            return topic_id
    mapped = topics_for_lesson(lesson_slug)
    return mapped[0][0] if mapped else None


def lessons_for_topic(topic_id: str) -> list[str]:
    for topic in TOPICS:
        if topic["id"] == topic_id:
            return [str(s) for s, _c, _p in topic["lessons"]]  # type: ignore[misc]
    return []


def published_topics() -> list[dict[str, object]]:
    return [t for t in TOPICS if t.get("status") == "published"]


def all_prerequisites() -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for topic in TOPICS:
        for prereq, kind in topic["prerequisites"]:  # type: ignore[misc]
            out.append((str(topic["id"]), str(prereq), str(kind)))
    return out


def all_lesson_topics() -> list[tuple[str, str, str, bool]]:
    """Return ``(lesson_slug, topic_id, confidence, is_primary)`` rows."""
    out: list[tuple[str, str, str, bool]] = []
    for topic in TOPICS:
        for slug, confidence, primary in topic["lessons"]:  # type: ignore[misc]
            out.append((str(slug), str(topic["id"]), str(confidence), bool(primary)))
    return out


def validate() -> list[str]:
    """Return structural problems. Empty means the registry is coherent."""
    problems: list[str] = []
    namespace_slugs = {slug for slug, _l, _t in NAMESPACES.values()}
    topic_ids = {str(t["id"]) for t in TOPICS}

    for topic in TOPICS:
        tid = str(topic["id"])
        ns = str(topic["namespace"])
        if ns not in NAMESPACES:
            problems.append(f"{tid}: unknown namespace {ns}")
        elif not tid.startswith(ns + "."):
            problems.append(f"{tid}: id does not match namespace {ns}")
        section_slug, _letter, _title = NAMESPACES.get(ns, ("", "", ""))
        if str(topic.get("module")) not in {section_slug, str(topic.get("module"))}:
            pass  # module is free-form within the section
        if topic["difficulty"] not in DIFFICULTIES:
            problems.append(f"{tid}: bad difficulty {topic['difficulty']}")
        if topic["status"] not in PUBLICATION_STATUSES:
            problems.append(f"{tid}: bad status {topic['status']}")
        for slug, confidence, _primary in topic["lessons"]:  # type: ignore[misc]
            if confidence not in CONFIDENCES:
                problems.append(f"{tid}: bad confidence {confidence}")
        for prereq, kind in topic["prerequisites"]:  # type: ignore[misc]
            if prereq not in topic_ids:
                problems.append(f"{tid}: unknown prerequisite {prereq}")
            if prereq == tid:
                problems.append(f"{tid}: prereq on itself")
            if kind not in PREREQ_KINDS:
                problems.append(f"{tid}: bad prereq kind {kind}")

    # Each lesson must have at most one primary topic.
    primaries: dict[str, list[str]] = {}
    for topic in TOPICS:
        for slug, _c, primary in topic["lessons"]:  # type: ignore[misc]
            if primary:
                primaries.setdefault(str(slug), []).append(str(topic["id"]))
    for slug, ids in primaries.items():
        if len(ids) > 1:
            problems.append(f"lesson {slug}: multiple primary topics {ids}")

    for slug in _cycle_members(
        {str(t["id"]): [p for p, _k in t["prerequisites"]] for t in TOPICS}  # type: ignore[misc]
    ):
        problems.append(f"topic {slug}: part of a prerequisite cycle")

    if set(namespace_slugs) != {s["slug"] for s in SECTIONS}:
        problems.append("namespace/section slug mismatch")

    return problems


def _cycle_members(graph: dict[str, list[str]]) -> list[str]:
    """Return topic ids lying on a cycle, via iterative DFS."""
    members: list[str] = []
    state: dict[str, int] = {}
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
