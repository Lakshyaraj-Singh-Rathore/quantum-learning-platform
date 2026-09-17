"""Make the backend package importable without PYTHONPATH.

Docker sets ``PYTHONPATH=/backend``, but Streamlit Community Cloud runs
``streamlit run frontend/Home.py`` from the repository root with no way to set
environment variables before the process starts. The frontend needs
``app.quantum.ir`` for CircuitIR, so put the backend directory on sys.path
ourselves.

Importing this module is idempotent and safe in every environment: if the
backend is already importable it does nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_backend_on_path() -> None:
    try:
        import app.quantum.ir  # noqa: F401
        return
    except ImportError:
        pass

    # frontend/lib/bootstrap.py -> repo root -> backend/
    backend = Path(__file__).resolve().parents[2] / "backend"
    if backend.is_dir():
        candidate = str(backend)
        if candidate not in sys.path:
            sys.path.insert(0, candidate)


ensure_backend_on_path()

__all__ = ["ensure_backend_on_path"]
