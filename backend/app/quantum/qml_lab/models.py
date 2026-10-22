"""Pydantic schemas for the QML Lab.

Every model sets ``extra="forbid"``. That is not stylistic. The Noise Lab
schema next door defaults each group to ``enabled: False`` with Pydantic's
default ``extra="ignore"``, so a caller who posts a flat, plausible-looking
payload gets a silently noiseless result that looks like a real answer:

    >>> NoiseConfig(depolarizing=0.35).model_dump()["stochastic"]["enabled"]
    False

A wrong-shaped QML config must fail loudly instead. ``extra="forbid"`` plus
required nesting turns that class of mistake into a 422 the caller can see.
See docs/qml/DECISIONS.md D-006.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.quantum.qml_lab import limits

#: Every dataset the platform can build, classification and regression alike.
#: Kept in step with ``limits.ALL_DATASETS`` by
#: ``test_the_dataset_literal_and_the_registry_cannot_drift`` — a Literal
#: cannot be built from a tuple without losing static typing, so the two are
#: written out and asserted equal rather than derived.
DatasetName = Literal[
    "moons", "circles", "iris_binary", "sine", "damped_cosine", "linear_mix"
]
Rotation = Literal["X", "Y", "Z"]
Entanglement = Literal["ring", "linear", "none"]
DiffMethod = Literal["backprop", "parameter-shift"]
#: Built from limits.ALGORITHMS so the schema and the ceiling table cannot
#: drift apart -- a new algorithm is unacceptable to the API until it is
#: listed there with its ceilings.
Algorithm = Literal["vqc", "hybrid_qnn", "quantum_kernel", "quantum_regression"]
ExperimentStatus = Literal["pending", "running", "completed", "failed", "cancelled"]


class DatasetConfig(BaseModel):
    """Which synthetic or bundled dataset to train on, and how much of it."""

    model_config = ConfigDict(extra="forbid")

    name: DatasetName = Field(default="moons", description="Dataset generator or bundled dataset")
    n_samples: int = Field(
        default=limits.DEFAULT_SAMPLES,
        ge=limits.MIN_SAMPLES,
        le=limits.MAX_SAMPLES,
        description="Total samples before the train/test split",
    )
    noise: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Gaussian jitter for the synthetic generators; ignored by iris_binary",
    )
    test_fraction: float = Field(
        default=0.3,
        ge=0.1,
        le=0.5,
        description="Fraction held out for testing, stratified by class",
    )


class CircuitConfig(BaseModel):
    """Shape of the encoder and the variational ansatz."""

    model_config = ConfigDict(extra="forbid")

    n_qubits: int = Field(
        default=limits.DEFAULT_QUBITS,
        ge=1,
        le=limits.MAX_QUBITS,
        description="Wires in the circuit; must be >= the dataset's feature count",
    )
    n_layers: int = Field(
        default=limits.DEFAULT_LAYERS,
        ge=1,
        le=limits.MAX_LAYERS,
        description="Repetitions of the variational block",
    )
    rotation: Rotation = Field(default="Y", description="Axis used by the angle encoder")
    entanglement: Entanglement = Field(default="ring", description="CNOT topology within a layer")
    n_hidden: int | None = Field(
        default=None,
        ge=1,
        le=limits.MAX_HIDDEN_UNITS,
        description=(
            "Width of the hybrid model's classical layer. Only meaningful for "
            "algorithm='hybrid_qnn'; must not exceed n_qubits, since each emitted "
            "value needs one wire to encode onto. None means 'use n_qubits'."
        ),
    )


class TrainingConfig(BaseModel):
    """Optimiser settings."""

    model_config = ConfigDict(extra="forbid")

    epochs: int = Field(default=limits.DEFAULT_EPOCHS, ge=1, le=limits.MAX_EPOCHS)
    batch_size: int = Field(default=limits.DEFAULT_BATCH_SIZE, ge=1, le=limits.MAX_BATCH_SIZE)
    learning_rate: float = Field(default=0.1, gt=0.0, le=1.0)
    diff_method: DiffMethod = Field(
        default="backprop",
        description=(
            "backprop is the default because parameter-shift costs 1 + 2*n_parameters "
            "circuit executions per sample; both are exact on a simulator"
        ),
    )


class QmlExperimentConfig(BaseModel):
    """A complete, self-contained experiment specification.

    One ``seed`` drives dataset generation, the split and weight
    initialisation, so an experiment is reproducible bit-for-bit from this
    object alone.
    """

    model_config = ConfigDict(extra="forbid")

    algorithm: Algorithm = Field(
        default=limits.DEFAULT_ALGORITHM,
        description=(
            "Which model to fit. Ceilings are enforced per algorithm (2C.1): a "
            "sample count that is fine for a VQC is far outside what a kernel can "
            "finish, because a kernel matrix is O(N^2) circuit evaluations."
        ),
    )
    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    circuit: CircuitConfig = Field(default_factory=CircuitConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    seed: int = Field(default=1234, ge=0, le=2**32 - 1, description="Master seed for the whole run")

    @model_validator(mode="after")
    def _check_algorithm_fit(self) -> "QmlExperimentConfig":
        """Reject combinations the per-field bounds cannot see.

        Pydantic validates each field in isolation, so n_hidden <= n_qubits and
        "n_hidden only means something for a hybrid" both have to be checked
        once the whole object exists. Rejecting loudly here is the 1A rule: a
        field that is silently ignored returns a plausible wrong answer.
        """
        hidden = self.circuit.n_hidden
        if hidden is not None:
            if self.algorithm != "hybrid_qnn":
                raise ValueError(
                    f"circuit.n_hidden is only valid for algorithm='hybrid_qnn', "
                    f"not {self.algorithm!r}"
                )
            if hidden > self.circuit.n_qubits:
                raise ValueError(
                    f"circuit.n_hidden={hidden} exceeds circuit.n_qubits="
                    f"{self.circuit.n_qubits}; angle encoding needs one wire per "
                    f"value emitted by the classical layer"
                )

        # The dataset and the algorithm must solve the same kind of problem.
        # Without this, `algorithm="quantum_regression"` with `dataset="moons"`
        # validates cleanly and then trains a regressor against ±1 class
        # labels -- it runs, reports an R², and means nothing. The inverse is
        # worse: a classifier on `sine` would threshold a continuous target.
        dataset_task = limits.task_for_dataset(self.dataset.name)
        algorithm_task = limits.task_for_algorithm(self.algorithm)
        if dataset_task != algorithm_task:
            raise ValueError(
                f"dataset {self.dataset.name!r} is a {dataset_task} dataset but "
                f"algorithm {self.algorithm!r} solves a {algorithm_task} task; "
                f"choose a {algorithm_task} dataset "
                f"({', '.join(limits.CLASSIFICATION_DATASETS if algorithm_task == 'classification' else limits.REGRESSION_DATASETS)})"
            )
        return self


class EpochRecord(BaseModel):
    """One row of the training history."""

    model_config = ConfigDict(extra="forbid")

    epoch: int = Field(ge=1)
    train_loss: float
    train_accuracy: float
    test_loss: float
    test_accuracy: float
    elapsed_seconds: float


class ProgressEvent(BaseModel):
    """Payload handed to the injected progress callback.

    Deliberately plain data: the engine knows nothing about Celery, HTTP or
    the database, so whatever consumes this is free to persist it, stream it
    or discard it.
    """

    model_config = ConfigDict(extra="forbid")

    epoch: int = Field(ge=0)
    total_epochs: int = Field(ge=1)
    batch: int = Field(ge=0)
    total_batches: int = Field(ge=1)
    train_loss: float | None = None
    message: str = ""


class EvaluationResult(BaseModel):
    """Classification metrics on one split."""

    model_config = ConfigDict(extra="forbid")

    accuracy: float
    precision: float
    recall: float
    f1: float
    confusion_matrix: list[list[int]] = Field(description="[[TN, FP], [FN, TP]]")
    n_samples: int


class RegressionResult(BaseModel):
    """Regression metrics on one split.

    A **separate type**, not EvaluationResult with nullable fields (2C.4).
    A result object whose ``accuracy`` is None invites a UI that renders it
    as 0, and "0" reads as "the model scored zero" -- a lie of a different
    kind than a blank. Keeping the types disjoint means a regression result
    cannot be handed to a view expecting a confusion matrix at all.
    """

    model_config = ConfigDict(extra="forbid")

    mae: float = Field(description="Mean absolute error, in target units")
    rmse: float = Field(description="Root mean squared error, in target units")
    r2: float = Field(description="Coefficient of determination; 1.0 is perfect, 0.0 is the mean")
    n_samples: int


class RegressionEpochRecord(BaseModel):
    """One row of a regression training history.

    Mirrors EpochRecord's shape so the loss-curve chart is reusable, but the
    second series is R^2 rather than accuracy, because accuracy does not
    exist for continuous targets.
    """

    model_config = ConfigDict(extra="forbid")

    epoch: int = Field(ge=1)
    train_loss: float
    train_r2: float
    test_loss: float
    test_r2: float
    elapsed_seconds: float


class BaselineResult(BaseModel):
    """Classical reference model's score, for the quantum-vs-classical view."""

    model_config = ConfigDict(extra="forbid")

    model: str
    train_accuracy: float
    test_accuracy: float
    n_parameters: int
    converged: bool
