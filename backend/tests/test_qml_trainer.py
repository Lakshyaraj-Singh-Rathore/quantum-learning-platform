"""Training loop: real optimisation, injectable callbacks, clean cancellation.

Cancellation is tested without Celery, which is the point of keeping the
engine free of any Celery import: ``should_cancel`` is just a callable, so the
worker's behaviour can be reproduced here exactly.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.quantum.qml_lab import trainer
from app.quantum.qml_lab.datasets import build_dataset
from app.quantum.qml_lab.errors import QmlCancelledError
from app.quantum.qml_lab.models import (
    CircuitConfig,
    DatasetConfig,
    ProgressEvent,
    TrainingConfig,
)
from app.quantum.qml_lab.vqc import VQC


def _fixture(epochs=4, batch_size=8, n_samples=40, n_qubits=2, n_layers=1, lr=0.2, seed=7):
    rng = np.random.default_rng(seed)
    dataset = build_dataset(DatasetConfig(name="moons", n_samples=n_samples, noise=0.1), rng)
    model = VQC(CircuitConfig(n_qubits=n_qubits, n_layers=n_layers), dataset.n_features, "backprop")
    params = model.initialise(rng)
    config = TrainingConfig(epochs=epochs, batch_size=batch_size, learning_rate=lr)
    return model, dataset, config, rng, params


# --------------------------------------------------------------------------
# Optimisation
# --------------------------------------------------------------------------


def test_training_reduces_a_real_loss_and_moves_the_parameters():
    model, dataset, config, rng, start = _fixture(epochs=6, lr=0.25)
    outcome = trainer.train(model, dataset, config, rng, start)

    assert outcome.status == "completed"
    assert outcome.epochs_completed == 6
    assert len(outcome.history) == 6

    assert outcome.history[-1].train_loss < outcome.history[0].train_loss
    assert np.linalg.norm(outcome.params.theta - start.theta) > 1e-3


def test_the_starting_parameters_are_not_mutated():
    """The caller's object must survive training so it can be compared against."""
    model, dataset, config, rng, start = _fixture(epochs=2)
    before = start.theta.copy()
    trainer.train(model, dataset, config, rng, start)
    assert np.array_equal(start.theta, before)


def test_history_rows_are_well_formed():
    model, dataset, config, rng, start = _fixture(epochs=3)
    outcome = trainer.train(model, dataset, config, rng, start)

    for index, record in enumerate(outcome.history, start=1):
        assert record.epoch == index
        assert np.isfinite(record.train_loss) and record.train_loss >= 0.0
        assert 0.0 <= record.train_accuracy <= 1.0
        assert 0.0 <= record.test_accuracy <= 1.0
        assert record.elapsed_seconds >= 0.0

    assert [r.elapsed_seconds for r in outcome.history] == sorted(r.elapsed_seconds for r in outcome.history)


def test_same_seed_reproduces_the_same_training_run():
    results = []
    for _ in range(2):
        model, dataset, config, rng, start = _fixture(epochs=3, seed=21)
        outcome = trainer.train(model, dataset, config, rng, start)
        results.append(outcome)

    assert np.array_equal(results[0].params.theta, results[1].params.theta)
    assert [r.train_loss for r in results[0].history] == [r.train_loss for r in results[1].history]


def test_square_loss_matches_a_hand_computed_value():
    values = np.array([0.5, -0.5, 1.0])
    labels = np.array([1.0, -1.0, -1.0])
    # ((1-0.5)^2 + (-1+0.5)^2 + (-1-1)^2) / 3 = (0.25 + 0.25 + 4) / 3
    assert float(trainer.square_loss(values, labels)) == pytest.approx(4.5 / 3)


def test_label_mapping_is_plus_minus_one():
    assert np.array_equal(trainer.to_pm1(np.array([0, 1, 1, 0])), np.array([-1.0, 1.0, 1.0, -1.0]))


def test_batch_size_larger_than_the_dataset_is_handled():
    model, dataset, config, rng, start = _fixture(epochs=2, batch_size=32, n_samples=20)
    outcome = trainer.train(model, dataset, config, rng, start)
    assert outcome.status == "completed"
    assert len(outcome.history) == 2


