"""Feature-flag discovery for the browser.

This router is mounted **unconditionally**. That is the entire point: an
endpoint that only exists when a feature is enabled cannot be the thing the UI
asks in order to decide whether that feature is enabled. A 404 is
indistinguishable from a typo'd path, a stripped ``/api`` prefix, a proxy
misconfiguration or a backend that failed to boot, so a nav driven by 404
would silently hide a feature that is actually on.

Here, ``{"qml_enabled": false}`` means the server said no. That is a different
fact from "the request did not arrive", and the client can tell them apart.

Unauthenticated, following ``GET /backends`` (``api/jobs.py:45``), which is
already an always-on capability-discovery endpoint consumed by
``src/api/backends.ts``. A single boolean is less sensitive than the backend
catalogue that endpoint already publishes.

Returns a **map** of flags rather than a QML-specific payload, so the next
feature flag does not need another endpoint or another client round trip.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["features"])


@router.get("/features")
def features() -> dict[str, bool]:
    """Which optional features this deployment has switched on."""
    settings = get_settings()
    return {"qml_enabled": settings.qml_enabled}
