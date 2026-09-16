"""qBraid credential/device gating.

A .env line without a trailing newline silently merges into the next line, so
QBRAID_DEVICE_ID becomes "ionq:ionq:sim:simulatorCELERY_SOFT_TIME_LIMIT=8".
The backend used to accept that and advertise itself as available, then fail at
submit time with an opaque error from the qBraid API.
"""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.quantum.backends import qbraid_sim


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _available(monkeypatch, key: str, device: str):
    monkeypatch.setenv("QBRAID_API_KEY", key)
    monkeypatch.setenv("QBRAID_DEVICE_ID", device)
    get_settings.cache_clear()
    return qbraid_sim.is_available()


def test_no_key_is_disabled(monkeypatch):
    ok, reason = _available(monkeypatch, "", "ionq:ionq:sim:simulator")
    assert ok is False
    assert "QBRAID_API_KEY" in reason


def test_key_alone_is_enough(monkeypatch):
    """The device id defaults to the free IonQ simulator."""
    ok, reason = _available(monkeypatch, "qbr_fake", "ionq:ionq:sim:simulator")
    assert ok is True
    assert reason == ""


@pytest.mark.parametrize(
    "device",
    [
        "ionq:ionq:sim:simulator",
        "qbraid:qbraid:sim:qir",
        "aws:rigetti:qpu:ankaa-3",
    ],
)
def test_real_device_ids_are_accepted(monkeypatch, device):
    ok, _ = _available(monkeypatch, "qbr_fake", device)
    assert ok is True


def test_env_line_run_together_is_rejected(monkeypatch):
    """The exact malformed value a missing newline produces."""
    ok, reason = _available(
        monkeypatch, "qbr_fake", "ionq:ionq:sim:simulatorCELERY_SOFT_TIME_LIMIT=8"
    )
    assert ok is False
    assert "malformed" in reason
    assert "own line" in reason


def test_garbage_device_is_rejected(monkeypatch):
    ok, reason = _available(monkeypatch, "qbr_fake", "garbage")
    assert ok is False
    assert "malformed" in reason


def test_empty_device_asks_for_one(monkeypatch):
    ok, reason = _available(monkeypatch, "qbr_fake", "")
    assert ok is False
    assert "QBRAID_DEVICE_ID" in reason
