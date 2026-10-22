"""The hybrid classical-quantum classifier.

The claim that needs proving here is not "it trains" — plenty of broken
models train. It is that **one optimiser step updates the classical weights
using a gradient that travelled through a real quantum circuit**. A hybrid
whose classical layer is effectively frozen, or whose gradient is computed
from something other than the circuit, would still produce a descending loss
curve and would still look fine in the UI.

So the load-bearing test is
:func:`test_classical_gradient_matches_finite_differences`, which compares
autograd's gradient of the classical block against a central finite
difference taken *through the circuit*. Nothing is mocked and no gradient is
stubbed (§1 non-negotiables).
"""

from __future__ import annotations

import numpy as np
import pennylane as qml
import pytest
from pennylane import numpy as pnp
from pydantic import ValidationError

from app.quantum.qml_lab import limits
from app.quantum.qml_lab.datasets import build_dataset
from app.quantum.qml_lab.errors import QmlConfigError
from app.quantum.qml_lab.hybrid import (
    ANGLE_MAX,
    ANGLE_MIN,
    HybridParameters,
    HybridQNN,
    n_classical_parameters,
    n_hybrid_parameters,
)
from app.quantum.qml_lab.models import (
    CircuitConfig,
    DatasetConfig,
    QmlExperimentConfig,
    TrainingConfig,
)
from app.quantum.qml_lab.trainer import square_loss, train
from app.quantum.qml_lab.vqc import Parameters


def _model(n_features=2, n_hidden=3, n_qubits=4, n_layers=2, diff_method="backprop"):
    cfg = CircuitConfig(
        n_qubits=n_qubits, n_layers=n_layers, rotation="Y", entanglement="ring"
    )
    return HybridQNN(cfg, n_features=n_features, n_hidden=n_hidden, diff_method=diff_method)


def _batch(model, seed=7, n=5):
    rng = np.random.default_rng(seed)
    params = model.initialise(rng)
    x = rng.uniform(0.0, np.pi, size=(n, model.n_features))
    y = np.where(rng.random(n) > 0.5, 1.0, -1.0)
    return params, x, y


# ---------------------------------------------------------------------------
# Parameter layout
# ---------------------------------------------------------------------------


def test_parameter_vector_is_classical_then_circuit_then_bias():
    model = _model(n_features=2, n_hidden=3, n_qubits=4, n_layers=2)
    params = model.initialise(np.random.default_rng(0))

    assert n_classical_parameters(2, 3) == 2 * 3 + 3
    assert len(params.theta) == n_hybrid_parameters(2, 3, 4, 2) == 9 + 16 + 1

    assert params.classical_weights.shape == (2, 3)
    assert params.classical_bias.shape == (3,)
    assert params.circuit_weights.shape == (2, 4, 2)

    # The slices must tile the vector exactly, with nothing shared or skipped.
    rebuilt = np.concatenate(
        [
            params.classical_weights.reshape(-1),
            params.classical_bias,
            params.circuit_weights.reshape(-1),
            [params.bias],
        ]
    )
    assert np.array_equal(rebuilt, np.asarray(params.theta, dtype=float))


def test_hybrid_parameters_is_not_a_vqc_parameters():
    """A hybrid vector read as a VQC vector would reshape into nonsense.

    Keeping the types separate is what makes that mistake impossible rather
    than merely discouraged, so assert the separation holds.
    """
    model = _model()
    params = model.initialise(np.random.default_rng(0))
    assert not isinstance(params, Parameters)

    with pytest.raises(ValueError):
        # 25 leading entries cannot reshape to (n_layers, n_qubits, 2) = 16.
        Parameters(
            theta=np.asarray(params.theta), n_qubits=4, n_layers=2
        ).circuit_weights


# ---------------------------------------------------------------------------
# The classical half
# ---------------------------------------------------------------------------


def test_classical_layer_output_is_inside_the_encoder_window():
    """tanh is in [-1, 1]; the encoder needs [0, π]. Check the rescaling."""
    model = _model(n_features=2, n_hidden=4)
    rng = np.random.default_rng(3)
    params = model.initialise(rng)
    # Deliberately extreme inputs: tanh saturates, so this probes the bounds.
    x = rng.normal(scale=50.0, size=(64, 2))

    angles = np.asarray(model.angles(x, params.theta), dtype=float)

    assert angles.shape == (64, 4)
    assert angles.min() >= ANGLE_MIN
    assert angles.max() <= ANGLE_MAX


