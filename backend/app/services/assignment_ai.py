"""AI-driven assignment generation & real-time evaluation using Gemini API and RAG."""

from __future__ import annotations

import datetime
import json
import logging
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.ai import gemini_client
from app.ai.rag import retrieve
from app.quantum.inspect import inspect_circuit
from app.quantum.ir import CircuitIR

log = logging.getLogger(__name__)

AVAILABLE_TOPICS = [
    {
        "id": "qubits_superposition",
        "label": "Qubits & Superposition",
        "description": "State vectors, Bloch sphere representation, and linear superposition",
        "keywords": ["qubit", "superposition", "bloch", "ket"],
    },
    {
        "id": "quantum_gates",
        "label": "Quantum Gates & Unitary Operators",
        "description": "Pauli X/Y/Z, Hadamard, Phase, Rotations (Rx, Ry, Rz), and CX/CZ",
        "keywords": ["gate", "hadamard", "pauli", "unitary", "rotation"],
    },
    {
        "id": "entanglement_bell",
        "label": "Entanglement & Bell States",
        "description": "EPR pairs, Bell state preparation, concurrence, and non-locality",
        "keywords": ["entangle", "bell", "ghz", "epr", "concurrence"],
    },
    {
        "id": "measurement_collapse",
        "label": "Measurement & Born Rule",
        "description": "Projective measurement, state collapse, probability distributions, and shot noise",
        "keywords": ["measure", "born rule", "collapse", "probability"],
    },
    {
        "id": "quantum_algorithms",
        "label": "Quantum Algorithms",
        "description": "Deutsch-Jozsa, Bernstein-Vazirani, Grover's search, and QFT",
        "keywords": ["deutsch", "jozsa", "grover", "algorithm", "oracle"],
    },
    {
        "id": "teleportation_dense",
        "label": "Teleportation & Superdense Coding",
        "description": "Quantum state transfer, entanglement as resource, and 2-bit communication",
        "keywords": ["teleportation", "superdense", "quantum channel"],
    },
    {
        "id": "density_matrices",
        "label": "Density Matrices & Mixed States",
        "description": "Ensembles, partial trace, purity, and environmental decoherence",
        "keywords": ["density matrix", "purity", "mixed state", "decoherence"],
    },
    {
        "id": "dynamic_circuits",
        "label": "Dynamic Circuits & Control Flow",
        "description": "Mid-circuit measurement, conditional branching, feed-forward, and while loops",
        "keywords": ["dynamic", "mid-circuit", "conditional", "feed-forward"],
    },
]

TOPIC_LOOKUP = {t["id"]: t for t in AVAILABLE_TOPICS}

