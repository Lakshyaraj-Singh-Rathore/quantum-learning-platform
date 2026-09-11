"""Streamlit grid composer.

Implements the locked UX rules without requiring the React build:
  - rows = qubits, columns = layers
  - global auto-insert column on collision
  - drop the gate on the TARGET, then pick control qubits
  - the two measurement buttons
  - if / for / while / box blocks with nested editing
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from app.quantum.ir import GATE_PARAMS, CircuitIR, Condition, Op
from app.quantum.params import ParamError, eval_param_expr

PALETTE = [
    ("h", "H", "Hadamard - creates superposition"),
    ("x", "X", "Pauli-X / NOT - bit flip"),
    ("cx", "CNOT (CX)", "Controlled-NOT - flips the target when the control is |1>"),
    ("ccx", "Toffoli (CCX)", "Flips the target when BOTH controls are |1>"),
    ("y", "Y", "Pauli-Y"),
    ("z", "Z", "Pauli-Z - phase flip"),
    ("id", "I", "Identity"),
    ("s", "S", "Phase pi/2"),
    ("sdg", "Sdg", "Phase -pi/2"),
    ("t", "T", "Phase pi/4"),
    ("tdg", "Tdg", "Phase -pi/4"),
    ("sx", "SX", "Square root of X"),
    ("p", "P(l)", "Phase gate, needs a parameter"),
    ("rx", "RX(t)", "Rotation about X"),
    ("ry", "RY(t)", "Rotation about Y"),
    ("rz", "RZ(t)", "Rotation about Z"),
    ("swap", "SWAP", "Swap two qubits"),
]

# Smallest circuit each gate can legally act on (controls + target must all be
# distinct qubits).
MIN_QUBITS = {"cx": 2, "swap": 2, "ccx": 3}

# Set by _resize() and drained on the next render.
RESIZE_WARNING_KEY = "composer_resize_warning"

STRUCTURAL = [
    ("measure", "Measure", "Measure one qubit into a classical bit"),
    ("reset", "Reset", "Reset a qubit to |0>"),
    ("barrier", "Barrier", "Visual/compiler barrier"),
]

BLOCKS = [
    ("if", "If / Else", "Conditional on classical bits"),
    ("for", "For loop", "Constant number of repetitions"),
    ("while", "While loop", "Runtime loop, capped at 32"),
    ("box", "Box", "Named sub-circuit"),
]


# --------------------------------------------------------------------------- #
# Session helpers
# --------------------------------------------------------------------------- #
def get_circuit() -> CircuitIR:
    if "circuit" not in st.session_state:
        st.session_state.circuit = CircuitIR(name="untitled", n_qubits=2, n_clbits=2)
    circuit = st.session_state.circuit
    if isinstance(circuit, dict):
        circuit = CircuitIR.from_dict(circuit)
        st.session_state.circuit = circuit
    return circuit


def set_circuit(ir: CircuitIR) -> None:
    st.session_state.circuit = ir


def circuit_dict() -> dict[str, Any]:
    return get_circuit().to_dict()


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render(key_prefix: str = "main") -> CircuitIR:
    ir = get_circuit()
    _toolbar(ir, key_prefix)
    st.divider()
    left, right = st.columns([1, 2.4], gap="medium")
    with left:
        _palette(ir, key_prefix)
    with right:
        _grid(ir, key_prefix)
    return ir


def _toolbar(ir: CircuitIR, key_prefix: str) -> None:
    columns = st.columns([1.1, 1.6, 1.6, 1.1, 1.0])

    with columns[0]:
        # The 15-qubit ceiling only applies to the dynamic engine, but a wider
        # circuit can still arrive via QASM import. Hard-coding max_value=15
        # made Streamlit raise StreamlitValueAboveMaxError and took the whole
        # Composer page down with an unrecoverable traceback, so the limit has
        # to stretch to whatever circuit is actually loaded.
        qubit_ceiling = max(15, ir.n_qubits)
        qubits = st.number_input(
            "Qubits",
            min_value=1,
            max_value=qubit_ceiling,
            value=ir.n_qubits,
            key=f"{key_prefix}_nq",
            help="Dynamic circuits are limited to 15 qubits.",
        )
        if ir.n_qubits > 15:
            st.warning(
                f"This circuit has {ir.n_qubits} qubits. Dynamic control flow "
                "is limited to 15, so it can only run as a static circuit."
            )
        if qubits != ir.n_qubits:
            _resize(ir, int(qubits))
            st.rerun()

    with columns[1]:
        if st.button(
            "Measure All (Append)",
            use_container_width=True,
            key=f"{key_prefix}_measure_all",
            help="Dynamic-safe: appends terminal measurements and deletes nothing.",
        ):
            ir.append_measure_all()
            st.rerun()

    with columns[2]:
        if st.button(
            "Normalize Terminal Measurement",
            use_container_width=True,
            key=f"{key_prefix}_normalize",
            help="Static convenience: replaces all TOP-LEVEL measurements with one "
            "terminal layer. Nested blocks are untouched.",
        ):
            warnings = ir.normalize_terminal_measurement()
            for warning in warnings:
                st.warning(warning)
            st.session_state[f"{key_prefix}_norm_warnings"] = warnings
            st.rerun()

    with columns[3]:
        if st.button("Compact", use_container_width=True, key=f"{key_prefix}_compact"):
            ir.compact_layers()
            st.rerun()

    with columns[4]:
        if st.button("Clear", use_container_width=True, key=f"{key_prefix}_clear"):
            set_circuit(CircuitIR(name=ir.name, n_qubits=ir.n_qubits, n_clbits=ir.n_clbits))
            st.rerun()

    for warning in st.session_state.pop(f"{key_prefix}_norm_warnings", []) or []:
        st.warning(warning)

    resize_warning = st.session_state.pop(RESIZE_WARNING_KEY, None)
    if resize_warning:
        st.warning(resize_warning)


def _resize(ir: CircuitIR, n_qubits: int) -> None:
    if n_qubits < ir.n_qubits:
        kept, dropped = [], []
        for op in ir.ops:
            if all(q < n_qubits for q in op.involved_qubits()):
                kept.append(op)
            else:
                dropped.append(op)
        ir.ops = kept
        if dropped:
            # Shrinking used to delete these silently, so a learner could lose
            # half a circuit and never be told.
            names = ", ".join(
                sorted({(op.gate or op.kind).upper() for op in dropped})
            )
            st.session_state[RESIZE_WARNING_KEY] = (
                f"Reducing to {n_qubits} qubit{'s' if n_qubits != 1 else ''} "
                f"removed {len(dropped)} operation"
                f"{'s' if len(dropped) != 1 else ''} that acted on qubits "
                f"q{n_qubits} and above ({names})."
            )
    ir.n_qubits = n_qubits
    ir.n_clbits = max(n_qubits, ir.n_clbits)
    set_circuit(CircuitIR.from_dict(ir.to_dict()))


def _palette(ir: CircuitIR, key_prefix: str) -> None:
    st.markdown("#### Palette")
    st.caption("Pick a gate, choose the target, then optionally add controls.")

    labels = [label for _, label, _ in PALETTE]
    choice = st.selectbox(
        "Gate",
        options=range(len(PALETTE)),
        format_func=lambda i: labels[i],
        key=f"{key_prefix}_gate_choice",
    )
    gate, _label, description = PALETTE[choice]
    st.caption(description)

    param_expr = None
    if GATE_PARAMS.get(gate):
        param_expr = st.text_input(
            "Parameter (radians)",
            value="pi/2",
            key=f"{key_prefix}_param",
            help="Only pi, numbers and + - * / ( ). Examples: pi/2, 3*pi/4, -0.5*pi, 1.234",
        )
        try:
            st.caption(f"= {eval_param_expr(param_expr):.6f} rad")
        except ParamError as exc:
            st.error(str(exc))

    qubit_options = list(range(ir.n_qubits))

    # CNOT and Toffoli are stored as X with controls, but a learner should not
    # have to know that. Picking them gives explicit, labelled control/target
    # pickers -- previously the only route was "X + add a control", and it was
    # far too easy to fill them in the wrong order and silently get
    # |00> + |01> (control and target swapped) instead of a Bell pair.
    n_controls = {"cx": 1, "ccx": 2}.get(gate)

    # A multi-qubit gate needs somewhere to put every control *and* the target.
    # Without this guard the pickers still render on an undersized circuit and
    # "Add gate" fails with the misleading "target cannot also be a control".
    min_qubits = MIN_QUBITS.get(gate, 1)
    if ir.n_qubits < min_qubits:
        st.warning(
            f"**{_label}** needs at least {min_qubits} qubits, but this circuit "
            f"has {ir.n_qubits}. Raise **Qubits** above to use it."
        )
        return

    if n_controls:
        emit_gate = "x"
        cols = st.columns(2)
        with cols[0]:
            controls = st.multiselect(
                f"Control qubit{'s' if n_controls > 1 else ''} "
                f"(pick exactly {n_controls})",
                qubit_options,
                key=f"{key_prefix}_cx_controls",
                help="The gate fires only when every control qubit is |1>.",
            )
        with cols[1]:
            target = st.selectbox(
                "Target qubit (gets flipped)",
                [q for q in qubit_options if q not in controls] or qubit_options,
                key=f"{key_prefix}_cx_target",
            )
        targets = [target]

        if len(controls) == n_controls and target not in controls:
            ctrl_txt = " and ".join(f"q{c}" for c in controls)
            st.caption(
                f"Flips **q{target}** when {ctrl_txt} "
                f"{'are' if n_controls > 1 else 'is'} |1>. "
                f"For a Bell pair: H on q0, then control q0, target q1."
            )
    elif gate == "swap":
        emit_gate = gate
        targets = st.multiselect(
            "Target qubits (exactly 2)", qubit_options, key=f"{key_prefix}_swap_targets"
        )
        controls = st.multiselect(
            "Control qubits (optional)",
            [q for q in qubit_options if q not in targets],
            key=f"{key_prefix}_controls",
        )
    else:
        emit_gate = gate
        targets = [
            st.selectbox("Target qubit", qubit_options, key=f"{key_prefix}_target")
        ]
        controls = st.multiselect(
            "Control qubits (optional)",
            [q for q in qubit_options if q not in targets],
            key=f"{key_prefix}_controls",
            help="Select one control for CX, two for Toffoli, or many for a general MCX.",
        )

    layer = st.number_input(
        "Layer (column)",
        min_value=0,
        max_value=max(ir.depth(), 0) + 1,
        value=max(ir.depth(), 0),
        key=f"{key_prefix}_layer",
        help="If the column is occupied, a new one is inserted and everything shifts right.",
    )

    if st.button("Add gate", type="primary", use_container_width=True, key=f"{key_prefix}_add"):
        if n_controls and len(controls) != n_controls:
            st.error(
                f"{_label} needs exactly {n_controls} control "
                f"qubit{'s' if n_controls > 1 else ''}; you picked {len(controls)}."
            )
            return
        if n_controls and targets[0] in controls:
            st.error("The target qubit cannot also be a control.")
            return
        try:
            params = [param_expr] if param_expr else []
            op = Op(
                kind="gate",
                gate=emit_gate,
                qubits=[int(q) for q in targets],
                controls=[int(c) for c in controls],
                params=params,
            )
            ir.place(op, int(layer))
            set_circuit(CircuitIR.from_dict(ir.to_dict()))
            st.rerun()
        except (ValueError, ParamError) as exc:
            st.error(str(exc))

    st.divider()
    st.markdown("#### Measurement & structure")
    for kind, label, help_text in STRUCTURAL:
        with st.expander(label):
            st.caption(help_text)
            if kind == "barrier":
                chosen = st.multiselect(
                    "Qubits (empty = all)", qubit_options, key=f"{key_prefix}_{kind}_q"
                )
            else:
                chosen = [st.selectbox("Qubit", qubit_options, key=f"{key_prefix}_{kind}_q")]
            clbit = None
            if kind == "measure":
                clbit = st.selectbox(
                    "Classical bit", list(range(ir.n_clbits)), key=f"{key_prefix}_{kind}_c"
                )
            if st.button(f"Add {label}", key=f"{key_prefix}_{kind}_add", use_container_width=True):
                op = Op(
                    kind=kind,
                    qubits=[int(q) for q in chosen],
                    clbits=[int(clbit)] if clbit is not None else [],
                )
                ir.place(op, ir.depth())
                set_circuit(CircuitIR.from_dict(ir.to_dict()))
                st.rerun()

    st.divider()
    st.markdown("#### Control flow blocks")
    _block_builder(ir, key_prefix)


def _block_builder(ir: CircuitIR, key_prefix: str) -> None:
    kind = st.selectbox(
        "Block type",
        [b[0] for b in BLOCKS],
        format_func=lambda k: dict((b[0], b[1]) for b in BLOCKS)[k],
        key=f"{key_prefix}_block_kind",
    )
    st.caption(dict((b[0], b[2]) for b in BLOCKS)[kind])

    kwargs: dict[str, Any] = {"kind": kind}

    if kind in {"if", "while"}:
        mode = st.radio(
            "Condition",
            ["Single bit", "Bitstring slice"],
            horizontal=True,
            key=f"{key_prefix}_cond_mode",
        )
        if mode == "Single bit":
            bit = st.selectbox(
                "Classical bit", list(range(ir.n_clbits)), key=f"{key_prefix}_cond_bit"
            )
            value = st.radio(
                "Equals", [1, 0], horizontal=True, key=f"{key_prefix}_cond_val"
            )
            kwargs["condition"] = Condition(type="bit_eq", bit=int(bit), value=int(value))
        else:
            start = st.number_input(
                "From bit", 0, ir.n_clbits - 1, 0, key=f"{key_prefix}_cond_start"
            )
            end = st.number_input(
                "To bit (exclusive)",
                int(start) + 1,
                ir.n_clbits,
                min(int(start) + 2, ir.n_clbits),
                key=f"{key_prefix}_cond_end",
            )
            pattern = st.text_input(
                "Equals bitstring",
                "1" * (int(end) - int(start)),
                key=f"{key_prefix}_cond_pattern",
            )
            kwargs["condition"] = Condition(
                type="bitstring_eq", start=int(start), end=int(end), value=pattern
            )

    if kind == "for":
        kwargs["loop_n"] = int(
            st.number_input("Repetitions N", 0, 256, 2, key=f"{key_prefix}_for_n")
        )
    if kind == "while":
        st.info("While loops are hard-capped at 32 iterations.")
    if kind == "box":
        kwargs["box_name"] = st.text_input("Box name", "block", key=f"{key_prefix}_box_name")

    if st.button("Add block", use_container_width=True, key=f"{key_prefix}_block_add"):
        try:
            ir.place(Op(**kwargs), ir.depth())
            set_circuit(CircuitIR.from_dict(ir.to_dict()))
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


# --------------------------------------------------------------------------- #
# Grid + editing
# --------------------------------------------------------------------------- #
def _grid(ir: CircuitIR, key_prefix: str) -> None:
    st.markdown("#### Timeline")
    if not ir.ops:
        st.info("Empty circuit. Add a gate from the palette to get started.")
        return

    from lib import viz

    viz.circuit_diagram(ir.to_dict())

    st.markdown("#### Operations")
    for op in sorted(ir.ops, key=lambda o: o.layer):
        columns = st.columns([0.6, 3.2, 1.0, 0.8])
        columns[0].markdown(f"`L{op.layer}`")
        columns[1].markdown(f"**{op.label()}** &nbsp; {_targets_text(op)}", unsafe_allow_html=True)

        if op.kind in {"if", "for", "while", "box"}:
            if columns[2].button("Edit inside", key=f"{key_prefix}_enter_{op.id}"):
                st.session_state[f"{key_prefix}_editing"] = op.id
                st.rerun()
        if columns[3].button("Delete", key=f"{key_prefix}_del_{op.id}"):
            ir.remove_op(op.id)
            set_circuit(CircuitIR.from_dict(ir.to_dict()))
            st.rerun()

    editing = st.session_state.get(f"{key_prefix}_editing")
    if editing:
        _nested_editor(ir, editing, key_prefix)


def _targets_text(op: Op) -> str:
    bits = []
    if op.controls:
        bits.append("ctrl " + ", ".join(f"q{c}" for c in op.controls))
    if op.qubits:
        bits.append("q" + ", q".join(str(q) for q in op.qubits))
    if op.clbits and op.kind == "measure":
        bits.append("-> c" + ", c".join(str(c) for c in op.clbits))
    if op.body:
        bits.append(f"({len(op.body)} inner op(s))")
    return " &middot; ".join(f"<code>{b}</code>" for b in bits)


def _nested_editor(ir: CircuitIR, op_id: str, key_prefix: str) -> None:
    """'Enter block' editor for nested operations."""
    block = next((o for o in ir.ops if o.id == op_id), None)
    if block is None:
        st.session_state.pop(f"{key_prefix}_editing", None)
        return

    @st.dialog(f"Edit block: {block.label()}", width="large")
    def _dialog() -> None:
        st.caption(
            "Operations added here run inside the block. "
            "Measurements inside blocks are never touched by "
            "'Normalize Terminal Measurement'."
        )

        branch = "body"
        if block.kind == "if":
            branch = (
                "body"
                if st.radio(
                    "Branch", ["if branch", "else branch"], horizontal=True, key="nested_branch"
                )
                == "if branch"
                else "else_body"
            )

        target_list: list[Op] = getattr(block, branch)

        if target_list:
            for inner in list(target_list):
                columns = st.columns([4, 1])
                columns[0].markdown(f"- **{inner.label()}** {_targets_text(inner)}", unsafe_allow_html=True)
                if columns[1].button("Remove", key=f"nested_del_{inner.id}"):
                    target_list.remove(inner)
                    set_circuit(CircuitIR.from_dict(ir.to_dict()))
                    st.rerun()
        else:
            st.info("This block is empty.")

        st.divider()
        kind = st.selectbox("Operation", ["gate", "measure", "reset"], key="nested_kind")
        qubit_options = list(range(ir.n_qubits))

        if kind == "gate":
            index = st.selectbox(
                "Gate",
                range(len(PALETTE)),
                format_func=lambda i: PALETTE[i][1],
                key="nested_gate",
            )
            gate = PALETTE[index][0]
            param = None
            if GATE_PARAMS.get(gate):
                param = st.text_input("Parameter", "pi/2", key="nested_param")
            targets = (
                st.multiselect("Targets (2)", qubit_options, key="nested_swap")
                if gate == "swap"
                else [st.selectbox("Target", qubit_options, key="nested_target")]
            )
            controls = st.multiselect(
                "Controls", [q for q in qubit_options if q not in targets], key="nested_controls"
            )
            new_op_kwargs = {
                "kind": "gate",
                "gate": gate,
                "qubits": [int(q) for q in targets],
                "controls": [int(c) for c in controls],
                "params": [param] if param else [],
            }
        else:
            qubit = st.selectbox("Qubit", qubit_options, key="nested_q")
            new_op_kwargs = {"kind": kind, "qubits": [int(qubit)]}
            if kind == "measure":
                clbit = st.selectbox("Classical bit", list(range(ir.n_clbits)), key="nested_c")
                new_op_kwargs["clbits"] = [int(clbit)]

        columns = st.columns(2)
        if columns[0].button("Add to block", type="primary", use_container_width=True):
            try:
                target_list.append(Op(**new_op_kwargs))
                set_circuit(CircuitIR.from_dict(ir.to_dict()))
                st.rerun()
            except (ValueError, ParamError) as exc:
                st.error(str(exc))
        if columns[1].button("Done", use_container_width=True):
            st.session_state.pop(f"{key_prefix}_editing", None)
            st.rerun()

    _dialog()
