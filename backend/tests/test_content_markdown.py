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


def test_chunking_never_splits_inside_a_code_block():
    """A Python comment looks like a level-1 heading, so a naive split on
    `#{1,3}\\s` cuts lessons in the middle of a code sample. Lessons are full of
    commented code, so the chunker must be fence-aware."""
    from app.ai.rag import chunk_markdown

    lesson = (
        "# Title\n\n"
        "Prose before the example.\n\n"
        "## Example\n\n"
        "```python\n"
        "# this comment looks like a heading\n"
        "qc.h(0)\n"
        "# and so does this one\n"
        "qc.measure(0, 0)\n"
        "```\n\n"
        "## After\n\n"
        "Prose after the example.\n"
    )
    chunks = chunk_markdown(lesson)
    # Each chunk must have balanced fences: a split inside a block leaves one.
    for i, chunk in enumerate(chunks):
        assert chunk.count("```") % 2 == 0, f"chunk {i} has an unbalanced fence"
    # The code must survive intact in a single chunk.
    joined = "\n".join(chunks)
    assert "# this comment looks like a heading" in joined
    assert "qc.measure(0, 0)" in joined
    assert any("qc.h(0)" in c and "qc.measure(0, 0)" in c for c in chunks), (
        "the code sample was split across chunks"
    )
