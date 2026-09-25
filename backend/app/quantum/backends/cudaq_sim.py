"""CUDA-Q GPU statevector backend.

Consumes the same portable transpiled circuit as every other static backend
(basis rx, ry, rz, cx) and replays it through CUDA-Q's kernel builder, so the
GPU runs the identical normalized program the CPU engines do. That is what
lets the cross-backend agreement tests treat this as just another engine.

Requires an NVIDIA GPU and ``pip install cudaq``. CUDA-Q has no native Windows
build -- on Windows it runs under WSL2 -- so this backend advertises itself as
unavailable rather than failing opaquely at submit time when either piece is
missing. "Missing" here means no usable device, not just a missing package:
``cudaq.get_targets()`` lists the targets compiled into the wheel, so a
CPU-only server with ``pip install cudaq`` still reports an ``nvidia`` target,
and the gate is the actual device count (see ``_gpu_device_count``).
See ``docs/CUDAQ_SETUP.md``.

Validated against CUDA-Q 0.16. Its wheel emits a FutureWarning that the
``sample``/``observe`` primitives will change in a future release; pin the
version until this adapter is ported to the new API.
"""

from __future__ import annotations

from typing import Any, Optional

from app.quantum.backends.base import (
    BackendError,
    Timer,
    guard_static_size,
    make_result,
    statevector_to_json,
)
from app.quantum.backends.gpu_guard import gpu_slot
from app.quantum.ir import CircuitIR
from app.quantum.normalize import measured_qubit_map, normalize

NAME = "cudaq"

#: fp32 halves VRAM traffic against fp64, which roughly halves the heat, and
#: four decimal places of probability is more than a teaching platform shows.
#: CUDA-Q's own nvidia target defaults to single precision as well.
DEFAULT_PRECISION = "fp32"

#: Noise is a density-matrix phenomenon: Kraus channels need rho (4^n
#: complex numbers), which no statevector simulator -- GPU or otherwise --
#: can hold. CUDA-Q ships a real density-matrix engine for exactly this, so
#: the noisy half of a run executes there while the GPU still provides the
#: ideal state views. The cap is what that CPU engine can simulate in a
#: job's time budget, not a software limitation of the platform.
NOISE_TARGET = "density-matrix-cpu"
NOISE_MAX_QUBITS = 11

#: Gate names in CUDA-Q's noise-model vocabulary. The static basis is
#: rx/ry/rz/cx; rz is a virtual-Z (zero-duration, no thermal error) on every
#: engine, matching app.quantum.noise's PULSE_1Q list. h/x/y are attached as
#: well so a kernel that reached us undecomposed still gets its pulses.
PULSE_GATES_1Q = ("rx", "ry", "h", "x", "y", "sx")
PULSE_GATES_2Q = ("cx",)

#: The normalization pass emits exactly these, so the translation below is
#: total rather than best-effort. Anything else is a bug in normalize(), not
#: an unsupported gate, and should surface loudly.
SUPPORTED_GATES = {"rx", "ry", "rz", "cx", "measure", "barrier"}


def _gpu_device_count() -> Optional[int]:
    """How many CUDA devices this process can see, or None if unknown.

    ``cudaq.get_targets()`` is not a hardware check: it lists targets built
    into the wheel. A GPU-less Linux box that merely ran ``pip install
    cudaq`` advertises the ``nvidia`` target, marks this backend available,
    and then fails every job with a raw "CUDA driver version is
    insufficient" RuntimeError. The device count is the honest probe; it is
    sub-millisecond, so no caching is warranted. Builds without the helper
    return None and we fall back to trusting the target list.
    """
    try:
        import cudaq

        return int(cudaq.num_available_gpus())
    except Exception:  # noqa: BLE001 - missing API or a broken driver
        return None


