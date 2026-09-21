"""Interactive demos are attached to the lessons that teach their concept.

The demos themselves are pure functions over :mod:`lib.playground`, whose maths
is covered by ``test_playground.py``. What matters here is the wiring: every
registered demo exists, every lesson maps to demos that make sense for it, and
rendering one inside the Learn page does not break the page.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import lesson_demos  # noqa: E402

LEARN_PAGE = ROOT / "pages" / "1_Learn.py"
CONTENT = ROOT.parent / "content"


# ------------------------------------------------------------------ registry
def test_every_mapped_demo_exists_in_the_registry():
    """A typo in the mapping would silently drop a demo."""
    for slug, keys in lesson_demos.DEMOS_FOR_LESSON.items():
        for key in keys:
            assert key in lesson_demos.DEMO_REGISTRY, f"{slug} -> unknown demo {key!r}"


def test_registry_entries_are_callable():
    for key, (title, blurb, render) in lesson_demos.DEMO_REGISTRY.items():
        assert title and blurb, key
        assert callable(render), key


def test_every_registered_demo_is_used_somewhere():
    """An unused demo is dead code; it should be mapped or removed."""
    used = {k for keys in lesson_demos.DEMOS_FOR_LESSON.values() for k in keys}
    assert used == set(lesson_demos.DEMO_REGISTRY)


@pytest.mark.skipif(not CONTENT.is_dir(), reason="content folder not present")
def test_every_mapped_lesson_actually_exists():
    """Slugs are filename stems; a rename would orphan the mapping."""
    slugs = {path.stem for path in CONTENT.glob("*.md")}
    for slug in lesson_demos.DEMOS_FOR_LESSON:
        assert slug in slugs, f"{slug} has demos but no lesson file"


def test_no_demos_returns_an_empty_list():
    assert lesson_demos.demos_for("does_not_exist") == []


# --------------------------------------------------------- sensible pairings
@pytest.mark.parametrize(
    "slug,expected",
    [
        ("01_qubits", "bloch"),
        ("13_classical_bit_vs_qubit", "bit_vs_qubit"),
        ("02_gates", "gates"),
        ("04_measurement", "measure"),
        ("06_grover", "interference"),
        ("11_bell_states", "plus_minus"),
    ],
)
def test_key_lessons_get_their_defining_demo(slug, expected):
    assert expected in lesson_demos.demos_for(slug)


def test_interference_is_attached_to_both_algorithm_lessons():
    """Deutsch-Jozsa and Grover both turn on interference."""
    for slug in ("05_deutsch_jozsa", "06_grover"):
        assert "interference" in lesson_demos.demos_for(slug)


def test_bit_ordering_is_taught_where_bitstrings_are_read():
    assert "bit_order" in lesson_demos.demos_for("04_measurement")


# ------------------------------------------------------------- page wiring
def test_learn_page_renders_demos():
    src = LEARN_PAGE.read_text()
    assert "lesson_demos" in src
    assert 'render_for_lesson(chosen["slug"])' in src


def test_demos_render_between_the_lesson_and_the_tutor():
    """Try the idea while it is fresh, before asking questions about it."""
    src = LEARN_PAGE.read_text()
    assert src.index("render_for_lesson") > src.index('st.markdown(detail["content"])')
    assert src.index("render_for_lesson") < src.index("Ask the AI tutor")


def test_demos_never_call_the_composer():
    """composer.render() uses columns; nesting it here would crash the page.

    Checked against the parsed module rather than the raw text, so the rule
    can still be explained in a docstring.
    """
    import ast

    tree = ast.parse((ROOT / "lib" / "lesson_demos.py").read_text())
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "render"
        and isinstance(node.value, ast.Name) and node.value.id == "composer"
    ]
    assert not calls


def test_demos_reuse_the_verified_visualisations():
    """A second Bloch sphere could disagree with the Composer's."""
    src = (ROOT / "lib" / "lesson_demos.py").read_text()
    assert "viz.bloch_sphere" in src
    assert "viz.histogram" in src


def test_demo_keys_are_namespaced_per_lesson():
    """Two lessons sharing a demo must not share widget state."""
    src = (ROOT / "lib" / "lesson_demos.py").read_text()
    assert 'f"demo_{slug}_{key}"' in src


# --------------------------------------------------------------- rendering
def test_render_for_lesson_reports_how_many_it_drew(monkeypatch):
    calls: list[str] = []

    class _Stub:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(lesson_demos.st, "divider", lambda *a, **k: None)
    monkeypatch.setattr(lesson_demos.st, "subheader", lambda *a, **k: None)
    monkeypatch.setattr(lesson_demos.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(
        lesson_demos.st, "tabs", lambda titles: [_Stub() for _ in titles]
    )
    for key, (title, blurb, _) in list(lesson_demos.DEMO_REGISTRY.items()):
        monkeypatch.setitem(
            lesson_demos.DEMO_REGISTRY, key,
            (title, blurb, lambda k, _key=key: calls.append(_key)),
        )

    drawn = lesson_demos.render_for_lesson("01_qubits")
    assert drawn == 3
    assert calls == lesson_demos.demos_for("01_qubits")


def test_render_for_lesson_is_a_noop_without_demos(monkeypatch):
    monkeypatch.setattr(lesson_demos.st, "divider", lambda *a, **k: pytest.fail(
        "should not draw a section when the lesson has no demos"))
    assert lesson_demos.render_for_lesson("09_quantum_noise") == 0
