"""Standardized result schema shared by every backend."""

from __future__ import annotations

import time
from typing import Any, Optional


class BackendError(RuntimeError):
    pass


class BackendUnavailable(BackendError):
    """Raised when a backend is not configured (e.g. missing qBraid keys)."""


def make_result(
    *,
    backend: str,
    counts: dict[str, int],
    shots: int,
    n_qubits: int,
    runtime: float,
    statevector: Optional[list[list[float]]] = None,
    warnings: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the common result JSON returned to the UI for all backends.

    ``counts`` keys use the Qiskit bit order: qubit 0 is the RIGHTMOST
    character of the bitstring. Every backend adapter converts into this
    convention so the histogram is comparable across engines.
    """
    total = sum(counts.values()) or 1
    probabilities = {k: v / total for k, v in counts.items()}
    return {
        "counts": dict(sorted(counts.items())),
        "probabilities": dict(sorted(probabilities.items())),
        "statevector": statevector,
        "metadata": {
            "backend": backend,
            "shots": shots,
            "n_qubits": n_qubits,
            "runtime_seconds": round(runtime, 4),
            "bit_order": "qiskit (qubit 0 = rightmost)",
            "warnings": warnings or [],
            **(metadata or {}),
        },
    }


class Timer:
    def __enter__(self) -> "Timer":
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.elapsed = time.perf_counter() - self.start

    @property
    def seconds(self) -> float:
        return getattr(self, "elapsed", time.perf_counter() - self.start)


def static_qubit_limit(backend: str = "") -> int:
    """Qubit ceiling for one backend.

    CPU simulators are bounded by system RAM; the GPU simulator is bounded by
    VRAM, which on a laptop card is both smaller and shared with the desktop.
    One global limit cannot describe both, so the ceiling is per backend.
    """
    from app.config import get_settings

    settings = get_settings()
    if backend.startswith("cudaq"):
        return settings.max_gpu_qubits
    return settings.max_static_qubits


def guard_static_size(ir: Any, backend: str = "") -> None:
    """Refuse circuits whose statevector will not fit in memory.

    A statevector costs 16 bytes * 2**n. At 24 qubits that is 268 MB for the
    amplitudes alone and the worker gets OOM-killed, which takes down the whole
    API rather than failing one job. Fail fast with a message that explains the
    limit instead.
    """
    limit = static_qubit_limit(backend)
    if ir.n_qubits > limit:
        where = "GPU memory" if backend.startswith("cudaq") else "memory"
        raise BackendError(
            f"This backend is limited to {limit} qubits (got {ir.n_qubits}). "
            f"A statevector for {ir.n_qubits} qubits needs about "
            f"{2 ** ir.n_qubits * 16 / 1e9:.1f} GB of {where}."
        )


def statevector_to_json(sv: Any, fix_global_phase: bool = True) -> list[list[float]]:
    """Serialize a complex statevector as [[re, im], ...].

    Transpiling to the portable basis can introduce an arbitrary global phase,
    which would make the phase-disk visualization differ between backends for
    physically identical states. By default the global phase is fixed so the
    first significant amplitude is real and positive.
    """
    import numpy as np

    data = np.asarray(sv, dtype=complex).ravel()
    if fix_global_phase and data.size:
        significant = np.flatnonzero(np.abs(data) > 1e-9)
        if significant.size:
            pivot = data[significant[0]]
            data = data * np.exp(-1j * np.angle(pivot))
    return [[float(z.real), float(z.imag)] for z in data]


__all__ = [
    "make_result",
    "guard_static_size",
    "static_qubit_limit",
    "statevector_to_json",
    "Timer",
    "BackendError",
    "BackendUnavailable",
]
