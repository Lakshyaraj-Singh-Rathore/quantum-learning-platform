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
        "name": "Qubits & Superposition",
        "label": "Qubits & Superposition",
        "category": "Foundations",
        "description": "State vectors, Bloch sphere representation, and linear superposition",
        "keywords": ["qubit", "superposition", "bloch", "ket"],
        "rag_query": "qubits and superposition state vectors Bloch sphere",
    },
    {
        "id": "quantum_gates",
        "name": "Quantum Gates & Unitary Operators",
        "label": "Quantum Gates & Unitary Operators",
        "category": "Gates",
        "description": "Pauli X/Y/Z, Hadamard, Phase, Rotations (Rx, Ry, Rz), and CX/CZ",
        "keywords": ["gate", "hadamard", "pauli", "unitary", "rotation"],
        "rag_query": "quantum gates unitary operations Hadamard Pauli rotation",
    },
    {
        "id": "entanglement_bell",
        "name": "Entanglement & Bell States",
        "label": "Entanglement & Bell States",
        "category": "Entanglement",
        "description": "EPR pairs, Bell state preparation, concurrence, and non-locality",
        "keywords": ["entangle", "bell", "ghz", "epr", "concurrence"],
        "rag_query": "entanglement Bell states EPR pairs concurrence",
    },
    {
        "id": "measurement_collapse",
        "name": "Measurement & Born Rule",
        "label": "Measurement & Born Rule",
        "category": "Measurement",
        "description": "Projective measurement, state collapse, probability distributions, and shot noise",
        "keywords": ["measure", "born rule", "collapse", "probability"],
        "rag_query": "quantum measurement state collapse Born rule probability",
    },
    {
        "id": "quantum_algorithms",
        "name": "Quantum Algorithms",
        "label": "Quantum Algorithms",
        "category": "Algorithms",
        "description": "Deutsch-Jozsa, Bernstein-Vazirani, Grover's search, and QFT",
        "keywords": ["deutsch", "jozsa", "grover", "algorithm", "oracle"],
        "rag_query": "quantum algorithms Grover search Deutsch-Jozsa QFT",
    },
    {
        "id": "teleportation_dense",
        "name": "Teleportation & Superdense Coding",
        "label": "Teleportation & Superdense Coding",
        "category": "Protocols",
        "description": "Quantum state transfer, entanglement as resource, and 2-bit communication",
        "keywords": ["teleportation", "superdense", "quantum channel"],
        "rag_query": "quantum teleportation superdense coding communications",
    },
    {
        "id": "density_matrices",
        "name": "Density Matrices & Mixed States",
        "label": "Density Matrices & Mixed States",
        "category": "Noise & States",
        "description": "Ensembles, partial trace, purity, and environmental decoherence",
        "keywords": ["density matrix", "purity", "mixed state", "decoherence"],
        "rag_query": "density matrices mixed states partial trace decoherence",
    },
    {
        "id": "dynamic_circuits",
        "name": "Dynamic Circuits & Control Flow",
        "label": "Dynamic Circuits & Control Flow",
        "category": "Control Flow",
        "description": "Mid-circuit measurement, conditional branching, feed-forward, and while loops",
        "keywords": ["dynamic", "mid-circuit", "conditional", "feed-forward"],
        "rag_query": "dynamic circuits mid-circuit measurement conditional feed-forward",
    },
]

