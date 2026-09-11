"""Regression: a reversed CNOT must be reported, not silently mis-simulated.

Dropping the X on q0 and the control on q1 (after H on q0) builds
CX(control=q1, target=q0). That is separable -- it measures as
{'00', '01'} with entanglement 0 -- and looks like a broken simulator to a
learner who expected a Bell pair.
"""

import pytest

from app.quantum.inspect import inspect_circuit
from app.quantum.ir import CircuitIR, Op


def _bell_attempt(control: int, target: int) -> CircuitIR:
    ir = CircuitIR(n_qubits=2, n_clbits=2)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="x", qubits=[target], controls=[control]), 1)
    ir.append_measure_all()
    return ir


def _control_warnings(ir: CircuitIR) -> list[str]:
    return [
        w
        for w in inspect_circuit(ir, "qiskit_aer", 1024)["warnings"]
        if "swap the control and the target" in w
    ]


def test_reversed_cnot_is_flagged():
    warnings = _control_warnings(_bell_attempt(control=1, target=0))
    assert warnings, "a control that is still |0> must be reported"
    assert "q1" in warnings[0] and "q0" in warnings[0]


def test_correct_bell_pair_is_not_flagged():
    assert _control_warnings(_bell_attempt(control=0, target=1)) == []


def test_reversed_cnot_really_is_separable():
    """Guards the premise: the warning describes a real physical difference."""
    from app.quantum.backends.qiskit_aer import run

    reversed_counts = run(_bell_attempt(1, 0), shots=1024, seed=1)["counts"]
    correct = run(_bell_attempt(0, 1), shots=1024, seed=1)
    assert set(reversed_counts) == {"00", "01"}
    assert set(correct["counts"]) == {"00", "11"}
    assert correct["metadata"]["metrics"]["entanglement_entropy"] == pytest.approx(1.0)


def test_toffoli_with_idle_controls_is_flagged():
    ir = CircuitIR(n_qubits=3, n_clbits=3)
    ir.place(Op(kind="gate", gate="x", qubits=[2], controls=[0, 1]), 0)
    assert _control_warnings(ir)


def test_toffoli_with_prepared_controls_is_not_flagged():
    ir = CircuitIR(n_qubits=3, n_clbits=3)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="h", qubits=[1]), 0)
    ir.place(Op(kind="gate", gate="x", qubits=[2], controls=[0, 1]), 1)
    assert _control_warnings(ir) == []


def test_partially_prepared_controls_are_not_flagged():
    """Only an entirely idle control set is suspicious."""
    ir = CircuitIR(n_qubits=3, n_clbits=3)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="x", qubits=[2], controls=[0, 1]), 1)
    assert _control_warnings(ir) == []
