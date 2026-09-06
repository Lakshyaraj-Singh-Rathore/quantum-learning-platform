"""qBraid execution backend (real submission, not export-only).

Submits the circuit as OpenQASM 3 to a configured qBraid device, polls the job
to completion and normalizes the returned counts into the platform schema.
Static circuits only; disabled with a clear message when credentials are absent.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from app.config import get_settings
from app.quantum.backends.base import BackendError, BackendUnavailable, Timer, make_result
from app.quantum.ir import CircuitIR
from app.quantum.qasm3_codec import to_qasm3

NAME = "qbraid"

POLL_INTERVAL = 1.0
DEFAULT_TIMEOUT = 300.0
TERMINAL_OK = {"COMPLETED", "DONE", "SUCCESS", "FINISHED"}
TERMINAL_BAD = {"FAILED", "CANCELLED", "CANCELED", "ERROR"}


def is_available() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.qbraid_api_key:
        return False, "Missing qBraid credentials (set QBRAID_API_KEY)."
    if not settings.qbraid_device_id:
        return False, "No qBraid device selected (set QBRAID_DEVICE_ID)."
    return True, ""


def run(
    ir: CircuitIR,
    shots: int = 1024,
    *,
    seed: Optional[int] = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    settings = get_settings()
    ok, reason = is_available()
    if not ok:
        raise BackendUnavailable(reason)
    if ir.is_dynamic():
        raise BackendError(
            "The qBraid backend supports static circuits only; "
            "dynamic circuits run on the Qiskit dynamic engine."
        )

    try:
        from qbraid.runtime import QbraidProvider
    except ImportError as exc:  # pragma: no cover
        raise BackendError("the qbraid SDK is not installed") from exc

    qasm = to_qasm3(ir)
    warnings: list[str] = []

    with Timer() as timer:
        try:
            provider = QbraidProvider(api_key=settings.qbraid_api_key)
            device = provider.get_device(settings.qbraid_device_id)
            job = device.run(qasm, shots=shots)
        except Exception as exc:  # noqa: BLE001 - surface SDK errors cleanly
            raise _translate(exc, settings.qbraid_device_id) from exc
        _wait_for(job, timeout)
        try:
            result = job.result()
        except Exception as exc:  # noqa: BLE001
            raise BackendError(f"qBraid job failed: {exc}") from exc
        counts = _extract_counts(result)

    counts = {_clean_key(k): int(v) for k, v in counts.items()}
    total = sum(counts.values())
    if total and total != shots:
        warnings.append(f"Device returned {total} shots (requested {shots}).")

    return make_result(
        backend=NAME,
        counts=counts,
        shots=shots,
        n_qubits=ir.n_qubits,
        runtime=timer.seconds,
        statevector=None,
        warnings=warnings + ["Executed remotely on qBraid; statevector is unavailable."],
        metadata={
            "mode": "static",
            "device_id": settings.qbraid_device_id,
            "job_id": str(getattr(job, "id", "") or getattr(job, "job_id", "")),
        },
    )


def _translate(exc: Exception, device_id: str) -> BackendError:
    """Turn raw SDK failures into actionable messages for the UI."""
    message = str(exc)
    lowered = message.lower()
    if "authenticate" in lowered or "unauthorized" in lowered or "401" in lowered:
        return BackendUnavailable(
            "qBraid rejected the credentials. Check that QBRAID_API_KEY is valid "
            "and that your account has Quantum Runtime access."
        )
    if "not found" in lowered or "no device" in lowered:
        return BackendUnavailable(
            f"qBraid device '{device_id}' was not found or is not enabled for this account. "
            "Set QBRAID_DEVICE_ID to a device you can access."
        )
    return BackendError(f"qBraid submission failed: {message}")


def _wait_for(job: Any, timeout: float) -> None:
    """Poll until the job reaches a terminal state."""
    waited = 0.0
    if hasattr(job, "wait_for_final_state"):
        try:
            job.wait_for_final_state(timeout=timeout)
            return
        except TypeError:
            job.wait_for_final_state()
            return
        except Exception:  # noqa: BLE001 - fall back to manual polling
            pass
    while waited < timeout:
        status = str(getattr(job, "status", lambda: "")() or "").upper()
        status = status.rsplit(".", 1)[-1]
        if status in TERMINAL_OK:
            return
        if status in TERMINAL_BAD:
            raise BackendError(f"qBraid job ended with status {status}")
        time.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL
    raise BackendError(f"qBraid job did not finish within {timeout:.0f}s")


def _extract_counts(result: Any) -> dict[str, int]:
    """Counts live in different places across qbraid SDK versions."""
    for getter in (
        lambda r: r.data.get_counts(),
        lambda r: r.get_counts(),
        lambda r: r.measurement_counts(),
        lambda r: r.data.measurement_counts,
        lambda r: r.counts,
    ):
        try:
            counts = getter(result)
        except Exception:  # noqa: BLE001
            continue
        if callable(counts):
            try:
                counts = counts()
            except Exception:  # noqa: BLE001
                continue
        if isinstance(counts, dict) and counts:
            return counts
    raise BackendError("could not read counts from the qBraid result payload")


def _clean_key(key: Any) -> str:
    return str(key).replace(" ", "").replace("0b", "")


__all__ = ["run", "NAME", "is_available"]
