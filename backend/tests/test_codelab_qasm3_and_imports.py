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


# --- Regression: gates that frameworks emit via qelib1.inc / u3 ------------
# Qiskit's qasm2.loads() does not define qelib1.inc gates unless you pass
# LEGACY_CUSTOM_INSTRUCTIONS, so a plain SWAP used to break both Cirq and
# PennyLane. u3 (from Cirq's PhasedXZGate) parses but is not in the IR gate
# set, so it has to be decomposed.

def _build(framework, code):
    from app.services.codelab import build_circuit

    return build_circuit(code, framework)


def test_cirq_swap_round_trips():
    res = _build("cirq", (
        "import cirq\n"
        "q = cirq.LineQubit.range(2)\n"
        "circuit = cirq.Circuit([cirq.SWAP(q[0], q[1])])\n"
    ))
    assert any(getattr(op, "gate", None) == "swap" for op in res["ir"].ops)


def test_cirq_sx_round_trips():
    res = _build("cirq", (
        "import cirq\n"
        "q = cirq.LineQubit.range(1)\n"
        "circuit = cirq.Circuit([cirq.X(q[0]) ** 0.5])\n"
    ))


def test_cirq_phasedxz_is_decomposed_not_rejected():
    res = _build("cirq", (
        "import cirq\n"
        "q = cirq.LineQubit.range(1)\n"
        "g = cirq.PhasedXZGate(x_exponent=0.5, z_exponent=0.2, "
        "axis_phase_exponent=0.1)\n"
        "circuit = cirq.Circuit([g(q[0])])\n"
    ))
    gates = {getattr(op, "gate", None) for op in res["ir"].ops}
    assert "u3" not in gates


def test_pennylane_swap_round_trips():
    res = _build("pennylane", (
        "import pennylane as qml\n"
        "dev = qml.device('default.qubit', wires=2)\n"
        "@qml.qnode(dev)\n"
        "def circuit():\n"
        "    qml.PauliX(0)\n"
        "    qml.SWAP(wires=[0, 1])\n"
        "    return qml.probs(wires=[0, 1])\n"
    ))
    assert any(getattr(op, "gate", None) == "swap" for op in res["ir"].ops)


def test_pennylane_qnode_with_args_gets_actionable_message():
    from app.services.codelab import CodeLabError

    with pytest.raises(CodeLabError) as exc:
        _build("pennylane", (
            "import pennylane as qml\n"
            "dev = qml.device('default.qubit', wires=1)\n"
            "@qml.qnode(dev)\n"
            "def circuit(theta):\n"
            "    qml.RX(theta, wires=0)\n"
            "    return qml.probs(wires=0)\n"
        ))
    assert "concrete values" in str(exc.value) or "defaults" in str(exc.value)
