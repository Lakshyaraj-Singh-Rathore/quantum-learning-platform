"""The QML migration: linear head, additive, and reversible.

Written because a migration that has only ever been run forwards is a
migration whose ``downgrade`` is a guess. These tests apply the revision to a
throwaway SQLite file, roll it back, and apply it again, asserting the table
appears and disappears and that nothing else moves.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.config import get_settings

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REVISION = "i4d7e0f3a6b9"
PREVIOUS = "h3c6d9e2f5a8"


def _script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(Config(str(BACKEND_ROOT / "alembic.ini")))


def test_there_is_exactly_one_head():
    """Two heads mean an un-mergeable branch point."""
    heads = _script_directory().get_heads()
    assert list(heads) == [REVISION], f"expected a single head {REVISION}, got {heads}"


def test_the_revision_chains_onto_the_previous_head():
    revision = _script_directory().get_revision(REVISION)
    assert revision.down_revision == PREVIOUS


def test_history_is_a_straight_line():
    script = _script_directory()
    revisions = list(script.walk_revisions())
    assert len(revisions) == 9, f"expected 9 revisions, found {len(revisions)}"
    for revision in revisions:
        assert not isinstance(revision.down_revision, tuple), f"{revision.revision} is a merge point"


@pytest.fixture
def migrated(tmp_path, monkeypatch):
    """A fresh SQLite database driven entirely by alembic."""
    db_path = tmp_path / "migration-test.db"
    url = f"sqlite:///{db_path}"

    # alembic/env.py:31 takes the URL from get_settings(), which is
    # lru_cached -- setting the environment variable alone would leave
    # alembic pointed at the suite's shared database and this test would
    # silently assert against the wrong file. Clear the cache both ways.
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    assert get_settings().database_url == url

    yield config, sa.create_engine(url)

    get_settings.cache_clear()


def _tables(engine) -> set[str]:
    return set(sa.inspect(engine).get_table_names())


def test_upgrade_creates_both_tables_and_downgrade_removes_them(migrated):
    config, engine = migrated

    command.upgrade(config, PREVIOUS)
    before = _tables(engine)
    assert not {"qml_experiments", "qml_epoch_metrics"} & before

    command.upgrade(config, REVISION)
    after = _tables(engine)
    assert after - before == {
        "qml_experiments",
        "qml_epoch_metrics",
    }, "the migration must add exactly the two QML tables and nothing else"

    command.downgrade(config, PREVIOUS)
    rolled_back = _tables(engine)
    assert rolled_back == before, "downgrade must restore the schema exactly"

    command.upgrade(config, REVISION)
    assert {"qml_experiments", "qml_epoch_metrics"} <= _tables(engine)


@pytest.mark.parametrize("model_name", ["QmlExperiment", "QmlEpochMetric"])
def test_each_table_matches_its_orm_model(migrated, model_name):
    """A model and a migration that disagree fail at runtime, not at import."""
    config, engine = migrated
    command.upgrade(config, REVISION)

    import app.models.qml as qml_models

    model = getattr(qml_models, model_name)
    table = model.__table__.name
    actual = {column["name"] for column in sa.inspect(engine).get_columns(table)}
    expected = {column.name for column in model.__table__.columns}
    assert actual == expected, f"{table}: missing={expected - actual} unexpected={actual - expected}"


def test_the_epoch_unique_constraint_exists(migrated):
    """Redelivery safety is a database guarantee, not a convention."""
    config, engine = migrated
    command.upgrade(config, REVISION)

    inspector = sa.inspect(engine)
    constraints = inspector.get_unique_constraints("qml_epoch_metrics")
    pairs = [tuple(c["column_names"]) for c in constraints]
    assert ("experiment_id", "epoch") in pairs, f"found {pairs}"


def test_a_duplicate_epoch_is_rejected_by_the_database(migrated):
    """Prove the constraint bites, rather than trusting the DDL."""
    config, engine = migrated
    command.upgrade(config, REVISION)

    # No users row is needed: SQLite does not enforce foreign keys unless
    # PRAGMA foreign_keys=ON, and the constraint under test is the unique one.
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO qml_experiments (user_id, status, run_hash, config) "
                "VALUES (1, 'running', 'h', '{}')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO qml_epoch_metrics "
                "(experiment_id, epoch, train_loss, train_accuracy, elapsed_seconds) "
                "VALUES (1, 1, 0.5, 0.5, 1.0)"
            )
        )

    with pytest.raises(sa.exc.IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    "INSERT INTO qml_epoch_metrics "
                    "(experiment_id, epoch, train_loss, train_accuracy, elapsed_seconds) "
                    "VALUES (1, 1, 0.4, 0.6, 2.0)"
                )
            )


def test_the_lookup_columns_are_indexed(migrated):
    """run_hash drives the duplicate-submission guard on every create."""
    config, engine = migrated
    command.upgrade(config, REVISION)

    inspector = sa.inspect(engine)
    indexed = {
        column
        for index in inspector.get_indexes("qml_experiments")
        for column in index["column_names"]
    }
    assert {"run_hash", "user_id", "status"} <= indexed

    epoch_indexed = {
        column
        for index in inspector.get_indexes("qml_epoch_metrics")
        for column in index["column_names"]
    }
    assert "experiment_id" in epoch_indexed
