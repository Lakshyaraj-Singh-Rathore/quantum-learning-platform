"""Grounded AI tutor: RAG context + deterministic tool output, no simulation."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai import rag
from app.ai.gemini_client import GeminiUnavailable, generate, is_configured
from app.ai.tools import (
    ToolError,
    get_simulation_result,
    tool_inspect_circuit,
    tool_summarize_circuit,
)
from app.models.user import User

SYSTEM_INSTRUCTION = """You are the QuantumLearn tutor, an expert in quantum computing
teaching students inside an interactive learning platform.

Rules you must follow:
- Ground every factual claim in the COURSE CONTEXT provided. If the context does not
  cover the question, say so plainly and answer from general knowledge, flagged as such.
- You cannot run simulations. Never claim to have executed a circuit. If the user wants
  results, tell them to press Run in the Composer. You may only interpret SIMULATION
  RESULT data that is given to you.
- When CIRCUIT ANALYSIS is provided, use its exact numbers (qubit counts, depth, gates)
  rather than guessing.
- Prefer short paragraphs and bullet points. Use LaTeX for math when helpful.
- Be encouraging and concrete; suggest the next concept or exercise when relevant.
"""


def answer(
    db: Session,
    user: User,
    message: str,
    circuit_ir: dict[str, Any] | None = None,
    job_id: int | None = None,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    tools_used: list[str] = []
    blocks: list[str] = []

    citations = rag.retrieve(db, message, k=4)
    if citations:
        joined = "\n\n".join(
            f"[{i + 1}] ({c['lesson_slug']}) {c['text']}" for i, c in enumerate(citations)
        )
        blocks.append(f"COURSE CONTEXT:\n{joined}")

    if circuit_ir:
        try:
            summary = tool_summarize_circuit(circuit_ir)
            report = tool_inspect_circuit(circuit_ir)
            tools_used += ["summarize_circuit", "inspect_circuit"]
            blocks.append(
                "CIRCUIT ANALYSIS:\n"
                f"- qubits: {summary['n_qubits']}, clbits: {summary['n_clbits']}, "
                f"depth: {summary['depth']}\n"
                f"- gates: {summary['gate_histogram']}\n"
                f"- dynamic: {summary['is_dynamic']}, "
                f"control flow: {summary['control_flow'] or 'none'}\n"
                f"- errors: {report['errors'] or 'none'}\n"
                f"- warnings: {report['warnings'] or 'none'}\n"
                f"OpenQASM 3:\n{summary['qasm3']}"
            )
        except ToolError as exc:
            blocks.append(f"CIRCUIT ANALYSIS: unavailable ({exc})")

    if job_id is not None:
        try:
            job = get_simulation_result(db, user, job_id)
            tools_used.append("get_simulation_result")
            if job.get("result"):
                result = job["result"]
                blocks.append(
                    "SIMULATION RESULT (already executed - do not claim you ran it):\n"
                    f"- backend: {result['metadata'].get('backend')}, "
                    f"shots: {result['metadata'].get('shots')}\n"
                    f"- counts: {result.get('counts')}\n"
                    f"- warnings: {result['metadata'].get('warnings')}"
                )
            else:
                blocks.append(f"SIMULATION RESULT: job {job_id} is {job['status']}.")
        except ToolError as exc:
            blocks.append(f"SIMULATION RESULT: unavailable ({exc})")

    context = "\n\n".join(blocks)
    prompt = f"{context}\n\nSTUDENT QUESTION:\n{message}" if context else message

    if not is_configured():
        return {
            "reply": _offline_reply(message, citations),
            "citations": citations,
            "tools_used": tools_used,
        }

    try:
        reply = generate(prompt, system_instruction=SYSTEM_INSTRUCTION, history=history)
    except GeminiUnavailable as exc:
        reply = str(exc)
    except Exception as exc:  # noqa: BLE001
        reply = f"The tutor is temporarily unavailable ({type(exc).__name__}: {exc})."

    return {"reply": reply, "citations": citations, "tools_used": tools_used}


def _offline_reply(message: str, citations: list[dict[str, Any]]) -> str:
    """Useful, honest response when no Gemini key is configured."""
    if not citations:
        return (
            "AI tutoring is not configured (no GEMINI_API_KEY), and I could not find "
            "matching curriculum content. Try the Learn page for the lesson list."
        )
    lines = [
        "AI tutoring is not configured (no GEMINI_API_KEY), so here are the most "
        "relevant excerpts from the course material:",
        "",
    ]
    for index, citation in enumerate(citations[:3], start=1):
        excerpt = citation["text"].strip()
        if len(excerpt) > 700:
            excerpt = excerpt[:700].rstrip() + "..."
        lines.append(f"**{index}. {citation['lesson_slug']}**\n\n{excerpt}\n")
    return "\n".join(lines)


__all__ = ["answer", "SYSTEM_INSTRUCTION"]
