"""The dispatch seam: algorithm → dataset, engine, trainer, result, inference.

Before this module, `services.run` built a `VQC` unconditionally. Every layer
above it honoured `config.algorithm` — the schema validated it, `limits`
capped per-algorithm, `/qml/describe` advertised four algorithms — and then
the one layer that mattered ignored it. Selecting "Quantum regression"
trained a classifier and reported accuracy. That is a wrong answer dressed as
a right one, and it is the single thing this module exists to prevent.

Everything that varies by algorithm is declared **once, in a table**, rather
than as `if algorithm == ...` scattered through the service. A new algorithm
is then a row, and the invariant tests in `test_qml_dispatch.py` fail loudly
if a row is incomplete.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from app.quantum.qml_lab import datasets as datasets_mod
from app.quantum.qml_lab import evaluator, limits, trainer
from app.quantum.qml_lab import regression_data as regression_mod
from app.quantum.qml_lab.baseline import LogisticRegressionBaseline
from app.quantum.qml_lab.errors import QmlConfigError
from app.quantum.qml_lab.hybrid import HybridQNN
from app.quantum.qml_lab.kernel import QuantumKernel, decision_values, fit_lssvm, predict
from app.quantum.qml_lab.models import (
    DatasetConfig,
    ProgressEvent,
    QmlExperimentConfig,
    TrainingConfig,
)
from app.quantum.qml_lab.regression import QuantumRegressor, evaluate_regression
from app.quantum.qml_lab.regression_data import RidgeBaseline
from app.quantum.qml_lab.vqc import VQC

#: Re-exported so callers have one place to ask. The table itself lives in
#: ``limits`` because ``models`` needs it and cannot import this module.
TASK_BY_ALGORITHM = limits.TASK_BY_ALGORITHM

#: Engine class name per algorithm. Asserted distinct by
#: ``test_the_four_algorithms_do_not_all_build_the_same_engine`` — the guard
#: against a dispatcher that quietly returns ``VQC`` for everything.
ENGINE_BY_ALGORITHM: dict[str, str] = {
    "vqc": "VQC",
    "hybrid_qnn": "HybridQNN",
    "quantum_kernel": "QuantumKernel",
    "quantum_regression": "QuantumRegressor",
}


def task_for(algorithm: str) -> str:
    return limits.task_for_algorithm(algorithm)


def is_regression(algorithm: str) -> bool:
    return task_for(algorithm) == "regression"


def has_epoch_loop(algorithm: str) -> bool:
    """Whether this algorithm trains iteratively.

    The kernel does not: it is a closed-form linear solve, `describe()` pins
    its epochs to 1, and there is no loop to report. It must therefore write
    **no** epoch rows — manufacturing one to satisfy a persistence path that
    expects them would mean inventing a `train_accuracy` for an epoch that
    never happened.
    """
    return algorithm != "quantum_kernel"


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------


def build_dataset_for_task(config: DatasetConfig, task: str, rng: np.random.Generator):
    """Build the dataset appropriate to ``task``.

    Two builders exist because the splits genuinely differ: the
    classification split is *stratified* (it balances classes), which is
    meaningless for a continuous target.
    """
    if task == "regression":
        return regression_mod.build_regression_dataset(
            config.name, config.n_samples, config.noise, config.test_fraction, rng
        )
    if task == "classification":
        return datasets_mod.build_dataset(config, rng)
    raise QmlConfigError(f"unknown task {task!r}")


def build_dataset_for_config(config: QmlExperimentConfig, rng: np.random.Generator):
    return build_dataset_for_task(config.dataset, task_for(config.algorithm), rng)


# ---------------------------------------------------------------------------
# Engines
# ---------------------------------------------------------------------------


def build_model(config: QmlExperimentConfig, n_features: int):
    """Construct the engine the config actually asked for."""
    algorithm = config.algorithm
    circuit = config.circuit

    if algorithm == "vqc":
        return VQC(circuit, n_features, config.training.diff_method)
    if algorithm == "hybrid_qnn":
        return HybridQNN(
            circuit,
            n_features=n_features,
            n_hidden=circuit.n_hidden or limits.DEFAULT_HIDDEN_UNITS,
            diff_method=config.training.diff_method,
        )
    if algorithm == "quantum_regression":
        return QuantumRegressor(circuit, n_features, config.training.diff_method)
    if algorithm == "quantum_kernel":
        return QuantumKernel(circuit, n_features)
    raise QmlConfigError(f"no engine registered for algorithm {algorithm!r}")


# ---------------------------------------------------------------------------
# A single outcome shape the service can consume regardless of algorithm
# ---------------------------------------------------------------------------


@dataclass
class DispatchOutcome:
    """What every algorithm returns, so the service has one code path."""

    status: str
    task: str
    history: list  # EpochRecord | RegressionEpochRecord, possibly empty
    epochs_completed: int
    duration_seconds: float
    #: Engine-specific trained state, handed back to persistence.
    artifact: Any
    #: The task-shaped result payload, already a plain dict.
    result: dict[str, Any]
    cancelled_at_epoch: int | None = None
    cancelled_at_batch: int | None = None
    timed_out: bool = False

    @property
    def interrupted(self) -> bool:
        return self.status in {"cancelled", "timed_out"}


def run_algorithm(
    config: QmlExperimentConfig,
    dataset,
    rng: np.random.Generator,
    *,
    on_progress: Callable[[ProgressEvent], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    deadline_seconds: float | None = None,
) -> DispatchOutcome:
    """Train and evaluate, by algorithm, returning one uniform outcome."""
    algorithm = config.algorithm
    if algorithm == "quantum_kernel":
        return _run_kernel(config, dataset, rng, on_progress=on_progress)
    if is_regression(algorithm):
        return _run_regression(
            config,
            dataset,
            rng,
            on_progress=on_progress,
            should_cancel=should_cancel,
            deadline_seconds=deadline_seconds,
        )
    return _run_classifier(
        config,
        dataset,
        rng,
        on_progress=on_progress,
        should_cancel=should_cancel,
        deadline_seconds=deadline_seconds,
    )


def _run_classifier(config, dataset, rng, *, on_progress, should_cancel, deadline_seconds):
    """VQC and the hybrid: same trainer, same metrics, different engine.

    The hybrid needs no trainer change — it already exposes ``VQC``'s method
    surface, which is why it trained through the unmodified trainer in Phase 5.
    """
    model = build_model(config, dataset.n_features)
    outcome = trainer.train(
        model,
        dataset,
        config.training,
        rng,
        model.initialise(rng),
        on_progress=on_progress,
        should_cancel=should_cancel,
        deadline_seconds=deadline_seconds,
    )

    if outcome.status in {"cancelled", "timed_out"}:
        return DispatchOutcome(
            status=outcome.status,
            task="classification",
            history=outcome.history,
            epochs_completed=outcome.epochs_completed,
            duration_seconds=outcome.duration_seconds,
            artifact=outcome.params,
            result={},
            cancelled_at_epoch=outcome.cancelled_at_epoch,
            cancelled_at_batch=outcome.cancelled_at_batch,
            timed_out=outcome.status == "timed_out",
        )

    predictions = model.predict(dataset.x_test, outcome.params)
    evaluation = evaluator.evaluate(dataset.y_test, predictions)
    baseline = LogisticRegressionBaseline().fit(
        dataset.x_train, dataset.y_train, np.random.default_rng(config.seed)
    )
    baseline_payload = {
        "model": "logistic_regression",
        "train_accuracy": float(
            evaluator.accuracy(dataset.y_train, baseline.predict(dataset.x_train))
        ),
        "test_accuracy": float(
            evaluator.accuracy(dataset.y_test, baseline.predict(dataset.x_test))
        ),
        "n_parameters": int(np.asarray(baseline.coefficients).size + 1),
        "converged": bool(baseline.converged),
    }

    return DispatchOutcome(
        status="completed",
        task="classification",
        history=outcome.history,
        epochs_completed=outcome.epochs_completed,
        duration_seconds=outcome.duration_seconds,
        artifact=outcome.params,
        result={
            "task": "classification",
            "algorithm": config.algorithm,
            "evaluation": evaluation.model_dump(),
            "baseline": baseline_payload,
            "circuit": model.describe(),
            "dataset": dataset.summary(),
            "epochs_completed": outcome.epochs_completed,
            "duration_seconds": outcome.duration_seconds,
            "final_train_loss": outcome.history[-1].train_loss if outcome.history else None,
            "final_train_accuracy": (
                outcome.history[-1].train_accuracy if outcome.history else None
            ),
        },
    )


def _run_regression(config, dataset, rng, *, on_progress, should_cancel, deadline_seconds):
    """Regression: MSE loss, R² history, metrics in the user's own units."""
    model = build_model(config, dataset.n_features)
    outcome = regression_mod.train_regression(
        model,
        dataset,
        config.training,
        rng,
        model.initialise(rng),
        on_progress=on_progress,
        should_cancel=should_cancel,
        deadline_seconds=deadline_seconds,
    )

    if outcome.status in {"cancelled", "timed_out"}:
        return DispatchOutcome(
            status=outcome.status,
            task="regression",
            history=outcome.history,
            epochs_completed=outcome.epochs_completed,
            duration_seconds=outcome.duration_seconds,
            artifact=(outcome.params, dataset.target_scaler),
            result={},
            cancelled_at_epoch=outcome.cancelled_at_epoch,
            cancelled_at_batch=outcome.cancelled_at_batch,
            timed_out=outcome.status == "timed_out",
        )

    # Metrics are computed against the raw targets, after mapping predictions
    # back through the train-fitted scaler -- so MAE and RMSE are in the
    # user's units, not the [-1, 1] the circuit works in.
    predictions = model.predict(dataset.x_test, outcome.params, dataset.target_scaler)
    evaluation = evaluate_regression(dataset.y_test, predictions)

    ridge = RidgeBaseline().fit(dataset.x_train, dataset.y_train)
    ridge_metrics = evaluate_regression(dataset.y_test, ridge.predict(dataset.x_test))

    return DispatchOutcome(
        status="completed",
        task="regression",
        history=outcome.history,
        epochs_completed=outcome.epochs_completed,
        duration_seconds=outcome.duration_seconds,
        artifact=(outcome.params, dataset.target_scaler),
        result={
            "task": "regression",
            "algorithm": config.algorithm,
            "evaluation": evaluation.model_dump(),
            "baseline": {
                "model": "ridge",
                "mae": ridge_metrics.mae,
                "rmse": ridge_metrics.rmse,
                "r2": ridge_metrics.r2,
                "n_parameters": int(np.asarray(ridge.coefficients).size + 1),
            },
            "circuit": model.describe(),
            "dataset": dataset.summary(),
            "epochs_completed": outcome.epochs_completed,
            "duration_seconds": outcome.duration_seconds,
            "final_train_loss": outcome.history[-1].train_loss if outcome.history else None,
            "final_train_r2": outcome.history[-1].train_r2 if outcome.history else None,
        },
    )


