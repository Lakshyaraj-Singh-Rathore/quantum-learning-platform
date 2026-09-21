"""Streamlit wrapper for the continuous Bloch sphere component.

Mirrors ``circuit_composer`` exactly, including the MIME pinning and the stale
bundle check, because both were fixed the hard way there.
"""

from __future__ import annotations

import mimetypes
import os
import re
from pathlib import Path
from typing import Any, Optional

import streamlit.components.v1 as components

# Streamlit serves component files through Python's mimetypes. On a slim base
# image /etc/mime.types is absent, so .js resolves to "application/javascript"
# and strict browsers refuse to execute the ES module -- the component then
# renders as a blank white iframe with nothing in the console.
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")

_BUILD_DIR = Path(__file__).parent / "frontend" / "build"
_DEV_URL = os.getenv("LIVE_BLOCH_DEV_URL", "")

_component: Any = None

if _DEV_URL:
    _component = components.declare_component("live_bloch", url=_DEV_URL)
elif (_BUILD_DIR / "index.html").exists():
    _component = components.declare_component("live_bloch", path=str(_BUILD_DIR))


def is_available() -> bool:
    return _component is not None


def build_is_consistent() -> tuple[bool, str]:
    """Check index.html only references assets that exist.

    build/ is gitignored, so a pull can leave an index.html pointing at a Vite
    hash that is no longer on disk. Every asset then 404s and the iframe paints
    blank.
    """
    index = _BUILD_DIR / "index.html"
    if not index.exists():
        return False, "The live Bloch bundle is not built."
    html = index.read_text(encoding="utf-8")
    missing = [
        ref
        for ref in re.findall(r'(?:src|href)="\./([^"]+)"', html)
        if not (_BUILD_DIR / ref).exists()
    ]
    if missing:
        return False, (
            "The live Bloch bundle is stale: index.html references "
            + ", ".join(missing)
            + ". Rebuild with: cd frontend/live_bloch/frontend && npm ci && npm run build"
        )
    return True, ""


def live_bloch(
    theta: float = 90.0,
    phi: float = 0.0,
    gates: Optional[list[str]] = None,
    key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Render the sphere and return the state the learner settled on."""
    if _component is None:
        return None
    default = {"theta": theta, "phi": phi, "gates": gates or []}
    return _component(
        theta=theta, phi=phi, gates=gates or [], key=key, default=default
    )


__all__ = ["live_bloch", "is_available", "build_is_consistent"]
