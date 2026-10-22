"""Resource limits for the QML Lab, enforced in one place.

Why this module exists separately from the Pydantic schema: the limits must be
applied **twice** — once when a request is validated, and again inside the
worker before execution, so that an experiment queued before a limit changed
cannot run outside the current limits. A pure function of the config, with no
FastAPI or Celery import, is callable from both.

The numbers come from the master prompt's resource table. They are ceilings,
not suggestions: they are never loosened without measured evidence, and the
Phase 4 benchmarks may lower them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.quantum.qml_lab.errors import QmlLimitExceededError

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.quantum.qml_lab.models import QmlExperimentConfig

# --- qubits -----------------------------------------------------------------
DEFAULT_QUBITS = 4
MAX_QUBITS = 8

# --- ansatz depth -----------------------------------------------------------
DEFAULT_LAYERS = 2
MAX_LAYERS = 4

# --- dataset size -----------------------------------------------------------
DEFAULT_SAMPLES = 200
MAX_SAMPLES = 1000
MIN_SAMPLES = 20

# --- optimisation -----------------------------------------------------------
DEFAULT_EPOCHS = 20
MAX_EPOCHS = 100
DEFAULT_BATCH_SIZE = 16
MAX_BATCH_SIZE = 32

# --- scheduling -------------------------------------------------------------
MAX_CONCURRENT_JOBS_PER_USER = 1

# Stricter than MAX_QUBITS because a density matrix costs 4**n complex numbers
# against a state vector's 2**n. Provisional (DECISIONS.md D-009): Phase 4
# measurements confirm or lower it. Unused in Phase 1, which is state-vector
# only; defined here so there is a single source of truth when noise arrives.
DENSITY_MATRIX_MAX_QUBITS = 6

#: Machine-readable limit table. Phase 2's ``/describe`` endpoint serves this
#: so the UI bounds its inputs with the same numbers the server enforces,
#: rather than a hand-copied duplicate that can drift.
LIMITS: dict[str, dict[str, Any]] = {
    "n_qubits": {"default": DEFAULT_QUBITS, "min": 1, "max": MAX_QUBITS},
    "n_layers": {"default": DEFAULT_LAYERS, "min": 1, "max": MAX_LAYERS},
    "n_samples": {"default": DEFAULT_SAMPLES, "min": MIN_SAMPLES, "max": MAX_SAMPLES},
    "epochs": {"default": DEFAULT_EPOCHS, "min": 1, "max": MAX_EPOCHS},
    "batch_size": {"default": DEFAULT_BATCH_SIZE, "min": 1, "max": MAX_BATCH_SIZE},
    "concurrent_jobs": {"default": 1, "min": 1, "max": MAX_CONCURRENT_JOBS_PER_USER},
    "density_matrix_qubits": {"default": 4, "min": 1, "max": DENSITY_MATRIX_MAX_QUBITS},
}


def check(config: "QmlExperimentConfig") -> list[str]:
    """Return a list of human-readable limit violations; empty means allowed.

    The Pydantic schema already bounds each field, so a config built through
    the API cannot normally reach here in violation. This is the second line of
    defence: it also catches a config deserialised from a stored row that was
    written when the limits were looser.
    """
    violations: list[str] = []

    if config.circuit.n_qubits > MAX_QUBITS:
        violations.append(f"n_qubits={config.circuit.n_qubits} exceeds the limit of {MAX_QUBITS}")
    if config.circuit.n_layers > MAX_LAYERS:
        violations.append(f"n_layers={config.circuit.n_layers} exceeds the limit of {MAX_LAYERS}")
    if config.dataset.n_samples > MAX_SAMPLES:
        violations.append(f"n_samples={config.dataset.n_samples} exceeds the limit of {MAX_SAMPLES}")
    if config.dataset.n_samples < MIN_SAMPLES:
        violations.append(f"n_samples={config.dataset.n_samples} is below the minimum of {MIN_SAMPLES}")
    if config.training.epochs > MAX_EPOCHS:
        violations.append(f"epochs={config.training.epochs} exceeds the limit of {MAX_EPOCHS}")
    if config.training.batch_size > MAX_BATCH_SIZE:
        violations.append(f"batch_size={config.training.batch_size} exceeds the limit of {MAX_BATCH_SIZE}")

    return violations


def enforce(config: "QmlExperimentConfig") -> None:
    """Raise :class:`QmlLimitExceededError` if the config breaches any limit."""
    violations = check(config)
    if violations:
        raise QmlLimitExceededError(violations)


def n_parameters(n_qubits: int, n_layers: int) -> int:
    """Trainable circuit parameters for the ansatz in :mod:`.circuit`.

    Two rotations (RY, RZ) per qubit per layer. The trainable bias in
    :class:`~app.quantum.qml_lab.vqc.Parameters` is counted separately because
    it is classical and costs no circuit evaluations under parameter-shift.
    """
    return int(n_layers) * int(n_qubits) * 2


def estimate_cost(config: "QmlExperimentConfig") -> dict[str, int | float | str]:
    """Estimate the circuit-execution cost of running ``config``.

    Used by the UI to warn before submission and by Phase 4 to tune the
    per-task timeout against measured throughput. Counts circuit *executions*,
    which dominate runtime; classical overhead is ignored.

    Parameter-shift needs two extra executions per parameter per sample, which
    is why it is roughly ``1 + 2 * n_parameters`` times more expensive than
    backprop. That ratio is the single biggest driver of runtime and is the
    reason backprop is the default.
    """
    n_train = int(round(config.dataset.n_samples * (1.0 - config.dataset.test_fraction)))
    n_params = n_parameters(config.circuit.n_qubits, config.circuit.n_layers)

    if config.training.diff_method == "parameter-shift":
        per_sample = 1 + 2 * n_params
    else:
        per_sample = 1

    train_execs = config.training.epochs * n_train * per_sample
    eval_execs = config.dataset.n_samples  # one forward pass over everything at the end

    return {
        "n_train": n_train,
        "n_parameters": n_params,
        "executions_per_sample": per_sample,
        "circuit_executions": train_execs + eval_execs,
        "state_vector_amplitudes": 2 ** config.circuit.n_qubits,
        "diff_method": config.training.diff_method,
    }
