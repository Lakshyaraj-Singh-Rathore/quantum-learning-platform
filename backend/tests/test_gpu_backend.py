"""CUDA-Q backend wiring, per-backend limits, and the thermal guard.

The GPU execution path itself cannot be exercised without a GPU, so these
tests cover everything around it: that the backend degrades cleanly when
CUDA-Q is absent, that the GPU gets its own qubit ceiling, and that the
thermal guard behaves -- including failing OPEN when temperature cannot be
read, which matters because refusing to simulate over missing telemetry would
be worse than the risk it guards.
"""

from __future__ import annotations

import importlib.util

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


def _fake_cudaq(monkeypatch, *target_names):
    """Stand in for an installed-but-headless CUDA-Q wheel.

    sys.modules injection means these tests behave identically whether or not
    the real cudaq package is installed in the environment running them.
    """
    import sys
    import types

    fake = types.SimpleNamespace(
        get_targets=lambda: [
            types.SimpleNamespace(name=n) for n in target_names
        ],
    )
    monkeypatch.setitem(sys.modules, "cudaq", fake)


def test_installed_wheel_without_a_device_is_not_available(monkeypatch):
    """get_targets() lists targets compiled into the wheel, not hardware.

    Regression: on a CPU-only Linux box, `pip install cudaq` advertises an
    nvidia target, so the backend used to claim availability and then fail
    every job with a raw "CUDA driver version is insufficient" error. The
    gate is the device count, which reports 0 with no GPU present.
    """
    _fake_cudaq(monkeypatch, "nvidia", "qpp-cpu")
    monkeypatch.setattr(cudaq_sim, "_gpu_device_count", lambda: 0)
    available, reason = cudaq_sim.is_available()
    assert not available
    assert "0 devices" in reason


def test_unknown_device_count_defers_to_the_target_list(monkeypatch):
    """Fail-open on missing telemetry, the same rule the thermal guard follows:
    older CUDA-Q builds without num_available_gpus() must not be locked out."""
    _fake_cudaq(monkeypatch, "nvidia")
    monkeypatch.setattr(cudaq_sim, "_gpu_device_count", lambda: None)
    assert cudaq_sim.is_available() == (True, "")


def test_no_nvidia_target_is_still_refused_even_with_devices(monkeypatch):
    _fake_cudaq(monkeypatch, "qpp-cpu")
    monkeypatch.setattr(cudaq_sim, "_gpu_device_count", lambda: 1)
    available, reason = cudaq_sim.is_available()
    assert not available
    assert "no GPU target" in reason


@pytest.mark.skipif(
    importlib.util.find_spec("cudaq") is None,
    reason="needs the real cudaq wheel installed",
)
def test_real_wheel_without_a_gpu_does_not_advertise_availability():
    """The exact failure mode seen on a GPU-less machine running the wheel."""
    import cudaq

    if cudaq.num_available_gpus() > 0:  # pragma: no cover - GPU machine
        pytest.skip("this machine actually has a CUDA GPU")
    available, reason = cudaq_sim.is_available()
    assert not available
    assert "GPU" in reason


# --------------------------------------------------------- bit-order conventions
def test_counts_map_cuda_qubit_order_onto_qiskit_order():
    """Pin the endianness convention without needing a GPU.

    Verified against CUDA-Q 0.16: `x` on qubit 0 of a 2-qubit register samples
    the bitstring "10" -- qubit 0 LEFTMOST, the opposite of Qiskit. The
    backend must hand back "01" so histograms align across engines.
    """
    ir = CircuitIR.from_dict({
        "n_qubits": 2, "n_clbits": 2,
        "ops": [{"kind": "gate", "gate": "x", "qubits": [0], "layer": 0}],
    })
    counts = cudaq_sim._counts_from_sample({"10": 100}, ir, {0: 0, 1: 1})
    assert counts == {"01": 100}


def test_measured_bit_lands_on_its_clbit_not_its_qubit():
    """q0 measured into clbit 1 must fill the clbit position.

    CUDA-Q reports the whole register, qubit 0 leftmost: "10" here means q0
    is set. The IR pads n_clbits up to n_qubits, so unmeasured clbits stay 0.
    A backend that confused qubit positions with clbit positions would give
    "01".
    """
    ir = CircuitIR.from_dict({
        "n_qubits": 2, "n_clbits": 2,
        "ops": [{"kind": "measure", "qubits": [0], "clbits": [1], "layer": 0}],
    })
    assert cudaq_sim._counts_from_sample({"10": 7}, ir, {0: 1}) == {"10": 7}
    # And the reverse mapping must flip where the bit lands.
    assert cudaq_sim._counts_from_sample({"10": 7}, ir, {0: 0}) == {"01": 7}


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


