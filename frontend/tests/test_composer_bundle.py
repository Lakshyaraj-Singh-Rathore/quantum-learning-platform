"""The React composer bundle must actually be loadable by a browser.

Two failure modes both show up as a blank white iframe with nothing in the
browser console, which is impossible to diagnose from the UI:

1. MIME type. Streamlit serves component files via Python's `mimetypes`. On a
   slim base image /etc/mime.types is missing, so .js resolves to
   "application/javascript" and strict-MIME browsers refuse to run the ES
   module.
2. A stale build. build/ is gitignored, so `git pull` can leave an index.html
   referencing a Vite hash that no longer exists on disk.
"""

from __future__ import annotations

import mimetypes
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BUILD = ROOT / "circuit_composer" / "frontend" / "build"


def test_importing_the_component_pins_js_mime_type():
    """Importing the package must repair the mapping on any base image."""
    mimetypes.add_type("application/javascript", ".js")  # simulate a slim image
    import importlib

    import circuit_composer

    importlib.reload(circuit_composer)
    assert mimetypes.guess_type("bundle.js")[0] == "text/javascript"
    assert mimetypes.guess_type("styles.css")[0] == "text/css"


@pytest.mark.skipif(not BUILD.exists(), reason="composer bundle not built")
def test_bundle_is_self_consistent():
    from circuit_composer import build_is_consistent

    ok, problem = build_is_consistent()
    assert ok, problem


@pytest.mark.skipif(not BUILD.exists(), reason="composer bundle not built")
def test_every_referenced_asset_exists():
    import re

    html = (BUILD / "index.html").read_text()
    refs = re.findall(r'(?:src|href)="\./([^"]+)"', html)
    assert refs, "index.html references no assets at all"
    for ref in refs:
        assert (BUILD / ref).exists(), f"missing asset {ref}"


@pytest.mark.skipif(not BUILD.exists(), reason="composer bundle not built")
def test_assets_use_relative_paths():
    """An absolute /assets/... path 404s under Streamlit's component route."""
    html = (BUILD / "index.html").read_text()
    assert 'src="/assets' not in html
    assert 'href="/assets' not in html


def test_stale_bundle_is_reported(tmp_path, monkeypatch):
    import circuit_composer

    fake = tmp_path / "build"
    fake.mkdir()
    (fake / "index.html").write_text(
        '<script type="module" crossorigin src="./assets/index-GONE.js"></script>'
    )
    monkeypatch.setattr(circuit_composer, "_BUILD_DIR", fake)
    ok, problem = circuit_composer.build_is_consistent()
    assert ok is False
    assert "stale" in problem
    assert "npm run build" in problem


def test_dockerfile_installs_the_mime_database():
    """Belt and braces: the image should ship /etc/mime.types too."""
    assert "media-types" in (ROOT / "Dockerfile").read_text()
