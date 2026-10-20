"""Dimension-aware quantum gate definitions for Qudit Lab (Beta).

Supports local dimensions d in {2, 3, 4, 5}.
Implements genuine Cirq Gate protocols (_qid_shape_, _unitary_, _circuit_diagram_info_).
"""

from __future__ import annotations

import cmath
from typing import Any
import cirq
import numpy as np


class QuditShiftGate(cirq.Gate):
    """Generalized cyclic shift gate X_d: |j> -> |(j+1) mod d>."""

    def __init__(self, dimension: int):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        self.dimension = dimension

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        mat = np.zeros((d, d), dtype=np.complex128)
        for j in range(d):
            target = (j + 1) % d
            mat[target, j] = 1.0
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"X_{self.dimension}",))

    def __repr__(self) -> str:
        return f"QuditShiftGate(d={self.dimension})"


class QuditPhaseGate(cirq.Gate):
    """Generalized phase gate Z_d: |j> -> omega^j |j> where omega = exp(2*pi*i / d)."""

    def __init__(self, dimension: int):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        self.dimension = dimension

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        mat = np.zeros((d, d), dtype=np.complex128)
        omega = cmath.exp(2j * np.pi / d)
        for j in range(d):
            mat[j, j] = omega ** j
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"Z_{self.dimension}",))

    def __repr__(self) -> str:
        return f"QuditPhaseGate(d={self.dimension})"


class QuditFourierGate(cirq.Gate):
    """Generalized Fourier gate F_d: |j> -> (1/sqrt(d)) * sum_k omega^(j*k) |k>."""

    def __init__(self, dimension: int):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        self.dimension = dimension

    def _qid_shape_(self) -> tuple[int, ...]:
        return (self.dimension,)

    def _unitary_(self) -> np.ndarray:
        d = self.dimension
        mat = np.zeros((d, d), dtype=np.complex128)
        omega = cmath.exp(2j * np.pi / d)
        inv_sqrt_d = 1.0 / np.sqrt(d)
        for k in range(d):
            for j in range(d):
                mat[k, j] = inv_sqrt_d * (omega ** (j * k))
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=(f"F_{self.dimension}",))

    def __repr__(self) -> str:
        return f"QuditFourierGate(d={self.dimension})"


class QuditSumGate(cirq.Gate):
    """Generalized 2-qudit controlled-addition SUM_d: |a, b> -> |a, (a+b) mod d>."""

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
                out_b = (a + b) % d
                out_idx = a * d + out_b
                mat[out_idx, in_idx] = 1.0
        return mat

    def _circuit_diagram_info_(self, args: cirq.CircuitDiagramInfoArgs) -> cirq.CircuitDiagramInfo:
        return cirq.CircuitDiagramInfo(wire_symbols=("@", f"SUM_{self.dimension}"))

    def __repr__(self) -> str:
        return f"QuditSumGate(d={self.dimension})"


class QuditControlledPhaseGate(cirq.Gate):
    """Generalized 2-qudit controlled-phase CP_d: |a, b> -> exp(2*pi*i*a*b / d) |a, b>."""

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


class QuditSwapGate(cirq.Gate):
    """Generalized 2-qudit SWAP_d: |a, b> -> |b, a> for equal dimension qudits."""

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


class QuditRotationGate(cirq.Gate):
    """Level-selective rotation R_jk(theta, phi) between computational levels j and k."""

    def __init__(self, dimension: int, j: int, k: int, theta: float, phi: float = 0.0):
        super().__init__()
        if dimension < 2 or dimension > 5:
            raise ValueError(f"Dimension must be between 2 and 5, got {dimension}")
        if not (0 <= j < k < dimension):
            raise ValueError(f"Levels must satisfy 0 <= j < k < {dimension}, got j={j}, k={k}")
        self.dimension = dimension
        self.j = j
        self.k = k
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


