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


def build_kernel(circ: Any, n_qubits: int):
    """Replay a transpiled Qiskit circuit through CUDA-Q's kernel builder.

    The same approach the Cirq adapter uses. Measurements are omitted: CUDA-Q
    samples the whole register, and the caller maps qubits to clbits. (With
    explicit ``mz`` calls CUDA-Q instead returns bits in *measurement order*,
    which would be a second mapping to keep straight; skipping the measure
    ops avoids it. Verified on 0.16: ``x(q0)`` with only ``mz(q1)`` yields the
    single-bit string ``"1"``, not a two-bit register.)

    ``cudaq.get_state`` indexes amplitudes with qubit 0 as the LEAST
    significant bit -- already Qiskit order, unlike Cirq -- so the statevector
    needs no reordering on this backend. Verified on 0.16: ``x(q0)`` of two
    qubits leaves index 1 nonzero.
    """
    import cudaq

    kernel = cudaq.make_kernel()
    qubits = kernel.qalloc(n_qubits)
    index = {qubit: position for position, qubit in enumerate(circ.qubits)}

    for instruction in circ.data:
        name = instruction.operation.name.lower()
        targets = [index[q] for q in instruction.qubits]

        if name in {"measure", "barrier"}:
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
    return kernel, qubits


def _counts_from_sample(sample: Any, ir: CircuitIR, mapping: dict) -> dict[str, int]:
    """Convert a CUDA-Q SampleResult into the platform's counts convention.

    Every backend returns Qiskit bit order -- qubit 0 is the RIGHTMOST
    character -- so the histogram is comparable across engines.
    """
    counts: dict[str, int] = {}
    n_clbits = max(ir.n_clbits, 1)

    for bitstring, hits in sample.items():
        # CUDA-Q reports qubit 0 leftmost over the full register. Verified on
        # 0.16: x(q0) of two qubits samples "10", the opposite of Qiskit.
        bits = str(bitstring)
        out = ["0"] * n_clbits
        for qubit, clbit in mapping.items():
            if qubit < len(bits) and clbit < n_clbits:
                # Write into Qiskit order: clbit 0 is the rightmost character.
                out[n_clbits - 1 - clbit] = bits[qubit]
        key = "".join(out)
        counts[key] = counts.get(key, 0) + int(hits)
    return counts


def run(
    ir: CircuitIR,
    shots: int = 1024,
    *,
    seed: Optional[int] = None,
    precision: str = DEFAULT_PRECISION,
) -> dict:
    available, reason = is_available()
    if not available:
        raise BackendError(reason)

    guard_static_size(ir, backend=NAME)

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

                kernel, _qubits = build_kernel(circ, ir.n_qubits)

                # State views show the ideal PRE-MEASUREMENT state on every
                # engine -- build_kernel drops measure ops, so get_state
                # answers that question here too, measured circuit or not.
                # The only thing that stops it is payload: 2**n complex
                # numbers copied out of VRAM, rebuilt as Python floats and
                # serialized into the job row. The GPU ceiling sits eight
                # qubits above the CPU one, so state views share the budget
                # every engine obeys; bigger circuits keep the histogram and
                # are told exactly why the amplitudes are absent.
                statevector = None
                cap = settings.max_static_qubits
                if ir.n_qubits <= cap:
                    state = cudaq.get_state(kernel)
                    statevector = statevector_to_json(list(state))
                else:
                    warnings.append(
                        f"State views omitted above {cap} qubits: 2^{ir.n_qubits} "
                        "amplitudes through JSON would outrun the worker's "
                        "memory. Counts are complete."
                    )

                sample = cudaq.sample(kernel, shots_count=int(shots))
                counts = _counts_from_sample(sample, ir, mapping)
    except RuntimeError as exc:
        # Raised by gpu_slot when the card is busy, hot, or cooling down.
        raise BackendError(str(exc)) from exc
    except BackendError:
        raise
    except Exception as exc:  # noqa: BLE001 - surface CUDA errors cleanly
        raise BackendError(f"CUDA-Q simulation failed: {exc}") from exc

    return make_result(
        backend=NAME,
        counts=counts,
        shots=shots,
        n_qubits=ir.n_qubits,
        runtime=timer.seconds,
        statevector=statevector,
        warnings=warnings,
        metadata={"precision": precision, "target": "nvidia"},
    )


__all__ = ["NAME", "DEFAULT_PRECISION", "SUPPORTED_GATES", "is_available",
           "build_kernel", "run"]
