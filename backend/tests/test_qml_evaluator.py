"""Metrics, checked against values computed by hand.

There is no scikit-learn to cross-check against, so the expected numbers in
this file are worked out from first principles in the comments. If a
definition here is wrong, these tests are the only thing that will say so.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.quantum.qml_lab.evaluator import (
    accuracy,
    confusion_matrix,
    evaluate,
    precision_recall_f1,
)

# A fixed 10-sample vector used across the suite.
#   index : 0  1  2  3  4  5  6  7  8  9
#   true  : 0  0  0  0  1  1  1  1  1  1   -> 4 negatives, 6 positives
#   pred  : 0  0  1  1  1  1  1  0  0  1   -> 6 predicted positive
# TN = indices 0,1            -> 2
# FP = indices 2,3            -> 2
# FN = indices 7,8            -> 2
# TP = indices 4,5,6,9        -> 4
Y_TRUE = np.array([0, 0, 0, 0, 1, 1, 1, 1, 1, 1])
Y_PRED = np.array([0, 0, 1, 1, 1, 1, 1, 0, 0, 1])


def test_confusion_matrix_against_hand_counts():
    assert confusion_matrix(Y_TRUE, Y_PRED).tolist() == [[2, 2], [2, 4]]


def test_accuracy_against_hand_count():
    # (TN + TP) / N = (2 + 4) / 10
    assert accuracy(Y_TRUE, Y_PRED) == pytest.approx(0.6)


def test_precision_recall_f1_against_hand_computation():
    precision, recall, f1 = precision_recall_f1(Y_TRUE, Y_PRED)
    # precision = TP / (TP + FP) = 4 / 6
    # recall    = TP / (TP + FN) = 4 / 6
    # f1        = 2PR / (P + R)  = 4 / 6
    assert precision == pytest.approx(4 / 6)
    assert recall == pytest.approx(4 / 6)
    assert f1 == pytest.approx(4 / 6)


def test_an_asymmetric_case_distinguishes_precision_from_recall():
    #   true : 1 1 1 1 0 0
    #   pred : 1 0 0 0 1 0
    # TP = 1, FN = 3, FP = 1, TN = 1
    # precision = 1/2, recall = 1/4, f1 = 2*(0.5*0.25)/0.75 = 1/3
    y_true = np.array([1, 1, 1, 1, 0, 0])
    y_pred = np.array([1, 0, 0, 0, 1, 0])

    assert confusion_matrix(y_true, y_pred).tolist() == [[1, 1], [3, 1]]
    precision, recall, f1 = precision_recall_f1(y_true, y_pred)
    assert precision == pytest.approx(0.5)
    assert recall == pytest.approx(0.25)
    assert f1 == pytest.approx(1 / 3)


def test_perfect_and_inverted_predictions():
    perfect = np.array([0, 1, 0, 1])
    assert accuracy(perfect, perfect) == 1.0
    assert confusion_matrix(perfect, perfect).tolist() == [[2, 0], [0, 2]]

    inverted = 1 - perfect
    assert accuracy(perfect, inverted) == 0.0
    assert confusion_matrix(perfect, inverted).tolist() == [[0, 2], [2, 0]]


def test_degenerate_cases_return_zero_not_nan():
    """A model that never predicts the positive class must not emit nan.

    Mathematically precision is undefined here; propagating nan into JSON and
    onto a chart is worse than reporting the zero the model behaves like.
    """
    y_true = np.array([0, 0, 1, 1])
    never_positive = np.array([0, 0, 0, 0])

    precision, recall, f1 = precision_recall_f1(y_true, never_positive)
    assert (precision, recall, f1) == (0.0, 0.0, 0.0)
    assert all(np.isfinite(v) for v in (precision, recall, f1))


def test_confusion_matrix_rows_sum_to_the_true_class_counts():
    matrix = confusion_matrix(Y_TRUE, Y_PRED)
    assert matrix[0].sum() == int(np.sum(Y_TRUE == 0))
    assert matrix[1].sum() == int(np.sum(Y_TRUE == 1))
    assert matrix.sum() == Y_TRUE.size


def test_evaluate_bundles_everything_consistently():
    result = evaluate(Y_TRUE, Y_PRED)
    assert result.n_samples == 10
    assert result.accuracy == pytest.approx(0.6)
    assert result.confusion_matrix == [[2, 2], [2, 4]]
    assert result.precision == pytest.approx(4 / 6)
    # The bundled result must agree with the standalone helpers.
    assert result.accuracy == accuracy(Y_TRUE, Y_PRED)


def test_shape_mismatch_is_refused():
    with pytest.raises(ValueError):
        confusion_matrix(np.array([0, 1]), np.array([0, 1, 1]))


def test_empty_input_is_handled():
    assert accuracy(np.array([]), np.array([])) == 0.0
