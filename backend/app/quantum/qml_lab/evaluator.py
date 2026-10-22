"""Classification metrics, computed from first principles.

There is no scikit-learn here to cross-check against, so the definitions are
spelled out and ``tests/test_qml_evaluator.py`` checks them against values
computed by hand on a small fixed prediction vector.

Convention for the confusion matrix is ``[[TN, FP], [FN, TP]]`` — rows are the
true class, columns the predicted class, class 1 is positive. The UI's matrix
view in Phase 3 renders it in that orientation, so it is stated here once
rather than being inferred at each use.
"""

from __future__ import annotations

import numpy as np

from app.quantum.qml_lab.models import EvaluationResult


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """2x2 counts as ``[[TN, FP], [FN, TP]]``."""
    y_true = np.asarray(y_true).astype(int).ravel()
    y_pred = np.asarray(y_pred).astype(int).ravel()
    if y_true.shape != y_pred.shape:
        raise ValueError(f"shape mismatch: y_true {y_true.shape} vs y_pred {y_pred.shape}")

    true_negative = int(np.sum((y_true == 0) & (y_pred == 0)))
    false_positive = int(np.sum((y_true == 0) & (y_pred == 1)))
    false_negative = int(np.sum((y_true == 1) & (y_pred == 0)))
    true_positive = int(np.sum((y_true == 1) & (y_pred == 1)))
    return np.array([[true_negative, false_positive], [false_negative, true_positive]], dtype=int)


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    y_true = np.asarray(y_true).astype(int).ravel()
    y_pred = np.asarray(y_pred).astype(int).ravel()
    if y_true.size == 0:
        return 0.0
    return float(np.mean(y_true == y_pred))


def precision_recall_f1(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float, float]:
    """Precision, recall and F1 for the positive class.

    Each degenerate case returns 0.0 rather than ``nan``: a model that never
    predicts the positive class has undefined precision mathematically, but
    propagating ``nan`` into a JSON response and onto a chart is worse than
    reporting the zero it behaves like.
    """
    matrix = confusion_matrix(y_true, y_pred)
    false_positive, false_negative, true_positive = int(matrix[0][1]), int(matrix[1][0]), int(matrix[1][1])

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return float(precision), float(recall), float(f1)


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> EvaluationResult:
    """Full metric set for one split."""
    precision, recall, f1 = precision_recall_f1(y_true, y_pred)
    return EvaluationResult(
        accuracy=accuracy(y_true, y_pred),
        precision=precision,
        recall=recall,
        f1=f1,
        confusion_matrix=confusion_matrix(y_true, y_pred).tolist(),
        n_samples=int(np.asarray(y_true).size),
    )
