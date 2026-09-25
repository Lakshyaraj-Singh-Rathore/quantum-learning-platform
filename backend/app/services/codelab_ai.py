"""Gemini-backed code generation for the Code Lab.

The model writes source code and nothing else. It cannot execute anything: the
generated text is returned to the editor, and running it still goes through
``codelab.build_circuit``, i.e. the same sandbox as hand-written code. This
preserves the platform rule that the AI may explain and generate, never
simulate.
"""

from __future__ import annotations

import re

from app.ai import gemini_client
from app.services.codelab import FRAMEWORKS, STARTERS

MAX_PROMPT_CHARS = 2_000

_SYSTEM = """\
You write short, correct quantum circuit programs for a teaching platform.

Hard requirements:
- Output ONLY source code. No prose, no explanation outside comments.
- Do not wrap the code in markdown fences.
- The program must assign its circuit to a variable named `circuit`.
- Never import os, sys, subprocess, socket, requests or open files. The
  sandbox blocks them and the program will fail to build.
- Never submit jobs to real hardware and never import qbraid.runtime.
- Keep it under 40 lines and comment the interesting steps.
- Prefer 2 to 5 qubits unless the user asks for more. The platform caps
  static simulation at 20 qubits.
"""

_FRAMEWORK_RULES = {
    "qiskit": "Use qiskit. Assign a QuantumCircuit to `circuit`.",
    "cirq": "Use cirq. Assign a cirq.Circuit to `circuit`.",
    "pennylane": (
        "Use pennylane. Assign a QNode to `circuit`. The QNode must take no "
        "required arguments, or give every parameter a default value."
    ),
    "qasm3": (
        "Write OpenQASM 3 source as a Python string assigned to `circuit`. "
        "Include the OPENQASM 3.0 header and stdgates.inc."
    ),
    "qbraid": (
        "Use qbraid.transpiler.transpile to convert a circuit to QASM 3 and "
        "assign the result to `circuit`. Build the source circuit with "
        "qiskit. Do NOT import qbraid.runtime: it submits jobs and spends "
        "credits, and the sandbox blocks it."
    ),
    "cudaq": (
        "Use cudaq's builder API: `circuit = cudaq.make_kernel()`, "
        "`q = circuit.qalloc(n)`, then gates like circuit.h(q[0]), "
        "circuit.rx(angle, q[0]), circuit.cx(q[0], q[1]) and measurement "
        "circuit.mz(q). Assign the kernel object itself to `circuit`. Do NOT "
        "use the @cudaq.kernel decorator (the lab evaluates kernel objects, "
        "not source text), no for_loop or conditional measurement, and keep "
        "every gate angle a literal float."
    ),
}

_FENCE = re.compile(r"^\s*```[a-zA-Z0-9]*\s*\n(.*?)\n?\s*```\s*$", re.S)


def strip_code_fence(text: str) -> str:
    """Remove a ``` wrapper if the model added one despite instructions."""
    match = _FENCE.match(text.strip())
    return (match.group(1) if match else text).strip() + "\n"


def build_prompt(request: str, framework: str) -> str:
    return (
        f"{_FRAMEWORK_RULES[framework]}\n\n"
        f"Here is a working example for this framework:\n\n"
        f"{STARTERS[framework]}\n\n"
        f"Now write a program for this request:\n{request.strip()}"
    )


def generate_code(request: str, framework: str) -> str:
    if framework not in FRAMEWORKS:
        raise ValueError(f"unknown framework {framework}")
    request = (request or "").strip()
    if not request:
        raise ValueError("describe the circuit you want first")
    if len(request) > MAX_PROMPT_CHARS:
        raise ValueError(
            f"description is too long ({len(request)} characters, "
            f"maximum {MAX_PROMPT_CHARS})"
        )

    reply = gemini_client.generate(
        build_prompt(request, framework),
        system_instruction=_SYSTEM,
        # No tools. The model writes text; it never calls back into the
        # platform and never runs anything.
        tools=None,
    )
    return strip_code_fence(reply)


__all__ = ["generate_code", "build_prompt", "strip_code_fence", "MAX_PROMPT_CHARS"]