def test_classical_layer_actually_depends_on_its_weights():
    """Perturbing W1 must change the emitted angles."""
    model = _model()
    params = model.initialise(np.random.default_rng(5))
    x = np.random.default_rng(6).uniform(0, np.pi, size=(4, 2))

    before = np.asarray(model.angles(x, params.theta), dtype=float)
    moved = np.array(params.theta, dtype=float)
    moved[0] += 1.0
    after = np.asarray(model.angles(x, moved), dtype=float)

    assert not np.allclose(before, after)


# ---------------------------------------------------------------------------
# End-to-end differentiation -- the load-bearing test
# ---------------------------------------------------------------------------


def test_classical_gradient_matches_finite_differences():
    """Autograd's classical gradient vs a central difference through the circuit.

    If the chain rule did not pass through the QNode, the analytic gradient of
    the classical block would be zero or wrong while the loss still moved.
    Agreement to 1e-7 against a numerical derivative of the *real* circuit is
    what rules that out.
    """
    model = _model(n_features=2, n_hidden=3, n_qubits=4, n_layers=2)
    params, x, y = _batch(model)

    def cost(theta):
        return square_loss(model.decision_values(x, theta), y)

    analytic = np.asarray(
        qml.grad(cost, argnums=0)(pnp.array(params.theta, requires_grad=True)), dtype=float
    )

    n_class = n_classical_parameters(model.n_features, model.n_hidden)
    assert np.linalg.norm(analytic[:n_class]) > 1e-9, "classical gradient is flat"
    assert np.linalg.norm(analytic[n_class:-1]) > 1e-9, "circuit gradient is flat"

    eps = 1e-6
    for i in range(n_class):
        up = np.array(params.theta, dtype=float)
        down = np.array(params.theta, dtype=float)
        up[i] += eps
        down[i] -= eps
        numeric = (float(cost(pnp.array(up))) - float(cost(pnp.array(down)))) / (2 * eps)
        assert numeric == pytest.approx(analytic[i], abs=1e-7), (
            f"classical parameter {i}: autograd {analytic[i]} vs finite difference {numeric}"
        )


def test_backprop_and_parameter_shift_agree_on_the_hybrid():
    """The Phase 1 invariant, re-asserted with a classical layer in the path."""
    back = _model(n_hidden=2, n_qubits=3, n_layers=1, diff_method="backprop")
    shift = _model(n_hidden=2, n_qubits=3, n_layers=1, diff_method="parameter-shift")
    params, x, y = _batch(back, n=4)

    def grad_of(model):
        def cost(theta):
            return square_loss(model.decision_values(x, theta), y)

        return np.asarray(
            qml.grad(cost, argnums=0)(pnp.array(params.theta, requires_grad=True)), dtype=float
        )

    assert np.allclose(grad_of(back), grad_of(shift), atol=1e-9)


def test_same_seed_initialises_bit_identically():
    model = _model()
    a = model.initialise(np.random.default_rng(99)).theta
    b = model.initialise(np.random.default_rng(99)).theta
    c = model.initialise(np.random.default_rng(100)).theta
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def test_training_moves_both_blocks_and_improves_the_loss():
    """Train through the *unmodified* trainer and check both halves learned.

    A hybrid where only the circuit weights move is a VQC with a random fixed
    preprocessor, so the per-block movement assertions are the point.
    """
    cfg = DatasetConfig(name="moons", n_samples=120, noise=0.1, test_fraction=0.3)
    rng = np.random.default_rng(1234)
    data = build_dataset(cfg, rng)

    model = _model(n_features=data.x_train.shape[1], n_hidden=4, n_qubits=4, n_layers=2)
    initial = model.initialise(rng)
    outcome = train(
        model,
        data,
        TrainingConfig(epochs=8, batch_size=16, learning_rate=0.1, diff_method="backprop"),
        rng,
        initial,
    )

    assert outcome.status == "completed"
    assert outcome.epochs_completed == 8
    assert outcome.history[-1].train_loss < outcome.history[0].train_loss

    final = HybridParameters(
        theta=np.asarray(outcome.params.theta),
        n_qubits=4,
        n_layers=2,
        n_features=model.n_features,
        n_hidden=model.n_hidden,
    )
    assert not np.allclose(final.classical_weights, initial.classical_weights)
    assert not np.allclose(final.circuit_weights, initial.circuit_weights)

    accuracy = float((model.predict(data.x_test, final) == data.y_test).mean())
    assert accuracy > 0.6, f"hybrid scored {accuracy} on moons, barely above chance"


