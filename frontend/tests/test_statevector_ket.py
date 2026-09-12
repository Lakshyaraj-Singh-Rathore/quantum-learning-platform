"""The statevector must be readable in textbook Dirac notation."""

import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "frontend"))
sys.path.insert(0, str(ROOT / "backend"))

from lib import viz  # noqa: E402
from lib.viz import _format_amplitude_latex as fmt  # noqa: E402

R2 = 1 / np.sqrt(2)


def render(amplitudes) -> str:
    result = {"statevector": [[z.real, z.imag] for z in np.array(amplitudes, dtype=complex)]}
    captured: list[str] = []
    with patch.object(viz.st, "latex", lambda s: captured.append(s)), patch.object(
        viz.st, "caption", lambda *a, **k: None
    ):
        viz.statevector_ket(result)
    return captured[0] if captured else ""


@pytest.mark.parametrize(
    "value, expected",
    [
        (0.7071 + 0j, "0.7071"),
        (-0.7071 + 0j, "-0.7071"),
        (0.7071j, "0.7071i"),
        (-0.7071j, "-0.7071i"),
        (0.5 + 0.5j, "(0.5 + 0.5i)"),
        (0.5 - 0.5j, "(0.5 - 0.5i)"),
        (1 + 0j, "1"),
        (-1 + 0j, "-1"),
    ],
)
def test_amplitude_formatting(value, expected):
    assert fmt(value) == expected


def test_basis_state_has_no_coefficient():
    """|0> should read as |0>, not 1|0>."""
    out = render([1, 0])
    assert out == r"\left|\psi\right\rangle = \left|0\right\rangle"


def test_plus_state():
    out = render([R2, R2])
    assert r"0.7071\,\left|0\right\rangle" in out
    assert r"+ 0.7071\,\left|1\right\rangle" in out


def test_minus_state_uses_a_minus_sign():
    out = render([R2, -R2])
    assert r"- 0.7071\,\left|1\right\rangle" in out
    assert "+ -" not in out


def test_imaginary_amplitude():
    assert "0.7071i" in render([R2, R2 * 1j])


def test_bell_state_omits_zero_amplitudes():
    out = render([R2, 0, 0, R2])
    assert r"\left|00\right\rangle" in out
    assert r"\left|11\right\rangle" in out
    assert r"\left|01\right\rangle" not in out


def test_ghz_uses_three_bit_labels():
    out = render([R2, 0, 0, 0, 0, 0, 0, R2])
    assert r"\left|000\right\rangle" in out
    assert r"\left|111\right\rangle" in out


def test_no_statevector_renders_nothing():
    with patch.object(viz.st, "latex") as latex:
        viz.statevector_ket({"counts": {"00": 10}})
    latex.assert_not_called()
