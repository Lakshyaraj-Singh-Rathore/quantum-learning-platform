"""Results must not keep describing a circuit the user has since changed.

Reported symptom: raise the composer to 15 qubits, run, then drop back to 2 --
the histogram still rendered the old 15-qubit result as if it were current,
because results are keyed only by last_job_id and survive edits to the grid.
"""

from __future__ import annotations

import json
from pathlib import Path

PAGE = Path(__file__).resolve().parents[1] / "pages" / "2_Composer.py"


def _stale(ran_on: dict, now: dict) -> bool:
    """The comparison the page performs."""
    return json.dumps(ran_on, sort_keys=True) != json.dumps(now, sort_keys=True)


def _circuit(n: int) -> dict:
    return {"name": "c", "n_qubits": n, "n_clbits": n, "ops": []}


def test_shrinking_qubits_marks_the_result_stale():
    assert _stale(_circuit(15), _circuit(2)) is True


def test_growing_qubits_marks_the_result_stale():
    assert _stale(_circuit(2), _circuit(15)) is True


def test_unchanged_circuit_is_not_stale():
    assert _stale(_circuit(4), _circuit(4)) is False


def test_key_order_does_not_create_false_staleness():
    a = {"n_qubits": 2, "name": "c", "ops": [], "n_clbits": 2}
    b = {"name": "c", "n_qubits": 2, "n_clbits": 2, "ops": []}
    assert _stale(a, b) is False


def test_adding_a_gate_marks_the_result_stale():
    before = _circuit(2)
    after = _circuit(2)
    after["ops"] = [{"kind": "gate", "gate": "h", "qubits": [0], "layer": 0}]
    assert _stale(before, after) is True


def test_page_records_the_circuit_each_job_ran_on():
    src = PAGE.read_text()
    assert "last_job_circuit" in src
    assert "last_job_qubits" in src


def test_page_warns_instead_of_silently_showing_old_data():
    src = PAGE.read_text()
    assert "stale_result" in src
    assert "earlier version of the circuit" in src
