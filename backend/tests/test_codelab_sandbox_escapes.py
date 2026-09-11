"""Sandbox escape regressions for the Code Lab.

Each case here was a *working* remote-code-execution path found during the
full-system audit. The Code Lab executes untrusted learner code, so these
must stay closed.
"""

import pytest

from app.services.codelab import CodeLabError, build_circuit

QISKIT_BELL = (
    "from qiskit import QuantumCircuit\n"
    "circuit = QuantumCircuit(2, 2)\n"
    "circuit.h(0)\n"
    "circuit.cx(0, 1)\n"
    "circuit.measure([0, 1], [0, 1])\n"
)


def _err(code: str, framework: str = "qiskit") -> str:
    """Run untrusted code and return the error it produced."""
    with pytest.raises(CodeLabError) as exc:
        build_circuit(code, framework)
    return str(exc.value)


@pytest.mark.parametrize(
    "name, code",
    [
        # __import__ received globals=None on a direct call, so the allowlist
        # was skipped entirely -- full RCE.
        ("builtins_import", "__builtins__['__import__']('os').system('true')\ncircuit=None"),
        ("eval_import", "eval(\"__import__('os').system('true')\")\ncircuit=None"),
        ("exec_import", "exec(\"import os\")\ncircuit=None"),
        ("importlib", "__builtins__['__import__']('importlib')\ncircuit=None"),
        ("plain_os", "import os\ncircuit=None"),
        ("subprocess", "import subprocess\ncircuit=None"),
        ("socket", "import socket\ncircuit=None"),
    ],
)
def test_import_escapes_are_blocked(name, code):
    assert "not allowed" in _err(code) or "not available" in _err(code)


def test_ctypes_via_numpy_is_blocked():
    """ctypes was reachable as an attribute of already-imported numpy."""
    code = (
        "import numpy\n"
        "numpy.ctypeslib.ctypes.CDLL('libc.so.6').system(b'true')\n"
        "circuit=None"
    )
    assert "ctypes is not available" in _err(code)


def test_popen_via_subclass_walk_is_blocked():
    """subprocess.Popen is reachable through the type hierarchy, no import."""
    code = (
        "cs=[c for c in ().__class__.__base__.__subclasses__() "
        "if 'Popen' in c.__name__]\n"
        "cs[0](['true'])\n"
        "circuit=None"
    )
    assert "subprocess is not available" in _err(code)


@pytest.mark.parametrize(
    "code",
    [
        "open('/etc/passwd').read()\ncircuit=None",
        "open('/tmp/codelab_should_not_exist','w').write('x')\ncircuit=None",
    ],
)
def test_file_access_is_blocked(code):
    assert "file access is disabled" in _err(code)


def test_missing_circuit_variable_is_explained():
    assert "never defined `circuit`" in _err("x = 1")


# --------------------------------------------------------------------- sanity
# The hardening must not break legitimate programs.


def test_qiskit_still_builds():
    result = build_circuit(QISKIT_BELL, "qiskit")
    assert result["ir"].n_qubits == 2


def test_cirq_still_builds():
    code = (
        "import cirq\n"
        "q = cirq.LineQubit.range(2)\n"
        "circuit = cirq.Circuit([cirq.H(q[0]), cirq.CNOT(q[0], q[1]), "
        "cirq.measure(*q)])\n"
    )
    assert build_circuit(code, "cirq")["ir"].n_qubits == 2


def test_pennylane_still_builds():
    code = (
        "import pennylane as qml\n"
        "dev = qml.device('default.qubit', wires=2)\n"
        "@qml.qnode(dev)\n"
        "def circuit():\n"
        "    qml.Hadamard(0)\n"
        "    qml.CNOT([0, 1])\n"
        "    return qml.probs(wires=[0, 1])\n"
    )
    assert build_circuit(code, "pennylane")["ir"].n_qubits == 2


def test_numpy_and_scipy_remain_usable():
    code = (
        "import numpy as np\n"
        "import scipy.linalg\n"
        "from qiskit import QuantumCircuit\n"
        "circuit = QuantumCircuit(1)\n"
        "circuit.rx(float(np.pi / 2), 0)\n"
    )
    assert build_circuit(code, "qiskit")["ir"].n_qubits == 1
