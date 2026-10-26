"""Comprehensive verification of MCX arbitrary controls and Measure gate parity.

Validates:
1. MCX gate with arbitrary controls (1, 2, 3, 4, 5+ controls) on both CPU and CUDA-Q GPU.
2. Negative controls on MCX.
3. Unmeasured circuit execution: circuits run freely without requiring measurements.
4. Correct classical bit register mapping for explicit measurements.
5. Circuit inspector sanity: no nag warnings when measurements are omitted.
"""

from __future__ import annotations

import pytest
from app.quantum.ir import CircuitIR, Op
from app.quantum.inspect import inspect_circuit, summarize_circuit
from app.quantum.backends.qiskit_aer import run as run_qiskit
from app.quantum.backends.cudaq_sim import run as run_cudaq, is_available as is_cudaq_available


@pytest.fixture(autouse=True)
def zero_cooldown(monkeypatch):
    """Disable GPU slot cooldown delay between automated test runs."""
    from app.config import get_settings
    settings = get_settings()
    monkeypatch.setattr(settings, "gpu_cooldown_seconds", 0.0)


def test_unmeasured_circuit_executes_without_errors():
    """Verify that a circuit without any measure operations executes successfully

    and evaluates the exact statevector directly (no measurement gimmick).
    """
    ir = CircuitIR(
        name="bell_unmeasured",
        n_qubits=2,
        n_clbits=2,
        ops=[
            Op(kind="gate", gate="h", qubits=[0], layer=0),
            Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=1),
        ],
    )
    # 1. Inspector reports ok and no measurement warning
    insp = inspect_circuit(ir)
    assert insp["ok"] is True
    assert not any("Measure All" in w for w in insp["warnings"])

    # 2. Qiskit Aer runs and returns Bell state counts & statevector
    res_aer = run_qiskit(ir, shots=1024)
    assert "00" in res_aer["counts"]
    assert "11" in res_aer["counts"]
    assert res_aer["statevector"] is not None
    # 50/50 probabilities
    assert 0.40 <= res_aer["probabilities"]["00"] <= 0.60
    assert 0.40 <= res_aer["probabilities"]["11"] <= 0.60


def test_unmeasured_circuit_cudaq_gpu():
    """Verify unmeasured Bell state runs on NVIDIA CUDA-Q GPU."""
    available, _ = is_cudaq_available()
    if not available:
        pytest.skip("CUDA-Q GPU not available")

    ir = CircuitIR(
        name="bell_gpu_unmeasured",
        n_qubits=2,
        n_clbits=2,
        ops=[
            Op(kind="gate", gate="h", qubits=[0], layer=0),
            Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=1),
        ],
    )
    res_gpu = run_cudaq(ir, shots=1024)
    assert "00" in res_gpu["counts"]
    assert "11" in res_gpu["counts"]
    assert res_gpu["statevector"] is not None
    assert 0.40 <= res_gpu["probabilities"]["00"] <= 0.60
    assert 0.40 <= res_gpu["probabilities"]["11"] <= 0.60


@pytest.mark.parametrize("num_controls", [1, 2, 3, 4, 5])
def test_mcx_arbitrary_controls_qiskit(num_controls: int):
    """Verify MCX (C^n X) flips the target if and only if all n controls are |1>."""
    n_qubits = num_controls + 1
    target = num_controls
    controls = list(range(num_controls))

    # Case A: All controls prepared to |1> -> target must flip to |1>
    ops_all_ones = [Op(kind="gate", gate="x", qubits=[c], layer=0) for c in controls]
    ops_all_ones.append(Op(kind="gate", gate="x", qubits=[target], controls=controls, layer=1))

    ir_all_ones = CircuitIR(
        name=f"mcx_{num_controls}_ones",
        n_qubits=n_qubits,
        n_clbits=n_qubits,
        ops=ops_all_ones,
    )

    res_ones = run_qiskit(ir_all_ones, shots=512)
    # In Qiskit bit ordering, target is leftmost bit (highest index qubit)
    # All qubits are |1>, so bitstring is "1" * n_qubits
    expected_ones = "1" * n_qubits
    assert res_ones["counts"].get(expected_ones, 0) == 512

    # Case B: One control is |0> (qubit 0 is not flipped) -> target must remain |0>
    ops_partial = [Op(kind="gate", gate="x", qubits=[c], layer=0) for c in controls[1:]]
    ops_partial.append(Op(kind="gate", gate="x", qubits=[target], controls=controls, layer=1))

    ir_partial = CircuitIR(
        name=f"mcx_{num_controls}_partial",
        n_qubits=n_qubits,
        n_clbits=n_qubits,
        ops=ops_partial,
    )
    res_partial = run_qiskit(ir_partial, shots=512)
    # Target (qubit num_controls) must be 0
    for bitstring in res_partial["counts"]:
        target_bit = bitstring[-(target + 1)]
        assert target_bit == "0"


@pytest.mark.parametrize("num_controls", [1, 2, 3, 4])
def test_mcx_arbitrary_controls_cudaq_gpu(num_controls: int):
    """Verify MCX with arbitrary controls executes on CUDA-Q GPU."""
    available, _ = is_cudaq_available()
    if not available:
        pytest.skip("CUDA-Q GPU not available")

    n_qubits = num_controls + 1
    target = num_controls
    controls = list(range(num_controls))

    # Prepare all controls to |1> -> target must flip to |1>
    ops = [Op(kind="gate", gate="x", qubits=[c], layer=0) for c in controls]
    ops.append(Op(kind="gate", gate="x", qubits=[target], controls=controls, layer=1))

    ir = CircuitIR(
        name=f"mcx_{num_controls}_gpu",
        n_qubits=n_qubits,
        n_clbits=n_qubits,
        ops=ops,
    )
    res = run_cudaq(ir, shots=256)
    expected = "1" * n_qubits
    assert res["counts"].get(expected, 0) == 256


def test_mcx_with_negative_controls():
    """Verify MCX with negative control fires when negative control is |0>."""
    # 3 qubits: q0 (positive control), q1 (negative control), q2 (target)
    # Fire condition: q0 == 1 AND q1 == 0 -> target q2 flips
    ops = [
        Op(kind="gate", gate="x", qubits=[0], layer=0),  # q0 = 1, q1 = 0
        Op(kind="gate", gate="x", qubits=[2], controls=[0], neg_controls=[1], layer=1),
    ]
    ir = CircuitIR(name="mcx_neg", n_qubits=3, n_clbits=3, ops=ops)
    res = run_qiskit(ir, shots=256)
    # Qiskit order: q2 q1 q0 -> "101"
    assert res["counts"].get("101", 0) == 256


def test_measure_classical_bit_routing():
    """Verify that routing measurement to a designated classical bit maps correctly."""
    # Measure q1 into c0, leaving q0 unmeasured
    ir = CircuitIR(
        name="routing_test",
        n_qubits=2,
        n_clbits=2,
        ops=[
            Op(kind="gate", gate="x", qubits=[1], layer=0),
            Op(kind="measure", qubits=[1], clbits=[0], layer=1),
        ],
    )
    res = run_qiskit(ir, shots=100)
    # c0 received 1 from q1. Padded to n_clbits (2): "01"
    assert "01" in res["counts"]
    assert res["counts"]["01"] == 100