# --------------------------------------------------- state views + sampling
def _install_fake_cudaq_engine(monkeypatch):
    """Stand in for the whole cudaq surface run() touches.

    Enough fidelity to exercise the adapter's bookkeeping -- kernel replay,
    get_state vs sample policy, count mapping -- on machines with no GPU,
    while counting calls so policy can be asserted, not just outcome.
    """
    import contextlib
    import sys
    import types

    calls = {"get_state": 0, "sample": 0, "noise_samples": 0, "noise_channels": 0,
             "targets": []}

    class _Qubits:
        def __getitem__(self, i):
            return i

    class _Kernel:
        def qalloc(self, n):
            return _Qubits()

        def rx(self, theta, q):
            pass
        ry = rx
        rz = rx

        def cx(self, control, target):
            pass

        def mz(self, q):
            # Real CUDA-Q records the measurement into a handle; the
            # bookkeeping under test only cares that it exists to attach a
            # readout channel to.
            pass

    class _Channel:
        def __init__(self, p):
            self.p = p

    class _NoiseModel:
        def add_all_qubit_channel(self, gate, channel):
            calls["noise_channels"] += 1

    def get_state(kernel):
        calls["get_state"] += 1
        s = 2 ** -0.5
        return [complex(s), 0j, 0j, complex(s)]

    def sample(kernel, shots_count=1024, noise_model=None):
        calls["sample"] += 1
        if noise_model is not None:
            calls["noise_samples"] += 1
        return {"00": shots_count // 2, "11": shots_count - shots_count // 2}

    def set_target(*a, **k):
        calls["targets"].append(a[0] if a else k.get("target"))

    fake = types.SimpleNamespace(
        make_kernel=_Kernel,
        get_state=get_state,
        sample=sample,
        set_target=set_target,
        set_random_seed=lambda s: None,
        get_targets=lambda: [types.SimpleNamespace(name="nvidia")],
        num_available_gpus=lambda: 1,
        NoiseModel=_NoiseModel,
        AmplitudeDampingChannel=_Channel,
        PhaseFlipChannel=_Channel,
        BitFlipChannel=_Channel,
    )
    monkeypatch.setitem(sys.modules, "cudaq", fake)
    # Bypass the thermal guard: this tests translation policy, not the slot.
    monkeypatch.setattr(cudaq_sim, "gpu_slot",
                        lambda **kw: contextlib.nullcontext())
    monkeypatch.setattr(cudaq_sim, "is_available", lambda: (True, ""))
    return calls


def _bell_measured() -> CircuitIR:
    return CircuitIR.from_dict({
        "n_qubits": 2, "n_clbits": 2,
        "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0],
             "layer": 1},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
            {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
        ],
    })


def test_measured_circuit_still_returns_stateviews(monkeypatch):
    """Parity with Aer/Cirq/PennyLane: state views are the ideal
    pre-measurement state. A measure op in the IR must not blank the
    Bloch sphere -- the kernel builder drops measures anyway."""
    calls = _install_fake_cudaq_engine(monkeypatch)
    result = cudaq_sim.run(_bell_measured(), shots=100)
    assert calls["get_state"] == 1 and calls["sample"] == 1
    assert len(result["statevector"]) == 4
    assert result["counts"] == {"00": 50, "11": 50}


def test_unmeasured_circuit_measures_everything(monkeypatch):
    """An empty histogram was a CUDA-Q-only quirk; every other engine
    auto-measures all qubits, so this one does too, with their warning."""
    _install_fake_cudaq_engine(monkeypatch)
    result = cudaq_sim.run(_circuit(2), shots=50)
    assert result["counts"] == {"00": 25, "11": 25}
    assert any("measured all qubits automatically" in w
               for w in result["metadata"]["warnings"])


def test_stateviews_capped_at_the_platforms_payload_budget(monkeypatch):
    """2**n amplitudes out of VRAM into a JSON job row is a worker OOM,
    not a feature -- above the CPU engines' ceiling the run is counts-only,
    loudly. get_state must not even be called."""
    calls = _install_fake_cudaq_engine(monkeypatch)
    big = CircuitIR.from_dict({
        "n_qubits": 21, "n_clbits": 21,
        "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
        ],
    })
    result = cudaq_sim.run(big, shots=10)
    assert calls["get_state"] == 0
    assert not result["statevector"]
    assert result["counts"]
    assert any("omitted" in w for w in result["metadata"]["warnings"])


