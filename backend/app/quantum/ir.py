from __future__ import annotations

from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator

from app.quantum.params import eval_param_expr

#: Canonical (base) gates. Controlled variants are expressed as a base gate
#: plus a non-empty ``controls`` list, so cx == x with 1 control, ccx == x with
#: 2 controls and mcx == x with N controls.
GATE_SET = {
    "h",
    "x",
    "y",
    "z",
    "id",
    "swap",
    "s",
    "sdg",
    "t",
    "tdg",
    "sx",
    "p",
    "rx",
    "ry",
    "rz",
}

#: Number of parameters each gate expects.
GATE_PARAMS = {"p": 1, "rx": 1, "ry": 1, "rz": 1}

#: Aliases accepted from the composer / QASM importer.
GATE_ALIASES = {
    "not": "x",
    "hadamard": "h",
    "identity": "id",
    "i": "id",
    "phase": "p",
    "u1": "p",
}

#: Aliases that additionally imply a number of control qubits.
CONTROLLED_ALIASES: dict[str, tuple[str, int]] = {
    "cx": ("x", 1),
    "cnot": ("x", 1),
    "ccx": ("x", 2),
    "toffoli": ("x", 2),
    "mcx": ("x", -1),  # -1 => arbitrary number of controls
    "cz": ("z", 1),
    "cy": ("y", 1),
    "cp": ("p", 1),
    "crz": ("rz", 1),
    "cswap": ("swap", 1),
    "fredkin": ("swap", 1),
}

CONTROL_FLOW_KINDS = {"if", "for", "while", "box"}
LEAF_KINDS = {"gate", "measure", "reset", "barrier"}

WHILE_CAP = 32


class Param(BaseModel):
    expr: str
    value: float

    @classmethod
    def from_expr(cls, expr: str) -> "Param":
        return cls(expr=expr, value=eval_param_expr(expr))

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, data: Any) -> Any:
        if isinstance(data, (int, float)) and not isinstance(data, bool):
            return {"expr": repr(float(data)), "value": float(data)}
        if isinstance(data, str):
            return {"expr": data, "value": eval_param_expr(data)}
        if isinstance(data, dict) and "value" not in data and "expr" in data:
            return {"expr": data["expr"], "value": eval_param_expr(data["expr"])}
        return data


class Condition(BaseModel):
    """Classical condition: single bit equality or a bitstring slice equality."""

    type: Literal["bit_eq", "bitstring_eq", "true"] = "bit_eq"
    bit: Optional[int] = None
    start: Optional[int] = None
    end: Optional[int] = None  # exclusive
    value: Optional[str | int] = None

    def evaluate(self, cbits: list[int]) -> bool:
        if self.type == "true":
            return True
        if self.type == "bit_eq":
            if self.bit is None or self.bit >= len(cbits):
                return False
            expected = int(self.value) if self.value is not None else 1
            return int(cbits[self.bit]) == expected
        if self.type == "bitstring_eq":
            start = 0 if self.start is None else self.start
            end = start + 1 if self.end is None else self.end
            if end > len(cbits):
                return False
            # c[start:end] read with c[start] as the most significant character
            got = "".join(str(int(cbits[i])) for i in range(start, end))
            expected = self.value
            if isinstance(expected, int):
                expected = format(expected, f"0{end - start}b")
            return got == str(expected)
        return False

    def describe(self) -> str:
        if self.type == "true":
            return "true"
        if self.type == "bit_eq":
            return f"c[{self.bit}] == {1 if self.value is None else self.value}"
        start = 0 if self.start is None else self.start
        end = start + 1 if self.end is None else self.end
        return f"c[{start}:{end}] == {self.value}"


