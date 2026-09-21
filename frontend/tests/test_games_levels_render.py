"""Every game level must render without raising.

This is the test that should have existed before shipping. The original Games
page crashed on every level with

    Columns can only be placed inside other columns up to one level of nesting

because the editor was rendered inside ``st.columns``. It escaped review
because the crash only fires with a NON-EMPTY circuit: ``composer._grid()``
returns early when there are no operations, so a level opened on a blank grid
never reaches the offending ``st.columns`` call.

Every level is therefore exercised twice: once empty, once with a gate placed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pytest.importorskip("streamlit.testing.v1")

from streamlit.testing.v1 import AppTest  # noqa: E402

PAGE = str(ROOT / "pages" / "6_Games.py")

# Slugs come from app.games, so the list cannot drift away from the seeds.
try:
    from app.games import GAME_LEVELS

    SLUGS = [level["slug"] for level in GAME_LEVELS]
except Exception:  # pragma: no cover - backend not importable
    SLUGS = []

def _login() -> tuple[str, dict]:
    """A real token; with a fake one the page stops at the API call and the
    editor -- the part that used to crash -- is never reached."""
    import json
    import os
    import urllib.request

    base = os.getenv("API_BASE_URL", "http://localhost:8000")
    request = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps(
            {"email": "instructor@local.dev", "password": "instructor123"}
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    payload = json.load(urllib.request.urlopen(request, timeout=10))
    return payload["access_token"], {
        "id": payload["user_id"],
        "email": payload["email"],
        "role": payload["role"],
    }


try:
    _TOKEN, _USER = _login()
except Exception:  # pragma: no cover - API not running
    _TOKEN, _USER = "", {}


NON_EMPTY = {
    "name": "probe",
    "n_qubits": 3,
    "n_clbits": 3,
    "ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [2], "controls": [0, 1], "layer": 1},
    ],
}


def _run(slug: str | None = None, circuit: dict | None = None) -> AppTest:
    at = AppTest.from_file(PAGE, default_timeout=120)
    at.session_state["token"] = _TOKEN
    at.session_state["user"] = _USER
    if slug:
        at.session_state["game_level"] = slug
    if circuit:
        at.session_state["circuit"] = circuit
    at.run()
    return at


def _nesting_errors(at: AppTest) -> list[str]:
    return [str(e) for e in at.exception if "one level of nesting" in str(e)]


pytestmark = pytest.mark.skipif(
    not _TOKEN, reason="needs the API running (these are integration tests)"
)


@pytest.mark.skipif(not SLUGS, reason="game levels unavailable")
@pytest.mark.parametrize("slug", SLUGS)
def test_level_renders_with_a_non_empty_circuit(slug):
    """The exact condition that broke in the browser."""
    at = _run(slug, NON_EMPTY)
    assert not _nesting_errors(at), _nesting_errors(at)


@pytest.mark.skipif(not SLUGS, reason="game levels unavailable")
@pytest.mark.parametrize("slug", SLUGS)
def test_level_renders_with_an_empty_circuit(slug):
    at = _run(slug, {"name": "e", "n_qubits": 2, "n_clbits": 2, "ops": []})
    assert not _nesting_errors(at), _nesting_errors(at)


def test_catalogue_renders():
    at = _run()
    assert not _nesting_errors(at), _nesting_errors(at)
