"""Normalise lesson markdown to the constraints the renderers actually impose.

    python3 backend/scripts/format_lesson.py [slug ...]

Two rules are enforced, both discovered by watching real content fail:

1. **Display maths must open and close on the same line.** Streamlit renders the
   remainder of the page as raw LaTeX if a ``$$`` block spans lines, so
   ``$$\n...\n$$`` is collapsed onto one line.

2. **Headings are never split mid-code-block.** Handled in
   ``app.ai.rag.split_on_headings``, not here, but this script is the authoring
   side of the same requirement.

Only whitespace inside maths delimiters is changed; prose and code blocks are
left byte-identical.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "content"

#: A "$$" block whose delimiters are each alone on their own line.
#:
#: The delimiters must be anchored to whole lines. A bare ``\$\$\n`` also
#: matches the *closing* delimiter of an already single-line block
#: (``$$x$$`` followed by a newline), which would swallow everything up to the
#: next block and merge unrelated maths onto one line.
MULTILINE_DISPLAY = re.compile(r"^\$\$\s*$\n(.*?)^\$\$\s*$", re.S | re.M)


def collapse_display_maths(text: str) -> tuple[str, int]:
    """Join multi-line ``$$`` blocks onto a single line. Returns (text, count)."""
    count = len(MULTILINE_DISPLAY.findall(text))
    return MULTILINE_DISPLAY.sub(
        lambda m: "$$" + " ".join(x.strip() for x in m.group(1).strip().split("\n")) + "$$",
        text,
    ), count


def format_lesson(slug: str) -> tuple[bool, int]:
    path = CONTENT_DIR / f"{slug}.md"
    if not path.exists():
        print(f"{slug}: MISSING")
        return False, 0
    original = path.read_text(encoding="utf-8")
    text, count = collapse_display_maths(original)
    if text != original:
        path.write_text(text, encoding="utf-8")
    return True, count


def main(argv: list[str]) -> int:
    slugs = argv or sorted(p.stem for p in CONTENT_DIR.glob("*.md"))
    total = 0
    for slug in slugs:
        ok, count = format_lesson(slug)
        if ok:
            total += count
            print(f"{slug}: collapsed {count} multi-line display maths block(s)")
    print(f"\n{total} block(s) collapsed across {len(slugs)} lesson(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