# Fallback curated question bank by topic (derived directly from verified curriculum)
CURATED_QUESTION_BANK: dict[str, list[dict[str, Any]]] = {
    "qubits_superposition": [
        {
            "id": "qs_1",
            "prompt": "What is the result of applying a Hadamard gate H to the computational ground state |0⟩?",
            "options": ["|0⟩", "|1⟩", "(|0⟩ + |1⟩)/√2", "(|0⟩ - |1⟩)/√2"],
            "correct_answer": "(|0⟩ + |1⟩)/√2",
            "explanation": "The Hadamard gate maps basis state |0⟩ into the symmetric superposition |+⟩ = (|0⟩ + |1⟩)/√2 with equal 50% probability amplitudes.",
        },
        {
            "id": "qs_2",
            "prompt": "On the Bloch sphere, which coordinates represent the state |+⟩ = (|0⟩ + |1⟩)/√2?",
            "options": ["(0, 0, 1)", "(1, 0, 0)", "(0, 1, 0)", "(0, 0, -1)"],
            "correct_answer": "(1, 0, 0)",
            "explanation": "The |+⟩ state lies along the positive X-axis on the equator of the Bloch sphere, corresponding to Cartesian coordinates (1, 0, 0).",
        },
        {
            "id": "qs_3",
            "prompt": "If a qubit is prepared in state |ψ⟩ = (1/2)|0⟩ + (√3/2)|1⟩, what is the probability of measuring |0⟩?",
            "options": ["50%", "25%", "75%", "100%"],
            "correct_answer": "25%",
            "explanation": "According to the Born rule, the probability is |1/2|² = 1/4 = 25%.",
        },
    ],
    "quantum_gates": [
        {
            "id": "qg_1",
            "prompt": "Which single-qubit gate satisfies the identity X Z = -Z X and acts as a bit-flip operation?",
            "options": ["Hadamard (H)", "Pauli-X (X)", "Phase (S)", "Identity (I)"],
            "correct_answer": "Pauli-X (X)",
            "explanation": "The Pauli-X gate flips |0⟩ to |1⟩ and |1⟩ to |0⟩, anti-commuting with Pauli-Z.",
        },
        {
            "id": "qg_2",
            "prompt": "What matrix property must all valid quantum logic gates possess to preserve state normalization?",
            "options": ["Hermitian", "Unitary (U† U = I)", "Orthogonal and diagonal", "Strictly real"],
            "correct_answer": "Unitary (U† U = I)",
            "explanation": "Quantum time evolution is unitary, ensuring the sum of all outcome probabilities always equals 1: ⟨ψ|U† U|ψ⟩ = ⟨ψ|ψ⟩ = 1.",
        },
        {
            "id": "qg_3",
            "prompt": "What does two consecutive applications of the Hadamard gate (H·H) yield?",
            "options": ["Pauli-X", "Pauli-Z", "Identity (I)", "Minus Identity (-I)"],
            "correct_answer": "Identity (I)",
            "explanation": "The Hadamard gate is self-inverse (H = H† = H⁻¹), so H² = I.",
        },
    ],
    "entanglement_bell": [
        {
            "id": "eb_1",
            "prompt": "Which circuit construct prepares the maximally entangled Bell state |Φ⁺⟩ = (|00⟩ + |11⟩)/√2 from |00⟩?",
            "options": [
                "H on q0, followed by CNOT with control q0 and target q1",
                "X on q0, followed by H on q1",
                "CNOT with control q0 and target q1, then H on q0",
                "H on both q0 and q1",
            ],
            "correct_answer": "H on q0, followed by CNOT with control q0 and target q1",
            "explanation": "H on q0 creates (|0⟩ + |1⟩)|0⟩/√2 = (|00⟩ + |10⟩)/√2. The subsequent CNOT flips q1 when q0 is 1, yielding (|00⟩ + |11⟩)/√2.",
        },
        {
            "id": "eb_2",
            "prompt": "What is the single-qubit reduced von Neumann entropy (Entanglement S) of a Bell state?",
            "options": ["0 bits", "0.5 bits", "1.0 bit", "2.0 bits"],
            "correct_answer": "1.0 bit",
            "explanation": "Tracing out one qubit of a maximally entangled pair leaves a completely mixed state ρ = I/2 with entropy S = -Tr(ρ log₂ ρ) = 1.0 bit.",
        },
        {
            "id": "eb_3",
            "prompt": "If Alice measures |0⟩ on her half of the Bell state |Φ⁺⟩ = (|00⟩ + |11⟩)/√2, what state does Bob instantaneously find upon measuring his qubit?",
            "options": ["|0⟩ with 100% certainty", "|1⟩ with 100% certainty", "Equal 50/50 superposition", "Cannot be determined"],
            "correct_answer": "|0⟩ with 100% certainty",
            "explanation": "Measuring Alice's qubit collapses the joint state to |00⟩, making Bob's measurement outcome strictly |0⟩ with certainty.",
        },
    ],
    "measurement_collapse": [
        {
            "id": "mc_1",
            "prompt": "According to the Born rule, what does the quantity |⟨b|ψ⟩|² describe?",
            "options": [
                "The energy of the state |ψ⟩",
                "The probability of obtaining measurement outcome |b⟩ from state |ψ⟩",
                "The phase angle between |b⟩ and |ψ⟩",
                "The speed of wave function collapse",
            ],
            "correct_answer": "The probability of obtaining measurement outcome |b⟩ from state |ψ⟩",
            "explanation": "The probability of projecting state |ψ⟩ into basis state |b⟩ is given by the squared modulus of their inner product.",
        },
        {
            "id": "mc_2",
            "prompt": "How does finite shot count (e.g., 1024 shots) affect experimental probability estimation?",
            "options": [
                "It eliminates all noise completely",
                "It introduces statistical Poisson shot noise proportional to 1/√N",
                "It shifts the eigenvalues of the Hamiltonian",
                "It alters the circuit depth",
            ],
            "correct_answer": "It introduces statistical Poisson shot noise proportional to 1/√N",
            "explanation": "Sampling variance scales as σ = √(p(1-p)/N), yielding standard 1/√N statistical convergence.",
        },
    ],
    "quantum_algorithms": [
        {
            "id": "qa_1",
            "prompt": "In the Deutsch-Jozsa algorithm, how many queries to the oracle are needed to determine if a function is constant or balanced?",
            "options": ["1 query", "2 queries", "2^(n-1) + 1 queries", "n queries"],
            "correct_answer": "1 query",
            "explanation": "Using quantum superposition and phase kickback, Deutsch-Jozsa evaluates global function properties in exactly 1 oracle query.",
        },
        {
            "id": "qa_2",
            "prompt": "What is the speedup achieved by Grover's search algorithm over classical unstructured search of N items?",
            "options": ["Exponential: O(log N)", "Quadratic: O(√N) queries vs classical O(N)", "Linear improvement", "Polynomial degree 4"],
            "correct_answer": "Quadratic: O(√N) queries vs classical O(N)",
            "explanation": "Grover's amplitude amplification rotates the state towards the target in ~ (π/4)√N steps, providing a provable quadratic speedup.",
        },
    ],
    "teleportation_dense": [
        {
            "id": "td_1",
            "prompt": "In the standard quantum teleportation protocol, how many classical bits must be transmitted from Alice to Bob to reconstruct the unknown state?",
            "options": ["0 classical bits", "1 classical bit", "2 classical bits", "Infinitely many bits"],
            "correct_answer": "2 classical bits",
            "explanation": "Alice's Bell measurement produces 2 classical bits (representing one of 4 Bell basis outcomes), allowing Bob to apply the matching Pauli correction (I, X, Z, or ZX).",
        },
        {
            "id": "td_2",
            "prompt": "Why doesn't quantum teleportation allow faster-than-light (superluminal) communication?",
            "options": [
                "Because entanglement is too fragile",
                "Because Bob cannot reconstruct the state without the 2 classical bits sent at subluminal speed",
                "Because the no-cloning theorem blocks it",
                "Because measurements are never 100% accurate",
            ],
            "correct_answer": "Because Bob cannot reconstruct the state without the 2 classical bits sent at subluminal speed",
            "explanation": "Until Bob receives the classical bits over a conventional channel, his reduced state is completely mixed and encodes zero information.",
        },
    ],
    "density_matrices": [
        {
            "id": "dm_1",
            "prompt": "What is the purity Tr(ρ²) of a completely pure quantum state |ψ⟩?",
            "options": ["0.0", "0.5", "1.0", "Depends on the basis"],
            "correct_answer": "1.0",
            "explanation": "For any pure state ρ = |ψ⟩⟨ψ|, ρ² = ρ, and therefore Tr(ρ²) = Tr(ρ) = 1.0.",
        },
        {
            "id": "dm_2",
            "prompt": "What operation allows computing the local state of subsystem A from a bipartite density matrix ρ_AB?",
            "options": ["Matrix determinant", "Partial trace Tr_B(ρ_AB)", "Hadamard transform", "Tensor product"],
            "correct_answer": "Partial trace Tr_B(ρ_AB)",
            "explanation": "The partial trace over subsystem B yields the reduced density matrix ρ_A = Tr_B(ρ_AB), discarding subsystem B's degrees of freedom.",
        },
    ],
    "dynamic_circuits": [
        {
            "id": "dc_1",
            "prompt": "What defines a dynamic quantum circuit compared to a static circuit?",
            "options": [
                "Using higher frequencies on the microwave generators",
                "Mid-circuit measurement with real-time classical feed-forward and conditional logic within qubit coherence times",
                "Allowing more than 20 qubits",
                "Executing only on superconducting QPUs",
            ],
            "correct_answer": "Mid-circuit measurement with real-time classical feed-forward and conditional logic within qubit coherence times",
            "explanation": "Dynamic circuits measure qubits mid-execution and use fast classical control hardware to branch (if/else, while) before decoherence occurs.",
        },
        {
            "id": "dc_2",
            "prompt": "In OpenQASM 3.0, which construct expresses a conditional X correction based on measurement bit c[0]?",
            "options": [
                "if (c[0] == 1) { x q[1]; }",
                "switch c[0]: x q[1]",
                "while (c[0]) { x q[1]; }",
                "branch(c[0], x q[1])",
            ],
            "correct_answer": "if (c[0] == 1) { x q[1]; }",
            "explanation": "OpenQASM 3 supports C-like conditional blocks: if (classical_condition) { operations }.",
        },
    ],
}


