"""Orchestration for QML Lab experiments.

Sits between the HTTP layer and the pure engine in ``app.quantum.qml_lab``.
Everything that needs both a database session and the engine lives here, so
the router stays thin and the Celery task is a few lines of wiring -- and so
the whole run can be exercised in a test without a broker.

The engine itself imports neither Celery nor SQLAlchemy; the three hooks it
accepts (``on_progress``, ``should_cancel`` and ``deadline_seconds``) are
supplied from here.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.qml import (
    ACTIVE_STATUSES,
    TERMINAL_STATUSES,
    CANCELLED,
    COMPLETED,
    FAILED,
    RUNNING,
    TIMED_OUT,
    QmlEpochMetric,
    QmlExperiment,
)
from app.quantum.qml_lab import algorithms, datasets, evaluator, limits, trainer
from app.quantum.qml_lab.baseline import run_baseline
from app.quantum.qml_lab.errors import QmlLabError, QmlPersistenceError
from app.quantum.qml_lab.models import ProgressEvent, QmlExperimentConfig
from app.quantum.qml_lab.persistence import load_model, save_model

logger = logging.getLogger(__name__)

#: Seconds of headroom between the engine's cooperative deadline and Celery's
#: soft time limit, so a timed-out run still has time to write its partial
#: history and a readable message before the worker is interrupted. Same
#: reasoning as the qBraid budget at ``app/workers/tasks.py:96``, which
#: subtracts a margin from the soft limit rather than racing it.
TIMEOUT_MARGIN_SECONDS = 30.0

#: Minimum gap between two reads of ``cancel_requested``. Polling the database
#: on every batch of a 1,000-sample run would cost more than the training.
CANCEL_POLL_INTERVAL_SECONDS = 0.5


def compute_config_hash(config: QmlExperimentConfig) -> str:
    """Cache key for an experiment.

    Mirrors ``app.quantum.inspect.compute_run_hash``: canonical JSON, sorted
    keys, compact separators, SHA-256. The whole validated config
    participates -- including the seed, because two runs differing only by
    seed are different experiments and must not share a cached result.
    """
    payload = json.dumps(config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def artifact_root() -> Path:
    """Directory for saved models.

    Relative values resolve against the backend package root so the location
    does not depend on the worker's working directory. The default lives
    under ``artifacts/``, which is already gitignored -- a trained model must
    never be committed.
    """
    configured = Path(get_settings().qml_artifact_dir)
    if configured.is_absolute():
        return configured
    return Path(__file__).resolve().parents[2] / configured


def training_deadline_seconds() -> float:
    """The cooperative budget handed to ``train()``.

    Strictly below the Celery soft limit so the cooperative path always wins
    and the user gets a clean ``timed_out`` instead of a
    ``SoftTimeLimitExceeded`` traceback. Derived from the QML-specific
    settings, never from the global Celery limits (§1.1).
    """
    soft = float(get_settings().qml_task_soft_time_limit)
    return max(1.0, soft - TIMEOUT_MARGIN_SECONDS)


# ---------------------------------------------------------------------------
# Lookups used by the API before it dispatches
# ---------------------------------------------------------------------------


def find_cached(db: Session, user_id: int, run_hash: str) -> QmlExperiment | None:
    """The duplicate-submission guard, copied from ``api/jobs.py:150-166``."""
    return db.scalar(
        select(QmlExperiment)
        .where(
            QmlExperiment.run_hash == run_hash,
            QmlExperiment.user_id == user_id,
            QmlExperiment.status == COMPLETED,
        )
        .order_by(QmlExperiment.id.desc())
        .limit(1)
    )


def find_active(db: Session) -> QmlExperiment | None:
    """The concurrency guard -- scoped GLOBALLY, not per user.

    The resource protected is the single worker slot, not a per-user quota.
    Counting per user would let two users each pass this check and both
    enqueue; the queue would serialise them anyway, so the second user would
    wait silently instead of being told immediately.
    """
    return db.scalar(
        select(QmlExperiment)
        .where(QmlExperiment.status.in_(tuple(ACTIVE_STATUSES)))
        .order_by(QmlExperiment.id.asc())
        .limit(1)
    )


def count_active(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(QmlExperiment)
            .where(QmlExperiment.status.in_(tuple(ACTIVE_STATUSES)))
        )
        or 0
    )


# ---------------------------------------------------------------------------
# Worker-side execution
# ---------------------------------------------------------------------------


class CancelPoller:
    """Throttled reader of ``cancel_requested``.

    The wall-clock deadline is *not* handled here -- it belongs to the engine
    (``train(deadline_seconds=...)``), which is what makes it work on every
    platform. This object answers one question only: has the user asked to
    stop?
    """

    def __init__(self, db: Session, experiment_id: int) -> None:
        self._db = db
        self._experiment_id = experiment_id
        self._last_poll = 0.0
        self._cached = False

    def __call__(self) -> bool:
        if self._cached:
            return True
        now = time.monotonic()
        if now - self._last_poll < CANCEL_POLL_INTERVAL_SECONDS:
            return False
        self._last_poll = now

        row = self._db.get(QmlExperiment, self._experiment_id)
        if row is None:
            return False
        # Without expiring it first, db.get returns the identity-map copy
        # loaded when the task started and would never observe the API's
        # UPDATE -- which is the entire point of a cooperative flag.
        self._db.expire(row, ["cancel_requested"])
        self._cached = bool(row.cancel_requested)
        return self._cached


def record_epoch(db: Session, experiment_id: int, record) -> bool:
    """Append one epoch row, tolerating redelivery.

    ``task_acks_late=True`` makes Celery at-least-once, so a redelivered task
    can replay epochs that are already stored. The unique constraint turns
    that into an IntegrityError we swallow, rather than a duplicated point on
    the user's loss curve.

    Returns True if a row was inserted, False if this epoch already existed.
    """
    # Duck-typed on the record, not branched on a task string: an
    # EpochRecord carries accuracy and no R2, a RegressionEpochRecord the
    # reverse. Writing a 0.0 into the column the record does not have is the
    # exact hazard relaxing train_accuracy's NOT NULL introduced, so the
    # absent metric is written as NULL.
    def _maybe(name: str):
        value = getattr(record, name, None)
        return None if value is None else float(value)

    metric = QmlEpochMetric(
        experiment_id=experiment_id,
        epoch=record.epoch,
        train_loss=float(record.train_loss),
        train_accuracy=_maybe("train_accuracy"),
        test_loss=_maybe("test_loss"),
        test_accuracy=_maybe("test_accuracy"),
        train_r2=_maybe("train_r2"),
        test_r2=_maybe("test_r2"),
        elapsed_seconds=float(record.elapsed_seconds),
    )
    savepoint = db.begin_nested()
    try:
        db.add(metric)
        savepoint.commit()
    except IntegrityError:
        savepoint.rollback()
        logger.info(
            "epoch %s of experiment %s already recorded; ignoring redelivery",
            record.epoch,
            experiment_id,
        )
        return False
    db.commit()
    return True


def load_history(db: Session, experiment_id: int, after_epoch: int = 0) -> list[dict[str, Any]]:
    """Epoch rows for the dashboard, newest-after-``after_epoch`` only.

    Incremental by design: the dashboard passes the last epoch it has seen
    and gets back just the new ones, instead of re-downloading the whole
    curve on every poll.
    """
    rows = db.scalars(
        select(QmlEpochMetric)
        .where(QmlEpochMetric.experiment_id == experiment_id, QmlEpochMetric.epoch > after_epoch)
        .order_by(QmlEpochMetric.epoch.asc())
    ).all()
    return [
        {
            "epoch": row.epoch,
            "train_loss": row.train_loss,
            "train_accuracy": row.train_accuracy,
            "test_loss": row.test_loss,
            "test_accuracy": row.test_accuracy,
            "elapsed_seconds": row.elapsed_seconds,
        }
        for row in rows
    ]


def execute_experiment(
    db: Session,
    experiment_id: int,
    *,
    celery_task_id: str | None = None,
    deadline_seconds: float | None = None,
) -> dict[str, Any]:
    """Run one experiment to a terminal state.

    Never raises for an expected outcome: a cancel, a timeout and an engine
    fault all close the row and return a summary.
    """
    experiment = db.get(QmlExperiment, experiment_id)
    if experiment is None:
        return {"experiment_id": experiment_id, "status": "missing"}

    if deadline_seconds is None:
        deadline_seconds = training_deadline_seconds()

    experiment.status = RUNNING
    experiment.started_at = datetime.now(timezone.utc)
    experiment.celery_task_id = celery_task_id
    experiment.error = None
    db.commit()

    try:
        # Re-validate in the worker. The row may have been queued before a
        # limit changed, and the stored blob is the only thing standing
        # between a hand-edited row and the engine.
        config = QmlExperimentConfig.model_validate(experiment.config)
        limits.enforce(config)

        rng = np.random.default_rng(config.seed)
        dataset = algorithms.build_dataset_for_config(config, rng)
        if dataset.n_features > config.circuit.n_qubits:
            raise QmlLabError(
                f"dataset '{config.dataset.name}' has {dataset.n_features} features but the "
                f"circuit has {config.circuit.n_qubits} qubits"
            )

        def on_progress(event: ProgressEvent) -> None:
            # Only epoch boundaries are persisted; batch events exist for
            # responsiveness in-process and would otherwise be thousands of
            # writes for data nobody reads.
            if event.message == "epoch":
                db.commit()

        # One dispatch call. Everything that varies by algorithm -- engine,
        # trainer, metric set, baseline, result shape -- is decided inside,
        # from a table, so this path cannot quietly train a VQC for an
        # algorithm the user did not pick.
        outcome = algorithms.run_algorithm(
            config,
            dataset,
            rng,
            on_progress=on_progress,
            should_cancel=CancelPoller(db, experiment_id),
            deadline_seconds=deadline_seconds,
        )

        # The kernel writes no epoch rows: it is a closed-form solve with no
        # loop, so its history is empty by design rather than by omission.
        for record in outcome.history:
            record_epoch(db, experiment_id, record)

        if outcome.interrupted:
            return _finish_interrupted(db, experiment, outcome)

        target = save_model(
            artifact_root(),
            experiment_id,
            config,
            outcome.artifact,
            metrics={
                "task": outcome.task,
                "evaluation": outcome.result.get("evaluation", {}),
                "baseline": outcome.result.get("baseline", {}),
            },
        )

        experiment.model_path = str(target)
        experiment.result = outcome.result
        experiment.status = COMPLETED
        experiment.finished_at = datetime.now(timezone.utc)
        db.commit()

        return {"experiment_id": experiment_id, "status": COMPLETED}

    except QmlLabError as exc:
        return _finish_failed(db, experiment, f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # noqa: BLE001 - any engine fault must still close the row
        logger.exception("QML experiment %s failed", experiment_id)
        return _finish_failed(db, experiment, f"{type(exc).__name__}: {exc}")


def _finish_interrupted(db: Session, experiment: QmlExperiment, outcome) -> dict[str, Any]:
    """Close a run that stopped early, keeping cancel and timeout distinct."""
    if outcome.timed_out:
        experiment.status = TIMED_OUT
        experiment.error = (
            f"Training exceeded its time budget after {outcome.epochs_completed} epoch(s). "
            "Reduce epochs, samples or qubits, or use the backprop differentiation method."
        )
    else:
        experiment.status = CANCELLED
        experiment.error = None

    experiment.result = {
        "interrupted": True,
        "reason": experiment.status,
        "epochs_completed": outcome.epochs_completed,
        "stopped_at_epoch": outcome.cancelled_at_epoch,
        "stopped_at_batch": outcome.cancelled_at_batch,
        "duration_seconds": outcome.duration_seconds,
    }
    # No model is saved for an interrupted run: a half-trained artifact that
    # looks loadable is worse than none at all.
    experiment.model_path = None
    experiment.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {"experiment_id": experiment.id, "status": experiment.status}


def force_terminal(db: Session, experiment_id: int, status: str, message: str | None) -> dict[str, Any]:
    """Close a row from outside the normal path.

    Used by the Celery soft-limit backstop: if the worker is interrupted
    before the engine's own deadline fires, the row would otherwise be left
    ``running`` forever and the concurrency slot never released.
    """
    experiment = db.get(QmlExperiment, experiment_id)
    if experiment is None or experiment.status in TERMINAL_STATUSES:
        return {"experiment_id": experiment_id, "status": "noop"}
    experiment.status = status
    experiment.error = message
    experiment.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {"experiment_id": experiment_id, "status": status}


def _finish_failed(db: Session, experiment: QmlExperiment, message: str) -> dict[str, Any]:
    experiment.status = FAILED
    experiment.error = message
    experiment.finished_at = datetime.now(timezone.utc)
    db.commit()
    return {"experiment_id": experiment.id, "status": FAILED}


# ---------------------------------------------------------------------------
# Inference and capability description
# ---------------------------------------------------------------------------


def run_inference(experiment: QmlExperiment, features: list[list[float]]) -> dict[str, Any]:
    """Predict on new points using the saved artifact.

    Loads from disk rather than re-training, which is what makes this a test
    of the persisted model rather than of a fresh one.
    """
    config = QmlExperimentConfig.model_validate(experiment.config)
    loaded = load_model(artifact_root(), experiment.id)

    # The scaler is part of the dataset build, so rebuild it from the same
    # seed. Deterministic by construction: the same seed yields the same split
    # and therefore the same train-only scaler.
    rng = np.random.default_rng(config.seed)
    dataset = algorithms.build_dataset_for_config(config, rng)

    raw = np.asarray(features, dtype=float)
    if raw.ndim != 2 or raw.shape[1] != dataset.n_features:
        raise ValueError(f"expected rows of {dataset.n_features} features, got shape {tuple(raw.shape)}")

    scaled = dataset.scaler.transform(raw)
    task = algorithms.task_for(config.algorithm)

    # One contract, task-tagged. The response never carries a zeroed field
    # for a task that lacks it: a regression row has no `probabilities`, and
    # a classification row has no `values`. A null there is the same hazard
    # D-033 rejected for results -- a UI renders 0 and it reads as a real
    # prediction of zero.
    payload: dict[str, Any] = {
        "task": task,
        "algorithm": config.algorithm,
        "feature_names": list(dataset.feature_names),
        "n_features": dataset.n_features,
    }

    if config.algorithm == "quantum_kernel":
        from app.quantum.qml_lab.kernel import decision_values as kernel_decision
        from app.quantum.qml_lab.kernel import predict as kernel_predict

        model = algorithms.build_model(config, dataset.n_features)
        rows = model.rectangular(scaled, loaded.support_x)
        payload["predictions"] = [int(v) for v in kernel_predict(loaded.params, rows)]
        # An LSSVM decision value is a signed margin, not a probability.
        # Reporting it as one would be an overclaim, so it is named for what
        # it is (§2C.3's labelling discipline).
        payload["decision_values"] = [
            float(v) for v in kernel_decision(loaded.params, rows)
        ]
        return payload

    if task == "regression":
        if loaded.target_scaler is None:
            raise QmlPersistenceError(
                "regression artifact is missing its target scaler; predictions would be "
                "in scaled units and silently wrong"
            )
        model = algorithms.build_model(config, dataset.n_features)
        # The *stored* scaler, never a refit one.
        values = model.predict(scaled, loaded.params, loaded.target_scaler)
        payload["values"] = [float(v) for v in values]
        payload["target_range"] = [
            float(loaded.target_scaler.y_min),
            float(loaded.target_scaler.y_max),
        ]
        return payload

    model = algorithms.build_model(config, dataset.n_features)
    payload["predictions"] = [int(v) for v in model.predict(scaled, loaded.params)]
    payload["probabilities"] = [
        float(v) for v in model.predict_proba(scaled, loaded.params)
    ]
    return payload


def describe() -> dict[str, Any]:
    """Capability document for the UI: limits, datasets and defaults.

    Served so the browser bounds its inputs with the same numbers the server
    enforces, instead of a hardcoded copy that can drift.
    """
    return {
        "limits": limits.LIMITS,
        # Compatibility field: the datasets valid for ``default_algorithm``.
        # It predates per-algorithm entries and is deliberately NOT the union
        # of all six -- a client reading only this list would otherwise offer
        # `sine` for a VQC, which the schema rejects with a 422.
        # ``algorithms[].datasets`` is the authoritative, task-filtered list
        # (§2C.7).
        "datasets": [
            _describe_dataset(name)
            for name in _datasets_for_task(limits.task_for_algorithm(limits.DEFAULT_ALGORITHM))
        ],
        "diff_methods": ["backprop", "parameter-shift"],
        "rotations": ["X", "Y", "Z"],
        "entanglements": ["ring", "linear", "none"],
        "device": "default.qubit",
        "max_concurrent_experiments": limits.MAX_CONCURRENT_JOBS,
        "statuses": ["queued", "running", "completed", "failed", "cancelled", "timed_out"],
        "default_algorithm": limits.DEFAULT_ALGORITHM,
        "algorithms": _describe_algorithms(),
    }


#: Which metrics a results panel should render, per task. The point of
#: serving this rather than letting the client decide is MT-006: a UI that
#: hardcodes "accuracy" renders 0 for a regression run, and 0 reads as
#: "scored zero" rather than "not applicable" (§2C.4, D-033).
_TASK_METRICS: dict[str, list[str]] = {
    "classification": ["accuracy", "precision", "recall", "f1"],
    "regression": ["mae", "rmse", "r2"],
}

#: Which per-epoch series the training chart should plot, per task.
_TASK_EPOCH_FIELDS: dict[str, list[str]] = {
    "classification": ["train_loss", "train_accuracy", "test_accuracy"],
    "regression": ["train_loss", "test_loss", "train_r2", "test_r2"],
}

_ALGORITHM_META: dict[str, dict[str, Any]] = {
    "vqc": {
        "label": "Variational classifier",
        "task": "classification",
        "summary": "Angle-encoded features, a trainable ansatz, sign of <Z0> as the label.",
    },
    "hybrid_qnn": {
        "label": "Hybrid QNN",
        "task": "classification",
        "summary": (
            "A classical affine layer and tanh feed the encoding angles, so the model "
            "differentiates end to end through autograd (D-031)."
        ),
    },
    "quantum_kernel": {
        "label": "Quantum kernel (LSSVM)",
        "task": "classification",
        "summary": (
            "Fidelity kernel between every pair of samples, fitted by least-squares SVM. "
            "Sample count is capped separately and hard because cost is quadratic (D-032)."
        ),
    },
    "quantum_regression": {
        "label": "Quantum regression",
        "task": "regression",
        "summary": (
            "Raw <Z0> as a continuous prediction, MSE loss, data re-uploading on by "
            "default so the model can represent more than frequency 1 (D-034)."
        ),
    },
}


def _datasets_for_task(task: str) -> tuple[str, ...]:
    """The dataset names valid for a task, from the single registry."""
    return (
        limits.REGRESSION_DATASETS if task == "regression" else limits.CLASSIFICATION_DATASETS
    )


def _describe_dataset(name: str) -> dict[str, Any]:
    """One dataset entry, one key shape for every task (D-032's rule)."""
    from app.quantum.qml_lab import regression_data

    maximum = datasets.DATASET_MAX_SAMPLES.get(name)
    if limits.task_for_dataset(name) == "regression":
        n_features = 2 if name == "linear_mix" else 1
        required = regression_data.REQUIRED_ANGLE_FREQUENCY[name]
    else:
        n_features = 4 if name == "iris_binary" else 2
        required = None
    return {
        "name": name,
        "max_samples": maximum if maximum is not None else limits.MAX_SAMPLES,
        "n_features": n_features,
        "required_angle_frequency": required,
    }


def _describe_algorithms() -> list[dict[str, Any]]:
    """Per-algorithm capability entries, all with an identical key shape.

    §2C.7 requires the config view to show only the options valid for the
    selected algorithm, **driven by this endpoint rather than hardcoded
    client-side**. D-032 guarantees every ``limits_for`` table has the same
    keys, so the UI reads one shape and never branches on algorithm name.
    """
    entries: list[dict[str, Any]] = []
    for name in limits.ALGORITHMS:
        meta = _ALGORITHM_META[name]
        task = meta["task"]

        # Filtered from the one registry, not from a per-branch literal.
        # DATASET_MAX_SAMPLES carries all six names now, so iterating it here
        # is what offered `sine` to a VQC.
        available = [_describe_dataset(dataset) for dataset in _datasets_for_task(task)]

        entries.append(
            {
                "name": name,
                "label": meta["label"],
                "task": task,
                "summary": meta["summary"],
                "limits": limits.limits_for(name),
                "datasets": available,
                "metrics": list(_TASK_METRICS[task]),
                "epoch_fields": list(_TASK_EPOCH_FIELDS[task]),
                "supports": {
                    # the classical hidden layer is hybrid-only
                    "n_hidden": name == "hybrid_qnn",
                    # the kernel is closed-form: epochs is pinned to 1, so a
                    # UI must not offer an epoch slider for it
                    "epochs": name != "quantum_kernel",
                    "diff_method": name != "quantum_kernel",
                    "data_reuploading": name == "quantum_regression",
                },
                "baseline": (
                    "ridge" if task == "regression" else "logistic_regression"
                ),
            }
        )
    return entries
