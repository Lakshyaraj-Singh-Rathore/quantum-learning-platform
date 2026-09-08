"""Thin Gemini wrapper with graceful degradation when no API key is set."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from app.config import get_settings

log = logging.getLogger(__name__)

#: Retry budget for embedding calls, which free-tier keys rate limit heavily.
EMBED_MAX_ATTEMPTS = 4
EMBED_BACKOFF_SECONDS = 1.5

#: Wall-clock ceiling for a chat completion, in seconds.
#:
#: Without this the SDK falls back to google-api-core's default retry policy,
#: which keeps retrying until a *600 second* deadline. The Streamlit client
#: gives up after 60s, so a slow or rate-limited call surfaced as the generic
#: "Cannot reach the API ... (timed out)" while the backend was still waiting.
#: Keep this comfortably under the client timeout so the user gets a real
#: error message from us instead of a dead connection.
CHAT_TIMEOUT_SECONDS = 30

#: Same reasoning for embeddings: bound each individual attempt.
EMBED_TIMEOUT_SECONDS = 10

#: Error fragments that indicate a retryable (as opposed to permanent) failure.
_TRANSIENT_MARKERS = (
    "429",
    "rate limit",
    "quota",
    "resource has been exhausted",
    "resource_exhausted",
    "503",
    "500",
    "unavailable",
    "deadline",
    "timeout",
    "temporarily",
)


def _is_transient(exc: Exception) -> bool:
    blob = f"{type(exc).__name__}: {exc}".lower()
    return any(marker in blob for marker in _TRANSIENT_MARKERS)


def _is_retired_model(exc: Exception) -> bool:
    """True when Google reports the configured model as gone.

    Google retires Gemini models on a rolling basis, so this surfaces a
    message that names the setting to change instead of a raw 404.
    """
    blob = f"{exc}".lower()
    return "404" in blob and (
        "no longer available" in blob
        or "is not found" in blob
        or "not supported for" in blob
    )


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


def _request_options(timeout: float) -> Any:
    """Per-call deadline for the SDK, or None if this SDK cannot express one.

    ``google-generativeai`` delegates to google-api-core, whose default retry
    policy runs to a 600s deadline. Every network call this module makes sits
    inside a user's HTTP request, so an unbounded deadline turns a transient
    Google-side slowdown into a client-side timeout with no diagnostic.
    """
    try:
        from google.generativeai.types import helper_types
    except ImportError:  # pragma: no cover - very old SDK
        return None
    return helper_types.RequestOptions(timeout=timeout)


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


def embed(text: str, *, max_attempts: int | None = None) -> Optional[list[float]]:
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

    def _call() -> Any:
        opts = _request_options(EMBED_TIMEOUT_SECONDS)
        try:
            return genai.embed_content(
                model=model,
                content=text,
                output_dimensionality=dim,
                request_options=opts,
            )
        except TypeError as exc:
            # Only a rejected kwarg justifies a retry; anything else is real.
            blob = str(exc)
            if "output_dimensionality" not in blob and "request_options" not in blob:
                raise
            try:
                return genai.embed_content(
                    model=model, content=text, request_options=opts
                )
            except TypeError as exc2:
                if "request_options" not in str(exc2):
                    raise
                return genai.embed_content(model=model, content=text)

    # Free-tier keys are rate limited; a burst of ingestion calls otherwise
    # loses most chunks. Retry transient failures with a short backoff.
    #
    # Callers on a user-facing request path must pass a small max_attempts:
    # the full budget blocks for 1.5+3+6 = 10.5s, which is latency a student
    # waiting on a chat reply should never pay. Retrieval degrades to keyword
    # search when this returns None, so failing fast is cheap.
    attempts = EMBED_MAX_ATTEMPTS if max_attempts is None else max(1, max_attempts)
    last: Exception | None = None
    for attempt in range(attempts):
        try:
            vector = _vector_of(_call())
            break
        except Exception as exc:  # noqa: BLE001
            last = exc
            if not _is_transient(exc) or attempt == attempts - 1:
                log.warning("embedding failed: %s", exc)
                return None
            delay = EMBED_BACKOFF_SECONDS * (2**attempt)
            log.info(
                "embedding rate limited (attempt %d/%d), retrying in %.1fs",
                attempt + 1,
                attempts,
                delay,
            )
            time.sleep(delay)
    else:  # pragma: no cover - loop always breaks or returns
        log.warning("embedding failed: %s", last)
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

    def _call() -> Any:
        opts = _request_options(CHAT_TIMEOUT_SECONDS)
        if opts is None:
            return model.generate_content(contents)
        try:
            return model.generate_content(contents, request_options=opts)
        except TypeError as exc:
            # Only treat this as "SDK too old" when the kwarg itself is
            # rejected. A TypeError raised *inside* the call is a real error and
            # must not be retried into a second, unbounded request.
            if "request_options" not in str(exc):
                raise
            return model.generate_content(contents)

    try:
        response = _call()
    except Exception as exc:  # noqa: BLE001
        if _is_retired_model(exc):
            raise GeminiUnavailable(
                f"The configured chat model '{settings.gemini_chat_model}' has been "
                "retired by Google. Update GEMINI_CHAT_MODEL in your .env "
                f"(details: {exc})"
            ) from exc
        raise
    return (getattr(response, "text", "") or "").strip()


__all__ = ["embed", "generate", "is_configured", "GeminiUnavailable"]