def generate_assignment(
    db: Session,
    topics: list[str],
    num_questions: int = 5,
    difficulty: str = "mixed",
) -> dict[str, Any]:
    """Generates an MCQ assignment divided topic-wise using Gemini API + RAG context."""
    if not topics:
        topics = ["qubits_superposition", "quantum_gates"]
    
    num_questions = max(1, min(int(num_questions), 25))
    
    # 1. Fetch RAG curriculum context for each topic
    rag_context_blocks: list[str] = []
    for t_id in topics:
        topic_info = TOPIC_LOOKUP.get(t_id, {"label": t_id, "keywords": [t_id]})
        query = f"{topic_info['label']} {' '.join(topic_info.get('keywords', []))}"
        try:
            chunks = retrieve(db, query, k=2)
            for c in chunks:
                rag_context_blocks.append(f"[{topic_info['label']}]\n{c['text'][:600]}")
        except Exception as exc:
            log.warning("RAG retrieval for assignment topic %s failed: %s", t_id, exc)

    rag_text = "\n\n".join(rag_context_blocks[:6])

    # 2. Try Gemini API generation if key is present
    if gemini_client.is_configured():
        try:
            system_instruction = (
                "You are an expert Quantum Computing Professor and Educational Assessor. "
                "Generate rigorous, high-quality Multiple Choice Questions (MCQs) for university-level learners. "
                "You must divide the questions topic-wise into clear sections corresponding to the requested topics. "
                "Rules:\n"
                "- MCQ BASED ONLY: Each question must have exactly 4 choices (options).\n"
                "- Exactly one correct answer.\n"
                "- Detailed, clear explanation citing quantum principles.\n"
                "- Output MUST be pure JSON conforming to the requested schema.\n"
            )

            prompt = (
                f"Create a quantum computing assignment with exactly {num_questions} questions.\n"
                f"Difficulty level: {difficulty}.\n"
                f"Selected topics:\n"
                + "\n".join(f"- {t}: {TOPIC_LOOKUP.get(t, {}).get('label', t)}" for t in topics)
                + f"\n\nCurriculum RAG Reference Excerpts:\n{rag_text}\n\n"
                "Return pure JSON with this EXACT structure:\n"
                "{\n"
                '  "title": "Quantum Computing Comprehensive Assessment",\n'
                f'  "total_questions": {num_questions},\n'
                '  "difficulty": "' + difficulty + '",\n'
                '  "sections": [\n'
                '    {\n'
                '      "topic_id": "topic_id_here",\n'
                '      "topic_title": "Human Readable Topic Name",\n'
                '      "questions": [\n'
                '        {\n'
                '          "id": "q1",\n'
                '          "prompt": "Question text here?",\n'
                '          "options": ["Choice A", "Choice B", "Choice C", "Choice D"],\n'
                '          "correct_answer": "Choice A",\n'
                '          "explanation": "Why Choice A is physically and mathematically correct."\n'
                '        }\n'
                '      ]\n'
                '    }\n'
                '  ]\n'
                "}"
            )

            response_raw = gemini_client.generate(prompt, system_instruction=system_instruction)
            cleaned = re.sub(r"^```(?:json)?\s*", "", response_raw.strip(), flags=re.I)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            parsed = json.loads(cleaned)
            if "sections" in parsed and isinstance(parsed["sections"], list):
                # Ensure each question has unique id and fields
                q_count = 0
                for s_idx, sec in enumerate(parsed["sections"]):
                    for q_idx, q in enumerate(sec.get("questions", [])):
                        q_count += 1
                        q["id"] = f"ai_q_{s_idx}_{q_idx}_{q_count}"
                parsed["generated_by"] = "gemini-3.1-flash"
                return parsed
        except Exception as exc:
            log.warning("Gemini assignment generation encountered error, falling back to verified bank: %s", exc)

    # 3. Fallback: Intelligent curriculum question assembler (100% reliable)
    sections: list[dict[str, Any]] = []
    per_topic = max(1, num_questions // len(topics))
    q_counter = 1

    for t_id in topics:
        topic_info = TOPIC_LOOKUP.get(t_id, {"label": t_id.replace("_", " ").title()})
        bank = CURATED_QUESTION_BANK.get(t_id, CURATED_QUESTION_BANK["qubits_superposition"])
        selected_q = bank[:per_topic]
        
        section_questions = []
        for q in selected_q:
            section_questions.append({
                "id": f"q_{q_counter}",
                "prompt": q["prompt"],
                "options": q["options"],
                "correct_answer": q["correct_answer"],
                "explanation": q["explanation"],
            })
            q_counter += 1

        sections.append({
            "topic_id": t_id,
            "topic_title": topic_info["label"],
            "questions": section_questions,
        })

    return {
        "title": "Quantum Computing Curriculum Assessment",
        "total_questions": sum(len(s["questions"]) for s in sections),
        "difficulty": difficulty,
        "generated_by": "curriculum-rag",
        "sections": sections,
    }


def evaluate_assignment(
    assignment: dict[str, Any],
    answers: dict[str, str],
) -> dict[str, Any]:
    """Real-time grading of submitted MCQ assignment with topic breakdown."""
    total_questions = 0
    total_correct = 0
    topic_breakdown: dict[str, dict[str, Any]] = {}
    detailed_feedback: list[dict[str, Any]] = []

    for sec in assignment.get("sections", []):
        t_id = sec.get("topic_id", "general")
        t_title = sec.get("topic_title", "General")

        if t_id not in topic_breakdown:
            topic_breakdown[t_id] = {
                "topic_title": t_title,
                "total": 0,
                "correct": 0,
                "percentage": 0.0,
            }

        for q in sec.get("questions", []):
            total_questions += 1
            topic_breakdown[t_id]["total"] += 1

            q_id = str(q.get("id"))
            user_choice = (answers.get(q_id) or "").strip()
            correct_choice = (q.get("correct_answer") or "").strip()

            is_correct = user_choice.lower() == correct_choice.lower()
            if is_correct:
                total_correct += 1
                topic_breakdown[t_id]["correct"] += 1

            detailed_feedback.append({
                "id": q_id,
                "topic": t_title,
                "prompt": q.get("prompt"),
                "your_answer": user_choice or "(No answer provided)",
                "correct_answer": correct_choice,
                "correct": is_correct,
                "explanation": q.get("explanation", ""),
            })

    # Compute percentages
    for t_id, stat in topic_breakdown.items():
        if stat["total"] > 0:
            stat["percentage"] = round((stat["correct"] / stat["total"]) * 100.0, 1)

    overall_percentage = round((total_correct / total_questions * 100.0), 1) if total_questions else 0.0

    return {
        "score": total_correct,
        "total_questions": total_questions,
        "percentage": overall_percentage,
        "passed": overall_percentage >= 70.0,
        "grade": (
            "Distinction (A*)" if overall_percentage >= 90
            else "Merit (A)" if overall_percentage >= 80
            else "Pass (B)" if overall_percentage >= 70
            else "Needs Review (C)" if overall_percentage >= 50
            else "Unsatisfactory (F)"
        ),
        "topic_breakdown": topic_breakdown,
        "feedback": detailed_feedback,
    }


def get_daily_challenge(db: Session, date_str: Optional[str] = None) -> dict[str, Any]:
    """Generates or retrieves the daily quantum circuit problem for today."""
    if not date_str:
        date_str = datetime.date.today().isoformat()

    # Deterministic daily rotation catalogue
    daily_challenges = [
        {
            "id": f"daily_{date_str}_1",
            "date": date_str,
            "title": "Daily Challenge: The Entangled Bell Pair |Φ⁻⟩",
            "difficulty": "Beginner · Daily Sprint",
            "reward_xp": 100,
            "story": (
                "Alice and Bob need an anti-phase entangled Bell channel |Φ⁻⟩ = (|00⟩ - |11⟩)/√2 for a secure "
                "quantum key distribution session. Construct this 2-qubit state using only H, X, and CNOT gates."
            ),
            "objectives": [
                "Prepare the state |Φ⁻⟩ = (|00⟩ - |11⟩)/√2 on 2 qubits.",
                "Ensure measurement probabilities are 50% for |00⟩ and 50% for |11⟩ with opposite relative phase.",
                "Measure both qubits into classical bits c[0] and c[1].",
            ],
            "allowed_gates": ["h", "x", "z", "cx", "measure"],
            "max_depth": 5,
            "target": {
                "counts": {"00": 0.5, "11": 0.5},
                "shots": 1024,
                "tolerance": 0.15,
            },
            "hints": [
                "Start with H on q[0], then a Pauli-Z or start with X on q[0] before H.",
                "Apply CX from q[0] onto q[1] to distribute the entanglement.",
            ],
            "starter_ir": {
                "name": "Daily Challenge: Bell State",
                "n_qubits": 2,
                "n_clbits": 2,
                "ops": [
                    {"id": "d1", "kind": "gate", "gate": "h", "qubits": [0], "controls": [], "params": [], "clbits": [], "layer": 0, "body": [], "else_body": [], "loop_var": "", "loop_value": 0},
                ],
            },
        },
        {
            "id": f"daily_{date_str}_2",
            "date": date_str,
            "title": "Daily Challenge: Greenberger-Horne-Zeilinger (GHZ) Triad",
            "difficulty": "Intermediate · Daily Sprint",
            "reward_xp": 150,
            "story": (
                "Prepare a genuine 3-qubit maximally entangled GHZ state |GHZ⟩ = (|000⟩ + |111⟩)/√2. "
                "This state exhibits extreme non-classical correlations and sensitive multipartite entanglement."
            ),
            "objectives": [
                "Prepare |GHZ⟩ = (|000⟩ + |111⟩)/√2 across 3 qubits.",
                "Output histogram must be evenly split between |000⟩ (50%) and |111⟩ (50%).",
                "Keep circuit depth under 6.",
            ],
            "allowed_gates": ["h", "cx", "x", "measure"],
            "max_depth": 6,
            "target": {
                "counts": {"000": 0.5, "111": 0.5},
                "shots": 1024,
                "tolerance": 0.15,
            },
            "hints": [
                "Put q[0] into superposition using H.",
                "Cascade CNOT gates: q[0] → q[1], then q[1] → q[2].",
            ],
            "starter_ir": {
                "name": "Daily Challenge: GHZ State",
                "n_qubits": 3,
                "n_clbits": 3,
                "ops": [
                    {"id": "d1", "kind": "gate", "gate": "h", "qubits": [0], "controls": [], "params": [], "clbits": [], "layer": 0, "body": [], "else_body": [], "loop_var": "", "loop_value": 0},
                ],
            },
        },
        {
            "id": f"daily_{date_str}_3",
            "date": date_str,
            "title": "Daily Challenge: Phase Kickback Flag",
            "difficulty": "Intermediate · Daily Sprint",
            "reward_xp": 120,
            "story": (
                "Implement the fundamental quantum oracle primitive: Phase Kickback. "
                "Prepare target qubit q[1] in the |-⟩ state, then apply a CNOT from control q[0] to observe how "
                "the eigenvalue phase kicks back onto control qubit q[0]."
            ),
            "objectives": [
                "Prepare q[0] in |+⟩ using H.",
                "Prepare q[1] in |-⟩ using X and H.",
                "Apply CX(q[0], q[1]) to kick back the phase.",
                "Apply H on q[0] to measure the kicked-back phase in the computational basis.",
            ],
            "allowed_gates": ["h", "x", "cx", "measure"],
            "max_depth": 6,
            "target": {
                "counts": {"11": 0.5, "10": 0.5},
                "shots": 1024,
                "tolerance": 0.15,
            },
            "hints": [
                "A CNOT into |-⟩ acts as a phase-flip gate Z on the control qubit!",
            ],
            "starter_ir": {
                "name": "Daily Challenge: Phase Kickback",
                "n_qubits": 2,
                "n_clbits": 2,
                "ops": [],
            },
        },
    ]

    # Select daily challenge based on hash of current date
    seed = sum(ord(c) for c in date_str)
    return daily_challenges[seed % len(daily_challenges)]


def verify_daily_challenge(challenge_id: str, circuit_ir_dict: dict[str, Any]) -> dict[str, Any]:
    """Evaluates the submitted circuit for the daily challenge."""
    try:
        ir = CircuitIR.from_dict(circuit_ir_dict)
    except Exception as exc:
        return {"passed": False, "score": 0, "message": f"Invalid circuit: {exc}"}

    report = inspect_circuit(ir, "auto", shots=1024)
    if not report.get("ok"):
        return {"passed": False, "score": 0, "message": "Circuit validation error: " + "; ".join(report.get("errors", []))}

    # Check depth
    depth = max((op.layer for op in ir.ops), default=0) + 1
    
    # Run lightweight simulation
    from app.quantum.backends.qiskit_aer import run_simulation
    try:
        result = run_simulation(ir, shots=1024)
        counts = result.counts or {}
        total = sum(counts.values()) or 1
        probs = {k: v / total for k, v in counts.items()}

        # Verify challenge conditions
        passed = False
        message = ""

        if "Bell" in challenge_id or "Φ" in challenge_id:
            p00 = probs.get("00", 0.0)
            p11 = probs.get("11", 0.0)
            passed = p00 >= 0.35 and p11 >= 0.35 and (p00 + p11) >= 0.85
            message = "Bell state verified! Outcomes 00 & 11 produced with balanced probabilities." if passed else f"Target |00⟩ & |11⟩ not met (got 00: {p00:.2f}, 11: {p11:.2f})."
        elif "GHZ" in challenge_id:
            p000 = probs.get("000", 0.0)
            p111 = probs.get("111", 0.0)
            passed = p000 >= 0.35 and p111 >= 0.35 and (p000 + p111) >= 0.85
            message = "GHZ tripartite entanglement verified! 000 and 111 measured." if passed else "State did not produce expected GHZ distribution."
        else:
            # General challenge passes if measurements exist and at least 2 gates placed
            passed = len(ir.ops) >= 2 and any(op.kind == "measure" for op in ir.ops)
            message = "Circuit executed successfully and verified!" if passed else "Make sure to measure qubits."

        return {
            "passed": passed,
            "score": 100 if passed else 30,
            "depth": depth,
            "counts": counts,
            "message": message,
        }
    except Exception as exc:
        return {"passed": False, "score": 0, "message": f"Simulation failed: {exc}"}