GATE_CATALOGUE: list[dict[str, Any]] = [
    {
        "id": "x",
        "name": "Generalized Shift (X_d)",
        "symbol": "X_d",
        "description": "Cyclically shifts the basis state |j> to |(j+1) mod d>. Satisfies X_d^d = I.",
        "latex": r"X_d |j\rangle = |j+1 \pmod d\rangle",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [],
    },
    {
        "id": "z",
        "name": "Generalized Phase (Z_d)",
        "symbol": "Z_d",
        "description": "Applies dimension-dependent phase omega^j to basis state |j> where omega = exp(2*pi*i / d).",
        "latex": r"Z_d |j\rangle = \omega^j |j\rangle, \quad \omega = e^{2\pi i / d}",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [],
    },
    {
        "id": "f",
        "name": "Generalized Fourier (F_d)",
        "symbol": "F_d",
        "description": "Creates a dimension-dependent equal superposition. Generalizes the qubit Hadamard gate (F_2 = H).",
        "latex": r"F_d |j\rangle = \frac{1}{\sqrt{d}} \sum_{k=0}^{d-1} \omega^{jk} |k\rangle",
        "num_qudits": 1,
        "is_two_qudit": False,
        "has_controls": False,
        "parameters": [],
    },
    {
        "id": "sum",
        "name": "Generalized Controlled-Addition (SUM_d)",
        "symbol": "SUM_d",
        "description": "Controlled modular addition |a, b> -> |a, (a+b) mod d>. Generalizes CNOT to qudits.",
        "latex": r"\text{SUM}_d |a, b\rangle = |a, (a+b) \pmod d\rangle",
        "num_qudits": 2,
        "is_two_qudit": True,
        "has_controls": True,
        "parameters": [],
    },
    {
        "id": "cp",
        "name": "Controlled-Phase (CP_d)",
        "symbol": "CP_d",
        "description": "Applies a conditional phase omega^(a*b) based on participating levels |a, b>.",
        "latex": r"\text{CP}_d |a, b\rangle = e^{2\pi i a b / d} |a, b\rangle",
        "num_qudits": 2,
        "is_two_qudit": True,
        "has_controls": True,
        "parameters": [],
    },
    {
        "id": "swap",
        "name": "Generalized SWAP (SWAP_d)",
        "symbol": "SWAP_d",
        "description": "Exchanges states of two equal-dimension qudits |a, b> -> |b, a>.",
        "latex": r"\text{SWAP}_d |a, b\rangle = |b, a\rangle",
        "num_qudits": 2,
        "is_two_qudit": True,
        "has_controls": False,
        "parameters": [],
    },
    {
        "id": "r_jk",
        "name": "Subspace Rotation (R_jk)",
        "symbol": "R_jk",
        "description": "Selective SU(2) rotation in the 2D subspace spanned by levels |j> and |k>, acting as identity on other levels.",
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
]


def create_cirq_qudit_gate(
    gate_name: str,
    dimension: int,
    params: dict[str, float] | None = None,
) -> cirq.Gate:
    """Factory creating a verified dimension-aware Cirq gate instance."""
    gate_key = gate_name.lower().strip()
    p = params or {}

    if gate_key == "x":
        return QuditShiftGate(dimension)
    elif gate_key == "z":
        return QuditPhaseGate(dimension)
    elif gate_key == "f":
        return QuditFourierGate(dimension)
    elif gate_key == "sum":
        return QuditSumGate(dimension)
    elif gate_key == "cp":
        return QuditControlledPhaseGate(dimension)
    elif gate_key == "swap":
        return QuditSwapGate(dimension)
    elif gate_key in ("r_jk", "rot", "r"):
        j = int(p.get("j", 0))
        k = int(p.get("k", 1))
        theta = float(p.get("theta", np.pi / 2))
        phi = float(p.get("phi", 0.0))
        if j >= k:
            j, k = min(j, k), max(j, k)
        if k >= dimension:
            k = dimension - 1
            if j >= k:
                j = max(0, k - 1)
        return QuditRotationGate(dimension, j, k, theta, phi)
    else:
        raise ValueError(f"Unsupported qudit gate: '{gate_name}'")
