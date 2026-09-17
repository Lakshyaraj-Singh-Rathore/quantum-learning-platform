"""qBraid authoring in the Code Lab, and Gemini-drafted source.

Two additions covered here:

* qBraid joins the Code Lab as a fifth framework. Its value is the LOCAL
  transpiler, which converts between circuit formats without touching the
  network. ``qbraid.runtime`` -- the submission client that spends credits --
  stays blocked, so learner code cannot run up a bill from the sandbox.
* Gemini can draft Code Lab source. The model only ever writes text into the
  editor; running it still goes through the same sandbox as hand-written code,
  which preserves the rule that the AI never executes or simulates anything.
"""

from __future__ import annotations

import pytest

from app.quantum.backends import qiskit_aer
from app.services import codelab_ai
from app.services.codelab import FRAMEWORKS, STARTERS, CodeLabError, build_circuit


# ----------------------------------------------------------- qBraid authoring
def test_qbraid_is_an_authoring_framework():
    assert "qbraid" in FRAMEWORKS
    assert "qbraid" in STARTERS


def test_qbraid_starter_builds_and_simulates():
    ir = build_circuit(STARTERS["qbraid"], "qbraid")["ir"]
    assert ir.n_qubits == 2
    counts = qiskit_aer.run(ir, shots=500, seed=3)["counts"]
    assert set(counts) == {"00", "11"}


def test_qbraid_transpiler_needs_no_credentials():
    """The local transpiler must work with no API key configured."""
    code = (
        "from qbraid.transpiler import transpile\n"
        "from qiskit import QuantumCircuit\n"
        "qc = QuantumCircuit(3, 3)\n"
        "qc.h(0)\n"
        "qc.cx(0, 1)\n"
        "qc.cx(0, 2)\n"
        "qc.measure([0, 1, 2], [0, 1, 2])\n"
        "circuit = transpile(qc, 'qasm3')\n"
    )
    ir = build_circuit(code, "qbraid")["ir"]
    assert ir.n_qubits == 3


@pytest.mark.parametrize(
    "code",
    [
        "from qbraid.runtime import QbraidProvider\ncircuit = 1",
        "import qbraid.runtime\ncircuit = 1",
    ],
    ids=["from-import", "plain-import"],
)
def test_qbraid_runtime_stays_blocked(code):
    """Submitting jobs from the sandbox would spend real credits."""
    with pytest.raises(CodeLabError) as exc:
        build_circuit(code, "qbraid")
    assert "credits" in str(exc.value)


def test_network_still_blocked_for_qbraid_framework():
    with pytest.raises(CodeLabError):
        build_circuit("import socket\ncircuit = 1", "qbraid")


# ------------------------------------------------------------ AI generation
def test_every_framework_has_generation_rules():
    for framework in FRAMEWORKS:
        assert framework in codelab_ai._FRAMEWORK_RULES


def test_prompt_includes_the_framework_example():
    prompt = codelab_ai.build_prompt("a GHZ state", "qbraid")
    assert "qbraid.transpiler" in prompt
    assert "GHZ" in prompt


def test_qbraid_prompt_warns_the_model_off_runtime():
    assert "qbraid.runtime" in codelab_ai._FRAMEWORK_RULES["qbraid"]


def test_system_prompt_forbids_execution_and_io():
    system = codelab_ai._SYSTEM
    for banned in ["subprocess", "socket", "qbraid.runtime"]:
        assert banned in system


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("```python\nx = 1\n```", "x = 1\n"),
        ("```\nx = 1\n```", "x = 1\n"),
        ("x = 1", "x = 1\n"),
        ("  x = 1  ", "x = 1\n"),
    ],
)
def test_code_fences_are_stripped(raw, expected):
    assert codelab_ai.strip_code_fence(raw) == expected


def test_empty_request_is_rejected():
    with pytest.raises(ValueError):
        codelab_ai.generate_code("   ", "qiskit")


def test_overlong_request_is_rejected():
    with pytest.raises(ValueError) as exc:
        codelab_ai.generate_code("x" * (codelab_ai.MAX_PROMPT_CHARS + 1), "qiskit")
    assert "too long" in str(exc.value)


def test_unknown_framework_is_rejected():
    with pytest.raises(ValueError):
        codelab_ai.generate_code("bell state", "brainfuck")


def test_generated_code_goes_through_the_sandbox(monkeypatch):
    """A hostile model reply must still be caught by the sandbox."""
    monkeypatch.setattr(
        codelab_ai.gemini_client,
        "generate",
        lambda *a, **k: "```python\nimport os\ncircuit = 1\n```",
    )
    code = codelab_ai.generate_code("do something bad", "qiskit")
    assert code == "import os\ncircuit = 1\n"
    with pytest.raises(CodeLabError):
        build_circuit(code, "qiskit")


# ------------------------------------------------------------------ HTTP API
def test_generate_requires_authentication(client):
    r = client.post("/codelab/generate", json={"prompt": "bell", "framework": "qiskit"})
    assert r.status_code == 401


def test_generate_rejects_unknown_framework(client, student_headers):
    r = client.post(
        "/codelab/generate",
        json={"prompt": "bell", "framework": "brainfuck"},
        headers=student_headers,
    )
    assert r.status_code == 422


def test_generate_without_a_key_is_503_not_500(client, student_headers):
    r = client.post(
        "/codelab/generate",
        json={"prompt": "bell state", "framework": "qbraid"},
        headers=student_headers,
    )
    assert r.status_code == 503
    assert "GEMINI_API_KEY" in r.text


def test_starters_expose_qbraid(client, student_headers):
    r = client.get("/codelab/starters", headers=student_headers)
    assert r.status_code == 200
    assert "qbraid" in r.json()["frameworks"]
