"""The always-mounted feature-flag endpoint.

The point of this endpoint is that it answers in BOTH flag states, so the
browser can distinguish "the server says this feature is off" from "the
request did not arrive". A 404 cannot make that distinction, which is why
flag visibility must not live behind the gated router.
"""

from __future__ import annotations

import importlib
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import get_settings


def _client_with_flag(enabled: bool) -> TestClient:
    os.environ["QML_ENABLED"] = "true" if enabled else "false"
    get_settings.cache_clear()
    import app.api.router as router_module

    importlib.reload(router_module)
    app = FastAPI()
    app.include_router(router_module.api_router)
    return TestClient(app)


@pytest.fixture
def restore_flag():
    previous = os.environ.get("QML_ENABLED")
    yield
    if previous is None:
        os.environ.pop("QML_ENABLED", None)
    else:
        os.environ["QML_ENABLED"] = previous
    get_settings.cache_clear()
    import app.api.router as router_module

    importlib.reload(router_module)


def test_features_answers_200_when_the_flag_is_off(client):
    """The whole contract: off must be an answer, not an error."""
    response = client.get("/features")
    assert response.status_code == 200
    assert response.json() == {"qml_enabled": False}


def test_features_needs_no_authentication(client):
    """Same posture as GET /backends (api/jobs.py:45)."""
    assert "authorization" not in {k.lower() for k in client.headers}
    assert client.get("/features").status_code == 200


def test_features_is_a_map_not_a_boolean(client):
    """Room for the next flag without another endpoint or round trip."""
    body = client.get("/features").json()
    assert isinstance(body, dict)
    assert all(isinstance(v, bool) for v in body.values())


def test_features_tracks_the_flag_in_both_directions(restore_flag):
    off = _client_with_flag(False)
    assert off.get("/features").json() == {"qml_enabled": False}
    assert off.get("/qml/describe").status_code == 404

    on = _client_with_flag(True)
    assert on.get("/features").json() == {"qml_enabled": True}
    assert on.get("/qml/describe").status_code in (200, 401, 403)


def test_the_features_route_exists_in_both_flag_states(restore_flag):
    """It must never be the thing that disappears."""
    for enabled in (False, True):
        paths = {getattr(r, "path", "") for r in _client_with_flag(enabled).app.routes}
        assert "/features" in paths, f"/features vanished with qml_enabled={enabled}"
