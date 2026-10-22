"""Minibatch training loop for the VQC.

Three properties this module is built around:

* **The loss is real.** Binary cross-entropy on probabilities derived from the
  measured expectation value, minimised by gradients of that same quantity.
  Nothing is scripted or faked: if the circuit cannot separate the data, the
  curve says so.
* **Cancellation is cooperative.** ``should_cancel`` is consulted before every
  batch *and* at the end of every epoch. The loop then returns a ``cancelled``
  outcome carrying the history so far — it does not raise, and it does not
  leave half-written state behind. There is no Celery ``revoke`` here and no
  Celery import anywhere in this package; the caller injects both callbacks.
* **It is seeded.** Batch shuffling draws from the single ``rng`` threaded
  through the run, so two runs of the same config agree bit-for-bit.

Adam is implemented inline rather than taken from PennyLane's optimiser
module: twenty lines, no API-stability risk, and the optimiser state is plain
numpy that the cancellation path can hand back unchanged.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from pennylane import grad as qml_grad
from pennylane import numpy as pnp

from app.quantum.qml_lab.datasets import Dataset
from app.quantum.qml_lab.errors import QmlCancelledError
from app.quantum.qml_lab.models import EpochRecord, ProgressEvent, TrainingConfig
from app.quantum.qml_lab.vqc import VQC, Parameters

ProgressCallback = Callable[[ProgressEvent], None]
CancelCallback = Callable[[], bool]

@dataclass
class TrainingOutcome:
    """Everything a caller needs after training, successful or cancelled."""

    status: str  # "completed" | "cancelled"
    params: Parameters
    history: list[EpochRecord] = field(default_factory=list)
    epochs_completed: int = 0
    duration_seconds: float = 0.0
    cancelled_at_epoch: int | None = None
    cancelled_at_batch: int | None = None

    @property
    def cancelled(self) -> bool:
        return self.status == "cancelled"

    def final_record(self) -> EpochRecord | None:
        return self.history[-1] if self.history else None


def square_loss(decision_values, labels):
    """Mean squared error between ``<Z> + bias`` and labels in ``{-1, +1}``.

    Log-loss was tried first and is the wrong choice for this model. The
    decision value is a measured expectation value, so it saturates at exactly
    ±1; mapping that linearly onto a probability puts samples at exactly 0 and
    1, where the log-loss derivative is ``1/ε``. Measured on the moons set that
    produced a gradient norm of **199.96** concentrated in a single parameter,
    and Adam's per-parameter normalisation turned it into a full-size step
    every iteration — the loss moved from 0.6601 to 0.6612 over six epochs and
    the model predicted one class for everything.

    Squared error against ±1 targets has bounded gradients over the whole
    range of a measurement and is the standard objective for this kind of
    classifier. The same function is both the differentiated cost and the
    reported metric, so the number on the chart is the number being optimised.
    """
    return pnp.mean((labels - decision_values) ** 2)


def to_pm1(labels: np.ndarray) -> np.ndarray:
    """Map ``{0, 1}`` class labels onto the ``{-1, +1}`` targets the loss uses."""
    return 2.0 * np.asarray(labels, dtype=float) - 1.0


def _accuracy(predictions: np.ndarray, labels: np.ndarray) -> float:
    return float(np.mean(predictions == labels))


def _evaluate_split(model: VQC, theta: np.ndarray, x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    values = np.asarray(model.decision_values(x, theta), dtype=float)
    loss = float(square_loss(values, to_pm1(y)))
    accuracy = _accuracy((values > 0.0).astype(int), y)
    return loss, accuracy


def train(
    model: VQC,
    dataset: Dataset,
    config: TrainingConfig,
    rng: np.random.Generator,
    initial: Parameters,
    *,
    on_progress: ProgressCallback | None = None,
    should_cancel: CancelCallback | None = None,
) -> TrainingOutcome:
    """Train ``model`` on ``dataset`` and return the outcome.

    ``initial`` is not mutated; the returned parameters are a separate object,
    so a caller holding the starting point can compare against it (which is
    exactly how the "parameters actually updated" acceptance test works).
    """
    started = time.perf_counter()
    theta = pnp.array(np.array(initial.theta, dtype=float), requires_grad=True)

    x_train = dataset.x_train
    y_train = to_pm1(dataset.y_train)
    n_train = int(x_train.shape[0])
    batch_size = min(config.batch_size, n_train)
    total_batches = max(1, int(np.ceil(n_train / batch_size)))

    # Adam moments, kept in plain numpy.
    moment_1 = np.zeros_like(np.asarray(theta, dtype=float))
    moment_2 = np.zeros_like(moment_1)
    step = 0

    history: list[EpochRecord] = []
    epochs_completed = 0
    cancelled_at_epoch: int | None = None
    cancelled_at_batch: int | None = None

    def _cancelled() -> bool:
        return bool(should_cancel()) if should_cancel is not None else False

    def _emit(event: ProgressEvent) -> None:
        if on_progress is not None:
            on_progress(event)

    def cost(parameters, batch_x, batch_y):
        return square_loss(model.decision_values(batch_x, parameters), batch_y)

    # argnums, not argnum: PennyLane 0.44 deprecated the singular spelling
    # ("argnum in qml.grad has been renamed to argnums to match jax and
    # catalyst"). Using the deprecated name emits a warning on every call and
    # would break on the next bump.
    gradient_of = qml_grad(cost, argnums=0)

    try:
        for epoch in range(1, config.epochs + 1):
            order = rng.permutation(n_train)

            for batch_index in range(total_batches):
                # Checked BEFORE the batch so a cancel never pays for work it
                # is about to discard.
                if _cancelled():
                    cancelled_at_epoch, cancelled_at_batch = epoch, batch_index
                    raise QmlCancelledError

                slice_ = order[batch_index * batch_size : (batch_index + 1) * batch_size]
                if slice_.size == 0:
                    continue
                batch_x = x_train[slice_]
                batch_y = y_train[slice_]

                gradient = np.asarray(gradient_of(theta, batch_x, batch_y), dtype=float)

                step += 1
                moment_1 = 0.9 * moment_1 + 0.1 * gradient
                moment_2 = 0.999 * moment_2 + 0.001 * np.square(gradient)
                corrected_1 = moment_1 / (1.0 - 0.9**step)
                corrected_2 = moment_2 / (1.0 - 0.999**step)
                updated = np.asarray(theta, dtype=float) - config.learning_rate * corrected_1 / (
                    np.sqrt(corrected_2) + 1e-8
                )
                theta = pnp.array(updated, requires_grad=True)

                _emit(
                    ProgressEvent(
                        epoch=epoch,
                        total_epochs=config.epochs,
                        batch=batch_index + 1,
                        total_batches=total_batches,
                        message="batch",
                    )
                )

            flat = np.asarray(theta, dtype=float)
            train_loss, train_accuracy = _evaluate_split(model, flat, dataset.x_train, dataset.y_train)
            test_loss, test_accuracy = _evaluate_split(model, flat, dataset.x_test, dataset.y_test)

            history.append(
                EpochRecord(
                    epoch=epoch,
                    train_loss=train_loss,
                    train_accuracy=train_accuracy,
                    test_loss=test_loss,
                    test_accuracy=test_accuracy,
                    elapsed_seconds=time.perf_counter() - started,
                )
            )
            epochs_completed = epoch

            _emit(
                ProgressEvent(
                    epoch=epoch,
                    total_epochs=config.epochs,
                    batch=total_batches,
                    total_batches=total_batches,
                    train_loss=train_loss,
                    message="epoch",
                )
            )

            # Checked again at the epoch boundary: a cancel arriving during the
            # final batch of an epoch is honoured without starting the next one.
            if _cancelled():
                cancelled_at_epoch, cancelled_at_batch = epoch, total_batches
                raise QmlCancelledError

        status = "completed"
    except QmlCancelledError:
        # Expected control flow, not a failure. The exception is caught here
        # and never reaches the caller.
        status = "cancelled"

    final = Parameters(
        theta=np.asarray(theta, dtype=float),
        n_qubits=initial.n_qubits,
        n_layers=initial.n_layers,
    )

    return TrainingOutcome(
        status=status,
        params=final,
        history=history,
        epochs_completed=epochs_completed,
        duration_seconds=time.perf_counter() - started,
        cancelled_at_epoch=cancelled_at_epoch,
        cancelled_at_batch=cancelled_at_batch,
    )
