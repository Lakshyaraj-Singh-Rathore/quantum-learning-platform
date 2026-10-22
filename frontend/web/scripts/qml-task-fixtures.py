"""Capture the real per-task QML payloads the UI has to render.

Phase 3's render fixture was hand-written and invented four keys that
`/qml/describe` does not return, so the harness was checking a contract that
did not exist. §3.3 therefore requires fixtures to be *captured from a real
response*, which is what this does: it runs one real experiment per algorithm
through the actual service, then writes the exact JSON the API would serve.

Two of the four shapes cannot be produced by hand without getting them wrong:

* **quantum_regression** stores ``train_accuracy = NULL`` in every epoch row,
  because R2 is not an accuracy. The frontend type claimed ``number``.
* **quantum_kernel** stores **zero** epoch rows — it is one closed-form solve,
  so there is no curve at all.

Both are the cases the dashboard gets wrong, so both must come from the
database rather than from an author's expectation of it.

Needs the backend virtualenv (PennyLane) and a database:

    DATABASE_URL=sqlite:////tmp/fixtures.db npm run fixtures:qml-tasks
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile

_BACKEND = pathlib.Path(__file__).resolve().parents[3] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/qml_task_fixtures.db")
os.environ.setdefault("JWT_SECRET", "fixture-secret-key-that-is-long-enough-123456")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("QBRAID_API_KEY", "")
os.environ.setdefault("QBRAID_DEVICE_ID", "")
os.environ.setdefault("CONTENT_DIR", str(_BACKEND.parent / "content"))

OUT = pathlib.Path(__file__).resolve().parents[1] / "test-fixtures"

#: Small but real. Every run here trains for actual epochs against actual
#: data; the numbers are measured, not plausible-looking.
CASES = [
    ("vqc", "moons", {}, 3),
    ("hybrid_qnn", "moons", {"n_hidden": 2}, 3),
    ("quantum_regression", "sine", {}, 3),
    ("quantum_kernel", "moons", {}, 1),
]


def _config(algorithm: str, dataset: str, circuit_extra: dict, epochs: int) -> dict:
    circuit = {"n_qubits": 4, "n_layers": 2, "rotation": "Y", "entanglement": "ring"}
    circuit.update(circuit_extra)
    return {
        "seed": 7,
        "algorithm": algorithm,
        "dataset": {"name": dataset, "n_samples": 60, "noise": 0.05, "test_fraction": 0.3},
        "circuit": circuit,
        "training": {
            "epochs": epochs,
            "batch_size": 16,
            "learning_rate": 0.1,
            "diff_method": "backprop",
        },
    }


def main() -> int:
    from alembic import command
    from alembic.config import Config

    # alembic.ini's script_location is relative, and this script does not run
    # from backend/, so resolve it explicitly rather than depending on cwd.
    alembic_config = Config(str(_BACKEND / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(_BACKEND / "alembic"))
    command.upgrade(alembic_config, "head")

    from app.database import SessionLocal
    from app.models.qml import QmlExperiment
    from app.models.user import User
    from app.services import qml_lab as service

    artifacts = pathlib.Path(tempfile.mkdtemp())
    service.artifact_root = lambda: artifacts  # type: ignore[assignment]

    db = SessionLocal()
    if db.query(User.id).first() is None:
        db.add(
            User(
                email="fixtures@example.com",
                password_hash="x",
                role="student",
                display_name="fixtures",
            )
        )
        db.commit()
    user_id = db.query(User.id).first()[0]
    db.close()

    payloads: dict[str, dict] = {}

    for algorithm, dataset, extra, epochs in CASES:
        config = _config(algorithm, dataset, extra, epochs)

        db = SessionLocal()
        row = QmlExperiment(
            user_id=user_id, status="queued", config=config, run_hash=f"fixture-{algorithm}"
        )
        db.add(row)
        db.commit()
        experiment_id = row.id
        db.close()

        db = SessionLocal()
        service.execute_experiment(db, experiment_id)
        db.close()

        db = SessionLocal()
        row = db.get(QmlExperiment, experiment_id)
        history = service.load_history(db, experiment_id)
        # Exactly what GET /qml/experiments/{id} serves.
        detail = {
            "id": row.id,
            "status": row.status,
            "config": row.config,
            "error": row.error,
            "cached": False,
            "history": history,
            "result": row.result,
            "epochs_recorded": len(history),
        }
        n_features = int(row.result["dataset"]["n_features"])
        inference = service.run_inference(row, [[0.1] * n_features, [-0.4] * n_features])
        db.close()

        payloads[algorithm] = {"detail": detail, "inference": inference}

        epoch_note = "no epoch rows (closed form)" if not history else f"{len(history)} epochs"
        first_accuracy = history[0].get("train_accuracy") if history else None
        print(f"  {algorithm:<20} {epoch_note:<28} first train_accuracy={first_accuracy!r}")

    (OUT / "qml-task-payloads.json").write_text(json.dumps(payloads, indent=2) + "\n")
    (OUT / "qml-describe.json").write_text(json.dumps(service.describe(), indent=2) + "\n")

    print(f"\nwrote {OUT / 'qml-task-payloads.json'}")
    print(f"wrote {OUT / 'qml-describe.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