def is_available() -> tuple[bool, str]:
    """Is CUDA-Q installed with a usable GPU target and a real device?

    Mirrors the qBraid gating pattern: return a reason the UI can display,
    rather than letting a job fail later with something opaque.
    """
    try:
        import cudaq
    except ImportError:
        return False, (
            "CUDA-Q is not installed. On Windows it runs under WSL2 — see "
            "docs/CUDAQ_SETUP.md."
        )

    try:
        targets = {target.name for target in cudaq.get_targets()}
    except Exception as exc:  # noqa: BLE001
        return False, f"CUDA-Q is installed but unusable: {exc}"

    if "nvidia" not in targets:
        return False, (
            "CUDA-Q is installed but exposes no GPU target. This backend needs "
            "an NVIDIA GPU with the CUDA runtime libraries present."
        )

    devices = _gpu_device_count()
    if devices is not None and devices < 1:
        return False, (
            "CUDA-Q is installed but sees no CUDA-capable GPU (0 devices). "
            "The API process needs a driver-visible NVIDIA GPU — on Windows "
            "that means the driver installed on the Windows side with WSL2 "
            "GPU passthrough. The CPU backends give identical results in the "
            "meantime."
        )
    return True, ""


def build_kernel(circ: Any, n_qubits: int, measurement_qubits=None):
    """Replay a transpiled Qiskit circuit through CUDA-Q's kernel builder.

    The same approach the Cirq adapter uses. By default measurements are
    omitted: CUDA-Q samples the whole register, and the caller maps qubits
    to clbits. (With explicit ``mz`` calls CUDA-Q instead returns bits in
    *measurement order*, which would be a second mapping to keep straight;
    skipping the measure ops avoids it. Verified on 0.16: ``x(q0)`` with only
    ``mz(q1)`` yields the single-bit string ``"1"``, not a two-bit register.)

    ``measurement_qubits`` flips that around for the NOISY run: an explicit
    ``mz`` on each listed qubit (in ascending order) is what a real
    ``BitFlipChannel`` attached to ``"mz"`` needs to bite -- CUDA-Q only
    applies readout noise where a measurement exists. The caller then maps
    result bits through the returned position list instead of trusting
    register order.

    ``cudaq.get_state`` indexes amplitudes with qubit 0 as the LEAST
    significant bit -- already Qiskit order, unlike Cirq -- so the statevector
    needs no reordering on this backend. Verified on 0.16: ``x(q0)`` of two
    qubits leaves index 1 nonzero.
    """
    import cudaq

    kernel = cudaq.make_kernel()
    qubits = kernel.qalloc(n_qubits)
    index = {qubit: position for position, qubit in enumerate(circ.qubits)}
    measured_order: list[int] = []

    for instruction in circ.data:
        name = instruction.operation.name.lower()
        targets = [index[q] for q in instruction.qubits]

        if name == "barrier":
            continue
        if name == "measure":
            if measurement_qubits is not None:
                kernel.mz(qubits[targets[0]])
            continue
        if name == "rx":
            kernel.rx(float(instruction.operation.params[0]), qubits[targets[0]])
        elif name == "ry":
            kernel.ry(float(instruction.operation.params[0]), qubits[targets[0]])
        elif name == "rz":
            kernel.rz(float(instruction.operation.params[0]), qubits[targets[0]])
        elif name == "cx":
            kernel.cx(qubits[targets[0]], qubits[targets[1]])
        else:
            raise BackendError(
                f"normalize() produced '{name}', which is outside the portable "
                f"basis {sorted(SUPPORTED_GATES)}. This is a normalization bug."
            )

    if measurement_qubits is not None:
        # kernel.mz was emitted per listed qubit in ascending order, so bit i
        # of a measured result string is qubit measured_order[i].
        measured_order = list(measurement_qubits)
    return kernel, qubits, measured_order


