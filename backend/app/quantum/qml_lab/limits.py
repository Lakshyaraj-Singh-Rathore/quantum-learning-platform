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

from app.quantum.qml_lab.errors import QmlConfigError, QmlLimitExceededError

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
# Scoped GLOBALLY, not per user. The resource being protected is the machine —
# one worker on a laptop — not a per-user quota, and the master prompt's limit
# table says "concurrent training jobs: 1" without qualification. Counting per
# user would let two users each pass the pre-dispatch check and both enqueue;
# the queue would still serialise them, so the second user would get a silent
# multi-hour wait instead of an immediate, honest 409. If per-user fairness is
# ever wanted it goes on top of this as a second, tighter cap — the global cap
# is the binding constraint and must exist regardless.
MAX_CONCURRENT_JOBS = 1

# Stricter than MAX_QUBITS because a density matrix costs 4**n complex numbers
# against a state vector's 2**n. Provisional (DECISIONS.md D-009): Phase 4
# measurements confirm or lower it. Unused in Phase 1, which is state-vector
# only; defined here so there is a single source of truth when noise arrives.
DENSITY_MATRIX_MAX_QUBITS = 6

#: Machine-readable limit table. Phase 2's ``/describe`` endpoint serves this
#: so the UI bounds its inputs with the same numbers the server enforces,
#: rather than a hand-copied duplicate that can drift.
def _base_table() -> dict[str, dict[str, Any]]:
    """Build the limit table from the **current** module constants.

    Read live rather than snapshotted at import, because the worker's second
    enforcement pass exists precisely for the case where a ceiling moved after
    a row was queued (``test_worker_reenforces_limits_that_tightened_after_the
    _row_was_queued``). A frozen copy would make :func:`check` blind to a
    tightened limit — the one scenario :func:`enforce` is there to catch.
    """
    return {
        "n_qubits": {"default": DEFAULT_QUBITS, "min": 1, "max": MAX_QUBITS},
        "n_layers": {"default": DEFAULT_LAYERS, "min": 1, "max": MAX_LAYERS},
        "n_samples": {"default": DEFAULT_SAMPLES, "min": MIN_SAMPLES, "max": MAX_SAMPLES},
        "epochs": {"default": DEFAULT_EPOCHS, "min": 1, "max": MAX_EPOCHS},
        "batch_size": {"default": DEFAULT_BATCH_SIZE, "min": 1, "max": MAX_BATCH_SIZE},
        "concurrent_jobs": {"default": 1, "min": 1, "max": MAX_CONCURRENT_JOBS},
        "density_matrix_qubits": {"default": 4, "min": 1, "max": DENSITY_MATRIX_MAX_QUBITS},
    }


LIMITS: dict[str, dict[str, Any]] = _base_table()


# --- per-algorithm ceilings (DECISIONS.md D-032, vision §2C.1) --------------
# A single flat table cannot serve algorithms whose cost *laws* differ, not
# merely their constants. Phase 4 measured backprop linear in circuit size and
# parameter-shift quadratic; a quantum kernel is worse than either, being
# O(N^2) in samples before a model is fitted at all.
#
# Only the keys an algorithm actually tightens appear here. Anything absent
# falls through to the module-level maximum above, so adding an algorithm
# cannot silently loosen a global ceiling.

#: Every algorithm the lab can run. The schema's Literal is built from this,
#: so a new entry cannot be accepted by the API until it is listed.
ALGORITHMS: tuple[str, ...] = (
    "vqc",
    "hybrid_qnn",
    "quantum_kernel",
    "quantum_regression",
)

DEFAULT_ALGORITHM = "vqc"

#: Width of the hybrid model's classical layer. Bounded by n_qubits at
#: construction (one wire per emitted value), so this is only the hard cap.
DEFAULT_HIDDEN_UNITS = 4
MAX_HIDDEN_UNITS = 8

#: The kernel's own sample ceiling, far below MAX_SAMPLES and deliberately so.
#: A kernel matrix needs N*(N+1)/2 circuit evaluations before anything is
#: fitted. Priced from Phase 4's measured forward cost of 10.377 ms/sample at
#: 8 qubits x 4 layers on the sandbox (docs/qml/04-benchmarks.md §3.3):
#:
#:   N = 250  ->   31,375 evaluations  ~ 326 s   (inside the 900 s soft limit)
#:   N = 1000 ->  500,500 evaluations  ~ 87 min  (102x over, structurally hopeless)
#:
#: 250 is the largest round number that leaves headroom for the linear solve
#: and the evaluation pass on the *slowest* machine measured. It is a ceiling,
#: not a target, and MT-004 may lower it once the target machine is measured.
MAX_KERNEL_SAMPLES = 250
DEFAULT_KERNEL_SAMPLES = 150

def _algorithm_overrides() -> dict[str, dict[str, int]]:
    """Per-algorithm tightenings, **re-read from the live constants**.

    A function rather than a module-level dict for the same reason
    :func:`_base_table` is one. A dict literal captures ``MAX_KERNEL_SAMPLES``
    at import time, so ``monkeypatch.setattr(limits, "MAX_KERNEL_SAMPLES", 10)``
    silently fails to reach anything — disabling the very ceiling the test is
    trying to exercise, while the test still passes against the real 250.

    This exact defect was found and fixed in ``LIMITS``/``limits_for`` one
    commit earlier and then recurred here, in the sibling structure, because
    the fix was applied to the symptom rather than to both snapshots. Both are
    now live-reading, and ``test_algorithm_overrides_track_the_live_constants``
    pins it.
    """
    return {
        "vqc": {},
        "hybrid_qnn": {},
        "quantum_kernel": {
            "n_samples": MAX_KERNEL_SAMPLES,
            # A kernel is fitted in closed form by one linear solve, so epochs
            # and batching do not apply. Pinned to 1 so a config that sets them
            # is rejected rather than quietly ignored.
            "epochs": 1,
        },
        "quantum_regression": {},
    }


