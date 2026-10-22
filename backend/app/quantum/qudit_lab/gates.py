"""Dimension-aware quantum gate definitions for Qudit Lab (Beta).

Supports local dimensions d in {2, 3, 4, 5}.
Implements genuine Cirq Gate protocols (_qid_shape_, _unitary_, _circuit_diagram_info_).
All gate operations follow rigorous quantum mathematical definitions.
"""

from __future__ import annotations

import cmath
from typing import Any
import cirq
import numpy as np


# ==============================================================================
# Single-Qudit Gate Classes
# ==============================================================================

class QuditShiftGate(cirq.Gate):
    """Generalized cyclic shift gate X_d^a: |j> -> |(j+a) mod d>."""

    def __init__(self, dimension: int, power: int = 1):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        self.dimension = dimension
        self.power = int(power) % dimension

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        mat = np.zeros((d, d), dtype=np.complex128)
        for j in range(d):
            target = (j + self.power) % d
            mat[target, j] = 1.0
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        if self.power == 1:
            sym = f"X_{self.dimension}"
        else:
            sym = f"X_{self.dimension}^{self.power}"
        return cirq.CircuitDiagramInfo(wire_symbols=(sym,))

    def __repr__(self) -> str:
        return f"QuditShiftGate(d={self.dimension}, power={self.power})"


class QuditPhaseGate(cirq.Gate):
    """Generalized phase gate Z_d^b: |j> -> omega^(b*j) |j> where omega = exp(2*pi*i / d)."""

    def __init__(self, dimension: int, power: int = 1):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        self.dimension = dimension
        self.power = int(power) % dimension

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        mat = np.zeros((d, d), dtype=np.complex128)
        omega = cmath.exp(2j * np.pi / d)
        for j in range(d):
            mat[j, j] = omega ** (self.power * j)
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        if self.power == 1:
            sym = f"Z_{self.dimension}"
        else:
            sym = f"Z_{self.dimension}^{self.power}"
        return cirq.CircuitDiagramInfo(wire_symbols=(sym,))

    def __repr__(self) -> str:
        return f"QuditPhaseGate(d={self.dimension}, power={self.power})"


class QuditFourierGate(cirq.Gate):
    """Generalized Fourier gate F_d or F_d^dagger.
    
    F_d: (F_d)_{kj} = (1/sqrt(d)) * omega^(j*k)
    F_d^dagger: (F_d^dagger)_{kj} = (1/sqrt(d)) * omega^(-j*k)
    """

    def __init__(self, dimension: int, adjoint: bool = False):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        self.dimension = dimension
        self.adjoint = bool(adjoint)

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        mat = np.zeros((d, d), dtype=np.complex128)
        sign = -1.0 if self.adjoint else 1.0
        omega = cmath.exp(sign * 2j * np.pi / d)
        inv_sqrt_d = 1.0 / np.sqrt(d)
        for k in range(d):
            for j in range(d):
                mat[k, j] = inv_sqrt_d * (omega ** (j * k))
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        sym = f"F_{self.dimension}†" if self.adjoint else f"F_{self.dimension}"
        return cirq.CircuitDiagramInfo(wire_symbols=(sym,))

    def __repr__(self) -> str:
        return f"QuditFourierGate(d={self.dimension}, adjoint={self.adjoint})"


class QuditIdentityGate(cirq.Gate):
    """Identity gate I_d."""

    def __init__(self, dimension: int):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        self.dimension = dimension

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        return np.eye(self.dimension, dtype=np.complex128)

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"I_{self.dimension}",))

    def __repr__(self) -> str:
        return f"QuditIdentityGate(d={self.dimension})"


class QuditLevelPhaseGate(cirq.Gate):
    """Level-selective phase P_j(theta): |k> -> exp(i*theta*delta_jk) |k>."""

    def __init__(self, dimension: int, j: int, theta: float):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if not (0 <= j < dimension):
            raise ValueError(f"Target level j must satisfy 0 <= j < {dimension}, got {j}")
        self.dimension = dimension
        self.j = int(j)
        self.theta = float(theta)

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        mat = np.eye(self.dimension, dtype=np.complex128)
        mat[self.j, self.j] = cmath.exp(1j * self.theta)
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"P_{self.j}(θ)",))

    def __repr__(self) -> str:
        return f"QuditLevelPhaseGate(d={self.dimension}, j={self.j}, θ={self.theta:.3f})"


