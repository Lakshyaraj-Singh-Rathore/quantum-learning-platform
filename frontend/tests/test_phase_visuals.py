"""Regression tests for the phase disk and Q-sphere.

Reported bug: "the quantum disk is flawed as it shows phase of only one state
when in superposition". Confirmed -- the old phase disk plotted every basis
state on one shared radial scale, so in H|0>, a Bell pair or GHZ the markers
had identical magnitude AND identical phase and landed on the exact same
(r, theta) point. Only one dot was ever visible.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

viz = pytest.importorskip("lib.viz")

SQRT2 = 1 / math.sqrt(2)


def _result(amplitudes: list[complex]) -> dict:
    return {"statevector": [[z.real, z.imag] for z in amplitudes]}


def test_relative_phase_removes_global_phase():
    """A global phase is unobservable and must not change the plot."""
    base = np.array([SQRT2, SQRT2], dtype=complex)
    rotated = base * np.exp(1j * 1.234)
    assert np.allclose(
        viz._relative_phases(base), viz._relative_phases(rotated), atol=1e-12
    )
    # reference state is pinned at zero
    assert abs(viz._relative_phases(rotated)[0]) < 1e-12


def test_relative_phase_preserves_real_phase_differences():
    """|0> + i|1> must still report a +90 degree relative phase."""
    phases = viz._relative_phases(np.array([SQRT2, 1j * SQRT2], dtype=complex))
    assert abs(math.degrees(phases[1]) - 90.0) < 1e-9


@pytest.mark.parametrize(
    "amplitudes,expected_states",
    [
        ([SQRT2, SQRT2], 2),  # H|0>
        ([SQRT2, 0, 0, SQRT2], 2),  # Bell
        ([SQRT2, 0, 0, 0, 0, 0, 0, SQRT2], 2),  # GHZ
        ([0.5, 0.5, 0.5, 0.5], 4),  # H on both qubits
    ],
)
def test_phase_disk_gives_every_state_a_distinct_position(amplitudes, expected_states):
    """The core regression: equal-phase states must not collapse onto one point."""
    captured: list = []

    class Recorder:
        def plotly_chart(self, figure, **kwargs):
            captured.append(figure)

        def caption(self, *a, **k):
            pass

        def info(self, *a, **k):
            raise AssertionError("phase_disk bailed out unexpectedly")

    original = viz.st
    viz.st = Recorder()
    try:
        viz.phase_disk(_result([complex(a) for a in amplitudes]))
    finally:
        viz.st = original

    assert captured, "no figure was rendered"
    figure = captured[0]

    # Collect the marker traces (one per basis state).
    points = [
        (float(trace.r[0]), float(trace.theta[0]))
        for trace in figure.data
        if getattr(trace, "mode", "") == "markers+text"
    ]
    assert len(points) == expected_states
    assert len(set(points)) == expected_states, (
        f"states overlap at identical coordinates: {points}"
    )


def test_qsphere_places_all_zeros_north_and_all_ones_south():
    captured: list = []

    class Recorder:
        def plotly_chart(self, figure, **kwargs):
            captured.append(figure)

        def caption(self, *a, **k):
            pass

        def info(self, *a, **k):
            raise AssertionError("qsphere bailed out unexpectedly")

    original = viz.st
    viz.st = Recorder()
    try:
        viz.qsphere(_result([complex(SQRT2), 0j, 0j, complex(SQRT2)]))
    finally:
        viz.st = original

    figure = captured[0]
    markers = [t for t in figure.data if getattr(t, "mode", "") == "markers+text"][0]
    by_label = {
        text: z for text, z in zip(markers.text, markers.z)
    }
    assert by_label["|00>"] > 0.99, "all-zeros must sit at the north pole"
    assert by_label["|11>"] < -0.99, "all-ones must sit at the south pole"


def test_histogram_forces_a_categorical_axis():
    """Bitstrings are numeric-looking and Plotly infers a linear axis.

    Reported symptom: the x-axis showed 0, 2, 4, 6, 8, 10 with bars in the
    wrong slots, and outcomes read as bare numbers rather than basis states.
    Cause: "00", "01", "10" parse as 0, 1, 10.
    """
    captured = []

    class Recorder:
        def plotly_chart(self, figure, **kwargs):
            captured.append(figure)

        def caption(self, *a, **k):
            pass

        def info(self, *a, **k):
            raise AssertionError("histogram bailed out")

        def checkbox(self, *a, **k):
            return False

    original = viz.st
    viz.st = Recorder()
    try:
        viz.histogram({"counts": {"00": 471, "01": 485, "10": 16, "11": 18}})
    finally:
        viz.st = original

    figure = captured[0]
    assert figure.layout.xaxis.type == "category", (
        "numeric-looking bitstrings must not be placed on a linear axis"
    )


def test_histogram_probability_mode_normalises():
    captured = []

    class Recorder:
        def plotly_chart(self, figure, **kwargs):
            captured.append(figure)

        def caption(self, *a, **k):
            pass

        def info(self, *a, **k):
            raise AssertionError("histogram bailed out")

    original = viz.st
    viz.st = Recorder()
    try:
        viz.histogram({"counts": {"00": 750, "11": 250}}, as_probability=True)
    finally:
        viz.st = original

    ys = list(captured[0].data[0].y)
    assert abs(sum(ys) - 1.0) < 1e-9
    assert abs(max(ys) - 0.75) < 1e-9
