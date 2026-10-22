"""QML Lab API tests.

Two client fixtures, because the feature flag has two states and both are
load-bearing:

* ``client`` (from conftest) is the real application with the default
  settings, i.e. ``qml_enabled`` false. Every /qml/* path must 404 there.
* ``qml_client`` reloads ``app.api.router`` with the flag on and mounts the
  resulting router. That exercises the real gating code in router.py rather
  than mounting ``qml.router`` directly, which would prove nothing about the
  flag.

Celery runs eagerly in the test suite (conftest sets ``task_always_eager``),
so POST /qml/experiments trains inline and returns a finished row. Configs
here are deliberately tiny -- 40 samples, 2 epochs, 2 qubits -- because the
point is the wiring, not the learning curve; the learning itself is proven in
test_qml_trainer.py.
"""

from __future__ import annotations

import importlib
import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import get_settings

QML_PATHS = [
    ("get", "/qml/describe"),
    ("post", "/qml/experiments"),
    ("get", "/qml/experiments"),
    ("get", "/qml/experiments/1"),
    ("get", "/qml/experiments/1/result"),
    ("post", "/qml/experiments/1/cancel"),
    ("post", "/qml/experiments/1/inference"),
]


def tiny_config(**overrides):
    config = {
        "seed": 7,
        "dataset": {"name": "moons", "n_samples": 40, "noise": 0.1, "test_fraction": 0.3},
        "circuit": {"n_qubits": 2, "n_layers": 1, "rotation": "Y", "entanglement": "ring"},
        "training": {"epochs": 2, "batch_size": 16, "learning_rate": 0.1, "diff_method": "backprop"},
    }
    config.update(overrides)
    return config


# ---------------------------------------------------------------------------
# Flag OFF -- the default application
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path", QML_PATHS)
def test_qml_paths_are_absent_when_flag_is_off(client, student_headers, method, path):
    """The flag's guarantee: with it off, the feature does not exist."""
    kwargs = {"json": {}} if method == "post" else {}
    response = client.request(method, path, headers=student_headers, **kwargs)
    assert response.status_code == 404, f"{method.upper()} {path} -> {response.status_code}"


def test_no_qml_route_is_registered_when_flag_is_off(client):
    paths = {getattr(route, "path", "") for route in client.app.routes}
    assert not [p for p in paths if p.startswith("/qml")], "a /qml route leaked in with the flag off"


def test_unrelated_endpoints_are_untouched_by_the_feature(client, student_headers):
    """Flag off must mean byte-identical behaviour for everything else."""
    assert client.get("/health").status_code == 200
    assert client.get("/jobs", headers=student_headers).status_code == 200


# ---------------------------------------------------------------------------
# Flag ON
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def other_student_headers(client):
    """A second, distinct user -- the global concurrency cap is about the
    machine, so it must bite across users, not just within one."""
    payload = {"email": "pytest-student-2@example.com", "password": "pw123456"}
    response = client.post("/auth/register", json=payload)
    if response.status_code != 201:
        response = client.post("/auth/login", json=payload)
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def qml_client(client, tmp_path_factory):
    """The application with qml_enabled true, built through the real router."""
    artifacts = tmp_path_factory.mktemp("qml-artifacts")
    previous = {k: os.environ.get(k) for k in ("QML_ENABLED", "QML_ARTIFACT_DIR")}
    os.environ["QML_ENABLED"] = "true"
    os.environ["QML_ARTIFACT_DIR"] = str(artifacts)
    get_settings.cache_clear()

    import app.api.router as router_module

    importlib.reload(router_module)
    app = FastAPI()
    app.include_router(router_module.api_router)

    with TestClient(app) as test_client:
        yield test_client

    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    get_settings.cache_clear()
    importlib.reload(router_module)


def test_global_features_endpoint_reports_true_when_flag_is_on(qml_client):
    """The always-mounted endpoint tracks the flag -- unauthenticated."""
    response = qml_client.get("/features")
    assert response.status_code == 200
    assert response.json() == {"qml_enabled": True}


def test_endpoints_require_authentication(qml_client):
    """Mounted does not mean public."""
    for method, path in QML_PATHS:
        kwargs = {"json": {}} if method == "post" else {}
        response = qml_client.request(method, path, **kwargs)
        assert response.status_code in (401, 403), f"{path} was reachable unauthenticated"


