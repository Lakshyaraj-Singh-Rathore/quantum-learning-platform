"""Angle encoding: classical features onto rotation angles.

The scaler in :mod:`.datasets` already maps every feature into ``[0, π]``, so
each feature becomes one rotation on one wire. When the circuit has more wires
than the dataset has features, the surplus wires are left in ``|0>`` and act
as ancillas that the ansatz entangles — they add expressivity rather than
being wasted, which is why a 2-feature dataset on the default 4 qubits is a
sensible configuration rather than a misconfiguration.
"""

from __future__ import annotations

from typing import Sequence

import pennylane as qml

from app.quantum.qml_lab.errors import QmlConfigError


def validate_feature_fit(n_features: int, n_qubits: int) -> None:
    """Angle encoding needs one wire per feature."""
    if n_features > n_qubits:
        raise QmlConfigError(
            f"angle encoding needs one wire per feature: the dataset has {n_features} "
            f"features but the circuit has {n_qubits} qubits; raise circuit.n_qubits to "
            f"at least {n_features}"
        )


def apply_angle_encoding(features: Sequence[float], n_qubits: int, rotation: str = "Y") -> None:
    """Apply one rotation per feature inside a QNode.

    ``rotation="Z"`` is preceded by a Hadamard on each encoded wire. An ``RZ``
    applied to ``|0>`` only contributes a global phase, so without the
    Hadamard a Z-axis encoding would discard the data entirely and train on
    nothing — the kind of fault that produces a model that runs, returns
    measurements and learns nothing.
    """
    n_features = len(features)
    validate_feature_fit(n_features, n_qubits)

    for wire in range(n_features):
        angle = features[wire]
        if rotation == "X":
            qml.RX(angle, wires=wire)
        elif rotation == "Y":
            qml.RY(angle, wires=wire)
        elif rotation == "Z":
            qml.Hadamard(wires=wire)
            qml.RZ(angle, wires=wire)
        else:  # pragma: no cover - Literal in the schema makes this unreachable
            raise QmlConfigError(f"unsupported rotation axis {rotation!r}")
