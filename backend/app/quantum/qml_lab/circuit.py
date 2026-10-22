"""The variational ansatz.

One layer is: ``RY(θ)`` and ``RZ(φ)`` on every wire, then a CNOT pattern. Two
rotations per wire per layer give the block enough freedom to move a point
anywhere on the Bloch sphere; a single rotation axis cannot, and an ansatz
built from one axis plus CNOTs is a common reason a QNN plateaus at chance.

Parameter count is therefore ``n_layers * n_qubits * 2`` — see
:func:`app.quantum.qml_lab.limits.n_parameters`, which is the single source of
truth so the cost estimate and the weight initialiser cannot disagree.
"""

from __future__ import annotations

from typing import Sequence

import pennylane as qml

from app.quantum.qml_lab.errors import QmlConfigError


def apply_entanglement(n_qubits: int, topology: str) -> None:
    """Apply one layer's entangling gates.

    ``ring`` closes the chain back to wire 0, except at two qubits where the
    wrap-around CNOT(1,0) would duplicate the chain's only link and buy
    nothing. One qubit cannot be entangled at all; both cases are handled
    quietly here rather than by rejecting the configuration, because a
    1-qubit circuit is a legitimate thing to want to inspect.
    """
    if n_qubits < 2 or topology == "none":
        return

    if topology == "linear":
        for wire in range(n_qubits - 1):
            qml.CNOT(wires=[wire, wire + 1])
    elif topology == "ring":
        for wire in range(n_qubits - 1):
            qml.CNOT(wires=[wire, wire + 1])
        if n_qubits > 2:
            qml.CNOT(wires=[n_qubits - 1, 0])
    else:  # pragma: no cover - Literal in the schema makes this unreachable
        raise QmlConfigError(f"unsupported entanglement topology {topology!r}")


def apply_ansatz(weights: Sequence[Sequence[Sequence[float]]], n_qubits: int, topology: str = "ring") -> None:
    """Apply the full variational block inside a QNode.

    ``weights`` is indexed ``[layer][wire][0 for RY, 1 for RZ]``.
    """
    for layer in weights:
        for wire in range(n_qubits):
            qml.RY(layer[wire][0], wires=wire)
            qml.RZ(layer[wire][1], wires=wire)
        apply_entanglement(n_qubits, topology)


def describe(n_qubits: int, n_layers: int, topology: str) -> dict[str, object]:
    """Structural summary for the UI's circuit view and for the phase reports."""
    per_layer_entanglers = 0
    if n_qubits >= 2 and topology != "none":
        per_layer_entanglers = n_qubits - 1 + (1 if topology == "ring" and n_qubits > 2 else 0)

    return {
        "n_qubits": n_qubits,
        "n_layers": n_layers,
        "entanglement": topology,
        "rotations_per_layer": n_qubits * 2,
        "entanglers_per_layer": per_layer_entanglers,
        "n_parameters": n_layers * n_qubits * 2,
        "depth_estimate": n_layers * (2 + (1 if per_layer_entanglers else 0)),
    }
