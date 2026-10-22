"""Record the real QML ansatz, gate by gate, for the frontend to check against.

The circuit view draws a preview built in TypeScript
(`src/components/qml/circuitIr.ts`) while the circuit that actually trains is
built in Python (`app/quantum/qml_lab/{encoder,circuit}.py`). Two
implementations of one ansatz drift — the preview quietly starts showing a
circuit nobody ran.

So this does not hand-write an expectation. It builds the genuine circuit with
PennyLane, captures the operations off the tape, and writes them out. The
`.mts` harness then rebuilds the same configuration in TypeScript and compares
gate for gate, wire for wire.

Needs the backend virtualenv (PennyLane). The backend package is located
relative to this file, so the working directory does not matter:

    npm run fixtures:qml-circuit
"""

from __future__ import annotations

import json
import pathlib
import sys

# The backend is a sibling of frontend/; importing the real builders is the
# entire point, so put it on the path rather than re-deriving the ansatz.
_BACKEND = pathlib.Path(__file__).resolve().parents[3] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import numpy as np
import pennylane as qml

from app.quantum.qml_lab.circuit import apply_ansatz, describe
from app.quantum.qml_lab.encoder import apply_angle_encoding

OUT = pathlib.Path(__file__).resolve().parents[1] / "test-fixtures" / "qml-circuit-golden.json"

# A grid that exercises every branch the builders have: the ring special case
# at 2 qubits, Z-encoding's Hadamard, "none" entanglement, and the case where
# the circuit has more wires than the dataset has features.
GRID = [
    {"n_qubits": 2, "n_layers": 1, "rotation": "Y", "entanglement": "ring", "n_features": 2},
    {"n_qubits": 2, "n_layers": 2, "rotation": "Y", "entanglement": "linear", "n_features": 2},
    {"n_qubits": 3, "n_layers": 1, "rotation": "Z", "entanglement": "ring", "n_features": 2},
    {"n_qubits": 4, "n_layers": 2, "rotation": "X", "entanglement": "ring", "n_features": 2},
    {"n_qubits": 4, "n_layers": 1, "rotation": "Y", "entanglement": "none", "n_features": 4},
    {"n_qubits": 4, "n_layers": 4, "rotation": "Y", "entanglement": "linear", "n_features": 3},
    {"n_qubits": 8, "n_layers": 2, "rotation": "Y", "entanglement": "ring", "n_features": 2},
]


def record(case: dict) -> dict:
    n_qubits = case["n_qubits"]
    n_layers = case["n_layers"]
    n_features = case["n_features"]

    rng = np.random.default_rng(0)
    features = rng.uniform(0.0, np.pi, size=n_features)
    weights = rng.normal(size=(n_layers, n_qubits, 2))

    with qml.tape.QuantumTape() as tape:
        apply_angle_encoding(features, n_qubits, case["rotation"])
        apply_ansatz(weights, n_qubits, case["entanglement"])
        qml.expval(qml.PauliZ(0))

    ops = []
    for op in tape.operations:
        wires = list(op.wires)
        if op.name == "CNOT":
            # The IR models a controlled-X as an X with a control wire, which
            # is how CircuitDiagram's glyph expects it.
            ops.append({"gate": "x", "qubits": [wires[1]], "controls": [wires[0]]})
        else:
            ops.append({"gate": op.name.lower(), "qubits": wires, "controls": []})

    return {
        **case,
        "ops": ops,
        "describe": describe(n_qubits, n_layers, case["entanglement"]),
    }


def main() -> int:
    cases = [record(c) for c in GRID]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"cases": cases}, indent=2) + "\n", encoding="utf-8")
    total = sum(len(c["ops"]) for c in cases)
    print(f"wrote {OUT} - {len(cases)} cases, {total} operations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