class QuditRotationGate(cirq.Gate):
    """Pairwise level rotation R_jk(theta, phi) on ordered levels j and k."""

    def __init__(self, dimension: int, j: int, k: int, theta: float, phi: float = 0.0):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if not (0 <= j < dimension and 0 <= k < dimension):
            raise ValueError(f"Levels must satisfy 0 <= j, k < {dimension}, got j={j}, k={k}")
        if j == k:
            raise ValueError(f"Levels must be distinct (j != k), got j=k={j}")
        self.dimension = dimension
        self.j = int(j)
        self.k = int(k)
        self.theta = float(theta)
        self.phi = float(phi)

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        mat = np.eye(d, dtype=np.complex128)
        c = np.cos(self.theta / 2.0)
        s = np.sin(self.theta / 2.0)
        phase_pos = cmath.exp(1j * self.phi)
        phase_neg = cmath.exp(-1j * self.phi)

        mat[self.j, self.j] = c
        mat[self.j, self.k] = -phase_neg * s
        mat[self.k, self.j] = phase_pos * s
        mat[self.k, self.k] = c
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"R_{self.j}{self.k}(θ)",))

    def __repr__(self) -> str:
        return f"QuditRotationGate(d={self.dimension}, j={self.j}, k={self.k}, θ={self.theta:.3f}, φ={self.phi:.3f})"


class QuditDiagonalGate(cirq.Gate):
    """General diagonal unitary D_d = diag(exp(i*phi_0), ..., exp(i*phi_{d-1}))."""

    def __init__(self, dimension: int, phases: list[float]):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if len(phases) < dimension:
            phases = list(phases) + [0.0] * (dimension - len(phases))
        self.dimension = dimension
        self.phases = [float(p) for p in phases[:dimension]]

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        diag_elements = [cmath.exp(1j * p) for p in self.phases]
        return np.diag(diag_elements).astype(np.complex128)

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"D_{self.dimension}",))

    def __repr__(self) -> str:
        return f"QuditDiagonalGate(d={self.dimension}, phases={self.phases})"


class QuditArbitraryUnitaryGate(cirq.Gate):
    """Arbitrary validated single-qudit unitary U_d."""

    def __init__(self, dimension: int, matrix: np.ndarray):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        arr = np.asarray(matrix, dtype=np.complex128)
        if arr.shape != (dimension, dimension):
            raise ValueError(f"Matrix shape must be ({dimension}, {dimension}), got {arr.shape}")
        if not np.all(np.isfinite(arr)):
            raise ValueError("Matrix contains non-finite values (NaN or Inf)")
        # Check unitarity U^dagger U = I within tolerance
        prod = arr.conj().T @ arr
        if not np.allclose(prod, np.eye(dimension), atol=1e-5):
            raise ValueError(f"Matrix is not unitary: U†U residual = {np.max(np.abs(prod - np.eye(dimension)))}")
        self.dimension = dimension
        self.matrix = arr

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        return self.matrix.copy()

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"U_{self.dimension}",))

    def __repr__(self) -> str:
        return f"QuditArbitraryUnitaryGate(d={self.dimension})"


class QuditPermutationGate(cirq.Gate):
    """Basis permutation gate mapping |j> -> |perm[j]>."""

    def __init__(self, dimension: int, perm: list[int]):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if sorted(perm) != list(range(dimension)):
            raise ValueError(f"Permutation must be a bijective mapping of 0..{dimension-1}, got {perm}")
        self.dimension = dimension
        self.perm = [int(p) for p in perm]

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        mat = np.zeros((d, d), dtype=np.complex128)
        for j, target in enumerate(self.perm):
            mat[target, j] = 1.0
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"Π_{self.dimension}",))

    def __repr__(self) -> str:
        return f"QuditPermutationGate(d={self.dimension}, perm={self.perm})"


# ==============================================================================
# Two-Qudit Gate Classes
# ==============================================================================

