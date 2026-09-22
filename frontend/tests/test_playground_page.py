"""The Playground page must render, including at slider extremes.

Written the way the Games page should have been tested first time: with a real
login, because a fake token stops the page at ``auth.require_login()`` before
any of the interesting code runs, and by driving widgets to their boundaries,
because that is where divide-by-zero and empty-state bugs live.
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

PAGE = str(ROOT / "pages" / "7_Playground.py")


def _login() -> tuple[str, dict]:
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

pytestmark = pytest.mark.skipif(
    not _TOKEN, reason="needs the API running (integration test)"
)


def _run(**state) -> AppTest:
    at = AppTest.from_file(PAGE, default_timeout=120)
    at.session_state["token"] = _TOKEN
    at.session_state["user"] = _USER
    for key, value in state.items():
        at.session_state[key] = value
    at.run()
    return at


def test_page_renders():
    at = _run()
    assert not at.exception, [str(e) for e in at.exception]


def test_page_has_all_seven_lessons():
    assert len(_run().tabs) == 7


def test_page_is_interactive():
    """The point of the page: it must actually have controls."""
    at = _run()
    assert len(at.slider) + len(at.select_slider) >= 8
    assert at.radio
    assert at.toggle


@pytest.mark.parametrize(
    "state",
    [
        {"pg_intro_theta": 0.0},
        {"pg_intro_theta": 180.0},
        {"pg_build_mode": "Amplitudes", "pg_a": 0.0, "pg_b": 0.0},
        {"pg_build_mode": "Amplitudes", "pg_a": -1.0, "pg_b": 1.0},
        {"pg_build_mode": "Bloch angles", "pg_theta": 0.0, "pg_phi": 0.0},
        {"pg_build_mode": "Bloch angles", "pg_theta": 180.0, "pg_phi": 360.0},
        {"pg_gates": ["H", "T", "Z", "S", "X", "Y"]},
        {"pg_m_theta": 0.0, "pg_shots": 1},
        {"pg_m_theta": 180.0, "pg_shots": 4096},
        {"pg_ia": 0.0, "pg_ib": 0.0},
        {"pg_ia": 1.0, "pg_ib": 1.0},
        {"pg_pm_h": True},
        {"pg_n": 1},
        {"pg_n": 30},
        {"pg_bits_n": 5, "pg_bits_v": 31},
        {"pg_bits_n": 2, "pg_bits_v": 0},
    ],
)
def test_extremes_do_not_crash(state):
    at = _run(**state)
    assert not at.exception, f"{state} -> {[str(e) for e in at.exception]}"


def test_no_column_nesting_violations():
    """The bug that broke every Games level; cheap to guard against again."""
    at = _run(pg_gates=["H"])
    nesting = [e for e in at.exception if "one level of nesting" in str(e)]
    assert not nesting


# --- Both outcomes get an observed figure ------------------------------------

def test_measurement_tab_shows_observed_for_both_outcomes():
    """Expected P(1) with no Observed P(1) left a number compared to nothing."""
    at = _run()
    labels = [m.label for m in at.metric]
    for wanted in ("Expected P(0)", "Observed P(0)", "Expected P(1)", "Observed P(1)"):
        assert wanted in labels, f"{wanted} missing from the measurement tab"


# --- The build tab uses the real composer ------------------------------------
#
# These need the compiled composer bundle. Without it the tab deliberately
# falls back to a gate dropdown, which is correct behaviour, not a failure.
_BUNDLE = (ROOT / "circuit_composer" / "frontend" / "build" / "index.html").is_file()
needs_bundle = pytest.mark.skipif(
    not _BUNDLE, reason="composer bundle not built (npm run build)"
)


@needs_bundle
def test_build_tab_has_no_gate_dropdown():
    at = _run()
    assert not any(
        "apply gates" in (m.label or "").lower() for m in at.multiselect
    ), "the gate dropdown should be the drag-and-drop grid"


@needs_bundle
def test_build_tab_reports_gates_it_cannot_apply():
    """This demo is single-qubit; a CNOT must be explained, not ignored."""
    at = _run(circuit={
        "name": "c", "n_qubits": 2, "n_clbits": 2, "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1}]})
    assert not at.exception
    assert any("single qubit" in (i.value or "") for i in at.info)


@needs_bundle
def test_build_tab_applies_gates_from_the_grid():
    """A circuit on the grid must actually change the reported state."""
    from lib import playground as pg

    plain = _run(circuit={"name": "c", "n_qubits": 1, "n_clbits": 1, "ops": []})
    with_h = _run(circuit={"name": "c", "n_qubits": 1, "n_clbits": 1, "ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0}]})
    before = {m.label: m.value for m in plain.metric}.get("P(0)")
    after = {m.label: m.value for m in with_h.metric}.get("P(0)")
    assert before != after, "placing H on the grid did not change the state"
    # And the value is the real physics, not an arbitrary change.
    expected = pg.probabilities(
        pg.apply_gates(pg.state_from_amplitudes(0.8, 0.6), ["H"]))[0]
    assert after == f"{expected:.1%}"
