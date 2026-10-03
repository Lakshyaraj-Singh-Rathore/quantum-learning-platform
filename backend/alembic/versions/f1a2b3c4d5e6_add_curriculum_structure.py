"""Add the curriculum hierarchy and attach existing lessons to it

Introduces the section -> topic -> lesson structure required by roadmap
section 3.0, and migrates the thirteen existing lessons and all existing
mastery rows onto it.

Design notes that matter for anyone reading this later:

* Every change is additive. No column is dropped, no row is deleted, and no
  stored score is recomputed. ``lessons.order_index`` and ``user_mastery.tag``
  keep their values so that anything not yet migrated keeps working.

* ``lessons.topic_slug`` is nullable. A lesson the curriculum does not claim
  remains a valid lesson; it is simply outside the hierarchy. This is what
  lets content land in the repo before the curriculum assigns it a home.

* ``user_mastery.topic_slug`` is backfilled only where the legacy tag maps
  unambiguously onto a topic (see ``curriculum.LEGACY_TAG_TO_TOPIC``). Rows
  whose tag has no mapping are left NULL rather than guessed at or dropped --
  they remain readable as prior progress. Nothing here fabricates mastery.

Revision ID: f1a2b3c4d5e6
Revises: e9c4a7d31b22
Create Date: 2026-10-03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

"""Frozen copy of the curriculum data as it stood when this migration
was written.

