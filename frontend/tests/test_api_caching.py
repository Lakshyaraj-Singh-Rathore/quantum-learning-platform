"""Read-only API calls must be memoised, and mutating ones must not be.

Streamlit re-runs the entire page on every interaction, and it executes the
body of every tab even when only one is visible. The Composer therefore fired
eight round-trips per gate drop -- backends, inspect, timeline, and four code
exports -- which is what made composing feel sluggish. Measured in one session:

    rerun 1: 9 HTTP calls, 708 ms
    rerun 2: 1 HTTP call,   62 ms

Caching is only safe for endpoints that are pure functions of their input.
Anything that creates a job, spends qBraid credits or writes to the database
must never be cached.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import api_client  # noqa: E402

CACHED = ["_backends_cached", "_inspect_cached", "_timeline_cached",
          "_export_qasm_cached", "_export_code_cached"]

# Submitting a job runs a simulation and, on qBraid, spends real credits.
MUST_NOT_CACHE = ["submit_job", "save_circuit", "import_qasm", "job_status",
                  "job_result", "ai_chat"]


def test_read_only_helpers_are_cached():
    for name in CACHED:
        fn = getattr(api_client, name, None)
        assert fn is not None, f"{name} is missing"
        assert hasattr(fn, "clear"), f"{name} is not wrapped in st.cache_data"


def test_mutating_calls_are_not_cached():
    for name in MUST_NOT_CACHE:
        fn = getattr(api_client, name, None)
        if fn is None:
            continue
        assert not hasattr(fn, "clear"), (
            f"{name} must not be cached: it has side effects "
            "(a job run, a credit spend, or a database write)"
        )


def test_cache_key_is_order_independent():
    a = {"n_qubits": 2, "ops": [], "n_clbits": 2}
    b = {"ops": [], "n_clbits": 2, "n_qubits": 2}
    assert api_client._key(a) == api_client._key(b)


def test_cache_key_distinguishes_different_circuits():
    a = {"n_qubits": 2, "n_clbits": 2, "ops": []}
    b = {"n_qubits": 3, "n_clbits": 3, "ops": []}
    assert api_client._key(a) != api_client._key(b)


def test_public_wrappers_still_exist():
    """The page calls these names; caching must be invisible to callers."""
    for name in ["backends", "inspect_circuit", "circuit_timeline",
                 "export_qasm", "export_code"]:
        assert callable(getattr(api_client, name))


def test_qbraid_warns_before_spending_credits():
    page = (ROOT / "pages" / "2_Composer.py").read_text()
    assert 'backend == "qbraid"' in page
    assert "credits" in page.lower()


def test_qbraid_wait_is_bounded_by_the_celery_budget():
    """Waiting 300 s under a 15 s task limit guaranteed a mid-flight kill."""
    tasks = (ROOT.parent / "backend" / "app" / "workers" / "tasks.py").read_text()
    assert 'engine == "qbraid"' in tasks
    assert "celery_soft_time_limit" in tasks