def _counts_from_sample(
    sample: Any, ir: CircuitIR, mapping: dict, bit_of: Optional[dict] = None
) -> dict[str, int]:
    """Convert a CUDA-Q SampleResult into the platform's counts convention.

    Every backend returns Qiskit bit order -- qubit 0 is the RIGHTMOST
    character -- so the histogram is comparable across engines.

    ``bit_of`` maps qubit -> position in the sampled bitstring. Register-wide
    sampling is already qubit order; a kernel with explicit ``mz`` reports
    measurement order instead, which the caller knows and passes in.
    """
    counts: dict[str, int] = {}
    n_clbits = max(ir.n_clbits, 1)
    result_rows = dict(sample.items()) if hasattr(sample, "items") and not isinstance(
        sample, dict
    ) else dict(sample)

    for bitstring, hits in result_rows.items():
        # CUDA-Q reports qubit 0 leftmost over the full register. Verified on
        # 0.16: x(q0) of two qubits samples "10", the opposite of Qiskit.
        bits = str(bitstring)
        out = ["0"] * n_clbits
        for qubit, clbit in mapping.items():
            pos = qubit if bit_of is None else bit_of.get(qubit)
            if pos is None or pos >= len(bits) or clbit >= n_clbits:
                continue
            # Write into Qiskit order: clbit 0 is the rightmost character.
            out[n_clbits - 1 - clbit] = bits[pos]
        key = "".join(out)
        counts[key] = counts.get(key, 0) + int(hits)
    return counts


def _thermal_probs(t_us: float, t1_us: float, t2_us: float) -> tuple[float, float]:
    """(amplitude-damping p, phase-flip p) for a pulse of duration ``t_us``.

    Mirrors Qiskit's ``thermal_relaxation_error`` in CUDA-Q's vocabulary of
    built-in channels: energy loss is an amplitude-damping event with
    probability 1 - exp(-t/T1); pure dephasing is a phase flip with
    1/T2 = 1/(2*T1) + 1/T_phi, so a T2 already clamped to <= 2*T1 leaves a
    non-negative dephasing rate. Applied back to back, the two channels damp
    coherences by exp(-t/2T1) * exp(-t/T_phi) = exp(-t/T2) -- the textbook
    single-qubit thermal model, not an invented approximation of it.
    """
    from math import exp

    if t_us <= 0.0:
        return 0.0, 0.0
    p_t1 = 1.0 - exp(-t_us / t1_us)
    inv_tphi = 1.0 / t2_us - 1.0 / (2.0 * t1_us)
    p_phi = (1.0 - exp(-t_us * inv_tphi)) / 2.0 if inv_tphi > 0.0 else 0.0
    return p_t1, max(0.0, min(0.5, p_phi))


def _build_cudaq_noise_model(cudaq: Any, clean: Any):
    """Assemble CUDA-Q's own NoiseModel from the platform's NoiseParams.

    Uses CUDA-Q's built-in validated channels (AmplitudeDampingChannel,
    PhaseFlipChannel, BitFlipChannel) via ``add_all_qubit_channel`` -- the
    same API its own noise-tutorial docs demonstrate, executed by CUDA-Q's
    density-matrix engine. Multiple channels on one (gate, qubit) compose
    sequentially, verified numerically on 0.16 (two 50% damping channels
    after one X left P(1) = 0.25).
    """
    model = cudaq.NoiseModel()
    applied = 0

    for t_us, gates in (
        (clean.gate_time_1q_us, PULSE_GATES_1Q),
        (clean.gate_time_2q_us, PULSE_GATES_2Q),
    ):
        p_t1, p_phi = _thermal_probs(t_us, clean.t1_us, clean.t2_us)
        if p_t1 <= 0.0 and p_phi <= 0.0:
            continue
        for gate in gates:
            if p_t1 > 0.0:
                model.add_all_qubit_channel(
                    gate, cudaq.AmplitudeDampingChannel(p_t1)
                )
            if p_phi > 0.0:
                model.add_all_qubit_channel(
                    gate, cudaq.PhaseFlipChannel(p_phi)
                )
            applied += 1

    if clean.readout_error > 0.0:
        # Readout is a fault of the measurement, not of the state: attaching a
        # bit-flip channel to "mz" is exactly that statement in CUDA-Q's
        # formalism. Verified on 0.16: p=0.5 flips an X-prepared |1> to a
        # 50/50 histogram.
        model.add_all_qubit_channel("mz", cudaq.BitFlipChannel(clean.readout_error))
        applied += 1

    return model, applied


