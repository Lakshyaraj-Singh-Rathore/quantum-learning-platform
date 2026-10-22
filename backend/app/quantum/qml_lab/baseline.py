"""Classical reference model: L2-regularised logistic regression.

The quantum-vs-classical comparison is only worth showing if the classical
side is a genuinely trained model. A constant or majority-class predictor
would make the QNN look good for free, so this fits real coefficients with
``scipy.optimize.minimize`` (L-BFGS-B) on the analytic gradient, and
``tests/test_qml_baseline.py`` asserts both that the coefficients move from
their initialisation and that accuracy clears a floor on separable data.

scipy is already a pinned dependency (``scipy==1.17.1``); scikit-learn is not,
and is not being added — DECISIONS.md D-014.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from app.quantum.qml_lab.models import BaselineResult


def _sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable logistic function.

    The naive ``1/(1+exp(-z))`` overflows for large negative ``z``; this
    branches so neither tail overflows.
    """
    out = np.empty_like(z, dtype=float)
    positive = z >= 0
    out[positive] = 1.0 / (1.0 + np.exp(-z[positive]))
    exp_z = np.exp(z[~positive])
    out[~positive] = exp_z / (1.0 + exp_z)
    return out


@dataclass
class LogisticRegressionBaseline:
    """Binary logistic regression with an intercept and L2 penalty."""

    l2: float = 1e-3
    max_iterations: int = 500

    coefficients: np.ndarray | None = None
    intercept: float = 0.0
    converged: bool = False
    initial_coefficients: np.ndarray | None = None

    def fit(self, x: np.ndarray, y: np.ndarray, rng: np.random.Generator) -> "LogisticRegressionBaseline":
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n_features = x.shape[1]

        start = np.concatenate([rng.normal(scale=0.01, size=n_features), np.zeros(1)])
        self.initial_coefficients = start[:-1].copy()

        def objective(params: np.ndarray) -> tuple[float, np.ndarray]:
            weights, bias = params[:-1], params[-1]
            logits = x @ weights + bias
            probabilities = _sigmoid(logits)
            # Mean negative log-likelihood, clipped away from log(0).
            clipped = np.clip(probabilities, 1e-12, 1.0 - 1e-12)
            loss = -np.mean(y * np.log(clipped) + (1 - y) * np.log(1 - clipped))
            loss += 0.5 * self.l2 * float(weights @ weights)

            residual = probabilities - y
            grad_w = x.T @ residual / x.shape[0] + self.l2 * weights
            grad_b = float(np.mean(residual))
            return loss, np.concatenate([grad_w, [grad_b]])

        result = minimize(
            objective,
            start,
            jac=True,
            method="L-BFGS-B",
            options={"maxiter": self.max_iterations},
        )

        self.coefficients = np.asarray(result.x[:-1], dtype=float)
        self.intercept = float(result.x[-1])
        self.converged = bool(result.success)
        return self

    # -- inference --------------------------------------------------------

    def _check_fitted(self) -> np.ndarray:
        if self.coefficients is None:
            raise ValueError("baseline is not fitted; call fit() first")
        return self.coefficients

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        weights = self._check_fitted()
        return _sigmoid(np.asarray(x, dtype=float) @ weights + self.intercept)

    def predict(self, x: np.ndarray) -> np.ndarray:
        return (self.predict_proba(x) >= 0.5).astype(int)

    @property
    def n_parameters(self) -> int:
        weights = self._check_fitted()
        return int(weights.size) + 1

    def coefficient_shift(self) -> float:
        """How far the coefficients travelled from their initialisation.

        A trained model moves; a stub does not. The test asserts this is
        comfortably non-zero, which is the cheapest guard against the baseline
        silently degrading into a constant predictor.
        """
        weights = self._check_fitted()
        if self.initial_coefficients is None:
            return 0.0
        return float(np.linalg.norm(weights - self.initial_coefficients))


def run_baseline(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
    rng: np.random.Generator,
) -> BaselineResult:
    """Fit on the training split and score both splits."""
    model = LogisticRegressionBaseline().fit(x_train, y_train, rng)
    return BaselineResult(
        model="logistic_regression_l2",
        train_accuracy=float(np.mean(model.predict(x_train) == np.asarray(y_train).ravel())),
        test_accuracy=float(np.mean(model.predict(x_test) == np.asarray(y_test).ravel())),
        n_parameters=model.n_parameters,
        converged=model.converged,
    )
