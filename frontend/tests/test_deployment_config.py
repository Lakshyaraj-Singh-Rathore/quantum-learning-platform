"""The deployment configuration must stay consistent with the code.

These are cheap checks for mistakes that are expensive to debug on a hosted
service, where the feedback loop is a five-minute redeploy:

* an env var named in render.yaml that the settings object does not read;
* the frontend growing a dependency on a simulator, blowing the 1 GB limit;
* losing the sys.path bootstrap that lets Streamlit Cloud import CircuitIR.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "frontend"))

RENDER = ROOT / "render.yaml"
ROOT_REQS = ROOT / "requirements.txt"
FRONT_REQS = ROOT / "frontend" / "requirements.txt"
CONFIG = ROOT / ".streamlit" / "config.toml"


def test_render_blueprint_exists():
    assert RENDER.is_file()


def test_render_runs_migrations_before_serving():
    text = RENDER.read_text()
    start = re.search(r"startCommand:\s*(.+)", text).group(1)
    assert "alembic upgrade head" in start
    assert start.index("alembic") < start.index("uvicorn")


def test_render_binds_the_injected_port():
    """Hardcoding 8000 would make the service unreachable on Render."""
    assert "--port $PORT" in RENDER.read_text()


def test_render_sets_the_small_instance_limits():
    text = RENDER.read_text()
    assert "CELERY_TASK_ALWAYS_EAGER" in text
    assert "MAX_STATIC_QUBITS" in text
    # 20 qubits peaks around 655 MB and would be OOM-killed on 512 MB.
    cap = re.search(r"MAX_STATIC_QUBITS\s*\n\s*value:\s*\"?(\d+)", text)
    assert cap and int(cap.group(1)) <= 16


def test_render_secrets_are_not_committed():
    text = RENDER.read_text()
    for secret in ("DATABASE_URL", "JWT_SECRET", "GEMINI_API_KEY", "QBRAID_API_KEY"):
        block = text.split(f"key: {secret}")[1][:60]
        assert "sync: false" in block, f"{secret} must be dashboard-managed"


@pytest.mark.parametrize(
    "name", ["DATABASE_URL", "JWT_SECRET", "GEMINI_API_KEY", "QBRAID_API_KEY",
             "API_CORS_ORIGINS", "MAX_STATIC_QUBITS", "CELERY_TASK_ALWAYS_EAGER"]
)
def test_every_render_env_var_is_read_by_settings(name):
    """A typo here fails silently: the setting just keeps its default."""
    from app.config import Settings

    assert name.lower() in Settings.model_fields


def _requirement_lines(text: str) -> list[str]:
    """Actual requirements, ignoring comments and blank lines."""
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def test_root_requirements_pull_in_the_frontend_only():
    """Streamlit Cloud installs the root file; it must not install qiskit."""
    lines = _requirement_lines(ROOT_REQS.read_text())
    assert any("frontend/requirements.txt" in line for line in lines)
    for heavy in ("qiskit", "cirq", "pennylane", "qbraid"):
        assert not any(heavy in line for line in lines)


def test_frontend_requirements_stay_light():
    lines = _requirement_lines(FRONT_REQS.read_text())
    for heavy in ("qiskit", "cirq", "pennylane", "qbraid"):
        assert not any(heavy in line.lower() for line in lines), (
            f"{heavy} in the frontend would blow the 1 GB Community Cloud limit"
        )


def test_frontend_needs_pydantic_for_circuit_ir():
    lines = _requirement_lines(FRONT_REQS.read_text())
    assert any("pydantic" in line for line in lines)


def test_streamlit_config_is_valid():
    text = CONFIG.read_text()
    # enableCORS=false with XSRF on is contradictory; Streamlit overrides it
    # and logs a warning on every boot.
    assert "enableCORS = false" not in text
    assert "headless = true" in text


def test_bootstrap_makes_the_backend_importable_without_pythonpath(monkeypatch):
    monkeypatch.delenv("PYTHONPATH", raising=False)
    from lib import bootstrap

    bootstrap.ensure_backend_on_path()
    import app.quantum.ir as ir

    assert ir.CircuitIR.__name__ == "CircuitIR"


def test_pages_that_need_the_backend_import_bootstrap_first():
    """composer.py imports app.* directly, so it must bootstrap first."""
    src = (ROOT / "frontend" / "lib" / "composer.py").read_text()
    assert src.index("from lib import bootstrap") < src.index("from app.quantum.ir")


def test_deployment_guide_exists():
    guide = ROOT / "docs" / "DEPLOYMENT.md"
    assert guide.is_file()
    text = guide.read_text()
    # The guide must warn about the traps that bite during a live demo.
    assert "Cold start" in text
    assert "expire" in text.lower()
