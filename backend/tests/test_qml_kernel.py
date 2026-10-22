"""Quantum kernel (LSSVM): fidelity properties, the triangle saving, the cap.

The fidelity kernel has exact mathematical properties — symmetry, a diagonal
of exactly 1, a range of [0, 1] — so these are asserted exactly rather than
with a tolerance that would hide a real error.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.quantum.qml_lab import evaluator, limits
from app.quantum.qml_lab.datasets import build_dataset
from app.quantum.qml_lab.errors import QmlConfigError, QmlLimitExceededError
from app.quantum.qml_lab.kernel import (
    QuantumKernel,
    decision_values,
    fit_lssvm,
    kernel_evaluations,
    predict,
)
from app.quantum.qml_lab.models import CircuitConfig, DatasetConfig


def _kernel(n_qubits: int = 4, n_features: int = 2) -> QuantumKernel:
    return QuantumKernel(CircuitConfig(n_qubits=n_qubits, n_layers=2), n_features=n_features)


def _moons(n_samples: int = 60):
    return build_dataset(
        DatasetConfig(name="moons", n_samples=n_samples, noise=0.1, test_fraction=0.3),
        np.random.default_rng(1234),
    )


# ---------------------------------------------------------------------------
# Fidelity kernel properties
# ---------------------------------------------------------------------------


def test_kernel_of_a_point_with_itself_is_exactly_one():
    """``|<φ(x)|φ(x)>|² = 1`` identically — not approximately."""
    kernel = _kernel()
    for point in ([0.0, 0.0], [1.3, 2.9], [np.pi, np.pi]):
        assert kernel.pair(np.array(point), np.array(point)) == pytest.approx(1.0, abs=1e-12)


def test_kernel_is_symmetric():
    kernel = _kernel()
    a, b = np.array([0.4, 2.1]), np.array([2.7, 0.9])
    assert kernel.pair(a, b) == pytest.approx(kernel.pair(b, a), abs=1e-12)


def test_kernel_values_stay_inside_zero_and_one():
    """A probability outside [0, 1] would mean the circuit is not unitary."""
    rng = np.random.default_rng(3)
    kernel = _kernel()
    points = rng.uniform(0.0, np.pi, size=(12, 2))
    for i in range(len(points)):
        for j in range(len(points)):
            value = kernel.pair(points[i], points[j])
            assert 0.0 - 1e-12 <= value <= 1.0 + 1e-12


def test_orthogonal_encodings_give_a_kernel_of_zero():
    """RY(0) and RY(π) are antipodal on the Bloch sphere, so fidelity is 0.

    A concrete analytic value, so the test fails if the adjoint is dropped
    or the probability index is wrong.
    """
    kernel = QuantumKernel(CircuitConfig(n_qubits=1, n_layers=1), n_features=1)
    assert kernel.pair(np.array([0.0]), np.array([np.pi])) == pytest.approx(0.0, abs=1e-12)


def test_kernel_decreases_as_points_separate():
    kernel = QuantumKernel(CircuitConfig(n_qubits=1, n_layers=1), n_features=1)
    origin = np.array([0.0])
    values = [kernel.pair(origin, np.array([d])) for d in (0.0, 0.5, 1.0, 1.5, np.pi)]
    assert values == sorted(values, reverse=True)


def test_gram_matrix_is_symmetric_with_an_exact_unit_diagonal():
    data = _moons(40)
    gram = _kernel().gram(data.x_train)
    assert gram.shape == (data.x_train.shape[0],) * 2
    assert np.array_equal(gram, gram.T), "the mirrored half must be bit-identical"
    assert np.all(gram.diagonal() == 1.0), "diagonal must be written as exactly 1, not computed"


# ---------------------------------------------------------------------------
# The upper-triangle saving, counted
# ---------------------------------------------------------------------------


def test_gram_evaluates_only_the_strict_upper_triangle(monkeypatch):
    """Counted, not asserted in prose.

    ``n(n-1)/2``, not ``n²`` and not ``n(n+1)/2`` — the diagonal is exactly 1
    analytically and must never cost a circuit evaluation.
    """
    data = _moons(40)
    kernel = _kernel()
    n = int(data.x_train.shape[0])

    calls: list[int] = []
    original = kernel.pair
    monkeypatch.setattr(kernel, "pair", lambda a, b: (calls.append(1), original(a, b))[1])

    kernel.gram(data.x_train)

    assert len(calls) == n * (n - 1) // 2
    assert len(calls) == kernel_evaluations(n)["train_pairs"]
    assert len(calls) < n * n / 2, "must be strictly cheaper than half the full matrix"


def test_kernel_evaluation_count_matches_the_documented_ceiling():
    """D-032 priced the cap; the code must agree with the decision record."""
    at_cap = kernel_evaluations(limits.MAX_KERNEL_SAMPLES)
    assert at_cap["train_pairs"] == 31_125  # 250 * 249 / 2
    assert at_cap["naive_full_matrix"] == 62_500
    # the saving is slightly better than 2x because the diagonal is free
    assert at_cap["naive_full_matrix"] / at_cap["train_pairs"] > 2.0


def test_evaluation_count_is_quadratic_which_is_why_the_cap_exists():
    small = kernel_evaluations(100)["train_pairs"]
    large = kernel_evaluations(1000)["train_pairs"]
    assert large / small == pytest.approx(100.0, rel=0.02)


def test_rectangular_kernel_has_no_symmetry_to_exploit():
    data = _moons(40)
    kernel = _kernel()
    rows = kernel.rectangular(data.x_test[:4], data.x_train[:6])
    assert rows.shape == (4, 6)
    assert np.all(rows >= 0.0) and np.all(rows <= 1.0)


# ---------------------------------------------------------------------------
# The hard cap (§2C.3)
# ---------------------------------------------------------------------------


def test_gram_refuses_more_samples_than_the_kernel_cap(monkeypatch):
    monkeypatch.setattr(limits, "MAX_KERNEL_SAMPLES", 10)
    kernel = _kernel()
    with pytest.raises(QmlLimitExceededError, match="capped at 10 samples"):
        kernel.gram(np.zeros((11, 2)))


def test_the_cap_error_quotes_the_cost_that_motivated_it(monkeypatch):
    monkeypatch.setattr(limits, "MAX_KERNEL_SAMPLES", 10)
    with pytest.raises(QmlLimitExceededError, match="circuit evaluations"):
        _kernel().gram(np.zeros((50, 2)))


def test_kernel_cap_is_far_below_the_global_sample_ceiling():
    assert limits.MAX_KERNEL_SAMPLES < limits.MAX_SAMPLES
    assert limits.max_for("quantum_kernel", "n_samples") == limits.MAX_KERNEL_SAMPLES


# ---------------------------------------------------------------------------
# LSSVM
# ---------------------------------------------------------------------------


def test_lssvm_solves_the_dual_system_it_claims_to():
    """Substitute the solution back into the stated linear system."""
    rng = np.random.default_rng(5)
    n, gamma = 8, 2.0
    base = rng.normal(size=(n, n))
    gram = base @ base.T
    y = rng.choice([-1.0, 1.0], size=n)

    fit = fit_lssvm(gram, y, gamma=gamma)

    assert np.sum(fit.alpha) == pytest.approx(0.0, abs=1e-8)
    residual = gram @ fit.alpha + fit.alpha / gamma + fit.bias - y
    assert np.allclose(residual, 0.0, atol=1e-8)


def test_lssvm_survives_a_singular_gram_matrix():
    """Duplicate encoded points are ordinary once features are clipped.

    Without the ``I/γ`` term this raises ``LinAlgError`` on input a user can
    produce by accident.
    """
    gram = np.ones((5, 5))  # every point identical -> rank 1
    fit = fit_lssvm(gram, np.array([1.0, 1.0, -1.0, -1.0, 1.0]), gamma=1.0)
    assert np.all(np.isfinite(fit.alpha))
    assert np.isfinite(fit.bias)


def test_lssvm_rejects_a_non_square_gram():
    with pytest.raises(QmlConfigError, match="square"):
        fit_lssvm(np.zeros((3, 4)), np.zeros(3))


def test_lssvm_rejects_a_label_count_that_does_not_match():
    with pytest.raises(QmlConfigError, match="entries"):
        fit_lssvm(np.eye(4), np.zeros(3))


@pytest.mark.parametrize("gamma", [0.0, -1.0])
def test_lssvm_rejects_a_non_positive_gamma(gamma):
    with pytest.raises(QmlConfigError, match="gamma"):
        fit_lssvm(np.eye(3), np.zeros(3), gamma=gamma)


def test_lssvm_reports_that_every_sample_is_a_support_vector():
    """The LSSVM trade-off, surfaced rather than hidden."""
    fit = fit_lssvm(np.eye(6), np.ones(6))
    assert fit.n_support == 6


def test_smaller_gamma_regularises_harder():
    rng = np.random.default_rng(7)
    base = rng.normal(size=(10, 10))
    gram = base @ base.T
    y = rng.choice([-1.0, 1.0], size=10)
    loose = fit_lssvm(gram, y, gamma=100.0)
    tight = fit_lssvm(gram, y, gamma=0.01)
    assert np.linalg.norm(tight.alpha) < np.linalg.norm(loose.alpha)


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------


def test_decision_values_match_the_stated_formula():
    """Uses a fixture whose bias is provably non-zero.

    The obvious fixture — balanced ±1 labels on an identity Gram — has a bias
    of **exactly 0.0** by symmetry, so it cannot distinguish ``Kα + b`` from
    ``Kα``. Mutant K7 (delete ``+ fit.bias``) survived the whole suite against
    it. The same blindness as the hybrid's output bias: a term that happens
    to be zero is invisible to every test that does not force it otherwise.
    """
    fit = fit_lssvm(np.eye(4), np.array([1.0, 1.0, 1.0, -1.0]))
    assert fit.bias != 0.0, "fixture must have a non-zero bias or it proves nothing"

    rows = np.array([[0.2, 0.4, 0.1, 0.3], [0.9, 0.0, 0.0, 0.1]])
    assert np.allclose(decision_values(fit, rows), rows @ fit.alpha + fit.bias)


def test_the_bias_shifts_every_decision_value_by_exactly_its_own_amount():
    """Pins the bias term's contribution directly, independent of the formula."""
    fit = fit_lssvm(np.eye(4), np.array([1.0, 1.0, 1.0, -1.0]))
    rows = np.array([[0.2, 0.4, 0.1, 0.3], [0.9, 0.0, 0.0, 0.1]])

    before = decision_values(fit, rows)
    fit.bias = fit.bias + 2.5
    after = decision_values(fit, rows)

    assert np.allclose(after - before, 2.5, atol=1e-12)