def test_describe_exposes_server_side_limits(qml_client, student_headers):
    body = qml_client.get("/qml/describe", headers=student_headers).json()
    assert body["limits"]["n_qubits"] == {"default": 4, "min": 1, "max": 8}
    assert body["limits"]["n_layers"]["max"] == 4
    assert body["limits"]["n_samples"]["max"] == 1000
    assert body["limits"]["epochs"]["max"] == 100
    assert body["limits"]["batch_size"]["max"] == 32
    assert body["max_concurrent_experiments"] == 1
    by_name = {entry["name"]: entry for entry in body["datasets"]}
    assert set(by_name) == {"moons", "circles", "iris_binary"}
    assert by_name["iris_binary"]["n_features"] == 4
    assert by_name["iris_binary"]["max_samples"] == 100
    assert set(body["diff_methods"]) == {"backprop", "parameter-shift"}


def test_unknown_field_is_rejected(qml_client, student_headers):
    """extra='forbid' all the way out to the HTTP edge."""
    response = qml_client.post(
        "/qml/experiments", headers=student_headers, json=tiny_config(sneaky_field=1)
    )
    assert response.status_code == 422


def test_over_limit_qubits_are_rejected_at_the_schema_boundary(qml_client, student_headers):
    response = qml_client.post(
        "/qml/experiments",
        headers=student_headers,
        json=tiny_config(circuit={"n_qubits": 99, "n_layers": 1, "rotation": "Y", "entanglement": "ring"}),
    )
    assert response.status_code == 422
    assert "n_qubits" in response.text
    assert "less than or equal to 8" in response.text


def test_dataset_wider_than_circuit_is_rejected_before_enqueue(qml_client, student_headers):
    """iris_binary has 4 features; a 2-qubit circuit cannot encode them."""
    response = qml_client.post(
        "/qml/experiments",
        headers=student_headers,
        json=tiny_config(
            dataset={"name": "iris_binary", "n_samples": 80, "noise": 0.0, "test_fraction": 0.3},
            circuit={"n_qubits": 2, "n_layers": 1, "rotation": "Y", "entanglement": "ring"},
        ),
    )
    assert response.status_code == 422
    assert "features" in str(response.json()["detail"]).lower()


