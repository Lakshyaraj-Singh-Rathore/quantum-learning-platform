"""Streamlit custom component wrapper for the React drag-and-drop composer.

Falls back gracefully when the React bundle has not been built: the caller can
check ``is_available()`` and use the pure-Python grid composer instead.
"""

from __future__ import annotations

import mimetypes
import re
import os
from pathlib import Path
from typing import Any, Optional

import streamlit.components.v1 as components

# Streamlit serves this component's files through Python's `mimetypes`. On a
# slim base image /etc/mime.types is absent, so .js resolves to
# "application/javascript" (or octet-stream) instead of "text/javascript".
# Browsers refuse to execute a strict-MIME module script served that way, and
# the component renders as a blank white iframe with nothing in the console.
# Pin the mappings here so the bundle loads on any base image.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/json", ".map")

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


def build_is_consistent() -> tuple[bool, str]:
    """Check index.html only references asset files that actually exist.

    Vite fingerprints its output (index-DHgvFsrF.js). Because build/ is
    gitignored, a `git pull` can leave an index.html pointing at a hash that is
    no longer on disk -- every asset 404s and the iframe paints blank white
    with no error. Detect that instead of letting it look like a code bug.
    """
    index = _BUILD_DIR / "index.html"
    if not index.exists():
        return False, "The composer bundle is not built."

    html = index.read_text(encoding="utf-8")
    missing = [
        ref
        for ref in re.findall(r'(?:src|href)="\./([^"]+)"', html)
        if not (_BUILD_DIR / ref).exists()
    ]
    if missing:
        return False, (
            "The composer bundle is stale: index.html references "
            + ", ".join(missing)
            + " which no longer exist. Rebuild with: "
            "cd frontend/circuit_composer/frontend && npm ci && npm run build"
        )
    return True, ""


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


__all__ = [
    "circuit_composer",
    "is_available",
    "build_instructions",
    "build_is_consistent",
]
