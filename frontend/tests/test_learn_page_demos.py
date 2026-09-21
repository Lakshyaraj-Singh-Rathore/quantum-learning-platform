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
