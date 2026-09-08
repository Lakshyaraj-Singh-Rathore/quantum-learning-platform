"""Authentication and role-based authorization."""

import pytest


def test_register_login_and_me(client):
    email = "auth-flow@example.com"
    registered = client.post("/auth/register", json={"email": email, "password": "pw123456"})
    assert registered.status_code == 201
    body = registered.json()
    assert body["role"] == "student"
    assert body["access_token"]

    logged_in = client.post("/auth/login", json={"email": email, "password": "pw123456"})
    assert logged_in.status_code == 200

    headers = {"Authorization": f"Bearer {logged_in.json()['access_token']}"}
    me = client.get("/auth/me", headers=headers).json()
    assert me["email"] == email
    assert me["role"] == "student"


def test_duplicate_registration_rejected(client):
    payload = {"email": "dupe@example.com", "password": "pw123456"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 400


def test_wrong_password_rejected(client):
    client.post("/auth/register", json={"email": "wrongpw@example.com", "password": "pw123456"})
    response = client.post(
        "/auth/login", json={"email": "wrongpw@example.com", "password": "nope1234"}
    )
    assert response.status_code == 401


def test_role_cannot_be_escalated_at_registration(client):
    response = client.post(
        "/auth/register",
        json={"email": "sneaky@example.com", "password": "pw123456", "role": "admin"},
    )
    assert response.json()["role"] == "student"


def test_protected_endpoints_require_a_token(client):
    assert client.get("/jobs").status_code == 401
    assert client.get("/auth/me").status_code == 401
    assert client.post("/ai/chat", json={"message": "hi"}).status_code == 401


def test_invalid_token_rejected(client):
    headers = {"Authorization": "Bearer not-a-real-token"}
    assert client.get("/auth/me", headers=headers).status_code == 401


def test_instructor_dashboard_is_role_gated(client, student_headers):
    assert client.get("/dashboard/instructor", headers=student_headers).status_code == 403

    login = client.post(
        "/auth/login", json={"email": "instructor@local.dev", "password": "instructor123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.get("/dashboard/instructor", headers=headers)
    assert response.status_code == 200
    assert "total_students" in response.json()


def test_gemini_embed_model_name_is_qualified():
    """The SDK rejects a bare embedding model id.

    Regression: GEMINI_EMBED_MODEL=text-embedding-004 made every embedding
    call fail with "Model names should start with 'models/'", leaving the RAG
    corpus unembedded while the app still reported a healthy startup.
    """
    from app.ai.gemini_client import _qualified_model

    assert _qualified_model("text-embedding-004") == "models/text-embedding-004"
    # already-qualified names must not be double-prefixed
    assert _qualified_model("models/text-embedding-004") == "models/text-embedding-004"
    assert _qualified_model("tunedModels/x") == "tunedModels/x"
    assert _qualified_model("  text-embedding-004  ") == "models/text-embedding-004"


def test_embed_always_matches_configured_dimension(monkeypatch):
    """Embeddings must fit the content_chunks.embedding column.

    Regression: text-embedding-004 (768 dims) was shut down by Google on
    2026-01-14. Its replacement gemini-embedding-001 returns 3072 dims, which
    would not fit the schema, so embed() requests output_dimensionality and
    truncates if the model ignores it.
    """
    import app.ai.gemini_client as gc
    from app.config import get_settings

    dim = get_settings().embedding_dim

    class Fake:
        def __init__(self, dims, accept):
            self.dims, self.accept = dims, accept

        def embed_content(self, model, content, output_dimensionality=None):
            if output_dimensionality is not None and not self.accept:
                raise TypeError("unexpected keyword")
            n = output_dimensionality if (output_dimensionality and self.accept) else self.dims
            return {"embedding": [0.5] * n}

    for dims, accept in ((3072, True), (3072, False), (dim, True)):
        monkeypatch.setattr(gc, "_client", lambda d=dims, a=accept: Fake(d, a))
        vector = gc.embed("hello")
        assert vector is not None
        assert len(vector) == dim


def test_embed_retries_transient_errors_only(monkeypatch):
    """Free-tier keys rate limit ingestion bursts.

    Regression: a burst of embedding calls hit 429s and silently lost 15 of 23
    chunks, leaving RAG partially on the keyword fallback. Transient failures
    must be retried; permanent ones must fail fast.
    """
    import app.ai.gemini_client as gc
    from app.config import get_settings

    monkeypatch.setattr(gc, "EMBED_BACKOFF_SECONDS", 0.0)
    dim = get_settings().embedding_dim

    class Fake:
        def __init__(self, fails, exc):
            self.calls, self.fails, self.exc = 0, fails, exc

        def embed_content(self, model, content, output_dimensionality=None):
            self.calls += 1
            if self.calls <= self.fails:
                raise self.exc
            return {"embedding": [0.5] * (output_dimensionality or dim)}

    # transient: recovers, and the vector still matches the schema
    fake = Fake(2, Exception("429 Resource has been exhausted (quota)"))
    monkeypatch.setattr(gc, "_client", lambda: fake)
    assert len(gc.embed("hi")) == dim
    assert fake.calls == 3

    # permanent: no retry storm
    fake = Fake(99, Exception("404 model not found"))
    monkeypatch.setattr(gc, "_client", lambda: fake)
    assert gc.embed("hi") is None
    assert fake.calls == 1

    # transient but persistent: bounded retries
    fake = Fake(99, Exception("429 rate limit"))
    monkeypatch.setattr(gc, "_client", lambda: fake)
    assert gc.embed("hi") is None
    assert fake.calls == gc.EMBED_MAX_ATTEMPTS


def test_ingestion_rechunks_a_stale_split(tmp_path, monkeypatch):
    """A stored split that no longer matches the chunker must be rebuilt.

    Regression: an early build stored one chunk per lesson. Because ingestion
    skipped any lesson that already had chunks, that coarse split persisted
    forever and retrieval returned whole lessons instead of focused passages.
    """
    import app.ai.rag as rag
    from app.database import SessionLocal
    from app.models.content import ContentChunk
    from sqlalchemy import func, select

    lesson = tmp_path / "demo.md"
    lesson.write_text(
        "\n".join(f"## Section {i}\n\n{'body text ' * 120}" for i in range(4)),
        encoding="utf-8",
    )
    expected = len(rag.chunk_markdown(lesson.read_text(encoding="utf-8")))
    assert expected > 1, "fixture must split into several chunks"

    monkeypatch.setattr(rag, "is_configured", lambda: True)
    monkeypatch.setattr(rag, "embed", lambda text: None)

    db = SessionLocal()
    try:
        db.query(ContentChunk).filter(ContentChunk.lesson_slug == "demo").delete()
        # seed the stale state: the whole lesson as a single chunk
        db.add(
            ContentChunk(
                lesson_slug="demo",
                chunk_index=0,
                text=lesson.read_text(encoding="utf-8"),
                tags=[],
                embedding=None,
            )
        )
        db.commit()

        rag.ingest_content_folder(db, folder=str(tmp_path))
        count = db.scalar(
            select(func.count()).select_from(ContentChunk).where(
                ContentChunk.lesson_slug == "demo"
            )
        )
        assert count == expected

        # and it must not churn on the next run
        rag.ingest_content_folder(db, folder=str(tmp_path))
        assert count == db.scalar(
            select(func.count()).select_from(ContentChunk).where(
                ContentChunk.lesson_slug == "demo"
            )
        )
    finally:
        db.query(ContentChunk).filter(ContentChunk.lesson_slug == "demo").delete()
        db.commit()
        db.close()


def test_retired_chat_model_names_the_setting(monkeypatch):
    """A retired model must point at GEMINI_CHAT_MODEL, not leak a raw 404.

    Regression: gemini-2.0-flash was retired and the tutor surfaced
    "temporarily unavailable (NotFound: 404 ...)", which reads like an outage
    rather than a one-line config change.
    """
    import app.ai.gemini_client as gc

    message = (
        "404 This model models/gemini-2.0-flash is no longer available. "
        "Please update your code to use models/gemini-3.6-flash."
    )
    assert gc._is_retired_model(Exception(message))
    assert not gc._is_retired_model(Exception("429 rate limit exceeded"))
    assert not gc._is_retired_model(Exception("500 internal error"))

    class FakeModel:
        def __init__(self, *a, **k):
            pass

        def generate_content(self, contents):
            raise RuntimeError(message)

    class FakeGenAI:
        GenerativeModel = FakeModel

    monkeypatch.setattr(gc, "_client", lambda: FakeGenAI())
    with pytest.raises(gc.GeminiUnavailable) as excinfo:
        gc.generate("hello")
    assert "GEMINI_CHAT_MODEL" in str(excinfo.value)


def test_chat_retrieval_does_not_block_on_rate_limits(monkeypatch):
    """Interactive retrieval must fail fast, not burn the retry budget.

    Regression: embed() retries transient 429s with 1.5+3+6s of backoff. That
    is correct for background ingestion, but rag.retrieve() runs inside a
    user's chat request, so a rate-limited key added ~10.5s to every question
    before Gemini was even contacted -- enough to hit the client timeout.
    """
    import time

    import app.ai.gemini_client as gc

    class RateLimited:
        def embed_content(self, model, content, output_dimensionality=None):
            raise RuntimeError("429 Resource has been exhausted (quota)")

    monkeypatch.setattr(gc, "_client", lambda: RateLimited())

    started = time.monotonic()
    assert gc.embed("hello", max_attempts=1) is None
    assert time.monotonic() - started < 0.5, "interactive embed must not sleep"

    # the ingestion path keeps the full budget
    assert gc.EMBED_MAX_ATTEMPTS > 1


def test_chat_and_embed_calls_are_deadline_bounded(monkeypatch):
    """Every Gemini call must carry a timeout.

    Regression: google-generativeai delegates to google-api-core, whose default
    retry policy runs to a 600s deadline. Both calls sit inside a user's HTTP
    request, so an unbounded deadline let the Streamlit client hit its own 60s
    timeout and report 'Cannot reach the API ... is the backend running?' while
    the backend was healthy and still waiting on Google.
    """
    import app.ai.gemini_client as gc

    seen = {}

    class FakeResp:
        text = "ok"

    class FakeModel:
        def __init__(self, *a, **k):
            pass

        def generate_content(self, contents, request_options=None):
            seen["chat"] = request_options
            return FakeResp()

    class FakeGenai:
        GenerativeModel = FakeModel

        def embed_content(self, model, content, output_dimensionality=None,
                          request_options=None):
            seen["embed"] = request_options
            return {"embedding": [0.0] * output_dimensionality}

    monkeypatch.setattr(gc, "_client", lambda: FakeGenai())

    gc.generate("hi")
    gc.embed("hi")

    for key in ("chat", "embed"):
        opts = seen[key]
        assert opts is not None, f"{key} call passed no request_options"
        assert getattr(opts, "timeout", None), f"{key} call has no timeout"
        assert opts.timeout <= 60, f"{key} timeout must beat the 60s client budget"
