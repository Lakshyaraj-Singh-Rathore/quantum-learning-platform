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


# --- Winning must not hide the evidence -------------------------------------

def test_results_panel_renders_the_full_table_not_just_failures():
    """The table used to be drawn only when `failures` was non-empty."""
    src = PAGE.read_text()
    assert 'extra.get("table")' in src
    assert 'if extra.get("failures"):' not in src, (
        "gating the table on failures hides it the moment the learner wins"
    )


def test_results_panel_warns_about_superposition():
    src = PAGE.read_text()
    assert "superposed" in src
    assert "superposition" in src.lower()


def test_results_panel_shows_the_observed_output_column():
    src = PAGE.read_text()
    assert '"Output"' in src


def test_results_panel_surfaces_state_fidelity():
    """A histogram cannot distinguish |Phi+> from |Phi->; the fidelity can."""
    src = PAGE.read_text()
    assert "fidelity" in src.lower()


# --- A result must not outlive the circuit that produced it ------------------
#
# Reported as "the game shows success on a wrong answer". The grader was
# right; the PAGE was wrong. `game_attempt` persisted across reruns, so after a
# win the "Level complete" banner stayed on screen while the learner edited the
# circuit into something incorrect.

def test_attempt_is_stamped_with_the_circuit_that_was_graded():
    src = PAGE.read_text()
    assert "game_attempt_circuit" in src
    assert "game_attempt_level" in src


def test_results_are_hidden_when_the_circuit_changes():
    src = PAGE.read_text()
    assert "same_circuit" in src
    assert "changed the circuit since the last run" in src


def test_stamp_ignores_op_ids():
    """Op ids are regenerated on every rebuild; comparing them always differs."""
    src = PAGE.read_text()
    assert "_without_ids" in src
    # Inlined rather than imported: app.quantum.inspect needs pydantic-settings,
    # which the Streamlit image does not install.
    assert "from app.quantum.inspect import" not in src


def test_every_clear_path_forgets_the_stamp_too():
    """A stale stamp with no attempt, or vice versa, would misreport."""
    src = PAGE.read_text()
    assert "_forget_attempt()" in src
    # The old bare pop is gone; all three sites go through the helper.
    assert 'st.session_state.pop("game_attempt", None)' not in src.split(
        "def _forget_attempt"
    )[1].split("def ")[1]
