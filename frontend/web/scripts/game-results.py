"""Generate test-fixtures/games-results.json from the platform's OWN graders.

    ../../../.venv-ql/bin/python scripts/game-results.py

Run it from the backend virtualenv (it imports the backend). Nothing here is
invented: the truth table comes from grade_truth_table() on a real CNOT, and
the convergence curve from subsample_curve() over counts a real Aer run
produced. The React result panels are then checked against this by
scripts/render-games.mts.

It needs no Celery worker -- it calls the graders and the simulator directly.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "backend"))

from app.quantum.backends import qiskit_aer  # noqa: E402
from app.quantum.ir import CircuitIR, Op  # noqa: E402
from app.services.game_graders import grade_truth_table, subsample_curve  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "test-fixtures" / "games-results.json"
SHOT_POINTS = [128, 256, 512, 1024, 2048, 4096]


def op(identifier: str, **kwargs) -> Op:
    fields = dict(
        id=identifier, kind="gate", gate="x", qubits=[0], controls=[], params=[],
        clbits=[], layer=0, condition=None, body=[], else_body=[], loop_n=None,
        loop_var="i", loop_bit=None, loop_value=1, box_name=None,
    )
    fields.update(kwargs)
    return Op(**fields)


def main() -> int:
    # Open the Vault level 1: flip q1 exactly when q0 is 1.
    vault = CircuitIR(
        name="vault", n_qubits=2, n_clbits=2,
        ops=[op("a", gate="x", qubits=[1], controls=[0], layer=0)],
    )
    score, note, details = grade_truth_table(vault, {"n_controls": 1})

    bell = CircuitIR(
        name="bell", n_qubits=2, n_clbits=2,
        ops=[
            op("a", gate="h", qubits=[0], layer=0),
            op("b", gate="x", qubits=[1], controls=[0], layer=1),
            op("c", kind="measure", gate="measure", qubits=[0], clbits=[0], layer=2),
            op("d", kind="measure", gate="measure", qubits=[1], clbits=[1], layer=2),
        ],
    )
    counts = qiskit_aer.run(bell, shots=4096)["counts"]
    ideal = {"00": 0.5, "11": 0.5}
    curve = subsample_curve(counts, ideal, SHOT_POINTS)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "truth_table": {"score": score, "note": note, "details": details},
                "shot_detective": {"counts": counts, "curve": curve, "ideal": ideal},
            },
            indent=2,
        )
        + "\n",
    )
    print(f"wrote {OUT} (truth table {details['testcases_passed']}/{details['testcases_total']}, {len(curve)} curve points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
