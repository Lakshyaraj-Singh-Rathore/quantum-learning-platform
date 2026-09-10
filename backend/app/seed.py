"""Bootstrap users, quizzes and coding challenges."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.assessment import CodingChallenge, Quiz, QuizQuestion
from app.models.user import User
from app.security import hash_password

log = logging.getLogger(__name__)


def ensure_user(db: Session, email: str, password: str, role: str, name: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        return user
    user = User(
        email=email,
        password_hash=hash_password(password),
        role=role,
        display_name=name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def seed_users(db: Session) -> None:
    settings = get_settings()
    ensure_user(
        db,
        settings.bootstrap_admin_email,
        settings.bootstrap_admin_password,
        "admin",
        "Platform Admin",
    )
    ensure_user(
        db,
        settings.bootstrap_instructor_email,
        settings.bootstrap_instructor_password,
        "instructor",
        "Course Instructor",
    )


QUIZZES = [
    {
        "slug": "basics",
        "title": "Qubits, Gates and Superposition",
        "tags": ["qubit", "gates"],
        "questions": [
            {
                "prompt": "Applying H to |0> produces which state?",
                "qtype": "mcq",
                "options": ["|0>", "|1>", "(|0> + |1>)/sqrt(2)", "(|0> - |1>)/sqrt(2)"],
                "answer": "(|0> + |1>)/sqrt(2)",
                "explanation": "H maps |0> to the equal superposition with a positive phase.",
                "tags": ["gates", "qubit"],
            },
            {
                "prompt": "Which gate flips |0> to |1>?",
                "qtype": "mcq",
                "options": ["X", "Z", "S", "T"],
                "answer": "X",
                "explanation": "X is the quantum NOT gate.",
                "tags": ["gates"],
            },
            {
                "prompt": "How many amplitudes describe an n-qubit pure state? (expression in n)",
                "qtype": "short",
                "options": [],
                "answer": "2^n|2**n|two to the n",
                "explanation": "The state vector has 2^n complex amplitudes.",
                "tags": ["qubit"],
            },
        ],
    },
    {
        "slug": "entanglement-measurement",
        "title": "Entanglement and Measurement",
        "tags": ["entanglement", "measurement"],
        "questions": [
            {
                "prompt": "Measuring the Bell state (|00> + |11>)/sqrt(2) can yield which outcomes?",
                "qtype": "mcq",
                "options": ["00 or 11", "01 or 10", "00 only", "any of the four"],
                "answer": "00 or 11",
                "explanation": "The Bell state is perfectly correlated.",
                "tags": ["entanglement", "measurement"],
            },
            {
                "prompt": "Which gate pair creates a Bell state from |00>?",
                "qtype": "mcq",
                "options": ["H then CNOT", "X then Z", "CNOT then H", "two Hadamards"],
                "answer": "H then CNOT",
                "explanation": "H on the control, then CNOT onto the target.",
                "tags": ["entanglement"],
            },
            {
                "prompt": "What does a mid-circuit measurement enable?",
                "qtype": "mcq",
                "options": [
                    "Classical feedback / dynamic circuits",
                    "Faster gates",
                    "More qubits",
                    "Removal of noise",
                ],
                "answer": "Classical feedback / dynamic circuits",
                "explanation": "Its outcome can steer later operations.",
                "tags": ["measurement", "dynamic"],
            },
        ],
    },
    {
        "slug": "quantum-noise",
        "title": "Quantum Noise and Decoherence",
        "tags": ["noise", "decoherence"],
        "questions": [
            {
                "prompt": "T1 describes which process?",
                "qtype": "mcq",
                "options": [
                    "Energy relaxation: |1> decaying to |0>",
                    "Loss of phase coherence only",
                    "Misreporting a measured bit",
                    "Crosstalk between neighbouring qubits",
                ],
                "answer": "Energy relaxation: |1> decaying to |0>",
                "explanation": (
                    "T1 is amplitude damping. The excited state loses energy to "
                    "the environment, so it is directional: it pushes toward |0>."
                ),
                "tags": ["noise"],
            },
            {
                "prompt": "Why can T2 never exceed 2*T1?",
                "qtype": "mcq",
                "options": [
                    "Because energy relaxation also destroys phase information",
                    "Because T2 is measured in different units",
                    "It is only a convention, not a physical limit",
                    "Because readout error dominates at long times",
                ],
                "answer": "Because energy relaxation also destroys phase information",
                "explanation": (
                    "A T1 event necessarily randomises phase, so dephasing can "
                    "never be slower than the bound set by relaxation. The "
                    "platform clamps T2 to 2*T1 and warns you."
                ),
                "tags": ["noise"],
            },
            {
                "prompt": (
                    "You set T1 and T2 extremely high and readout error to 20%. "
                    "What happens to state fidelity?"
                ),
                "qtype": "mcq",
                "options": [
                    "It stays near 1.000; only the counts are corrupted",
                    "It drops to about 0.80",
                    "It drops to 0.50",
                    "Fidelity cannot be computed with readout error",
                ],
                "answer": "It stays near 1.000; only the counts are corrupted",
                "explanation": (
                    "Readout error is a measurement fault, not a channel acting "
                    "on the state. The state was correct; the reported bit was "
                    "not. That is why the platform excludes readout when "
                    "computing state fidelity."
                ),
                "tags": ["noise", "measurement"],
            },
            {
                "prompt": "Purity Tr(rho^2) falls below 1. What does that mean?",
                "qtype": "mcq",
                "options": [
                    "The state has become a statistical mixture (decohered)",
                    "The circuit used too many shots",
                    "The state is entangled",
                    "A gate was applied incorrectly",
                ],
                "answer": "The state has become a statistical mixture (decohered)",
                "explanation": (
                    "Purity 1 means a definite pure state. Lower means the "
                    "register is a mixture, which is the signature of "
                    "decoherence."
                ),
                "tags": ["noise"],
            },
            {
                "prompt": (
                    "Why do Z, S, T and RZ pick up no thermal error in this "
                    "simulation?"
                ),
                "qtype": "mcq",
                "options": [
                    "They are virtual gates: a phase-frame change taking zero time",
                    "They are too small to matter",
                    "It is a simplification with no hardware basis",
                    "They are applied after the noise model runs",
                ],
                "answer": "They are virtual gates: a phase-frame change taking zero time",
                "explanation": (
                    "Hardware implements Z-type rotations by redefining the "
                    "phase reference for later pulses. No pulse is emitted, so "
                    "no decoherence accumulates."
                ),
                "tags": ["noise", "gates"],
            },
            {
                "prompt": (
                    "Name the noise channel that models |1> decaying to |0>. "
                    "(two words)"
                ),
                "qtype": "short",
                "options": [],
                "answer": "amplitude damping|amplitude-damping",
                "explanation": "Amplitude damping is the channel form of T1.",
                "tags": ["noise"],
            },
        ],
    },
    {
        "slug": "bell-states-quiz",
        "title": "The Four Bell States",
        "tags": ["entanglement"],
        "questions": [
            {
                "prompt": (
                    "Phi+ and Phi- give identical histograms. What distinguishes "
                    "them?"
                ),
                "qtype": "mcq",
                "options": [
                    "The relative phase on the |11> term",
                    "The number of shots required",
                    "Phi- is not physically realisable",
                    "Nothing; they are the same state",
                ],
                "answer": "The relative phase on the |11> term",
                "explanation": (
                    "They are orthogonal states with the same measurement "
                    "statistics. Use the phase disk or phase table to tell them "
                    "apart, or undo the Bell circuit."
                ),
                "tags": ["entanglement"],
            },
            {
                "prompt": "Measuring Psi+ = (|01> + |10>)/sqrt(2) can give:",
                "qtype": "mcq",
                "options": [
                    "01 or 10 only",
                    "00 or 11 only",
                    "any of the four outcomes",
                    "always 01",
                ],
                "answer": "01 or 10 only",
                "explanation": "Psi states are anti-correlated: the bits always differ.",
                "tags": ["entanglement"],
            },
            {
                "prompt": (
                    "Why is each qubit of a Bell pair shown with a zero-length "
                    "Bloch vector?"
                ),
                "qtype": "mcq",
                "options": [
                    "Its reduced state is maximally mixed, so it has no state of its own",
                    "The visualisation is broken",
                    "The qubit was measured",
                    "Bloch vectors are undefined for two qubits",
                ],
                "answer": (
                    "Its reduced state is maximally mixed, so it has no state of its own"
                ),
                "explanation": (
                    "Tracing out the partner leaves I/2. All the information is "
                    "in the correlation, not in either qubit."
                ),
                "tags": ["entanglement"],
            },
        ],
    },
    {
        "slug": "grover",
        "title": "Grover Search",
        "tags": ["grover", "algorithms"],
        "questions": [
            {
                "prompt": "Grover search on N items needs roughly how many iterations?",
                "qtype": "mcq",
                "options": ["O(N)", "O(sqrt(N))", "O(log N)", "O(1)"],
                "answer": "O(sqrt(N))",
                "explanation": "Grover gives a quadratic speed-up.",
                "tags": ["grover"],
            },
            {
                "prompt": "What does the Grover oracle do to the marked state?",
                "qtype": "mcq",
                "options": [
                    "Flips its phase",
                    "Measures it",
                    "Deletes it",
                    "Doubles its amplitude",
                ],
                "answer": "Flips its phase",
                "explanation": "The oracle marks the solution with a phase flip.",
                "tags": ["grover"],
            },
        ],
    },
]


CHALLENGES = [
    {
        "slug": "bell-state",
        "title": "Build a Bell State",
        "prompt": (
            "Create the entangled state (|00> + |11>)/sqrt(2) on two qubits, then measure "
            "both qubits. You should see roughly 50% `00` and 50% `11` and nothing else."
        ),
        "allowed_gates": ["h", "x", "cx", "measure"],
        "target": {
            "type": "counts",
            "counts": {"00": 0.5, "11": 0.5},
            # A 50/50 split carries real shot noise: at 1024 shots the total
            # variation distance of a *correct* Bell state exceeds 0.12 often
            # enough that ~12% of correct submissions were graded as failures.
            # 0.25 keeps that below 0.2% while still rejecting wrong answers
            # (a plain |00> circuit has tvd 0.5 and still scores 0).
            "tolerance": 0.25,
            "shots": 1024,
        },
        "constraints": {"max_qubits": 2, "max_depth": 6, "required_gates": ["h"]},
        "tags": ["entanglement", "gates"],
        "is_dynamic": False,
    },
    {
        "slug": "grover-2qubit",
        "title": "Grover Search for |11>",
        "prompt": (
            "Implement one Grover iteration on two qubits so the marked state |11> is found "
            "with near-certainty. Hint: uniform superposition, phase oracle (CZ), then the "
            "diffuser. A controlled-Z can be built from H, CX, H on the target."
        ),
        "allowed_gates": ["h", "x", "z", "cx", "cz", "measure"],
        "target": {
            "type": "counts",
            "counts": {"11": 1.0},
            "tolerance": 0.15,
            "shots": 1024,
        },
        "constraints": {"max_qubits": 2, "max_depth": 20, "required_gates": ["h"]},
        "tags": ["grover", "algorithms"],
        "is_dynamic": False,
    },
    {
        "slug": "dynamic-reset-loop",
        "title": "Dynamic Feedback: Force Qubit 0 to |0>",
        "prompt": (
            "Use a mid-circuit measurement plus runtime control flow to guarantee qubit 0 "
            "ends in |0>. Put q0 in superposition, measure it into c[0], and use a while "
            "loop (capped at 32 iterations) with an if/else block so that whenever c[0] is 1 "
            "you flip and re-measure. Every shot should end with c[0] = 0."
        ),
        "allowed_gates": ["h", "x", "id", "measure"],
        "target": {
            "type": "counts",
            "counts": {"00": 1.0},
            "tolerance": 0.05,
            "shots": 256,
        },
        "constraints": {
            "max_qubits": 2,
            "must_be_dynamic": True,
            "required_gates": ["h"],
        },
        "tags": ["dynamic", "measurement"],
        "is_dynamic": True,
    },
]


def seed_quizzes(db: Session) -> None:
    for spec in QUIZZES:
        quiz = db.scalar(select(Quiz).where(Quiz.slug == spec["slug"]))
        if quiz is not None:
            continue
        quiz = Quiz(slug=spec["slug"], title=spec["title"], tags=spec["tags"])
        db.add(quiz)
        db.flush()
        for question in spec["questions"]:
            db.add(QuizQuestion(quiz_id=quiz.id, **question))
    db.commit()


def seed_challenges(db: Session) -> None:
    for spec in CHALLENGES:
        existing = db.scalar(select(CodingChallenge).where(CodingChallenge.slug == spec["slug"]))
        if existing is not None:
            continue
        db.add(CodingChallenge(**spec))
    db.commit()


def seed_all(db: Session) -> dict[str, int]:
    seed_users(db)
    seed_quizzes(db)
    seed_challenges(db)
    log.info("seed complete")
    return {"quizzes": len(QUIZZES), "challenges": len(CHALLENGES)}


__all__ = ["seed_all", "seed_users", "seed_quizzes", "seed_challenges", "ensure_user"]