#: Snapshot for introspection and docs. Call :func:`_algorithm_overrides` (or
#: :func:`limits_for`) for anything that must honour a runtime change.
ALGORITHM_LIMITS: dict[str, dict[str, int]] = _algorithm_overrides()


def limits_for(algorithm: str) -> dict[str, dict[str, Any]]:
    """The effective limit table for ``algorithm``.

    Returns the same shape as :data:`LIMITS` so ``/describe`` and the UI read
    one structure regardless of algorithm — the values move, the shape does
    not (§2C.1).
    """
    if algorithm not in ALGORITHMS:
        raise QmlConfigError(
            f"unknown algorithm {algorithm!r}; expected one of {', '.join(ALGORITHMS)}"
        )
    table = _base_table()
    for key, ceiling in _algorithm_overrides()[algorithm].items():
        if key in table:
            table[key]["max"] = ceiling
            if table[key]["default"] > ceiling:
                table[key]["default"] = ceiling
    if algorithm == "quantum_kernel":
        table["n_samples"]["default"] = DEFAULT_KERNEL_SAMPLES
    if algorithm == "hybrid_qnn":
        table["n_hidden"] = {
            "default": DEFAULT_HIDDEN_UNITS,
            "min": 1,
            "max": MAX_HIDDEN_UNITS,
        }
    return table


def max_for(algorithm: str, key: str) -> int:
    """The binding ceiling for one field, after per-algorithm tightening."""
    return int(limits_for(algorithm)[key]["max"])


def check(config: "QmlExperimentConfig") -> list[str]:
    """Return a list of human-readable limit violations; empty means allowed.

    The Pydantic schema already bounds each field, so a config built through
    the API cannot normally reach here in violation. This is the second line of
    defence: it also catches a config deserialised from a stored row that was
    written when the limits were looser.

    Checked **per algorithm** (§2C.1): a configuration that is legal for a VQC
    can be far outside what a kernel can finish, so the ceiling consulted
    depends on ``config.algorithm``.
    """
    violations: list[str] = []
    algorithm = getattr(config, "algorithm", DEFAULT_ALGORITHM)
    table = limits_for(algorithm)

    def ceiling(key: str) -> int:
        return int(table[key]["max"])

    if config.circuit.n_qubits > ceiling("n_qubits"):
        violations.append(
            f"n_qubits={config.circuit.n_qubits} exceeds the limit of {ceiling('n_qubits')}"
        )
    if config.circuit.n_layers > ceiling("n_layers"):
        violations.append(
            f"n_layers={config.circuit.n_layers} exceeds the limit of {ceiling('n_layers')}"
        )
    if config.dataset.n_samples > ceiling("n_samples"):
        suffix = (
            f" for {algorithm} (a kernel matrix is O(N^2) circuit evaluations)"
            if algorithm == "quantum_kernel"
            else ""
        )
        violations.append(
            f"n_samples={config.dataset.n_samples} exceeds the limit of "
            f"{ceiling('n_samples')}{suffix}"
        )
    if config.dataset.n_samples < MIN_SAMPLES:
        violations.append(f"n_samples={config.dataset.n_samples} is below the minimum of {MIN_SAMPLES}")
    if config.training.epochs > ceiling("epochs"):
        suffix = (
            f" for {algorithm}, which is fitted in closed form by one linear solve"
            if algorithm == "quantum_kernel"
            else ""
        )
        violations.append(
            f"epochs={config.training.epochs} exceeds the limit of {ceiling('epochs')}{suffix}"
        )
    if config.training.batch_size > ceiling("batch_size"):
        violations.append(
            f"batch_size={config.training.batch_size} exceeds the limit of {ceiling('batch_size')}"
        )
    n_hidden = getattr(config.circuit, "n_hidden", None)
    if n_hidden is not None and n_hidden > MAX_HIDDEN_UNITS:
        violations.append(f"n_hidden={n_hidden} exceeds the limit of {MAX_HIDDEN_UNITS}")

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

    **The evaluation term is per epoch, not once** (DECISIONS.md D-028).
    :func:`~app.quantum.qml_lab.trainer.train` scores *both* splits at the end
    of *every* epoch (``trainer.py:220-221``), so evaluation costs
    ``epochs * n_samples`` forward executions. An earlier version charged it
    once and was measured 2.39x low at the maximum configuration under the
    default gradient method, where the evaluation pass is 59% of all circuit
    executions. :func:`test_estimate_cost_matches_a_real_training_run` pins
    this against a ``qml.Tracker`` count of an actual run.
    """
    n_train = int(round(config.dataset.n_samples * (1.0 - config.dataset.test_fraction)))
    n_params = n_parameters(config.circuit.n_qubits, config.circuit.n_layers)

    if config.training.diff_method == "parameter-shift":
        per_sample = 1 + 2 * n_params
    else:
        per_sample = 1

    train_execs = config.training.epochs * n_train * per_sample
    # Forward-only, both splits, every epoch. Method-independent: evaluation
    # takes no gradient, so parameter-shift pays the same as backprop here.
    eval_execs = config.training.epochs * config.dataset.n_samples

    return {
        "n_train": n_train,
        "n_parameters": n_params,
        "executions_per_sample": per_sample,
        "training_executions": train_execs,
        "evaluation_executions": eval_execs,
        "circuit_executions": train_execs + eval_execs,
        "state_vector_amplitudes": 2 ** config.circuit.n_qubits,
        "diff_method": config.training.diff_method,
    }
