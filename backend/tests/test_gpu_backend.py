"""CUDA-Q backend wiring, per-backend limits, and the thermal guard.

The GPU execution path itself cannot be exercised without a GPU, so these
tests cover everything around it: that the backend degrades cleanly when
CUDA-Q is absent, that the GPU gets its own qubit ceiling, and that the
thermal guard behaves -- including failing OPEN when temperature cannot be
read, which matters because refusing to simulate over missing telemetry would
be worse than the risk it guards.
"""

from __future__ import annotations

import pytest

from app.quantum.backends import cudaq_sim, gpu_guard
from app.quantum.backends.base import BackendError, static_qubit_limit
from app.quantum.ir import CircuitIR


def _circuit(n: int) -> CircuitIR:
    return CircuitIR.from_dict({
        "n_qubits": n, "n_clbits": n,
        "ops": [{"kind": "gate", "gate": "h", "qubits": [0], "layer": 0}],
    })


# ------------------------------------------------------- per-backend limits
def test_cpu_backends_share_the_ram_ceiling():
    for backend in ("qiskit_aer", "cirq", "pennylane"):
        assert static_qubit_limit(backend) == 20


def test_gpu_gets_its_own_ceiling():
    """VRAM is a different budget from system RAM, so one limit cannot serve."""
    assert static_qubit_limit("cudaq") == 28
    assert static_qubit_limit("cudaq") != static_qubit_limit("qiskit_aer")


def test_unknown_backend_falls_back_to_the_cpu_ceiling():
    assert static_qubit_limit("something_else") == 20
    assert static_qubit_limit("") == 20


def test_gpu_ceiling_fits_a_six_gb_card_in_both_precisions():
    """Measured on a mobile RTX 4050: 6141 MiB total, 84 MiB used.

    The ceiling must fit fp64 as well as fp32, otherwise selecting double
    precision would OOM at a qubit count the UI advertises as supported.
    """
    limit = static_qubit_limit("cudaq")
    free_bytes = (6141 - 84) * 1024**2
    for per_amplitude in (8, 16):          # fp32, fp64
        needed = (2**limit) * per_amplitude * 1.15   # +15% workspace
        assert needed < free_bytes, f"{limit}q at {per_amplitude}B does not fit"


# ------------------------------------------------------------ availability
def test_backend_reports_why_it_is_unavailable():
    """Without CUDA-Q it must explain itself, not fail later at submit."""
    available, reason = cudaq_sim.is_available()
    if not available:
        assert reason
        assert "CUDA-Q" in reason


def test_run_refuses_cleanly_without_cuda(monkeypatch):
    monkeypatch.setattr(cudaq_sim, "is_available", lambda: (False, "no GPU here"))
    with pytest.raises(BackendError) as exc:
        cudaq_sim.run(_circuit(4))
    assert "no GPU here" in str(exc.value)


def test_backend_is_registered():
    from app.workers.tasks import STATIC_RUNNERS

    assert "cudaq" in STATIC_RUNNERS


def test_backend_appears_in_the_catalogue(client, student_headers):
    response = client.get("/backends", headers=student_headers)
    assert response.status_code == 200
    ids = {b["id"] for b in response.json()["backends"]}
    assert "cudaq" in ids


def test_catalogue_entry_carries_a_reason_when_unavailable(client, student_headers):
    entry = next(
        b for b in client.get("/backends", headers=student_headers).json()["backends"]
        if b["id"] == "cudaq"
    )
    if not entry["available"]:
        assert entry["reason"], "an unavailable backend must say why"


# ------------------------------------------------------------- thermal guard
def test_temperature_read_failure_is_not_fatal(monkeypatch):
    """nvidia-smi has a limited feature set under WSL2; missing data is normal."""
    monkeypatch.setattr(gpu_guard, "gpu_temperature_c", lambda: None)
    ok, reason = gpu_guard.check_thermal(80)
    assert ok is True
    assert reason == ""


def test_hot_gpu_is_refused(monkeypatch):
    monkeypatch.setattr(gpu_guard, "gpu_temperature_c", lambda: 85)
    ok, reason = gpu_guard.check_thermal(80)
    assert ok is False
    assert "85" in reason and "Aer" in reason


def test_cool_gpu_is_allowed(monkeypatch):
    monkeypatch.setattr(gpu_guard, "gpu_temperature_c", lambda: 55)
    assert gpu_guard.check_thermal(80) == (True, "")


def test_the_limit_is_inclusive(monkeypatch):
    """At exactly the limit, refuse -- the card is already at the ceiling."""
    monkeypatch.setattr(gpu_guard, "gpu_temperature_c", lambda: 80)
    ok, _ = gpu_guard.check_thermal(80)
    assert ok is False


def test_zero_limit_disables_the_check(monkeypatch):
    monkeypatch.setattr(gpu_guard, "gpu_temperature_c",
                        lambda: pytest.fail("should not probe when disabled"))
    assert gpu_guard.check_thermal(0) == (True, "")


# ------------------------------------------------------------ concurrency
def test_only_one_gpu_job_at_a_time(monkeypatch):
    monkeypatch.setattr(gpu_guard, "gpu_temperature_c", lambda: 50)
    with gpu_guard.gpu_slot(temp_limit_c=80, cooldown=0):
        with pytest.raises(RuntimeError) as exc:
            with gpu_guard.gpu_slot(temp_limit_c=80, cooldown=0):
                pass
    assert "already running" in str(exc.value)


def test_the_slot_is_released_after_use(monkeypatch):
    monkeypatch.setattr(gpu_guard, "gpu_temperature_c", lambda: 50)
    with gpu_guard.gpu_slot(temp_limit_c=80, cooldown=0):
        pass
    # Must be acquirable again immediately when cooldown is off.
    with gpu_guard.gpu_slot(temp_limit_c=80, cooldown=0):
        pass


def test_the_slot_is_released_even_when_the_body_raises(monkeypatch):
    monkeypatch.setattr(gpu_guard, "gpu_temperature_c", lambda: 50)
    with pytest.raises(ValueError):
        with gpu_guard.gpu_slot(temp_limit_c=80, cooldown=0):
            raise ValueError("boom")
    with gpu_guard.gpu_slot(temp_limit_c=80, cooldown=0):
        pass


def test_cooldown_blocks_back_to_back_runs(monkeypatch):
    """The real risk is a learner pressing Run repeatedly, not one long job."""
    monkeypatch.setattr(gpu_guard, "gpu_temperature_c", lambda: 50)
    with gpu_guard.gpu_slot(temp_limit_c=80, cooldown=0):
        pass
    with pytest.raises(RuntimeError) as exc:
        with gpu_guard.gpu_slot(temp_limit_c=60, cooldown=30):
            pass
    assert "cooling down" in str(exc.value)


def test_cooldown_of_zero_never_blocks(monkeypatch):
    monkeypatch.setattr(gpu_guard, "gpu_temperature_c", lambda: 50)
    assert gpu_guard.seconds_until_ready(0) == 0.0


# --------------------------------------------------------- gate translation
def test_only_the_portable_basis_is_accepted():
    """normalize() emits rx/ry/rz/cx; anything else is a normalization bug."""
    assert cudaq_sim.SUPPORTED_GATES == {
        "rx", "ry", "rz", "cx", "measure", "barrier"
    }


def test_default_precision_is_single():
    """fp32 halves VRAM traffic, which roughly halves the heat."""
    assert cudaq_sim.DEFAULT_PRECISION == "fp32"
