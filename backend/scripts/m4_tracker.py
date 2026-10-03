"""Generate the M4 lesson rewrite tracker.

Run from the repository root:

    python3 backend/scripts/m4_tracker.py

The tracker is derived from the target curriculum, the topic registry, the
content-gap coverage table and the real lesson files. Nothing here invents
lesson names, slugs or topic identifiers: where the repository does not
already define a topic for a target item, the entry says so and is flagged,
because creating topics is an architectural change that needs approval.

Outputs:
    docs/M4_LESSON_REWRITE_TRACKER.md
    docs/M4_LESSON_REWRITE_TRACKER.json
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.curriculum import (  # noqa: E402
    NAMESPACES,
    TOPICS,
    all_lesson_topics,
    lessons_for_topic,
)
from curriculum_reports import COVERAGE, TARGET_CURRICULUM  # noqa: E402

CONTENT_DIR = ROOT / "content"

VALIDATION_NOT_RUN = "not_run"
REWRITE_NOT_STARTED = "not_started"

#: Section slug per roadmap letter, from the live registry.
SECTION_BY_LETTER: dict[str, tuple[str, str]] = {
    letter: (slug, title) for slug, letter, title in NAMESPACES.values()
}

TOPICS_BY_ID = {str(t["id"]): t for t in TOPICS}

#: Reading rate used only to estimate duration for EXISTING content, and always
#: labelled as an estimate. Nothing is invented for unauthored items.
WORDS_PER_MINUTE = 180


def slugify(name: str) -> str:
    """Conservative slug derivation. Only used to *propose* a slug for an
    unauthored item, never to rename an existing one."""
    s = name.lower()
    s = s.replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def lesson_meta(slug: str) -> dict[str, Any]:
    path = CONTENT_DIR / f"{slug}.md"
    if not path.exists():
        return {"exists": False, "words": 0, "title": None, "sections": 0, "has_code": False,
                "has_math": False, "has_exercise": False}
    text = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.M)
    headings = re.findall(r"^#{2,3}\s+(.+)$", text, flags=re.M)
    return {
        "exists": True,
        "words": len(text.split()),
        "title": title_match.group(1).strip() if title_match else slug,
        "sections": len(headings),
        "has_code": "```" in text,
        "has_math": ("$$" in text) or bool(re.search(r"(?<!\$)\$(?!\$).+\$(?!\$)", text)),
        "has_exercise": bool(re.search(r"exercise|practice|try it|check your", text, re.I)),
    }


def build_rows() -> list[dict[str, Any]]:
    """One row per target item, in roadmap order."""
    links = all_lesson_topics()
    secondary_by_lesson: dict[str, list[str]] = {}
    for lesson_slug, topic_id, _conf, is_primary in links:
        if not is_primary:
            secondary_by_lesson.setdefault(lesson_slug, []).append(topic_id)

    prereqs_by_topic = {str(t["id"]): list(t.get("prerequisites") or []) for t in TOPICS}

    rows: list[dict[str, Any]] = []
    for section_key, items in TARGET_CURRICULUM.items():
        letter = section_key.split()[0]
        section_slug, section_name = SECTION_BY_LETTER[letter]
        for index, item in enumerate(items, start=1):
            topic_id, content_status = COVERAGE.get(item, (None, "missing"))
            topic = TOPICS_BY_ID.get(topic_id) if topic_id else None

            existing_slugs = lessons_for_topic(topic_id) if topic_id else []
            # lessons_for_topic preserves registry order, which is not
            # "primary first". A target item should point at the lesson that
            # actually claims the topic as its primary, so sort by is_primary.
            primaries = {ls for ls, tid, _c, p in links if p and tid == topic_id}
            primary_slug = (
                sorted(existing_slugs, key=lambda s: (s not in primaries, s))[0]
                if existing_slugs else None
            )
            meta = lesson_meta(primary_slug) if primary_slug else {
                "exists": False, "words": 0, "title": None, "sections": 0,
                "has_code": False, "has_math": False, "has_exercise": False,
            }

            if content_status == "existing" and primary_slug:
                lesson_slug: str | None = primary_slug
                lesson_title: str | None = meta["title"]
                slug_state = "assigned"
            elif content_status == "partial" and primary_slug:
                lesson_slug = primary_slug
                lesson_title = meta["title"]
                slug_state = "assigned"
            else:
                lesson_slug = None
                lesson_title = None
                slug_state = "pending"

            item_id = f"M4-{letter}{index:02d}"

            # An unauthored item has no topic in the registry. Creating one is an
            # architectural change and is flagged rather than done silently.
            topic_state = "registered" if topic_id else "PENDING_TOPIC_CREATION"

            notes: list[str] = []
            if topic_id is None:
                notes.append(
                    "No registered topic covers this target item. Authoring it "
                    "requires a new topic identifier, which changes the "
                    "curriculum architecture and needs explicit approval."
                )
            if slug_state == "pending":
                notes.append(
                    f"Proposed slug '{slugify(item)}' is a suggestion only; it "
                    "is not an existing stable slug."
                )
            if content_status == "partial":
                notes.append(
                    "Existing lesson touches this item without covering the "
                    "intended scope."
                )
            if topic_id and len(existing_slugs) > 1:
                notes.append(
                    f"Topic already has {len(existing_slugs)} lessons: "
                    + ", ".join(existing_slugs)
                )

            rows.append({
                "item_id": item_id,
                "section_id": section_slug,
                "section_name": section_name,
                "topic_id": topic_id,
                "topic_name": str(topic["title"]) if topic else None,
                "topic_state": topic_state,
                "lesson_slug": lesson_slug,
                "lesson_title": lesson_title,
                "proposed_slug": None if lesson_slug else slugify(item),
                "content_status": content_status,
                "rewrite_status": REWRITE_NOT_STARTED,
                "primary_topic": topic_id if content_status in ("existing", "partial") else None,
                "secondary_topics": secondary_by_lesson.get(primary_slug or "", []),
                # Other lessons already mapped to this topic. A topic can have
                # several primary lessons, and M4 must rewrite every existing
                # lesson, so they are listed rather than dropped.
                "additional_existing_lessons": [
                    s for s in existing_slugs if s != primary_slug
                ],
                "prerequisites": prereqs_by_topic.get(topic_id, []) if topic_id else [],
                "difficulty": (str(topic["difficulty"]) if topic else None),
                "estimated_duration_min": (
                    round(meta["words"] / WORDS_PER_MINUTE, 1)
                    if meta["exists"] else None
                ),
                "objectives": list(topic.get("learning_objectives") or []) if topic else [],
                "existing_content_review": (
                    f"{meta['words']} words, {meta['sections']} sections, "
                    f"code={meta['has_code']}, math={meta['has_math']}, "
                    f"exercise={meta['has_exercise']}"
                    if meta["exists"] else "No existing content."
                ),
                "rewrite_scope": (
                    "Rewrite existing lesson to the authoring standard."
                    if content_status == "existing"
                    else "Complete partial lesson to the authoring standard."
                    if content_status == "partial"
                    else "Author new lesson."
                ),
                "mathematics_required": (
                    bool(meta["has_math"]) if meta["exists"] else None
                ),
                "code_required": bool(meta["has_code"]) if meta["exists"] else None,
                "simulation_required": None,
                "exercises_required": (
                    not meta["has_exercise"] if meta["exists"] else True
                ),
                "references_required": True,
                "technical_review": VALIDATION_NOT_RUN,
                "schema_validation": VALIDATION_NOT_RUN,
                "mapping_validation": VALIDATION_NOT_RUN,
                "prerequisite_validation": VALIDATION_NOT_RUN,
                "code_validation": VALIDATION_NOT_RUN,
                "integration_validation": VALIDATION_NOT_RUN,
                "review_notes": " ".join(notes),
                "last_updated": date.today().isoformat(),
            })
    rows.extend(_orphan_lesson_rows(rows))
    return rows


def _orphan_lesson_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Existing lessons that no target-curriculum item points at.

    The 97-item target list and the 17-topic registry do not line up: some
    registered topics have no target item, yet their lessons exist on disk.
    M4 mandates rewriting every existing lesson, so these are tracked here
    rather than silently left out.
    """
    covered = {r["lesson_slug"] for r in rows if r["lesson_slug"]}
    for r in rows:
        covered.update(r.get("additional_existing_lessons") or [])

    links = all_lesson_topics()
    topic_of_primary: dict[str, str] = {
        ls: tid for ls, tid, _c, p in links if p
    }
    prereqs_by_topic = {str(t["id"]): list(t.get("prerequisites") or []) for t in TOPICS}
    section_of_topic: dict[str, tuple[str, str]] = {}
    for t in TOPICS:
        ns = str(t["namespace"])
        slug, letter, title = NAMESPACES[ns]
        section_of_topic[str(t["id"])] = (slug, title)

    extra: list[dict[str, Any]] = []
    for path in sorted(CONTENT_DIR.glob("*.md")):
        slug = path.stem
        if slug in covered:
            continue
        topic_id = topic_of_primary.get(slug)
        topic = TOPICS_BY_ID.get(topic_id) if topic_id else None
        meta = lesson_meta(slug)
        section_slug, section_name = section_of_topic.get(
            topic_id, ("unassigned", "Unassigned"))
        extra.append({
            "item_id": f"M4-EXTRA-{slug}",
            "section_id": section_slug,
            "section_name": section_name,
            "topic_id": topic_id,
            "topic_name": str(topic["title"]) if topic else None,
            "topic_state": "registered" if topic_id else "PENDING_TOPIC_CREATION",
            "lesson_slug": slug,
            "lesson_title": meta["title"],
            "proposed_slug": None,
            "content_status": "existing",
            "rewrite_status": REWRITE_NOT_STARTED,
            "primary_topic": topic_id,
            "secondary_topics": [t for ls, t, _c, p in links if ls == slug and not p],
            "prerequisites": prereqs_by_topic.get(topic_id, []) if topic_id else [],
            "difficulty": str(topic["difficulty"]) if topic else None,
            "estimated_duration_min": round(meta["words"] / WORDS_PER_MINUTE, 1),
            "objectives": list(topic.get("learning_objectives") or []) if topic else [],
            "existing_content_review": (
                f"{meta['words']} words, {meta['sections']} sections, "
                f"code={meta['has_code']}, math={meta['has_math']}, "
                f"exercise={meta['has_exercise']}"
            ),
            "rewrite_scope": "Rewrite existing lesson to the authoring standard.",
            "mathematics_required": bool(meta["has_math"]),
            "code_required": bool(meta["has_code"]),
            "simulation_required": None,
            "exercises_required": not meta["has_exercise"],
            "references_required": True,
            "technical_review": VALIDATION_NOT_RUN,
            "schema_validation": VALIDATION_NOT_RUN,
            "mapping_validation": VALIDATION_NOT_RUN,
            "prerequisite_validation": VALIDATION_NOT_RUN,
            "code_validation": VALIDATION_NOT_RUN,
            "integration_validation": VALIDATION_NOT_RUN,
            "review_notes": (
                "This lesson exists on disk but no target-curriculum item "
                "points at it: the 97-item target list and the 17-topic "
                "registry do not line up. M4 still requires rewriting it."
            ),
            "last_updated": date.today().isoformat(),
        })
    return extra