class Op(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    kind: Literal["gate", "measure", "reset", "barrier", "if", "for", "while", "box"]
    gate: Optional[str] = None
    qubits: list[int] = Field(default_factory=list)
    controls: list[int] = Field(default_factory=list)
    params: list[Param] = Field(default_factory=list)
    clbits: list[int] = Field(default_factory=list)
    layer: int = 0
    condition: Optional[Condition] = None
    body: list["Op"] = Field(default_factory=list)
    else_body: list["Op"] = Field(default_factory=list)
    loop_n: Optional[int] = None  # for-loop: compile-time constant N
    loop_var: str = "i"
    loop_bit: Optional[int] = None  # while-loop: classical bit watched
    loop_value: int = 1
    box_name: Optional[str] = None

    @model_validator(mode="after")
    def _normalize(self) -> "Op":
        if self.gate:
            name = self.gate.strip().lower()
            if name in CONTROLLED_ALIASES:
                base, n_controls = CONTROLLED_ALIASES[name]
                if n_controls < 0:
                    # arbitrary number of controls: last qubit is the target
                    if not self.controls and len(self.qubits) > 1:
                        self.controls = self.qubits[:-1]
                        self.qubits = self.qubits[-1:]
                elif not self.controls and len(self.qubits) > n_controls:
                    self.controls = self.qubits[:n_controls]
                    self.qubits = self.qubits[n_controls:]
                name = base
            name = GATE_ALIASES.get(name, name)
            self.gate = name

        if self.kind == "gate":
            if self.gate not in GATE_SET:
                raise ValueError(f"unsupported gate: {self.gate}")
            if not self.qubits:
                raise ValueError(f"gate {self.gate} requires at least one target qubit")
            expected = GATE_PARAMS.get(self.gate, 0)
            if len(self.params) != expected:
                raise ValueError(
                    f"gate {self.gate} expects {expected} parameter(s), got {len(self.params)}"
                )
            if self.gate == "swap" and len(self.qubits) != 2:
                raise ValueError("swap requires exactly 2 target qubits")
            if self.gate != "swap" and len(self.qubits) != 1:
                raise ValueError(f"gate {self.gate} requires exactly 1 target qubit")
            overlap = set(self.controls) & set(self.qubits)
            if overlap:
                raise ValueError(f"control and target qubits overlap: {sorted(overlap)}")
            if len(set(self.controls)) != len(self.controls):
                raise ValueError("duplicate control qubits")

        if self.kind == "measure":
            if len(self.qubits) != 1:
                raise ValueError("measure acts on exactly one qubit")
            if not self.clbits:
                self.clbits = [self.qubits[0]]

        if self.kind == "if" and self.condition is None:
            raise ValueError("if-block requires a condition")

        if self.kind == "for":
            if self.loop_n is None or self.loop_n < 0:
                raise ValueError("for-loop requires a compile-time constant N >= 0")

        if self.kind == "while":
            if self.loop_bit is None and self.condition is None:
                raise ValueError("while-loop requires a classical condition")
            if self.condition is None and self.loop_bit is not None:
                self.condition = Condition(type="bit_eq", bit=self.loop_bit, value=self.loop_value)

        if self.kind == "box" and not self.box_name:
            self.box_name = "box"

        return self

    # ------------------------------------------------------------------ utils
    def involved_qubits(self) -> set[int]:
        qs: set[int] = set(self.qubits) | set(self.controls)
        for child in list(self.body) + list(self.else_body):
            qs |= child.involved_qubits()
        return qs

    def involved_clbits(self) -> set[int]:
        cs: set[int] = set(self.clbits)
        if self.condition is not None:
            if self.condition.bit is not None:
                cs.add(self.condition.bit)
            if self.condition.start is not None and self.condition.end is not None:
                cs |= set(range(self.condition.start, self.condition.end))
        for child in list(self.body) + list(self.else_body):
            cs |= child.involved_clbits()
        return cs

    def is_dynamic(self) -> bool:
        """True when execution depends on runtime classical state."""
        if self.kind in {"if", "while"}:
            return True
        if self.condition is not None and self.condition.type != "true":
            return True
        return any(child.is_dynamic() for child in list(self.body) + list(self.else_body))

    def label(self) -> str:
        if self.kind == "gate":
            name = self.gate or "?"
            if self.controls:
                name = ("c" * len(self.controls)) + name if len(self.controls) < 3 else f"mc{name}"
            if self.params:
                name += "(" + ", ".join(p.expr for p in self.params) + ")"
            return name
        if self.kind == "if":
            return f"if ({self.condition.describe() if self.condition else 'true'})"
        if self.kind == "for":
            return f"for {self.loop_var} in [0..{self.loop_n})"
        if self.kind == "while":
            return f"while ({self.condition.describe() if self.condition else 'true'})"
        if self.kind == "box":
            return f"box {self.box_name}"
        return self.kind


Op.model_rebuild()


class CircuitIR(BaseModel):
    name: str = "untitled"
    n_qubits: int = 2
    n_clbits: int = 2
    ops: list[Op] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> "CircuitIR":
        if self.n_qubits < 1:
            raise ValueError("circuit needs at least one qubit")
        if self.n_clbits < self.n_qubits:
            self.n_clbits = self.n_qubits
        for op in self.walk():
            for q in op.involved_qubits():
                if q < 0 or q >= self.n_qubits:
                    raise ValueError(f"qubit index {q} out of range (n_qubits={self.n_qubits})")
            for c in op.involved_clbits():
                if c < 0 or c >= self.n_clbits:
                    raise ValueError(f"clbit index {c} out of range (n_clbits={self.n_clbits})")
        return self

    # -------------------------------------------------------------- inspection
    def is_dynamic(self) -> bool:
        return any(op.is_dynamic() for op in self.ops)

    def max_layer(self) -> int:
        if not self.ops:
            return -1
        return max(op.layer for op in self.ops)

    def occupied_at(self, layer: int) -> set[int]:
        occ: set[int] = set()
        for op in self.ops:
            if op.layer == layer:
                occ |= op.involved_qubits()
        return occ

    def clbits_written_at(self, layer: int) -> set[int]:
        """Classical bits written by ops already sitting in ``layer``."""
        written: set[int] = set()
        for op in self.ops:
            if op.layer == layer and op.kind == "measure":
                written |= set(op.clbits)
        return written

    def walk(self) -> list[Op]:
        out: list[Op] = []

        def rec(ops: list[Op]) -> None:
            for op in ops:
                out.append(op)
                rec(op.body)
                rec(op.else_body)

        rec(self.ops)
        return out

    def has_measurements(self) -> bool:
        return any(op.kind == "measure" for op in self.walk())

    def depth(self) -> int:
        return self.max_layer() + 1

    # ------------------------------------------------------------------ edits
    def shift_layers(self, from_layer: int) -> None:
        for op in self.ops:
            if op.layer >= from_layer:
                op.layer += 1

    def place(self, op: Op, layer: int) -> None:
        """Place ``op`` at ``layer`` using global auto-insert-column collisions.

        If any qubit involved in ``op`` is already busy at ``layer``, a new
        column is inserted at ``layer`` and every op with ``layer >= t`` shifts
        one step right (IBM Quantum Composer behaviour).
        """
        if layer < 0:
            layer = 0
        # A qubit collision is the obvious case, but two measurements writing
        # the same classical bit in one column also conflict: the second
        # silently overwrote the first, so the earlier result vanished from
        # the counts with nothing to indicate it had happened.
        clbit_clash = bool(
            op.kind == "measure" and set(op.clbits) & self.clbits_written_at(layer)
        )
        if op.involved_qubits() & self.occupied_at(layer) or clbit_clash:
            self.shift_layers(layer)
        op.layer = layer
        self.ops.append(op)
        self.ops.sort(key=lambda o: o.layer)

    def remove_op(self, op_id: str) -> bool:
        before = len(self.ops)
        self.ops = [o for o in self.ops if o.id != op_id]
        return len(self.ops) != before

    def compact_layers(self) -> None:
        """Remove empty columns without reordering operations."""
        used = sorted({op.layer for op in self.ops})
        remap = {old: new for new, old in enumerate(used)}
        for op in self.ops:
            op.layer = remap[op.layer]

    # ----------------------------------------------------------- measurements
    def append_measure_all(self) -> None:
        """Button A - dynamic safe.

        Appends terminal measurements for every qubit at the end of the
        top-level timeline. Existing measurements (including mid-circuit ones
        used by dynamic logic) are left untouched.
        """
        layer = self.max_layer() + 1
        for q in range(self.n_qubits):
            self.ops.append(Op(kind="measure", qubits=[q], clbits=[q], layer=layer))

    def normalize_terminal_measurement(self) -> list[str]:
        """Button B - static convenience, TOP LEVEL ONLY.

        Removes every ``measure`` op in the top-level timeline and inserts one
        clean terminal measure-all layer. Measurements nested inside
        blocks/boxes are never touched. Returns warnings to surface in the UI.
        """
        warnings: list[str] = []
        removed = len([o for o in self.ops if o.kind == "measure"])
        nested = [o for o in self.walk() if o.kind == "measure" and o not in self.ops]
        self.ops = [op for op in self.ops if op.kind != "measure"]
        self.compact_layers()
        layer = self.max_layer() + 1
        for q in range(self.n_qubits):
            self.ops.append(Op(kind="measure", qubits=[q], clbits=[q], layer=layer))
        if removed:
            warnings.append(
                f"Removed {removed} top-level measurement(s); this may break dynamic semantics."
            )
        if nested:
            warnings.append(
                f"{len(nested)} measurement(s) inside nested blocks were left unchanged."
            )
        return warnings

    # ------------------------------------------------------------------- io
    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CircuitIR":
        return cls.model_validate(data)


def empty_circuit(n_qubits: int = 2, name: str = "untitled") -> CircuitIR:
    return CircuitIR(name=name, n_qubits=n_qubits, n_clbits=n_qubits, ops=[])
