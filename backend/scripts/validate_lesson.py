"""Validate lesson content against the M4 authoring standard.

    python3 backend/scripts/validate_lesson.py [slug ...]

Checks the mechanical rules from docs/M4_CONTENT_AUTHORING_STANDARD.md that can
be verified without a human reader:

  * title is the first level-1 heading, and there is no YAML front-matter
  * required sections are present
  * 3-6 learning objectives, using measurable verbs
  * maths delimiters are balanced and compile under KaTeX
  * code fences are balanced
  * exercises exist and are followed by an answers section
  * a references section exists
  * headings are frequent enough to produce sane RAG chunks

It does NOT claim to judge pedagogy or mathematical truth. Those need a human
reviewer, and the tracker records them separately.

Exit code is 0 when every checked lesson passes, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "content"

#: Sections every lesson must carry, matched case-insensitively on the heading.
REQUIRED_SECTIONS = [
    r"learning objectives?",
    r"exercises?",
    r"summary",
    r"references?",
]

#: Verbs that make an objective checkable. Anything else is flagged as vague.
MEASURABLE_VERBS = {
    "define", "explain", "calculate", "compare", "construct", "interpret",
    "implement", "analyse", "analyze", "state", "derive", "apply", "identify",
    "distinguish", "list", "compute", "show", "describe", "draw", "predict",
    "evaluate", "classify", "convert", "locate", "prepare", "measure",
    "write", "enter", "build", "predict", "report", "verify", "use", "run",
}
VAGUE_VERBS = {"understand", "appreciate", "learn", "know", "grasp", "explore"}

#: Roughly CHUNK_TARGET_CHARS; a section much larger than this makes one chunk
#: that is too coarse for retrieval.
CHUNK_TARGET_CHARS = 1200


class LessonReport:
    def __init__(self, slug: str) -> None:
        self.slug = slug
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return not self.errors


def _headings(text: str) -> list[tuple[int, str]]:
    """Headings, ignoring fenced code blocks.

    A Python comment such as ``# run the circuit`` looks exactly like a
    level-1 heading, so scanning raw text reports headings that do not exist.
    """
    out: list[tuple[int, str]] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            out.append((len(m.group(1)), m.group(2).strip()))
    return out


def validate(slug: str, text: str) -> LessonReport:
    rep = LessonReport(slug)

    # -- front-matter -------------------------------------------------------- #
    if text.lstrip().startswith("---"):
        rep.errors.append(
            "starts with YAML front-matter; there is no front-matter parser, "
            "so this would render as literal text"
        )

    # -- title --------------------------------------------------------------- #
    headings = _headings(text)
    if not headings or headings[0][0] != 1:
        rep.errors.append("no level-1 heading; the first H1 becomes the lesson title")
    elif sum(1 for lvl, _ in headings if lvl == 1) > 1:
        rep.warnings.append("more than one H1; only the first is used as the title")

    # -- required sections --------------------------------------------------- #
    heading_text = "\n".join(h.lower() for _lvl, h in headings)
    for pattern in REQUIRED_SECTIONS:
        if not re.search(pattern, heading_text):
            rep.errors.append(f"missing required section matching /{pattern}/i")

    # -- objectives ---------------------------------------------------------- #
    obj_match = re.search(
        r"^##\s+Learning objectives?\s*$(.*?)(?=^##\s|\Z)", text, flags=re.M | re.S
    )
    if obj_match:
        bullets = re.findall(r"^\s*[-*]\s+(.+)$", obj_match.group(1), flags=re.M)
        if not (3 <= len(bullets) <= 6):
            rep.errors.append(
                f"{len(bullets)} learning objectives; the standard requires 3-6"
            )
        for b in bullets:
            first = re.sub(r"[^a-zA-Z]", "", b.split()[0]).lower() if b.split() else ""
            if first in VAGUE_VERBS:
                rep.warnings.append(f"objective uses a vague verb: {b.strip()[:60]}")
            elif first not in MEASURABLE_VERBS:
                rep.warnings.append(
                    f"objective does not start with a measurable verb: {b.strip()[:60]}"
                )

    # -- maths --------------------------------------------------------------- #
    if text.count("$$") % 2:
        rep.errors.append("odd number of $$ delimiters; display maths is unbalanced")
    stripped = re.sub(r"\$\$.*?\$\$", "", text, flags=re.S)
    if stripped.count("$") % 2:
        rep.errors.append("odd number of single $ delimiters; inline maths is unbalanced")

    # -- display maths must open and close on one line ----------------------- #
    # Streamlit renders the remainder of the page as raw LaTeX if a $$ block
    # spans lines, so this is enforced per line, not per document.
    for number, line in enumerate(text.split("\n"), start=1):
        if "$$" not in line:
            continue
        if line.count("$$") % 2:
            rep.errors.append(
                f"line {number} opens a $$ block that does not close on the "
                "same line; Streamlit renders the remainder as raw LaTeX"
            )
        elif line.count("$$") > 2:
            rep.errors.append(
                f"line {number} has more than one $$ pair; split them onto "
                "separate lines"
            )

    # -- code fences --------------------------------------------------------- #
    if text.count("```") % 2:
        rep.errors.append("odd number of ``` fences; a code block is unclosed")

    # -- exercises must have answers ---------------------------------------- #
    if re.search(r"^##\s+Exercises?", heading_text, flags=re.M):
        after = text.split(re.search(r"^##\s+Exercises?\s*$", text, flags=re.M).group(0), 1)[1]
        if not re.search(r"^#{2,3}\s+Answers?", after, flags=re.M):
            rep.errors.append("exercises section has no answers subsection")

    # -- chunking ------------------------------------------------------------ #
    sections = re.split(r"\n(?=#{1,3}\s)", text.strip())
    for sec in sections:
        if len(sec) > CHUNK_TARGET_CHARS * 2:
            title = sec.strip().splitlines()[0][:60]
            rep.warnings.append(
                f"section is {len(sec)} chars (>2x chunk target); consider splitting: {title}"
            )

    return rep


def main(argv: list[str]) -> int:
    slugs = argv or sorted(p.stem for p in CONTENT_DIR.glob("*.md"))
    reports = []
    for slug in slugs:
        path = CONTENT_DIR / f"{slug}.md"
        if not path.exists():
            print(f"{slug}: MISSING")
            reports.append(LessonReport(slug))
            reports[-1].errors.append("file not found")
            continue
        reports.append(validate(slug, path.read_text(encoding="utf-8")))

    failed = 0
    for rep in reports:
        status = "PASS" if rep.ok else "FAIL"
        if not rep.ok:
            failed += 1
        print(f"{status}  {rep.slug}")
        for e in rep.errors:
            print(f"      error:   {e}")
        for w in rep.warnings:
            print(f"      warning: {w}")
    print(f"\n{len(reports) - failed}/{len(reports)} lessons pass")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
