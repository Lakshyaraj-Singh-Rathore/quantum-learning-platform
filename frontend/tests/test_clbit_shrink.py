"""Classical-bit width must follow the qubit count down, not just up.

Reported symptom: raise the composer to 4 qubits, drop back to 2, and the
histogram still showed four-character bitstrings ("0000", "0011") for a
two-qubit circuit.

Cause: both the Python composer and the React component computed the new width
as max(<needed>, <current n_clbits>). Folding in the *current* width makes it a
ratchet -- it can only ever grow. 2 -> 4 -> 2 therefore left n_clbits at 4, and
Qiskit faithfully reported four classical bits.

The fix keeps a floor at n_qubits (so "Measure All" always has somewhere to
write) and at the highest clbit any surviving operation actually uses,
including measurements nested inside if/for/while bodies.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.quantum.ir import CircuitIR  # noqa: E402


def _resize(ir: CircuitIR, n_qubits: int) -> CircuitIR:
    """Mirror of lib.composer._resize's width logic, without Streamlit."""
    ir.ops = [op for op in ir.ops if all(q < n_qubits for q in op.involved_qubits())]
    ir.n_qubits = n_qubits
    used: set[int] = set()
    for op in ir.ops:
        used |= op.involved_clbits()
    ir.n_clbits = max(n_qubits, (max(used) + 1) if used else 0)
    return CircuitIR.from_dict(ir.to_dict())


BELL_OPS = [
    {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
    {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
    {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
    {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
]


def test_growing_then_shrinking_restores_the_width():
    ir = CircuitIR.from_dict({"n_qubits": 2, "n_clbits": 2, "ops": BELL_OPS})
    ir = _resize(ir, 4)
    assert ir.n_clbits == 4
    ir = _resize(ir, 2)
    assert ir.n_qubits == 2
    assert ir.n_clbits == 2, "clbits must shrink back, or bitstrings stay too wide"


def test_histogram_bitstrings_are_the_right_length():
    from app.quantum.backends import qiskit_aer

    ir = CircuitIR.from_dict({"n_qubits": 2, "n_clbits": 2, "ops": BELL_OPS})
    ir = _resize(_resize(ir, 4), 2)
    counts = qiskit_aer.run(ir, shots=500, seed=3)["counts"]
    assert all(len(k) == 2 for k in counts), counts
    assert set(counts) == {"00", "11"}


def test_width_is_held_up_by_a_surviving_measurement():
    """Never shrink below a clbit a remaining measurement still writes to."""
    ir = CircuitIR.from_dict({
        "n_qubits": 4, "n_clbits": 4,
        "ops": [{"kind": "measure", "qubits": [0], "clbits": [3], "layer": 0}],
    })
    ir = _resize(ir, 2)
    assert ir.n_qubits == 2
    assert ir.n_clbits == 4


def test_nested_measurement_pins_the_width():
    """A measurement inside an if-block still counts."""
    ir = CircuitIR.from_dict({
        "n_qubits": 4, "n_clbits": 4,
        "ops": [
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 0},
            {"kind": "if",
             "condition": {"type": "bit_eq", "bit": 0, "value": 1},
             "body": [{"kind": "measure", "qubits": [1], "clbits": [2], "layer": 0}],
             "layer": 1},
        ],
    })
    ir = _resize(ir, 2)
    assert ir.n_clbits == 3


def test_empty_circuit_shrinks_cleanly():
    ir = CircuitIR.from_dict({"n_qubits": 4, "n_clbits": 4, "ops": []})
    ir = _resize(ir, 2)
    assert (ir.n_qubits, ir.n_clbits) == (2, 2)


def test_python_composer_does_not_ratchet():
    src = (ROOT / "lib" / "composer.py").read_text()
    assert "ir.n_clbits = max(n_qubits, ir.n_clbits)" not in src, (
        "folding the current width back in makes clbits a one-way ratchet"
    )


def test_react_required_clbits_does_not_fold_in_current_width():
    src = (ROOT / "circuit_composer" / "frontend" / "src" / "ir.ts").read_text()
    assert "Math.max(n, ir.n_clbits ?? 0)" not in src


# --- An already-too-wide circuit must heal itself -------------------------
#
# Narrowing on resize is not enough: a circuit that was saved to session_state
# before that fix existed (or loaded from a saved circuit, or imported from
# QASM) stays wide forever and keeps printing "00000000001" for two qubits.
# get_circuit() runs on every render, so it corrects those too.

def test_required_clbits_narrows_an_overwide_register():
    from lib.composer import required_clbits

    stuck = CircuitIR.from_dict({
        "n_qubits": 2, "n_clbits": 11,
        "ops": [
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 0},
            {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 0},
        ],
    })
    assert required_clbits(stuck) == 2


def test_required_clbits_respects_a_high_bit_in_use():
    from lib.composer import required_clbits

    wide = CircuitIR.from_dict({
        "n_qubits": 2, "n_clbits": 11,
        "ops": [{"kind": "measure", "qubits": [0], "clbits": [9], "layer": 0}],
    })
    assert required_clbits(wide) == 10


def test_required_clbits_floors_at_qubit_count():
    from lib.composer import required_clbits

    empty = CircuitIR.from_dict({"n_qubits": 5, "n_clbits": 1, "ops": []})
    assert required_clbits(empty) == 5


def test_get_circuit_heals_session_state():
    """The user's exact stuck circuit, corrected on the next render."""
    from lib import composer

    class FakeState(dict):
        def __getattr__(self, k):
            return self[k]

        def __setattr__(self, k, v):
            self[k] = v

    state = FakeState()
    state["circuit"] = {
        "name": "stuck", "n_qubits": 2, "n_clbits": 11,
        "ops": [{"kind": "measure", "qubits": [0], "clbits": [0], "layer": 0}],
    }
    original = composer.st.session_state
    composer.st.session_state = state
    try:
        healed = composer.get_circuit()
    finally:
        composer.st.session_state = original
    assert healed.n_clbits == 2


def test_measure_all_sizes_from_the_new_measurements():
    """React measureAllAppend used to size from the circuit before appending."""
    src = (
        ROOT / "circuit_composer" / "frontend" / "src" / "ir.ts"
    ).read_text()
    assert "requiredClbits({ ...ir, ops })" in src