# ---------------------------------------------------------------------------
# Full lifecycle
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def finished_experiment(qml_client, student_headers):
    response = qml_client.post(
        "/qml/experiments", headers=student_headers, json=tiny_config()
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_experiment_runs_to_completion(finished_experiment):
    assert finished_experiment["status"] == "completed", finished_experiment.get("error")
    assert finished_experiment["cached"] is False


def test_detail_carries_epoch_history_for_the_dashboard(qml_client, student_headers, finished_experiment):
    body = qml_client.get(
        f"/qml/experiments/{finished_experiment['id']}", headers=student_headers
    ).json()
    assert body["epochs_recorded"] == 2
    assert [row["epoch"] for row in body["history"]] == [1, 2]
    first = body["history"][0]
    assert {"epoch", "train_loss", "train_accuracy", "test_loss", "elapsed_seconds"} <= set(first)
    assert isinstance(first["train_loss"], float)


def test_history_polling_is_incremental(qml_client, student_headers, finished_experiment):
    """after_epoch lets the dashboard fetch only what it has not seen."""
    url = f"/qml/experiments/{finished_experiment['id']}"
    assert len(qml_client.get(url, headers=student_headers).json()["history"]) == 2

    partial = qml_client.get(url, params={"after_epoch": 1}, headers=student_headers).json()
    assert [row["epoch"] for row in partial["history"]] == [2]

    caught_up = qml_client.get(url, params={"after_epoch": 2}, headers=student_headers).json()
    assert caught_up["history"] == []
    assert caught_up["epochs_recorded"] == 2, "the total is still reported while the delta is empty"


def test_result_reports_metrics_and_the_classical_baseline(qml_client, student_headers, finished_experiment):
    body = qml_client.get(
        f"/qml/experiments/{finished_experiment['id']}/result", headers=student_headers
    ).json()
    assert body["status"] == "completed"
    evaluation = body["result"]["evaluation"]
    assert 0.0 <= evaluation["accuracy"] <= 1.0
    assert len(evaluation["confusion_matrix"]) == 2
    baseline = body["result"]["baseline"]
    assert 0.0 <= baseline["test_accuracy"] <= 1.0
    assert baseline["n_parameters"] > 0
    assert baseline["model"]


def test_duplicate_submission_returns_the_cached_run(qml_client, student_headers, finished_experiment):
    """The run_hash guard from jobs.py:150-166, not a new idempotency system."""
    response = qml_client.post(
        "/qml/experiments", headers=student_headers, json=tiny_config()
    )
    assert response.status_code == 201
    assert response.json()["cached"] is True
    assert response.json()["id"] == finished_experiment["id"]


def test_inference_returns_one_prediction_per_input(qml_client, student_headers, finished_experiment):
    response = qml_client.post(
        f"/qml/experiments/{finished_experiment['id']}/inference",
        headers=student_headers,
        json={"features": [[0.2, 0.4], [-0.9, 0.1], [1.4, -0.3]]},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["predictions"]) == 3
    assert set(body["predictions"]) <= {0, 1}
    assert len(body["probabilities"]) == 3
    assert all(0.0 <= p <= 1.0 for p in body["probabilities"])
    assert body["n_features"] == 2


def test_inference_rejects_the_wrong_feature_width(qml_client, student_headers, finished_experiment):
    response = qml_client.post(
        f"/qml/experiments/{finished_experiment['id']}/inference",
        headers=student_headers,
        json={"features": [[0.1, 0.2, 0.3, 0.4, 0.5]]},
    )
    assert response.status_code == 422


def test_listing_shows_the_users_own_experiments(qml_client, student_headers, finished_experiment):
    rows = qml_client.get("/qml/experiments", headers=student_headers).json()
    assert any(row["id"] == finished_experiment["id"] for row in rows)


# ---------------------------------------------------------------------------
# Concurrency, cancellation, ownership
# ---------------------------------------------------------------------------


def test_second_experiment_is_refused_while_one_is_active(qml_client, student_headers, finished_experiment):
    """Max 1 concurrent job. A running row is inserted directly so the test
    does not depend on eager-Celery timing."""
    from app.database import SessionLocal
    from app.models.qml import QmlExperiment

    db = SessionLocal()
    try:
        owner = db.get(QmlExperiment, finished_experiment["id"]).user_id
        blocker = QmlExperiment(
            user_id=owner, status="running", config=tiny_config(), run_hash="blocker-hash"
        )
        db.add(blocker)
        db.commit()
        blocker_id = blocker.id
    finally:
        db.close()

    try:
        # A different seed, so this is a genuinely new run and the 409 comes
        # from the concurrency cap rather than from the duplicate guard.
        response = qml_client.post(
            "/qml/experiments", headers=student_headers, json=tiny_config(seed=4242)
        )
        assert response.status_code == 409
        assert str(blocker_id) in str(response.json()["detail"])
    finally:
        db = SessionLocal()
        try:
            db.delete(db.get(QmlExperiment, blocker_id))
            db.commit()
        finally:
            db.close()


def test_another_users_running_job_also_blocks(qml_client, student_headers, other_student_headers, finished_experiment):
    """The cap is global: the protected resource is the single worker slot.

    Per-user scoping would let this second user enqueue and then wait
    silently behind the first job instead of being told immediately.
    """
    from app.database import SessionLocal
    from app.models.qml import QmlExperiment

    db = SessionLocal()
    try:
        owner = db.get(QmlExperiment, finished_experiment["id"]).user_id
        blocker = QmlExperiment(
            user_id=owner, status="running", config=tiny_config(seed=77), run_hash="cross-user"
        )
        db.add(blocker)
        db.commit()
        blocker_id = blocker.id
    finally:
        db.close()

    try:
        response = qml_client.post(
            "/qml/experiments", headers=other_student_headers, json=tiny_config(seed=4243)
        )
        assert response.status_code == 409
        message = str(response.json()["detail"])
        assert "Another experiment" in message, message
    finally:
        db = SessionLocal()
        try:
            db.delete(db.get(QmlExperiment, blocker_id))
            db.commit()
        finally:
            db.close()


def test_cancel_sets_the_cooperative_flag(qml_client, student_headers, finished_experiment):
    from app.database import SessionLocal
    from app.models.qml import QmlExperiment

    db = SessionLocal()
    try:
        owner = db.get(QmlExperiment, finished_experiment["id"]).user_id
        row = QmlExperiment(user_id=owner, status="running", config=tiny_config(), run_hash="cancel-hash")
        db.add(row)
        db.commit()
        row_id = row.id
    finally:
        db.close()

    response = qml_client.post(f"/qml/experiments/{row_id}/cancel", headers=student_headers)
    assert response.status_code == 200

    db = SessionLocal()
    try:
        refreshed = db.get(QmlExperiment, row_id)
        assert refreshed.cancel_requested is True
        assert refreshed.status == "running", "cancel requests, it does not pretend to have stopped anything"
        db.delete(refreshed)
        db.commit()
    finally:
        db.close()


def test_cancelling_a_finished_experiment_is_a_conflict(qml_client, student_headers, finished_experiment):
    """409, not a polite 200: there is nothing left to stop and saying
    otherwise would be a lie. The result must also be untouched."""
    before = qml_client.get(
        f"/qml/experiments/{finished_experiment['id']}/result", headers=student_headers
    ).json()

    response = qml_client.post(
        f"/qml/experiments/{finished_experiment['id']}/cancel", headers=student_headers
    )
    assert response.status_code == 409
    assert "already finished" in str(response.json()["detail"])

    after = qml_client.get(
        f"/qml/experiments/{finished_experiment['id']}/result", headers=student_headers
    ).json()
    assert after == before


def test_cancelling_twice_is_idempotent(qml_client, student_headers, finished_experiment):
    """Double-clicking Cancel must not be a 500."""
    from app.database import SessionLocal
    from app.models.qml import QmlExperiment

    db = SessionLocal()
    try:
        owner = db.get(QmlExperiment, finished_experiment["id"]).user_id
        row = QmlExperiment(
            user_id=owner, status="running", config=tiny_config(seed=55), run_hash="twice"
        )
        db.add(row)
        db.commit()
        row_id = row.id
    finally:
        db.close()

    url = f"/qml/experiments/{row_id}/cancel"
    first = qml_client.post(url, headers=student_headers)
    second = qml_client.post(url, headers=student_headers)
    assert (first.status_code, second.status_code) == (200, 200)
    assert second.json()["status"] == "running"

    db = SessionLocal()
    try:
        row = db.get(QmlExperiment, row_id)
        assert row.cancel_requested is True
        db.delete(row)
        db.commit()
    finally:
        db.close()


def test_result_before_completion_is_a_conflict(qml_client, student_headers, finished_experiment):
    from app.database import SessionLocal
    from app.models.qml import QmlExperiment

    db = SessionLocal()
    try:
        owner = db.get(QmlExperiment, finished_experiment["id"]).user_id
        row = QmlExperiment(user_id=owner, status="queued", config=tiny_config(), run_hash="pending-hash")
        db.add(row)
        db.commit()
        row_id = row.id
    finally:
        db.close()

    assert qml_client.get(f"/qml/experiments/{row_id}/result", headers=student_headers).status_code == 409
    assert qml_client.post(
        f"/qml/experiments/{row_id}/inference", headers=student_headers, json={"features": [[0.1, 0.2]]}
    ).status_code == 409

    db = SessionLocal()
    try:
        db.delete(db.get(QmlExperiment, row_id))
        db.commit()
    finally:
        db.close()


def test_missing_experiment_is_404(qml_client, student_headers):
    assert qml_client.get("/qml/experiments/999999", headers=student_headers).status_code == 404


def test_another_users_experiment_is_403(qml_client, student_headers, finished_experiment):
    from app.database import SessionLocal
    from app.models.qml import QmlExperiment

    db = SessionLocal()
    try:
        row = QmlExperiment(user_id=999_999, status="completed", config=tiny_config(), run_hash="other-user")
        db.add(row)
        db.commit()
        row_id = row.id
    finally:
        db.close()

    response = qml_client.get(f"/qml/experiments/{row_id}", headers=student_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not your job", "ownership wording mirrors api/jobs.py:205"

    db = SessionLocal()
    try:
        db.delete(db.get(QmlExperiment, row_id))
        db.commit()
    finally:
        db.close()
