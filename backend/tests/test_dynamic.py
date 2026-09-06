"""Dynamic execution engine: control flow, the while cap and limits."""

import pytest

from app.config import get_settings
from app.quantum.backends import dynamic_qiskit
from app.quantum.backends.dynamic_qiskit import DynamicLimitError, WhileCapExceeded
from app.quantum.ir import CircuitIR, Condition, Op


def _forever_loop() -> CircuitIR:
    """c[0] is set to 1 and the body never clears it -> must hit the cap."""
    ir = CircuitIR(name="forever", n_qubits=1, n_clbits=1)
    ir.place(Op(kind="gate", gate="x", qubits=[0]), 0)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 1)
    ir.place(
        Op(
            kind="while",
            condition=Condition(type="bit_eq", bit=0, value=1),
            body=[Op(kind="gate", gate="id", qubits=[0])],
        ),
        2,
    )
    return ir


def test_while_cap_stops_infinite_loop():
    result = dynamic_qiskit.run(_forever_loop(), shots=3, seed=1)
    assert result["metadata"]["while_cap_hits"] == 3
    assert result["metadata"]["while_cap"] == get_settings().while_cap
    assert any("cap" in w.lower() for w in result["metadata"]["warnings"])


def test_while_cap_can_raise_in_strict_mode():
    with pytest.raises(WhileCapExceeded):
        dynamic_qiskit.run(_forever_loop(), shots=1, strict_while_cap=True)


def test_while_loop_terminates_and_forces_zero():
    """Flip-and-remeasure until c[0] == 0; every shot must end at 0."""
    ir = CircuitIR(name="force0", n_qubits=1, n_clbits=1)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 1)
    ir.place(
        Op(
            kind="while",
            condition=Condition(type="bit_eq", bit=0, value=1),
            body=[
                Op(kind="gate", gate="x", qubits=[0]),
                Op(kind="measure", qubits=[0], clbits=[0]),
            ],
        ),
        2,
    )
    result = dynamic_qiskit.run(ir, shots=200, seed=5)
    assert result["counts"] == {"0": 200}
    assert result["metadata"]["while_cap_hits"] == 0


def test_if_else_branches_on_measurement():
    ir = CircuitIR(name="ifelse", n_qubits=2)
    ir.place(Op(kind="gate", gate="x", qubits=[0]), 0)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 1)
    ir.place(
        Op(
            kind="if",
            condition=Condition(type="bit_eq", bit=0, value=1),
            body=[Op(kind="gate", gate="x", qubits=[1])],
            else_body=[Op(kind="gate", gate="id", qubits=[1])],
        ),
        2,
    )
    ir.place(Op(kind="measure", qubits=[1], clbits=[1]), 3)

    # c[0] is deterministically 1, so the if-branch always runs
    assert dynamic_qiskit.run(ir, shots=50, seed=2)["counts"] == {"11": 50}


def test_for_loop_unrolls_in_dynamic_engine():
    ir = CircuitIR(name="for", n_qubits=1, n_clbits=1)
    ir.place(Op(kind="for", loop_n=3, body=[Op(kind="gate", gate="x", qubits=[0])]), 0)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 1)
    # odd number of flips -> |1>
    assert dynamic_qiskit.run(ir, shots=20, seed=1)["counts"] == {"1": 20}


def test_reset_collapses_qubit_to_zero():
    ir = CircuitIR(name="reset", n_qubits=1, n_clbits=1)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="reset", qubits=[0]), 1)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 2)
    ir.place(
        Op(kind="if", condition=Condition(type="bit_eq", bit=0, value=1), body=[]), 3
    )
    assert dynamic_qiskit.run(ir, shots=100, seed=4)["counts"] == {"0": 100}


def test_qubit_limit_enforced():
    settings = get_settings()
    ir = CircuitIR(name="big", n_qubits=settings.max_dynamic_qubits + 1)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 0)
    ir.place(Op(kind="if", condition=Condition(type="bit_eq", bit=0, value=1), body=[]), 1)
    with pytest.raises(DynamicLimitError):
        dynamic_qiskit.run(ir, shots=1)


def test_shot_limit_enforced():
    settings = get_settings()
    ir = CircuitIR(name="shots", n_qubits=1, n_clbits=1)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 0)
    ir.place(Op(kind="if", condition=Condition(type="bit_eq", bit=0, value=1), body=[]), 1)
    with pytest.raises(DynamicLimitError):
        dynamic_qiskit.run(ir, shots=settings.max_dynamic_shots + 1)
