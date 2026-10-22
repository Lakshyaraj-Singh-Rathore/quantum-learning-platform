"""Encoder, ansatz and the VQC's structure.

These run real circuits on ``default.qubit``. Nothing is mocked: a test that
stubs the QNode proves only that the stub works.
"""

from __future__ import annotations

import numpy as np
import pennylane as qml
import pytest

from app.quantum.qml_lab import circuit as circuit_mod
from app.quantum.qml_lab import limits
from app.quantum.qml_lab.encoder import apply_angle_encoding, validate_feature_fit
from app.quantum.qml_lab.errors import QmlConfigError
from app.quantum.qml_lab.models import CircuitConfig
from app.quantum.qml_lab.vqc import VQC


def _model(n_qubits=2, n_layers=1, rotation="Y", entanglement="ring", n_features=2, diff="backprop") -> VQC:
    return VQC(CircuitConfig(n_qubits=n_qubits, n_layers=n_layers, rotation=rotation, entanglement=entanglement),
               n_features=n_features, diff_method=diff)


# --------------------------------------------------------------------------
# Encoder
# --------------------------------------------------------------------------


def test_more_features_than_wires_is_refused():
    with pytest.raises(QmlConfigError):
        validate_feature_fit(n_features=5, n_qubits=4)


def test_fewer_features_than_wires_is_allowed():
    validate_feature_fit(n_features=2, n_qubits=4)


@pytest.mark.parametrize("rotation", ["X", "Y", "Z"])
def test_every_rotation_axis_actually_encodes_the_data(rotation):
    """Changing the input must change the state — including on the Z axis.

    ``RZ`` on ``|0>`` is a global phase only, so a Z encoding without the
    preceding Hadamard would discard the features entirely and train on
    nothing. This catches that directly.
    """
    device = qml.device("default.qubit", wires=2)

    @qml.qnode(device)
    def node(features):
        apply_angle_encoding(features, n_qubits=2, rotation=rotation)
        return qml.density_matrix(wires=[0, 1])

    # The density matrix, deliberately. Two weaker choices both fail here:
    #   * qml.probs cannot see a Z-axis encoding at all, because the feature
    #     goes into the relative phase and leaves |amplitude|^2 untouched.
    #   * qml.state passes even when the Hadamard is removed, because
    #     RZ(theta)|0> differs from RZ(theta')|0> by a *global* phase, which
    #     the state vector carries but no measurement can ever observe. A
    #     mutation test confirmed that version of this assertion was vacuous.
    # The density matrix quotients out global phase, so a difference here is
    # necessarily observable.
    low = np.asarray(node([0.2, 0.3]))
    high = np.asarray(node([2.9, 0.3]))
    assert not np.allclose(low, high), f"rotation {rotation} ignored its input observably"


def test_unencoded_wires_stay_in_the_ground_state():
    device = qml.device("default.qubit", wires=3)

    @qml.qnode(device)
    def node(features):
        apply_angle_encoding(features, n_qubits=3, rotation="Y")
        return qml.expval(qml.PauliZ(2))

    assert float(node([1.0, 2.0])) == pytest.approx(1.0)


# --------------------------------------------------------------------------
# Ansatz
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "n_qubits, topology, expected",
    [
        (4, "ring", 4),
        (4, "linear", 3),
        (4, "none", 0),
        (2, "ring", 1),
        (2, "linear", 1),
        (1, "ring", 0),
    ],
)
def test_entangler_counts_per_topology(n_qubits, topology, expected):
    """A ring on two wires must not duplicate the chain's only link."""
    info = circuit_mod.describe(n_qubits, n_layers=1, topology=topology)
    assert info["entanglers_per_layer"] == expected


