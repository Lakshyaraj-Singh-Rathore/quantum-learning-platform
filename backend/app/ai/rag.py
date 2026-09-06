"""Curriculum ingestion + retrieval over Postgres/pgvector.

Falls back to keyword scoring when embeddings are unavailable (no API key), so
the tutor still cites real lesson content in a demo environment.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.gemini_client import embed, is_configured
from app.config import get_settings
from app.models.content import ContentChunk, Lesson

log = logging.getLogger(__name__)

CHUNK_TARGET_CHARS = 1200

TAG_KEYWORDS = {
    "qubit": ["qubit", "superposition", "bloch", "ket"],
    "gates": ["gate", "hadamard", "pauli", "rotation", "unitary"],
    "entanglement": ["entangle", "bell", "ghz", "epr"],
    "measurement": ["measure", "collapse", "shot", "probabilit"],
    "algorithms": ["deutsch", "jozsa", "oracle", "algorithm"],
    "grover": ["grover", "amplitude amplification", "diffuser", "search"],
    "variational": ["vqe", "qaoa", "ansatz", "variational", "optimiz"],
    "dynamic": ["dynamic", "mid-circuit", "feed-forward", "while", "if/else", "conditional"],
}


def infer_tags(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({tag for tag, words in TAG_KEYWORDS.items() if any(w in lowered for w in words)})


def chunk_markdown(text: str) -> list[str]:
    """Split on headings, then pack sections up to a target size."""
    sections = re.split(r"\n(?=#{1,3}\s)", text.strip())
    chunks: list[str] = []
    buffer = ""
    for section in sections:
        if not section.strip():
            continue
        if len(buffer) + len(section) < CHUNK_TARGET_CHARS:
            buffer = f"{buffer}\n\n{section}".strip()
        else:
            if buffer:
                chunks.append(buffer.strip())
            buffer = section.strip()
    if buffer:
        chunks.append(buffer.strip())
    return chunks or [text.strip()]


def _title_of(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, flags=re.M)
    return match.group(1).strip() if match else fallback.replace("_", " ").title()


def ingest_content_folder(db: Session, folder: str | None = None, force: bool = False) -> dict:
    """Load /content markdown into lessons + embedded chunks (idempotent)."""
    settings = get_settings()
    root = Path(folder or settings.content_dir)
    if not root.exists():
        log.info("content folder %s not found; skipping ingestion", root)
        return {"lessons": 0, "chunks": 0, "skipped": True}

    lessons = 0
    chunks_written = 0
    embedded = 0

    for order, path in enumerate(sorted(root.glob("*.md"))):
        slug = path.stem
        text = path.read_text(encoding="utf-8")
        tags = infer_tags(text)

        lesson = db.scalar(select(Lesson).where(Lesson.slug == slug))
        if lesson is None:
            lesson = Lesson(
                slug=slug,
                title=_title_of(text, slug),
                path=str(path),
                tags=tags,
                order_index=order,
            )
            db.add(lesson)
            lessons += 1
        else:
            lesson.title = _title_of(text, slug)
            lesson.tags = tags
            lesson.order_index = order

        existing = db.scalar(
            select(func.count()).select_from(ContentChunk).where(ContentChunk.lesson_slug == slug)
        )

        # Chunks ingested before a GEMINI_API_KEY was configured are stored
        # with embedding=NULL. Without this backfill they would never gain an
        # embedding, silently degrading RAG to keyword matching forever.
        if existing and not force:
            if is_configured():
                # NB: a real pgvector column stores SQL NULL, but the JSON
                # fallback used on SQLite stores the string 'null'. Filter in
                # Python so the backfill works identically on both.
                rows = db.scalars(
                    select(ContentChunk).where(ContentChunk.lesson_slug == slug)
                ).all()
                for stale in rows:
                    if stale.embedding is not None:
                        continue
                    vector = embed(stale.text)
                    if vector is not None:
                        stale.embedding = vector
                        embedded += 1
            continue
        if existing and force:
            for stale in db.scalars(
                select(ContentChunk).where(ContentChunk.lesson_slug == slug)
            ).all():
                db.delete(stale)

        for index, chunk in enumerate(chunk_markdown(text)):
            vector = embed(chunk)
            if vector is not None:
                embedded += 1
            db.add(
                ContentChunk(
                    lesson_slug=slug,
                    chunk_index=index,
                    text=chunk,
                    tags=infer_tags(chunk) or tags,
                    embedding=vector,
                )
            )
            chunks_written += 1

    db.commit()

    # Report the true corpus state, not just what this run touched: a partial
    # backfill (e.g. embeddings rejected mid-run) is otherwise invisible.
    total_chunks = db.scalar(select(func.count()).select_from(ContentChunk)) or 0
    unembedded = sum(
        1 for row in db.scalars(select(ContentChunk)).all() if row.embedding is None
    )
    if unembedded:
        log.warning(
            "%d of %d content chunks still have no embedding; "
            "AI retrieval will use the keyword fallback for those",
            unembedded,
            total_chunks,
        )
    return {
        "lessons": lessons,
        "chunks": chunks_written,
        "embedded": embedded,
        "total_chunks": total_chunks,
        "unembedded": unembedded,
        "skipped": False,
    }


def retrieve(db: Session, query: str, k: int = 4) -> list[dict[str, Any]]:
    """Top-k curriculum chunks: vector search when possible, else keywords."""
    vector = embed(query)
    if vector is not None:
        try:
            rows = db.scalars(
                select(ContentChunk)
                .where(ContentChunk.embedding.isnot(None))
                .order_by(ContentChunk.embedding.cosine_distance(vector))
                .limit(k)
            ).all()
            if rows:
                return [_as_citation(r) for r in rows]
        except Exception as exc:  # noqa: BLE001
            log.warning("vector search failed, falling back to keywords: %s", exc)
    return _keyword_search(db, query, k)


def _keyword_search(db: Session, query: str, k: int) -> list[dict[str, Any]]:
    terms = [t for t in re.findall(r"[a-zA-Z]{3,}", query.lower()) if t not in _STOPWORDS]
    rows = db.scalars(select(ContentChunk).limit(500)).all()
    scored: list[tuple[int, ContentChunk]] = []
    for row in rows:
        lowered = row.text.lower()
        score = sum(lowered.count(term) for term in terms)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [_as_citation(row) for _score, row in scored[:k]]


def _as_citation(chunk: ContentChunk) -> dict[str, Any]:
    return {
        "lesson_slug": chunk.lesson_slug,
        "chunk_index": chunk.chunk_index,
        "text": chunk.text,
        "tags": chunk.tags or [],
    }


_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "what", "why", "how", "does", "are", "was",
    "can", "you", "explain", "please", "tell", "about", "from", "into", "when", "which",
}


__all__ = ["ingest_content_folder", "retrieve", "chunk_markdown", "infer_tags"]