class QuditSumGate(cirq.Gate):
    """Generalized 2-qudit controlled-addition SUM_d: |a, b> -> |a, (a+b) mod d>
    or inverse SUM_d^dagger: |a, b> -> |a, (b-a) mod d>.
    """

    def __init__(self, dimension: int, adjoint: bool = False):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        self.dimension = dimension
        self.adjoint = bool(adjoint)

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension, self.dimension)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        dim = d * d
        mat = np.zeros((dim, dim), dtype=np.complex128)
        for a in range(d):
            for b in range(d):
                in_idx = a * d + b
                out_b = (b - a) % d if self.adjoint else (a + b) % d
                out_idx = a * d + out_b
                mat[out_idx, in_idx] = 1.0
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        target_sym = f"SUM_{self.dimension}†" if self.adjoint else f"SUM_{self.dimension}"
        return cirq.CircuitDiagramInfo(wire_symbols=("@", target_sym))

    def __repr__(self) -> str:
        return f"QuditSumGate(d={self.dimension}, adjoint={self.adjoint})"


class QuditControlledShiftGate(cirq.Gate):
    """Controlled modular shift CSX_d(c, a): |x, y> -> |x, (y + a*delta_xc) mod d>."""

    def __init__(self, dimension: int, control_level: int = 1, shift: int = 1):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if not (0 <= control_level < dimension):
            raise ValueError(f"Control level must be in 0..{dimension-1}, got {control_level}")
        self.dimension = dimension
        self.control_level = int(control_level)
        self.shift = int(shift) % dimension

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension, self.dimension)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        dim = d * d
        mat = np.zeros((dim, dim), dtype=np.complex128)
        for x in range(d):
            for y in range(d):
                in_idx = x * d + y
                out_y = (y + self.shift) % d if x == self.control_level else y
                out_idx = x * d + out_y
                mat[out_idx, in_idx] = 1.0
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"@{self.control_level}", f"X^{self.shift}"))

    def __repr__(self) -> str:
        return f"QuditControlledShiftGate(d={self.dimension}, c={self.control_level}, shift={self.shift})"


class QuditControlledPhaseGate(cirq.Gate):
    """Generalized controlled-phase GCP_d: |a, b> -> omega^(a*b) |a, b>."""

    def __init__(self, dimension: int):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        self.dimension = dimension

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension, self.dimension)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        dim = d * d
        mat = np.zeros((dim, dim), dtype=np.complex128)
        omega = cmath.exp(2j * np.pi / d)
        for a in range(d):
            for b in range(d):
                idx = a * d + b
                mat[idx, idx] = omega ** (a * b)
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=("@", f"CP_{self.dimension}"))

    def __repr__(self) -> str:
        return f"QuditControlledPhaseGate(d={self.dimension})"


class QuditSelectiveControlledPhaseGate(cirq.Gate):
    """Level-selective controlled phase SCP_d(theta, c, t): |a, b> -> exp(i*theta*delta_ac*delta_bt) |a, b>."""

    def __init__(self, dimension: int, control_level: int, target_level: int, theta: float):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if not (0 <= control_level < dimension and 0 <= target_level < dimension):
            raise ValueError(f"Levels must be in 0..{dimension-1}, got c={control_level}, t={target_level}")
        self.dimension = dimension
        self.control_level = int(control_level)
        self.target_level = int(target_level)
        self.theta = float(theta)

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension, self.dimension)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        mat = np.eye(d * d, dtype=np.complex128)
        idx = self.control_level * d + self.target_level
        mat[idx, idx] = cmath.exp(1j * self.theta)
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"@{self.control_level}", f"P_{self.target_level}(θ)"))

    def __repr__(self) -> str:
        return f"QuditSelectiveControlledPhaseGate(d={self.dimension}, c={self.control_level}, t={self.target_level}, θ={self.theta:.3f})"


class QuditSwapGate(cirq.Gate):
    """Generalized 2-qudit SWAP_d: |a, b> -> |b, a>."""

    def __init__(self, dimension: int):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        self.dimension = dimension

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension, self.dimension)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        dim = d * d
        mat = np.zeros((dim, dim), dtype=np.complex128)
        for a in range(d):
            for b in range(d):
                in_idx = a * d + b
                out_idx = b * d + a
                mat[out_idx, in_idx] = 1.0
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=("x", "x"))

    def __repr__(self) -> str:
        return f"QuditSwapGate(d={self.dimension})"