def test_entanglement_actually_entangles():
    """'ring' must produce a non-product state; 'none' must not."""

    def purity_of_subsystem(topology: str) -> float:
        device = qml.device("default.qubit", wires=2)

        @qml.qnode(device)
        def node():
            qml.RY(np.pi / 2, wires=0)
            qml.RY(np.pi / 3, wires=1)
            circuit_mod.apply_entanglement(2, topology)
            return qml.density_matrix(wires=[0])

        reduced = np.asarray(node())
        return float(np.real(np.trace(reduced @ reduced)))

    assert purity_of_subsystem("none") == pytest.approx(1.0, abs=1e-9)
    assert purity_of_subsystem("ring") < 0.99


def test_parameter_count_matches_the_limits_module():
    for n_qubits, n_layers in [(2, 1), (4, 2), (8, 4)]:
        described = circuit_mod.describe(n_qubits, n_layers, "ring")["n_parameters"]
        assert described == limits.n_parameters(n_qubits, n_layers)


# --------------------------------------------------------------------------
# VQC
# --------------------------------------------------------------------------


def test_initialised_weight_vector_has_the_right_length():
    model = _model(n_qubits=4, n_layers=2, n_features=2)
    params = model.initialise(np.random.default_rng(3))
    assert params.theta.size == limits.n_parameters(4, 2) + 1  # +1 for the bias
    assert params.circuit_weights.shape == (2, 4, 2)
    assert params.bias == 0.0


def test_predictions_come_from_a_measurement_in_minus_one_to_one():
    model = _model(n_qubits=2, n_layers=2)
    params = model.initialise(np.random.default_rng(3))
    x = np.random.default_rng(4).uniform(0, np.pi, size=(6, 2))

    values = np.asarray(model.decision_values(x, params.theta), dtype=float)
    assert values.shape == (6,)
    assert np.all(values >= -1.0001) and np.all(values <= 1.0001)

    probabilities = model.predict_proba(x, params)
    assert np.all((probabilities >= 0.0) & (probabilities <= 1.0))

    labels = model.predict(x, params)
    assert set(np.unique(labels)).issubset({0, 1})
    # The hard label must agree with the measured sign, not be computed apart from it.
    assert np.array_equal(labels, (values > 0).astype(int))


def test_the_circuit_responds_to_its_parameters():
    """A circuit that ignores its weights would 'run' and never learn."""
    model = _model(n_qubits=2, n_layers=2)
    rng = np.random.default_rng(3)
    x = rng.uniform(0, np.pi, size=(4, 2))

    first = model.initialise(rng)
    second = first.copy()
    second.theta = second.theta + 0.7

    assert not np.allclose(
        np.asarray(model.decision_values(x, first.theta), dtype=float),
        np.asarray(model.decision_values(x, second.theta), dtype=float),
    )


def test_bias_shifts_the_decision_value_by_exactly_itself():
    model = _model(n_qubits=2, n_layers=1)
    rng = np.random.default_rng(8)
    x = rng.uniform(0, np.pi, size=(3, 2))

    params = model.initialise(rng)
    base = np.asarray(model.decision_values(x, params.theta), dtype=float)

    shifted = params.copy()
    shifted.theta[-1] = 0.25
    moved = np.asarray(model.decision_values(x, shifted.theta), dtype=float)

    assert np.allclose(moved - base, 0.25)


def test_describe_reports_the_real_structure():
    model = _model(n_qubits=4, n_layers=2, n_features=2, rotation="Y")
    info = model.describe()
    assert info["n_qubits"] == 4
    assert info["n_features"] == 2
    assert info["ancilla_wires"] == 2
    assert info["measurement"] == "expval(PauliZ(0))"
    assert info["device"] == "default.qubit"
    assert info["encoding"] == "angle-Y"


def test_draw_renders_a_real_circuit():
    model = _model(n_qubits=2, n_layers=1)
    params = model.initialise(np.random.default_rng(3))
    drawing = model.draw(np.array([0.5, 1.0]), params)
    assert "RY" in drawing and "RZ" in drawing
    assert drawing.count("\n") >= 1


def test_too_many_features_is_refused_at_construction():
    with pytest.raises(QmlConfigError):
        VQC(CircuitConfig(n_qubits=2), n_features=4)