def test_an_all_one_class_problem_puts_the_answer_entirely_in_the_bias():
    """With a constant target the bias carries it; alpha should be ~0.

    An independent check that the intercept is real and load-bearing rather
    than an unused field that happens to be summed in.
    """
    fit = fit_lssvm(np.eye(3), np.array([5.0, 5.0, 5.0]))
    assert fit.bias == pytest.approx(5.0, abs=1e-9)
    assert np.allclose(fit.alpha, 0.0, atol=1e-9)


def test_predict_is_binary_and_never_emits_a_third_class_at_exactly_zero():
    """``np.sign`` returns 0 at zero, which would be a third label.

    Constructed so the decision value is exactly 0.0, the case a tolerance
    based test would never reach.
    """
    fit = fit_lssvm(np.eye(2), np.array([1.0, -1.0]))
    fit.alpha = np.array([1.0, -1.0])
    fit.bias = 0.0
    rows = np.array([[0.5, 0.5]])  # 1*0.5 + (-1)*0.5 + 0 == 0.0 exactly
    assert decision_values(fit, rows)[0] == 0.0
    assert set(np.unique(predict(fit, rows))) <= {0, 1}


def test_predict_labels_are_zero_and_one_not_minus_one_and_one():
    """The evaluator's confusion matrix indexes on {0, 1}."""
    fit = fit_lssvm(np.eye(3), np.array([1.0, -1.0, 1.0]))
    labels = predict(fit, np.eye(3))
    assert set(np.unique(labels)) <= {0, 1}


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


