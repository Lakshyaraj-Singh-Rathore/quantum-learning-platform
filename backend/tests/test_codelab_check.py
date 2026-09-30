"""POST /codelab/check: the static checks the new editor asks for.

The Streamlit editor ran these in Python on every rerun. The new Code Lab asks
the server instead, so these tests pin the contract the UI depends on: findings
are 1-based, the endpoint never raises on nonsense, and it never executes the
learner's code.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

VALID_QISKIT = (
    "from qiskit import QuantumCircuit\n"
    "circuit = QuantumCircuit(2, 2)\n"
    "circuit.h(0)\n"
    "circuit.cx(0, 1)\n"
    "circuit.measure([0, 1], [0, 1])\n"
)


def check(client, headers, code: str, framework: str = "qiskit"):
    return client.post(
        "/codelab/check", json={"code": code, "framework": framework}, headers=headers
    )


def test_valid_code_reports_no_findings(client, student_headers):
    response = check(client, student_headers, VALID_QISKIT)
    assert response.status_code == 200
    assert response.json()["findings"] == []


def test_a_syntax_error_is_reported_with_a_line_number(client, student_headers):
    response = check(client, student_headers, "circuit = QuantumCircuit(2\n")
    assert response.status_code == 200
    findings = response.json()["findings"]
    assert findings, "a broken program must produce at least one finding"
    assert findings[0]["line"] >= 1
    assert findings[0]["message"]


def test_a_blocked_import_is_reported(client, student_headers):
    findings = check(client, student_headers, "import os\n").json()["findings"]
    assert any("os" in f["message"] for f in findings)


def test_a_program_without_a_circuit_variable_is_reported(client, student_headers):
    findings = check(client, student_headers, "from qiskit import QuantumCircuit\n").json()[
        "findings"
    ]
    assert any("circuit" in f["message"].lower() for f in findings)


def test_an_unknown_qasm_gate_is_reported(client, student_headers):
    qasm = 'OPENQASM 3;\ninclude "stdgates.inc";\nqubit[2] q;\nfrobnicate q[0];\n'
    findings = check(client, student_headers, qasm, "qasm3").json()["findings"]
    assert any("frobnicate" in f["message"] for f in findings)


def test_the_annotated_source_marks_the_offending_line(client, student_headers):
    annotated = check(client, student_headers, "import os\n").json()["annotated"]
    assert annotated.startswith("import os")
    assert "^^^" in annotated


@pytest.mark.parametrize("code", ["", "   ", "((((", "\x00\x01", "def f(:\n  pass"])
def test_nonsense_never_raises_and_never_500s(client, student_headers, code):
    """A checker that blows up on the first keystroke would break the editor."""
    response = check(client, student_headers, code)
    assert response.status_code == 200
    assert isinstance(response.json()["findings"], list)


def test_the_endpoint_requires_a_signed_in_user(client):
    """An anonymous POST must not reach the checker."""
    with TestClient(app) as anonymous:
        response = anonymous.post(
            "/codelab/check", json={"code": VALID_QISKIT, "framework": "qiskit"}
        )
    assert response.status_code in {401, 403}
