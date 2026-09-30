"""Capture REAL engine results for the result views to be tested against.

    ../../../.venv-ql/bin/python scripts/engine-fixtures.py

Run from the backend virtualenv so qiskit-aer is importable. These are not
invented numbers: they come out of the same `run()` the Celery worker calls, so
the fixtures are exactly the payloads the browser receives from GET
/jobs/{id}/result. The only reason they are captured here is that a sandbox has
no Redis, so no job can complete — on a real stack the same payload arrives
over HTTP.

Regenerate whenever the result schema changes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(BACKEND))

from app.quantum.backends import qiskit_aer  # noqa: E402
from app.quantum.ir import CircuitIR  # noqa: E402
from app.quantum.noise import NoiseParams  # noqa: E402


def op(kind: str, op_id: str, **kwargs):
    base = {
        "id": op_id,
        "kind": kind,
        "gate": None,
        "qubits": [],
        "controls": [],
        "params": [],
        "clbits": [],
        "layer": 0,
        "condition": None,
        "body": [],
        "else_body": [],
        "loop_n": None,
        "loop_var": "i",
        "loop_bit": None,
        "loop_value": 1,
        "box_name": None,
    }
    base.update(kwargs)
    return base


def measure_all(n_qubits: int, layer: int) -> list[dict]:
    return [
        op("measure", f"m{q}", qubits=[q], clbits=[q], layer=layer) for q in range(n_qubits)
    ]


def circuit(name: str, n_qubits: int, ops: list[dict]) -> CircuitIR:
    return CircuitIR.from_dict(
        {"name": name, "n_qubits": n_qubits, "n_clbits": n_qubits, "ops": ops}
    )


cases: dict[str, object] = {}

# Bell state: the canonical entangled pair, with a statevector, non-trivial
# metrics and an off-diagonal density matrix.
bell = circuit(
    "bell",
    2,
    [
        op("gate", "h", gate="h", qubits=[0], layer=0),
        op("gate", "cx", gate="x", qubits=[1], controls=[0], layer=1),
        *measure_all(2, 2),
    ],
)
cases["bell"] = qiskit_aer.run(bell, shots=1024, seed=7)

# Three qubits with a phase: exercises partial traces and the phase table.
ghz = circuit(
    "ghz3",
    3,
    [
        op("gate", "h", gate="h", qubits=[0], layer=0),
        op("gate", "cx1", gate="x", qubits=[1], controls=[0], layer=1),
        op("gate", "cx2", gate="x", qubits=[2], controls=[1], layer=2),
        op("gate", "p", gate="p", qubits=[2], params=[{"expr": "pi/4", "value": 0.7853981633974483}], layer=3),
        *measure_all(3, 4),
    ],
)
cases["ghz3"] = qiskit_aer.run(ghz, shots=2048, seed=11)

# The same Bell state under a noise model: this is what fills the noisy gauges
# and the ideal-vs-noisy comparison.
noise = NoiseParams(
    enabled=True,
    t1_us=50.0,
    t2_us=30.0,
    readout_error=0.02,
    gate_time_1q_us=0.1,
    gate_time_2q_us=0.4,
    gate_time_3q_us=1.0,
)
cases["bell_noisy"] = qiskit_aer.run(bell, shots=1024, seed=7, noise=noise)

out = Path(__file__).resolve().parent.parent / "test-fixtures" / "engine-results.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(cases, indent=2))
print(f"wrote {out}")
for name, payload in cases.items():  # type: ignore[union-attr]
    meta = payload["metadata"]  # type: ignore[index]
    print(f"  {name}: counts={payload['counts']} metrics={meta.get('metrics')}")  # type: ignore[index]
