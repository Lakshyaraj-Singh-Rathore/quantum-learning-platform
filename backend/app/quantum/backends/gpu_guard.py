"""Keep GPU work from cooking a laptop.

A statevector simulation is a short burst -- a 26-qubit, 100-gate circuit moves
about 107 GB through VRAM, roughly half a second on a mobile RTX 4050 -- so a
single job is not the problem. The problem is a learner pressing Run twenty
times in a row and chaining those bursts together.

Three defences, cheapest first:

* a process-wide lock, so two GPU jobs never overlap (they would also exceed
  VRAM);
* a cooldown, so submissions cannot chain back-to-back;
* a temperature gate, which refuses new work on an already-hot card.

Everything here fails open. If the temperature cannot be read the job still
runs: refusing to simulate because monitoring is unavailable would be worse
than the overheating risk it guards against.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time

#: Only one GPU job at a time. Module-level, so it is shared by every task in
#: this worker process.
_GPU_LOCK = threading.Lock()
_last_finished: float = 0.0
_last_lock = threading.Lock()

#: nvidia-smi inside WSL2 has, in NVIDIA's words, a "Limited Feature Set", and
#: temperature is usually one of the missing fields. The Windows binary is
#: reachable from WSL through interop and does report it, so try both.
_SMI_CANDIDATES = ("nvidia-smi", "nvidia-smi.exe")


def gpu_temperature_c() -> int | None:
    """Current GPU temperature, or None if it cannot be determined."""
    for binary in _SMI_CANDIDATES:
        if shutil.which(binary) is None:
            continue
        try:
            output = subprocess.run(
                [binary, "--query-gpu=temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, check=True,
            ).stdout.strip().splitlines()
        except Exception:  # noqa: BLE001 - monitoring must never break a run
            continue
        for line in output:
            try:
                return int(line.strip())
            except ValueError:
                continue
    return None


def check_thermal(limit_c: int) -> tuple[bool, str]:
    """Is the card cool enough for more work?

    Returns ``(ok, reason)``. Unknown temperature counts as ok.
    """
    if limit_c <= 0:
        return True, ""
    temperature = gpu_temperature_c()
    if temperature is None:
        return True, ""
    if temperature >= limit_c:
        return False, (
            f"The GPU is at {temperature}°C, at or above the {limit_c}°C limit. "
            "Give it a moment to cool, or run this on Qiskit Aer instead."
        )
    return True, ""


def seconds_until_ready(cooldown: float) -> float:
    """How long until the next GPU job may start."""
    if cooldown <= 0:
        return 0.0
    with _last_lock:
        elapsed = time.monotonic() - _last_finished
    return max(0.0, cooldown - elapsed)


def _mark_finished() -> None:
    global _last_finished
    with _last_lock:
        _last_finished = time.monotonic()


class gpu_slot:
    """Context manager holding the single GPU slot for the duration of a run.

    Raises ``RuntimeError`` if the card is busy, hot, or still cooling down;
    the caller turns that into a clean backend error.
    """

    def __init__(self, *, temp_limit_c: int, cooldown: float, wait: float = 0.0):
        self.temp_limit_c = temp_limit_c
        self.cooldown = cooldown
        self.wait = wait

    def __enter__(self):
        remaining = seconds_until_ready(self.cooldown)
        if remaining > 0:
            if self.wait <= 0:
                raise RuntimeError(
                    f"The GPU is cooling down; {remaining:.1f}s remaining. "
                    "Qiskit Aer is available now if you do not want to wait."
                )
            time.sleep(min(remaining, self.wait))

        ok, reason = check_thermal(self.temp_limit_c)
        if not ok:
            raise RuntimeError(reason)

        if not _GPU_LOCK.acquire(timeout=max(self.wait, 0.1)):
            raise RuntimeError(
                "Another GPU simulation is already running. Only one fits in "
                "VRAM at a time, so please wait for it to finish."
            )
        return self

    def __exit__(self, *exc):
        _mark_finished()
        _GPU_LOCK.release()
        return False


__all__ = [
    "gpu_temperature_c", "check_thermal", "seconds_until_ready", "gpu_slot",
]
