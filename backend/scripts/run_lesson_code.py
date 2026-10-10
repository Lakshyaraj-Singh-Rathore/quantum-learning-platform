"""Extract the Python blocks from a lesson and execute them in order.

Lessons build a circuit up across several fenced blocks, so the blocks are
concatenated rather than run in isolation -- that is how a reader following
the lesson top to bottom would end up with them. Warnings are errors: a
DeprecationWarning today is a hard failure after the next Qiskit upgrade.

Usage:
    python run_lesson_code.py <lesson_slug> [<lesson_slug> ...]
"""

from __future__ import annotations

import re
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"
BACKEND = ROOT / "backend"

FENCE = re.compile(r"^```(\w*)[ \t]*$", re.MULTILINE)


def python_blocks(text: str) -> list[str]:
    """Return the bodies of fenced ```python blocks, in file order."""
    blocks: list[str] = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        m = FENCE.match(lines[i])
        if not m:
            i += 1
            continue
        lang = m.group(1)
        # find the closing fence
        j = i + 1
        body: list[str] = []
        while j < len(lines) and not FENCE.match(lines[j]):
            body.append(lines[j])
            j += 1
        if j >= len(lines):
            raise ValueError(f"unterminated code fence starting at line {i + 1}")
        if lang == "python":
            blocks.append("\n".join(body))
        i = j + 1
    return blocks


def fence_parity(text: str) -> int:
    n = 0
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            n += 1
    return n


def main() -> int:
    rc = 0
    for slug in sys.argv[1:]:
        path = CONTENT / f"{slug}.md"
        if not path.exists():
            print(f"{slug}: MISSING content/{slug}.md")
            rc = 1
            continue
        text = path.read_text(encoding="utf-8")

        if fence_parity(text) % 2:
            print(f"{slug}: FAIL odd number of code fences ({fence_parity(text)})")
            rc = 1
            continue

        blocks = python_blocks(text)
        if not blocks:
            print(f"{slug}: no python blocks (fences balanced: {fence_parity(text)})")
            continue

        source = "\n\n".join(blocks)
        proc = subprocess.run(
            [sys.executable, "-W", "error::Warning", "-c", source],
            cwd=BACKEND,
            env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin", "HOME": "/home/user"},
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            print(f"{slug}: OK  {len(blocks)} python block(s) ran clean")
            if proc.stdout.strip():
                print(textwrap.indent(proc.stdout.rstrip(), "    "))
        else:
            rc = 1
            print(f"{slug}: FAIL {len(blocks)} python block(s)")
            print(textwrap.indent(proc.stderr.rstrip(), "    "))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
