"""Every lesson must render, with its demos, without raising.

Written the way the Games page should have been tested first time:

* with a REAL login, because a fake token stops the page before the demos run;
* against every lesson, because a demo is only reached on the lesson it is
  mapped to;
* checking specifically for column-nesting errors, the failure that broke every
  Games level.
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

from lib import lesson_demos  # noqa: E402

PAGE = str(ROOT / "pages" / "1_Learn.py")
BASE = os.getenv("API_BASE_URL", "http://localhost:8000")


def _login() -> tuple[str, dict]:
    request = urllib.request.Request(
        BASE + "/auth/login",
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
    _LESSONS = json.load(urllib.request.urlopen(BASE + "/lessons", timeout=10))
except Exception:  # pragma: no cover - API not running
    _TOKEN, _USER, _LESSONS = "", {}, []

pytestmark = pytest.mark.skipif(
    not _TOKEN, reason="needs the API running (integration test)"
)


def _open_lesson(index: int) -> AppTest:
    at = AppTest.from_file(PAGE, default_timeout=120)
    at.session_state["token"] = _TOKEN
    at.session_state["user"] = _USER
    at.run()
    at.sidebar.radio[0].set_value("All").run()   # show every track
    at.sidebar.radio[1].set_value(index).run()   # pick the lesson
    return at


@pytest.mark.parametrize("index", range(len(_LESSONS)))
def test_lesson_renders_with_its_demos(index):
    at = _open_lesson(index)
    assert not at.exception, [str(e) for e in at.exception]


@pytest.mark.parametrize("index", range(len(_LESSONS)))
def test_no_column_nesting_violations(index):
    """The exact failure that broke every Games level."""
    at = _open_lesson(index)
    nesting = [e for e in at.exception if "one level of nesting" in str(e)]
    assert not nesting, str(nesting)


def test_lessons_with_demos_show_the_section():
    indexes = [
        i for i, lesson in enumerate(_LESSONS)
        if lesson_demos.demos_for(lesson["slug"])
    ]
    assert indexes, "no lesson has demos registered"
    for index in indexes[:4]:  # a sample keeps the suite quick
        at = _open_lesson(index)
        headings = [s.value for s in at.subheader]
        assert any("Try it yourself" in (h or "") for h in headings), (
            f"{_LESSONS[index]['slug']} has demos but no demo section"
        )


def test_lessons_without_demos_are_unchanged():
    indexes = [
        i for i, lesson in enumerate(_LESSONS)
        if not lesson_demos.demos_for(lesson["slug"])
    ]
    if not indexes:
        pytest.skip("every lesson has demos")
    at = _open_lesson(indexes[0])
    headings = [s.value for s in at.subheader]
    assert not any("Try it yourself" in (h or "") for h in headings)
    assert not at.exception


# --- The measure / reset cycle ----------------------------------------------
#
# Driven through the real page, because the interesting behaviour is the
# interaction: the buttons must swap enabled state, the slider must lock while
# the qubit is collapsed, and a reset must restore the superposition.

def _qubits_lesson() -> int:
    for index, lesson in enumerate(_LESSONS):
        if lesson["slug"] == "01_qubits":
            return index
    pytest.skip("01_qubits lesson not present")


def _button(at, fragment):
    matches = [b for b in at.button if fragment.lower() in (b.label or "").lower()]
    assert matches, f"no button matching {fragment!r}"
    return matches[0]


def _state_key(at, suffix):
    keys = [k for k in at.session_state.filtered_state if k.endswith(suffix)]
    assert keys, f"no session key ending {suffix!r}"
    return keys[0]


def test_measure_and_reset_buttons_exist():
    at = _open_lesson(_qubits_lesson())
    assert not at.exception
    assert _button(at, "Measure the qubit")
    assert _button(at, "Reset qubit")


def test_reset_starts_disabled_and_measure_starts_enabled():
    """Nothing to reset until the qubit has actually been measured."""
    at = _open_lesson(_qubits_lesson())
    assert _button(at, "Measure the qubit").disabled is False
    assert _button(at, "Reset qubit").disabled is True


def test_measuring_collapses_the_qubit():
    at = _open_lesson(_qubits_lesson())
    _button(at, "Measure the qubit").click().run()
    assert not at.exception, [str(e) for e in at.exception]
    collapsed = at.session_state[_state_key(at, "_collapsed")]
    assert collapsed in (0, 1)
    # The buttons swap over: you cannot measure a collapsed qubit again.
    assert _button(at, "Measure the qubit").disabled is True
    assert _button(at, "Reset qubit").disabled is False


def test_collapse_locks_the_theta_slider():
    """A collapsed qubit has a definite value; sliding theta would be a lie."""
    at = _open_lesson(_qubits_lesson())
    before = [s for s in at.slider if "θ" in (s.label or "")]
    assert before and before[0].disabled is False
    _button(at, "Measure the qubit").click().run()
    after = [s for s in at.slider if "θ" in (s.label or "")]
    assert after and after[0].disabled is True


def test_reset_restores_the_superposition():
    at = _open_lesson(_qubits_lesson())
    _button(at, "Measure the qubit").click().run()
    _button(at, "Reset qubit").click().run()
    assert not at.exception
    assert at.session_state[_state_key(at, "_collapsed")] is None
    assert _button(at, "Measure the qubit").disabled is False


def test_history_survives_a_reset():
    """The record of outcomes is what shows the distribution emerging."""
    at = _open_lesson(_qubits_lesson())
    _button(at, "Measure the qubit").click().run()
    _button(at, "Reset qubit").click().run()
    assert len(at.session_state[_state_key(at, "_history")]) == 1


def test_repeated_cycles_produce_both_outcomes():
    """At theta = 90 the qubit is a genuine coin flip, not a fixed answer."""
    at = _open_lesson(_qubits_lesson())
    seen = set()
    for _ in range(20):
        _button(at, "Measure the qubit").click().run()
        # The key only exists once something has been measured.
        seen.add(at.session_state[_state_key(at, "_collapsed")])
        _button(at, "Reset qubit").click().run()
        if seen == {0, 1}:
            break
    assert seen == {0, 1}, f"only ever saw {seen} in 20 cycles"