# --------------------------------------------------------------------------
# Progress callbacks
# --------------------------------------------------------------------------


def test_progress_is_reported_for_batches_and_epochs():
    model, dataset, config, rng, start = _fixture(epochs=2, batch_size=8, n_samples=40)
    events: list[ProgressEvent] = []

    outcome = trainer.train(model, dataset, config, rng, start, on_progress=events.append)

    assert outcome.status == "completed"
    epoch_events = [e for e in events if e.message == "epoch"]
    batch_events = [e for e in events if e.message == "batch"]

    assert len(epoch_events) == 2
    assert len(batch_events) >= 2
    assert all(e.total_epochs == 2 for e in events)
    assert all(1 <= e.batch <= e.total_batches for e in batch_events)
    assert epoch_events[-1].train_loss is not None


def test_training_works_without_any_callbacks():
    model, dataset, config, rng, start = _fixture(epochs=2)
    assert trainer.train(model, dataset, config, rng, start).status == "completed"


# --------------------------------------------------------------------------
# Cancellation
# --------------------------------------------------------------------------


def test_cancel_before_the_first_batch_stops_immediately_without_raising():
    model, dataset, config, rng, start = _fixture(epochs=5)
    outcome = trainer.train(model, dataset, config, rng, start, should_cancel=lambda: True)

    assert outcome.status == "cancelled"
    assert outcome.cancelled is True
    assert outcome.epochs_completed == 0
    assert outcome.history == []
    assert outcome.cancelled_at_epoch == 1
    assert outcome.cancelled_at_batch == 0


def test_cancel_mid_training_keeps_the_partial_history():
    model, dataset, config, rng, start = _fixture(epochs=10, batch_size=8, n_samples=40)

    calls = {"n": 0}

    def should_cancel() -> bool:
        calls["n"] += 1
        return calls["n"] > 7  # let a couple of epochs complete first

    outcome = trainer.train(model, dataset, config, rng, start, should_cancel=should_cancel)

    assert outcome.status == "cancelled"
    assert 0 < outcome.epochs_completed < 10
    assert len(outcome.history) == outcome.epochs_completed
    assert np.all(np.isfinite(outcome.params.theta))


def test_cancellation_is_checked_at_the_epoch_boundary_too():
    """A cancel arriving during the final batch must not start a new epoch."""
    # 40 samples, 30% held out -> 28 training rows, so a batch size of 32 is
    # clamped to one batch per epoch and the checks alternate strictly
    # pre-batch / post-epoch.
    model, dataset, config, rng, start = _fixture(epochs=6, batch_size=32, n_samples=40)

    seen: list[str] = []

    def should_cancel() -> bool:
        seen.append("check")
        return len(seen) == 2  # the post-epoch check of epoch 1

    outcome = trainer.train(model, dataset, config, rng, start, should_cancel=should_cancel)

    assert outcome.status == "cancelled"
    assert outcome.epochs_completed == 1
    assert len(outcome.history) == 1, "the completed epoch's history must be kept"
    assert outcome.cancelled_at_epoch == 1
    assert outcome.cancelled_at_batch == 1  # the single batch of that epoch


def test_cancellation_never_leaks_an_exception():
    model, dataset, config, rng, start = _fixture(epochs=3)

    def explode_if_uncaught() -> bool:
        return True

    try:
        outcome = trainer.train(model, dataset, config, rng, start, should_cancel=explode_if_uncaught)
    except QmlCancelledError:  # pragma: no cover - this is the failure being guarded
        pytest.fail("QmlCancelledError escaped train(); cancellation must be an outcome, not an exception")

    assert outcome.status == "cancelled"


def test_a_completed_run_is_not_marked_cancelled():
    model, dataset, config, rng, start = _fixture(epochs=2)
    outcome = trainer.train(model, dataset, config, rng, start, should_cancel=lambda: False)

    assert outcome.status == "completed"
    assert outcome.cancelled is False
    assert outcome.cancelled_at_epoch is None
    assert outcome.final_record() is not None
