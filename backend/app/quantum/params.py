from __future__ import annotations

import ast
import math
import re

ALLOWED_CHARS = re.compile(r"^[0-9piPI+\-*/().\s]+$")


class ParamError(ValueError):
    pass


def eval_param_expr(expr: str) -> float:
    """Evaluate a parameter expression using ONLY pi, numbers, + - * / ( )."""
    raw = (expr or "").strip()
    if not raw:
        raise ParamError("empty parameter expression")
    if not ALLOWED_CHARS.match(raw):
        raise ParamError("parameter may only contain pi, numbers, and + - * / ( )")
    stripped = re.sub(r"pi", "", raw, flags=re.IGNORECASE)
    if re.search(r"[a-zA-Z_]", stripped):
        raise ParamError("variables like theta are not allowed")

    substituted = re.sub(r"pi", f"({math.pi})", raw, flags=re.IGNORECASE)
    try:
        tree = ast.parse(substituted, mode="eval")
    except SyntaxError as exc:
        raise ParamError(f"invalid expression: {exc}") from exc
    if not _is_safe(tree):
        raise ParamError("unsafe or unsupported expression")
    try:
        value = eval(compile(tree, "<param>", "eval"), {"__builtins__": {}}, {})  # noqa: S307
    except Exception as exc:  # noqa: BLE001
        raise ParamError(f"could not evaluate expression: {exc}") from exc
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ParamError("expression must evaluate to a number")
    return float(value)


def _is_safe(node: ast.AST) -> bool:
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.UAdd,
        ast.USub,
        ast.Load,
    )
    for child in ast.walk(node):
        if not isinstance(child, allowed):
            return False
        if isinstance(child, ast.Constant) and not isinstance(child.value, (int, float)):
            return False
        if isinstance(child, ast.Constant) and isinstance(child.value, bool):
            return False
    return True


def format_param(value: float) -> str:
    """Render a float radian value as a readable expression."""
    ratio = value / math.pi
    for denom in (1, 2, 3, 4, 6, 8):
        num = ratio * denom
        if abs(num - round(num)) < 1e-9 and round(num) != 0:
            n = int(round(num))
            if denom == 1:
                return "pi" if n == 1 else ("-pi" if n == -1 else f"{n}*pi")
            return f"{n}*pi/{denom}"
    if abs(value) < 1e-12:
        return "0"
    return repr(round(value, 10))
