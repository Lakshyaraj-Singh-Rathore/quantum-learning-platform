"""Streamlit custom component wrapper for the React drag-and-drop composer.

Falls back gracefully when the React bundle has not been built: the caller can
check ``is_available()`` and use the pure-Python grid composer instead.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import streamlit.components.v1 as components

_BUILD_DIR = Path(__file__).parent / "frontend" / "build"
_DEV_URL = os.getenv("COMPOSER_DEV_URL", "")

_component: Any = None

if _DEV_URL:
    _component = components.declare_component("circuit_composer", url=_DEV_URL)
elif (_BUILD_DIR / "index.html").exists():
    _component = components.declare_component("circuit_composer", path=str(_BUILD_DIR))


def is_available() -> bool:
    """True when the React bundle (or a dev server) is reachable."""
    return _component is not None


def build_instructions() -> str:
    return (
        "The React drag-and-drop composer is not built yet. Run:\n\n"
        "```bash\ncd frontend/circuit_composer/frontend\nnpm install && npm run build\n```\n\n"
        "Until then the Python grid composer below provides the same functionality."
    )


def circuit_composer(
    value: dict[str, Any],
    n_qubits: int = 2,
    key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Render the drag-and-drop composer and return the edited circuit IR."""
    if _component is None:
        return None
    return _component(value=value, nQubits=n_qubits, key=key, default=value)


__all__ = ["circuit_composer", "is_available", "build_instructions"]
