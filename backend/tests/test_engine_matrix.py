"""Every advertised engine must really work, in the role it is advertised for.

Three distinct capabilities get conflated when people ask "do you support
framework X?", so they are tested separately here:

* EXECUTION  - the platform can run a circuit on that engine.
* EXPORT     - the platform emits a standalone program for that engine, and
               that program is valid code (not just a string).
* AUTHORING  - a user can write code in that framework in the Code Lab and
               have it compiled into the platform's IR.
"""

from __future__ import annotations

import ast

import pytest

from app.quantum import (
    codegen_cirq,
    codegen_pennylane,
    codegen_qbraid,
    codegen_qiskit,
)
from app.quantum.backends import (
    cirq_sim,
    cudaq_sim,
    pennylane_sim,
    qbraid_sim,
    qiskit_aer,
)
from app.quantum.ir import CircuitIR
from app.quantum.qasm3_codec import from_qasm3, to_qasm3
from app.services.codelab import FRAMEWORKS, STARTERS, build_circuit

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

DYNAMIC = {
    "n_qubits": 2,
    "n_clbits": 2,
    "ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
        {
            "kind": "if",
            "condition": {"type": "bit_eq", "bit": 0, "value": 1},
            "body": [{"kind": "gate", "gate": "x", "qubits": [1], "layer": 0}],
            "layer": 2,
        },
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 3},
    ],
}


def _bell() -> CircuitIR:
    return CircuitIR.from_dict(BELL)


# ---------------------------------------------------------------- execution
_EXEC_ENGINES = [qiskit_aer, cirq_sim, pennylane_sim]
_EXEC_IDS = ["qiskit_aer", "cirq", "pennylane"]
if cudaq_sim.is_available()[0]:  # only on a machine with a real CUDA GPU
    _EXEC_ENGINES.append(cudaq_sim)
    _EXEC_IDS.append("cudaq")


@pytest.mark.parametrize("backend", _EXEC_ENGINES, ids=_EXEC_IDS)
def test_engine_executes_bell_state(backend, monkeypatch):
    # Tests submit back-to-back; the thermal guard's cooldown is for learners
    # hammering Run, and must not fail an otherwise-fine GPU run here.
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "gpu_cooldown_seconds", 0.0)
    probs = backend.run(_bell(), shots=2000, seed=11)["probabilities"]
    outcomes = {k for k, v in probs.items() if v > 0.02}
    assert outcomes == {"00", "11"}, probs


def test_qbraid_is_wired_and_gated_on_credentials():
    """qBraid is a real backend; without a key it must refuse, not crash."""
    available, message = qbraid_sim.is_available()
    if not available:
        assert "qBraid" in message
    else:  # pragma: no cover - only when a key is configured
        assert message == ""


# ------------------------------------------------------------------- export
@pytest.mark.parametrize(
    "gen",
    [codegen_qiskit, codegen_cirq, codegen_pennylane, codegen_qbraid],
    ids=["qiskit", "cirq", "pennylane", "qbraid"],
)
def test_export_emits_syntactically_valid_python(gen):
    ast.parse(gen.generate(_bell(), 256))


def test_export_emits_qasm3():
    qasm = to_qasm3(_bell())
    assert "OPENQASM 3" in qasm
    assert "qubit[2]" in qasm


def test_qasm3_round_trip_preserves_semantics():
    reimported = from_qasm3(to_qasm3(_bell()), name="rt")
    before = qiskit_aer.run(_bell(), shots=2000, seed=9)["probabilities"]
    after = qiskit_aer.run(reimported, shots=2000, seed=9)["probabilities"]
    assert {k for k, v in before.items() if v > 0.02} == {
        k for k, v in after.items() if v > 0.02
    }


# ---------------------------------------------------------------- authoring
def test_codelab_advertises_its_frameworks():
    """qBraid joined as an authoring target via its local transpiler; CUDA-Q
    joined as the GPU-native language (listed only where the wheel exists,
    but FRAMEWORKS itself is the full universe)."""
    assert set(FRAMEWORKS) == {
        "qiskit", "cirq", "pennylane", "qasm3", "qbraid", "cudaq",
    }


@pytest.mark.parametrize(
    "framework", ["qiskit", "cirq", "pennylane", "qasm3", "qbraid"]
)
def test_codelab_starter_compiles_and_runs(framework):
    """The starter shown in the UI must not be broken."""
    result = build_circuit(STARTERS[framework], framework)
    ir = result["ir"]
    assert ir.n_qubits >= 1
    qiskit_aer.run(ir, shots=64, seed=2)


def test_codelab_cudaq_starter_compiles_when_the_wheel_is_present():
    import importlib.util

    if importlib.util.find_spec("cudaq") is None:
        pytest.skip("CUDA-Q ships only with the GPU image")
    result = build_circuit(STARTERS["cudaq"], "cudaq")
    ir = result["ir"]
    assert ir.n_qubits == 2
    qiskit_aer.run(ir, shots=64, seed=2)


# --------------------------------------------------- dynamic circuit policy
@pytest.mark.parametrize(
    "gen,supports",
    [(codegen_qiskit, True), (codegen_cirq, True),
     (codegen_pennylane, False), (codegen_qbraid, False)],
    ids=["qiskit", "cirq", "pennylane", "qbraid"],
)
def test_dynamic_export_is_honest(gen, supports):
    """Engines that cannot do control flow must say so, not emit wrong code."""
    ir = CircuitIR.from_dict(DYNAMIC)
    code = gen.generate(ir, 100)
    ast.parse(code)
    if supports:
        assert "import" in code
    else:
        # An explanatory stub: a docstring and no executable import statement.
        assert "dynamic" in code.lower() or "control flow" in code.lower()
        assert not any(
            line.startswith("import ") or line.startswith("from ")
            for line in code.splitlines()
        )
