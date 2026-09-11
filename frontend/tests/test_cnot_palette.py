"""The palette must make CNOT control/target unambiguous.

Reported bug: building "H then CNOT" produced |00> + |01> instead of a Bell
pair. The engine was correct -- |00> + |01> is exactly what you get when the
CNOT's control and target are swapped. The cause was the palette: there was no
CNOT entry at all, so the only route was "pick X, set Target, add a Control",
and "Target" naturally reads as "the qubit I am placing the CNOT on".
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "frontend"))

from app.quantum.backends import qiskit_aer as aer  # noqa: E402
from app.quantum.ir import CircuitIR, Op  # noqa: E402
from lib.composer import PALETTE  # noqa: E402


def test_palette_offers_cnot_and_toffoli_by_name():
    gates = {g for g, _label, _desc in PALETTE}
    assert "cx" in gates, "learners must be able to pick CNOT directly"
    assert "ccx" in gates


def test_cnot_palette_labels_say_which_qubit_is_flipped():
    desc = {g: d for g, _l, d in PALETTE}
    assert "control" in desc["cx"].lower()
    assert "target" in desc["cx"].lower()


def test_control_q0_target_q1_after_h_is_a_bell_pair():
    """The op the fixed palette emits must entangle, not just flip q0."""
    ir = CircuitIR.model_validate({"n_qubits": 2, "n_clbits": 2, "ops": []})
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="x", qubits=[1], controls=[0]), 1)

    counts = aer.run(ir, shots=2000, seed=1)["counts"]
    assert set(counts) == {"00", "11"}, f"expected a Bell pair, got {counts}"


def test_swapped_control_and_target_is_not_a_bell_pair():
    """Pin the symptom, so the two cases can never be confused again."""
    ir = CircuitIR.model_validate({"n_qubits": 2, "n_clbits": 2, "ops": []})
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="x", qubits=[0], controls=[1]), 1)

    counts = aer.run(ir, shots=2000, seed=1)["counts"]
    assert set(counts) == {"00", "01"}, (
        "swapping control/target should give |00>+|01>; this is the exact "
        f"symptom that was reported. Got {counts}"
    )
