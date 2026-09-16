"""Page width and component mount contract.

Two user-visible regressions this locks down:

* "the composer feels quite squeezed" -- set_page_config(layout="wide") only
  runs in the script Streamlit executes. Opening /Composer directly never ran
  Home.py, so every page fell back to the narrow default column.
* "white screen" -- React.StrictMode double-mounts, and
  withStreamlitConnection removes its RENDER_EVENT listener on unmount. If
  Streamlit's single RENDER event lands in that gap the wrapper renders null
  forever: a blank white iframe with nothing in the console.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGES = sorted((ROOT / "pages").glob("*.py"))
INDEX_TSX = ROOT / "circuit_composer" / "frontend" / "src" / "index.tsx"


@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_every_page_sets_wide_layout(page: Path):
    src = page.read_text()
    assert "set_page_config" in src, f"{page.name} renders narrow when opened directly"
    assert 'layout="wide"' in src


def test_home_still_sets_wide_layout():
    assert 'layout="wide"' in (ROOT / "Home.py").read_text()


def test_component_is_not_wrapped_in_strict_mode():
    src = INDEX_TSX.read_text()
    assert "StrictMode" not in src.split("// NOTE")[-1].replace(
        "StrictMode mounts", ""
    ) or "<React.StrictMode>" not in src
    assert "<React.StrictMode>" not in src


def test_component_retries_ready_signal():
    """A missed RENDER event must not leave a permanently blank iframe."""
    src = INDEX_TSX.read_text()
    assert "setComponentReady" in src
    assert "childElementCount" in src


def test_frame_height_is_clamped():
    src = INDEX_TSX.read_text()
    assert "MIN_FRAME_HEIGHT" in src
    assert "setFrameHeight" in src


def test_desktop_layout_is_not_shrunk():
    """The 720px breakpoint made ordinary laptop windows feel cramped."""
    css = (ROOT / "circuit_composer" / "frontend" / "src" / "styles.css").read_text()
    assert "max-width: 720px" not in css
    assert "max-width: 560px" in css
