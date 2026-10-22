"""The variational quantum classifier.

Predictions are derived from a real measurement: the QNode returns
``<Z>`` on wire 0, which lies in ``[-1, 1]``, and the class probability is
``(1 + <Z> + bias) / 2`` clipped to ``[0, 1]``. Nothing here fabricates a
score from the parameters directly — the measurement is the prediction.

Both supported differentiation methods are exact on a state-vector simulator:
``backprop`` differentiates through the simulation, ``parameter-shift``
evaluates the circuit at shifted parameters. They must agree, and
``tests/test_qml_gradients.py`` holds them to 1e-9 permanently.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pennylane as qml
from pennylane import numpy as pnp

from app.quantum.qml_lab import circuit as circuit_mod
from app.quantum.qml_lab import limits
from app.quantum.qml_lab.encoder import apply_angle_encoding, validate_feature_fit
from app.quantum.qml_lab.models import CircuitConfig


@dataclass
class Parameters:
    """Trainable state: circuit rotation angles plus one classical bias.

    Stored as a single flat vector because that is what the optimiser and the
    ``.npz`` artifact both want; ``circuit_weights`` reshapes a view for the
    QNode. The bias is the final element — it is classical, so it costs no
    circuit executions under parameter-shift, while letting the decision
    threshold move off ``<Z> = 0``.
    """

    theta: np.ndarray
    n_qubits: int
    n_layers: int

    @property
    def n_circuit_parameters(self) -> int:
        return limits.n_parameters(self.n_qubits, self.n_layers)

    @property
    def circuit_weights(self) -> np.ndarray:
        return self.theta[:-1].reshape(self.n_layers, self.n_qubits, 2)

    @property
    def bias(self) -> float:
        return float(self.theta[-1])

    def copy(self) -> "Parameters":
        return Parameters(theta=np.array(self.theta, dtype=float), n_qubits=self.n_qubits, n_layers=self.n_layers)


class VQC:
    """A variational quantum classifier over ``default.qubit``."""

    def __init__(self, config: CircuitConfig, n_features: int, diff_method: str = "backprop") -> None:
        validate_feature_fit(n_features, config.n_qubits)
        self.config = config
        self.n_features = int(n_features)
        self.diff_method = diff_method
        self.device = qml.device("default.qubit", wires=config.n_qubits)
        self._qnode = self._build_qnode()

    # -- construction -----------------------------------------------------

    def _build_qnode(self):
        @qml.qnode(self.device, interface="autograd", diff_method=self.diff_method)
        def node(features, weights):
            apply_angle_encoding(features, self.config.n_qubits, self.config.rotation)
            circuit_mod.apply_ansatz(weights, self.config.n_qubits, self.config.entanglement)
            return qml.expval(qml.PauliZ(0))

        return node

    def initialise(self, rng: np.random.Generator) -> Parameters:
        """Draw starting angles from the one seeded generator.

        Small normal draws rather than uniform over ``[0, 2π]``: starting near
        the identity keeps the first gradients informative instead of landing
        on a plateau.
        """
        n = limits.n_parameters(self.config.n_qubits, self.config.n_layers)
        theta = np.concatenate([rng.normal(loc=0.0, scale=0.1, size=n), np.zeros(1)])
        return Parameters(theta=theta, n_qubits=self.config.n_qubits, n_layers=self.config.n_layers)

    # -- forward ----------------------------------------------------------

    def expectation(self, features, theta):
        """``<Z_0>`` for one sample. Accepts plain or autograd arrays."""
        weights = theta[:-1].reshape(self.config.n_layers, self.config.n_qubits, 2)
        return self._qnode(features, weights)

    def decision_values(self, x, theta):
        """``<Z_0> + bias`` for every row; the sign is the predicted class."""
        values = [self.expectation(row, theta) + theta[-1] for row in x]
        return pnp.stack(values) if _is_autograd(theta) else np.asarray(values, dtype=float)

    def predict_proba(self, x: np.ndarray, params: Parameters) -> np.ndarray:
        """Probability of class 1, mapped from the measured expectation value."""
        values = np.asarray(self.decision_values(x, params.theta), dtype=float)
        return np.clip((1.0 + values) / 2.0, 0.0, 1.0)

    def predict(self, x: np.ndarray, params: Parameters) -> np.ndarray:
        """Hard class labels in ``{0, 1}``."""
        return (np.asarray(self.decision_values(x, params.theta), dtype=float) > 0.0).astype(int)

    # -- introspection ----------------------------------------------------

    def describe(self) -> dict[str, object]:
        info = circuit_mod.describe(self.config.n_qubits, self.config.n_layers, self.config.entanglement)
        info.update(
            {
                "encoding": f"angle-{self.config.rotation}",
                "n_features": self.n_features,
                "ancilla_wires": self.config.n_qubits - self.n_features,
                "diff_method": self.diff_method,
                "measurement": "expval(PauliZ(0))",
                "device": "default.qubit",
            }
        )
        return info

    def draw(self, features: np.ndarray, params: Parameters) -> str:
        """Text rendering of the concrete circuit, for reports and the UI."""
        weights = params.circuit_weights
        return qml.draw(self._qnode, max_length=200)(features, weights)


def _is_autograd(value) -> bool:
    return hasattr(value, "_value") or isinstance(value, pnp.tensor)