class QuditControlledUnitaryGate(cirq.Gate):
    """Controlled unitary CU_d applying U when control is at level c."""

    def __init__(self, dimension: int, control_level: int, target_unitary: np.ndarray):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if not (0 <= control_level < dimension):
            raise ValueError(f"Control level must be in 0..{dimension-1}, got {control_level}")
        u = np.asarray(target_unitary, dtype=np.complex128)
        if u.shape != (dimension, dimension):
            raise ValueError(f"Target unitary shape must be ({dimension}, {dimension}), got {u.shape}")
        prod = u.conj().T @ u
        if not np.allclose(prod, np.eye(dimension), atol=1e-5):
            raise ValueError("Target matrix for CU is not unitary")
        self.dimension = dimension
        self.control_level = int(control_level)
        self.target_unitary = u

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension, self.dimension)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        dim = d * d
        mat = np.zeros((dim, dim), dtype=np.complex128)
        for x in range(d):
            if x == self.control_level:
                for y in range(d):
                    for y_prime in range(d):
                        in_idx = x * d + y_prime
                        out_idx = x * d + y
                        mat[out_idx, in_idx] = self.target_unitary[y, y_prime]
            else:
                for y in range(d):
                    idx = x * d + y
                    mat[idx, idx] = 1.0
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"@{self.control_level}", f"U_{self.dimension}"))

    def __repr__(self) -> str:
        return f"QuditControlledUnitaryGate(d={self.dimension}, c={self.control_level})"


# ==============================================================================
# Multi-Qudit / Multi-Controlled Gate Classes
# ==============================================================================

class QuditMultiControlledShiftGate(cirq.Gate):
    """Multi-controlled modular shift:
    |x_1, ..., x_k, t> -> |x_1, ..., x_k, (t + a*prod delta_xi_ci) mod d>.
    Supports 2 controls (double-controlled shift) or general k controls.
    """

    def __init__(self, dimension: int, num_controls: int, control_levels: list[int], shift: int = 1):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if num_controls < 1:
            raise ValueError(f"num_controls must be at least 1, got {num_controls}")
        if len(control_levels) != num_controls:
            raise ValueError(f"control_levels length {len(control_levels)} must match num_controls {num_controls}")
        for c in control_levels:
            if not (0 <= c < dimension):
                raise ValueError(f"Control level {c} out of bounds for d={dimension}")
        self.dimension = dimension
        self.num_controls = int(num_controls)
        self.control_levels = [int(c) for c in control_levels]
        self.shift = int(shift) % dimension

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,) * (self.num_controls + 1)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        n_qudits = self.num_controls + 1
        dim = d ** n_qudits
        mat = np.zeros((dim, dim), dtype=np.complex128)

        # Lexicographical iteration over all basis configurations
        for in_idx in range(dim):
            # Decompose in_idx into digits base d
            temp = in_idx
            digits = []
            for _ in range(n_qudits):
                digits.append(temp % d)
                temp //= d
            digits.reverse()

            controls = digits[:-1]
            target = digits[-1]

            if controls == self.control_levels:
                out_target = (target + self.shift) % d
            else:
                out_target = target

            out_digits = controls + [out_target]
            out_idx = 0
            for dig in out_digits:
                out_idx = out_idx * d + dig

            mat[out_idx, in_idx] = 1.0

        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        symbols = [f"@{c}" for c in self.control_levels] + [f"X^{self.shift}"]
        return cirq.CircuitDiagramInfo(wire_symbols=tuple(symbols))

    def __repr__(self) -> str:
        return f"QuditMultiControlledShiftGate(d={self.dimension}, controls={self.control_levels}, shift={self.shift})"


