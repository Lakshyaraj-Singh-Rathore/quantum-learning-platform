"""QML Lab engine — variational quantum classifiers on a local simulator.

A pure library: no FastAPI, no Celery, no database. The API layer and the
Celery task added in Phase 2 orchestrate these pieces; nothing in this package
imports them, which is what lets the whole engine be tested without a broker.

Typical use::

    rng = np.random.default_rng(config.seed)          # one generator per run
    dataset = datasets.build_dataset(config.dataset, rng)
    model = VQC(config.circuit, dataset.n_features, config.training.diff_method)
    outcome = trainer.train(model, dataset, config.training, rng, model.initialise(rng))
    result = evaluator.evaluate(dataset.y_test, model.predict(dataset.x_test, outcome.params))

The single ``rng`` threaded through dataset generation, the split, batch
shuffling and weight initialisation is what makes a run reproducible
bit-for-bit from ``config.seed`` alone.
"""

from __future__ import annotations

from app.quantum.qml_lab import (
    baseline,
    circuit,
    datasets,
    encoder,
    evaluator,
    limits,
    models,
    persistence,
    trainer,
    vqc,
)
from app.quantum.qml_lab.errors import (
    QmlCancelledError,
    QmlConfigError,
    QmlDatasetError,
    QmlLabError,
    QmlLimitExceededError,
    QmlPersistenceError,
)
from app.quantum.qml_lab.models import (
    CircuitConfig,
    DatasetConfig,
    EvaluationResult,
    QmlExperimentConfig,
    TrainingConfig,
)
from app.quantum.qml_lab.vqc import VQC, Parameters

__all__ = [
    "VQC",
    "CircuitConfig",
    "DatasetConfig",
    "EvaluationResult",
    "Parameters",
    "QmlCancelledError",
    "QmlConfigError",
    "QmlDatasetError",
    "QmlExperimentConfig",
    "QmlLabError",
    "QmlLimitExceededError",
    "QmlPersistenceError",
    "TrainingConfig",
    "baseline",
    "circuit",
    "datasets",
    "encoder",
    "evaluator",
    "limits",
    "models",
    "persistence",
    "trainer",
    "vqc",
]
