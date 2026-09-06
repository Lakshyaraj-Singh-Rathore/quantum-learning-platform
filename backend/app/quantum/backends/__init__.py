"""Simulation backend adapters, all returning the standardized result schema."""

from app.quantum.backends.base import BackendError, BackendUnavailable, make_result

__all__ = ["make_result", "BackendError", "BackendUnavailable"]
