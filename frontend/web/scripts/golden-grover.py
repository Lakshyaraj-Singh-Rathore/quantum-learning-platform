"""Regenerate the golden numbers the Grover module is checked against.

    ../../../.venv-ql/bin/python scripts/golden-grover.py > test-fixtures/grover-golden.json

Run it from the backend virtualenv (numpy lives there):

    /home/user/.venv-ql/bin/python scripts/golden-grover.py

The truth is frontend/lib/grover_lab.py -- the same module the Streamlit Grover
lab calls today. scripts/golden-grover.mts checks src/lib/grover.ts agrees, so
the React module cannot start showing a different probability than the one a
learner sees in Streamlit.

`measure` is excluded: it draws from numpy's PCG64, which JavaScript cannot
reproduce, and the lesson it teaches is the distribution, not the draw.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

import grover_lab as gl  # noqa: E402

out: dict[str, object] = {}

out["optimalIterations"] = [
    {"n_qubits": n, "value": gl.optimal_iterations(n)} for n in range(1, 7)
]

# Every state's probability, at every iteration, for a few sizes and targets.
out["run"] = []
for n_qubits, target, iterations in (
    (2, 1, 4),
    (3, 5, 6),
    (4, 9, 8),
    (6, 45, 12),
):
    frames = gl.run(n_qubits, target, iterations)
    out["run"].append(  # type: ignore[union-attr]
        {
            "n_qubits": n_qubits,
            "target": target,
            "iterations": iterations,
            "frames": [
                {
                    "iteration": frame["iteration"],
                    "stage": frame["stage"],
                    "target_probability": frame["target_probability"],
                    "probabilities": [float(p) for p in frame["probabilities"]],
                    "amplitudes": [[float(a.real), float(a.imag)] for a in frame["amplitudes"]],
                }
                for frame in frames
            ],
        }
    )

# The closed form must match the simulation -- this is the cross-check the
# module itself relies on.
out["analytic"] = [
    {"n_qubits": n, "iteration": k, "value": gl.analytic_probability(n, k)}
    for n in (2, 3, 4, 5, 6)
    for k in range(0, 14)
]

out["parsePassword"] = [
    {"text": text, "n_qubits": n, "target": gl.parse_password(text, n)[0], "error": gl.parse_password(text, n)[1]}
    for text, n in (
        ("101101", 6),
        ("000", 3),
        ("1", 1),
        ("101", 3),
        ("", 3),
        ("abc", 3),
        ("10", 3),
        ("1111", 3),
        ("1 0 1", 3),
    )
]

out["classicalAttempts"] = [
    {"n_qubits": n, "target": t, **gl.classical_attempts(n, t)}
    for n, t in ((6, 45), (3, 0), (3, 7), (1, 0), (6, 0))
]

out["label"] = [{"index": i, "n_qubits": n, "value": gl.label(i, n)} for i, n in ((0, 3), (5, 3), (45, 6), (7, 3), (1, 1))]

print(json.dumps(out, indent=2))
