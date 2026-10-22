"""Quantum regression: continuous targets, continuous output, MSE.

Three things change relative to the classifier, and all three are the kind of
difference that produces a model which *runs* while being quietly wrong if
you skip it (vision §2C.4):

1. **The metrics are different.** Accuracy, precision, recall, F1 and a
   confusion matrix are undefined for a continuous target. MAE, RMSE and R²
   replace them, in a separate result type rather than a union with nullable
   fields.
2. **The loss is different.** Mean squared error on the raw residual, not the
   ±1 margin loss the classifier uses.
3. **The target needs its own scaler.** ``<Z₀>`` lives in ``[-1, 1]``, so a
   target in, say, ``[0, 40]`` is unreachable no matter how the circuit is
   trained — the model would converge to predicting a constant and look
   broken. The target is scaled into ``[-1, 1]`` on the **training split
   only** and predictions are mapped back, so every reported MAE and RMSE is
   in the user's own units.

Point 3 is the leakage-sensitive one: fitting the target scaler on all the
data before splitting would leak the test split's range into training, and
R² would be flattering. :class:`TargetScaler` is fitted from ``y_train``
alone and ``tests/test_qml_regression.py`` asserts it.
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
from app.quantum.qml_lab.models import CircuitConfig, RegressionResult

# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean absolute error."""
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    if y_true.shape != y_pred.shape:
        raise ValueError(f"shape mismatch: y_true {y_true.shape} vs y_pred {y_pred.shape}")
    if y_true.size == 0:
        return 0.0
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root mean squared error."""
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    if y_true.shape != y_pred.shape:
        raise ValueError(f"shape mismatch: y_true {y_true.shape} vs y_pred {y_pred.shape}")
    if y_true.size == 0:
        return 0.0
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Coefficient of determination, ``1 - SS_res/SS_tot``.

    When the truth is constant ``SS_tot`` is zero and R² is undefined. Rather
    than returning ``nan`` into a JSON response, report 1.0 if the prediction
    is also exactly that constant and 0.0 otherwise — which is what the score
    means in the limit, and keeps the number renderable.
    """
    y_true = np.asarray(y_true, dtype=float).ravel()
    y_pred = np.asarray(y_pred, dtype=float).ravel()
    if y_true.shape != y_pred.shape:
        raise ValueError(f"shape mismatch: y_true {y_true.shape} vs y_pred {y_pred.shape}")
    if y_true.size == 0:
        return 0.0

    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
    if ss_tot == 0.0:
        return 1.0 if ss_res == 0.0 else 0.0
    return float(1.0 - ss_res / ss_tot)


def evaluate_regression(y_true: np.ndarray, y_pred: np.ndarray) -> RegressionResult:
    """Full regression metric set for one split, in the target's own units."""
    return RegressionResult(
        mae=mae(y_true, y_pred),
        rmse=rmse(y_true, y_pred),
        r2=r2_score(y_true, y_pred),
        n_samples=int(np.asarray(y_true).size),
    )


# ---------------------------------------------------------------------------
# Target scaling
# ---------------------------------------------------------------------------


@dataclass
class TargetScaler:
    """Map a continuous target onto ``[-1, 1]`` and back.

    Fitted on the **training split only**. The quantum model's output is
    ``<Z₀> + bias``, so a target outside roughly ``[-1, 1]`` is simply not
    representable; without this the model would saturate and report a
    catastrophic R² that says nothing about the circuit.
    """

    y_min: float = 0.0
    y_max: float = 1.0
    fitted: bool = False

    def fit(self, y_train: np.ndarray) -> "TargetScaler":
        y = np.asarray(y_train, dtype=float).ravel()
        if y.size == 0:
            raise QmlConfigError("cannot fit a target scaler on an empty training split")
        self.y_min = float(np.min(y))
        self.y_max = float(np.max(y))
        self.fitted = True
        return self

    @property
    def _span(self) -> float:
        span = self.y_max - self.y_min
        # A constant target is degenerate but must not divide by zero; mapping
        # everything to 0.0 is the honest answer and R² will report it.
        return span if span > 0.0 else 1.0

    def transform(self, y: np.ndarray) -> np.ndarray:
        if not self.fitted:
            raise QmlConfigError("TargetScaler.transform called before fit")
        y = np.asarray(y, dtype=float)
        return 2.0 * (y - self.y_min) / self._span - 1.0

    def inverse_transform(self, z: np.ndarray) -> np.ndarray:
        if not self.fitted:
            raise QmlConfigError("TargetScaler.inverse_transform called before fit")
        z = np.asarray(z, dtype=float)
        return (z + 1.0) / 2.0 * self._span + self.y_min

    def to_dict(self) -> dict[str, float | bool]:
        return {"y_min": self.y_min, "y_max": self.y_max, "fitted": self.fitted}


# ---------------------------------------------------------------------------
# Loss
# ---------------------------------------------------------------------------


def mse_loss(predictions, targets):
    """Mean squared error, autograd-differentiable.

    The classifier's ``square_loss`` works on ±1 labels; this is the same
    algebra but stated separately because the semantics differ — here the
    residual is in scaled target units, not a classification margin.
    """
    diff = predictions - targets
    return pnp.mean(diff**2)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass
