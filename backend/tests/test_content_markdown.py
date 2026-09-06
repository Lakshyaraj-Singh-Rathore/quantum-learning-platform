"""The lesson corpus must render correctly in Streamlit.

Regression: display-math blocks written across two lines, or without blank
lines around them, broke Streamlit's markdown parser. The rest of the lesson
then rendered as raw red LaTeX instead of formatted prose.
"""

from __future__ import annotations

import pathlib

import pytest

CONTENT = pathlib.Path(__file__).resolve().parents[2] / "content"
LESSONS = sorted(CONTENT.glob("*.md"))


def test_corpus_is_present():
    assert LESSONS, f"no lessons found in {CONTENT}"


@pytest.mark.parametrize("path", LESSONS, ids=lambda p: p.name)
def test_display_math_is_single_line_and_isolated(path: pathlib.Path):
    lines = path.read_text(encoding="utf-8").split("\n")
    for number, line in enumerate(lines, start=1):
        count = line.count("$$")
        assert count != 1, (
            f"{path.name}:{number} opens a $$ block that does not close on the "
            "same line; Streamlit renders the remainder as raw LaTeX"
        )
        if count >= 2:
            before = lines[number - 2].strip() if number >= 2 else ""
            after = lines[number].strip() if number < len(lines) else ""
            assert before == "", f"{path.name}:{number} needs a blank line before $$"
            assert after == "", f"{path.name}:{number} needs a blank line after $$"


@pytest.mark.parametrize("path", LESSONS, ids=lambda p: p.name)
def test_inline_math_delimiters_are_balanced(path: pathlib.Path):
    for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        if "$$" in line:
            continue
        assert line.count("$") % 2 == 0, (
            f"{path.name}:{number} has an unbalanced inline $ delimiter"
        )
