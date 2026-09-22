"""No duplicate controls, and buttons that actually stick.

Reported together: the Composer toolbar appeared twice, and Clear, Reset,
Measure All and Delete all seemed not to work. Same root cause. The React grid
renders its own Qubits/Measure All/Normalize/Compact/Clear along the top of the
canvas, and ``composer.render()`` drew a second identical set. Worse, the
Python copies mutated the session circuit while the component -- keyed on a
constant -- replayed its stale value on the next rerun and overwrote them.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

COMPOSER_LIB = ROOT / "lib" / "composer.py"
PAGES_WITH_GRID = [ROOT / "pages" / "2_Composer.py", ROOT / "pages" / "6_Games.py"]


# ------------------------------------------------------- no duplicate toolbar
def test_toolbar_is_skipped_when_the_grid_owns_it():
    """secondary=True means the React canvas already has these controls."""
    source = COMPOSER_LIB.read_text()
    render = source[source.index("def render("):source.index("def _toolbar(")]
    assert "if not secondary:" in render
    assert render.index("if not secondary:") < render.index("_toolbar(ir, key_prefix)")


def test_toolbar_still_renders_without_the_grid():
    """The Python editor is the fallback; it must keep its controls."""
    source = COMPOSER_LIB.read_text()
    assert "_toolbar(ir, key_prefix)" in source


# ------------------------------------------ the grid cannot undo Python edits
def test_set_circuit_bumps_the_grid_epoch():
    from lib import composer

    assert hasattr(composer, "grid_epoch")
    assert hasattr(composer, "GRID_EPOCH_KEY")


def test_grid_updates_do_not_bump_the_epoch():
    """Remounting mid-drag would lose the interaction."""
    import inspect

    from lib import composer

    source = inspect.getsource(composer.set_circuit)
    assert "from_grid" in source
    assert "if not from_grid:" in source


@pytest.mark.parametrize("page", PAGES_WITH_GRID, ids=lambda p: p.name)
def test_component_is_keyed_on_the_epoch(page):
    """A constant key lets Streamlit replay the component's stale value."""
    source = page.read_text()
    assert 'key="react_composer"' not in source, (
        "a constant key makes Python-side edits get overwritten"
    )
    assert "grid_epoch()" in source


def test_every_grid_callback_marks_itself_as_from_grid():
    """Otherwise the component's own echo would bump the epoch every rerun."""
    for path in ROOT.rglob("*.py"):
        if "node_modules" in str(path) or path.name.startswith("test_"):
            continue
        text = path.read_text()
        if "CircuitIR.from_dict(edited)" not in text:
            continue
        for line in text.splitlines():
            if "CircuitIR.from_dict(edited)" in line and "set_circuit" in line:
                assert "from_grid=True" in line, f"{path.name}: {line.strip()}"


# ------------------------------------------------------------ delete an op
def test_operations_list_offers_delete():
    source = COMPOSER_LIB.read_text()
    assert '"Delete"' in source
    assert "ir.remove_op(op.id)" in source


def test_delete_persists_through_set_circuit():
    """Removing an op must write the circuit back, not mutate a copy."""
    source = COMPOSER_LIB.read_text()
    grid = source[source.index("def _grid("):]
    delete = grid[grid.index('"Delete"'):]
    assert "set_circuit(" in delete[:400]


def test_remove_op_actually_removes():
    from app.quantum.ir import CircuitIR

    ir = CircuitIR.from_dict({"n_qubits": 2, "n_clbits": 2, "ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [1], "layer": 1}]})
    target = ir.ops[0].id
    ir.remove_op(target)
    assert len(ir.ops) == 1
    assert all(op.id != target for op in ir.ops)


# ------------------------------------------------- measurement button rules
def test_measure_all_appends_without_deleting():
    from app.quantum.ir import CircuitIR

    ir = CircuitIR.from_dict({"n_qubits": 2, "n_clbits": 2, "ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1}]})
    ir.append_measure_all()
    measures = [op for op in ir.ops if op.kind == "measure"]
    assert len(measures) == 3, "the existing mid-circuit measure must survive"
    assert any(op.layer == 1 for op in measures)


def test_normalize_leaves_nested_measures_alone():
    from app.quantum.ir import CircuitIR

    ir = CircuitIR.from_dict({"n_qubits": 2, "n_clbits": 2, "ops": [
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 0},
        {"kind": "if", "condition": {"type": "bit_eq", "bit": 0, "value": 1},
         "body": [{"kind": "measure", "qubits": [1], "clbits": [1], "layer": 0}],
         "layer": 1}]})
    ir.normalize_terminal_measurement()
    block = next(op for op in ir.ops if op.kind == "if")
    assert any(op.kind == "measure" for op in block.body)


# ---------------------------------------------------------- editor checks
def test_code_lab_validates_by_default():
    """Problems must be visible without pressing Build."""
    page = (ROOT / "pages" / "5_Code_Lab.py").read_text()
    assert "code_checks.check(code, framework)" in page
    # Not hidden behind an expander or a button.
    index = page.index("code_checks.check(code, framework)")
    assert "st.expander" not in page[max(0, index - 300):index]


def test_code_lab_imports_the_checker():
    tree = ast.parse((ROOT / "pages" / "5_Code_Lab.py").read_text())
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "lib"
        for alias in node.names
    }
    assert "code_checks" in imported