Migrations must not import from live application modules: this file was
originally importing app.curriculum, and later changed the TOPICS key
from "slug" to "id", which broke this migration for anyone running
`alembic upgrade head` from scratch. The data is inlined here so the
migration is self-contained and reproduces its original result.
"""

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


def all_prerequisites() -> list[tuple[str, str, str]]:
    out = []
    for topic in TOPICS:
        for prereq, kind in topic["prerequisites"]:
            out.append((topic["slug"], prereq, kind))
    return out


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e9c4a7d31b22"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return table in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()

    # -- new tables ------------------------------------------------------- #
    if not _has_table("curriculum_sections"):
        op.create_table(
            "curriculum_sections",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=80), unique=True),
            sa.Column("title", sa.String(length=200)),
            sa.Column("position", sa.Integer(), default=0),
            sa.Column("summary", sa.Text(), default=""),
        )

    if not _has_table("curriculum_topics"):
        op.create_table(
            "curriculum_topics",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=80), unique=True),
            sa.Column("title", sa.String(length=200)),
            sa.Column("section_slug", sa.String(length=80), index=True),
            sa.Column("position", sa.Integer(), default=0),
            sa.Column("difficulty", sa.String(length=20), default="beginner"),
            sa.Column("summary", sa.Text(), default=""),
            sa.Column("learning_objectives", sa.Text(), default="[]"),
            sa.ForeignKeyConstraint(["section_slug"], ["curriculum_sections.slug"]),
        )

    if not _has_table("topic_prerequisites"):
        op.create_table(
            "topic_prerequisites",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("topic_slug", sa.String(length=80), index=True),
            sa.Column("prerequisite_slug", sa.String(length=80), index=True),
            sa.Column("kind", sa.String(length=20), default="required"),
            sa.ForeignKeyConstraint(["topic_slug"], ["curriculum_topics.slug"]),
            sa.ForeignKeyConstraint(["prerequisite_slug"], ["curriculum_topics.slug"]),
        )

    # -- new columns ------------------------------------------------------ #
    if not _has_column("lessons", "topic_slug"):
        op.add_column("lessons", sa.Column("topic_slug", sa.String(length=80), nullable=True))
    if not _has_column("lessons", "position"):
        op.add_column("lessons", sa.Column("position", sa.Integer(), nullable=True))
    if not _has_column("lessons", "difficulty"):
        op.add_column("lessons", sa.Column("difficulty", sa.String(length=20), nullable=True))
    if not _has_column("lessons", "learning_objectives"):
        op.add_column("lessons", sa.Column("learning_objectives", sa.Text(), nullable=True))
    if not _has_column("user_mastery", "topic_slug"):
        op.add_column("user_mastery", sa.Column("topic_slug", sa.String(length=80), nullable=True))

    # -- seed sections ---------------------------------------------------- #
    # Idempotent: keyed on slug, so a re-run updates rather than duplicates.
    for section in SECTIONS:
        bind.execute(
            sa.text(
                """
                INSERT INTO curriculum_sections (slug, title, position, summary)
                VALUES (:slug, :title, :position, '')
                ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title,
                                                position = EXCLUDED.position
                """
            ),
            dict(section),
        )

    # -- seed topics ------------------------------------------------------ #
    import json

    for topic in TOPICS:
        bind.execute(
            sa.text(
                """
                INSERT INTO curriculum_topics
                    (slug, title, section_slug, position, difficulty, summary,
                     learning_objectives)
                VALUES (:slug, :title, :section, :position, :difficulty, :summary,
                        :objectives)
                ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title,
                                                section_slug = EXCLUDED.section_slug,
                                                position = EXCLUDED.position,
                                                difficulty = EXCLUDED.difficulty,
                                                summary = EXCLUDED.summary,
                                                learning_objectives = EXCLUDED.learning_objectives
                """
            ),
            {
                "slug": topic["slug"],
                "title": topic["title"],
                "section": topic["section"],
                "position": topic["position"],
                "difficulty": topic["difficulty"],
                "summary": topic["summary"],
                "objectives": json.dumps(topic["objectives"]),
            },
        )

    # -- seed prerequisite edges ------------------------------------------ #
    bind.execute(sa.text("DELETE FROM topic_prerequisites"))
    for topic_slug, prereq_slug, kind in all_prerequisites():
        bind.execute(
            sa.text(
                """
                INSERT INTO topic_prerequisites (topic_slug, prerequisite_slug, kind)
                VALUES (:topic, :prereq, :kind)
                """
            ),
            {"topic": topic_slug, "prereq": prereq_slug, "kind": kind},
        )

    # -- attach existing lessons ------------------------------------------ #
    # Position is the index within the topic's lesson list, so it reflects
    # conceptual order rather than the filename number.
    for topic in TOPICS:
        for index, lesson_slug in enumerate(topic["lessons"]):
            bind.execute(
                sa.text(
                    """
                    UPDATE lessons
                       SET topic_slug = :topic,
                           position = :position,
                           difficulty = :difficulty,
                           learning_objectives = COALESCE(learning_objectives, '[]')
                     WHERE slug = :lesson
                    """
                ),
                {
                    "topic": topic["slug"],
                    "position": index,
                    "difficulty": topic["difficulty"],
                    "lesson": lesson_slug,
                },
            )

    # -- migrate mastery rows onto stable topic identifiers --------------- #
    # Only rows whose tag has an unambiguous mapping are stamped. Each UPDATE
    # sets topic_slug and nothing else: score, attempts and updated_at are
    # left exactly as they were, so no learner's history is rewritten.
    for tag, topic_slug in LEGACY_TAG_TO_TOPIC.items():
        bind.execute(
            sa.text(
                "UPDATE user_mastery SET topic_slug = :topic WHERE tag = :tag"
            ),
            {"topic": topic_slug, "tag": tag},
        )


def downgrade() -> None:
    # Reverse order: drop the columns first, then the tables.
    for table, column in (
        ("user_mastery", "topic_slug"),
        ("lessons", "learning_objectives"),
        ("lessons", "difficulty"),
        ("lessons", "position"),
        ("lessons", "topic_slug"),
    ):
        if _has_column(table, column):
            with op.batch_alter_table(table) as batch:
                batch.drop_column(column)

    for table in ("topic_prerequisites", "curriculum_topics", "curriculum_sections"):
        if _has_table(table):
            op.drop_table(table)
