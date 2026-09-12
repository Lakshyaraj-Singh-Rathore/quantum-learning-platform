"""Code Lab: OpenQASM 3 input and a workable import allowlist."""

import pytest

from app.services.codelab import FRAMEWORKS, STARTERS, CodeLabError, build_circuit


def test_qasm3_is_a_supported_framework():
    assert "qasm3" in FRAMEWORKS
    assert "qasm3" in STARTERS


def test_qasm3_starter_parses():
    result = build_circuit(STARTERS["qasm3"], "qasm3")
    assert result["ir"].n_qubits == 2
    assert len(result["ir"].ops) == 4


def test_qasm3_is_returned_verbatim():
    """QASM is data, not a program: it must not be round-tripped or rewritten."""
    source = STARTERS["qasm3"]
    assert build_circuit(source, "qasm3")["qasm3"] == source


def test_bad_qasm3_is_explained():
    with pytest.raises(CodeLabError) as exc:
        build_circuit("this is not qasm", "qasm3")
    assert "Could not parse your OpenQASM 3" in str(exc.value)


@pytest.mark.parametrize(
    "module",
    ["qiskit_aer", "matplotlib", "pandas", "networkx", "time", "heapq", "textwrap", "logging"],
)
def test_previously_blocked_safe_modules_now_import(module):
    code = f"import {module}\nfrom qiskit import QuantumCircuit\ncircuit = QuantumCircuit(1)"
    assert build_circuit(code, "qiskit")["ir"].n_qubits == 1


def test_opaque_instructions_are_decomposed():
    """initialize() has no direct QASM3 form; transpiling keeps it working."""
    code = "from qiskit import QuantumCircuit\nqc = QuantumCircuit(1)\nqc.initialize([0, 1], [0])\ncircuit = qc"
    assert build_circuit(code, "qiskit")["ir"].n_qubits == 1


def test_custom_unitary_is_decomposed():
    code = (
        "from qiskit import QuantumCircuit\nimport numpy as np\n"
        "qc = QuantumCircuit(1)\nqc.unitary(np.array([[0, 1], [1, 0]]), [0])\ncircuit = qc"
    )
    assert build_circuit(code, "qiskit")["ir"].n_qubits == 1


def test_unbound_parameter_gets_an_actionable_message():
    code = (
        "from qiskit import QuantumCircuit\nfrom qiskit.circuit import Parameter\n"
        "t = Parameter('t')\nqc = QuantumCircuit(1)\nqc.rx(t, 0)\ncircuit = qc"
    )
    with pytest.raises(CodeLabError) as exc:
        build_circuit(code, "qiskit")
    assert "unbound Parameter" in str(exc.value)
    assert "assign_parameters" in str(exc.value)


@pytest.mark.parametrize(
    "code",
    [
        "import logging\nlogging.os.system('touch /tmp/codelab_escape')\ncircuit=None",
        "import matplotlib\nmatplotlib.os.system('touch /tmp/codelab_escape')\ncircuit=None",
        "import logging\nlogging.os.popen('id')\ncircuit=None",
    ],
)
def test_os_is_not_reachable_through_permitted_modules(code):
    """Widening the allowlist must not open a path to os.system."""
    with pytest.raises(CodeLabError) as exc:
        build_circuit(code, "qiskit")
    assert "not available in the code lab" in str(exc.value)