class QuditMultiControlledPhaseGate(cirq.Gate):
    """Multi-controlled phase applying exp(i*theta) only to |levels[0], ..., levels[n-1]>."""

    def __init__(self, dimension: int, num_qudits: int, levels: list[int], theta: float):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if len(levels) != num_qudits:
            raise ValueError(f"levels count {len(levels)} must match num_qudits {num_qudits}")
        for l in levels:
            if not (0 <= l < dimension):
                raise ValueError(f"Level {l} out of bounds for d={dimension}")
        self.dimension = dimension
        self.num_qudits = int(num_qudits)
        self.levels = [int(l) for l in levels]
        self.theta = float(theta)

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,) * self.num_qudits

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        dim = d ** self.num_qudits
        mat = np.eye(dim, dtype=np.complex128)

        # Compute index of the target level tuple
        target_idx = 0
        for l in self.levels:
            target_idx = target_idx * d + l

        mat[target_idx, target_idx] = cmath.exp(1j * self.theta)
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        symbols = [f"@{l}" for l in self.levels[:-1]] + [f"P_{self.levels[-1]}(θ)"]
        return cirq.CircuitDiagramInfo(wire_symbols=tuple(symbols))

    def __repr__(self) -> str:
        return f"QuditMultiControlledPhaseGate(d={self.dimension}, levels={self.levels}, θ={self.theta:.3f})"


class QuditControlledSwapGate(cirq.Gate):
    """Controlled SWAP gate: 1 control qudit + 2 target qudits.
    Swaps the two targets when the control is at level c.
    """

    def __init__(self, dimension: int, control_level: int = 1):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if not (0 <= control_level < dimension):
            raise ValueError(f"Control level {control_level} out of bounds for d={dimension}")
        self.dimension = dimension
        self.control_level = int(control_level)

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension, self.dimension, self.dimension)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        dim = d ** 3
        mat = np.zeros((dim, dim), dtype=np.complex128)

        for x in range(d):
            for a in range(d):
                for b in range(d):
                    in_idx = (x * d + a) * d + b
                    if x == self.control_level:
                        out_idx = (x * d + b) * d + a
                    else:
                        out_idx = in_idx
                    mat[out_idx, in_idx] = 1.0

        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"@{self.control_level}", "x", "x"))

    def __repr__(self) -> str:
        return f"QuditControlledSwapGate(d={self.dimension}, c={self.control_level})"


# ==============================================================================
# Gate Catalogue Metadata
# ==============================================================================