# --------------------------------------------------------------------------- #
# Noise on CUDA-Q: NoiseModel channels for the pulses, readout as a channel on
# mz, and an ideal twin run so the Ideal-vs-noisy tab has both histories from
# THIS engine. Bookkeeping against the fake; the channel physics itself is
# CUDA-Q's, exercised on real hardware and cross-checked against its own
# density-matrix reference below.
# --------------------------------------------------------------------------- #
def _noise_params(**kw):
    from app.quantum.noise import NoiseParams

    base = dict(enabled=True, t1_us=50.0, t2_us=30.0, readout_error=0.02)
    base.update(kw)
    return NoiseParams(**base)


def test_noisy_run_attaches_real_channels_and_both_histories(monkeypatch):
    calls = _install_fake_cudaq_engine(monkeypatch)
    result = cudaq_sim.run(_bell_measured(), shots=100, noise=_noise_params())

    assert calls["noise_samples"] == 1  # exactly one sampling carries the model
    assert calls["sample"] == 2         # ...and the ideal twin runs without it
    assert calls["noise_channels"] >= 10
    assert calls["targets"].count("density-matrix-cpu") >= 1

    meta = result["metadata"]
    assert meta["noise"] == {
        "enabled": True, "t1_us": 50.0, "t2_us": 30.0, "readout_error": 0.02,
    }
    # The fake ignores the channels, so noisy and ideal agree -- proving the
    # two histograms come from the same kernel, not from a re-parameterization.
    assert result["counts"] == meta["ideal_counts"] == {"00": 50, "11": 50}
    assert meta["metrics"]["total_variation"] == pytest.approx(0.0)
    assert meta["metrics"]["shot_leakage"] == pytest.approx(0.0)
    assert meta["mode"] == "static"
    assert "density-matrix" in meta["target"]

    warnings = meta["warnings"]
    assert any("teaching approximation" in w for w in warnings)
    assert any("IDEAL state" in w for w in warnings)       # statevector caveat
    assert any("density-matrix" in w for w in warnings)     # where noise ran
    assert any("Fidelity/purity" in w for w in warnings)    # omitted, explained


def test_noiseless_run_reports_perfect_metrics_and_skips_dm_target(monkeypatch):
    calls = _install_fake_cudaq_engine(monkeypatch)
    result = cudaq_sim.run(_bell_measured(), shots=100, noise=_noise_params(enabled=False))
    meta = result["metadata"]
    assert meta["noise"]["enabled"] is False
    assert meta["ideal_counts"] is None
    assert meta["metrics"]["fidelity"] == 1.0
    assert meta["metrics"]["purity"] == 1.0
    assert calls["sample"] == 1
    assert "density-matrix-cpu" not in calls["targets"]
    assert calls["noise_channels"] == 0


def test_noisy_run_above_density_matrix_cap_is_refused_early(monkeypatch):
    """The refusal must explain the physics and the alternative, not just say
    'too big' -- and it must happen before any simulation starts."""
    _install_fake_cudaq_engine(monkeypatch)
    big = CircuitIR.from_dict({
        "n_qubits": cudaq_sim.NOISE_MAX_QUBITS + 1,
        "n_clbits": cudaq_sim.NOISE_MAX_QUBITS + 1,
        "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
        ],
    })
    with pytest.raises(BackendError, match="density-matrix"):
        cudaq_sim.run(big, shots=10, noise=_noise_params())


@pytest.mark.skipif(importlib.util.find_spec("cudaq") is None,
                    reason="needs the real CUDA-Q wheel (any Linux; no GPU)")
def test_cudaq_noise_channels_match_independent_reference():
    """Physics gate against the REAL package on CUDA-Q's own density-matrix
    engine: full amplitude damping after X must empty |1>, and two chained
    50% channels must leave P(1) = 0.25 -- sequential composition, exactly
    what the thermal model above assumes. Both numbers are hand-derivable
    from the channel definitions, not tuned to the implementation."""
    import cudaq

    cudaq.set_target("density-matrix-cpu")
    k = cudaq.make_kernel()
    q = k.qalloc(1)
    k.x(q[0])
    k.mz(q[0])

    nm = cudaq.NoiseModel()
    nm.add_all_qubit_channel("x", cudaq.AmplitudeDampingChannel(1.0))
    counts = dict(cudaq.sample(k, noise_model=nm, shots_count=300).items())
    assert counts.get("0", 0) == 300  # every shot decayed to ground

    nm2 = cudaq.NoiseModel()
    nm2.add_all_qubit_channel("x", cudaq.AmplitudeDampingChannel(0.5))
    nm2.add_all_qubit_channel("x", cudaq.AmplitudeDampingChannel(0.5))
    c2 = dict(cudaq.sample(k, noise_model=nm2, shots_count=4000).items())
    p1 = c2.get("1", 0) / 4000
    assert abs(p1 - 0.25) < 0.05  # two half-dampings compose sequentially
