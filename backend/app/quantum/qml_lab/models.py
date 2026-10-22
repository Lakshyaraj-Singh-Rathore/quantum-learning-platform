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

from pydantic import BaseModel, ConfigDict, Field

from app.quantum.qml_lab import limits

DatasetName = Literal["moons", "circles", "iris_binary"]
Rotation = Literal["X", "Y", "Z"]
Entanglement = Literal["ring", "linear", "none"]
DiffMethod = Literal["backprop", "parameter-shift"]
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

    dataset: DatasetConfig = Field(default_factory=DatasetConfig)
    circuit: CircuitConfig = Field(default_factory=CircuitConfig)
    training: TrainingConfig = Field(default_factory=TrainingConfig)
    seed: int = Field(default=1234, ge=0, le=2**32 - 1, description="Master seed for the whole run")


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


class BaselineResult(BaseModel):
    """Classical reference model's score, for the quantum-vs-classical view."""

    model_config = ConfigDict(extra="forbid")

    model: str
    train_accuracy: float
    test_accuracy: float
    n_parameters: int
    converged: bool
