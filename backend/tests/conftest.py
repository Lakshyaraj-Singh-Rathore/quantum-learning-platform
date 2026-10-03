"""Test fixtures: SQLite-backed API client with Celery running eagerly."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# The test suite is hermetic by default: it uses a throwaway SQLite file and
# overrides any developer .env / shell values so tests never touch a real
# database or hit remote providers.
#
# Opt-in override for cross-database verification. Setting
# QL_TEST_DATABASE_URL points the whole suite at a disposable PostgreSQL
# staging database instead. The default stays SQLite, so ordinary runs are
# unaffected -- and pointing this at anything production-like is never correct.
_PG_OVERRIDE = os.environ.get("QL_TEST_DATABASE_URL", "").strip()
if _PG_OVERRIDE:
    os.environ["DATABASE_URL"] = _PG_OVERRIDE
else:
    _DB_FILE = Path(tempfile.gettempdir()) / "quantumlearn_test.db"
    if _DB_FILE.exists():
        _DB_FILE.unlink()
    os.environ["DATABASE_URL"] = f"sqlite:///{_DB_FILE}"
os.environ["JWT_SECRET"] = "test-secret-key-that-is-long-enough-123456"
os.environ["GEMINI_API_KEY"] = ""
os.environ["QBRAID_API_KEY"] = ""
os.environ["QBRAID_DEVICE_ID"] = ""
os.environ["CONTENT_DIR"] = str(ROOT.parent / "content")


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.workers.celery_app import celery_app

    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = False

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def student_headers(client):
    response = client.post(
        "/auth/register",
        json={"email": "pytest-student@example.com", "password": "pw123456"},
    )
    if response.status_code != 201:
        response = client.post(
            "/auth/login",
            json={"email": "pytest-student@example.com", "password": "pw123456"},
        )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def bell_ir() -> dict:
    return {
        "name": "bell",
        "n_qubits": 2,
        "n_clbits": 2,
        "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "gate", "gate": "cx", "qubits": [0, 1], "layer": 1},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
            {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
        ],
    }


@pytest.fixture
def dynamic_ir() -> dict:
    return {
        "name": "dynamic",
        "n_qubits": 2,
        "n_clbits": 2,
        "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
            {
                "kind": "if",
                "condition": {"type": "bit_eq", "bit": 0, "value": 1},
                "body": [{"kind": "gate", "gate": "x", "qubits": [1]}],
                "layer": 2,
            },
            {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 3},
        ],
    }
