"""Check the RAG chunks a lesson will produce, using the real chunker.

Runs ``app.ai.rag.chunk_markdown`` against the lesson file and reports the
conventions the ingester actually cares about: chunk count, oversized chunks,
and balanced code fences inside each chunk.

Usage:
    python check_lesson_chunks.py <lesson_slug> [<lesson_slug> ...]

Exit code 1 if any chunk is oversized or has an unbalanced fence.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.rag import CHUNK_TARGET_CHARS, chunk_markdown  # noqa: E402

CONTENT = ROOT / "content"
# Sections are packed while under CHUNK_TARGET_CHARS, so a chunk is only
# oversized when it started that way. 1.6x is the practical ceiling: beyond
# that the section itself should be split at a heading.
OVERSIZE = int(CHUNK_TARGET_CHARS * 1.6)


def fence_balance(text: str) -> int:
    return sum(1 for line in text.split("\n") if line.strip().startswith("```"))


def main() -> int:
    rc = 0
    for slug in sys.argv[1:]:
        path = CONTENT / f"{slug}.md"
        if not path.exists():
            print(f"{slug}: MISSING content/{slug}.md")
            rc = 1
            continue
        text = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(text)
        sizes = [len(c) for c in chunks]
        bad_fence = [i for i, c in enumerate(chunks) if fence_balance(c) % 2]
        oversized = [(i, s) for i, s in enumerate(sizes) if s > OVERSIZE]

        print(
            f"{slug}: {len(chunks)} chunk(s), "
            f"min={min(sizes)}, median={sorted(sizes)[len(sizes) // 2]}, "
            f"max={max(sizes)} (target {CHUNK_TARGET_CHARS}, oversize limit {OVERSIZE})"
        )
        if oversized:
            rc = 1
            for i, s in oversized:
                head = chunks[i].split("\n")[0][:80]
                print(f"  FAIL chunk {i} is {s} chars; starts: {head!r}")
        if bad_fence:
            rc = 1
            for i in bad_fence:
                head = chunks[i].split("\n")[0][:80]
                print(f"  FAIL chunk {i} has unbalanced fences; starts: {head!r}")
        if not oversized and not bad_fence:
            print("  ok")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
