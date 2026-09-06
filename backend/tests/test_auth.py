"""Authentication and role-based authorization."""


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
