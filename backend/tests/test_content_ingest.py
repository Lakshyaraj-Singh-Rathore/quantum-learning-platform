"""Regressions for lesson content handling."""

from pathlib import Path

from app.ai.rag import TRACK_MARKER_RE, infer_track

REPO = Path(__file__).resolve().parents[2]
CONTENT = REPO / "content"


def test_track_marker_is_parsed():
    assert infer_track("<!-- track: circuit -->\n# Title") == "circuit"
    assert infer_track("<!-- track: theory -->\n# Title") == "theory"
    assert infer_track("# No marker") == "theory"


def test_track_marker_is_strippable():
    """Streamlit escapes HTML, so the marker must not reach the reader."""
    body = "<!-- track: circuit -->\n# Control Flow\n\nText."
    cleaned = TRACK_MARKER_RE.sub("", body, count=1).lstrip()
    assert not cleaned.startswith("<!--")
    assert cleaned.startswith("# Control Flow")


def test_no_lesson_renders_its_marker():
    for path in sorted(CONTENT.glob("*.md")):
        cleaned = TRACK_MARKER_RE.sub("", path.read_text(encoding="utf-8"), count=1).lstrip()
        assert "<!-- track:" not in cleaned, f"{path.name} still shows its marker"


def test_content_directory_is_discoverable_from_the_repo():
    """The /content default only exists in Docker; a checkout must still work."""
    local = Path(REPO / "content")
    assert local.is_dir()
    assert len(list(local.glob("*.md"))) >= 13
