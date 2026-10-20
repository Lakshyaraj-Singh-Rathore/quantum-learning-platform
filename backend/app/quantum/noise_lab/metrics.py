"""Analytical and statistical quantum metrics calculation for Noise Lab."""

from __future__ import annotations

import math
from typing import Any
import numpy as np

from app.quantum.noise_lab.models import NoiseMetrics


def total_variation_distance(p: dict[str, float], q: dict[str, float]) -> float:
    """Total variation distance between two probability mass distributions."""
    all_keys = set(p.keys()) | set(q.keys())
    return float(0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in all_keys))


def calculate_metrics(
    ideal_statevector: np.ndarray | None,
    noisy_density_matrix: np.ndarray | None,
    ideal_probs: dict[str, float],
    noisy_probs: dict[str, float],
) -> NoiseMetrics:
    """Compute quantum state fidelity, purity, trace distance, and entropy."""
    tvd = total_variation_distance(ideal_probs, noisy_probs)

    fidelity: float | None = None
    purity: float | None = None
    trace_dist: float | None = None
    entropy: float | None = None
    is_exact = False

    if noisy_density_matrix is not None:
        rho = np.asarray(noisy_density_matrix, dtype=complex)
        # Ensure trace normalization
        tr = np.trace(rho)
        if abs(tr) > 1e-12:
            rho = rho / tr
        
        # 1. Purity Tr(rho^2)
        purity_val = float(np.real(np.trace(rho @ rho)))
        purity = max(0.0, min(1.0, purity_val))

        # 2. Von Neumann Entropy S(rho) = -Tr(rho log2 rho)
        eigenvalues = np.real(np.linalg.eigvalsh(rho))
        pos_eigs = eigenvalues[eigenvalues > 1e-12]
        if len(pos_eigs) > 0:
            entropy_val = float(-np.sum(pos_eigs * np.log2(pos_eigs)))
            entropy = max(0.0, entropy_val)
        else:
            entropy = 0.0

        # 3. State Fidelity with ideal statevector |psi>
        if ideal_statevector is not None:
            psi = np.asarray(ideal_statevector, dtype=complex).ravel()
            psi_norm = np.linalg.norm(psi)
            if psi_norm > 1e-12:
                psi = psi / psi_norm
                # F = <psi|rho|psi>
                fid = float(np.real(psi.conj().T @ (rho @ psi)))
                fidelity = max(0.0, min(1.0, fid))
                is_exact = True

                # 4. Trace Distance D(rho, |psi><psi|)
                # Delta = rho - |psi><psi|
                rho_ideal = np.outer(psi, psi.conj())
                delta = rho - rho_ideal
                eig_delta = np.linalg.eigvalsh(delta)
                trace_dist = float(0.5 * np.sum(np.abs(eig_delta)))

    elif ideal_statevector is not None and ideal_probs == noisy_probs:
        # Noiseless pure state baseline
        fidelity = 1.0
        purity = 1.0
        trace_dist = 0.0
        entropy = 0.0
        is_exact = True
    elif fidelity is None and ideal_probs and noisy_probs:
        # Fallback when density matrix is unavailable (e.g. > 8 qubits):
        # Compute Classical Bhattacharyya / Hellinger fidelity from sampled distributions
        all_keys = set(ideal_probs.keys()) | set(noisy_probs.keys())
        bhattacharyya = sum(math.sqrt(ideal_probs.get(k, 0.0) * noisy_probs.get(k, 0.0)) for k in all_keys)
        fidelity = max(0.0, min(1.0, float(bhattacharyya ** 2)))
        trace_dist = tvd
        is_exact = False

    return NoiseMetrics(
        fidelity=round(fidelity, 6) if fidelity is not None else None,
        purity=round(purity, 6) if purity is not None else None,
        trace_distance=round(trace_dist, 6) if trace_dist is not None else None,
        total_variation_distance=round(tvd, 6),
        entropy_bits=round(entropy, 4) if entropy is not None else None,
        is_exact_density_matrix=is_exact,
    )
