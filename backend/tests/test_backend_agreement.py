"""Every gate must behave the same on every engine.

The static pipeline normalises IR -> Qiskit -> transpile -> Cirq/PennyLane. A
conversion bug there shows up as one engine disagreeing with the others, which
no single-backend test can catch.

Each gate is sandwiched between Hadamards so a phase-only gate still changes
the measured distribution -- testing Z on |0> alone would pass even if Z were
implemented as the identity.
"""

from __future__ import annotations

import pytest

from app.quantum.backends import cirq_sim, cudaq_sim, pennylane_sim, qiskit_aer
from app.quantum.ir import GATE_PARAMS, GATE_SET, CircuitIR

SHOTS = 8000
#: Sampling noise at 8000 shots is well under this.
TOLERANCE = 0.05


def _engines():
    """CPU engines always; CUDA-Q joins automatically when a GPU is present.

    The GPU path translates the same normalized circuit, so on hardware this
    battery is the check that the endianness and gate-replay assumptions in
    cudaq_sim are actually true. On CI (no GPU) it changes nothing.
    """
    engines = [qiskit_aer, cirq_sim, pennylane_sim]
    if cudaq_sim.is_available()[0]:
        engines.append(cudaq_sim)
    return engines


@pytest.fixture(autouse=True)
def _no_gpu_cooldown(monkeypatch):
    """Serial submissions would otherwise trip the back-to-back cooldown.

    The thermal guard protects learners hammering Run; tests run one at a
    time, so the gap is pure friction on GPU machines. No-op without a GPU.
    """
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "gpu_cooldown_seconds", 0.0)


def _distribution(module, ir: CircuitIR) -> dict[str, float]:
    result = module.run(ir, shots=SHOTS, seed=11)
    return {k: v / SHOTS for k, v in result["counts"].items()}


def _tvd(a: dict[str, float], b: dict[str, float]) -> float:
    return 0.5 * sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in set(a) | set(b))


def _sandwiched(gate: str) -> CircuitIR:
    n_qubits = 2 if gate == "swap" else 1
    op: dict = {"kind": "gate", "gate": gate,
                "qubits": [0, 1] if gate == "swap" else [0], "layer": 1}
    if GATE_PARAMS.get(gate):
        op["params"] = ["pi/3"] * GATE_PARAMS[gate]
    ops = [{"kind": "gate", "gate": "h", "qubits": [0], "layer": 0}, op,
           {"kind": "gate", "gate": "h", "qubits": [0], "layer": 2}]
    ops += [{"kind": "measure", "qubits": [q], "clbits": [q], "layer": 3}
            for q in range(n_qubits)]
    return CircuitIR.from_dict(
        {"n_qubits": n_qubits, "n_clbits": n_qubits, "ops": ops}
    )


@pytest.mark.parametrize("gate", sorted(GATE_SET))
def test_all_engines_agree_on_every_gate(gate):
    ir = _sandwiched(gate)
    dists = {mod.NAME: _distribution(mod, ir) for mod in _engines()}
    aer = dists["qiskit_aer"]
    worst = max(
        (_tvd(aer, other) for name, other in dists.items() if name != "qiskit_aer"),
        default=0.0,
    )
    assert worst < TOLERANCE, (
        f"{gate}: engines disagree by {worst:.4f}\\n"
        + "\n".join(f"  {name}={dist}" for name, dist in dists.items())
    )


@pytest.mark.parametrize("gate", sorted(GATE_SET))
def test_qasm3_round_trip_preserves_every_gate(gate):
    """Export to QASM3 and back must not change what the circuit does."""
    from app.quantum.qasm3_codec import from_qasm3, to_qasm3

    ir = _sandwiched(gate)
    reimported = from_qasm3(to_qasm3(ir), name="round-trip")
    before = _distribution(qiskit_aer, ir)
    after = _distribution(qiskit_aer, reimported)
    assert _tvd(before, after) < TOLERANCE, f"{gate} changed across the round trip"


def test_engines_agree_on_an_entangled_circuit():
    """Bit ordering is the usual culprit; a Bell pair exposes it."""
    ir = CircuitIR.from_dict({"n_qubits": 2, "n_clbits": 2, "ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2}]})
    for module in _engines():
        probs = _distribution(module, ir)
        outcomes = {k for k, v in probs.items() if v > 0.02}
        assert outcomes == {"00", "11"}, f"{module.NAME} gave {outcomes}"


def test_engines_agree_on_an_asymmetric_circuit():
    """A circuit whose outcome differs under a bit-order flip."""
    ir = CircuitIR.from_dict({"n_qubits": 2, "n_clbits": 2, "ops": [
        {"kind": "gate", "gate": "x", "qubits": [0], "layer": 0},
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 1}]})
    for module in _engines():
        probs = _distribution(module, ir)
        top = max(probs, key=probs.get)
        assert top == "01", f"{module.NAME} put qubit 0 in the wrong position: {top}"