def write_markdown(rows: list[dict[str, Any]], out: Path) -> None:
    by_status = {s: sum(1 for r in rows if r["content_status"] == s)
                 for s in ("existing", "partial", "missing")}
    pending_topics = sum(1 for r in rows if r["topic_id"] is None)

    lines = [
        "# M4 Lesson Rewrite Tracker",
        "",
        "Generated by `backend/scripts/m4_tracker.py` from the target curriculum,",
        "the topic registry, the content-gap coverage table and the real lesson",
        "files. Regenerate rather than editing by hand.",
        "",
        "This is the authoritative work queue for M4. Nothing is marked",
        "`verified` until its content and applicable validations have passed.",
        "",
        "## Summary",
        "",
        f"- Target items: **{len(rows)}**",
        f"- Existing: **{by_status['existing']}**",
        f"- Partial: **{by_status['partial']}**",
        f"- Missing: **{by_status['missing']}**",
        f"- Items with a registered topic: **{len(rows) - pending_topics}**",
        f"- Items needing topic creation: **{pending_topics}**",
        "",
        "> **Scope warning.** Most target items have **no registered topic**,",
        "> because the registry defines 17 topics while the target curriculum",
        "> lists 97 items. Authoring those items requires creating new topic",
        "> identifiers, which changes the curriculum architecture. Per the M4",
        "> brief, architecture changes are out of scope without explicit",
        "> approval, so those rows are recorded with",
        "> `topic_state = PENDING_TOPIC_CREATION` rather than silently assigned.",
        "",
        "## Status vocabulary",
        "",
        "Content: `existing` | `partial` | `missing`",
        "",
        "Rewrite: `not_started` | `audited` | `in_progress` | `draft_complete` |",
        "`technical_review` | `content_review` | `integration_test` | `verified` |",
        "`blocked` | `deferred`",
        "",
        "Validation: `not_run` | `passed` | `failed` | `blocked` | `not_applicable`",
        "",
    ]

    for letter in [k.split()[0] for k in TARGET_CURRICULUM]:
        section_slug, section_name = SECTION_BY_LETTER[letter]
        items = [r for r in rows if r["item_id"].startswith(f"M4-{letter}")]
        counts = {s: sum(1 for r in items if r["content_status"] == s)
                  for s in ("existing", "partial", "missing")}
        lines += [
            f"## Section {letter} — {section_name}",
            "",
            f"`{section_slug}` — {len(items)} items "
            f"(existing {counts['existing']}, partial {counts['partial']}, "
            f"missing {counts['missing']})",
            "",
            "| Item ID | Target item | Topic ID | Lesson slug | Status | Rewrite | Notes |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in items:
            topic_cell = f"`{r['topic_id']}`" if r["topic_id"] else "— *pending*"
            slug_cell = f"`{r['lesson_slug']}`" if r["lesson_slug"] else (
                f"*{r['proposed_slug']}?*")
            note = r["review_notes"].split(".")[0] if r["review_notes"] else ""
            lines.append(
                f"| {r['item_id']} | {_target_name(r['item_id'])} | {topic_cell} | "
                f"{slug_cell} | {r['content_status']} | {r['rewrite_status']} | "
                f"{note} |"
            )
        lines.append("")

    extras = [r for r in rows if r["item_id"].startswith("M4-EXTRA-")]
    if extras:
        lines += [
            "## Existing lessons with no target-curriculum item",
            "",
            "These lessons exist on disk and must still be rewritten, but no",
            "97-item target row points at them. The target list and the",
            "17-topic registry do not line up; this section makes the",
            "mismatch visible instead of hiding it.",
            "",
            "| Item ID | Lesson slug | Topic ID | Status | Rewrite |",
            "|---|---|---|---|---|",
        ]
        for r in extras:
            topic_cell = f"`{r['topic_id']}`" if r["topic_id"] else "— *pending*"
            lines.append(
                f"| {r['item_id']} | `{r['lesson_slug']}` | {topic_cell} | "
                f"{r['content_status']} | {r['rewrite_status']} |"
            )
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")


_TARGET_INDEX: dict[str, str] = {}


def _build_target_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    for section_key, items in TARGET_CURRICULUM.items():
        letter = section_key.split()[0]
        for index, item in enumerate(items, start=1):
            idx[f"M4-{letter}{index:02d}"] = item
    return idx


_TARGET_INDEX.update(_build_target_index())


def _target_name(item_id: str) -> str:
    return _TARGET_INDEX.get(item_id, "")


def main() -> None:
    rows = build_rows()
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)

    (docs / "M4_LESSON_REWRITE_TRACKER.json").write_text(
        json.dumps(
            {
                "generated_by": "backend/scripts/m4_tracker.py",
                "generated_on": date.today().isoformat(),
                "items": rows,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_markdown(rows, docs / "M4_LESSON_REWRITE_TRACKER.md")
    pending = sum(1 for r in rows if r["topic_id"] is None)
    print(f"wrote {len(rows)} tracker items to {docs} ({pending} need topic creation)")


if __name__ == "__main__":
    main()
