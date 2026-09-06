"""OpenQASM 3 import/export round-tripping and the parameter grammar."""

import math

import pytest

from app.quantum.ir import CircuitIR, Condition, Op
from app.quantum.params import ParamError, eval_param_expr
from app.quantum.qasm3_codec import _parse_fallback, from_qasm3, to_qasm3


def test_param_grammar_accepts_pi_expressions():
    assert eval_param_expr("pi/2") == pytest.approx(math.pi / 2)
    assert eval_param_expr("3*pi/4") == pytest.approx(3 * math.pi / 4)
    assert eval_param_expr("-0.5*pi") == pytest.approx(-math.pi / 2)
    assert eval_param_expr("1.234") == pytest.approx(1.234)
    assert eval_param_expr("(pi + 2) / 2") == pytest.approx((math.pi + 2) / 2)


@pytest.mark.parametrize("bad", ["theta", "pi**2", "__import__('os')", "x + 1", ""])
def test_param_grammar_rejects_everything_else(bad):
    with pytest.raises(ParamError):
        eval_param_expr(bad)


def test_bell_roundtrip():
    ir = CircuitIR(name="bell", n_qubits=2)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="cx", qubits=[0, 1]), 1)
    ir.append_measure_all()

    qasm = to_qasm3(ir)
    assert "OPENQASM 3.0;" in qasm
    assert "qubit[2] q;" in qasm

    back = from_qasm3(qasm)
    assert back.n_qubits == 2
    assert [o.gate for o in back.ops if o.kind == "gate"] == ["h", "x"]
    assert sum(1 for o in back.ops if o.kind == "measure") == 2


def test_mcx_export_and_import():
    ir = CircuitIR(name="mcx", n_qubits=4)
    ir.place(Op(kind="gate", gate="mcx", qubits=[0, 1, 2, 3]), 0)
    qasm = to_qasm3(ir)
    assert "ctrl(3) @ x" in qasm

    back = from_qasm3(qasm)
    op = back.ops[0]
    assert op.gate == "x"
    assert op.controls == [0, 1, 2]
    assert op.qubits == [3]


def test_control_flow_roundtrip_both_parsers():
    ir = CircuitIR(name="cf", n_qubits=2)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 0)
    ir.place(
        Op(
            kind="if",
            condition=Condition(type="bit_eq", bit=0, value=1),
            body=[Op(kind="gate", gate="x", qubits=[1])],
            else_body=[Op(kind="gate", gate="z", qubits=[1])],
        ),
        1,
    )
    ir.place(
        Op(
            kind="while",
            condition=Condition(type="bit_eq", bit=0, value=1),
            body=[Op(kind="gate", gate="x", qubits=[0]), Op(kind="measure", qubits=[0])],
        ),
        2,
    )
    ir.place(Op(kind="for", loop_n=3, body=[Op(kind="gate", gate="h", qubits=[1])]), 3)

    qasm = to_qasm3(ir)
    for parser in (from_qasm3, _parse_fallback):
        back = parser(qasm, "cf")
        kinds = [o.kind for o in back.ops]
        assert kinds == ["measure", "if", "while", "for"]
        assert back.is_dynamic()
        assert back.ops[1].else_body[0].gate == "z"
        assert back.ops[3].loop_n == 3


def test_bitstring_condition_roundtrip():
    ir = CircuitIR(name="bs", n_qubits=3)
    ir.place(
        Op(
            kind="if",
            condition=Condition(type="bitstring_eq", start=0, end=3, value="101"),
            body=[Op(kind="gate", gate="x", qubits=[0])],
        ),
        0,
    )
    qasm = to_qasm3(ir)
    assert 'c[0:2] == "101"' in qasm

    for parser in (from_qasm3, _parse_fallback):
        cond = parser(qasm, "bs").ops[0].condition
        assert cond.type == "bitstring_eq"
        assert (cond.start, cond.end) == (0, 3)
        assert cond.evaluate([1, 0, 1]) is True
        assert cond.evaluate([0, 0, 1]) is False


def test_parameterized_gate_roundtrip():
    ir = CircuitIR(name="p", n_qubits=1)
    ir.place(Op(kind="gate", gate="rx", qubits=[0], params=["pi/2"]), 0)
    qasm = to_qasm3(ir)
    assert "rx(pi/2)" in qasm
    op = from_qasm3(qasm).ops[0]
    assert op.params[0].value == pytest.approx(math.pi / 2)


def test_unsupported_gate_is_rejected():
    with pytest.raises(ValueError):
        Op(kind="gate", gate="frobnicate", qubits=[0])
