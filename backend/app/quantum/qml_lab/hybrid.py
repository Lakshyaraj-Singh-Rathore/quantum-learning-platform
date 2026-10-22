"""A hybrid classical-quantum classifier, differentiated end to end.

A classical layer learns *what to feed the circuit*. Raw features go through
one trainable affine map and a ``tanh``, the result is rescaled into the
encoder's ``[0, π]`` window, and only then is it angle-encoded and pushed
through the same variational ansatz the pure VQC uses. The classical weights
and the circuit weights live in **one flat parameter vector** and are updated
by the same optimiser step, so the classical layer is genuinely learning a
representation for the quantum model rather than being a fixed preprocessor.

**No PyTorch** (DECISIONS.md D-031, vision §2C.2). ``autograd`` is already a
PennyLane dependency, and ``interface="autograd"`` differentiates straight
through the QNode into the classical weights. ``qml.qnn.TorchLayer`` is the
only thing torch would add, and it is a wrapper around what is written here
directly. The proof that this works is not an assertion that it should:
:func:`tests.test_qml_hybrid.test_classical_gradient_matches_finite_differences`
compares the autograd gradient of the *classical* block against a central
finite difference taken through the real circuit.

Layout of the flat vector, in order::

    [ W1 : n_features * n_hidden ][ b1 : n_hidden ][ circuit : 2*n_qubits*n_layers ][ bias : 1 ]

The ordering matters because :mod:`.persistence` stores the vector verbatim
and :class:`HybridParameters` is the only thing that knows how to read it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pennylane as qml
from pennylane import numpy as pnp

from app.quantum.qml_lab import circuit as circuit_mod
from app.quantum.qml_lab import limits
from app.quantum.qml_lab.encoder import apply_angle_encoding, validate_feature_fit
from app.quantum.qml_lab.errors import QmlConfigError
from app.quantum.qml_lab.models import CircuitConfig

#: The encoder's angle window. ``tanh`` lands in [-1, 1]; this maps it onto
#: [0, π] so the classical block can never emit an angle the encoder would
#: silently wrap around.
ANGLE_MIN = 0.0
ANGLE_MAX = float(np.pi)


def n_classical_parameters(n_features: int, n_hidden: int) -> int:
    """Weights plus biases of the single classical layer."""
    return int(n_features) * int(n_hidden) + int(n_hidden)


def n_hybrid_parameters(n_features: int, n_hidden: int, n_qubits: int, n_layers: int) -> int:
    """Total trainable parameters, classical and quantum together.

    The trailing ``+ 1`` is the classical output bias, the same one the pure
    VQC carries: it shifts the decision threshold off ``<Z> = 0`` and costs no
    circuit executions under parameter-shift.
    """
    return (
        n_classical_parameters(n_features, n_hidden)
        + limits.n_parameters(n_qubits, n_layers)
        + 1
    )


@dataclass
class HybridParameters:
    """Trainable state for :class:`HybridQNN`.

    Deliberately **not** a subclass of :class:`~app.quantum.qml_lab.vqc.Parameters`.
    That class reads ``theta[:-1]`` as circuit weights, which for a hybrid
    vector is the classical block as well and would reshape into silent
    nonsense. A separate type makes the mistake impossible rather than
    merely documented.
    """

    theta: np.ndarray
    n_qubits: int
    n_layers: int
    n_features: int
    n_hidden: int

    @property
    def n_circuit_parameters(self) -> int:
        return limits.n_parameters(self.n_qubits, self.n_layers)

    @property
    def classical_weights(self) -> np.ndarray:
        """``W1``, shaped ``(n_features, n_hidden)``."""
        size = self.n_features * self.n_hidden
        return np.asarray(self.theta[:size], dtype=float).reshape(self.n_features, self.n_hidden)

    @property
    def classical_bias(self) -> np.ndarray:
        """``b1``, shaped ``(n_hidden,)``."""
        start = self.n_features * self.n_hidden
        return np.asarray(self.theta[start : start + self.n_hidden], dtype=float)

    @property
    def circuit_weights(self) -> np.ndarray:
        """Ansatz angles, shaped ``(n_layers, n_qubits, 2)``."""
        start = n_classical_parameters(self.n_features, self.n_hidden)
        block = self.theta[start : start + self.n_circuit_parameters]
        return np.asarray(block, dtype=float).reshape(self.n_layers, self.n_qubits, 2)

    @property
    def bias(self) -> float:
        return float(self.theta[-1])

    def copy(self) -> "HybridParameters":
        return HybridParameters(
            theta=np.array(self.theta, dtype=float),
            n_qubits=self.n_qubits,
            n_layers=self.n_layers,
            n_features=self.n_features,
            n_hidden=self.n_hidden,
        )


class HybridQNN:
    """Classical affine layer -> tanh -> angle encoding -> ansatz -> ``<Z_0>``.

    Exposes the same surface the trainer drives (``decision_values``,
    ``initialise``, ``predict``, ``predict_proba``, ``describe``), so it trains
    through :func:`app.quantum.qml_lab.trainer.train` with no change to the
    trainer at all.
    """

    def __init__(
        self,
        config: CircuitConfig,
        n_features: int,
        n_hidden: int | None = None,
        diff_method: str = "backprop",
    ) -> None:
        hidden = int(n_hidden) if n_hidden is not None else int(config.n_qubits)
        if hidden < 1:
            raise QmlConfigError(f"n_hidden must be at least 1, got {hidden}")
        # The classical layer's width *is* the number of encoded wires, so the
        # encoder's one-wire-per-feature rule applies to it, not to the raw
        # feature count. Checked here so the failure names n_hidden.
        if hidden > config.n_qubits:
            raise QmlConfigError(
                f"the classical layer emits {hidden} values but the circuit has "
                f"{config.n_qubits} qubits; angle encoding needs one wire per value, "
                f"so lower circuit.n_hidden to at most {config.n_qubits} or raise n_qubits"
            )
        validate_feature_fit(hidden, config.n_qubits)

        self.config = config
        self.n_features = int(n_features)
        self.n_hidden = hidden
        self.diff_method = diff_method
        self.device = qml.device("default.qubit", wires=config.n_qubits)
        self._qnode = self._build_qnode()

    # -- construction -----------------------------------------------------

    def _build_qnode(self):
        @qml.qnode(self.device, interface="autograd", diff_method=self.diff_method)
        def node(angles, weights):
            apply_angle_encoding(angles, self.config.n_qubits, self.config.rotation)
            circuit_mod.apply_ansatz(weights, self.config.n_qubits, self.config.entanglement)
            return qml.expval(qml.PauliZ(0))

        return node

    def initialise(self, rng: np.random.Generator) -> HybridParameters:
        """Draw a starting vector from the one seeded generator.

        The classical block uses Xavier-style scaling (``1/sqrt(fan_in)``)
        rather than the circuit block's flat 0.1: a classical layer initialised
        as small as the rotation angles would emit near-identical angles for
        every sample, and the first gradients would carry almost no signal
        about the data.
        """
        n_class = n_classical_parameters(self.n_features, self.n_hidden)
        n_circ = limits.n_parameters(self.config.n_qubits, self.config.n_layers)

        scale = 1.0 / np.sqrt(max(1, self.n_features))
        classical = rng.normal(loc=0.0, scale=scale, size=n_class)
        circuit = rng.normal(loc=0.0, scale=0.1, size=n_circ)
        theta = np.concatenate([classical, circuit, np.zeros(1)])

        return HybridParameters(
            theta=theta,
            n_qubits=self.config.n_qubits,
            n_layers=self.config.n_layers,
            n_features=self.n_features,
            n_hidden=self.n_hidden,
        )

    # -- the classical half -----------------------------------------------

    def _split(self, theta):
        """Slice the flat vector. Works on plain and autograd arrays alike."""
        n_w = self.n_features * self.n_hidden
        n_class = n_classical_parameters(self.n_features, self.n_hidden)
        w1 = pnp.reshape(theta[:n_w], (self.n_features, self.n_hidden))
        b1 = theta[n_w:n_class]
        circuit = pnp.reshape(
            theta[n_class : n_class + limits.n_parameters(self.config.n_qubits, self.config.n_layers)],
            (self.config.n_layers, self.config.n_qubits, 2),
        )
        return w1, b1, circuit, theta[-1]

    def angles(self, x, theta):
        """Classical layer output, already mapped into ``[0, π]``.

        Vectorised over the batch on purpose: this half is ordinary linear
        algebra and costs no circuit executions, so there is nothing to gain
        from doing it row by row.
        """
        w1, b1, _, _ = self._split(theta)
        hidden = pnp.tanh(pnp.dot(x, w1) + b1)
        return (hidden + 1.0) * (ANGLE_MAX - ANGLE_MIN) / 2.0 + ANGLE_MIN

    # -- forward ----------------------------------------------------------

    def expectation(self, features, theta):
        """``<Z_0>`` for one *already-encoded* angle vector."""
        _, _, circuit, _ = self._split(theta)
        return self._qnode(features, circuit)

    def decision_values(self, x, theta):
        """``<Z_0> + bias`` for every row of ``x``.

        One QNode call per sample, exactly as the pure VQC does — PennyLane is
        not given a broadcast dimension here, so batch size multiplies circuit
        executions (Phase 4, §2B.3).
        """
        encoded = self.angles(x, theta)
        _, _, circuit, bias = self._split(theta)
        values = [self._qnode(encoded[i], circuit) + bias for i in range(len(x))]
        return pnp.stack(values) if _is_autograd(theta) else np.asarray(values, dtype=float)

    def predict_proba(self, x: np.ndarray, params: HybridParameters) -> np.ndarray:
        values = np.asarray(self.decision_values(x, params.theta), dtype=float)
        return np.clip((1.0 + values) / 2.0, 0.0, 1.0)

    def predict(self, x: np.ndarray, params: HybridParameters) -> np.ndarray:
        return (np.asarray(self.decision_values(x, params.theta), dtype=float) > 0.0).astype(int)

    # -- introspection ----------------------------------------------------

    def describe(self) -> dict[str, object]:
        info = circuit_mod.describe(
            self.config.n_qubits, self.config.n_layers, self.config.entanglement
        )
        info.update(
            {
                "algorithm": "hybrid_qnn",
                "encoding": f"angle-{self.config.rotation}",
                "n_features": self.n_features,
                "n_hidden": self.n_hidden,
                "classical_layer": f"{self.n_features}->{self.n_hidden} affine + tanh",
                "n_classical_parameters": n_classical_parameters(self.n_features, self.n_hidden),
                "n_total_parameters": n_hybrid_parameters(
                    self.n_features, self.n_hidden, self.config.n_qubits, self.config.n_layers
                ),
                "ancilla_wires": self.config.n_qubits - self.n_hidden,
                "diff_method": self.diff_method,
                "interface": "autograd",
                "measurement": "expval(PauliZ(0))",
                "device": "default.qubit",
            }
        )
        return info

    def draw(self, features: np.ndarray, params: HybridParameters) -> str:
        """Text rendering of the circuit for the angles ``features`` produces."""
        encoded = np.asarray(self.angles(np.atleast_2d(features), params.theta), dtype=float)[0]
        return qml.draw(self._qnode, max_length=200)(encoded, params.circuit_weights)


def _is_autograd(value) -> bool:
    return hasattr(value, "_value") or isinstance(value, pnp.tensor)
