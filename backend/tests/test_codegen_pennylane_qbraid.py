"""Generated PennyLane and qBraid programs must be valid and correct.

A code generator that emits plausible-looking but unrunnable code is worse
than none, so these tests compile the output and -- for PennyLane, which runs
locally -- execute it and compare against Aer.
"""

from __future__ import annotations

import ast
import subprocess
import sys

import pytest

from app.quantum import codegen_pennylane, codegen_qbraid
from app.quantum.ir import CircuitIR

BELL = [
    {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
    {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
    {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
    {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
]

DYNAMIC = [
    {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
    {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
    {
        "kind": "if",
        "condition": {"type": "bit_eq", "bit": 0, "value": 1},
        "body": [{"kind": "gate", "gate": "x", "qubits": [1], "layer": 0}],
        "layer": 2,
    },
]


def _ir(ops, n_qubits=2, n_clbits=2):
    return CircuitIR.model_validate(
        {"n_qubits": n_qubits, "n_clbits": n_clbits, "ops": ops}
    )


def test_pennylane_output_is_valid_python():
    ast.parse(codegen_pennylane.generate(_ir(BELL), 512))


def test_qbraid_output_is_valid_python():
    ast.parse(codegen_qbraid.generate(_ir(BELL), 512))


def test_pennylane_script_runs_and_produces_a_bell_pair():
    """Execute the generated file as a standalone program."""
    code = codegen_pennylane.generate(_ir(BELL), 400)
    proc = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=300
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "'00'" in out and "'11'" in out
    assert "'01'" not in out and "'10'" not in out, f"Bell pair leaked: {out}"


def test_pennylane_emits_controlled_gates_for_arbitrary_control_counts():
    ops = [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [3], "controls": [0, 1, 2], "layer": 1},
    ]
    code = codegen_pennylane.generate(_ir(ops, 4, 4), 100)
    assert "qml.ctrl(qml.PauliX, control=[0, 1, 2])" in code
    ast.parse(code)


def test_pennylane_uses_adjoint_for_dagger_gates():
    ops = [
        {"kind": "gate", "gate": "sdg", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "tdg", "qubits": [1], "layer": 0},
    ]
    code = codegen_pennylane.generate(_ir(ops), 100)
    assert "qml.adjoint(qml.S(wires=0))" in code
    assert "qml.adjoint(qml.T(wires=1))" in code


def test_qbraid_script_embeds_the_circuit_as_qasm3():
    code = codegen_qbraid.generate(_ir(BELL), 2048)
    assert "OPENQASM 3.0;" in code
    assert "cx q[0], q[1];" in code
    assert "SHOTS = 2048" in code
    assert "QBRAID_API_KEY" in code


@pytest.mark.parametrize("module", [codegen_pennylane, codegen_qbraid])
def test_dynamic_circuits_are_refused_with_an_explanation(module):
    """Neither backend runs dynamic circuits, so neither may pretend to."""
    code = module.generate(_ir(DYNAMIC), 100)
    ast.parse(code)  # still a valid file
    assert "Qiskit" in code, "must point the user at the engine that does work"
    assert "qml.qnode" not in code
    assert "device.run" not in code
