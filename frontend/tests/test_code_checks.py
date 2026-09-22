"""Live editor diagnostics: catch typos before Build, and never cry wolf.

A checker that fires on valid code is worse than none, because learners stop
reading it. Every "clean" case here is a program the sandbox genuinely accepts.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import code_checks as cc  # noqa: E402

VALID_QISKIT = (
    "from qiskit import QuantumCircuit\n"
    "circuit = QuantumCircuit(2, 2)\n"
    "circuit.h(0)\n"
    "circuit.cx(0, 1)\n"
)
VALID_QASM = (
    "OPENQASM 3.0;\n"
    'include "stdgates.inc";\n'
    "qubit[2] q;\n"
    "bit[2] c;\n"
    "h q[0];\n"
    "cx q[0], q[1];\n"
    "c[0] = measure q[0];\n"
    "c[1] = measure q[1];\n"
)


# --------------------------------------------------------------- no false alarms
def test_valid_qiskit_is_clean():
    assert cc.check(VALID_QISKIT, "qiskit") == []


def test_valid_qasm_is_clean():
    assert cc.check(VALID_QASM, "qasm3") == []


def test_declarations_are_not_reported_as_undeclared():
    """`qubit[2] q;` declares q; the old check flagged it as a use of `qubit`."""
    findings = cc.check(VALID_QASM, "qasm3")
    assert not any("qubit" in message for _, _, message in findings)


def test_empty_source_is_quiet():
    assert cc.check("", "qiskit") == []
    assert cc.check("", "qasm3") == []


# ------------------------------------------------------------------ python
def test_syntax_error_is_reported_with_a_line():
    findings = cc.check("circuit = QuantumCircuit(2, 2\n", "qiskit")
    assert findings
    line, _column, message = findings[0]
    assert line >= 1
    assert "Syntax error" in message


def test_blocked_import_is_flagged():
    findings = cc.check("import os\ncircuit = 1\n", "qiskit")
    assert any("os" in message and "blocked" in message for _, _, message in findings)


def test_from_import_of_a_blocked_module_is_flagged():
    findings = cc.check("from subprocess import run\ncircuit = 1\n", "qiskit")
    assert any("subprocess" in message for _, _, message in findings)


def test_missing_circuit_variable_is_flagged():
    findings = cc.check("from qiskit import QuantumCircuit\nqc = QuantumCircuit(2)\n", "qiskit")
    assert any("circuit" in message for _, _, message in findings)


def test_qbraid_runtime_is_flagged():
    source = "from qbraid.runtime import QbraidProvider\ncircuit = 1\n"
    findings = cc.check(source, "qbraid")
    assert any("credits" in message for _, _, message in findings)


# -------------------------------------------------------------------- qasm
def test_missing_header_is_flagged():
    findings = cc.check("qubit[2] q;\nh q[0];\n", "qasm3")
    assert any("OPENQASM" in message for _, _, message in findings)


def test_unknown_gate_is_flagged_with_its_line():
    findings = cc.check("OPENQASM 3.0;\nqubit[2] q;\nhadamard q[0];\n", "qasm3")
    match = [f for f in findings if "hadamard" in f[2]]
    assert match and match[0][0] == 3


def test_undeclared_register_is_flagged():
    findings = cc.check("OPENQASM 3.0;\nqubit[2] q;\nh r[0];\n", "qasm3")
    assert any("`r`" in message for _, _, message in findings)


def test_missing_semicolon_is_flagged():
    findings = cc.check("OPENQASM 3.0;\nqubit[2] q;\nh q[0]\n", "qasm3")
    assert any(";" in message for _, _, message in findings)


def test_missing_qubit_register_is_flagged():
    findings = cc.check("OPENQASM 3.0;\n", "qasm3")
    assert any("qubit register" in message for _, _, message in findings)


# ------------------------------------------------------------------ safety
@pytest.mark.parametrize("source", ["\x00", "def", "((((", "🙂" * 50, "\n" * 200])
def test_checker_never_raises(source):
    for framework in ("qiskit", "cirq", "pennylane", "qasm3", "qbraid"):
        cc.check(source, framework)


def test_annotate_marks_the_offending_lines():
    source = "OPENQASM 3.0;\nqubit[2] q;\nhadamard q[0];\n"
    rendered = cc.annotate(source, cc.check(source, "qasm3"))
    assert "^^^" in rendered
    assert "hadamard" in rendered
