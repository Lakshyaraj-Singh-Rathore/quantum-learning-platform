"""Noise model behaviour: clamping, readout vs decoherence, virtual-Z."""

from __future__ import annotations

from app.quantum.backends import qiskit_aer as aer
from app.quantum.inspect import compute_run_hash
from app.quantum.ir import CircuitIR
from app.quantum.noise import NoiseParams, total_variation

BELL = {
    "n_qubits": 2,
    "n_clbits": 2,
    "ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
    ],
}


def _probs(counts: dict[str, int]) -> dict[str, float]:
    total = sum(counts.values()) or 1
    return {k: v / total for k, v in counts.items()}


def test_t2_is_clamped_to_twice_t1():
    """T2 > 2*T1 is unphysical and makes Aer raise; clamp and report it."""
    clean, notes = NoiseParams(t1_us=10.0, t2_us=100.0).clamped()
    assert clean.t2_us == 20.0
    assert any("clamped" in n.lower() for n in notes)


def test_readout_percentage_is_normalised():
    clean, notes = NoiseParams(readout_error=2.0).clamped()
    assert abs(clean.readout_error - 0.02) < 1e-12
    assert notes


def test_noise_off_leaves_bell_clean():
    result = aer.run(CircuitIR.model_validate(BELL), shots=2000, seed=7)
    probabilities = _probs(result["counts"])
    assert probabilities.get("01", 0.0) + probabilities.get("10", 0.0) < 0.01
    assert result["metadata"]["noise"]["enabled"] is False


def test_readout_error_leaks_counts_without_touching_the_state():
    """Readout error is a measurement fault, so it only moves counts."""
    noise = NoiseParams(
        enabled=True, t1_us=1e9, t2_us=1e9, readout_error=0.20
    )
    result = aer.run(CircuitIR.model_validate(BELL), shots=4000, seed=7, noise=noise)
    probabilities = _probs(result["counts"])
    leakage = probabilities.get("01", 0.0) + probabilities.get("10", 0.0)
    # Two independent bits each flipped with p=0.2 -> ~32% of shots land off-support.
    assert 0.20 < leakage < 0.45
    assert result["metadata"]["noise"]["enabled"] is True


def test_strong_decoherence_degrades_the_distribution():
    noise = NoiseParams(
        enabled=True,
        t1_us=1.0,
        t2_us=1.0,
        readout_error=0.0,
        gate_time_1q_us=0.6,
        gate_time_2q_us=2.0,
    )
    ideal = _probs(aer.run(CircuitIR.model_validate(BELL), shots=4000, seed=3)["counts"])
    noisy = _probs(
        aer.run(CircuitIR.model_validate(BELL), shots=4000, seed=3, noise=noise)["counts"]
    )
    assert total_variation(ideal, noisy) > 0.05


def test_virtual_z_gates_take_no_thermal_error():
    """Z is a frame change in software, so it must not decohere the qubit."""
    circuit = {
        "n_qubits": 1,
        "n_clbits": 1,
        "ops": [
            {"kind": "gate", "gate": "z", "qubits": [0], "layer": 0},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
        ],
    }
    noise = NoiseParams(enabled=True, t1_us=0.5, t2_us=0.5, readout_error=0.0)
    result = aer.run(CircuitIR.model_validate(circuit), shots=1000, seed=1, noise=noise)
    assert result["counts"].get("0", 0) == 1000


def test_run_hash_separates_noisy_from_ideal_runs():
    """Otherwise a noisy request would be served a cached ideal result."""
    ideal = compute_run_hash(BELL, "qiskit_aer", 1024, "auto", None)
    noisy = compute_run_hash(
        BELL, "qiskit_aer", 1024, "auto", {"enabled": True, "t1_us": 10.0}
    )
    other = compute_run_hash(
        BELL, "qiskit_aer", 1024, "auto", {"enabled": True, "t1_us": 20.0}
    )
    assert ideal != noisy
    assert noisy != other