def test_kernel_classifier_learns_moons_better_than_chance():
    data = _moons(80)
    kernel = _kernel()
    gram = kernel.gram(data.x_train)
    fit = fit_lssvm(gram, np.where(data.y_train == 0, -1.0, 1.0), gamma=1.0)
    predictions = predict(fit, kernel.rectangular(data.x_test, data.x_train))
    assert evaluator.accuracy(data.y_test, predictions) > 0.7


def test_kernel_classifier_is_deterministic():
    """No shot sampling, so two identical runs must agree bit for bit."""

    def run():
        data = _moons(40)
        kernel = _kernel()
        gram = kernel.gram(data.x_train)
        fit = fit_lssvm(gram, np.where(data.y_train == 0, -1.0, 1.0))
        return predict(fit, kernel.rectangular(data.x_test, data.x_train))

    assert np.array_equal(run(), run())


def test_describe_labels_the_classifier_lssvm_not_svm():
    """§2C.3: the overclaim is the thing being prevented."""
    described = _kernel().describe()
    assert described["classifier"] == "LSSVM"
    assert described["algorithm"] == "quantum_kernel"
    assert described["max_samples"] == limits.MAX_KERNEL_SAMPLES
    assert "upper triangle" in str(described["computes"])


def test_limit_error_does_not_shred_a_single_string_into_characters():
    """Regression guard for a real defect found while writing this module.

    ``QmlLimitExceededError`` joins its argument with "; ". A bare string is
    a valid iterable of characters, so passing one produced
    ``t; o; o;  ; b; i; g`` in the API response — wrong, and silent, because
    the type hint was never enforced.
    """
    from app.quantum.qml_lab.errors import QmlLimitExceededError

    single = QmlLimitExceededError("too many samples")
    assert single.violations == ["too many samples"]
    assert str(single) == "too many samples"

    several = QmlLimitExceededError(["a", "b"])
    assert str(several) == "a; b"


def test_algorithm_overrides_track_the_live_constants(monkeypatch):
    """The snapshot-vs-live defect, pinned in the structure where it recurred.

    A module-level dict literal captures the constant at import, so a runtime
    change never reaches ``limits_for`` and a ceiling test passes against the
    real value while believing it tested the patched one.
    """
    monkeypatch.setattr(limits, "MAX_KERNEL_SAMPLES", 42)
    assert limits.max_for("quantum_kernel", "n_samples") == 42
    assert limits._algorithm_overrides()["quantum_kernel"]["n_samples"] == 42