GATE_CATALOGUE: list[dict[str, Any]] = [
    # Single Qudit
    {
        "id": "x",
        "name": "Generalized Shift (X_d)",
        "symbol": "X_d",
        "category": "single",
        "description": "Cyclically shifts the basis state |j> to |(j+a) mod d>. Satisfies X_d^d = I.",
        "latex": r"X_d^a |j\rangle = |(j+a) \pmod d\rangle",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [
            {"name": "power", "label": "Shift Power a", "default": 1, "min": 1, "max": 4, "step": 1},
        ],
    },
    {
        "id": "z",
        "name": "Generalized Phase (Z_d)",
        "symbol": "Z_d",
        "category": "single",
        "description": "Applies dimension-dependent phase omega^(b*j) to |j> where omega = exp(2*pi*i / d).",
        "latex": r"Z_d^b |j\rangle = \omega^{bj} |j\rangle, \quad \omega = e^{2\pi i / d}",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [
            {"name": "power", "label": "Phase Power b", "default": 1, "min": 1, "max": 4, "step": 1},
        ],
    },
    {
        "id": "f",
        "name": "Generalized Fourier (F_d)",
        "symbol": "F_d",
        "category": "single",
        "description": "Creates a dimension-dependent equal superposition. Generalizes Hadamard (F_2 = H).",
        "latex": r"F_d |j\rangle = \frac{1}{\sqrt{d}} \sum_{k=0}^{d-1} \omega^{jk} |k\rangle",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [],
    },
    {
        "id": "f_dag",
        "name": "Inverse Fourier (F_d†)",
        "symbol": "F_d†",
        "category": "single",
        "description": "Conjugate transpose inverse of Fourier gate F_d. F_d† F_d = I_d.",
        "latex": r"F_d^\dagger |j\rangle = \frac{1}{\sqrt{d}} \sum_{k=0}^{d-1} \omega^{-jk} |k\rangle",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [],
    },
    {
        "id": "id",
        "name": "Identity (I_d)",
        "symbol": "I_d",
        "category": "single",
        "description": "Identity operation leaving qudit state unchanged.",
        "latex": r"I_d |j\rangle = |j\rangle",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [],
    },
    {
        "id": "p_j",
        "name": "Level Phase (P_j)",
        "symbol": "P_j",
        "category": "single",
        "description": "Applies phase exp(i*theta) exclusively to computational level |j>.",
        "latex": r"P_j(\theta) |k\rangle = e^{i\theta \delta_{jk}} |k\rangle",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [
            {"name": "j", "label": "Target Level j", "default": 1, "min": 0, "max": 4, "step": 1},
            {"name": "theta", "label": "Angle θ (rad)", "default": 1.5708, "min": -6.283, "max": 6.283, "step": 0.05},
        ],
    },
    {
        "id": "r_jk",
        "name": "Subspace Rotation (R_jk)",
        "symbol": "R_jk",
        "category": "single",
        "description": "Selective SU(2) rotation in the 2D subspace spanned by levels |j> and |k>.",
        "latex": r"R_{jk}(\theta, \phi) = \exp\left(-i \frac{\theta}{2} (\cos\phi \sigma_x^{jk} + \sin\phi \sigma_y^{jk})\right)",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [
            {"name": "j", "label": "Level j", "default": 0, "min": 0, "max": 4, "step": 1},
            {"name": "k", "label": "Level k", "default": 1, "min": 0, "max": 4, "step": 1},
            {"name": "theta", "label": "Angle θ (rad)", "default": 1.5708, "min": -6.283, "max": 6.283, "step": 0.05},
            {"name": "phi", "label": "Phase φ (rad)", "default": 0.0, "min": -6.283, "max": 6.283, "step": 0.05},
        ],
    },
    {
        "id": "diag",
        "name": "Diagonal Unitary (D_d)",
        "symbol": "D_d",
        "category": "single",
        "description": "Configurable per-level phase unitary D_d = diag(exp(i*phi_0), ..., exp(i*phi_{d-1})).",
        "latex": r"D_d = \sum_{j=0}^{d-1} e^{i\phi_j} |j\rangle\langle j|",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [
            {"name": "phi_0", "label": "Phase φ₀", "default": 0.0, "min": -6.283, "max": 6.283, "step": 0.05},
            {"name": "phi_1", "label": "Phase φ₁", "default": 1.5708, "min": -6.283, "max": 6.283, "step": 0.05},
            {"name": "phi_2", "label": "Phase φ₂", "default": 3.1416, "min": -6.283, "max": 6.283, "step": 0.05},
        ],
    },
    # Two Qudit
    {
        "id": "sum",
        "name": "Controlled-Addition (SUM_d)",
        "symbol": "SUM_d",
        "category": "two_qudit",
        "description": "Controlled modular addition |a, b> -> |a, (a+b) mod d>. Generalizes CNOT.",
        "latex": r"\text{SUM}_d |a, b\rangle = |a, (a+b) \pmod d\rangle",
        "num_qudits": 2,
        "is_two_qudit": True,
        "has_controls": True,
        "parameters": [],
    },
    {
        "id": "sum_dag",
        "name": "Inverse Addition (SUM_d†)",
        "symbol": "SUM_d†",
        "category": "two_qudit",
        "description": "Inverse controlled modular addition |a, b> -> |a, (b-a) mod d>.",
        "latex": r"\text{SUM}_d^\dagger |a, b\rangle = |a, (b-a) \pmod d\rangle",
        "num_qudits": 2,
        "is_two_qudit": True,
        "has_controls": True,
        "parameters": [],
    },
    {
        "id": "csx",
        "name": "Controlled Shift (CSX_d)",
        "symbol": "CSX_d",
        "category": "two_qudit",
        "description": "Applies modular shift to target only when control is at level c.",
        "latex": r"\text{CSX}_d(c, a) |x, y\rangle = |x, (y + a\delta_{xc}) \pmod d\rangle",
        "num_qudits": 2,
        "is_two_qudit": True,
        "has_controls": True,
        "parameters": [
            {"name": "c", "label": "Control Level c", "default": 1, "min": 0, "max": 4, "step": 1},
            {"name": "a", "label": "Shift a", "default": 1, "min": 1, "max": 4, "step": 1},
        ],
    },
    {
        "id": "cp",
        "name": "Controlled-Phase (GCP_d)",
        "symbol": "GCP_d",
        "category": "two_qudit",
        "description": "Generalized product controlled-phase omega^(a*b) |a, b>.",
        "latex": r"\text{GCP}_d |a, b\rangle = e^{2\pi i a b / d} |a, b\rangle",
        "num_qudits": 2,
        "is_two_qudit": True,
        "has_controls": True,
        "parameters": [],
    },
    {
        "id": "scp",
        "name": "Selective CP (SCP_d)",
        "symbol": "SCP_d",
        "category": "two_qudit",
        "description": "Applies phase exp(i*theta) only when control is at level c and target at level t.",
        "latex": r"\text{SCP}_d(\theta, c, t) |a, b\rangle = e^{i\theta \delta_{ac}\delta_{bt}} |a, b\rangle",
        "num_qudits": 2,
        "is_two_qudit": True,
        "has_controls": True,
        "parameters": [
            {"name": "c", "label": "Control Level c", "default": 1, "min": 0, "max": 4, "step": 1},
            {"name": "t", "label": "Target Level t", "default": 1, "min": 0, "max": 4, "step": 1},
            {"name": "theta", "label": "Phase θ (rad)", "default": 1.5708, "min": -6.283, "max": 6.283, "step": 0.05},
        ],
    },
    {
        "id": "swap",
        "name": "Generalized SWAP (SWAP_d)",
        "symbol": "SWAP_d",
        "category": "two_qudit",
        "description": "Exchanges states of two equal-dimension qudits |a, b> -> |b, a>.",
        "latex": r"\text{SWAP}_d |a, b\rangle = |b, a\rangle",
        "num_qudits": 2,
        "is_two_qudit": True,
        "has_controls": False,
        "parameters": [],
    },
    # Multi-Qudit
    {
        "id": "ccx",
        "name": "Double-Controlled Shift",
        "symbol": "CCX_d",
        "category": "multi",
        "description": "Shifts target qudit when two control qudits match levels (c1, c2). Qudit Toffoli.",
        "latex": r"|x, y, z\rangle \to |x, y, (z + a\delta_{x c_1}\delta_{y c_2}) \pmod d\rangle",
        "num_qudits": 3,
        "is_two_qudit": False,
        "has_controls": True,
        "parameters": [
            {"name": "c1", "label": "Ctrl 1 Level", "default": 1, "min": 0, "max": 4, "step": 1},
            {"name": "c2", "label": "Ctrl 2 Level", "default": 1, "min": 0, "max": 4, "step": 1},
            {"name": "a", "label": "Shift a", "default": 1, "min": 1, "max": 4, "step": 1},
        ],
    },
    {
        "id": "cswap",
        "name": "Controlled SWAP (Fredkin_d)",
        "symbol": "CSWAP_d",
        "category": "multi",
        "description": "Swaps two target qudits when the control qudit is at level c.",
        "latex": r"|c, a, b\rangle \to |c, b, a\rangle \text{ if } x=c \text{ else } |c, a, b\rangle",
        "num_qudits": 3,
        "is_two_qudit": False,
        "has_controls": True,
        "parameters": [
            {"name": "c", "label": "Control Level c", "default": 1, "min": 0, "max": 4, "step": 1},
        ],
    },
    {
        "id": "mcp",
        "name": "Multi-Controlled Phase",
        "symbol": "MCP_d",
        "category": "multi",
        "description": "Applies exp(i*theta) only when all participating qudits match specified basis levels.",
        "latex": r"\text{MCP}_d(\theta) |\mathbf{x}\rangle = e^{i\theta \prod_i \delta_{x_i, c_i}} |\mathbf{x}\rangle",
        "num_qudits": 3,
        "is_two_qudit": False,
        "has_controls": True,
        "parameters": [
            {"name": "theta", "label": "Phase θ (rad)", "default": 1.5708, "min": -6.283, "max": 6.283, "step": 0.05},
        ],
    },
]


