"""Composer layout contract.

The user asked for an IBM-Quantum-Composer-style arrangement:
  * the timeline sits ABOVE the circuit and is never collapsed,
  * drag-and-drop is the primary editor,
  * the supporting palette sections collapse into dropdowns,
  * but the timeline and the operations list must NOT be dropdowns.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "2_Composer.py"
COMPOSER = ROOT / "lib" / "composer.py"
STRIP = ROOT / "lib" / "timeline_strip.py"


def test_timeline_renders_before_the_editor():
    src = PAGE.read_text()
    assert src.index("timeline_strip.render") < src.index("circuit_composer(")


def test_timeline_is_not_inside_an_expander():
    """It used to be 'Timeline - step through the circuit' in a collapsed box."""
    assert "Timeline - step through the circuit" not in PAGE.read_text()
    assert "st.expander" not in STRIP.read_text()


def test_secondary_palette_sections_are_dropdowns():
    src = COMPOSER.read_text()
    for label in ("Measurement & structure", "Control flow blocks"):
        assert label in src
    assert "def _palette_structural" in src
    # collapsed mode must route through expanders
    assert "collapsed" in src


def test_operations_list_is_never_collapsed():
    """The ops list is plain markdown, not an expander."""
    src = COMPOSER.read_text()
    ops_at = src.index('st.markdown("#### Operations")')
    window = src[max(0, ops_at - 400) : ops_at]
    assert "st.expander" not in window


def test_page_and_modules_parse():
    for path in (PAGE, COMPOSER, STRIP):
        ast.parse(path.read_text())


def test_code_lab_uses_real_syntax_highlighting():
    src = (ROOT / "pages" / "5_Code_Lab.py").read_text()
    assert '_SYNTAX' in src
    assert 'language="qasm"' in src
    # the old placeholder highlighting is gone for the QASM view
    assert 'st.code(built["qasm3"], language="text")' not in src
