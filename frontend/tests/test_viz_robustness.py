"""Visualizations must degrade gracefully, never crash the page.

Found by feeding malformed results into every viz helper: a statevector whose
length is not a power of two (truncated payload, or a non-qubit backend) made
bloch_sphere raise "cannot reshape array of size 3 into shape (2,)", which
takes down the whole results panel rather than hiding one tab.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lib import viz  # noqa: E402

VIZ_FUNCS = [
    "histogram",
    "probability_table",
    "statevector_ket",
    "phase_disk",
    "qsphere",
    "density_matrix",
    "bloch_sphere",
    "amplitude_table",
    "born_vs_shots",
    "ideal_vs_noisy",
    "metric_meters",
    "phase_table",
]

EMPTY = {"counts": {}, "probabilities": {}, "statevector": None, "metadata": {}}
NO_SV = {"counts": {"00": 10}, "probabilities": {"00": 1.0},
         "statevector": None, "metadata": {"n_qubits": 2}}
BELL = {"counts": {"00": 500, "11": 500}, "probabilities": {"00": 0.5, "11": 0.5},
        "statevector": [[0.7071, 0], [0, 0], [0, 0], [0.7071, 0]],
        "metadata": {"n_qubits": 2}}
# 3 amplitudes: not 2**n. This is the payload that used to crash bloch_sphere.
RAGGED = {"counts": {"00": 1}, "probabilities": {"00": 1.0},
          "statevector": [[1, 0], [0, 0], [0, 0]], "metadata": {"n_qubits": 2}}
ALL_ZERO = {"counts": {"0": 1}, "probabilities": {"0": 1.0},
            "statevector": [[0, 0], [0, 0]], "metadata": {"n_qubits": 1}}


@pytest.mark.parametrize("name", VIZ_FUNCS)
@pytest.mark.parametrize(
    "result",
    [EMPTY, NO_SV, BELL, RAGGED, ALL_ZERO],
    ids=["empty", "no_statevector", "bell", "ragged_statevector", "all_zero"],
)
def test_viz_never_raises(name, result):
    func = getattr(viz, name, None)
    if func is None:
        pytest.skip(f"{name} not present")
    func(result)  # must not raise


def test_ragged_statevector_is_treated_as_absent():
    assert viz._amplitudes(RAGGED) is None


def test_power_of_two_statevector_is_parsed():
    amps = viz._amplitudes(BELL)
    assert amps is not None and amps.size == 4


def test_empty_statevector_is_none():
    assert viz._amplitudes(EMPTY) is None
