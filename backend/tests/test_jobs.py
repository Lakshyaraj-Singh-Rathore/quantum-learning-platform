"""Job submission lifecycle, backend routing and autograding."""

import pytest


def _result(client, headers, job_id):
    return client.get(f"/jobs/{job_id}/result", headers=headers).json()


def test_backend_catalogue_reports_availability(client):
    body = client.get("/backends").json()
    ids = {b["id"] for b in body["backends"]}
    assert {"qiskit_aer", "cirq", "pennylane", "qbraid", "qiskit_dynamic"} <= ids
    assert body["limits"]["while_cap"] == 32

    qbraid = next(b for b in body["backends"] if b["id"] == "qbraid")
    assert qbraid["available"] is False  # no credentials in the test env
    assert "qBraid" in qbraid["reason"]


@pytest.mark.parametrize("backend", ["qiskit_aer", "cirq", "pennylane"])
def test_static_job_completes_on_every_backend(client, student_headers, bell_ir, backend):
    created = client.post(
        "/jobs",
        json={"circuit_ir": bell_ir, "backend": backend, "shots": 400},
        headers=student_headers,
    )
    assert created.status_code == 201

    result = _result(client, student_headers, created.json()["id"])
    assert result["status"] == "completed"
    assert set(result["result"]["counts"]) <= {"00", "11"}
    assert result["result"]["metadata"]["engine"] == backend


def test_dynamic_circuit_is_routed_to_the_qiskit_engine(client, student_headers, dynamic_ir):
    created = client.post(
        "/jobs",
        json={"circuit_ir": dynamic_ir, "backend": "cirq", "shots": 200},
        headers=student_headers,
    )
    result = _result(client, student_headers, created.json()["id"])

    assert result["status"] == "completed"
    assert result["result"]["metadata"]["engine"] == "qiskit_dynamic"
    warnings = " ".join(result["result"]["metadata"]["warnings"])
    assert "dynamic" in warnings.lower()
    # perfectly correlated: the if-branch flips q1 exactly when c[0] == 1
    assert set(result["result"]["counts"]) <= {"00", "11"}


def test_qbraid_rejected_without_credentials(client, student_headers, bell_ir):
    response = client.post(
        "/jobs",
        json={"circuit_ir": bell_ir, "backend": "qbraid", "shots": 10},
        headers=student_headers,
    )
    assert response.status_code == 422
    assert "qBraid" in str(response.json()["detail"])


def test_dynamic_qubit_limit_rejected_at_submission(client, student_headers):
    ir = {
        "name": "too-big",
        "n_qubits": 16,
        "n_clbits": 16,
        "ops": [
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 0},
            {
                "kind": "if",
                "condition": {"type": "bit_eq", "bit": 0, "value": 1},
                "body": [{"kind": "gate", "gate": "x", "qubits": [1]}],
                "layer": 1,
            },
        ],
    }
    response = client.post(
        "/jobs", json={"circuit_ir": ir, "backend": "auto", "shots": 8}, headers=student_headers
    )
    assert response.status_code == 422
    assert "15 qubits" in str(response.json()["detail"])


def test_invalid_circuit_rejected(client, student_headers):
    bad = {"name": "bad", "n_qubits": 1, "ops": [{"kind": "gate", "gate": "nope", "qubits": [0]}]}
    response = client.post(
        "/jobs", json={"circuit_ir": bad, "backend": "qiskit_aer"}, headers=student_headers
    )
    assert response.status_code == 422


def test_results_are_cached_by_run_hash(client, student_headers, bell_ir):
    payload = {"circuit_ir": bell_ir, "backend": "qiskit_aer", "shots": 128}
    first = client.post("/jobs", json=payload, headers=student_headers).json()
    second = client.post("/jobs", json=payload, headers=student_headers).json()
    assert first["id"] == second["id"]


