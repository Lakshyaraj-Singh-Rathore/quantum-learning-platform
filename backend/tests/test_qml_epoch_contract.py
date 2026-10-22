"""The capability document and the history endpoint must agree, both ways.

`/qml/describe` tells the client which per-epoch series exist for an
algorithm (`epoch_fields`); `load_history` is where those series actually
come from. Nothing in the build made the two agree, and they drifted in
*both* directions at once:

  - `quantum_regression` advertised `train_r2` and `test_r2`, which
    `load_history` never serialised, so the client asked for a series that
    no response could contain and drew an empty chart.
  - every classification algorithm omitted `test_loss` from `epoch_fields`
    while `load_history` returned it, so a client that trusted the document
    silently dropped a curve it could have drawn.

A one-directional test would have caught one of those and blessed the other.
These assert the equivalence, which is the only form that closes both ends.

This is the fourth appearance of this defect shape (frozen `LIMITS`, then
`ALGORITHM_LIMITS`; `describe()`'s dataset advertisement versus the schema
*and* the route; `trainer.train`'s parameter type). The lesson each time was
the same: a rule proved at one construction site is not proved at the
others. So these tests enumerate every algorithm from the registry rather
than naming any, and a fifth algorithm is covered the day it is added.
"""

from __future__ import annotations

import pytest

from app.database import SessionLocal
from app.quantum.qml_lab.limits import TASK_BY_ALGORITHM
from app.quantum.qml_lab.models import EpochRecord, RegressionEpochRecord
from app.services.qml_lab import _TASK_EPOCH_FIELDS, describe, load_history

#: Keys `load_history` emits that are bookkeeping, not plotted metrics.
_NON_METRIC_KEYS = {"epoch", "elapsed_seconds"}

#: The engine-side record each task's trainer actually produces. This is the
#: ground truth: a series can only exist if some record carries it.
_RECORD_FOR_TASK = {
    "classification": EpochRecord,
    "regression": RegressionEpochRecord,
}


def _metric_fields(model) -> set[str]:
    return set(model.model_fields) - _NON_METRIC_KEYS


@pytest.mark.parametrize("task", sorted(_TASK_EPOCH_FIELDS))
def test_advertised_fields_are_exactly_what_the_engine_records(task: str) -> None:
    """document == engine.

    Catches both drift directions at the source: advertising a metric no
    record carries, and recording one the document never mentions.
    """
    advertised = set(_TASK_EPOCH_FIELDS[task])
    recorded = _metric_fields(_RECORD_FOR_TASK[task])

    assert advertised == recorded, (
        f"{task}: epoch_fields and the epoch record disagree.\n"
        f"  advertised but never recorded: {sorted(advertised - recorded)}\n"
        f"  recorded but never advertised: {sorted(recorded - advertised)}"
    )


@pytest.mark.parametrize("task", sorted(_TASK_EPOCH_FIELDS))
def test_every_advertised_field_is_serialised_by_the_history_endpoint(task: str, client) -> None:
    """document -> endpoint.

    `load_history` returning a fixed set of keys is deliberate (the response
    shape must not depend on the task), so the check is that every
    advertised name is among them. This is the assertion that was missing
    when `train_r2`/`test_r2` were added to the table and to `record_epoch`
    but not to the serialiser.
    """
    # `client` is requested only to get the schema created; the assertion
    # goes through the service, not HTTP.
    served = set(_history_keys())
    advertised = set(_TASK_EPOCH_FIELDS[task])

    missing = advertised - served
    assert not missing, (
        f"{task} advertises {sorted(missing)} but load_history never serialises "
        f"them; a client asking for that series gets undefined. "
        f"load_history emits: {sorted(served)}"
    )


def test_history_serialises_nothing_it_cannot_source(client) -> None:
    """endpoint -> document.

    The reverse direction: every metric key the endpoint emits must be
    advertised by *some* task. Without this, a column could be served
    forever with no client ever told it exists -- which is exactly how
    `test_loss` went unadvertised for three phases.
    """
    served = set(_history_keys()) - _NON_METRIC_KEYS
    advertised_anywhere = {f for fields in _TASK_EPOCH_FIELDS.values() for f in fields}

    orphaned = served - advertised_anywhere
    assert not orphaned, (
        f"load_history serialises {sorted(orphaned)}, which no task advertises. "
        f"Either add it to _TASK_EPOCH_FIELDS or stop serialising it."
    )


def test_describe_reports_the_same_fields_it_stores_per_task() -> None:
    """The contract must hold at the boundary users touch, not just inside.

    Phase 5b's lesson: proving a rule in the model does not prove it at the
    endpoint. `describe()` is what the browser actually reads, so assert
    there too, for every registered algorithm.
    """
    payload = describe()
    assert payload["algorithms"], "describe() advertised no algorithms"

    for entry in payload["algorithms"]:
        task = TASK_BY_ALGORITHM[entry["name"]]
        assert entry["epoch_fields"] == _TASK_EPOCH_FIELDS[task], (
            f"{entry['name']}: describe() served {entry['epoch_fields']}, "
            f"the table says {_TASK_EPOCH_FIELDS[task]}"
        )


def test_an_algorithm_without_an_epoch_loop_still_advertises_consistently() -> None:
    """`quantum_kernel` writes zero epoch rows yet advertises epoch_fields.

    That is the documented D-042 behaviour and not a bug, but it is exactly
    the trap a client falls into: gating the training chart on
    `epoch_fields` being non-empty produces a permanently empty axis. Pin
    the pairing so the client's real gate -- `supports.epochs` -- stays
    meaningful.
    """
    payload = describe()
    kernel = next(a for a in payload["algorithms"] if a["name"] == "quantum_kernel")

    assert kernel["epoch_fields"], "kernel's fields come from its task, not its loop"
    assert kernel["supports"]["epochs"] is False, (
        "a client must be able to tell 'no training loop' from 'no data yet', "
        "and epoch_fields cannot carry that distinction"
    )


def _history_keys() -> list[str]:
    """The keys `load_history` emits, read from a real row rather than a literal.

    Deliberately not a hardcoded list: reading the shape back from the
    function under test is what makes this a contract test rather than a
    restatement of the code.
    """
    from app.models.qml import QmlEpochMetric, QmlExperiment
    from app.models.user import User

    db = SessionLocal()
    try:
        user_id = db.query(User.id).first()[0]
        experiment = QmlExperiment(
            user_id=user_id,
            status="running",
            config={},
            run_hash="epoch-contract-probe",
        )
        db.add(experiment)
        db.flush()
        db.add(
            QmlEpochMetric(
                experiment_id=experiment.id,
                epoch=1,
                train_loss=0.5,
                elapsed_seconds=1.0,
            )
        )
        db.flush()

        rows = load_history(db, experiment.id)
        assert rows, "fixture wrote no epoch row, so the key set would be vacuous"
        return list(rows[0])
    finally:
        db.rollback()
        db.close()
