"""Gradients: the two supported differentiation methods must agree.

This is the permanent form of the Phase 0 feasibility probe, which measured
``max|parameter-shift - backprop| = 2.220e-16`` on a real circuit. Keeping it
as a test means the agreement is re-proved on every run rather than cited
from a report.

Both methods are exact on a state-vector simulator, so the tolerance is 1e-9
— the same bar the repository's golden suites use — not a loose "close
enough" threshold.
"""

from __future__ import annotations

import numpy as np
import pytest
from pennylane import grad as qml_grad
from pennylane import numpy as pnp

from app.quantum.qml_lab.models import CircuitConfig
from app.quantum.qml_lab.trainer import square_loss, to_pm1
from app.quantum.qml_lab.vqc import VQC

TOLERANCE = 1e-9


def _setup(n_qubits=2, n_layers=1, diff="backprop"):
    config = CircuitConfig(n_qubits=n_qubits, n_layers=n_layers)
    model = VQC(config, n_features=2, diff_method=diff)
    rng = np.random.default_rng(17)
    params = model.initialise(rng)
    x = rng.uniform(0.0, np.pi, size=(6, 2))
    y = to_pm1(np.array([0, 1, 0, 1, 1, 0]))
    return model, params, x, y


def _loss_gradient(model, theta, x, y):
    def cost(parameters):
        return square_loss(model.decision_values(x, parameters), y)

    return np.asarray(qml_grad(cost, argnums=0)(pnp.array(theta, requires_grad=True)), dtype=float)


def test_backprop_and_parameter_shift_agree_on_the_loss_gradient():
    backprop_model, params, x, y = _setup(diff="backprop")
    shift_model = VQC(backprop_model.config, n_features=2, diff_method="parameter-shift")

    g_backprop = _loss_gradient(backprop_model, params.theta, x, y)
    g_shift = _loss_gradient(shift_model, params.theta, x, y)

    delta = float(np.max(np.abs(g_backprop - g_shift)))
    assert delta < TOLERANCE, f"gradient methods disagree by {delta:.3e}"


@pytest.mark.parametrize("n_qubits, n_layers", [(2, 1), (3, 2)])
def test_agreement_holds_across_circuit_shapes(n_qubits, n_layers):
    backprop_model, params, x, y = _setup(n_qubits=n_qubits, n_layers=n_layers, diff="backprop")
    shift_model = VQC(backprop_model.config, n_features=2, diff_method="parameter-shift")

    delta = float(
        np.max(np.abs(_loss_gradient(backprop_model, params.theta, x, y) - _loss_gradient(shift_model, params.theta, x, y)))
    )
    assert delta < TOLERANCE


def test_gradient_is_not_trivially_zero():
    """An all-zero gradient would make every agreement test pass vacuously."""
    model, params, x, y = _setup()
    gradient = _loss_gradient(model, params.theta, x, y)

    assert gradient.shape == params.theta.shape
    assert np.linalg.norm(gradient) > 1e-6
    assert np.count_nonzero(np.abs(gradient) > 1e-9) >= 2


def test_gradient_matches_a_central_finite_difference():
    """Check the autodiff result against an independent numerical estimate.

    Finite differences know nothing about PennyLane's machinery, so agreement
    here rules out both methods sharing a common bug.
    """
    model, params, x, y = _setup()
    analytic = _loss_gradient(model, params.theta, x, y)

    def loss_at(theta):
        return float(square_loss(np.asarray(model.decision_values(x, theta), dtype=float), y))

    step = 1e-6
    for index in range(min(4, params.theta.size)):
        plus, minus = params.theta.copy(), params.theta.copy()
        plus[index] += step
        minus[index] -= step
        numeric = (loss_at(plus) - loss_at(minus)) / (2 * step)
        assert numeric == pytest.approx(analytic[index], abs=1e-6)


def test_the_bias_gradient_is_analytic():
    """d/d(bias) of mean((y - (<Z> + b))^2) is -2 * mean(y - <Z> - b).

    Hand-derived, so a sign error in the loss shows up immediately.
    """
    model, params, x, y = _setup()
    gradient = _loss_gradient(model, params.theta, x, y)

    values = np.asarray(model.decision_values(x, params.theta), dtype=float)
    expected = float(-2.0 * np.mean(y - values))

    assert gradient[-1] == pytest.approx(expected, abs=1e-9)


def test_parameter_shift_is_not_silently_falling_back_to_backprop():
    """Confirm the QNode really was built with the method we asked for."""
    _, params, x, y = _setup()
    shift_model = VQC(CircuitConfig(n_qubits=2, n_layers=1), n_features=2, diff_method="parameter-shift")

    assert shift_model.diff_method == "parameter-shift"
    assert shift_model.describe()["diff_method"] == "parameter-shift"
    assert np.linalg.norm(_loss_gradient(shift_model, params.theta, x, y)) > 1e-6
