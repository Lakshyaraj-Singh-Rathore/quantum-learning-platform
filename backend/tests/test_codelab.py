"""Learner-written code must compile to a circuit -- and must not escape."""

from __future__ import annotations

import pytest

from app.services.codelab import (
    FRAMEWORKS,
    STARTERS,
    CodeLabError,
    build_circuit,
)

BELL_QISKIT = (
    "from qiskit import QuantumCircuit\n"
    "circuit = QuantumCircuit(2, 2)\n"
    "circuit.h(0)\n"
    "circuit.cx(0, 1)\n"
    "circuit.measure([0, 1], [0, 1])\n"
)


@pytest.mark.parametrize("framework", FRAMEWORKS)
def test_every_starter_compiles_to_a_circuit(framework):
    """The example we hand the learner must actually work."""
    built = build_circuit(STARTERS[framework], framework)
    ir = built["ir"]
    assert ir.n_qubits == 2
    assert any(op.gate == "h" for op in ir.walk() if op.kind == "gate")
    assert "OPENQASM 3" in built["qasm3"]


def test_qiskit_code_produces_a_bell_pair_ir():
    ir = build_circuit(BELL_QISKIT, "qiskit")["ir"]
    gates = [op.gate for op in ir.walk() if op.kind == "gate"]
    assert "h" in gates
    assert "x" in gates  # cx is stored as x with a control
    assert any(op.controls for op in ir.walk() if op.kind == "gate")


def test_program_stdout_is_returned_to_the_learner():
    code = "print('hello from my program')\n" + BELL_QISKIT
    assert "hello from my program" in build_circuit(code, "qiskit")["stdout"]


# --------------------------------------------------------------------------- #
# Failure modes: the message must teach, not dump a traceback
# --------------------------------------------------------------------------- #
def test_missing_circuit_variable_is_explained():
    with pytest.raises(CodeLabError, match="never defined `circuit`"):
        build_circuit("from qiskit import QuantumCircuit\nqc = QuantumCircuit(2)", "qiskit")


def test_syntax_error_is_reported():
    with pytest.raises(CodeLabError, match="SyntaxError"):
        build_circuit("this is not python!!", "qiskit")


def test_runtime_error_is_reported():
    with pytest.raises(CodeLabError, match="ZeroDivisionError"):
        build_circuit("x = 1 / 0", "qiskit")


def test_empty_program_is_rejected():
    with pytest.raises(CodeLabError):
        build_circuit("   ", "qiskit")


def test_unknown_framework_is_rejected():
    with pytest.raises(CodeLabError, match="framework must be"):
        build_circuit(BELL_QISKIT, "braket")


def test_oversized_program_is_rejected():
    with pytest.raises(CodeLabError, match="too long"):
        build_circuit("#" * 20_001, "qiskit")


# --------------------------------------------------------------------------- #
# Sandbox
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "module", ["os", "subprocess", "socket", "shutil", "pathlib", "sys"]
)
def test_dangerous_imports_are_blocked(module):
    with pytest.raises(CodeLabError, match="not allowed"):
        build_circuit(f"import {module}\ncircuit = None", "qiskit")


def test_file_access_is_blocked():
    with pytest.raises(CodeLabError, match="file access is disabled"):
        build_circuit("open('/etc/passwd').read()\ncircuit = None", "qiskit")


def test_scientific_imports_are_still_allowed():
    """The sandbox must not get in the way of legitimate work."""
    code = (
        "import numpy as np\n"
        "from qiskit import QuantumCircuit\n"
        "circuit = QuantumCircuit(1, 1)\n"
        "circuit.rx(np.pi / 2, 0)\n"
        "circuit.measure(0, 0)\n"
    )
    assert build_circuit(code, "qiskit")["ir"].n_qubits == 1


def test_infinite_loop_is_killed_by_the_timeout():
    with pytest.raises(CodeLabError, match="did not finish"):
        build_circuit("while True:\n    pass\n", "qiskit")
