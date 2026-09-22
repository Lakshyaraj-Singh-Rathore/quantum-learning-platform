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

import json
import os
import sys
import urllib.request
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


# --- Stale results must not read as a pass -----------------------------------

def _graded(slug: str, circuit: dict) -> dict:
    """Submit a circuit and wait for its grade."""
    import time

    base = os.getenv("API_BASE_URL", "http://localhost:8000")

    def call(method, path, payload=None):
        request = urllib.request.Request(
            base + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + _TOKEN},
            method=method,
        )
        return json.load(urllib.request.urlopen(request, timeout=20))

    submitted = call("POST", f"/challenges/{slug}/submit", {"circuit_ir": circuit})
    for _ in range(40):
        outcome = call("GET", f"/attempts/{submitted['attempt_id']}")
        if outcome.get("status") == "graded":
            return outcome
        time.sleep(0.4)
    pytest.fail("attempt never finished grading")


CORRECT_BELL = {
    "name": "g", "n_qubits": 2, "n_clbits": 2, "ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2}]}

WRONG_BELL = {**CORRECT_BELL, "ops": [
    {"kind": "gate", "gate": "x", "qubits": [0], "layer": 0},
    *CORRECT_BELL["ops"][1:]]}


def _stamp(circuit: dict) -> str:
    from app.quantum.inspect import _strip_ids
    from app.quantum.ir import CircuitIR

    return json.dumps(_strip_ids(CircuitIR.from_dict(circuit).to_dict()), sort_keys=True)


def _with_attempt(circuit: dict, outcome: dict, stamp: str) -> AppTest:
    at = AppTest.from_file(PAGE, default_timeout=120)
    at.session_state["token"] = _TOKEN
    at.session_state["user"] = _USER
    at.session_state["game_level"] = "game-bug-bell"
    at.session_state["game_attempt"] = outcome
    at.session_state["game_attempt_level"] = "game-bug-bell"
    at.session_state["game_attempt_circuit"] = stamp
    at.session_state["circuit"] = circuit
    at.run()
    return at


def test_the_wrong_bell_circuit_does_not_pass():
    """Guard the grader itself: X + CNOT gives |11>, not a Bell pair."""
    outcome = _graded("game-bug-bell", WRONG_BELL)
    assert outcome["passed"] is False
    assert outcome["score"] == 0.0


def test_a_win_stays_visible_while_the_circuit_is_unchanged():
    win = _graded("game-bug-bell", CORRECT_BELL)
    assert win["passed"] is True
    at = _with_attempt(CORRECT_BELL, win, _stamp(CORRECT_BELL))
    assert any("Level complete" in (s.value or "") for s in at.success)


def test_editing_the_circuit_retracts_the_win():
    """The exact report: a success banner beside a wrong circuit."""
    win = _graded("game-bug-bell", CORRECT_BELL)
    at = _with_attempt(WRONG_BELL, win, _stamp(CORRECT_BELL))
    assert not any("Level complete" in (s.value or "") for s in at.success)
    assert any("changed the circuit" in (i.value or "") for i in at.info)
