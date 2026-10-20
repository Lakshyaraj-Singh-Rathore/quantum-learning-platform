"""Generalized quantum noise channels for Qudit Lab (Beta).

Supports local dimensions d in {2, 3, 4, 5}.
Implements Kraus representations compatible with Cirq's DensityMatrixSimulator.
"""

from __future__ import annotations

import cmath
from typing import Sequence
import cirq
import numpy as np

from app.quantum.qudit_lab.gates import QuditPhaseGate, QuditShiftGate
from app.quantum.qudit_lab.models import QuditNoiseConfig


class QuditDepolarizingChannel(cirq.Gate):
    """Generalized qudit depolarizing channel:

    E(rho) = (1 - p)*rho + (p / d)*I_d
    Represented via d^2 Kraus operators using generalized Pauli basis {X^j Z^k / sqrt(d)}.
    """

    def __init__(self, dimension: int, p: float):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be in 2..5, got {dimension}")
        if not (0.0 <= p <= 1.0):
            raise ValueError(f"Depolarizing probability p must be in [0, 1], got {p}")
        self.dimension = dimension
        self.p = float(p)

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _kraus_(self) -> Sequence[np.ndarray]:
        d = self.dimension
        p = self.p
        if p == 0.0:
            return [np.eye(d, dtype=np.complex128)]

        x_mat = QuditShiftGate(d)._unitary_()
        z_mat = QuditPhaseGate(d)._unitary_()

        kraus_ops: list[np.ndarray] = []
        c0 = np.sqrt(1.0 - p + (p / (d * d)))
        c_rest = np.sqrt(p / (d * d))

        for j in range(d):
            x_pow = np.linalg.matrix_power(x_mat, j)
            for k in range(d):
                z_pow = np.linalg.matrix_power(z_mat, k)
                op = x_pow @ z_pow
                if j == 0 and k == 0:
                    kraus_ops.append(c0 * op)
                else:
                    kraus_ops.append(c_rest * op)

        return kraus_ops

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"Depol({self.p:.2f})",))

    def __repr__(self) -> str:
        return f"QuditDepolarizingChannel(d={self.dimension}, p={self.p:.3f})"


class QuditDephasingChannel(cirq.Gate):
    """Generalized qudit dephasing channel:

    Damps off-diagonal coherences: rho_jk -> (1 - gamma)*rho_jk (for j != k)
    while preserving diagonal populations rho_jj.
    """

    def __init__(self, dimension: int, gamma: float):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be in 2..5, got {dimension}")
        if not (0.0 <= gamma <= 1.0):
            raise ValueError(f"Dephasing gamma must be in [0, 1], got {gamma}")
        self.dimension = dimension
        self.gamma = float(gamma)

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _kraus_(self) -> Sequence[np.ndarray]:
        d = self.dimension
        gamma = self.gamma
        if gamma == 0.0:
            return [np.eye(d, dtype=np.complex128)]

        kraus_ops: list[np.ndarray] = []
        # K_0 = sqrt(1 - (d-1)/d * gamma) * I_d
        k0_factor = np.sqrt(max(0.0, 1.0 - ((d - 1) / d) * gamma))
        kraus_ops.append(k0_factor * np.eye(d, dtype=np.complex128))

        omega = cmath.exp(2j * np.pi / d)
        km_factor = np.sqrt(gamma / d)
        for m in range(1, d):
            km = np.zeros((d, d), dtype=np.complex128)
            for j in range(d):
                km[j, j] = km_factor * (omega ** (j * m))
            kraus_ops.append(km)

        return kraus_ops

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"Dephase({self.gamma:.2f})",))

    def __repr__(self) -> str:
        return f"QuditDephasingChannel(d={self.dimension}, gamma={self.gamma:.3f})"


class QuditRelaxationChannel(cirq.Gate):
    """Multi-level cascade relaxation channel:

    Models downward decay |j> -> |j-1> with transition rate gamma * j / (d - 1).
    Trace-preserving and positive semidefiniteness preserving.
    """

    def __init__(self, dimension: int, gamma: float):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be in 2..5, got {dimension}")
        if not (0.0 <= gamma <= 1.0):
            raise ValueError(f"Relaxation gamma must be in [0, 1], got {gamma}")
        self.dimension = dimension
        self.gamma = float(gamma)

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _kraus_(self) -> Sequence[np.ndarray]:
        d = self.dimension
        gamma = self.gamma
        if gamma == 0.0:
            return [np.eye(d, dtype=np.complex128)]

        # Probability for each level j
        decay_rates = [gamma * (j / (d - 1)) for j in range(d)]

        # A_0: no-jump operator
        a0 = np.zeros((d, d), dtype=np.complex128)
        for j in range(d):
            a0[j, j] = np.sqrt(max(0.0, 1.0 - decay_rates[j]))
        kraus_ops: list[np.ndarray] = [a0]

        # A_j: decay transition from |j> to |j-1>
        for j in range(1, d):
            aj = np.zeros((d, d), dtype=np.complex128)
            aj[j - 1, j] = np.sqrt(decay_rates[j])
            kraus_ops.append(aj)

        return kraus_ops

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"Relax({self.gamma:.2f})",))

    def __repr__(self) -> str:
        return f"QuditRelaxationChannel(d={self.dimension}, gamma={self.gamma:.3f})"


def get_qudit_noise_operations(
    qudit_id: cirq.Qid,
    noise_config: QuditNoiseConfig | None,
) -> list[cirq.Operation]:
    """Generates Cirq noise operations for a given qudit if configured."""
    if not noise_config or not noise_config.is_active():
        return []

    ops: list[cirq.Operation] = []
    dim = qudit_id.dimension

    if noise_config.depolarizing.enabled and noise_config.depolarizing.p > 0.0:
        ops.append(QuditDepolarizingChannel(dim, noise_config.depolarizing.p).on(qudit_id))

    if noise_config.dephasing.enabled and noise_config.dephasing.gamma > 0.0:
        ops.append(QuditDephasingChannel(dim, noise_config.dephasing.gamma).on(qudit_id))

    if noise_config.relaxation.enabled and noise_config.relaxation.gamma > 0.0:
        ops.append(QuditRelaxationChannel(dim, noise_config.relaxation.gamma).on(qudit_id))

    return ops
