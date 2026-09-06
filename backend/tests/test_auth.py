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