def run(
    ir: CircuitIR,
    shots: int = 1024,
    *,
    seed: Optional[int] = None,
    precision: str = DEFAULT_PRECISION,
    noise: Optional[Any] = None,
) -> dict:
    """GPU statevector run; with ``noise.enabled`` the counts come from
    CUDA-Q's own density-matrix engine (see NOISE_MAX_QUBITS)."""
    available, reason = is_available()
    if not available:
        raise BackendError(reason)

    guard_static_size(ir, backend=NAME)

    noise_on = noise is not None and noise.enabled
    if noise_on and ir.n_qubits > NOISE_MAX_QUBITS:
        raise BackendError(
            f"Noisy CUDA-Q runs use its {NOISE_TARGET} engine, which carries "
            f"4^{ir.n_qubits} density-matrix elements in memory -- beyond "
            f"{NOISE_MAX_QUBITS} qubits that stops being a laptop-scale "
            "computation. The noise model on Qiskit Aer has no such cap "
            "problem at small sizes, or run this circuit noise-free here."
        )

    from app.config import get_settings

    import cudaq

    settings = get_settings()
    circ = normalize(ir)
    mapping = measured_qubit_map(ir)
    warnings: list[str] = []

    if not mapping:
        # Same convention as Qiskit Aer, Cirq and PennyLane: an unmeasured
        # circuit is measured across every qubit rather than returning an
        # empty histogram. The IR validator pads n_clbits up to n_qubits, so
        # the mapping always has somewhere to land.
        mapping = {q: q for q in range(ir.n_qubits)}
        warnings.append(
            "No measurements in circuit; measured all qubits automatically."
        )

    noise_meta: dict = {"enabled": False}
    metrics: dict = {}
    ideal_counts: dict[str, int] | None = None
    statevector = None

    try:
        # One job at a time, not while the card is hot, not back-to-back.
        with gpu_slot(
            temp_limit_c=settings.gpu_temp_limit_c,
            cooldown=settings.gpu_cooldown_seconds,
        ):
            with Timer() as timer:
                cudaq.set_target("nvidia", option=precision)
                if seed is not None:
                    cudaq.set_random_seed(int(seed))

                kernel, _qubits, _order = build_kernel(circ, ir.n_qubits)

                # State views show the ideal PRE-MEASUREMENT state on every
                # engine -- build_kernel drops measure ops, so get_state
                # answers that question here too, measured circuit or not.
                # The only thing that stops it is payload: 2**n complex
                # numbers copied out of VRAM, rebuilt as Python floats and
                # serialized into the job row. The GPU ceiling sits eight
                # qubits above the CPU one, so state views share the budget
                # every engine obeys; bigger circuits keep the histogram and
                # are told exactly why the amplitudes are absent.
                cap = settings.max_static_qubits
                amplitudes = None
                if ir.n_qubits <= cap:
                    state = cudaq.get_state(kernel)
                    amplitudes = list(state)
                    statevector = statevector_to_json(amplitudes)
                else:
                    warnings.append(
                        f"State views omitted above {cap} qubits: 2^{ir.n_qubits} "
                        "amplitudes through JSON would outrun the worker's "
                        "memory. Counts are complete."
                    )

                if amplitudes is not None and ir.n_qubits >= 2:
                    import numpy as np

                    from app.quantum.noise import entanglement_entropy

                    entropy, concurrence = entanglement_entropy(
                        np.array(amplitudes, dtype=complex), ir.n_qubits
                    )
                    metrics["entanglement_entropy"] = entropy
                    metrics["concurrence"] = concurrence
                    metrics["entangled"] = entropy > 0.05

                if not noise_on:
                    sample = cudaq.sample(kernel, shots_count=int(shots))
                    counts = _counts_from_sample(sample, ir, mapping)
                else:
                    from app.quantum.noise import total_variation

                    clean, noise_notes = noise.clamped()
                    warnings.extend(noise_notes)
                    noise_meta = {
                        "enabled": True,
                        "t1_us": clean.t1_us,
                        "t2_us": clean.t2_us,
                        "readout_error": clean.readout_error,
                    }
                    warnings.append(
                        "Noise model is a teaching approximation with parameters you chose, "
                        "not calibration from any real device."
                    )
                    if statevector is not None:
                        warnings.append(
                            "Statevector shown is the IDEAL state; only the counts carry noise."
                        )

                    # Explicit mz on every mapped qubit, ascending: this is
                    # what lets CUDA-Q's own readout channel attach, and both
                    # the ideal and the noisy histogram then share the exact
                    # same bit layout.
                    measured = sorted(mapping)
                    kernel_m, _kq, order = build_kernel(
                        circ, ir.n_qubits, measurement_qubits=measured
                    )
                    bit_of = {q: pos for pos, q in enumerate(order)}

                    model, applied = _build_cudaq_noise_model(cudaq, clean)
                    warnings.append(
                        f"Noisy sampling runs on CUDA-Q's {NOISE_TARGET} engine "
                        f"(up to {NOISE_MAX_QUBITS} qubits): Kraus channels need a "
                        "density matrix, which no statevector simulator holds. "
                        "Same CUDA-Q, same kernel, its own noise model."
                    )
                    cudaq.set_target(NOISE_TARGET)

                    # The noisy half, then the identical noise-free run so the
                    # Ideal-vs-noisy tab has both histograms from this engine.
                    noisy_raw = cudaq.sample(
                        kernel_m, noise_model=model, shots_count=int(shots)
                    )
                    counts = _counts_from_sample(noisy_raw, ir, mapping, bit_of)
                    ideal_raw = cudaq.sample(kernel_m, shots_count=int(shots))
                    ideal_counts = _counts_from_sample(
                        ideal_raw, ir, mapping, bit_of
                    )

                    if applied == 0:
                        warnings.append(
                            "Every noise probability rounded to zero (gates too "
                            "fast or times too long); the noisy run equals the ideal one."
                        )

                    total_noisy = sum(counts.values()) or 1
                    total_ideal = sum(ideal_counts.values()) or 1
                    ideal_probs = {k: v / total_ideal for k, v in ideal_counts.items()}
                    noisy_probs = {k: v / total_noisy for k, v in counts.items()}
                    metrics["total_variation"] = total_variation(
                        ideal_probs, noisy_probs
                    )
                    support = {k for k, v in ideal_probs.items() if v >= 0.02}
                    metrics["shot_leakage"] = sum(
                        v for k, v in noisy_probs.items() if k not in support
                    )
                    # CUDA-Q 0.16's get_state refuses a noise model, so the
                    # noisy density matrix (and thus F/purity) is not
                    # available here; the UI omits those two gauges rather
                    # than showing anything computed some other way.
                    warnings.append(
                        "Fidelity/purity gauges are omitted: CUDA-Q 0.16 get_state "
                        "cannot carry a noise model. Qiskit Aer shows both."
                    )
    except RuntimeError as exc:
        # Raised by gpu_slot when the card is busy, hot, or cooling down.
        raise BackendError(str(exc)) from exc
    except BackendError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface CUDA errors cleanly
        raise BackendError(f"CUDA-Q simulation failed: {exc}") from exc

    if not noise_on:
        # True statements, not placeholders: with no noise the state is pure,
        # the run agrees with itself, and nothing leaked. Aer's noiseless path
        # reports the same, and the meters draw from these keys.
        metrics.setdefault("fidelity", 1.0)
        metrics.setdefault("purity", 1.0)
        metrics.setdefault("total_variation", 0.0)
        metrics.setdefault("shot_leakage", 0.0)

    target_meta = "nvidia"
    if noise_on:
        target_meta = f"nvidia + {NOISE_TARGET}"

    return make_result(
        backend=NAME,
        counts=counts,
        shots=shots,
        n_qubits=ir.n_qubits,
        runtime=timer.seconds,
        statevector=statevector,
        warnings=warnings,
        metadata={
            "precision": precision,
            "target": target_meta,
            "mode": "static",
            "noise": noise_meta,
            "metrics": metrics,
            "ideal_counts": ideal_counts,
        },
    )


__all__ = ["NAME", "DEFAULT_PRECISION", "SUPPORTED_GATES", "NOISE_TARGET",
           "NOISE_MAX_QUBITS", "is_available", "build_kernel", "run"]
