"""Quantum metrics, physical validation, and partial trace operations for Qudit Lab."""

from __future__ import annotations

import itertools
import math
from typing import Any
import numpy as np

from app.quantum.qudit_lab.models import (
    ComplexVal,
    ReducedStateResult,
    StateValidation,
)

TOLERANCE_TRACE = 1e-5
TOLERANCE_HERMITIAN = 1e-5
TOLERANCE_POSITIVITY = -1e-5


def format_complex(val: complex) -> ComplexVal:
    """Converts a complex number to a serialized ComplexVal with magnitude and phase."""
    r = float(np.real(val))
    i = float(np.imag(val))
    # Clean up floating point noise near zero
    if abs(r) < 1e-12:
        r = 0.0
    if abs(i) < 1e-12:
        i = 0.0
    mag = float(np.abs(val))
    phase = float(np.angle(val))
    if mag < 1e-12:
        phase = 0.0
    return ComplexVal(real=r, imag=i, mag=mag, phase=phase)


def matrix_to_complex_grid(mat: np.ndarray) -> list[list[ComplexVal]]:
    """Converts 2D numpy complex matrix to nested list of ComplexVal."""
    rows, cols = mat.shape
    return [[format_complex(mat[r, c]) for c in range(cols)] for r in range(rows)]


def generate_basis_labels(dimensions: list[int]) -> list[str]:
    """Generates standard computational basis state labels e.g. ['|0,0>', '|0,1>', ...] in lexicographic order."""
    if not dimensions:
        return []
    ranges = [range(d) for d in dimensions]
    labels: list[str] = []
    for tup in itertools.product(*ranges):
        labels.append("|" + ",".join(str(x) for x in tup) + "⟩")
    return labels


def validate_density_matrix(
    rho: np.ndarray,
    total_dim: int,
    calculate_entropy: bool = True,
) -> StateValidation:
    """Validates trace, Hermiticity, positive-semidefiniteness, purity and von Neumann entropy."""
    diagnostics: list[str] = []

    # Check shape
    if rho.shape != (total_dim, total_dim):
        return StateValidation(
            is_valid=False,
            trace=0.0,
            trace_residual=1.0,
            hermiticity_residual=1.0,
            is_hermitian=False,
            min_eigenvalue=-1.0,
            is_positive_semidefinite=False,
            purity=0.0,
            entropy=None,
            diagnostics=[f"Invalid shape {rho.shape}, expected ({total_dim}, {total_dim})"],
        )

    # 1. Trace
    tr = float(np.real(np.trace(rho)))
    tr_residual = float(abs(tr - 1.0))
    if tr_residual > TOLERANCE_TRACE:
        diagnostics.append(f"Trace residual {tr_residual:.2e} exceeds tolerance {TOLERANCE_TRACE:.2e}")

    # 2. Hermiticity: rho == rho^dagger
    diff_herm = rho - rho.conj().T
    herm_residual = float(np.max(np.abs(diff_herm)))
    is_herm = herm_residual <= TOLERANCE_HERMITIAN
    if not is_herm:
        diagnostics.append(f"Hermiticity residual {herm_residual:.2e} exceeds tolerance {TOLERANCE_HERMITIAN:.2e}")

    # 3. Positivity & eigenvalues
    # Enforce symmetric/hermitian projection for numerical stability before eigh
    rho_sym = 0.5 * (rho + rho.conj().T)
    evals = np.linalg.eigvalsh(rho_sym)
    min_eval = float(np.min(evals))
    is_psd = min_eval >= TOLERANCE_POSITIVITY
    if not is_psd:
        diagnostics.append(f"Negative eigenvalue detected: {min_eval:.2e}")

    # 4. Purity: gamma = Tr(rho^2) = sum(lambda_i^2)
    purity = float(np.sum(evals ** 2))
    # Clamp purity to theoretical interval [1/D, 1] within tolerance
    min_theoretical_purity = 1.0 / total_dim
    if purity < min_theoretical_purity - 1e-4 or purity > 1.0001:
        diagnostics.append(
            f"Purity {purity:.4f} outside theoretical interval [{min_theoretical_purity:.4f}, 1.0]"
        )

    # 5. Von Neumann entropy: S = - sum(eval * log2(eval))
    entropy_val: float | None = None
    if calculate_entropy:
        ent = 0.0
        for ev in evals:
            if ev > 1e-12:
                ent -= float(ev * math.log2(ev))
        entropy_val = max(0.0, ent)

    is_valid = (tr_residual <= TOLERANCE_TRACE) and is_herm and is_psd

    return StateValidation(
        is_valid=is_valid,
        trace=tr,
        trace_residual=tr_residual,
        hermiticity_residual=herm_residual,
        is_hermitian=is_herm,
        min_eigenvalue=min_eval,
        is_positive_semidefinite=is_psd,
        purity=purity,
        entropy=entropy_val,
        diagnostics=diagnostics,
    )


def compute_reduced_density_matrix(
    rho: np.ndarray,
    dimensions: list[int],
    keep_wire: int,
) -> np.ndarray:
    """Computes the reduced density matrix rho_keep by partial trace over all other subsystems.

    Supports arbitrary subsystem dimensions.
    """
    n = len(dimensions)
    if n == 1:
        return rho

    target_dim = dimensions[keep_wire]
    # Reshape (D, D) into tensor of shape (d_0, ..., d_{n-1}, d_0, ..., d_{n-1})
    tensor_shape = dimensions + dimensions
    t = rho.reshape(tensor_shape)

    # We need to trace out all indices k != keep_wire
    # Let row indices be 0 .. n-1, col indices be n .. 2n-1
    # Trace out means contracting index k with index n+k
    # We iteratively trace out subsystems starting from the last to keep indices stable
    wires_to_trace = [w for w in range(n) if w != keep_wire]

    current_tensor = t
    current_dims_rows = list(dimensions)
    current_dims_cols = list(dimensions)

    for w in sorted(wires_to_trace, reverse=True):
        # In current_tensor, row axis w and col axis len(current_dims_rows) + w
        row_axis = w
        col_axis = len(current_dims_rows) + w
        current_tensor = np.trace(current_tensor, axis1=row_axis, axis2=col_axis)
        current_dims_rows.pop(w)
        current_dims_cols.pop(w)

    return current_tensor.reshape((target_dim, target_dim))


def get_reduced_state_summary(
    rho: np.ndarray,
    dimensions: list[int],
    wire_idx: int,
) -> ReducedStateResult:
    """Calculates reduced state, purity, entropy and populations for a single qudit."""
    dim = dimensions[wire_idx]
    red_rho = compute_reduced_density_matrix(rho, dimensions, wire_idx)

    # Populations (diagonals)
    pops = [float(np.real(red_rho[i, i])) for i in range(dim)]

    # Eigenvalues for purity and entropy
    evals = np.linalg.eigvalsh(0.5 * (red_rho + red_rho.conj().T))
    purity = float(np.sum(evals ** 2))

    entropy_val = 0.0
    for ev in evals:
        if ev > 1e-12:
            entropy_val -= float(ev * math.log2(ev))

    return ReducedStateResult(
        wire_index=wire_idx,
        dimension=dim,
        density_matrix=matrix_to_complex_grid(red_rho),
        purity=purity,
        entropy=max(0.0, entropy_val),
        populations=pops,
    )
