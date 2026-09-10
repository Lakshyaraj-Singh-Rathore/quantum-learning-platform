"""Timeline stepping, entanglement metrics and count-key padding."""

from __future__ import annotations

from app.quantum.backends import qiskit_aer as aer
from app.quantum.ir import CircuitIR
from app.quantum.noise import NoiseParams, entanglement_entropy
from app.quantum.timeline import build_timeline

import numpy as np

BELL_OPS = [
    {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
    {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
]


def _ir(ops, n_qubits=2, n_clbits=2):
    return CircuitIR.model_validate(
        {"n_qubits": n_qubits, "n_clbits": n_clbits, "ops": ops}
    )


def test_entanglement_entropy_separates_product_from_bell():
    root = 1 / np.sqrt(2)
    product = np.array([root, root, 0, 0], dtype=complex)  # H on q0 only
    entropy, concurrence = entanglement_entropy(product, 2)
    assert entropy < 1e-9
    assert concurrence is not None and concurrence < 1e-6

    bell = np.array([root, 0, 0, root], dtype=complex)
    entropy, concurrence = entanglement_entropy(bell, 2)
    assert abs(entropy - 1.0) < 1e-9
    assert abs(concurrence - 1.0) < 1e-6


def test_timeline_tracks_entanglement_appearing_at_the_cnot():
    timeline = build_timeline(_ir(BELL_OPS))
    assert timeline["supported"]
    steps = timeline["steps"]
    assert len(steps) == 3  # initial + 2 gates

    assert steps[0]["entanglement_entropy"] == 0.0
    assert steps[1]["entanglement_entropy"] < 1e-9  # after H, still separable
    assert abs(steps[2]["entanglement_entropy"] - 1.0) < 1e-9
    assert steps[2]["entangled"] is True


def test_timeline_stops_showing_state_after_measurement():
    """A measurement collapses the register, so no single statevector exists."""
    ops = BELL_OPS + [
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2}
    ]
    steps = build_timeline(_ir(ops))["steps"]
    assert "statevector" in steps[2]
    assert "state_unavailable" in steps[3]
    assert "no longer one pure state" in steps[3]["state_unavailable"]


def test_timeline_narrates_the_cnot_as_entangling():
    steps = build_timeline(_ir(BELL_OPS))["steps"]
    assert "entanglement" in steps[2]["narration"].lower()


def test_timeline_refuses_oversized_registers():
    result = build_timeline(_ir([], n_qubits=12, n_clbits=12))
    assert result["supported"] is False
    assert "limited to" in result["reason"]


def test_counts_are_padded_to_the_register_width():
    """Aer returns "0"/"1" for a partially measured circuit.

    Unpadded keys read as a single-qubit result in the UI and are parsed as
    numbers by the plotting layer, which is what made the histogram show bare
    0 and 1 instead of real basis states.
    """
    ops = BELL_OPS + [
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2}
    ]
    result = aer.run(_ir(ops), shots=200, seed=1)
    assert result["counts"]
    for key in result["counts"]:
        assert len(key) == 2, f"count key {key!r} is not padded to 2 bits"


def test_noisy_run_reports_ideal_counts_and_metrics():
    ops = BELL_OPS + [
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
    ]
    noise = NoiseParams(
        enabled=True,
        t1_us=8.0,
        t2_us=6.0,
        readout_error=0.05,
        gate_time_1q_us=0.6,
        gate_time_2q_us=2.0,
    )
    result = aer.run(_ir(ops), shots=2000, seed=5, noise=noise)
    metadata = result["metadata"]

    ideal = metadata["ideal_counts"]
    assert ideal, "a noisy run must also report the ideal distribution"
    assert set(ideal) <= {"00", "11"}, "ideal Bell has no 01/10"

    metrics = metadata["metrics"]
    assert 0.0 <= metrics["fidelity"] < 1.0
    assert 0.0 <= metrics["purity"] < 1.0
    assert metrics["total_variation"] > 0.0
    assert abs(metrics["entanglement_entropy"] - 1.0) < 1e-9


def test_ideal_run_reports_perfect_metrics():
    ops = BELL_OPS + [
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
    ]
    metrics = aer.run(_ir(ops), shots=500, seed=1)["metadata"]["metrics"]
    assert metrics["fidelity"] == 1.0
    assert metrics["purity"] == 1.0
    assert metrics["total_variation"] == 0.0
