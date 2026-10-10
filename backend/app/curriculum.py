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
            ("13_classical_bit_vs_qubit", "high", True),
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

    # ================================================================== #
    # M4 expansion - 54 topics approved at c8f7144 (Gate 1).             #
    # Generated from the committed architecture in                       #
    # backend/scripts/topic_gap_analysis.py: effective_proposal() and    #
    # TOPIC_OBJECTIVES. Status is 'draft' because no lesson content      #
    # exists yet; each is published when its lesson is authored and      #
    # validated, so draft topics never reach learner navigation.         #
    #                                                                    #
    # Prerequisite entries are (id, kind) or (id, kind, rationale). The  #
    # rationale is optional and preserved when present.                  #
    # ================================================================== #

    # ---- M4 expansion: Mathematical Foundations ---------------------------- #
    {
        "id": "math.complex_numbers",
        "title": "Complex Numbers and Euler's Formula",
        "namespace": "math",
        "module": "mathematical-foundations",
        "position": 11,
        "difficulty": "beginner",
        "status": "draft",
        "description": (
            "Complex arithmetic, the polar form and Euler's formula, and why "
            "quantum amplitudes are complex."
        ),
        "objectives": [
            "Represent a complex number in rectangular and polar form",
            "Derive and apply Euler's formula for a complex phase",
            "Compute the magnitude and phase of a complex amplitude",
        ],
        "lessons": [
            ("14_complex_numbers", "high", True),
        ],
        "prerequisites": [],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "math.linear_algebra",
        "title": "Vectors, Matrices and Linear Algebra",
        "namespace": "math",
        "module": "mathematical-foundations",
        "position": 12,
        "difficulty": "beginner",
        "status": "draft",
        "description": (
            "Vectors, matrices and change of basis, the language every "
            "quantum state is written in."
        ),
        "objectives": [
            "Represent a state as a column vector in a chosen basis",
            "Multiply a matrix by a vector and interpret the result",
            "Transform a vector between two bases",
        ],
        "lessons": [
            ("15_linear_algebra", "high", True),
        ],
        "prerequisites": [
            (
                "math.complex_numbers",
                "required",
                "Matrix entries are complex; inner products need "
                "conjugation."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "math.probability_and_statistics",
        "title": "Probability, Expectation and Sampling Statistics",
        "namespace": "math",
        "module": "mathematical-foundations",
        "position": 13,
        "difficulty": "beginner",
        "status": "draft",
        "description": (
            "Expectation, variance and the sampling statistics that govern "
            "finite-shot results."
        ),
        "objectives": [
            "Compute expectation and variance of a discrete distribution",
            "Derive the standard error of an estimated probability",
            "Choose a shot count that makes an effect larger than its error bar",
        ],
        "lessons": [
            ("17_probability_and_statistics", "high", True),
        ],
        "prerequisites": [],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "math.eigen_and_operators",
        "title": "Eigenvalues, Eigenvectors and Operator Classes",
        "namespace": "math",
        "module": "mathematical-foundations",
        "position": 14,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Eigenvalues, eigenvectors and the operator classes whose spectra "
            "carry physical meaning."
        ),
        "objectives": [
            "Compute eigenvalues and eigenvectors of a two-by-two matrix",
            "Recognise Hermitian and unitary matrices and state their key properties",
            "Explain why observable quantities correspond to Hermitian operators",
        ],
        "lessons": [
            ("16_eigen_and_operators", "high", True),
        ],
        "prerequisites": [
            (
                "math.linear_algebra",
                "required",
                "Eigen-decomposition is defined on matrices; Hermitian and "
                "unitary are properties of a matrix."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "math.group_theory",
        "title": "Introductory Group Theory",
        "namespace": "math",
        "module": "mathematical-foundations",
        "position": 15,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Groups, generators and the matrix groups that later underpin "
            "Clifford circuits and stabilisers."
        ),
        "objectives": [
            "State the group axioms and give a matrix example",
            "Identify generators of a group",
            "Recognise the Pauli group and the Clifford group",
        ],
        "lessons": [
            ("18_group_theory", "high", True),
        ],
        "prerequisites": [
            (
                "math.linear_algebra",
                "recommended",
                "Matrix groups are the motivating example, but the topic "
                "can be taught from symmetry alone."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },

    # ---- M4 expansion: Core Quantum Theory --------------------------------- #
    {
        "id": "core.quantum_postulates",
        "title": "Quantum Postulates",
        "namespace": "core",
        "module": "core-quantum-theory",
        "position": 12,
        "difficulty": "beginner",
        "status": "draft",
        "description": (
            "The postulates of quantum mechanics stated as a whole: states, "
            "evolution, measurement and composition."
        ),
        "objectives": [
            "State the four postulates of quantum mechanics",
            "Identify which postulate a given operation instantiates",
            "Explain how the postulates together constrain what a quantum computer can do",
        ],
        "lessons": [
            ("19_quantum_postulates", "high", True),
        ],
        "prerequisites": [
            (
                "qc.qubits",
                "recommended",
                "Postulates are best motivated after the reader has met a "
                "state vector and the Born rule in practice."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "core.no_cloning",
        "title": "No-Cloning and No-Deleting",
        "namespace": "core",
        "module": "core-quantum-theory",
        "position": 13,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "The no-cloning and no-deleting theorems, their proofs, and what "
            "they forbid and permit."
        ),
        "objectives": [
            "Prove the no-cloning theorem from linearity",
            "Explain why cloning is possible for orthogonal states but not general ones",
            "State the consequence of no-cloning for error correction and cryptography",
        ],
        "lessons": [
            ("22_no_cloning", "high", True),
        ],
        "prerequisites": [
            (
                "qc.qubits",
                "required",
                "The proof is a short argument about linearity of unitary "
                "evolution on superpositions."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "core.density_matrices",
        "title": "Density Matrices, Mixed States and Partial Trace",
        "namespace": "core",
        "module": "core-quantum-theory",
        "position": 14,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "The density operator, mixed states, purity and the partial trace "
            "used to describe subsystems."
        ),
        "objectives": [
            "Construct the density matrix of a pure and of a mixed state",
            "Compute purity and interpret it as a measure of mixedness",
            "Trace out a subsystem to obtain a reduced density matrix",
        ],
        "lessons": [
            ("20_density_matrices", "high", True),
        ],
        "prerequisites": [
            ("core.quantum_postulates", "recommended", "The density operator formalises the measurement postulate."),
            (
                "qc.entanglement",
                "required",
                "Partial trace is only meaningful once a composite system "
                "has been reduced; entanglement is the motivating case."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "core.entanglement_measures",
        "title": "Entanglement Entropy and Monogamy",
        "namespace": "core",
        "module": "core-quantum-theory",
        "position": 15,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Von Neumann entropy, concurrence and monogamy as quantitative "
            "measures of entanglement."
        ),
        "objectives": [
            "Compute the entanglement entropy of a bipartite pure state",
            "State the monogamy of entanglement and its consequence for sharing correlations",
            "Compare entanglement entropy with concurrence for Bell states",
        ],
        "lessons": [
            ("21_entanglement_measures", "high", True),
        ],
        "prerequisites": [
            (
                "core.density_matrices",
                "required",
                "Entropy of entanglement is the von Neumann entropy of a "
                "reduced density matrix."
            ),
            ("qc.bell_states", "required", "Bell states are the reference maximally entangled pair."),
        ],
        "assessments": [],
        "visualizations": [],
    },

    # ---- M4 expansion: Introduction to Quantum Computing ------------------- #
    {
        "id": "qc.dirac_notation",
        "title": "Dirac Notation and Inner Products",
        "namespace": "qc",
        "module": "intro-quantum-computing",
        "position": 14,
        "difficulty": "beginner",
        "status": "draft",
        "description": (
            "Bra-ket notation, inner and outer products, and the conventions "
            "used throughout the curriculum."
        ),
        "objectives": [
            "Write a state and its dual in bra-ket notation",
            "Compute inner products and normalise a state",
            "Interpret the outer product as an operator",
        ],
        "lessons": [
            ("23_dirac_notation", "high", True),
        ],
        "prerequisites": [
            (
                "math.linear_algebra",
                "recommended",
                "Bra-ket is a notation for the inner product, but it can be "
                "introduced operationally first."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "qc.reading_results",
        "title": "Understanding Circuits and Finding Results",
        "namespace": "qc",
        "module": "intro-quantum-computing",
        "position": 15,
        "difficulty": "beginner",
        "status": "draft",
        "description": (
            "Reading circuits and results: gate order, bit ordering and "
            "interpreting an outcome distribution."
        ),
        "objectives": [
            "Read a circuit diagram and state the gate order",
            "Apply the qubit-zero-rightmost bit ordering convention",
            "Interpret a measurement histogram",
        ],
        "lessons": [
            ("27_reading_results", "high", True),
        ],
        "prerequisites": [
            ("qc.basic_gates", "recommended", "Reading a circuit requires knowing the gate symbols."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "qc.tensor_products",
        "title": "Tensor Products and Multi-Qubit Spaces",
        "namespace": "qc",
        "module": "intro-quantum-computing",
        "position": 16,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Building multi-qubit spaces with the tensor product, and why "
            "state space grows exponentially."
        ),
        "objectives": [
            "Compute the tensor product of two state vectors",
            "Explain why n qubits require two-to-the-n amplitudes",
            "Determine whether a two-qubit state is separable or entangled",
        ],
        "lessons": [
            ("24_tensor_products", "high", True),
        ],
        "prerequisites": [
            ("qc.dirac_notation", "required", "Kronecker products are written in bra-ket."),
            ("qc.qubits", "required", "Multi-qubit space is built from single-qubit spaces."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "qc.teleportation",
        "title": "Quantum Teleportation",
        "namespace": "qc",
        "module": "intro-quantum-computing",
        "position": 17,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "The teleportation protocol, why it needs two classical bits, and "
            "why it does not permit signalling."
        ),
        "objectives": [
            "Construct the teleportation circuit",
            "Explain why two classical bits are required and why they enforce the speed limit",
            "Verify the protocol output for a known input state",
        ],
        "lessons": [
            ("26_teleportation", "high", True),
        ],
        "prerequisites": [
            ("qc.bell_states", "required", "Teleportation consumes a shared Bell pair."),
            (
                "adv.dynamic_circuits",
                "required",
                "Bob's correction is conditional on Alice's two classical "
                "bits, so the circuit needs mid-circuit feed-forward."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },

    # ---- M4 expansion: Introduction to Qiskit ------------------------------ #
    {
        "id": "qiskit.composer",
        "title": "The Quantum Composer",
        "namespace": "qiskit",
        "module": "intro-qiskit",
        "position": 7,
        "difficulty": "beginner",
        "status": "draft",
        "description": (
            "Using the Composer: placing gates, controls, parameters, "
            "barriers and measurement."
        ),
        "objectives": [
            "Place gates and multi-qubit controls on the timeline",
            "Enter gate parameters in the supported syntax",
            "Explain what the barrier and reset operations do",
        ],
        "lessons": [
            ("28_composer_guide", "high", True),
        ],
        "prerequisites": [
            ("qc.basic_gates", "required", "You must know what a gate does before placing one."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "qiskit.estimator",
        "title": "The Estimator Primitive",
        "namespace": "qiskit",
        "module": "intro-qiskit",
        "position": 8,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "The Estimator primitive: computing expectation values of "
            "observables and its relation to Sampler."
        ),
        "objectives": [
            "Compute the expectation value of a Pauli observable",
            "Choose basis-change gates to measure in the X, Y or Z basis",
            "Contrast Estimator with Sampler and state when each is appropriate",
        ],
        "lessons": [
            ("29_primitives", "high", True),
        ],
        "prerequisites": [
            (
                "qiskit.sampler",
                "recommended",
                "Sampler is the other half of the primitive pair and "
                "already exists as a topic."
            ),
            ("nisq.vqe", "recommended", "Estimator is motivated by expectation values in VQE."),
        ],
        "assessments": [],
        "visualizations": [],
    },

    # ---- M4 expansion: Quantum Algorithms ---------------------------------- #
    {
        "id": "algo.bernstein_vazirani",
        "title": "Bernstein-Vazirani",
        "namespace": "algo",
        "module": "quantum-algorithms",
        "position": 19,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "The Bernstein-Vazirani algorithm: recovering a hidden string in "
            "one query."
        ),
        "objectives": [
            "Construct the Bernstein-Vazirani circuit",
            "Explain why one query suffices where classical needs n",
            "Relate the algorithm to the Deutsch-Jozsa phase-kickback pattern",
        ],
        "lessons": [
            ("30_bernstein_vazirani", "high", True),
        ],
        "prerequisites": [
            (
                "algo.deutsch_jozsa",
                "required",
                "Same oracle/phase-kickback machinery; BV is the "
                "generalisation."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "algo.simon",
        "title": "Simon's Algorithm",
        "namespace": "algo",
        "module": "quantum-algorithms",
        "position": 20,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Simon's algorithm and the exponential oracle separation it "
            "establishes."
        ),
        "objectives": [
            "Construct Simon's circuit",
            "Explain how the linear system of equations reveals the hidden mask",
            "State the exponential separation it demonstrates",
        ],
        "lessons": [
            ("34_simon", "high", True),
        ],
        "prerequisites": [
            (
                "algo.deutsch_jozsa",
                "required",
                "Same oracle-query model; Simon motivates the exponential "
                "separation that Shor later exploits."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "algo.qft",
        "title": "Quantum Fourier Transform",
        "namespace": "algo",
        "module": "quantum-algorithms",
        "position": 21,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "The quantum Fourier transform: circuit structure, gate count and "
            "role as an algorithmic primitive."
        ),
        "objectives": [
            "Construct the QFT circuit on n qubits",
            "State the gate-count advantage over the classical FFT",
            "Explain the effect of QFT on a periodic superposition",
        ],
        "lessons": [
            ("31_qft", "high", True),
        ],
        "prerequisites": [
            ("qc.basic_gates", "required", "QFT is a circuit of H and controlled-phase gates."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "algo.phase_estimation",
        "title": "Quantum Phase Estimation",
        "namespace": "algo",
        "module": "quantum-algorithms",
        "position": 22,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Quantum phase estimation: extracting an eigenphase of a unitary "
            "into a register."
        ),
        "objectives": [
            "Construct the phase estimation circuit",
            "Explain the role of the inverse QFT",
            "State the precision and success probability in terms of register size",
        ],
        "lessons": [
            ("32_phase_estimation", "high", True),
        ],
        "prerequisites": [
            ("algo.qft", "required", "QPE is the inverse QFT applied to a controlled-U register."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "algo.amplitude_estimation",
        "title": "Amplitude Estimation",
        "namespace": "algo",
        "module": "quantum-algorithms",
        "position": 23,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Amplitude estimation: quadratic speed-up over sampling, and its "
            "relation to phase estimation."
        ),
        "objectives": [
            "Construct the amplitude estimation circuit from the Grover operator",
            "Explain the quadratic improvement in estimation error",
            "Relate amplitude estimation to quantum phase estimation",
        ],
        "lessons": [
            ("36_amplitude_estimation", "high", True),
        ],
        "prerequisites": [
            (
                "algo.phase_estimation",
                "required",
                "Amplitude estimation IS phase estimation on the Grover "
                "operator."
            ),
            ("algo.grover", "required", "The Grover operator is the input to the estimation."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "algo.hhl",
        "title": "HHL Linear Systems",
        "namespace": "algo",
        "module": "quantum-algorithms",
        "position": 24,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "The HHL algorithm for linear systems, its speed-up and its "
            "well-known fine print."
        ),
        "objectives": [
            "State the linear systems problem HHL addresses",
            "Outline the HHL circuit including phase estimation and inversion",
            "List the caveats that limit the claimed speed-up",
        ],
        "lessons": [
            ("37_hhl", "high", True),
        ],
        "prerequisites": [
            ("algo.phase_estimation", "required", "HHL uses phase estimation to extract eigenvalues."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "algo.quantum_walks",
        "title": "Quantum Walks",
        "namespace": "algo",
        "module": "quantum-algorithms",
        "position": 25,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Discrete and continuous-time quantum walks and their algorithmic "
            "uses."
        ),
        "objectives": [
            "Define a discrete-time quantum walk with a coin operator",
            "Contrast quantum walk spreading with classical diffusion",
            "State an algorithmic application of quantum walks",
        ],
        "lessons": [
            ("35_quantum_walks", "high", True),
        ],
        "prerequisites": [
            (
                "algo.grover",
                "recommended",
                "Grover can be recast as a walk search; helpful but not "
                "needed to define a walk."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "algo.shors",
        "title": "Shor's Algorithm",
        "namespace": "algo",
        "module": "quantum-algorithms",
        "position": 26,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Shor's algorithm: order finding, its reduction from factoring, "
            "and its caveats."
        ),
        "objectives": [
            "Reduce factoring to order finding",
            "Explain how phase estimation performs order finding",
            "State the assumptions and the impact on public-key cryptography",
        ],
        "lessons": [
            ("33_shors_algorithm", "high", True),
        ],
        "prerequisites": [
            ("algo.phase_estimation", "required", "Order finding is an application of phase estimation."),
            ("algo.qft", "required", "Shor's period-finding core is a QFT."),
        ],
        "assessments": [],
        "visualizations": [],
    },

    # ---- M4 expansion: Advanced Gates and Circuits ------------------------- #
    {
        "id": "adv.circuit_identities",
        "title": "Circuit Identities and Simplification",
        "namespace": "adv",
        "module": "advanced-gates-circuits",
        "position": 15,
        "difficulty": "beginner",
        "status": "draft",
        "description": (
            "Circuit identities and simplification: cancelling gates and "
            "reducing depth."
        ),
        "objectives": [
            "Apply standard identities such as H squared equals I and SWAP as three CNOTs",
            "Cancel adjacent inverse gates",
            "Simplify a short circuit and check the result",
        ],
        "lessons": [
            ("40_circuit_identities", "high", True),
        ],
        "prerequisites": [
            ("qc.basic_gates", "required", "Identities are statements about gate products."),
            ("adv.quantum_universality", "recommended", "Motivates why rewriting to a basis matters."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "adv.multi_controlled_gates",
        "title": "Toffoli, Multi-Controlled Gates and Controlled Rotations",
        "namespace": "adv",
        "module": "advanced-gates-circuits",
        "position": 16,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Toffoli, multi-controlled X and controlled rotations, and their "
            "decomposition cost."
        ),
        "objectives": [
            "Construct Toffoli and general multi-controlled X circuits",
            "Apply controlled rotation gates",
            "Estimate the decomposition cost of a many-control gate",
        ],
        "lessons": [
            ("38_multi_controlled", "high", True),
        ],
        "prerequisites": [
            ("qc.basic_gates", "required", "Controlled gates extend the single-qubit set."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "adv.parameterized_two_qubit",
        "title": "U3, iSWAP and fSim",
        "namespace": "adv",
        "module": "advanced-gates-circuits",
        "position": 17,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "U3, iSWAP and fSim: the parameterised two-qubit gates native to "
            "real hardware."
        ),
        "objectives": [
            "Define U3, iSWAP and fSim and their matrix forms",
            "Relate each to the portable rotation and CNOT basis",
            "Explain why hardware exposes these gates natively",
        ],
        "lessons": [
            ("39_two_qubit_gates", "high", True),
        ],
        "prerequisites": [
            (
                "qc.basic_gates",
                "required",
                "These are specific two-qubit/one-qubit parameterisations "
                "of the same idea."
            ),
            (
                "adv.multi_controlled_gates",
                "recommended",
                "Controlled rotations are the usual consumer of these "
                "gates."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "adv.compilation",
        "title": "Native Gates, Connectivity and Routing",
        "namespace": "adv",
        "module": "advanced-gates-circuits",
        "position": 18,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Native gate sets, connectivity constraints and the routing that "
            "inserts SWAPs."
        ),
        "objectives": [
            "Explain how connectivity constrains which two-qubit gates can run",
            "Describe how routing inserts SWAPs to satisfy connectivity",
            "Estimate the depth cost of routing on a simple topology",
        ],
        "lessons": [
            ("42_compilation", "high", True),
        ],
        "prerequisites": [
            ("qc.basic_gates", "required", "Transpilation rewrites a circuit made of known gates."),
            ("adv.quantum_universality", "recommended", "Universality is why a fixed basis suffices."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "adv.multipartite_entanglement",
        "title": "GHZ versus W States",
        "namespace": "adv",
        "module": "advanced-gates-circuits",
        "position": 19,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "GHZ and W states, their differing robustness, and multipartite "
            "entanglement classes."
        ),
        "objectives": [
            "Construct GHZ and W states",
            "Explain why GHZ entanglement is fragile under loss of one qubit",
            "Contrast the two states using a measurable witness",
        ],
        "lessons": [
            ("41_multipartite_entanglement", "high", True),
        ],
        "prerequisites": [
            (
                "qc.entanglement",
                "required",
                "Both are multipartite extensions of two-qubit "
                "entanglement."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "adv.resource_estimation",
        "title": "Resource Estimation",
        "namespace": "adv",
        "module": "advanced-gates-circuits",
        "position": 20,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Counting qubits, gates and depth to decide whether an algorithm "
            "is feasible."
        ),
        "objectives": [
            "Count qubits, gate depth and two-qubit gate count for a circuit",
            "Translate a depth budget into a feasibility judgement",
            "Explain how error rates convert depth into a success probability",
        ],
        "lessons": [
            ("43_resource_estimation", "high", True),
        ],
        "prerequisites": [
            (
                "adv.compilation",
                "required",
                "Counts depend on the compiled circuit, not the abstract "
                "one."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },

    # ---- M4 expansion: Variational and NISQ Algorithms --------------------- #
    {
        "id": "nisq.approximation_ratios",
        "title": "Approximation Ratios",
        "namespace": "nisq",
        "module": "variational-nisq",
        "position": 10,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Approximation ratios as the quality measure for approximate "
            "optimisation."
        ),
        "objectives": [
            "Define the approximation ratio for a maximisation problem",
            "Compute the ratio achieved by a given QAOA output",
            "Interpret the known worst-case ratio for QAOA at depth one",
        ],
        "lessons": [
            ("46_approximation_ratios", "high", True),
        ],
        "prerequisites": [
            ("nisq.qaoa", "required", "The ratio is the quality measure for a QAOA solution."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "nisq.optimization",
        "title": "Classical Optimization Loops and the Parameter-Shift Rule",
        "namespace": "nisq",
        "module": "variational-nisq",
        "position": 11,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "The classical optimisation loop around a parameterised circuit, "
            "including the parameter-shift rule."
        ),
        "objectives": [
            "Describe the classical optimisation loop",
            "Apply the parameter-shift rule to obtain an analytic gradient",
            "Compare gradient-based and gradient-free optimisers for noisy objectives",
        ],
        "lessons": [
            ("45_optimization_loops", "high", True),
        ],
        "prerequisites": [
            ("nisq.parameterized_circuits", "required", "Gradients are taken with respect to ansatz parameters."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "nisq.qml",
        "title": "Quantum Machine Learning, Feature Maps and Kernels",
        "namespace": "nisq",
        "module": "variational-nisq",
        "position": 12,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Quantum machine learning: feature maps, kernels and variational "
            "classifiers."
        ),
        "objectives": [
            "Construct a quantum feature map and a kernel from it",
            "Train a variational classifier",
            "State the known limitations of near-term quantum machine learning",
        ],
        "lessons": [
            ("47_quantum_machine_learning", "high", True),
        ],
        "prerequisites": [
            ("nisq.parameterized_circuits", "required", "Feature maps are parameterised circuits."),
            ("nisq.optimization", "recommended", "Training is the same hybrid loop."),
        ],
        "assessments": [],
        "visualizations": [],
    },

    # ---- M4 expansion: Error Correction and Fault Tolerance ---------------- #
    {
        "id": "qec.bit_flip_code",
        "title": "Three-Qubit Bit-Flip Code",
        "namespace": "qec",
        "module": "error-correction",
        "position": 15,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "The three-qubit bit-flip code: encoding, syndrome measurement "
            "and correction."
        ),
        "objectives": [
            "Construct the encoding circuit for the bit-flip code",
            "Measure the syndrome without collapsing the encoded state",
            "Apply the conditional correction and verify the output",
        ],
        "lessons": [
            ("49_bit_flip_code", "high", True),
        ],
        "prerequisites": [
            (
                "adv.dynamic_circuits",
                "required",
                "Syndrome measurement plus conditional correction is a "
                "dynamic circuit."
            ),
            ("qiskit.quantum_noise", "required", "The bit-flip channel is the error model being corrected."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "qec.phase_flip_code",
        "title": "Three-Qubit Phase-Flip Code",
        "namespace": "qec",
        "module": "error-correction",
        "position": 16,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "The three-qubit phase-flip code and its relation to the bit-flip "
            "code by basis change."
        ),
        "objectives": [
            "Construct the phase-flip code circuit",
            "Show the code is the bit-flip code in the X basis",
            "Verify correction of a single phase error",
        ],
        "lessons": [
            ("50_phase_flip_code", "high", True),
        ],
        "prerequisites": [
            (
                "qec.bit_flip_code",
                "required",
                "Same structure in the conjugate basis; teach the pattern "
                "once."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "qec.error_mitigation",
        "title": "Error Mitigation: ZNE, PEC and Readout Correction",
        "namespace": "qec",
        "module": "error-correction",
        "position": 17,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Error mitigation: zero-noise extrapolation, probabilistic error "
            "cancellation and readout correction."
        ),
        "objectives": [
            "Explain the difference between error mitigation and error correction",
            "Apply zero-noise extrapolation to a noisy expectation value",
            "Construct and apply a readout error correction matrix",
        ],
        "lessons": [
            ("55_error_mitigation", "high", True),
        ],
        "prerequisites": [
            (
                "qiskit.quantum_noise",
                "required",
                "Mitigation post-processes noisy results; it needs a noise "
                "model first."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "qec.stabilizer_formalism",
        "title": "Stabilizer Formalism",
        "namespace": "qec",
        "module": "error-correction",
        "position": 18,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "The stabiliser formalism: describing codes by the operators that "
            "fix them."
        ),
        "objectives": [
            "Define a stabiliser group and its code space",
            "Determine the stabilisers of a given code",
            "Derive the syndrome from stabiliser measurement outcomes",
        ],
        "lessons": [
            ("51_stabilizer_formalism", "high", True),
        ],
        "prerequisites": [
            ("qec.phase_flip_code", "required", "Stabilisers generalise the two three-qubit codes."),
            (
                "math.group_theory",
                "recommended",
                "The stabiliser group is a group; helpful, not strictly "
                "needed."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "qec.surface_codes",
        "title": "Surface Codes",
        "namespace": "qec",
        "module": "error-correction",
        "position": 19,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Surface codes: lattice stabilisers, decoding and why they are "
            "the leading practical family."
        ),
        "objectives": [
            "Describe the stabiliser layout of a surface code",
            "Explain how the code distance sets the error-correcting power",
            "State why surface codes suit nearest-neighbour hardware",
        ],
        "lessons": [
            ("52_surface_codes", "high", True),
        ],
        "prerequisites": [
            ("qec.stabilizer_formalism", "required", "Surface codes are stabiliser codes on a lattice."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "qec.logical_physical",
        "title": "Logical and Physical Qubits, and Overhead",
        "namespace": "qec",
        "module": "error-correction",
        "position": 20,
        "difficulty": "advanced",
        "status": "draft",
        "description": "Logical versus physical qubits and the overhead a code demands.",
        "objectives": [
            "Define a logical qubit in terms of physical qubits",
            "Compute the physical-to-logical ratio for a code family",
            "Explain how overhead scales with target error rate",
        ],
        "lessons": [
            ("53_logical_physical_qubits", "high", True),
        ],
        "prerequisites": [
            (
                "qec.surface_codes",
                "required",
                "Overhead is quoted as physical qubits per logical qubit "
                "for a specific code."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "qec.threshold_theorem",
        "title": "Threshold Theorem and Fault Tolerance",
        "namespace": "qec",
        "module": "error-correction",
        "position": 21,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "The threshold theorem and the fault-tolerant construction it "
            "licenses."
        ),
        "objectives": [
            "State the threshold theorem and its assumptions",
            "Explain why arbitrarily long computation becomes possible below threshold",
            "Distinguish fault-tolerant from merely error-detecting constructions",
        ],
        "lessons": [
            ("54_threshold_theorem", "high", True),
        ],
        "prerequisites": [
            (
                "qec.logical_physical",
                "required",
                "The threshold is a bound on physical error rate given an "
                "overhead budget."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },

    # ---- M4 expansion: Quantum Hardware and Ecosystem ---------------------- #
    {
        "id": "hw.ecosystem",
        "title": "Quantum Ecosystem: Qiskit, Cirq, PennyLane, CUDA-Q and Braket",
        "namespace": "hw",
        "module": "hardware-ecosystem",
        "position": 21,
        "difficulty": "beginner",
        "status": "draft",
        "description": (
            "A survey of the quantum software ecosystem and the roles of the "
            "major frameworks."
        ),
        "objectives": [
            "Name the major SDKs and what each is best at",
            "Explain the role of a hardware provider service",
            "Choose tooling appropriate to a task",
        ],
        "lessons": [
            ("65_quantum_ecosystem", "high", True),
        ],
        "prerequisites": [
            ("qc.basic_gates", "recommended", "Survey of tooling; assumes the basics."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "hw.neutral_atoms",
        "title": "Neutral Atoms",
        "namespace": "hw",
        "module": "hardware-ecosystem",
        "position": 22,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Neutral-atom arrays: encoding, Rydberg gates and reconfigurable "
            "geometry."
        ),
        "objectives": [
            "Describe how neutral atoms encode qubits",
            "Explain the Rydberg blockade mechanism for entangling gates",
            "State the scaling advantage of atom arrays",
        ],
        "lessons": [
            ("59_neutral_atoms", "high", True),
        ],
        "prerequisites": [
            ("qiskit.quantum_noise", "recommended", "Same per-platform metrics."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "hw.nisq_limitations",
        "title": "NISQ Limitations",
        "namespace": "hw",
        "module": "hardware-ecosystem",
        "position": 23,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "What NISQ devices can and cannot do, and why depth is the "
            "binding constraint."
        ),
        "objectives": [
            "State the constraints defining the NISQ regime",
            "Explain why circuit depth is limited by error rates",
            "Assess whether a proposed algorithm fits current hardware",
        ],
        "lessons": [
            ("62_nisq_limitations", "high", True),
        ],
        "prerequisites": [
            ("qiskit.quantum_noise", "required", "NISQ limits are decoherence and gate-error limits."),
            ("adv.resource_estimation", "recommended", "Depth budgets quantify what is feasible."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "hw.photonic_systems",
        "title": "Photonic Systems",
        "namespace": "hw",
        "module": "hardware-ecosystem",
        "position": 24,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Photonic quantum computing: qubit encodings, gates and the loss "
            "challenge."
        ),
        "objectives": [
            "Describe a photonic qubit encoding",
            "Explain how linear optics implements gates probabilistically",
            "State why loss is the dominant error channel",
        ],
        "lessons": [
            ("58_photonic_systems", "high", True),
        ],
        "prerequisites": [
            ("qiskit.quantum_noise", "recommended", "Same per-platform metrics."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "hw.spin_qubits",
        "title": "Spin-Based Qubits",
        "namespace": "hw",
        "module": "hardware-ecosystem",
        "position": 25,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Spin qubits in semiconductors: encoding, control and integration "
            "prospects."
        ),
        "objectives": [
            "Describe how electron or nuclear spin encodes a qubit",
            "Explain how exchange interaction produces two-qubit gates",
            "State the main fabrication and coherence challenges",
        ],
        "lessons": [
            ("60_spin_qubits", "high", True),
        ],
        "prerequisites": [
            ("qiskit.quantum_noise", "recommended", "Same per-platform metrics."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "hw.superconducting_qubits",
        "title": "Superconducting Qubits",
        "namespace": "hw",
        "module": "hardware-ecosystem",
        "position": 26,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Superconducting qubits: the transmon, its control and its "
            "characteristic error budget."
        ),
        "objectives": [
            "Describe how a transmon encodes a qubit",
            "State typical coherence times and gate fidelities",
            "Identify the dominant error mechanisms for this platform",
        ],
        "lessons": [
            ("56_superconducting_qubits", "high", True),
        ],
        "prerequisites": [
            ("qiskit.quantum_noise", "recommended", "T1/T2 are the figures quoted per platform."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "hw.trapped_ions",
        "title": "Trapped Ions",
        "namespace": "hw",
        "module": "hardware-ecosystem",
        "position": 27,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Trapped-ion qubits: encoding, gates and the connectivity "
            "advantage."
        ),
        "objectives": [
            "Describe how ion internal states encode a qubit",
            "Explain how trapped ions achieve all-to-all connectivity",
            "Contrast gate speed and coherence with superconducting devices",
        ],
        "lessons": [
            ("57_trapped_ions", "high", True),
        ],
        "prerequisites": [
            ("qiskit.quantum_noise", "recommended", "Same per-platform metrics."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "hw.platform_comparison",
        "title": "Calibrated Noise Models and Connectivity Topologies",
        "namespace": "hw",
        "module": "hardware-ecosystem",
        "position": 28,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Comparing platforms through calibrated noise models and "
            "connectivity topologies."
        ),
        "objectives": [
            "Read a calibrated noise model for a device",
            "Compare connectivity topologies across platforms",
            "Choose a platform appropriate to a given workload",
        ],
        "lessons": [
            ("61_platform_comparison", "high", True),
        ],
        "prerequisites": [
            ("hw.superconducting_qubits", "required", "Needs at least one concrete platform to calibrate against."),
            (
                "hw.trapped_ions",
                "recommended",
                "A comparison that has seen only one platform compares "
                "nothing; trapped ions are the contrasting case of "
                "all-to-all connectivity."
            ),
            (
                "hw.photonic_systems",
                "recommended",
                "Photonic and matter qubits differ on connectivity and "
                "loss, which is the substance of the comparison."
            ),
            (
                "hw.neutral_atoms",
                "recommended",
                "Neutral atoms add a third connectivity regime "
                "(reconfigurable geometry)."
            ),
            (
                "hw.spin_qubits",
                "recommended",
                "Spin qubits contribute the most constrained connectivity "
                "and the smallest footprint."
            ),
            ("adv.compilation", "recommended", "Connectivity is what routing has to work around."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "hw.benchmarking",
        "title": "Quantum Benchmarking",
        "namespace": "hw",
        "module": "hardware-ecosystem",
        "position": 29,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Benchmarking quantum devices: randomised benchmarking, quantum "
            "volume and beyond."
        ),
        "objectives": [
            "Describe randomised benchmarking and what it measures",
            "Define quantum volume and its limitations",
            "Choose a benchmark appropriate to a claimed capability",
        ],
        "lessons": [
            ("64_benchmarking", "high", True),
        ],
        "prerequisites": [
            ("hw.nisq_limitations", "required", "Benchmarks measure how close a device is to its limits."),
            ("hw.platform_comparison", "recommended", "Cross-platform comparison needs comparable metrics."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "hw.complexity_classes",
        "title": "BQP, P, NP and BPP",
        "namespace": "hw",
        "module": "hardware-ecosystem",
        "position": 30,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "BQP and its relation to P, NP and BPP, and what separations are "
            "known or believed."
        ),
        "objectives": [
            "Define BQP, BPP and NP",
            "State the known inclusions relating these classes",
            "Explain what quantum speed-up evidence does and does not establish",
        ],
        "lessons": [
            ("63_complexity_classes", "high", True),
        ],
        "prerequisites": [
            ("algo.grover", "recommended", "Grover and Shor are the separations that motivate BQP."),
        ],
        "assessments": [],
        "visualizations": [],
    },

    # ---- M4 expansion: Quantum Communication and Simulation ---------------- #
    {
        "id": "comm.cryptography",
        "title": "Quantum Cryptography, QKD and Post-Quantum Cryptography",
        "namespace": "comm",
        "module": "communication-simulation",
        "position": 11,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Quantum cryptography, QKD and the post-quantum response to "
            "Shor's algorithm."
        ),
        "objectives": [
            "Explain how a QKD protocol detects eavesdropping",
            "State the security assumption underlying QKD",
            "Distinguish post-quantum cryptography from quantum cryptography",
        ],
        "lessons": [
            ("68_quantum_cryptography", "high", True),
        ],
        "prerequisites": [
            (
                "core.no_cloning",
                "required",
                "QKD security rests on the impossibility of cloning an "
                "unknown state."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "comm.superdense_coding",
        "title": "Superdense Coding",
        "namespace": "comm",
        "module": "communication-simulation",
        "position": 12,
        "difficulty": "intermediate",
        "status": "draft",
        "description": (
            "Superdense coding: sending two classical bits with one qubit "
            "using shared entanglement."
        ),
        "objectives": [
            "Construct the superdense coding circuit",
            "Explain why two bits are transmitted per qubit",
            "State the entanglement resource cost",
        ],
        "lessons": [
            ("66_superdense_coding", "high", True),
        ],
        "prerequisites": [
            ("qc.bell_states", "required", "Consumes a shared Bell pair to send two bits in one qubit."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "comm.quantum_networks",
        "title": "Quantum Repeaters and the Quantum Internet",
        "namespace": "comm",
        "module": "communication-simulation",
        "position": 13,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Quantum repeaters and the quantum internet: extending "
            "entanglement across distance."
        ),
        "objectives": [
            "Explain why direct transmission fails at long distance",
            "Describe entanglement swapping and a repeater chain",
            "State what a quantum internet enables beyond point-to-point links",
        ],
        "lessons": [
            ("67_quantum_networks", "high", True),
        ],
        "prerequisites": [
            (
                "qc.teleportation",
                "required",
                "Repeaters are chained entanglement swapping, which is "
                "teleportation between nodes."
            ),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "comm.quantum_simulation",
        "title": "Quantum Simulation and Many-Body Systems",
        "namespace": "comm",
        "module": "communication-simulation",
        "position": 14,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Simulating quantum systems, and why it was the original "
            "motivation for quantum computing."
        ),
        "objectives": [
            "Map a Hamiltonian onto a qubit Hamiltonian",
            "Explain why classical simulation scales exponentially",
            "State what observables are accessible from a simulation",
        ],
        "lessons": [
            ("69_quantum_simulation", "high", True),
        ],
        "prerequisites": [
            ("algo.phase_estimation", "recommended", "Energy estimation is the original simulation application."),
            ("nisq.vqe", "recommended", "VQE is the NISQ-era alternative for the same task."),
        ],
        "assessments": [],
        "visualizations": [],
    },
    {
        "id": "comm.trotterization",
        "title": "Trotterization",
        "namespace": "comm",
        "module": "communication-simulation",
        "position": 15,
        "difficulty": "advanced",
        "status": "draft",
        "description": (
            "Trotterisation: decomposing Hamiltonian evolution into gates and "
            "controlling the error."
        ),
        "objectives": [
            "Apply the first-order Trotter formula",
            "Bound the Trotter error in terms of the time step",
            "Trade off step size against circuit depth",
        ],
        "lessons": [
            ("70_trotterization", "high", True),
        ],
        "prerequisites": [
            (
                "comm.quantum_simulation",
                "required",
                "Trotterisation is how a simulated Hamiltonian evolution is "
                "broken into gates."
            ),
        ],
        "assessments": [],
        "visualizations": [],
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


#: Evidence for each lesson -> topic mapping, keyed ``"<lesson>::<topic>"``.
#:
#: Entries cite what the lesson actually contains (section headings, worked
#: derivations, exercises) or, where assessment data is involved, which
#: authored quiz or challenge backs the link. Every mapping in TOPICS must have
#: an entry here; a test enforces that, so an unexplained mapping cannot land.
#:
#: ``inferred`` marks a mapping resting on indirect evidence. Those are never
#: treated as verified and never gate mastery on their own.
LESSON_TOPIC_EVIDENCE: dict[str, str] = {
    "13_classical_bit_vs_qubit::qc.qubits": (
        "Lesson is titled 'A Classical Switch vs a Qubit' and works through the "
        "classical-switch comparison end to end. Content-derived."
    ),
    "13_classical_bit_vs_qubit::core.quantum_interference": (
        "Contains 'The decisive experiment', 'The hidden coin hypothesis' and "
        "'Now break the interference' — an explicit interference demonstration. "
        "Content-derived."
    ),
    "01_qubits::qc.qubits": (
        "Titled 'Qubits and Superposition'; sections on basis states, the Bloch "
        "sphere and multiple qubits. Primary source for the topic."
    ),
    "01_qubits::qc.superposition": (
        "Has 'Why amplitudes matter more than probabilities', which is the "
        "amplitude-versus-probability distinction. It does NOT cover relative "
        "versus global phase or density matrices, so this is partial only."
    ),
    "02_gates::qc.basic_gates": (
        "Titled 'Quantum Gates'; enumerates single-qubit, rotation/phase and "
        "multi-qubit gates with matrices. Primary source."
    ),
    "02_gates::adv.quantum_universality": (
        "Has a 'Universality and transpilation' section. Covers the concept but "
        "not native gate sets or routing, so partial."
    ),
    "10_gates_bootcamp::qc.basic_gates": (
        "Titled 'Gates Bootcamp: Every Gate, Step by Step'; walks I, X, H, Z, Y, "
        "S/S-dagger individually. Practice material for the same topic."
    ),
    "11_bell_states::qc.bell_states": (
        "Titled 'The Four Bell States'; derives each one and distinguishes them. "
        "Primary source."
    ),
    "11_bell_states::qc.entanglement": (
        "Has 'Why maximally entangled' and 'The crucial observation'. Supports "
        "the entanglement topic but does not generalise to separability tests."
    ),
    "03_entanglement::qc.entanglement": (
        "Titled 'Entanglement'; covers non-separability, GHZ, and 'what "
        "entanglement is not'. Primary source for the general concept."
    ),
    "04_measurement::core.measurement_theory": (
        "Titled 'Measurement and Dynamic Circuits'; covers shots, the Born-rule "
        "reading and terminal versus mid-circuit measurement. Primary source."
    ),
    "04_measurement::qiskit.sampler": (
        "Has a 'Shots' section on sampling and counts. Covers the primitive "
        "conceptually but does not demonstrate the Sampler API or convergence."
    ),
    "04_measurement::adv.dynamic_circuits": (
        "Has 'Dynamic circuits: classical feedback' and 'The two measurement "
        "buttons'. Introductory only; the dedicated lessons go deeper."
    ),
    "09_quantum_noise::qiskit.quantum_noise": (
        "Titled 'Quantum Noise and Decoherence'; covers T1/T2, amplitude damping "
        "and dephasing. Primary source."
    ),
    "09_quantum_noise::core.quantum_channels": (
        "Has 'The standard noise channels' with depolarizing, amplitude- and "
        "phase-damping. Channel content is genuine but framed for practitioners."
    ),
    "05_deutsch_jozsa::algo.deutsch_jozsa": (
        "Titled 'Deutsch-Jozsa and Quantum Parallelism'; covers the promise, "
        "phase kickback and the circuit. Primary source."
    ),
    "05_deutsch_jozsa::core.quantum_interference": (
        "Has 'The phase kickback trick' and 'Why it works', which is applied "
        "interference. Secondary: the lesson's purpose is the algorithm."
    ),
    "06_grover::algo.grover": (
        "Titled 'Grover's Search Algorithm'; covers the iteration, geometry "
        "and over-rotation. Primary source."
    ),
    "06_grover::core.quantum_interference": (
        "Has 'Geometry' and 'Do not over-rotate', describing amplitude "
        "amplification. Secondary: the lesson's purpose is the algorithm."
    ),
    "07_vqe_qaoa::nisq.vqe": (
        "Titled 'Variational Algorithms: VQE and QAOA'; has 'The hybrid loop' "
        "and a VQE section. Primary source."
    ),
    "07_vqe_qaoa::nisq.qaoa": (
        "Has a dedicated QAOA section. Shares one lesson with VQE, so both are "
        "covered at similar depth rather than one being primary."
    ),
    "07_vqe_qaoa::nisq.parameterized_circuits": (
        "Has 'Ansatz design and barren plateaus'. Covers the ideas; no "
        "parameter-shift derivation. Partial."
    ),
    "08_dynamic_circuits::adv.dynamic_circuits": (
        "Titled 'Dynamic Circuits and Classical Control Flow'; covers if/else, "
        "bitstring comparison, for and while. Primary source."
    ),
    "12_control_flow::adv.dynamic_circuits": (
        "Titled 'Control Flow: if, for, while and Box'; includes 'Measurement "
        "semantics: the trap'. Hands-on counterpart to 08."
    ),

    # ---- M4 expansion: planned lessons (content not yet authored) ----- #
    # These record a planned assignment from the approved architecture,  #
    # not content-derived evidence: the lesson files do not exist yet.   #
    # Each is replaced with content-derived evidence on authoring.       #
    "40_circuit_identities::adv.circuit_identities": (
        "Planned lesson for 'Circuit Identities and Simplification', assigned "
        "by the approved M4 architecture (c8f7144). No content exists yet, so "
        "this is a planned-assignment record rather than content-derived "
        "evidence; it is replaced with content-derived detail when the lesson "
        "is authored."
    ),
    "42_compilation::adv.compilation": (
        "Planned lesson for 'Native Gates, Connectivity and Routing', "
        "assigned by the approved M4 architecture (c8f7144). No content "
        "exists yet, so this is a planned-assignment record rather than "
        "content-derived evidence; it is replaced with content-derived detail "
        "when the lesson is authored."
    ),
    "38_multi_controlled::adv.multi_controlled_gates": (
        "Planned lesson for 'Toffoli, Multi-Controlled Gates and Controlled "
        "Rotations', assigned by the approved M4 architecture (c8f7144). No "
        "content exists yet, so this is a planned-assignment record rather "
        "than content-derived evidence; it is replaced with content-derived "
        "detail when the lesson is authored."
    ),
    "41_multipartite_entanglement::adv.multipartite_entanglement": (
        "Planned lesson for 'GHZ versus W States', assigned by the approved "
        "M4 architecture (c8f7144). No content exists yet, so this is a "
        "planned-assignment record rather than content-derived evidence; it "
        "is replaced with content-derived detail when the lesson is authored."
    ),
    "39_two_qubit_gates::adv.parameterized_two_qubit": (
        "Planned lesson for 'U3, iSWAP and fSim', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "43_resource_estimation::adv.resource_estimation": (
        "Planned lesson for 'Resource Estimation', assigned by the approved "
        "M4 architecture (c8f7144). No content exists yet, so this is a "
        "planned-assignment record rather than content-derived evidence; it "
        "is replaced with content-derived detail when the lesson is authored."
    ),
    "36_amplitude_estimation::algo.amplitude_estimation": (
        "Planned lesson for 'Amplitude Estimation', assigned by the approved "
        "M4 architecture (c8f7144). No content exists yet, so this is a "
        "planned-assignment record rather than content-derived evidence; it "
        "is replaced with content-derived detail when the lesson is authored."
    ),
    "30_bernstein_vazirani::algo.bernstein_vazirani": (
        "Planned lesson for 'Bernstein-Vazirani', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "37_hhl::algo.hhl": (
        "Planned lesson for 'HHL Linear Systems', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "32_phase_estimation::algo.phase_estimation": (
        "Planned lesson for 'Quantum Phase Estimation', assigned by the "
        "approved M4 architecture (c8f7144). No content exists yet, so this "
        "is a planned-assignment record rather than content-derived evidence; "
        "it is replaced with content-derived detail when the lesson is "
        "authored."
    ),
    "31_qft::algo.qft": (
        "Planned lesson for 'Quantum Fourier Transform', assigned by the "
        "approved M4 architecture (c8f7144). No content exists yet, so this "
        "is a planned-assignment record rather than content-derived evidence; "
        "it is replaced with content-derived detail when the lesson is "
        "authored."
    ),
    "35_quantum_walks::algo.quantum_walks": (
        "Planned lesson for 'Quantum Walks', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "33_shors_algorithm::algo.shors": (
        "Planned lesson for 'Shor's Algorithm', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "34_simon::algo.simon": (
        "Planned lesson for 'Simon's Algorithm', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "68_quantum_cryptography::comm.cryptography": (
        "Planned lesson for 'Quantum Cryptography, QKD and Post-Quantum "
        "Cryptography', assigned by the approved M4 architecture (c8f7144). "
        "No content exists yet, so this is a planned-assignment record rather "
        "than content-derived evidence; it is replaced with content-derived "
        "detail when the lesson is authored."
    ),
    "67_quantum_networks::comm.quantum_networks": (
        "Planned lesson for 'Quantum Repeaters and the Quantum Internet', "
        "assigned by the approved M4 architecture (c8f7144). No content "
        "exists yet, so this is a planned-assignment record rather than "
        "content-derived evidence; it is replaced with content-derived detail "
        "when the lesson is authored."
    ),
    "69_quantum_simulation::comm.quantum_simulation": (
        "Planned lesson for 'Quantum Simulation and Many-Body Systems', "
        "assigned by the approved M4 architecture (c8f7144). No content "
        "exists yet, so this is a planned-assignment record rather than "
        "content-derived evidence; it is replaced with content-derived detail "
        "when the lesson is authored."
    ),
    "66_superdense_coding::comm.superdense_coding": (
        "Planned lesson for 'Superdense Coding', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "70_trotterization::comm.trotterization": (
        "Planned lesson for 'Trotterization', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "20_density_matrices::core.density_matrices": (
        "Planned lesson for 'Density Matrices, Mixed States and Partial "
        "Trace', assigned by the approved M4 architecture (c8f7144). No "
        "content exists yet, so this is a planned-assignment record rather "
        "than content-derived evidence; it is replaced with content-derived "
        "detail when the lesson is authored."
    ),
    "21_entanglement_measures::core.entanglement_measures": (
        "Planned lesson for 'Entanglement Entropy and Monogamy', assigned by "
        "the approved M4 architecture (c8f7144). No content exists yet, so "
        "this is a planned-assignment record rather than content-derived "
        "evidence; it is replaced with content-derived detail when the lesson "
        "is authored."
    ),
    "22_no_cloning::core.no_cloning": (
        "Planned lesson for 'No-Cloning and No-Deleting', assigned by the "
        "approved M4 architecture (c8f7144). No content exists yet, so this "
        "is a planned-assignment record rather than content-derived evidence; "
        "it is replaced with content-derived detail when the lesson is "
        "authored."
    ),
    "19_quantum_postulates::core.quantum_postulates": (
        "Planned lesson for 'Quantum Postulates', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "64_benchmarking::hw.benchmarking": (
        "Planned lesson for 'Quantum Benchmarking', assigned by the approved "
        "M4 architecture (c8f7144). No content exists yet, so this is a "
        "planned-assignment record rather than content-derived evidence; it "
        "is replaced with content-derived detail when the lesson is authored."
    ),
    "63_complexity_classes::hw.complexity_classes": (
        "Planned lesson for 'BQP, P, NP and BPP', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "65_quantum_ecosystem::hw.ecosystem": (
        "Planned lesson for 'Quantum Ecosystem: Qiskit, Cirq, PennyLane, "
        "CUDA-Q and Braket', assigned by the approved M4 architecture "
        "(c8f7144). No content exists yet, so this is a planned-assignment "
        "record rather than content-derived evidence; it is replaced with "
        "content-derived detail when the lesson is authored."
    ),
    "59_neutral_atoms::hw.neutral_atoms": (
        "Planned lesson for 'Neutral Atoms', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "62_nisq_limitations::hw.nisq_limitations": (
        "Planned lesson for 'NISQ Limitations', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "58_photonic_systems::hw.photonic_systems": (
        "Planned lesson for 'Photonic Systems', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "61_platform_comparison::hw.platform_comparison": (
        "Planned lesson for 'Calibrated Noise Models and Connectivity "
        "Topologies', assigned by the approved M4 architecture (c8f7144). No "
        "content exists yet, so this is a planned-assignment record rather "
        "than content-derived evidence; it is replaced with content-derived "
        "detail when the lesson is authored."
    ),
    "60_spin_qubits::hw.spin_qubits": (
        "Planned lesson for 'Spin-Based Qubits', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "56_superconducting_qubits::hw.superconducting_qubits": (
        "Planned lesson for 'Superconducting Qubits', assigned by the "
        "approved M4 architecture (c8f7144). No content exists yet, so this "
        "is a planned-assignment record rather than content-derived evidence; "
        "it is replaced with content-derived detail when the lesson is "
        "authored."
    ),
    "57_trapped_ions::hw.trapped_ions": (
        "Planned lesson for 'Trapped Ions', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "14_complex_numbers::math.complex_numbers": (
        "Planned lesson for 'Complex Numbers and Euler's Formula', assigned "
        "by the approved M4 architecture (c8f7144). No content exists yet, so "
        "this is a planned-assignment record rather than content-derived "
        "evidence; it is replaced with content-derived detail when the lesson "
        "is authored."
    ),
    "16_eigen_and_operators::math.eigen_and_operators": (
        "Planned lesson for 'Eigenvalues, Eigenvectors and Operator Classes', "
        "assigned by the approved M4 architecture (c8f7144). No content "
        "exists yet, so this is a planned-assignment record rather than "
        "content-derived evidence; it is replaced with content-derived detail "
        "when the lesson is authored."
    ),
    "18_group_theory::math.group_theory": (
        "Planned lesson for 'Introductory Group Theory', assigned by the "
        "approved M4 architecture (c8f7144). No content exists yet, so this "
        "is a planned-assignment record rather than content-derived evidence; "
        "it is replaced with content-derived detail when the lesson is "
        "authored."
    ),
    "15_linear_algebra::math.linear_algebra": (
        "Planned lesson for 'Vectors, Matrices and Linear Algebra', assigned "
        "by the approved M4 architecture (c8f7144). No content exists yet, so "
        "this is a planned-assignment record rather than content-derived "
        "evidence; it is replaced with content-derived detail when the lesson "
        "is authored."
    ),
    "17_probability_and_statistics::math.probability_and_statistics": (
        "Planned lesson for 'Probability, Expectation and Sampling "
        "Statistics', assigned by the approved M4 architecture (c8f7144). No "
        "content exists yet, so this is a planned-assignment record rather "
        "than content-derived evidence; it is replaced with content-derived "
        "detail when the lesson is authored."
    ),
    "46_approximation_ratios::nisq.approximation_ratios": (
        "Planned lesson for 'Approximation Ratios', assigned by the approved "
        "M4 architecture (c8f7144). No content exists yet, so this is a "
        "planned-assignment record rather than content-derived evidence; it "
        "is replaced with content-derived detail when the lesson is authored."
    ),
    "45_optimization_loops::nisq.optimization": (
        "Planned lesson for 'Classical Optimization Loops and the Parameter- "
        "Shift Rule', assigned by the approved M4 architecture (c8f7144). No "
        "content exists yet, so this is a planned-assignment record rather "
        "than content-derived evidence; it is replaced with content-derived "
        "detail when the lesson is authored."
    ),
    "47_quantum_machine_learning::nisq.qml": (
        "Planned lesson for 'Quantum Machine Learning, Feature Maps and "
        "Kernels', assigned by the approved M4 architecture (c8f7144). No "
        "content exists yet, so this is a planned-assignment record rather "
        "than content-derived evidence; it is replaced with content-derived "
        "detail when the lesson is authored."
    ),
    "23_dirac_notation::qc.dirac_notation": (
        "Planned lesson for 'Dirac Notation and Inner Products', assigned by "
        "the approved M4 architecture (c8f7144). No content exists yet, so "
        "this is a planned-assignment record rather than content-derived "
        "evidence; it is replaced with content-derived detail when the lesson "
        "is authored."
    ),
    "27_reading_results::qc.reading_results": (
        "Planned lesson for 'Understanding Circuits and Finding Results', "
        "assigned by the approved M4 architecture (c8f7144). No content "
        "exists yet, so this is a planned-assignment record rather than "
        "content-derived evidence; it is replaced with content-derived detail "
        "when the lesson is authored."
    ),
    "26_teleportation::qc.teleportation": (
        "Planned lesson for 'Quantum Teleportation', assigned by the approved "
        "M4 architecture (c8f7144). No content exists yet, so this is a "
        "planned-assignment record rather than content-derived evidence; it "
        "is replaced with content-derived detail when the lesson is authored."
    ),
    "24_tensor_products::qc.tensor_products": (
        "Planned lesson for 'Tensor Products and Multi-Qubit Spaces', "
        "assigned by the approved M4 architecture (c8f7144). No content "
        "exists yet, so this is a planned-assignment record rather than "
        "content-derived evidence; it is replaced with content-derived detail "
        "when the lesson is authored."
    ),
    "49_bit_flip_code::qec.bit_flip_code": (
        "Planned lesson for 'Three-Qubit Bit-Flip Code', assigned by the "
        "approved M4 architecture (c8f7144). No content exists yet, so this "
        "is a planned-assignment record rather than content-derived evidence; "
        "it is replaced with content-derived detail when the lesson is "
        "authored."
    ),
    "55_error_mitigation::qec.error_mitigation": (
        "Planned lesson for 'Error Mitigation: ZNE, PEC and Readout "
        "Correction', assigned by the approved M4 architecture (c8f7144). No "
        "content exists yet, so this is a planned-assignment record rather "
        "than content-derived evidence; it is replaced with content-derived "
        "detail when the lesson is authored."
    ),
    "53_logical_physical_qubits::qec.logical_physical": (
        "Planned lesson for 'Logical and Physical Qubits, and Overhead', "
        "assigned by the approved M4 architecture (c8f7144). No content "
        "exists yet, so this is a planned-assignment record rather than "
        "content-derived evidence; it is replaced with content-derived detail "
        "when the lesson is authored."
    ),
    "50_phase_flip_code::qec.phase_flip_code": (
        "Planned lesson for 'Three-Qubit Phase-Flip Code', assigned by the "
        "approved M4 architecture (c8f7144). No content exists yet, so this "
        "is a planned-assignment record rather than content-derived evidence; "
        "it is replaced with content-derived detail when the lesson is "
        "authored."
    ),
    "51_stabilizer_formalism::qec.stabilizer_formalism": (
        "Planned lesson for 'Stabilizer Formalism', assigned by the approved "
        "M4 architecture (c8f7144). No content exists yet, so this is a "
        "planned-assignment record rather than content-derived evidence; it "
        "is replaced with content-derived detail when the lesson is authored."
    ),
    "52_surface_codes::qec.surface_codes": (
        "Planned lesson for 'Surface Codes', assigned by the approved M4 "
        "architecture (c8f7144). No content exists yet, so this is a planned- "
        "assignment record rather than content-derived evidence; it is "
        "replaced with content-derived detail when the lesson is authored."
    ),
    "54_threshold_theorem::qec.threshold_theorem": (
        "Planned lesson for 'Threshold Theorem and Fault Tolerance', assigned "
        "by the approved M4 architecture (c8f7144). No content exists yet, so "
        "this is a planned-assignment record rather than content-derived "
        "evidence; it is replaced with content-derived detail when the lesson "
        "is authored."
    ),
    "28_composer_guide::qiskit.composer": (
        "Planned lesson for 'The Quantum Composer', assigned by the approved "
        "M4 architecture (c8f7144). No content exists yet, so this is a "
        "planned-assignment record rather than content-derived evidence; it "
        "is replaced with content-derived detail when the lesson is authored."
    ),
    "29_primitives::qiskit.estimator": (
        "Planned lesson for 'The Estimator Primitive', assigned by the "
        "approved M4 architecture (c8f7144). No content exists yet, so this "
        "is a planned-assignment record rather than content-derived evidence; "
        "it is replaced with content-derived detail when the lesson is "
        "authored."
    ),
}

#: Mappings whose evidence is indirect and which must not be treated as
#: verified. Kept visible so a reviewer can promote or retire them.
REVIEW_REQUIRED: dict[str, str] = {
    "algorithms::algo.grover": (
        "INFERRED. 'algorithms' is an authored tag on the Grover quiz. It is "
        "mapped to algo.grover only because Grover is currently the sole "
        "algorithms quiz. If a second algorithms assessment is authored, this "
        "inference stops holding and legacy mastery will need re-deriving."
    ),
}


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
        # Tolerant of the optional third rationale element so both the
        # historical two-tuple and the M4 three-tuple shapes work.
        for prereq, kind, *_rationale in topic["prerequisites"]:  # type: ignore[misc]
            out.append((str(topic["id"]), str(prereq), str(kind)))
    return out


def all_prerequisites_with_rationale() -> list[tuple[str, str, str, str]]:
    """Return ``(topic_id, prerequisite_id, kind, rationale)`` rows.

    Separate from :func:`all_prerequisites` so the three-tuple contract that
    the already-applied migration ``a2b3c4d5e6f7`` unpacks is never broken.
    A topic declaring no rationale yields an empty string, so the two shapes
    stay interchangeable.
    """
    out: list[tuple[str, str, str, str]] = []
    for topic in TOPICS:
        for entry in topic["prerequisites"]:  # type: ignore[misc]
            rationale = str(entry[2]) if len(entry) > 2 else ""
            out.append((str(topic["id"]), str(entry[0]), str(entry[1]), rationale))
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
        for prereq, kind, *_rationale in topic["prerequisites"]:  # type: ignore[misc]
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
        {str(t["id"]): [p[0] for p in t["prerequisites"]] for t in TOPICS}  # type: ignore[misc]
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
