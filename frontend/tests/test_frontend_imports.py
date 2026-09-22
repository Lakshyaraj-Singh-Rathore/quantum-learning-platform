"""The frontend may only import backend modules that are dependency-free.

The Streamlit image installs ``frontend/requirements.txt`` only. It gets the
backend package on ``sys.path`` (for ``CircuitIR``) but NOT the backend's
dependencies, so importing a backend module that needs one crashes the page at
runtime with ModuleNotFoundError -- which is exactly what happened when the
Games page imported ``app.quantum.inspect``, since that pulls in
``app.config`` and therefore ``pydantic-settings``.

Static import checks, so these run without the API and cost nothing.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

BACKEND = ROOT.parent / "backend"

#: Backend modules the frontend is allowed to import. Each must depend only on
#: the standard library plus packages in frontend/requirements.txt.
SAFE_BACKEND_MODULES = {
    "app.quantum.ir",
    "app.quantum.params",
}

PYTHON_FILES = sorted(
    list((ROOT / "pages").glob("*.py"))
    + list((ROOT / "lib").glob("*.py"))
    + [ROOT / "Home.py"]
)


def _backend_imports(path: Path) -> list[tuple[int, str]]:
    """Every ``app.*`` module imported by this file, with line numbers."""
    found: list[tuple[int, str]] = []
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("app"):
            found.append((node.lineno, node.module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app"):
                    found.append((node.lineno, alias.name))
    return found


@pytest.mark.parametrize("path", PYTHON_FILES, ids=lambda p: p.name)
def test_only_dependency_free_backend_modules_are_imported(path):
    for line, module in _backend_imports(path):
        assert module in SAFE_BACKEND_MODULES, (
            f"{path.name}:{line} imports {module!r}, which is not known to be "
            "safe for the Streamlit image. Backend modules that touch "
            "app.config need pydantic-settings, which the frontend does not "
            "install. Inline the helper instead."
        )


def test_the_safe_list_is_actually_safe():
    """Each allowed module must import without any backend-only package."""
    for module in SAFE_BACKEND_MODULES:
        source = BACKEND / (module.replace(".", "/") + ".py")
        assert source.is_file(), f"{module} does not exist"
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            for name in names:
                root = name.split(".")[0]
                assert root != "pydantic_settings", (
                    f"{module} imports {name}, which the frontend cannot install"
                )
                if name.startswith("app"):
                    assert name in SAFE_BACKEND_MODULES, (
                        f"{module} imports {name}, so that must be safe too"
                    )


def test_games_page_does_not_import_the_inspect_module():
    """The exact regression: inspect pulls in app.config -> pydantic-settings."""
    page = ROOT / "pages" / "6_Games.py"
    for _, module in _backend_imports(page):
        assert module != "app.quantum.inspect"


def test_circuit_stamp_strips_ids_like_the_backend():
    """The inlined helper must match app.quantum.inspect._strip_ids exactly."""
    import json
    import types

    from app.quantum.inspect import _strip_ids
    from app.quantum.ir import CircuitIR

    tree = ast.parse((ROOT / "pages" / "6_Games.py").read_text())
    func = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_without_ids"
    )
    module = types.ModuleType("stamp")
    exec(compile(ast.Module([func], []), "<stamp>", "exec"), module.__dict__)

    circuits = [
        {"n_qubits": 2, "n_clbits": 2, "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0}]},
        {"n_qubits": 2, "n_clbits": 2, "ops": [
            {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 0},
            {"kind": "if", "condition": {"type": "bit_eq", "bit": 0, "value": 1},
             "body": [{"kind": "gate", "gate": "x", "qubits": [1], "layer": 0}],
             "layer": 1}]},
    ]
    for raw in circuits:
        as_dict = CircuitIR.from_dict(raw).to_dict()
        assert json.dumps(module._without_ids(as_dict), sort_keys=True) == json.dumps(
            _strip_ids(as_dict), sort_keys=True
        )


def test_stamp_actually_removes_ids():
    import json
    import types

    from app.quantum.ir import CircuitIR

    tree = ast.parse((ROOT / "pages" / "6_Games.py").read_text())
    func = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_without_ids"
    )
    module = types.ModuleType("stamp")
    exec(compile(ast.Module([func], []), "<stamp>", "exec"), module.__dict__)

    ir = CircuitIR.from_dict({"n_qubits": 1, "n_clbits": 1, "ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0}]})
    assert '"id"' not in json.dumps(module._without_ids(ir.to_dict()))
