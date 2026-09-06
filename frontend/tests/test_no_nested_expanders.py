"""Guard against Streamlit's 'Expanders may not be nested' crash.

Regression: 2_Composer.py wrapped composer.render() -- which opens its own
expanders -- in an expander, crashing the page whenever the React composer
was built. AppTest does not enforce the nesting rule, so this checks the
source directly instead.
"""

from __future__ import annotations

import ast
import pathlib

FRONTEND = pathlib.Path(__file__).resolve().parents[1]

#: Helpers that open an expander internally, so a caller must not wrap them.
EXPANDER_OPENING_CALLS = {"render", "login_form", "require_login"}


def _is_expander(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "expander"
    )


def _calls_in(node: ast.AST) -> set[str]:
    found = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
            found.add(child.func.attr)
        elif isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            found.add(child.func.id)
    return found


def test_no_expander_wraps_an_expander_opening_helper():
    offenders = []
    for path in sorted(FRONTEND.rglob("*.py")):
        if "node_modules" in path.parts or "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.With):
                continue
            if not any(_is_expander(item.context_expr) for item in node.items):
                continue
            for name in _calls_in(node) & EXPANDER_OPENING_CALLS:
                offenders.append(f"{path.relative_to(FRONTEND)}:{node.lineno} wraps {name}()")

    assert not offenders, "expander nesting will crash Streamlit:\n  " + "\n  ".join(offenders)


def test_nested_expanders_are_never_written_literally():
    offenders = []
    for path in sorted(FRONTEND.rglob("*.py")):
        if "node_modules" in path.parts or "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.With):
                continue
            if not any(_is_expander(item.context_expr) for item in node.items):
                continue
            for child in ast.walk(node):
                if child is node or not isinstance(child, ast.With):
                    continue
                if any(_is_expander(i.context_expr) for i in child.items):
                    offenders.append(f"{path.relative_to(FRONTEND)}:{child.lineno}")

    assert not offenders, "literally nested expanders:\n  " + "\n  ".join(offenders)
