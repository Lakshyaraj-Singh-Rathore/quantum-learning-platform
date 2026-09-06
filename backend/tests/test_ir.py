"""Circuit IR rules: collisions, controls and the two measurement buttons."""

import pytest

from app.quantum.ir import CircuitIR, Op


def test_collision_inserts_column_globally():
    ir = CircuitIR(name="c", n_qubits=3)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="x", qubits=[2]), 1)

    # dropping on q0 at layer 0 collides -> everything at layer >= 0 shifts right
    ir.place(Op(kind="gate", gate="y", qubits=[0]), 0)

    by_gate = {o.gate: o.layer for o in ir.ops}
    assert by_gate["y"] == 0
    assert by_gate["h"] == 1
    assert by_gate["x"] == 2  # shifted even though q2 was free


def test_no_collision_keeps_layer():
    ir = CircuitIR(name="c", n_qubits=2)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="x", qubits=[1]), 0)
    assert [o.layer for o in ir.ops] == [0, 0]


def test_controls_count_as_occupancy():
    ir = CircuitIR(name="c", n_qubits=3)
    ir.place(Op(kind="gate", gate="cx", qubits=[0, 1]), 0)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    assert ir.ops[0].layer != ir.ops[1].layer


def test_mcx_normalizes_to_controls():
    op = Op(kind="gate", gate="mcx", qubits=[0, 1, 2, 3])
    assert op.gate == "x"
    assert op.controls == [0, 1, 2]
    assert op.qubits == [3]


def test_control_target_overlap_rejected():
    with pytest.raises(ValueError):
        Op(kind="gate", gate="x", qubits=[0], controls=[0])


def test_measure_all_append_preserves_existing():
    ir = CircuitIR(name="m", n_qubits=2)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 1)  # mid-circuit
    ir.append_measure_all()

    measures = [o for o in ir.ops if o.kind == "measure"]
    assert len(measures) == 3  # original kept + 2 terminal


def test_normalize_terminal_measurement_is_top_level_only():
    ir = CircuitIR(name="m", n_qubits=2)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 0)
    ir.place(
        Op(kind="box", box_name="inner", body=[Op(kind="measure", qubits=[1], clbits=[1])]), 1
    )

    warnings = ir.normalize_terminal_measurement()

    top_level = [o for o in ir.ops if o.kind == "measure"]
    assert len(top_level) == 2  # exactly one terminal layer
    assert len({o.layer for o in top_level}) == 1

    box = next(o for o in ir.ops if o.kind == "box")
    assert len(box.body) == 1  # nested measurement untouched
    assert any("dynamic" in w for w in warnings)


def test_is_dynamic_detection():
    static = CircuitIR(name="s", n_qubits=1)
    static.place(Op(kind="measure", qubits=[0], clbits=[0]), 0)
    assert not static.is_dynamic()

    dynamic = CircuitIR(name="d", n_qubits=1)
    dynamic.place(
        Op(
            kind="while",
            loop_bit=0,
            body=[Op(kind="gate", gate="x", qubits=[0])],
        ),
        0,
    )
    assert dynamic.is_dynamic()


def test_out_of_range_qubit_rejected():
    with pytest.raises(ValueError):
        CircuitIR(
            name="bad", n_qubits=2, ops=[Op(kind="gate", gate="h", qubits=[5], layer=0)]
        )