def _run_kernel(config, dataset, rng, *, on_progress):
    """Closed-form LSSVM. No epoch loop, and therefore no epoch rows.

    The progress contract is honest about that: two events naming the real
    phases (building the Gram matrix, then solving), rather than a synthetic
    epoch invented to satisfy a caller that expects one.
    """
    import time

    started = time.perf_counter()
    model = build_model(config, dataset.n_features)

    def emit(message: str, fraction: float) -> None:
        if on_progress is not None:
            on_progress(
                ProgressEvent(
                    epoch=1,
                    total_epochs=1,
                    batch=int(fraction * 100),
                    total_batches=100,
                    message=message,
                )
            )

    emit("kernel:gram", 0.0)
    gram = model.gram(dataset.x_train)
    emit("kernel:solve", 0.8)

    signed = np.where(dataset.y_train == 0, -1.0, 1.0)
    fit = fit_lssvm(gram, signed, gamma=1.0)

    test_kernel = model.rectangular(dataset.x_test, dataset.x_train)
    evaluation = evaluator.evaluate(dataset.y_test, predict(fit, test_kernel))
    train_predictions = predict(fit, gram)

    baseline = LogisticRegressionBaseline().fit(
        dataset.x_train, dataset.y_train, np.random.default_rng(config.seed)
    )
    emit("kernel:done", 1.0)

    duration = time.perf_counter() - started
    return DispatchOutcome(
        status="completed",
        task="classification",
        history=[],  # deliberate: no epochs happened
        epochs_completed=0,
        duration_seconds=duration,
        artifact=(fit, dataset.x_train),
        result={
            "task": "classification",
            "algorithm": "quantum_kernel",
            "evaluation": evaluation.model_dump(),
            "baseline": {
                "model": "logistic_regression",
                "train_accuracy": float(
                    evaluator.accuracy(dataset.y_train, baseline.predict(dataset.x_train))
                ),
                "test_accuracy": float(
                    evaluator.accuracy(dataset.y_test, baseline.predict(dataset.x_test))
                ),
                "n_parameters": int(np.asarray(baseline.coefficients).size + 1),
                "converged": bool(baseline.converged),
            },
            "circuit": model.describe(),
            "dataset": dataset.summary(),
            "epochs_completed": 0,
            "duration_seconds": duration,
            # Named so a reader cannot mistake these for epoch metrics.
            "kernel": {
                "classifier": "LSSVM",
                "n_support": fit.n_support,
                "gamma": fit.gamma,
                "train_accuracy": float(evaluator.accuracy(dataset.y_train, train_predictions)),
                "evaluations": _kernel_evaluation_count(dataset),
                "gram_preview": _gram_preview(gram),
            },
            "final_train_loss": None,
            "final_train_accuracy": None,
        },
    )


def _kernel_evaluation_count(dataset) -> dict[str, int]:
    from app.quantum.qml_lab.kernel import kernel_evaluations

    return kernel_evaluations(int(dataset.x_train.shape[0]), int(dataset.x_test.shape[0]))


#: Largest Gram matrix shipped in the result JSON. The full 250×250 matrix is
#: 62,500 floats; a result blob that large is slow to read and nothing renders
#: it at full resolution anyway.
GRAM_PREVIEW_MAX = 40


def _gram_preview(gram: np.ndarray) -> dict[str, Any]:
    """A bounded, honest slice of the Gram matrix for the heatmap.

    ``truncated`` is reported so the UI can say so rather than implying the
    user is looking at the whole matrix.
    """
    n = int(gram.shape[0])
    size = min(n, GRAM_PREVIEW_MAX)
    return {
        "size": size,
        "n_total": n,
        "truncated": size < n,
        "symmetric": True,
        "unit_diagonal": True,
        "values": [[round(float(v), 6) for v in row[:size]] for row in gram[:size]],
    }
