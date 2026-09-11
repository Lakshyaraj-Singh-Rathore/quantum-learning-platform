"""Regression tests for model-level bugs found in the Composer audit."""

import pytest

from app.quantum.inspect import inspect_circuit
from app.quantum.ir import CircuitIR, Op
from app.quantum.qasm3_codec import QasmError, from_qasm3


def test_same_layer_clbit_clash_auto_inserts_column():
    """Two measures into one clbit in one column silently lost a result."""
    ir = CircuitIR(n_qubits=2, n_clbits=2)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 0)
    ir.place(Op(kind="measure", qubits=[1], clbits=[0]), 0)
    layers = sorted(op.layer for op in ir.ops)
    assert layers == [0, 1], "the clashing measure must be pushed to a new column"


def test_distinct_clbits_share_a_layer():
    ir = CircuitIR(n_qubits=2, n_clbits=2)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 0)
    ir.place(Op(kind="measure", qubits=[1], clbits=[1]), 0)
    assert {op.layer for op in ir.ops} == {0}


def test_static_clbit_overwrite_is_reported():
    ir = CircuitIR(n_qubits=2, n_clbits=2)
    ir.place(Op(kind="gate", gate="x", qubits=[0]), 0)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 1)
    ir.place(Op(kind="measure", qubits=[1], clbits=[0]), 2)
    warnings = inspect_circuit(ir, "qiskit_aer", 100)["warnings"]
    assert any("c0" in w and "last measurement" in w for w in warnings)


def test_clean_circuit_has_no_overwrite_warning():
    ir = CircuitIR(n_qubits=2, n_clbits=2)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.append_measure_all()
    warnings = inspect_circuit(ir, "qiskit_aer", 100)["warnings"]
    assert not any("last measurement" in w for w in warnings)


@pytest.mark.parametrize(
    "src, needle",
    [
        ("qubit[2] q;\nbit[2] c;\nh q[7];", "qubit index 7"),
        ("qubit[2] q;\nbit[2] c;\nc[5] = measure q[0];", "clbit index 5"),
    ],
)
def test_import_rejects_out_of_range_indices(src, needle):
    """Imports used to yield a corrupt IR that only failed later, in a backend."""
    qasm = 'OPENQASM 3.0;\ninclude "stdgates.inc";\n' + src
    with pytest.raises(QasmError) as exc:
        from_qasm3(qasm)
    assert needle in str(exc.value)


def test_valid_import_still_works():
    qasm = (
        'OPENQASM 3.0;\ninclude "stdgates.inc";\n'
        "qubit[2] q;\nbit[2] c;\nh q[0];\ncx q[0], q[1];\nc[0] = measure q[0];"
    )
    ir = from_qasm3(qasm)
    assert ir.n_qubits == 2
    assert len(ir.ops) == 3
