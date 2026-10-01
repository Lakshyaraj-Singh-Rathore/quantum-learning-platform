"""Regenerate the golden numbers the lesson demos are checked against.

    ../../../.venv-ql/bin/python scripts/golden-demos.py > test-fixtures/demo-golden.json

Run it from the backend virtualenv (numpy lives there):

    /home/user/.venv-ql/bin/python scripts/golden-demos.py

The truth here is frontend/lib/playground.py — the same module the Streamlit
demos call today, not a re-derivation of it. scripts/golden-demos.mts is the
check that src/lib/demos.ts agrees, so a ported demo cannot start showing a
different number than the one a learner sees in Streamlit.

`sample` is deliberately absent: it draws from numpy's PCG64, which JavaScript
cannot reproduce, and the lesson it teaches is the distribution, not the draw.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))

import playground as pg  # noqa: E402

out: dict[str, object] = {}

# |psi> from Bloch angles, across the sphere including both poles.
out["stateFromAngles"] = [
    {
        "theta": theta,
        "phi": phi,
        "state": [[float(a.real), float(a.imag)] for a in pg.state_from_angles(theta, phi)],
        "probabilities": list(pg.probabilities(pg.state_from_angles(theta, phi))),
    }
    for theta in (0.0, 30.0, 45.0, 90.0, 120.0, 180.0)
    for phi in (0.0, 45.0, 90.0, 180.0, 270.0, 360.0)
]

# Renormalising a pair of real amplitudes, including the degenerate zero case.
out["stateFromAmplitudes"] = [
    {
        "alpha": alpha,
        "beta": beta,
        "state": [[float(a.real), float(a.imag)] for a in pg.state_from_amplitudes(alpha, beta)],
    }
    for alpha, beta in ((0.8, 0.6), (-0.8, 0.6), (1.0, 0.0), (0.0, 0.0), (0.3, -0.3), (2.0, 2.0))
]

# Gate sequences applied left to right, from every landmark start.
SEQUENCES = [
    [],
    ["H"],
    ["X"],
    ["X", "Z"],
    ["H", "S", "H"],
    ["T", "T"],
    ["H", "Z", "H"],
    ["Y"],
    ["S", "T", "Z"],
]
out["applyGates"] = []
for name, (theta, phi) in pg.LANDMARKS.items():
    start = pg.state_from_angles(theta, phi)
    for sequence in SEQUENCES:
        state = pg.apply_gates(start, list(sequence))
        theta_out, phi_out = pg.bloch_angles_of(state)
        out["applyGates"].append(  # type: ignore[union-attr]
            {
                "start": name,
                "gates": list(sequence),
                "state": [[float(a.real), float(a.imag)] for a in state],
                "probabilities": list(pg.probabilities(state)),
                "theta": theta_out,
                "phi": phi_out,
            }
        )

# Two paths meeting at one outcome.
out["interference"] = [
    {
        "a": a,
        "b": b,
        **pg.interference(a, b),
    }
    for a, b in (
        (pg.SQRT1_2, -pg.SQRT1_2),
        (pg.SQRT1_2, pg.SQRT1_2),
        (0.5, 0.5),
        (-0.5, 0.5),
        (0.0, 0.0),
        (1.0, -1.0),
    )
]

out["stateSpaceRows"] = pg.state_space_rows(20)

out["bitstringTable"] = [
    {"value": value, "n": n, "rows": pg.bitstring_table(value, n)}
    for value, n in ((1, 3), (0, 2), (5, 3), (7, 3), (16, 5), (31, 5))
]

print(json.dumps(out, indent=2))
