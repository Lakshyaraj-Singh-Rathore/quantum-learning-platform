"""Fast, local checks so the Code Lab shows mistakes as you type.

Nothing here executes the learner's program. It is a static pass that runs on
every keystroke, so it must be cheap and must never raise: the point is to
surface a typo before the learner presses Build and waits for the sandbox.

A finding is ``(line, column, message)``. Line numbers are 1-based so they
match what the editor shows.
"""

from __future__ import annotations

import ast
import re

Finding = tuple[int, int, str]

#: Modules the sandbox refuses. Catching these here turns a confusing runtime
#: ImportError into an obvious red line.
BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib", "requests",
    "urllib", "importlib", "ctypes", "multiprocessing", "threading", "pickle",
}

#: Gates the platform's QASM importer understands.
QASM_GATES = {
    "h", "x", "y", "z", "id", "s", "sdg", "t", "tdg", "sx", "p", "rx", "ry",
    "rz", "cx", "cz", "ccx", "swap", "measure", "reset", "barrier",
}

_QASM_GATE_CALL = re.compile(r"^\s*([a-zA-Z][a-zA-Z0-9_]*)\s*(\([^)]*\))?\s+[a-zA-Z]")


def check_python(source: str, framework: str) -> list[Finding]:
    """Syntax, blocked imports, and the missing ``circuit`` variable."""
    findings: list[Finding] = []

    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [(exc.lineno or 1, (exc.offset or 1), f"Syntax error: {exc.msg}")]

    assigns_circuit = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in BLOCKED_IMPORTS:
                    findings.append((
                        node.lineno, node.col_offset + 1,
                        f"`{root}` is blocked in the sandbox and will fail at build time.",
                    ))
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in BLOCKED_IMPORTS:
                findings.append((
                    node.lineno, node.col_offset + 1,
                    f"`{root}` is blocked in the sandbox and will fail at build time.",
                ))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id == "circuit":
                    assigns_circuit = True

    if source.strip() and not assigns_circuit:
        findings.append((
            max(1, source.count("\n") + 1), 1,
            "Nothing is assigned to `circuit`. The platform reads that variable "
            "to find your circuit.",
        ))

    if framework == "qbraid" and "qbraid.runtime" in source:
        line = next(
            (i for i, text in enumerate(source.splitlines(), 1)
             if "qbraid.runtime" in text), 1,
        )
        findings.append((
            line, 1,
            "`qbraid.runtime` submits jobs and spends credits, so the sandbox "
            "blocks it. Use qbraid.transpiler here.",
        ))

    return sorted(findings)


def check_qasm3(source: str) -> list[Finding]:
    """Header, declarations and gate names, without a full parse.

    The real parser runs at build time. This is the subset of mistakes worth
    flagging instantly: a missing header, no qubit register, an unknown gate.
    """
    findings: list[Finding] = []
    text = source.strip()
    if not text:
        return findings

    lines = source.splitlines()
    lowered = source.lower()

    if "openqasm 3" not in lowered:
        findings.append((1, 1, "Missing the `OPENQASM 3.0;` header."))
    if not re.search(r"\bqubit\s*\[", lowered) and not re.search(r"\bqreg\b", lowered):
        findings.append((1, 1, "No qubit register declared, e.g. `qubit[2] q;`."))

    declared = set()
    for match in re.finditer(r"\b(?:qubit|bit)\s*\[\s*\d+\s*\]\s*([a-zA-Z_]\w*)", source):
        declared.add(match.group(1))

    for number, raw in enumerate(lines, 1):
        line = raw.split("//")[0].strip()
        if not line or line.startswith(("OPENQASM", "include", "qubit", "bit",
                                        "qreg", "creg", "//", "gate", "}", "{")):
            continue
        if line.startswith(("if", "for", "while", "box")):
            continue
        # `c[0] = measure q[0];` is an assignment, not a gate call.
        if "=" in line and "measure" in line:
            continue
        match = _QASM_GATE_CALL.match(line)
        if not match:
            continue
        name = match.group(1)
        if name not in QASM_GATES:
            findings.append((
                number, raw.index(name) + 1,
                f"Unknown gate `{name}`. Supported: "
                + ", ".join(sorted(QASM_GATES)[:10]) + ", …",
            ))
        if not line.endswith(";"):
            findings.append((number, len(raw), "Missing `;` at the end of the statement."))

    for number, raw in enumerate(lines, 1):
        line = raw.split("//")[0]
        # Skip the declarations themselves: in `qubit[2] q;` the token before
        # the bracket is the TYPE, not a register being indexed.
        stripped = line.strip()
        if stripped.startswith(("qubit", "bit", "qreg", "creg")):
            continue
        for register in re.findall(r"\b([a-zA-Z_]\w*)\s*\[\s*\d+\s*\]", line):
            if register in declared or register in QASM_GATES:
                continue
            findings.append((
                number, raw.index(register) + 1,
                f"`{register}` is used but never declared.",
            ))
            break

    return sorted(set(findings))


def check(source: str, framework: str) -> list[Finding]:
    """Validate ``source`` for ``framework``. Never raises."""
    try:
        if framework == "qasm3":
            return check_qasm3(source)
        return check_python(source, framework)
    except Exception:  # noqa: BLE001 - a broken checker must not break the page
        return []


def annotate(source: str, findings: list[Finding]) -> str:
    """Render the source with error markers, for a read-only preview."""
    by_line: dict[int, list[str]] = {}
    for line, _column, message in findings:
        by_line.setdefault(line, []).append(message)

    out: list[str] = []
    for number, text in enumerate(source.splitlines(), 1):
        out.append(text)
        for message in by_line.get(number, []):
            out.append(f"#  ^^^ {message}")
    return "\n".join(out)


__all__ = ["BLOCKED_IMPORTS", "QASM_GATES", "check", "check_python",
           "check_qasm3", "annotate", "Finding"]