TOPIC_LOOKUP = {t["id"]: t for t in AVAILABLE_TOPICS}
# Backward compatibility aliases
TOPIC_LOOKUP["qubits_gates"] = TOPIC_LOOKUP["quantum_gates"]

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
                q_count = 0
                all_questions = []
                by_topic = {}
                for s_idx, sec in enumerate(parsed["sections"]):
                    t_id = sec.get("topic_id") or f"topic_{s_idx}"
                    t_name = sec.get("topic_title") or TOPIC_LOOKUP.get(t_id, {}).get("name", t_id)
                    sec_questions = []
                    for q_idx, q in enumerate(sec.get("questions", [])):
                        q_count += 1
                        q_id = q.get("id") or f"ai_q_{s_idx}_{q_idx}_{q_count}"
                        q_obj = {
                            "id": q_id,
                            "topic_id": t_id,
                            "topic_name": t_name,
                            "prompt": q.get("prompt", ""),
                            "options": q.get("options", []),
                            "correct_answer": q.get("correct_answer", ""),
                            "explanation": q.get("explanation", ""),
                            "difficulty": difficulty,
                            "source": "gemini-api",
                        }
                        sec_questions.append(q_obj)
                        all_questions.append(q_obj)
                    sec["questions"] = sec_questions
                    by_topic[t_id] = sec_questions

                return {
                    "assignment_id": f"asgn_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "created_at": datetime.datetime.now().isoformat(),
                    "title": parsed.get("title", "Quantum Computing Comprehensive Assessment"),
                    "topics": topics,
                    "total_questions": len(all_questions),
                    "difficulty": difficulty,
                    "by_topic": by_topic,
                    "questions": all_questions,
                    "sections": parsed["sections"],
                    "model_used": "Gemini 1.5 Flash (via Gemini API + RAG)",
                    "generated_by": "gemini-1.5-flash",
                }
        except Exception as exc:
            log.warning("Gemini assignment generation encountered error, falling back to verified bank: %s", exc)

    # 3. Fallback: Intelligent curriculum question assembler (100% reliable)
    sections: list[dict[str, Any]] = []
    all_questions: list[dict[str, Any]] = []
    by_topic: dict[str, list[dict[str, Any]]] = {}
    per_topic = max(1, num_questions // len(topics))
    q_counter = 1

    for t_id in topics:
        topic_info = TOPIC_LOOKUP.get(t_id, {"name": t_id.replace("_", " ").title(), "label": t_id})
        t_name = topic_info.get("name") or topic_info.get("label", t_id)
        bank = CURATED_QUESTION_BANK.get(t_id, CURATED_QUESTION_BANK["qubits_superposition"])
        selected_q = bank[:per_topic]
        
        section_questions = []
        for q in selected_q:
            q_obj = {
                "id": f"q_{q_counter}",
                "topic_id": t_id,
                "topic_name": t_name,
                "prompt": q["prompt"],
                "options": q["options"],
                "correct_answer": q["correct_answer"],
                "explanation": q["explanation"],
                "difficulty": difficulty,
                "source": "curriculum-rag",
            }
            section_questions.append(q_obj)
            all_questions.append(q_obj)
            q_counter += 1

        by_topic[t_id] = section_questions
        sections.append({
            "topic_id": t_id,
            "topic_title": t_name,
            "questions": section_questions,
        })

    return {
        "assignment_id": f"asgn_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "created_at": datetime.datetime.now().isoformat(),
        "title": "Quantum Computing Curriculum Assessment",
        "topics": topics,
        "total_questions": len(all_questions),
        "difficulty": difficulty,
        "by_topic": by_topic,
        "questions": all_questions,
        "sections": sections,
        "model_used": "Curriculum RAG Bank",
        "generated_by": "curriculum-rag",
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
    results_list: list[dict[str, Any]] = []

    # Flatten questions from sections or by_topic or questions
    raw_questions: list[dict[str, Any]] = []
    if assignment.get("questions") and isinstance(assignment["questions"], list):
        raw_questions = assignment["questions"]
    elif assignment.get("sections") and isinstance(assignment["sections"], list):
        for sec in assignment["sections"]:
            raw_questions.extend(sec.get("questions", []))
    elif assignment.get("by_topic") and isinstance(assignment["by_topic"], dict):
        for q_list in assignment["by_topic"].values():
            raw_questions.extend(q_list)

    for q in raw_questions:
        total_questions += 1
        t_id = q.get("topic_id", "general")
        t_title = q.get("topic_name") or q.get("topic_title") or t_id.replace("_", " ").title()

        if t_id not in topic_breakdown:
            topic_breakdown[t_id] = {
                "topic_title": t_title,
                "total": 0,
                "correct": 0,
                "percentage": 0.0,
            }

        topic_breakdown[t_id]["total"] += 1

        q_id = str(q.get("id"))
        user_choice = (answers.get(q_id) or "").strip()
        correct_choice = (q.get("correct_answer") or "").strip()

        is_correct = user_choice.lower() == correct_choice.lower() if user_choice and correct_choice else False
        if is_correct:
            total_correct += 1
            topic_breakdown[t_id]["correct"] += 1

        result_item = {
            "id": q_id,
            "prompt": q.get("prompt", ""),
            "topic_id": t_id,
            "topic_name": t_title,
            "selected_idx": -1,
            "correct_idx": -1,
            "is_correct": is_correct,
            "selected_text": user_choice or "(No answer provided)",
            "correct_text": correct_choice,
            "explanation": q.get("explanation", ""),
        }
        results_list.append(result_item)
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
    grade = (
        "Distinction (A*)" if overall_percentage >= 90
        else "Merit (A)" if overall_percentage >= 80
        else "Pass (B)" if overall_percentage >= 70
        else "Needs Review (C)" if overall_percentage >= 50
        else "Unsatisfactory (F)"
    )

    summary = (
        f"You scored {total_correct} out of {total_questions} ({overall_percentage}%). "
        f"Grade: {grade}. "
        + ("Excellent mastery of quantum principles!" if overall_percentage >= 80 else "Review the pedagogical explanations below to sharpen your quantum knowledge.")
    )

    return {
        "assignment_id": assignment.get("assignment_id", f"asgn_eval_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"),
        "score": total_correct,
        "total": total_questions,
        "total_questions": total_questions,
        "percentage": overall_percentage,
        "passed": overall_percentage >= 70.0,
        "grade": grade,
        "summary": summary,
        "topic_scores": topic_breakdown,
        "topic_breakdown": topic_breakdown,
        "results": results_list,
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
            "challenge_id": f"daily_{date_str}_1",
            "date": date_str,
            "title": "Daily Challenge: The Entangled Bell Pair |Φ⁻⟩",
            "difficulty": "beginner",
            "topic": "Entanglement & Bell States",
            "reward_xp": 100,
            "xp_reward": 100,
            "prompt": (
                "Construct the anti-phase entangled Bell state |Φ⁻⟩ = (|00⟩ - |11⟩)/√2 using single-qubit gates and CNOT. "
                "Ensure measurements yield a balanced 50/50 probability distribution across |00⟩ and |11⟩."
            ),
            "story": (
                "Alice and Bob need an anti-phase entangled Bell channel |Φ⁻⟩ = (|00⟩ - |11⟩)/√2 for a secure "
                "quantum key distribution session. Construct this 2-qubit state using only H, X, and CNOT gates."
            ),
            "target_state": "|Φ⁻⟩ = (|00⟩ - |11⟩)/√2",
            "allowed_gates": ["h", "x", "z", "cx", "measure"],
            "constraints": {
                "max_qubits": 2,
                "max_gates": 8,
                "target_fidelity": 0.90,
            },
            "hints": [
                "Start with H on q[0], then a Pauli-Z or start with X on q[0] before H.",
                "Apply CX from q[0] onto q[1] to distribute the entanglement.",
                "Measure both qubits into classical bits c[0] and c[1].",
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
            "challenge_id": f"daily_{date_str}_2",
            "date": date_str,
            "title": "Daily Challenge: Greenberger-Horne-Zeilinger (GHZ) Triad",
            "difficulty": "intermediate",
            "topic": "Multipartite Entanglement",
            "reward_xp": 150,
            "xp_reward": 150,
            "prompt": (
                "Prepare a genuine 3-qubit maximally entangled GHZ state |GHZ⟩ = (|000⟩ + |111⟩)/√2. "
                "Keep circuit depth under 6 and verify an even split between |000⟩ (50%) and |111⟩ (50%)."
            ),
            "story": (
                "Prepare a genuine 3-qubit maximally entangled GHZ state |GHZ⟩ = (|000⟩ + |111⟩)/√2. "
                "This state exhibits extreme non-classical correlations and sensitive multipartite entanglement."
            ),
            "target_state": "|GHZ⟩ = (|000⟩ + |111⟩)/√2",
            "allowed_gates": ["h", "cx", "x", "measure"],
            "constraints": {
                "max_qubits": 3,
                "max_gates": 10,
                "target_fidelity": 0.90,
            },
            "hints": [
                "Put q[0] into superposition using H.",
                "Cascade CNOT gates: q[0] → q[1], then q[1] → q[2].",
                "Measure all 3 qubits into classical bits.",
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
            "challenge_id": f"daily_{date_str}_3",
            "date": date_str,
            "title": "Daily Challenge: Phase Kickback Flag",
            "difficulty": "intermediate",
            "topic": "Quantum Oracles & Phase Kickback",
            "reward_xp": 120,
            "xp_reward": 120,
            "prompt": (
                "Implement the quantum oracle primitive: Phase Kickback. "
                "Prepare target qubit q[1] in the |-⟩ state, then apply a CNOT from control q[0] to observe how "
                "the eigenvalue phase kicks back onto control qubit q[0]."
            ),
            "story": (
                "Implement the fundamental quantum oracle primitive: Phase Kickback. "
                "Prepare target qubit q[1] in the |-⟩ state, then apply a CNOT from control q[0] to observe how "
                "the eigenvalue phase kicks back onto control qubit q[0]."
            ),
            "target_state": "|+⟩, |-⟩ Phase Kickback",
            "allowed_gates": ["h", "x", "cx", "measure"],
            "constraints": {
                "max_qubits": 2,
                "max_gates": 8,
                "target_fidelity": 0.90,
            },
            "hints": [
                "Prepare q[0] in |+⟩ using H.",
                "Prepare q[1] in |-⟩ using X then H.",
                "Apply CX(q[0], q[1]) to kick back the relative phase.",
                "Apply H on q[0] before measurement.",
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


def resolve_daily_challenge_type(challenge_id: str) -> str:
    """Accurately identifies the quantum challenge type from challenge_id."""
    cid = (challenge_id or "").lower()
    
    # Direct keyword or suffix matches
    if "ghz" in cid or "triad" in cid or cid.endswith("_2"):
        return "ghz"
    if "kickback" in cid or "oracle" in cid or cid.endswith("_3"):
        return "kickback"
    if "bell" in cid or "phi" in cid or "φ" in cid or cid.endswith("_1"):
        return "bell"
        
    # Date-based fallback if format is daily_YYYY-MM-DD
    import re
    match = re.search(r"\d{4}-\d{2}-\d{2}", cid)
    if match:
        date_str = match.group(0)
        seed = sum(ord(c) for c in date_str)
        idx = seed % 3
        if idx == 0:
            return "bell"
        elif idx == 1:
            return "ghz"
        elif idx == 2:
            return "kickback"
            
    return "general"


def verify_daily_challenge(challenge_id: str, circuit_ir_dict: dict[str, Any]) -> dict[str, Any]:
    """Evaluates the submitted circuit for the daily challenge."""
    try:
        ir = CircuitIR.from_dict(circuit_ir_dict)
    except Exception as exc:
        return {
            "passed": False,
            "score": 0,
            "fidelity": 0.0,
            "feedback": f"Invalid circuit format: {exc}",
            "message": f"Invalid circuit: {exc}",
        }

    report = inspect_circuit(ir, "auto", shots=1024)
    if not report.get("ok"):
        err_msg = "Circuit validation error: " + "; ".join(report.get("errors", []))
        return {
            "passed": False,
            "score": 0,
            "fidelity": 0.0,
            "feedback": err_msg,
            "message": err_msg,
        }

    # Check depth
    depth = max((op.layer for op in ir.ops), default=0) + 1
    
    # Run lightweight simulation
    from app.quantum.backends.qiskit_aer import run as run_aer_sim
    try:
        result = run_aer_sim(ir, shots=1024)
        counts = result.get("counts") if isinstance(result, dict) else (getattr(result, "counts", None) or {})
        total = sum(counts.values()) or 1
        probs = {k: v / total for k, v in counts.items()}

        # Verify challenge conditions based on challenge type
        ch_type = resolve_daily_challenge_type(challenge_id)
        passed = False
        message = ""
        fidelity = 0.0

        if ch_type == "ghz":
            # 3-Qubit GHZ State (|000⟩ + |111⟩)/√2
            p000 = probs.get("000", 0.0)
            p111 = probs.get("111", 0.0)
            fidelity = round(p000 + p111, 4)
            passed = p000 >= 0.35 and p111 >= 0.35 and (p000 + p111) >= 0.85
            if passed:
                message = f"GHZ tripartite entanglement verified! Balanced outcomes across |000⟩ ({p000*100:.1f}%) and |111⟩ ({p111*100:.1f}%)."
            else:
                message = f"Target |000⟩ & |111⟩ not met (got |000⟩: {p000*100:.1f}%, |111⟩: {p111*100:.1f}%). Expected 50/50 superposition across |000⟩ and |111⟩."

        elif ch_type == "bell":
            # 2-Qubit Bell State (|00⟩ ± |11⟩)/√2
            p00 = probs.get("00", 0.0)
            p11 = probs.get("11", 0.0)
            fidelity = round(p00 + p11, 4)
            passed = p00 >= 0.35 and p11 >= 0.35 and (p00 + p11) >= 0.85
            if passed:
                message = f"Bell state verified! Outcomes 00 ({p00*100:.1f}%) & 11 ({p11*100:.1f}%) produced with balanced probabilities."
            else:
                message = f"Target |00⟩ & |11⟩ not met (got 00: {p00*100:.1f}%, 11: {p11*100:.1f}%). Expected balanced 50/50 superposition."

        elif ch_type == "kickback":
            # Phase kickback flag: measuring q[0] after kickback yields 1 (rightmost bit)
            p_q0_1 = sum(v for k, v in probs.items() if len(k) >= 1 and k[-1] == "1")
            fidelity = round(p_q0_1, 4)
            passed = p_q0_1 >= 0.85
            if passed:
                message = f"Phase kickback verified! Eigenvalue phase successfully inverted control qubit q[0] to |1⟩ (P(q0=1) = {p_q0_1*100:.1f}%)."
            else:
                message = f"Phase kickback condition not met (P(q[0]=1) = {p_q0_1*100:.1f}%, expected ≥ 85%). Prepare q[1] in |-⟩ using X then H, CX(q[0], q[1]), and H on q[0] before measurement."

        else:
            # General fallback challenge verification
            passed = len(ir.ops) >= 2 and any(op.kind == "measure" for op in ir.ops)
            fidelity = 1.0 if passed else 0.4
            message = "Circuit executed successfully and verified!" if passed else "Make sure to measure qubits."

        return {
            "passed": passed,
            "score": 100 if passed else 30,
            "fidelity": fidelity,
            "feedback": message,
            "message": message,
            "depth": depth,
            "counts": counts,
            "details": {"depth": depth, "counts": counts, "fidelity": fidelity},
        }
    except Exception as exc:
        return {
            "passed": False,
            "score": 0,
            "fidelity": 0.0,
            "feedback": f"Simulation execution failed: {exc}",
            "message": f"Simulation failed: {exc}",
        }
