"""The Games page and the palette filtering it depends on."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PAGE = ROOT / "pages" / "6_Games.py"
COMPOSER = ROOT / "lib" / "composer.py"


def test_games_page_exists():
    assert PAGE.is_file()


def test_games_page_sets_wide_layout():
    """Streamlit only honours set_page_config in the script it runs."""
    src = PAGE.read_text()
    assert "set_page_config" in src
    assert 'layout="wide"' in src


def test_games_page_requires_login():
    assert "auth.require_login()" in PAGE.read_text()


def test_composer_render_accepts_allowed_gates():
    """Game levels restrict the palette to the gates the level teaches."""
    import inspect

    from lib import composer

    signature = inspect.signature(composer.render)
    assert "allowed_gates" in signature.parameters


def test_palette_filters_to_allowed_gates():
    from lib import composer

    everything = {gate for gate, _, _ in composer.PALETTE}
    assert {"h", "x", "cx"} <= everything

    source = COMPOSER.read_text()
    # The filter must fall back to the full palette rather than render an
    # empty selectbox if a level names gates that do not exist.
    assert "or PALETTE" in source


def test_palette_filter_is_threaded_through_every_layer():
    source = COMPOSER.read_text()
    assert "_palette_gates(ir, key_prefix, allowed_gates)" in source
    assert "_palette(ir, key_prefix, collapsed=True, allowed_gates=allowed_gates)" in source


def test_api_client_exposes_games():
    from lib import api_client

    assert callable(api_client.games)


def test_games_call_is_not_cached():
    """Progress changes after every attempt, so a cached catalogue would lie."""
    from lib import api_client

    assert not hasattr(api_client.games, "clear")


# --- Regression: the level view must not nest columns -----------------------
#
# composer.render() uses st.columns internally (the Operations list renders one
# row of columns per op), and Streamlit allows only ONE level of column
# nesting. The first version of this page put the editor inside
# `brief, board = st.columns(...)`, which crashed every level with
# "Columns can only be placed inside other columns up to one level of nesting".
#
# It slipped through because the crash needs a NON-EMPTY circuit: _grid()
# returns early on an empty one, so the offending st.columns call never ran in
# a test that started from a blank grid.

def test_editor_is_not_rendered_inside_a_column():
    src = PAGE.read_text()
    assert "brief, board = st.columns" not in src, (
        "composer.render() uses columns internally; wrapping it in a column "
        "exceeds Streamlit's one-level nesting limit"
    )
    assert "composer_slot = st.container()" in src


def test_level_view_uses_the_drag_and_drop_grid():
    """Games should offer the same React composer as the Composer page."""
    src = PAGE.read_text()
    assert "circuit_composer(" in src
    assert "react_available" in src
    assert 'key="react_composer"' in src


def test_secondary_palette_when_react_is_available():
    """Drag-and-drop stays primary; the Python palette collapses behind it."""
    src = PAGE.read_text()
    assert 'secondary=True' in src


def test_level_view_offers_a_reset_for_broken_circuits():
    src = PAGE.read_text()
    assert "Reset to broken" in src
    assert "Clear circuit" in src
