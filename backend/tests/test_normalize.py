"""Transpilation to the portable basis and cross-backend agreement."""

import pytest

from app.quantum.backends import cirq_sim, pennylane_sim, qiskit_aer
from app.quantum.ir import CircuitIR, Op
from app.quantum.normalize import PORTABLE_BASIS, NormalizeError, normalize, to_qiskit


def _bell() -> CircuitIR:
    ir = CircuitIR(name="bell", n_qubits=2)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="cx", qubits=[0, 1]), 1)
    ir.append_measure_all()
    return ir


def test_transpiles_to_portable_basis():
    ir = CircuitIR(name="mix", n_qubits=3)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="t", qubits=[1]), 0)
    ir.place(Op(kind="gate", gate="mcx", qubits=[0, 1, 2]), 1)
    ir.place(Op(kind="gate", gate="swap", qubits=[0, 1]), 2)

    circuit = normalize(ir)
    used = set(circuit.count_ops()) - {"measure", "barrier", "reset"}
    assert used <= set(PORTABLE_BASIS)


def test_controlled_non_x_gate_keeps_its_controls():
    ir = CircuitIR(name="cz", n_qubits=2)
    ir.place(Op(kind="gate", gate="z", qubits=[1], controls=[0]), 0)
    circuit = to_qiskit(ir, include_measurements=False)
    assert circuit.data[0].operation.num_qubits == 2


def test_for_loop_is_unrolled_statically():
    ir = CircuitIR(name="loop", n_qubits=1)
    ir.place(Op(kind="for", loop_n=4, body=[Op(kind="gate", gate="x", qubits=[0])]), 0)
    circuit = to_qiskit(ir, include_measurements=False)
    assert circuit.count_ops()["x"] == 4


def test_runtime_control_flow_cannot_compile_statically():
    ir = CircuitIR(name="dyn", n_qubits=1)
    ir.place(Op(kind="while", loop_bit=0, body=[Op(kind="gate", gate="x", qubits=[0])]), 0)
    with pytest.raises(NormalizeError):
        to_qiskit(ir)


@pytest.mark.parametrize("backend", [qiskit_aer, cirq_sim, pennylane_sim])
def test_all_static_backends_agree_on_bell(backend):
    result = backend.run(_bell(), shots=2000, seed=11)
    counts = result["counts"]
    assert set(counts) <= {"00", "11"}
    assert counts.get("00", 0) / 2000 == pytest.approx(0.5, abs=0.08)
    assert result["metadata"]["backend"] == backend.NAME


@pytest.mark.parametrize("backend", [qiskit_aer, cirq_sim, pennylane_sim])
def test_bit_order_is_consistent_across_backends(backend):
    """Only qubit 0 is excited, so the bitstring must be 001, not 100."""
    ir = CircuitIR(name="asym", n_qubits=3)
    ir.place(Op(kind="gate", gate="x", qubits=[0]), 0)
    ir.append_measure_all()
    assert list(backend.run(ir, shots=64, seed=3)["counts"]) == ["001"]


def test_statevectors_match_across_backends():
    ir = CircuitIR(name="phase", n_qubits=2)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="t", qubits=[0]), 1)
    ir.place(Op(kind="gate", gate="cx", qubits=[0, 1]), 2)
    ir.append_measure_all()

    vectors = [
        backend.run(ir, shots=8, seed=1)["statevector"]
        for backend in (qiskit_aer, cirq_sim, pennylane_sim)
    ]
    for other in vectors[1:]:
        for (re_a, im_a), (re_b, im_b) in zip(vectors[0], other):
            assert re_a == pytest.approx(re_b, abs=1e-5)
            assert im_a == pytest.approx(im_b, abs=1e-5)
