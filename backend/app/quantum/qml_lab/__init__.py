"""QML Lab engine — variational quantum classifiers on a local simulator.

A pure library: no FastAPI, no Celery, no database. The API layer and the
Celery task added in Phase 2 orchestrate these pieces; nothing in this package
imports them, which is what lets the whole engine be tested without a broker.

Typical use::

    rng = np.random.default_rng(config.seed)          # one generator per run
    dataset = algorithms.build_dataset_for_config(config, rng)
    outcome = algorithms.run_algorithm(config, dataset, rng)
    result = outcome.result

``algorithms`` is the only entry point that is correct for all four
algorithms. The older ``datasets.build_dataset`` + ``VQC`` + ``trainer.train``
sequence is still what happens *inside* ``run_algorithm`` for the classifiers,
but writing it out by hand silently trains a VQC whatever the config says, and
raises on a regression dataset.

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
