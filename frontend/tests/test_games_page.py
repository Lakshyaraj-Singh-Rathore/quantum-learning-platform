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