def test_jobs_are_private_to_their_owner(client, student_headers, bell_ir):
    created = client.post(
        "/jobs",
        json={"circuit_ir": bell_ir, "backend": "qiskit_aer", "shots": 64},
        headers=student_headers,
    ).json()

    other = client.post(
        "/auth/register", json={"email": "nosy@example.com", "password": "pw123456"}
    ).json()
    headers = {"Authorization": f"Bearer {other['access_token']}"}

    assert client.get(f"/jobs/{created['id']}", headers=headers).status_code == 403


def test_qasm_import_export_roundtrip_over_http(client, student_headers, bell_ir):
    exported = client.post(
        "/qasm/export", json={"circuit_ir": bell_ir}, headers=student_headers
    ).text
    assert "OPENQASM 3.0;" in exported

    imported = client.post(
        "/qasm/import", json={"qasm3": exported, "name": "bell"}, headers=student_headers
    ).json()
    assert imported["is_dynamic"] is False
    assert imported["circuit_ir"]["n_qubits"] == 2


@pytest.mark.parametrize("framework", ["qiskit", "cirq", "qasm3"])
def test_code_export_endpoints(client, student_headers, dynamic_ir, framework):
    code = client.post(
        f"/export/{framework}", json={"circuit_ir": dynamic_ir}, headers=student_headers
    ).text
    assert code.strip()
    if framework == "cirq":
        # dynamic circuits must ship the Python driver
        assert "DynamicDriver" in code
        assert "WHILE_CAP" in code


def test_grade_counts_tolerates_shot_noise():
    """A correct Bell state must pass across the whole plausible noise range.

    Regression test: the seeded tolerance was once tight enough that ~12% of
    *correct* submissions were graded as failures. Walk the +/-3 sigma band of
    a 1024-shot 50/50 split (a ~1-in-370 tail) and require every outcome to
    pass. Demanding 4 sigma would force a tolerance so wide it stops
    discriminating against genuinely wrong distributions.
    """
    from app.services.autograder import PASS_THRESHOLD, grade_counts

    target = {"counts": {"00": 0.5, "11": 0.5}, "tolerance": 0.25}
    shots = 1024
    sigma = int((0.25 * shots) ** 0.5)  # ~16 counts
    for delta in range(-3 * sigma, 3 * sigma + 1, sigma or 1):
        n00 = shots // 2 + delta
        score, _ = grade_counts({"00": n00, "11": shots - n00}, target)
        assert score >= PASS_THRESHOLD, f"correct Bell state failed at delta={delta}"

    # ...while a plainly wrong distribution still scores zero.
    score, _ = grade_counts({"00": shots}, target)
    assert score < PASS_THRESHOLD


def test_challenge_submission_is_autograded(client, student_headers, bell_ir):
    submitted = client.post(
        "/challenges/bell-state/submit",
        json={"circuit_ir": bell_ir, "shots": 1024},
        headers=student_headers,
    )
    assert submitted.status_code == 200
    attempt_id = submitted.json()["attempt_id"]

    graded = client.get(f"/attempts/{attempt_id}", headers=student_headers).json()
    assert graded["status"] == "graded"
    assert graded["passed"] is True
    assert graded["score"] > 0.8


def test_challenge_constraints_are_enforced(client, student_headers):
    """A plain |00> circuit is not a Bell state and must fail."""
    ir = {
        "name": "wrong",
        "n_qubits": 2,
        "n_clbits": 2,
        "ops": [
            {"kind": "gate", "gate": "x", "qubits": [0], "layer": 0},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
            {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 1},
        ],
    }
    submitted = client.post(
        "/challenges/bell-state/submit",
        json={"circuit_ir": ir, "shots": 256},
        headers=student_headers,
    ).json()
    graded = client.get(f"/attempts/{submitted['attempt_id']}", headers=student_headers).json()
    assert graded["passed"] is False


def test_ai_never_exposes_a_simulation_tool():
    from app.ai.tools import ALLOWED_TOOLS, FORBIDDEN_TOOLS

    assert "get_simulation_result" in ALLOWED_TOOLS
    for forbidden in FORBIDDEN_TOOLS:
        assert forbidden not in ALLOWED_TOOLS
