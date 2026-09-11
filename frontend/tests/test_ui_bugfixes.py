"""Regression tests for UI bugs found during the full interface audit."""

import os
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "frontend"))
sys.path.insert(0, str(ROOT / "backend"))

from app.quantum.ir import CircuitIR, Op  # noqa: E402

from lib.composer import MIN_QUBITS, RESIZE_WARNING_KEY  # noqa: E402

COMPOSER = str(ROOT / "frontend" / "pages" / "2_Composer.py")
CODE_LAB = str(ROOT / "frontend" / "pages" / "5_Code_Lab.py")

TOFFOLI_INDEX = 3  # position of "Toffoli (CCX)" in the palette


def _login(at: AppTest) -> AppTest:
    at.session_state["access_token"] = os.environ.get("TEST_TOKEN", "")
    return at


def test_min_qubits_table():
    """Multi-qubit gates need room for every control plus a distinct target."""
    assert MIN_QUBITS["cx"] == 2
    assert MIN_QUBITS["swap"] == 2
    assert MIN_QUBITS["ccx"] == 3


def test_resize_drop_warning_is_recorded():
    """Shrinking the qubit count must not delete gates silently."""
    from lib import composer

    ir = CircuitIR.model_validate({"n_qubits": 3, "n_clbits": 3, "ops": []})
    ir.place(Op(kind="gate", gate="x", qubits=[2], controls=[0]), 0)

    import streamlit as st

    st.session_state.clear()
    composer._resize(ir, 2)

    assert ir.ops == [], "the op on q2 should be removed"
    warning = st.session_state.get(RESIZE_WARNING_KEY)
    assert warning, "a warning must be recorded when ops are dropped"
    assert "removed 1 operation" in warning
    assert "q2" in warning


def test_resize_without_loss_emits_no_warning():
    from lib import composer
    import streamlit as st

    ir = CircuitIR.model_validate({"n_qubits": 3, "n_clbits": 3, "ops": []})
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)

    st.session_state.clear()
    composer._resize(ir, 2)

    assert len(ir.ops) == 1
    assert st.session_state.get(RESIZE_WARNING_KEY) is None


def test_growing_qubit_count_never_warns():
    from lib import composer
    import streamlit as st

    ir = CircuitIR.model_validate({"n_qubits": 2, "n_clbits": 2, "ops": []})
    ir.place(Op(kind="gate", gate="x", qubits=[1], controls=[0]), 0)

    st.session_state.clear()
    composer._resize(ir, 5)

    assert len(ir.ops) == 1
    assert ir.n_qubits == 5
    assert st.session_state.get(RESIZE_WARNING_KEY) is None
