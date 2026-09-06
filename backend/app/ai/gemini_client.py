"""Thin Gemini wrapper with graceful degradation when no API key is set."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.config import get_settings

log = logging.getLogger(__name__)


class GeminiUnavailable(RuntimeError):
    pass


def is_configured() -> bool:
    """True only when a key is set AND the SDK is importable."""
    if not get_settings().gemini_api_key:
        return False
    try:
        import google.generativeai  # noqa: F401
    except ImportError:
        return False
    return True


def _client():
    settings = get_settings()
    if not settings.gemini_api_key:
        raise GeminiUnavailable(
            "Gemini is not configured. Set GEMINI_API_KEY to enable AI tutoring."
        )
    try:
        import google.generativeai as genai
    except ImportError as exc:  # pragma: no cover
        raise GeminiUnavailable("google-generativeai is not installed") from exc

    genai.configure(api_key=settings.gemini_api_key)
    return genai


def _qualified_model(name: str) -> str:
    """Return a model name the SDK accepts.

    ``genai.embed_content`` rejects a bare id with "Model names should start
    with 'models/' or 'tunedModels/'", so accept either form in configuration
    and normalise here.
    """
    name = (name or "").strip()
    if name.startswith(("models/", "tunedModels/")):
        return name
    return f"models/{name}"


def embed(text: str) -> Optional[list[float]]:
    """Embed a single chunk of text; returns None when Gemini is unavailable.

    ``gemini-embedding-001`` returns 3072 dimensions by default, but the
    ``content_chunks.embedding`` column is sized to ``settings.embedding_dim``.
    Request ``output_dimensionality`` so the vector matches the schema without
    a migration; older models ignore/reject the argument, so fall back to a
    plain call and truncate.
    """
    try:
        genai = _client()
    except GeminiUnavailable:
        return None
    settings = get_settings()
    model = _qualified_model(settings.gemini_embed_model)
    dim = settings.embedding_dim

    def _vector_of(result: Any) -> list[float]:
        raw = result["embedding"] if isinstance(result, dict) else result.embedding
        return list(raw)

    try:
        try:
            result = genai.embed_content(
                model=model, content=text, output_dimensionality=dim
            )
        except TypeError:
            # SDK too old to accept the kwarg
            result = genai.embed_content(model=model, content=text)
        vector = _vector_of(result)
    except Exception as exc:  # noqa: BLE001
        log.warning("embedding failed: %s", exc)
        return None

    if len(vector) != dim:
        log.warning(
            "embedding model %s returned %d dims, expected %d; truncating",
            model,
            len(vector),
            dim,
        )
        vector = vector[:dim]
        if len(vector) < dim:
            return None
    return vector


def generate(
    prompt: str,
    system_instruction: str | None = None,
    tools: list[Any] | None = None,
    history: list[dict[str, str]] | None = None,
) -> str:
    genai = _client()
    settings = get_settings()
    model = genai.GenerativeModel(
        settings.gemini_chat_model,
        system_instruction=system_instruction,
        tools=tools or None,
    )
    contents: list[dict[str, Any]] = []
    for turn in history or []:
        role = "model" if turn.get("role") in {"assistant", "model"} else "user"
        contents.append({"role": role, "parts": [turn.get("content", "")]})
    contents.append({"role": "user", "parts": [prompt]})

    response = model.generate_content(contents)
    return (getattr(response, "text", "") or "").strip()


__all__ = ["embed", "generate", "is_configured", "GeminiUnavailable"]
