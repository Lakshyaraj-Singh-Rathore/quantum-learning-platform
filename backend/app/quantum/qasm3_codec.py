"""OpenQASM 3 import/export for the platform circuit IR.

Export is fully deterministic. Import uses the ``openqasm3`` parser when the
library is available and falls back to a line-oriented parser covering the
subset of QASM3 the platform itself emits.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from app.quantum.ir import (
    CONTROLLED_ALIASES,
    GATE_ALIASES,
    GATE_SET,
    CircuitIR,
    Condition,
    Op,
    Param,
)
from app.quantum.params import format_param

QREG = "q"
CREG = "c"

#: gates that exist directly in stdgates.inc with one control
STD_CONTROLLED = {
    ("x", 1): "cx",
    ("x", 2): "ccx",
    ("y", 1): "cy",
    ("z", 1): "cz",
    ("p", 1): "cp",
    ("rz", 1): "crz",
    ("rx", 1): "crx",
    ("ry", 1): "cry",
    ("swap", 1): "cswap",
}


class QasmError(ValueError):
    pass


# --------------------------------------------------------------------------- #
# Export
# --------------------------------------------------------------------------- #
def to_qasm3(ir: CircuitIR) -> str:
    lines = [
        "OPENQASM 3.0;",
        'include "stdgates.inc";',
        "",
        f"qubit[{ir.n_qubits}] {QREG};",
        f"bit[{ir.n_clbits}] {CREG};",
        "",
    ]
    ops = sorted(ir.ops, key=lambda o: o.layer)
    lines.extend(_emit_ops(ops, indent=0))
    return "\n".join(lines).rstrip() + "\n"


def _emit_ops(ops: list[Op], indent: int) -> list[str]:
    pad = "  " * indent
    out: list[str] = []
    for op in ops:
        out.extend(_emit_op(op, indent, pad))
    return out


def _emit_op(op: Op, indent: int, pad: str) -> list[str]:
    if op.kind == "gate":
        return [pad + _emit_gate(op)]
    if op.kind == "measure":
        q, c = op.qubits[0], (op.clbits[0] if op.clbits else op.qubits[0])
        return [f"{pad}{CREG}[{c}] = measure {QREG}[{q}];"]
    if op.kind == "reset":
        return [f"{pad}reset {QREG}[{q}];" for q in op.qubits]
    if op.kind == "barrier":
        targets = op.qubits or []
        if not targets:
            return [f"{pad}barrier {QREG};"]
        joined = ", ".join(f"{QREG}[{q}]" for q in targets)
        return [f"{pad}barrier {joined};"]
    if op.kind == "if":
        cond = _emit_condition(op.condition)
        out = [f"{pad}if ({cond}) {{}}".replace("{}", "{")]
        out.extend(_emit_ops(op.body, indent + 1))
        out.append(f"{pad}}}")
        if op.else_body:
            out.append(f"{pad}else {{")
            out.extend(_emit_ops(op.else_body, indent + 1))
            out.append(f"{pad}}}")
        return out
    if op.kind == "for":
        out = [f"{pad}for int {op.loop_var} in [0:{max((op.loop_n or 0) - 1, -1)}] {{"]
        out.extend(_emit_ops(op.body, indent + 1))
        out.append(f"{pad}}}")
        return out
    if op.kind == "while":
        cond = _emit_condition(op.condition)
        out = [f"{pad}while ({cond}) {{"]
        out.extend(_emit_ops(op.body, indent + 1))
        out.append(f"{pad}}}")
        return out
    if op.kind == "box":
        out = [f"{pad}box {{  // {op.box_name}"]
        out.extend(_emit_ops(op.body, indent + 1))
        out.append(f"{pad}}}")
        return out
    raise QasmError(f"cannot emit op kind {op.kind}")


def _emit_gate(op: Op) -> str:
    name = op.gate or "id"
    params = ""
    if op.params:
        params = "(" + ", ".join(p.expr for p in op.params) + ")"
    n_ctrl = len(op.controls)
    targets = [f"{QREG}[{q}]" for q in op.qubits]
    ctrls = [f"{QREG}[{q}]" for q in op.controls]

    if n_ctrl == 0:
        return f"{name}{params} {', '.join(targets)};"

    std = STD_CONTROLLED.get((name, n_ctrl))
    if std:
        return f"{std}{params} {', '.join(ctrls + targets)};"

    mod = "ctrl @ " if n_ctrl == 1 else f"ctrl({n_ctrl}) @ "
    return f"{mod}{name}{params} {', '.join(ctrls + targets)};"


def _emit_condition(cond: Optional[Condition]) -> str:
    if cond is None or cond.type == "true":
        return "true"
    if cond.type == "bit_eq":
        return f"{CREG}[{cond.bit}] == {1 if cond.value is None else cond.value}"
    start = 0 if cond.start is None else cond.start
    end = start + 1 if cond.end is None else cond.end
    value = cond.value
    if isinstance(value, int):
        value = format(value, f"0{end - start}b")
    # QASM slice bounds are inclusive; the IR stores an exclusive end
    return f'{CREG}[{start}:{end - 1}] == "{value}"'


# --------------------------------------------------------------------------- #
# Import
# --------------------------------------------------------------------------- #
def from_qasm3(source: str, name: str = "imported") -> CircuitIR:
    """Parse QASM3 into the platform IR (openqasm3 parser, regex fallback)."""
    try:
        return _parse_with_openqasm3(source, name)
    except QasmError:
        raise
    except Exception:  # noqa: BLE001 - fall back to the simple parser
        return _parse_fallback(source, name)


def _parse_with_openqasm3(source: str, name: str) -> CircuitIR:
    import openqasm3
    from openqasm3 import ast as qast

    program = openqasm3.parse(source)
    n_qubits = 0
    n_clbits = 0

    for stmt in program.statements:
        if isinstance(stmt, qast.QubitDeclaration):
            n_qubits = max(n_qubits, _int_of(stmt.size) or 1)
        elif isinstance(stmt, qast.ClassicalDeclaration):
            size = getattr(stmt.type, "size", None)
            n_clbits = max(n_clbits, _int_of(size) or 1)

    if n_qubits == 0:
        raise QasmError("no qubit declaration found")

    ir = CircuitIR(name=name, n_qubits=n_qubits, n_clbits=max(n_clbits, n_qubits), ops=[])
    ops = _walk_statements(program.statements, qast)
    for op in ops:
        ir.place(op, ir.max_layer() + 1 if ir.ops else 0)
    _relayer(ir)
    return ir


def _walk_statements(statements: list[Any], qast: Any) -> list[Op]:
    out: list[Op] = []
    for stmt in statements:
        op = _stmt_to_op(stmt, qast)
        if op is not None:
            out.append(op)
    return out


def _stmt_to_op(stmt: Any, qast: Any) -> Optional[Op]:  # noqa: C901 - dispatch table
    if isinstance(stmt, (qast.QubitDeclaration, qast.ClassicalDeclaration, qast.Include)):
        return None

    if isinstance(stmt, qast.QuantumGate):
        gate = stmt.name.name.lower()
        qubits = [_index_of(q) for q in stmt.qubits]
        params = [Param.from_expr(_expr_text(a)) for a in (stmt.arguments or [])]
        n_ctrl = 0
        for mod in stmt.modifiers or []:
            mod_name = getattr(mod.modifier, "name", str(mod.modifier)).lower()
            if "ctrl" in mod_name:
                n_ctrl += _int_of(mod.argument) or 1
        if n_ctrl:
            return Op(
                kind="gate",
                gate=GATE_ALIASES.get(gate, gate),
                controls=qubits[:n_ctrl],
                qubits=qubits[n_ctrl:],
                params=params,
            )
        return Op(kind="gate", gate=gate, qubits=qubits, params=params)

    if isinstance(stmt, qast.QuantumMeasurementStatement):
        qubit = _index_of(stmt.measure.qubit)
        target = _index_of(stmt.target) if stmt.target is not None else qubit
        return Op(kind="measure", qubits=[qubit], clbits=[target])

    if isinstance(stmt, qast.QuantumReset):
        return Op(kind="reset", qubits=[_index_of(stmt.qubits)])

    if isinstance(stmt, qast.QuantumBarrier):
        return Op(kind="barrier", qubits=[_index_of(q) for q in stmt.qubits if _has_index(q)])

    if isinstance(stmt, qast.BranchingStatement):
        cond = _condition_from_expr(stmt.condition, qast)
        return Op(
            kind="if",
            condition=cond,
            body=_walk_statements(stmt.if_block, qast),
            else_body=_walk_statements(stmt.else_block or [], qast),
        )

    if isinstance(stmt, qast.ForInLoop):
        n = _range_length(stmt.set_declaration)
        return Op(
            kind="for",
            loop_n=n,
            loop_var=getattr(stmt.identifier, "name", "i"),
            body=_walk_statements(stmt.block, qast),
        )

    if isinstance(stmt, qast.WhileLoop):
        return Op(
            kind="while",
            condition=_condition_from_expr(stmt.while_condition, qast),
            body=_walk_statements(stmt.block, qast),
        )

    if isinstance(stmt, qast.Box):
        return Op(kind="box", box_name="box", body=_walk_statements(stmt.body, qast))

    return None


def _condition_from_expr(expr: Any, qast: Any) -> Condition:
    if isinstance(expr, qast.BinaryExpression):
        lhs, rhs = expr.lhs, expr.rhs
        value = _literal_of(rhs)
        if _has_range(lhs):
            start, end = _range_of(lhs)
            return Condition(type="bitstring_eq", start=start, end=end, value=value)
        return Condition(type="bit_eq", bit=_index_of(lhs), value=int(value))
    if _has_index(expr):
        return Condition(type="bit_eq", bit=_index_of(expr), value=1)
    return Condition(type="true")


# ------------------------------- AST helpers ------------------------------- #
def _int_of(node: Any) -> Optional[int]:
    if node is None:
        return None
    if isinstance(node, int):
        return node
    value = getattr(node, "value", None)
    return int(value) if isinstance(value, (int, float)) else None


def _literal_of(node: Any) -> Any:
    value = getattr(node, "value", node)
    if isinstance(value, str):
        return value.strip('"')
    return value


def _index_items(node: Any) -> list[Any]:
    """Flatten the index payload of IndexedIdentifier / IndexExpression."""
    out: list[Any] = []
    for attr in ("indices", "index"):
        raw = getattr(node, attr, None)
        if raw is None:
            continue
        groups = raw if isinstance(raw, list) else [raw]
        for group in groups:
            items = group if isinstance(group, list) else [group]
            out.extend(items)
    return out


def _has_index(node: Any) -> bool:
    return bool(_index_items(node))


def _has_range(node: Any) -> bool:
    return any(hasattr(i, "start") and hasattr(i, "end") for i in _index_items(node))


def _range_of(node: Any) -> tuple[int, int]:
    for item in _index_items(node):
        if hasattr(item, "start") and hasattr(item, "end"):
            start = _int_of(item.start) or 0
            end = _int_of(item.end)
            # QASM ranges are inclusive; the IR uses an exclusive end
            return start, (start + 1 if end is None else end + 1)
    return 0, 1


def _index_of(node: Any) -> int:
    for item in _index_items(node):
        got = _int_of(item)
        if got is not None:
            return got
    raise QasmError(f"could not resolve register index from {node!r}")


def _expr_text(node: Any) -> str:
    try:
        import openqasm3

        return openqasm3.dumps(node).strip()
    except Exception:  # noqa: BLE001
        return str(_literal_of(node))


def _range_length(decl: Any) -> int:
    start = _int_of(getattr(decl, "start", None)) or 0
    end = _int_of(getattr(decl, "end", None))
    if end is None:
        return 0
    return max(end - start + 1, 0)


# --------------------------------------------------------------------------- #
# Fallback parser (subset we emit)
# --------------------------------------------------------------------------- #
_RE_QUBIT = re.compile(r"qubit\[(\d+)\]")
_RE_BIT = re.compile(r"bit\[(\d+)\]")
_RE_MEASURE_A = re.compile(r"c\[(\d+)\]\s*=\s*measure\s+q\[(\d+)\]")
_RE_MEASURE_B = re.compile(r"measure\s+q\[(\d+)\]\s*->\s*c\[(\d+)\]")
_RE_GATE = re.compile(
    r"^(?:(ctrl(?:\((\d+)\))?)\s*@\s*)?([a-zA-Z_][a-zA-Z0-9_]*)\s*(\(([^)]*)\))?\s+(.+)$"
)
_RE_QIDX = re.compile(r"q\[(\d+)\]")
_RE_IF = re.compile(r"^if\s*\((.+)\)\s*\{$")
_RE_ELSE = re.compile(r"^\}?\s*else\s*\{$")
_RE_FOR = re.compile(r"^for\s+\w+\s+(\w+)\s+in\s*\[(\d+)\s*:\s*(-?\d+)\]\s*\{$")
_RE_WHILE = re.compile(r"^while\s*\((.+)\)\s*\{$")
_RE_BOX = re.compile(r"^box\s*\{(?:\s*//\s*(\S+))?")
_RE_COND_BIT = re.compile(r'^c\[(\d+)\]\s*==\s*"?(\d+)"?$')
_RE_COND_SLICE = re.compile(r"^c\[(\d+)\s*:\s*(\d+)\]\s*==\s*\"?([01]+)\"?$")


def _parse_fallback(source: str, name: str) -> CircuitIR:
    text = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    # normalise inline braces: `for ... { h q[0]; }` -> one statement per line
    text = re.sub(r"\{", "{\n", text)
    text = re.sub(r"\}", "\n}\n", text)
    text = re.sub(r";", ";\n", text)
    raw_lines = [ln.strip() for ln in text.splitlines()]

    n_qubits = 0
    n_clbits = 0
    for line in raw_lines:
        m = _RE_QUBIT.search(line)
        if m:
            n_qubits = max(n_qubits, int(m.group(1)))
        m = _RE_BIT.search(line)
        if m:
            n_clbits = max(n_clbits, int(m.group(1)))
    if n_qubits == 0:
        raise QasmError("no qubit[N] declaration found")

    body_lines: list[str] = []
    for line in raw_lines:
        if not line or line.startswith("//"):
            continue
        if line.startswith(("OPENQASM", "include", "qubit[", "bit[")):
            continue
        body_lines.append(line)

    ops, consumed = _parse_block(body_lines, 0)
    if consumed != len(body_lines):
        pass  # tolerate trailing noise

    ir = CircuitIR(name=name, n_qubits=n_qubits, n_clbits=max(n_clbits, n_qubits), ops=[])
    for op in ops:
        ir.ops.append(op)
    _relayer(ir)
    return ir


def _parse_block(lines: list[str], i: int) -> tuple[list[Op], int]:  # noqa: C901
    ops: list[Op] = []
    while i < len(lines):
        line = lines[i]
        if line.startswith("}"):
            return ops, i
        if _RE_ELSE.match(line):
            return ops, i

        m = _RE_IF.match(line)
        if m:
            cond = _parse_condition(m.group(1))
            body, i = _parse_block(lines, i + 1)
            else_body: list[Op] = []
            if i < len(lines) and (_RE_ELSE.match(lines[i]) or lines[i] == "}"):
                if _RE_ELSE.match(lines[i]):
                    else_body, i = _parse_block(lines, i + 1)
                elif i + 1 < len(lines) and _RE_ELSE.match(lines[i + 1]):
                    else_body, i = _parse_block(lines, i + 2)
            ops.append(Op(kind="if", condition=cond, body=body, else_body=else_body))
            i += 1
            continue

        m = _RE_FOR.match(line)
        if m:
            var, start, end = m.group(1), int(m.group(2)), int(m.group(3))
            body, i = _parse_block(lines, i + 1)
            ops.append(Op(kind="for", loop_var=var, loop_n=max(end - start + 1, 0), body=body))
            i += 1
            continue

        m = _RE_WHILE.match(line)
        if m:
            cond = _parse_condition(m.group(1))
            body, i = _parse_block(lines, i + 1)
            ops.append(Op(kind="while", condition=cond, body=body))
            i += 1
            continue

        m = _RE_BOX.match(line)
        if m:
            body, i = _parse_block(lines, i + 1)
            ops.append(Op(kind="box", box_name=m.group(1) or "box", body=body))
            i += 1
            continue

        op = _parse_leaf(line)
        if op is not None:
            ops.append(op)
        i += 1
    return ops, i


def _parse_leaf(line: str) -> Optional[Op]:
    stmt = line.rstrip(";").strip()
    if not stmt:
        return None

    m = _RE_MEASURE_A.search(stmt)
    if m:
        return Op(kind="measure", qubits=[int(m.group(2))], clbits=[int(m.group(1))])
    m = _RE_MEASURE_B.search(stmt)
    if m:
        return Op(kind="measure", qubits=[int(m.group(1))], clbits=[int(m.group(2))])

    if stmt.startswith("reset"):
        return Op(kind="reset", qubits=[int(x) for x in _RE_QIDX.findall(stmt)])
    if stmt.startswith("barrier"):
        return Op(kind="barrier", qubits=[int(x) for x in _RE_QIDX.findall(stmt)])

    m = _RE_GATE.match(stmt)
    if not m:
        return None
    ctrl_kw, ctrl_n, gate, _, params_txt, targets_txt = m.groups()
    gate = gate.lower()
    qubits = [int(x) for x in _RE_QIDX.findall(targets_txt)]
    if not qubits:
        return None
    params = [Param.from_expr(p.strip()) for p in (params_txt or "").split(",") if p.strip()]

    n_ctrl = 0
    if ctrl_kw:
        n_ctrl = int(ctrl_n) if ctrl_n else 1
    elif gate in CONTROLLED_ALIASES:
        base, implied = CONTROLLED_ALIASES[gate]
        n_ctrl = implied if implied > 0 else max(len(qubits) - 1, 0)
        gate = base
    if gate not in GATE_SET and gate in GATE_ALIASES:
        gate = GATE_ALIASES[gate]
    if gate not in GATE_SET:
        raise QasmError(f"unsupported gate in QASM: {gate}")

    return Op(
        kind="gate",
        gate=gate,
        controls=qubits[:n_ctrl],
        qubits=qubits[n_ctrl:],
        params=params,
    )


def _parse_condition(text: str) -> Condition:
    raw = text.strip()
    m = _RE_COND_SLICE.match(raw)
    if m:
        return Condition(
            type="bitstring_eq",
            start=int(m.group(1)),
            end=int(m.group(2)) + 1,  # QASM end is inclusive, IR end is exclusive
            value=m.group(3),
        )
    m = _RE_COND_BIT.match(raw)
    if m:
        return Condition(type="bit_eq", bit=int(m.group(1)), value=int(m.group(2)))
    m = re.match(r"^c\[(\d+)\]$", raw)
    if m:
        return Condition(type="bit_eq", bit=int(m.group(1)), value=1)
    if raw in {"true", "1"}:
        return Condition(type="true")
    raise QasmError(f"unsupported condition: {raw}")


def _relayer(ir: CircuitIR) -> None:
    """Assign sequential-but-packed layers to top-level ops after import."""
    ops = list(ir.ops)
    ir.ops = []
    frontier: dict[int, int] = {}
    for op in ops:
        involved = op.involved_qubits() or set(range(ir.n_qubits))
        layer = max((frontier.get(q, 0) for q in involved), default=0)
        if op.kind in {"if", "for", "while", "box"} or op.condition is not None:
            layer = max(frontier.values(), default=0)
            involved = set(range(ir.n_qubits))
        op.layer = layer
        for q in involved:
            frontier[q] = layer + 1
        ir.ops.append(op)


__all__ = ["to_qasm3", "from_qasm3", "QasmError"]
