"""Regressions from a from-scratch audit of the running system.

Each test here corresponds to a bug found by probing the live stack rather than
by reading code. They are grouped by the failure they prevent.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.quantum.backends import cirq_sim, pennylane_sim, qiskit_aer
from app.quantum.backends.base import BackendError
from app.quantum.inspect import inspect_circuit
from app.quantum.ir import FOR_LOOP_CAP, CircuitIR


def _c(n, ops, nc=None):
    return {"n_qubits": n, "n_clbits": nc if nc is not None else n, "ops": ops}


def _g(gate, qubits, layer, **kw):
    return {"kind": "gate", "gate": gate, "qubits": qubits, "layer": layer, **kw}


# --- BUG: negative layers corrupted depth() -------------------------------
def test_negative_layer_is_rejected():
    with pytest.raises(ValidationError):
        CircuitIR.from_dict(_c(2, [_g("h", [0], -5)]))


def test_depth_is_correct_without_negative_layers():
    ir = CircuitIR.from_dict(_c(2, [_g("h", [0], 0), _g("x", [1], 1)]))
    assert ir.depth() == 2


# --- BUG: swap q[0], q[0] reached Qiskit and died there -------------------
def test_swap_onto_itself_is_rejected_early():
    with pytest.raises(ValidationError) as exc:
        CircuitIR.from_dict(_c(2, [_g("swap", [0, 0], 0)]))
    assert "different" in str(exc.value)


def test_normal_swap_still_allowed():
    ir = CircuitIR.from_dict(_c(2, [_g("swap", [0, 1], 0)]))
    assert len(ir.ops) == 1


# --- BUG: static circuits had no qubit ceiling; 24q OOM-killed the worker --
@pytest.mark.parametrize("backend", [qiskit_aer, cirq_sim, pennylane_sim])
def test_oversized_static_circuit_is_refused_by_every_backend(backend):
    ir = CircuitIR.from_dict(_c(24, [_g("h", [0], 0)]))
    with pytest.raises(BackendError) as exc:
        backend.run(ir, shots=4)
    assert "limited to" in str(exc.value)


def test_inspect_reports_oversized_static_circuit():
    ir = CircuitIR.from_dict(_c(30, [_g("h", [0], 0)]))
    report = inspect_circuit(ir, "qiskit_aer", 10)
    assert report["ok"] is False
    assert any("limited to" in e for e in report["errors"])


def test_normal_sized_circuit_still_runs():
    ir = CircuitIR.from_dict(
        _c(2, [_g("h", [0], 0), {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1}])
    )
    assert qiskit_aer.run(ir, shots=32)["counts"]


# --- BUG: for-loop N was unbounded and unrolls into real gates ------------
def test_for_loop_n_is_capped():
    with pytest.raises(ValidationError) as exc:
        CircuitIR.from_dict(
            _c(1, [{"kind": "for", "loop_n": 10_000_000,
                    "body": [_g("x", [0], 0)], "layer": 0}])
        )
    assert "capped" in str(exc.value)


def test_for_loop_at_the_cap_is_allowed():
    ir = CircuitIR.from_dict(
        _c(1, [{"kind": "for", "loop_n": FOR_LOOP_CAP,
                "body": [_g("x", [0], 0)], "layer": 0}])
    )
    assert ir.ops[0].loop_n == FOR_LOOP_CAP


# --- Physics must stay correct -------------------------------------------
def test_bell_state_probabilities():
    ir = CircuitIR.from_dict(_c(2, [
        _g("h", [0], 0),
        _g("x", [1], 1, controls=[0]),
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
    ]))
    probs = qiskit_aer.run(ir, shots=4000, seed=7)["probabilities"]
    assert set(k for k, v in probs.items() if v > 0.02) == {"00", "11"}
    assert abs(probs["00"] - 0.5) < 0.06


def test_backends_agree_on_ghz():
    ir = CircuitIR.from_dict(_c(3, [
        _g("h", [0], 0),
        _g("x", [1], 1, controls=[0]),
        _g("x", [2], 2, controls=[0]),
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 3},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 3},
        {"kind": "measure", "qubits": [2], "clbits": [2], "layer": 3},
    ]))
    seen = []
    for backend in (qiskit_aer, cirq_sim, pennylane_sim):
        probs = backend.run(ir, shots=2000, seed=5)["probabilities"]
        seen.append({k for k, v in probs.items() if v > 0.02})
    assert seen[0] == seen[1] == seen[2] == {"000", "111"}


# --- BUG: an unknown backend name escaped as an unhandled HTTP 500 --------
def test_unknown_backend_is_422_not_500(client, student_headers):
    bell = _c(2, [
        _g("h", [0], 0),
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
    ])
    r = client.post(
        "/jobs",
        json={"circuit_ir": bell, "backend": "nonexistent", "shots": 10},
        headers=student_headers,
    )
    assert r.status_code == 422, r.text
    assert "unknown backend" in r.text


def test_oversized_job_is_422_not_accepted(client, student_headers):
    r = client.post(
        "/jobs",
        json={
            "circuit_ir": _c(30, [_g("h", [0], 0)]),
            "backend": "qiskit_aer",
            "shots": 10,
        },
        headers=student_headers,
    )
    assert r.status_code == 422, r.text
    assert "limited to" in r.text


def test_valid_job_is_still_accepted(client, student_headers):
    bell = _c(2, [
        _g("h", [0], 0),
        _g("x", [1], 1, controls=[0]),
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
    ])
    r = client.post(
        "/jobs",
        json={"circuit_ir": bell, "backend": "qiskit_aer", "shots": 64},
        headers=student_headers,
    )
    assert r.status_code == 201, r.text