def test_bias_shifts_the_decision_value_by_exactly_its_own_amount():
    """The trailing bias must reach the output.

    Found by mutation: deleting ``+ bias`` from ``decision_values`` left the
    whole suite green, because the bias *initialises to zero* and the
    prediction test compared ``predict`` against the same ``decision_values``
    it was derived from — self-consistent, and blind. Setting the bias
    explicitly is the only thing that catches it.
    """
    model = _model()
    params, x, _ = _batch(model)

    theta = np.array(params.theta, dtype=float)
    theta[-1] = 0.0
    unbiased = np.asarray(model.decision_values(x, theta), dtype=float)

    shift = 0.37
    theta[-1] = shift
    biased = np.asarray(model.decision_values(x, theta), dtype=float)

    assert np.allclose(biased - unbiased, shift)
    assert not np.allclose(biased, unbiased)


def test_predictions_are_derived_from_the_measurement():
    model = _model()
    params, x, _ = _batch(model)
    proba = model.predict_proba(x, params)
    labels = model.predict(x, params)
    values = np.asarray(model.decision_values(x, params.theta), dtype=float)

    assert np.all((proba >= 0.0) & (proba <= 1.0))
    assert np.array_equal(labels, (values > 0.0).astype(int))
    assert np.allclose(proba, np.clip((1.0 + values) / 2.0, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Configuration rejection
# ---------------------------------------------------------------------------


def test_classical_layer_wider_than_the_register_is_rejected():
    cfg = CircuitConfig(n_qubits=3, n_layers=1)
    with pytest.raises(QmlConfigError, match="one wire per value"):
        HybridQNN(cfg, n_features=2, n_hidden=4)


def test_n_hidden_above_n_qubits_is_rejected_by_the_schema():
    with pytest.raises(ValidationError, match="one wire per"):
        QmlExperimentConfig.model_validate(
            {
                "algorithm": "hybrid_qnn",
                "circuit": {"n_qubits": 3, "n_hidden": 4},
            }
        )


def test_n_hidden_on_a_non_hybrid_algorithm_is_rejected():
    """Silently ignoring it is the Noise Lab trap this schema exists to avoid."""
    with pytest.raises(ValidationError, match="only valid for algorithm='hybrid_qnn'"):
        QmlExperimentConfig.model_validate(
            {"algorithm": "vqc", "circuit": {"n_qubits": 4, "n_hidden": 2}}
        )


def test_describe_reports_the_classical_block():
    info = _model(n_features=2, n_hidden=3, n_qubits=4, n_layers=2).describe()
    assert info["algorithm"] == "hybrid_qnn"
    assert info["n_hidden"] == 3
    assert info["n_classical_parameters"] == 9
    assert info["n_total_parameters"] == 26
    assert info["interface"] == "autograd"
    assert info["ancilla_wires"] == 1


def test_draw_renders_the_circuit_the_classical_layer_actually_produced():
    """The drawing must show the *computed* angles, not the raw features.

    A drawing that encoded the raw input would look perfectly plausible while
    hiding the fact that the classical layer is in the path at all.
    """
    model = _model(n_features=2, n_hidden=3, n_qubits=4, n_layers=2)
    params = model.initialise(np.random.default_rng(1))
    features = np.array([0.5, 1.0])

    angles = np.asarray(model.angles(np.atleast_2d(features), params.theta), dtype=float)[0]
    drawing = model.draw(features, params)
    lines = [line for line in drawing.splitlines() if line.strip()]

    assert len(lines) == 4, "one line per wire"
    # Each encoded wire opens with an RY carrying its own computed angle.
    for wire in range(model.n_hidden):
        assert f"RY({angles[wire]:.2f})" in lines[wire], (
            f"wire {wire} does not open with the classical layer's angle"
        )
    # The surplus wire is an ancilla: no encoding rotation, straight into the
    # ansatz, which starts at a different angle than any encoded value.
    assert not any(f"RY({a:.2f})" in lines[3] for a in angles)
    assert "<Z>" in lines[0] and "<Z>" not in lines[1]
    assert drawing.count("╭●") >= 2, "entangling layers missing"


# ---------------------------------------------------------------------------
# Per-algorithm ceilings (2C.1)
# ---------------------------------------------------------------------------


#: The only keys an algorithm may add beyond the global table, and the
#: ``supports`` flag in ``/qml/describe`` that announces each one. An addition
#: that is not listed here fails the build rather than appearing in the API
#: unannounced.
DECLARED_EXTRA_LIMIT_KEYS = {"n_hidden": "n_hidden"}


def test_no_algorithm_drops_a_limit_key_and_every_entry_has_the_same_fields():
    """§2C.1: values move per algorithm; the *entry* shape never does.

    Named for what it actually checks. An earlier version of this test was
    called ``..._shape_is_identical_across_algorithms`` while asserting only
    a subset relation — ``hybrid_qnn`` really does carry an extra
    ``n_hidden`` key, so the stronger name was promising a guarantee the code
    does not make. The guarantee that *does* hold is below, and
    :func:`test_any_extra_limit_key_is_declared_and_announced` covers
    additions.
    """
    tables = {a: limits.limits_for(a) for a in limits.ALGORITHMS}
    base_keys = set(limits.LIMITS)
    for algorithm, table in tables.items():
        assert base_keys <= set(table), f"{algorithm} dropped a key the UI reads"
        for key, entry in table.items():
            assert set(entry) == {"default", "min", "max"}, (
                f"{algorithm}.{key} has fields {sorted(entry)}; a UI that renders "
                f"one control per entry needs every entry to look the same"
            )


def test_any_extra_limit_key_is_declared_and_announced():
    """An algorithm may add a key, but never silently.

    This is what lets the config view iterate the limits table and render a
    control per entry **without branching on the algorithm name** (§2C.7):
    an extra key is self-describing, and the matching ``supports`` flag in
    ``/qml/describe`` is asserted to agree with its presence.
    """
    from app.services.qml_lab import describe

    entries = {entry["name"]: entry for entry in describe()["algorithms"]}
    base_keys = set(limits.LIMITS)

    for algorithm in limits.ALGORITHMS:
        extras = set(limits.limits_for(algorithm)) - base_keys
        assert extras <= set(DECLARED_EXTRA_LIMIT_KEYS), (
            f"{algorithm} adds undeclared limit key(s) {extras - set(DECLARED_EXTRA_LIMIT_KEYS)}"
        )
        supports = entries[algorithm]["supports"]
        for key, flag in DECLARED_EXTRA_LIMIT_KEYS.items():
            assert supports[flag] is (key in extras), (
                f"{algorithm}: supports[{flag!r}]={supports[flag]} contradicts the limits "
                f"table, which {'has' if key in extras else 'lacks'} {key!r}"
            )


def test_kernel_sample_ceiling_is_far_below_the_global_one():
    assert limits.MAX_KERNEL_SAMPLES < limits.MAX_SAMPLES
    assert limits.max_for("quantum_kernel", "n_samples") == limits.MAX_KERNEL_SAMPLES
    assert limits.max_for("vqc", "n_samples") == limits.MAX_SAMPLES
    # Defaults must sit inside their own ceiling.
    for algorithm in limits.ALGORITHMS:
        table = limits.limits_for(algorithm)
        for key, spec in table.items():
            assert spec["default"] <= spec["max"], f"{algorithm}.{key} default exceeds its max"


def test_an_algorithm_cannot_loosen_a_global_ceiling():
    for algorithm in limits.ALGORITHMS:
        table = limits.limits_for(algorithm)
        for key, spec in limits.LIMITS.items():
            assert table[key]["max"] <= spec["max"], (
                f"{algorithm} raised {key} above the global maximum"
            )


def test_check_is_evaluated_per_algorithm():
    payload = {
        "dataset": {"name": "moons", "n_samples": 400, "test_fraction": 0.3},
        "circuit": {"n_qubits": 4, "n_layers": 2},
        "training": {"epochs": 1, "batch_size": 16},
    }
    as_vqc = QmlExperimentConfig.model_validate({**payload, "algorithm": "vqc"})
    as_kernel = QmlExperimentConfig.model_validate({**payload, "algorithm": "quantum_kernel"})

    assert limits.check(as_vqc) == []
    violations = limits.check(as_kernel)
    assert len(violations) == 1
    assert "400" in violations[0] and str(limits.MAX_KERNEL_SAMPLES) in violations[0]
    assert "O(N^2)" in violations[0]


def test_unknown_algorithm_is_rejected():
    with pytest.raises(QmlConfigError, match="unknown algorithm"):
        limits.limits_for("definitely_not_an_algorithm")


# ---------------------------------------------------------------------------
# /qml/describe drives the config view (§2C.7)
# ---------------------------------------------------------------------------


def test_describe_lists_every_algorithm_with_one_shape():
    from app.services.qml_lab import describe

    entries = describe()["algorithms"]
    assert [e["name"] for e in entries] == list(limits.ALGORITHMS)
    shapes = {tuple(sorted(e)) for e in entries}
    assert len(shapes) == 1, f"algorithm entries differ in shape: {shapes}"


def test_describe_keeps_every_pre_existing_key():
    """Additive only — the Phase 3 UI reads these and must not break."""
    from app.services.qml_lab import describe

    payload = describe()
    for key in (
        "limits",
        "datasets",
        "diff_methods",
        "rotations",
        "entanglements",
        "device",
        "max_concurrent_experiments",
        "statuses",
    ):
        assert key in payload, f"describe() dropped pre-existing key {key!r}"
    assert payload["limits"] == limits.LIMITS


def test_describe_never_offers_classification_metrics_for_regression():
    """Server-side half of MT-006.

    A config view that hardcodes "accuracy" renders 0 for a regression run,
    and 0 reads as "scored zero" rather than "not applicable". The metric
    list is therefore served, not inferred client-side.
    """
    from app.services.qml_lab import describe

    for entry in describe()["algorithms"]:
        if entry["task"] == "regression":
            assert entry["metrics"] == ["mae", "rmse", "r2"]
            for banned in ("accuracy", "precision", "recall", "f1"):
                assert banned not in entry["metrics"]
                assert banned not in entry["epoch_fields"]
        else:
            assert "accuracy" in entry["metrics"]
            assert "r2" not in entry["metrics"]


def test_describe_marks_the_kernel_as_having_no_epoch_control():
    """The LSSVM is closed-form; an epoch slider for it would be a lie."""
    from app.services.qml_lab import describe

    kernel = next(e for e in describe()["algorithms"] if e["name"] == "quantum_kernel")
    assert kernel["supports"]["epochs"] is False
    assert kernel["supports"]["diff_method"] is False
    assert kernel["limits"]["epochs"]["max"] == 1
    assert "LSSVM" in kernel["label"], "§2C.3 requires the kernel be labelled LSSVM where surfaced"


def test_describe_regression_datasets_carry_their_frequency_requirement():
    """So a UI can warn when n_layers is below what the target needs (D-034)."""
    from app.services.qml_lab import describe

    entry = next(e for e in describe()["algorithms"] if e["name"] == "quantum_regression")
    assert entry["datasets"], "regression must offer its own datasets"
    for dataset in entry["datasets"]:
        assert dataset["required_angle_frequency"] >= 1
        assert dataset["required_angle_frequency"] <= limits.MAX_LAYERS
    names = {d["name"] for d in entry["datasets"]}
    assert "moons" not in names, "classification datasets must not leak into regression"


def test_describe_classification_algorithms_do_not_offer_regression_datasets():
    from app.services.qml_lab import describe

    for entry in describe()["algorithms"]:
        if entry["task"] == "classification":
            names = {d["name"] for d in entry["datasets"]}
            assert "sine" not in names and "linear_mix" not in names