def create_cirq_qudit_gate(
    gate_name: str,
    dimension: int,
    params: dict[str, Any] | None = None,
) -> cirq.Gate:
    """Factory creating a verified dimension-aware Cirq gate instance."""
    gate_key = gate_name.lower().strip()
    p = params or {}

    # Single-qudit
    if gate_key == "x":
        power = int(p.get("power", p.get("a", 1)))
        return QuditShiftGate(dimension, power=power)
    elif gate_key == "z":
        power = int(p.get("power", p.get("b", 1)))
        return QuditPhaseGate(dimension, power=power)
    elif gate_key == "f":
        return QuditFourierGate(dimension, adjoint=False)
    elif gate_key in ("f_dag", "fdg", "f_adj"):
        return QuditFourierGate(dimension, adjoint=True)
    elif gate_key in ("id", "i"):
        return QuditIdentityGate(dimension)
    elif gate_key in ("p_j", "pj", "phase_j"):
        j = int(p.get("j", 1))
        theta = float(p.get("theta", np.pi / 2))
        return QuditLevelPhaseGate(dimension, j=j, theta=theta)
    elif gate_key in ("r_jk", "rot", "r"):
        j = int(p.get("j", 0))
        k = int(p.get("k", 1))
        theta = float(p.get("theta", np.pi / 2))
        phi = float(p.get("phi", 0.0))
        if j == k:
            k = (j + 1) % dimension
        return QuditRotationGate(dimension, j, k, theta, phi)
    elif gate_key in ("diag", "d_d"):
        if "phases" in p and isinstance(p["phases"], (list, tuple)):
            phases = [float(x) for x in p["phases"]]
        else:
            phases = [float(p.get(f"phi_{i}", 0.0)) for i in range(dimension)]
        return QuditDiagonalGate(dimension, phases)
    elif gate_key in ("u_d", "u"):
        matrix = np.array(p["matrix"], dtype=np.complex128)
        return QuditArbitraryUnitaryGate(dimension, matrix)
    elif gate_key == "perm":
        perm = p.get("perm", list(range(dimension)))
        return QuditPermutationGate(dimension, perm)

    # Two-qudit
    elif gate_key == "sum":
        return QuditSumGate(dimension, adjoint=False)
    elif gate_key in ("sum_dag", "sum_adj", "sub"):
        return QuditSumGate(dimension, adjoint=True)
    elif gate_key == "csx":
        c = int(p.get("c", p.get("control_level", 1)))
        a = int(p.get("a", p.get("shift", 1)))
        return QuditControlledShiftGate(dimension, control_level=c, shift=a)
    elif gate_key in ("cp", "gcp"):
        return QuditControlledPhaseGate(dimension)
    elif gate_key == "scp":
        c = int(p.get("c", 1))
        t = int(p.get("t", 1))
        theta = float(p.get("theta", np.pi / 2))
        return QuditSelectiveControlledPhaseGate(dimension, control_level=c, target_level=t, theta=theta)
    elif gate_key == "swap":
        return QuditSwapGate(dimension)
    elif gate_key == "cu":
        c = int(p.get("c", 1))
        matrix = np.array(p["matrix"], dtype=np.complex128)
        return QuditControlledUnitaryGate(dimension, control_level=c, target_unitary=matrix)

    # Multi-qudit
    elif gate_key in ("ccx", "ccx_d", "ccshift"):
        c1 = int(p.get("c1", 1))
        c2 = int(p.get("c2", 1))
        a = int(p.get("a", 1))
        return QuditMultiControlledShiftGate(dimension, num_controls=2, control_levels=[c1, c2], shift=a)
    elif gate_key in ("mcx", "mcx_d"):
        ctrl_levels = [int(x) for x in p.get("control_levels", [1, 1])]
        a = int(p.get("a", 1))
        return QuditMultiControlledShiftGate(dimension, num_controls=len(ctrl_levels), control_levels=ctrl_levels, shift=a)
    elif gate_key in ("mcp", "mcp_d"):
        levels = [int(x) for x in p.get("levels", [1, 1, 1])]
        theta = float(p.get("theta", np.pi / 2))
        return QuditMultiControlledPhaseGate(dimension, num_qudits=len(levels), levels=levels, theta=theta)
    elif gate_key in ("cswap", "cswap_d"):
        c = int(p.get("c", 1))
        return QuditControlledSwapGate(dimension, control_level=c)

    else:
        raise ValueError(f"Unsupported qudit gate: '{gate_name}'")
