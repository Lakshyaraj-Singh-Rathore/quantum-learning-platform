"""Quantum kernel classifier, fitted by **least-squares SVM (LSSVM)**.

Three deliberate constraints, all from §2C.3, and each one is the difference
between a page that returns and a page that hangs.

**It is an LSSVM, and it says so everywhere it is surfaced.** A standard
C-SVM needs a quadratic-programming solver and a dual formulation with box
constraints — a dependency and a pile of machinery for an algorithm that is
one of four. An LSSVM replaces the inequality constraints with equalities, so
the whole fit is a single linear system, ``numpy.linalg.solve`` on the matrix
that has *already been computed*. The two are not the same estimator: LSSVM
loses sparsity (every sample becomes a support vector) and is less robust to
outliers. Calling it "SVM" in the UI would be a quiet overclaim, so the label
is "Quantum kernel (LSSVM)" and a test asserts it.

**Only the strict upper triangle is computed.** The kernel is symmetric and
its diagonal is *exactly* 1 — ``|<φ(x)|φ(x)>|² = 1`` by construction, not
approximately — so computing the full matrix does slightly more than twice
the necessary work for no information at all.

**Sample count is capped separately and hard.** Cost is quadratic, which is
the whole problem: priced from the measured 10.377 ms/sample at 8q×4L, 250
samples is ≈326 s and fits inside the 900 s soft limit, while the 1000 the
classifier handles without comment would be ≈87 minutes — 102× over
(D-032). The cap lives in ``ALGORITHM_LIMITS``, not in a comment here.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pennylane as qml

from app.quantum.qml_lab import limits
from app.quantum.qml_lab.encoder import apply_angle_encoding, validate_feature_fit
from app.quantum.qml_lab.errors import QmlConfigError, QmlLimitExceededError
from app.quantum.qml_lab.models import CircuitConfig


def kernel_evaluations(n_train: int, n_test: int = 0) -> dict[str, int]:
    """Exact circuit-evaluation count, before any fitting happens.

    Split out and returned as a dict so ``estimate_cost`` and the UI can show
    the number *before* the user commits to a run — the quadratic term is the
    entire reason this algorithm needs its own ceiling.

    The train block is ``n(n-1)/2``, not ``n(n+1)/2``: the diagonal is exactly
    1 analytically and is never evaluated.
    """
    train = n_train * (n_train - 1) // 2
    test = n_test * n_train
    return {
        "train_pairs": int(train),
        "test_pairs": int(test),
        "total": int(train + test),
        "naive_full_matrix": int(n_train * n_train + n_test * n_train),
    }


@dataclass
class LSSVMFit:
    """The solved dual system plus the data it is defined against."""

    alpha: np.ndarray
    bias: float
    x_train: np.ndarray
    y_train: np.ndarray
    gamma: float

    @property
    def n_support(self) -> int:
        """Every sample is a support vector — that is the LSSVM trade-off.

        Reported rather than hidden, because a reader comparing this to a
        C-SVM will reasonably expect sparsity and should see that it is gone.
        """
        return int(self.x_train.shape[0])


class QuantumKernel:
    """Fidelity kernel ``K(a,b) = |<φ(a)|φ(b)>|²`` over the angle encoding.

    Evaluated as the probability of returning to the all-zeros state after
    ``U(b)`` followed by ``U(a)†``, which is what that inner product *is*;
    no shot sampling, so the value is exact to floating point.
    """

    def __init__(self, config: CircuitConfig, n_features: int) -> None:
        validate_feature_fit(n_features, config.n_qubits)
        self.config = config
        self.n_features = int(n_features)
        self.device = qml.device("default.qubit", wires=config.n_qubits)
        self._qnode = self._build_qnode()

    def _build_qnode(self):
        @qml.qnode(self.device)
        def node(a, b):
            apply_angle_encoding(b, self.config.n_qubits, self.config.rotation)
            qml.adjoint(apply_angle_encoding)(a, self.config.n_qubits, self.config.rotation)
            return qml.probs(wires=range(self.config.n_qubits))

        return node

    def pair(self, a: np.ndarray, b: np.ndarray) -> float:
        """Kernel value for one pair, in ``[0, 1]``."""
        return float(self._qnode(np.asarray(a, dtype=float), np.asarray(b, dtype=float))[0])

    def gram(self, x: np.ndarray, *, progress: object = None) -> np.ndarray:
        """Symmetric Gram matrix, strict upper triangle only.

        The diagonal is written as exactly 1.0 rather than evaluated, and the
        lower triangle is mirrored rather than recomputed.
        """
        x = np.asarray(x, dtype=float)
        n = int(x.shape[0])
        self._guard(n)

        matrix = np.eye(n, dtype=float)
        for i in range(n):
            for j in range(i + 1, n):
                value = self.pair(x[i], x[j])
                matrix[i, j] = value
                matrix[j, i] = value
        return matrix

    def rectangular(self, x_rows: np.ndarray, x_cols: np.ndarray) -> np.ndarray:
        """Kernel between two different sets — no symmetry to exploit."""
        x_rows = np.asarray(x_rows, dtype=float)
        x_cols = np.asarray(x_cols, dtype=float)
        out = np.empty((x_rows.shape[0], x_cols.shape[0]), dtype=float)
        for i in range(x_rows.shape[0]):
            for j in range(x_cols.shape[0]):
                out[i, j] = self.pair(x_rows[i], x_cols[j])
        return out

    def _guard(self, n: int) -> None:
        ceiling = limits.max_for("quantum_kernel", "n_samples")
        if n > ceiling:
            evaluations = kernel_evaluations(n)["train_pairs"]
            raise QmlLimitExceededError(
                [
                    f"quantum_kernel is capped at {ceiling} samples; {n} would need "
                    f"{evaluations:,} circuit evaluations before fitting even begins"
                ]
            )

    def describe(self) -> dict[str, object]:
        return {
            "algorithm": "quantum_kernel",
            "classifier": "LSSVM",
            "kernel": "fidelity |<phi(a)|phi(b)>|^2",
            "encoding": f"angle-{self.config.rotation}",
            "n_qubits": self.config.n_qubits,
            "n_features": self.n_features,
            "device": "default.qubit",
            "computes": "strict upper triangle; diagonal is exactly 1",
            "max_samples": limits.max_for("quantum_kernel", "n_samples"),
        }


def fit_lssvm(gram: np.ndarray, y: np.ndarray, gamma: float = 1.0) -> LSSVMFit:
    """Solve the LSSVM dual system in one shot.

    ``[0    1ᵀ      ] [b]   [0]``
    ``[1    K + I/γ ] [α] = [y]``

    ``I/γ`` is the regularisation that makes the system solvable even when the
    Gram matrix is singular — which it *will* be here, because duplicate or
    near-duplicate encoded points are common once features are clipped into
    ``[0, π]``. Without it this raises ``LinAlgError`` on perfectly ordinary
    input.
    """
    gram = np.asarray(gram, dtype=float)
    y = np.asarray(y, dtype=float).ravel()
    n = gram.shape[0]

    if gram.shape != (n, n):
        raise QmlConfigError(f"gram matrix must be square, got {gram.shape}")
    if y.shape[0] != n:
        raise QmlConfigError(f"gram is {n}x{n} but y has {y.shape[0]} entries")
    if gamma <= 0.0:
        raise QmlConfigError(f"gamma must be positive, got {gamma}")

    system = np.zeros((n + 1, n + 1), dtype=float)
    system[0, 1:] = 1.0
    system[1:, 0] = 1.0
    system[1:, 1:] = gram + np.eye(n) / gamma

    rhs = np.zeros(n + 1, dtype=float)
    rhs[1:] = y

    solution = np.linalg.solve(system, rhs)
    return LSSVMFit(
        alpha=solution[1:],
        bias=float(solution[0]),
        x_train=np.empty((n, 0)),
        y_train=y,
        gamma=float(gamma),
    )


def decision_values(fit: LSSVMFit, kernel_rows: np.ndarray) -> np.ndarray:
    """``f(x) = Σ αᵢ K(x, xᵢ) + b`` for each row of ``kernel_rows``."""
    return np.asarray(kernel_rows, dtype=float) @ fit.alpha + fit.bias


def predict(fit: LSSVMFit, kernel_rows: np.ndarray) -> np.ndarray:
    """Class labels in ``{0, 1}``.

    ``np.sign`` returns 0 at exactly zero, which would be a third class; the
    comparison is therefore written as ``> 0`` so the output is always binary.
    """
    return (decision_values(fit, kernel_rows) > 0.0).astype(int)