class RegressionParameters:
    """Circuit angles plus one output bias, for the regressor."""

    theta: np.ndarray
    n_qubits: int
    n_layers: int

    @property
    def n_circuit_parameters(self) -> int:
        return limits.n_parameters(self.n_qubits, self.n_layers)

    @property
    def circuit_weights(self) -> np.ndarray:
        return np.asarray(self.theta[:-1], dtype=float).reshape(self.n_layers, self.n_qubits, 2)

    @property
    def bias(self) -> float:
        return float(self.theta[-1])

    def copy(self) -> "RegressionParameters":
        return RegressionParameters(
            theta=np.array(self.theta, dtype=float),
            n_qubits=self.n_qubits,
            n_layers=self.n_layers,
        )


class QuantumRegressor:
    """``<Z₀> + bias`` read as a continuous prediction in scaled units.

    Structurally close to the classifier — same ansatz, same encoder, same
    one-QNode-call-per-sample loop — but the output is used directly rather
    than thresholded, and it is never squashed into a probability.
    """

    def __init__(
        self,
        config: CircuitConfig,
        n_features: int,
        diff_method: str = "backprop",
        data_reuploading: bool = True,
    ) -> None:
        validate_feature_fit(n_features, config.n_qubits)
        self.config = config
        self.n_features = int(n_features)
        self.diff_method = diff_method
        self.data_reuploading = bool(data_reuploading)
        self.device = qml.device("default.qubit", wires=config.n_qubits)
        self._qnode = self._build_qnode()

    def _build_qnode(self):
        """Encode once, or re-encode before every ansatz layer.

        **Re-uploading is the default, and it is not a tuning preference.**
        A model that encodes the input once is a Fourier series in the
        encoding angle whose accessible spectrum is ``{0, ±1}`` — it can
        represent ``sin(x)`` and literally cannot represent ``sin(2x)``, no
        matter how it is trained or how many ansatz layers follow. Measured
        directly on this circuit: sweeping the input and taking an FFT of
        ``<Z₀>`` gives a single-encoding spectrum with frequency-2 power at
        1e-5, i.e. numerical noise.

        Re-uploading the features before each of ``n_layers`` blocks widens
        the spectrum to frequencies up to ``n_layers`` (Pérez-Salinas et al.,
        "Data re-uploading for a universal quantum classifier"), which is what
        makes a regression target with any real structure learnable at all.
        ``tests/test_qml_regression.py::test_reuploading_widens_the_frequency_
        spectrum`` pins the difference.
        """

        @qml.qnode(self.device, interface="autograd", diff_method=self.diff_method)
        def node(features, weights):
            if not self.data_reuploading:
                apply_angle_encoding(features, self.config.n_qubits, self.config.rotation)
                circuit_mod.apply_ansatz(
                    weights, self.config.n_qubits, self.config.entanglement
                )
            else:
                for layer in range(self.config.n_layers):
                    apply_angle_encoding(
                        features, self.config.n_qubits, self.config.rotation
                    )
                    circuit_mod.apply_ansatz(
                        weights[layer : layer + 1],
                        self.config.n_qubits,
                        self.config.entanglement,
                    )
            return qml.expval(qml.PauliZ(0))

        return node

    def initialise(self, rng: np.random.Generator) -> RegressionParameters:
        n = limits.n_parameters(self.config.n_qubits, self.config.n_layers)
        theta = np.concatenate([rng.normal(loc=0.0, scale=0.1, size=n), np.zeros(1)])
        return RegressionParameters(
            theta=theta, n_qubits=self.config.n_qubits, n_layers=self.config.n_layers
        )

    def expectation(self, features, theta):
        weights = pnp.reshape(theta[:-1], (self.config.n_layers, self.config.n_qubits, 2))
        return self._qnode(features, weights)

    def decision_values(self, x, theta):
        """Continuous prediction in **scaled** units, one QNode call per row."""
        values = [self.expectation(row, theta) + theta[-1] for row in x]
        return pnp.stack(values) if _is_autograd(theta) else np.asarray(values, dtype=float)

    def predict_scaled(self, x: np.ndarray, params: RegressionParameters) -> np.ndarray:
        return np.asarray(self.decision_values(x, params.theta), dtype=float)

    def predict(
        self, x: np.ndarray, params: RegressionParameters, scaler: TargetScaler
    ) -> np.ndarray:
        """Prediction in the **user's** units.

        Takes the scaler explicitly rather than holding one: the scaler
        belongs to the dataset split, and a model silently carrying a stale
        one is how a reloaded artifact starts producing plausible nonsense.
        """
        return scaler.inverse_transform(self.predict_scaled(x, params))

    def describe(self) -> dict[str, object]:
        info = circuit_mod.describe(
            self.config.n_qubits, self.config.n_layers, self.config.entanglement
        )
        info.update(
            {
                "algorithm": "quantum_regression",
                "encoding": f"angle-{self.config.rotation}",
                "n_features": self.n_features,
                "ancilla_wires": self.config.n_qubits - self.n_features,
                "diff_method": self.diff_method,
                "interface": "autograd",
                "measurement": "expval(PauliZ(0))",
                "output": "continuous, scaled to [-1, 1]",
                "data_reuploading": self.data_reuploading,
                "max_frequency": self.config.n_layers if self.data_reuploading else 1,
                "loss": "mse",
                "metrics": ["mae", "rmse", "r2"],
                "device": "default.qubit",
            }
        )
        return info

    def draw(self, features: np.ndarray, params: RegressionParameters) -> str:
        return qml.draw(self._qnode, max_length=200)(features, params.circuit_weights)


def _is_autograd(value) -> bool:
    return hasattr(value, "_value") or isinstance(value, pnp.tensor)
