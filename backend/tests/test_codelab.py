"""Learner-written code must compile to a circuit -- and must not escape."""

from __future__ import annotations

import importlib.util

import pytest

from app.services import codelab
from app.services.codelab import (
    FRAMEWORKS,
    STARTERS,
    CodeLabError,
    build_circuit,
)


def _package_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False

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
    if framework == "cudaq" and not _package_present("cudaq"):
        pytest.skip("the CUDA-Q wheel ships only with the GPU image")
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


# --------------------------------------------------------------------------- #
# CUDA-Q framework: the learner writes a real cudaq.make_kernel() builder and
# we convert the Quake MLIR that CUDA-Q's own printer emits for it. The
# function under test lives inside the sandboxed child script template, so it
# is extracted verbatim -- exactly the code the child executes, no copy.
# --------------------------------------------------------------------------- #
_QUAKE_MLIR_BELL = """\
module attributes {quake.mangled_name_map = {...}} {
  func.func @__nvqpp__mlirgen__PythonKernelBuilderInstance() attributes {"cudaq-entrypoint", "cudaq-kernel"} {
    %cst = arith.constant 3.000000e-01 : f64
    %cst_0 = arith.constant 5.000000e-01 : f64
    %0 = quake.alloca !quake.veq<2>
    %1 = quake.extract_ref %0[0] : (!quake.veq<2>) -> !quake.ref
    quake.ry (%cst_0) %1 : (f64, !quake.ref) -> ()
    quake.rz (%cst) %1 : (f64, !quake.ref) -> ()
    %2 = quake.extract_ref %0[1] : (!quake.veq<2>) -> !quake.ref
    quake.x [%1] %2 : (!quake.ref, !quake.ref) -> ()
    %measOut = quake.mz %0 : (!quake.veq<2>) -> !cc.sequence<!cc.measure_handle>
    return
  }
}
"""


def _quake_parser():
    src = codelab._CHILD
    start = src.index("def _quake_to_qasm3")
    end = src.index("def to_qasm3")
    body = src[start:end].replace("{{", "{").replace("}}", "}")
    ns: dict = {}
    exec(compile(body, "<quake-parser-under-test>", "exec"), ns)
    return ns["_quake_to_qasm3"]


def test_quake_parser_translates_captured_mlir_exactly():
    parse = _quake_parser()
    out = parse(_QUAKE_MLIR_BELL)
    assert "ry(0.5) q[0];" in out
    assert "rz(0.3) q[0];" in out
    # a controlled x prints as quake.x with a bracketed control: that IS a cx
    assert "cx q[0], q[1];" in out
    assert "qubit[2] q;" in out
    assert "c[1] = measure q[1];" in out
    # and the emitted text must feed the platform's own importer cleanly
    from app.quantum.qasm3_codec import from_qasm3

    ir = from_qasm3(out, name="probe")
    assert ir.n_qubits == 2
    gates = [op.gate for op in ir.walk() if op.kind == "gate"]
    assert "ry" in gates and any(op.controls for op in ir.walk() if op.kind == "gate")


def test_quake_parser_refuses_flow_and_unknown_gates():
    parse = _quake_parser()
    with pytest.raises(ValueError, match="control flow"):
        parse("    %r = cc.loop body {\n")
    with pytest.raises(ValueError, match="not convertible"):
        parse(
            "%cst = arith.constant 1.0 : f64\n"
            "%0 = quake.alloca !quake.veq<1>\n"
            "%1 = quake.extract_ref %0[0]\n"
            "quake.pauli (%cst) [%1] : () -> ()\n"
        )
    with pytest.raises(ValueError, match="no qubits"):
        parse("module attributes {} {\n}\n")


def test_cudaq_framework_rejects_non_builder_objects():
    # No cudaq import needed: the conversion itself must reject anything that
    # is not a make_kernel() object, with the fix spelled out.
    code = "class NotAKernel:\n    pass\ncircuit = NotAKernel()\n"
    with pytest.raises(CodeLabError, match="cudaq.make_kernel"):
        build_circuit(code, "cudaq")


def test_cudaq_starter_round_trips_through_real_cudaq():
    """End to end on a machine that has the wheel: the starter kernel is built
    by CUDA-Q, printed by CUDA-Q, and lands as platform IR."""
    if not _package_present("cudaq"):
        pytest.skip("the CUDA-Q wheel ships only with the GPU image")
    built = build_circuit(STARTERS["cudaq"], "cudaq")
    ir = built["ir"]
    assert ir.n_qubits == 2
    gates = [op.gate for op in ir.walk() if op.kind == "gate"]
    assert "h" in gates and "x" in gates  # cx = x with a control
    assert ir.has_measurements()


def test_available_frameworks_hides_cudaq_without_the_wheel():
    listed = codelab.available_frameworks()
    assert "cudaq" in listed if _package_present("cudaq") else "cudaq" not in listed
    for core in ("qiskit", "cirq", "pennylane", "qasm3"):
        assert core in listed
