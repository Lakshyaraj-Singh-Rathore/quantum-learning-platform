"""Interactive demonstrations embedded in the lessons that teach them.

Each function renders one self-contained demo. ``DEMOS_FOR_LESSON`` maps a
lesson slug to the demos that belong with it, so a learner meets the
interaction beside the paragraph it illustrates rather than on a separate page.

All state maths comes from :mod:`lib.playground` and all drawing from
:mod:`lib.viz`, whose Bloch and phase helpers are verified against analytic
physics. Nothing here re-implements either.

Layout rule: these render inside the Learn page's main column, so a demo may
use ``st.columns`` at most one level deep and must never call
``composer.render()``, which itself uses columns.
"""

from __future__ import annotations

import math

import streamlit as st

from lib import playground as pg, viz

# Optional React components. Both degrade to the Streamlit versions if their
# bundle is missing, so a lesson never breaks because a build step was skipped.
try:
    from live_bloch import is_available as _bloch_available, live_bloch
except Exception:  # noqa: BLE001
    live_bloch = None

    def _bloch_available() -> bool:
        return False

try:
    from circuit_composer import circuit_composer
    from circuit_composer import is_available as _composer_available
except Exception:  # noqa: BLE001
    circuit_composer = None

    def _composer_available() -> bool:
        return False


# --------------------------------------------------------------------------- #
# 01 qubits / 13 classical bit vs qubit
# --------------------------------------------------------------------------- #
def bit_vs_qubit(key: str) -> None:
    """A bit picks a side; a qubit lives on a continuum until you measure it.

    The measure/reset cycle is the part a probability bar cannot teach:
    measurement is destructive. Once the qubit collapses it STAYS collapsed,
    and measuring again returns the same answer, which is why the button
    disables itself and only a reset brings the superposition back.
    """
    import numpy as np

    collapsed_key = f"{key}_collapsed"      # the observed bit, or None
    history_key = f"{key}_history"          # outcomes across reset cycles
    st.session_state.setdefault(history_key, [])

    st.caption(
        "A classical bit has two options. A qubit has infinitely many — but "
        "only until you look at it."
    )
    left, right = st.columns(2)

    with left:
        st.markdown("**Classical bit**")
        bit = st.radio("Value", [0, 1], horizontal=True, key=f"{key}_bit")
        st.metric("Reads as", bit)
        st.caption(
            "Reading it changes nothing. Read it a million times and it is "
            "still the value you set."
        )

    with right:
        st.markdown("**Qubit**")
        theta = st.slider(
            "θ — how far from |0⟩ toward |1⟩", 0.0, 180.0, 90.0, 1.0,
            key=f"{key}_theta",
            disabled=st.session_state.get(collapsed_key) is not None,
            help="Locked while the qubit is collapsed — reset it to move again.",
        )
        prepared = pg.state_from_angles(theta, 0.0)
        observed = st.session_state.get(collapsed_key)
        state = (
            prepared if observed is None
            else np.array([1.0, 0.0] if observed == 0 else [0.0, 1.0], dtype=complex)
        )
        p0, p1 = pg.probabilities(state)

        st.code(f"|ψ⟩ = {pg.ket_string(state)}", language="text")
        bar = st.columns(2)
        bar[0].metric("P(0)", f"{p0:.1%}")
        bar[1].metric("P(1)", f"{p1:.1%}")

    # Controls sit below the two columns: st.columns cannot nest more than one
    # level deep, and these need a row of their own.
    st.markdown("---")
    controls = st.columns([1, 1, 2])

    if controls[0].button(
        "🔬 Measure the qubit",
        key=f"{key}_measure",
        use_container_width=True,
        disabled=observed is not None,
        help="Collapses the superposition to a single definite value.",
    ):
        outcome, _ = pg.collapse(prepared)
        st.session_state[collapsed_key] = outcome
        st.session_state[history_key] = st.session_state[history_key] + [outcome]
        st.rerun()

    if controls[1].button(
        "♻ Reset qubit",
        key=f"{key}_reset",
        use_container_width=True,
        disabled=observed is None,
        help="Prepares a fresh qubit so you can measure again.",
    ):
        st.session_state[collapsed_key] = None
        st.rerun()

    history = st.session_state[history_key]
    if history:
        zeros = history.count(0)
        recent = " ".join(str(h) for h in history[-24:])
        controls[2].caption(
            f"**{len(history)}** measurement(s): "
            f"**{zeros}** zeros, **{len(history) - zeros}** ones\n\n"
            f"`{recent}`"
        )
        if controls[2].button("Clear the record", key=f"{key}_clearhist"):
            st.session_state[history_key] = []
            st.rerun()

    if observed is None:
        st.info(
            "The qubit is in **superposition**. It has no value yet — not a "
            "hidden one you cannot see, genuinely none. Press **Measure** and "
            "it is forced to choose."
        )
    else:
        st.success(
            f"**Collapsed to |{observed}⟩.** The superposition is gone. Measure "
            f"again and you will get {observed} every time — the state really "
            "did change when you looked. Press **Reset** for a fresh qubit."
        )
        if len(history) >= 4:
            zeros = history.count(0)
            st.caption(
                f"Across {len(history)} prepare-and-measure cycles you have seen "
                f"{zeros} zeros and {len(history) - zeros} ones. Individual "
                "results are unpredictable; the proportion is not."
            )


def build_a_qubit(key: str) -> None:
    """Amplitudes are not probabilities."""
    st.caption(
        "Amplitudes can be negative; probabilities never are. Squaring hides "
        "the sign — but the sign still matters, as interference shows."
    )
    cols = st.columns(2)
    alpha = cols[0].slider("Amplitude of |0⟩", -1.0, 1.0, 0.8, 0.01, key=f"{key}_a")
    beta = cols[1].slider("Amplitude of |1⟩", -1.0, 1.0, 0.6, 0.01, key=f"{key}_b")

    state = pg.state_from_amplitudes(alpha, beta)
    if abs(math.hypot(alpha, beta) - 1.0) > 0.01:
        st.info(
            f"Your numbers had length {math.hypot(alpha, beta):.3f}, so they were "
            "rescaled to 1. Probabilities have to sum to 100%."
        )

    p0, p1 = pg.probabilities(state)
    st.code(f"|ψ⟩ = {pg.ket_string(state)}", language="text")
    st.dataframe(
        [
            {"Basis": "|0⟩", "Amplitude": f"{state[0].real:+.3f}",
             "Squared": f"{p0:.3f}", "Probability": f"{p0:.1%}"},
            {"Basis": "|1⟩", "Amplitude": f"{state[1].real:+.3f}",
             "Squared": f"{p1:.3f}", "Probability": f"{p1:.1%}"},
        ],
        hide_index=True, use_container_width=True,
    )
    if alpha * beta < 0:
        st.success(
            "One amplitude is negative, yet both probabilities are positive. "
            "That hidden sign is what makes interference possible."
        )


def bloch_explorer(key: str) -> None:
    """Move theta and phi; the sphere, state and probabilities all follow.

    Uses the React component when its bundle is present, which redraws
    continuously as you drag instead of once per Streamlit rerun. Falls back to
    sliders plus the verified Plotly sphere otherwise.
    """
    if _bloch_available() and live_bloch is not None:
        st.caption(
            "Drag the sphere to rotate it, click it to set the state, or use "
            "the sliders. Everything updates as you move — no page reload."
        )
        live_bloch(theta=90.0, phi=0.0, key=f"{key}_live")
        return

    st.caption(
        "Every pure single-qubit state is a point on this sphere. |0⟩ is the "
        "north pole, |1⟩ the south, and the equator is where measurement is a "
        "coin flip."
    )
    cols = st.columns([1, 1, 2])
    theta = cols[0].slider("θ (degrees)", 0.0, 180.0, 90.0, 1.0, key=f"{key}_theta")
    phi = cols[1].slider("φ (degrees)", 0.0, 360.0, 0.0, 1.0, key=f"{key}_phi")
    preset = cols[2].selectbox(
        "…or jump to a landmark", ["(custom)"] + list(pg.LANDMARKS),
        key=f"{key}_preset",
    )
    if preset != "(custom)":
        theta, phi = pg.LANDMARKS[preset]
        st.caption(f"Showing **{preset}** at θ={theta:.0f}°, φ={phi:.0f}°.")

    state = pg.state_from_angles(theta, phi)
    p0, p1 = pg.probabilities(state)

    st.code(f"|ψ⟩ = {pg.ket_string(state)}", language="text")
    metrics = st.columns(2)
    metrics[0].metric("P(0)", f"{p0:.1%}")
    metrics[1].metric("P(1)", f"{p1:.1%}")

    viz.bloch_sphere(pg.as_result(state))


# --------------------------------------------------------------------------- #
# 02 gates / 10 gates bootcamp
# --------------------------------------------------------------------------- #
def gate_sandbox(key: str) -> None:
    """Apply gates to a starting state and watch the Bloch vector move."""
    st.caption(
        "Gates rotate the state on the Bloch sphere. Stack a few and watch "
        "where the arrow ends up."
    )
    cols = st.columns([1, 2])
    start = cols[0].selectbox(
        "Start from", list(pg.LANDMARKS), key=f"{key}_start"
    )
    gates = cols[1].multiselect(
        "Apply gates, left to right (like a circuit wire)",
        list(pg.GATES), key=f"{key}_gates",
        help="; ".join(f"{g}: {h}" for g, h in pg.GATE_HELP.items()),
    )

    theta, phi = pg.LANDMARKS[start]
    state = pg.state_from_angles(theta, phi)
    before = pg.probabilities(state)
    if gates:
        state = pg.apply_gates(state, gates)
    after = pg.probabilities(state)

    wire = " ── ".join(["|ψ⟩"] + gates) if gates else "|ψ⟩ (no gates yet)"
    st.code(f"{wire}\n\n|ψ⟩ = {pg.ket_string(state)}", language="text")

    metrics = st.columns(3)
    metrics[0].metric("P(0)", f"{after[0]:.1%}", f"{(after[0]-before[0])*100:+.1f} pts")
    metrics[1].metric("P(1)", f"{after[1]:.1%}", f"{(after[1]-before[1])*100:+.1f} pts")
    theta_out, phi_out = pg.bloch_angles_of(state)
    metrics[2].metric("θ, φ", f"{theta_out:.0f}°, {phi_out:.0f}°")

    viz.bloch_sphere(pg.as_result(state))


def plus_vs_minus(key: str) -> None:
    """Identical histograms, different physics."""
    st.caption(
        "These two states are indistinguishable when you measure them, yet one "
        "more gate tells them apart. This is why phase is real information."
    )
    plus = pg.state_from_angles(90, 0)
    minus = pg.state_from_angles(90, 180)

    apply_h = st.toggle("Apply H to both", key=f"{key}_h")
    if apply_h:
        plus, minus = pg.apply_gates(plus, ["H"]), pg.apply_gates(minus, ["H"])

    cols = st.columns(2)
    for column, name, state in (
        (cols[0], "H|+⟩" if apply_h else "|+⟩", plus),
        (cols[1], "H|−⟩" if apply_h else "|−⟩", minus),
    ):
        with column:
            st.markdown(f"**{name}**")
            st.code(pg.ket_string(state), language="text")
            p0, p1 = pg.probabilities(state)
            st.write(f"P(0) = **{p0:.0%}** · P(1) = **{p1:.0%}**")

    if apply_h:
        st.success(
            "**H|+⟩ = |0⟩ and H|−⟩ = |1⟩.** The relative phase was carrying "
            "information the whole time; one gate turned it into something you "
            "can measure."
        )
    else:
        st.warning(
            "Both give 50/50 in the computational basis. A histogram alone can "
            "never tell them apart — toggle the switch above."
        )


# --------------------------------------------------------------------------- #
# 04 measurement
# --------------------------------------------------------------------------- #
def measurement_lab(key: str) -> None:
    """The Born rule, and the sampling error that comes with finite shots."""
    st.caption(
        "You cannot predict one shot. You can predict the distribution — and "
        "even that only approximately, from a finite number of shots."
    )
    cols = st.columns([1, 1, 1])
    theta = cols[0].slider("θ (degrees)", 0.0, 180.0, 90.0, 1.0, key=f"{key}_theta")
    shots = cols[1].select_slider(
        "Shots", options=[1, 10, 100, 1024, 4096], value=1024, key=f"{key}_shots"
    )
    seed = st.session_state.get(f"{key}_seed", 0)
    if cols[2].button("🎲 Run again", use_container_width=True, key=f"{key}_roll"):
        seed = st.session_state[f"{key}_seed"] = seed + 1

    state = pg.state_from_angles(theta, 0.0)
    p0, _ = pg.probabilities(state)
    counts = pg.sample(state, shots, seed=seed)
    observed = counts["0"] / max(shots, 1)

    # Both outcomes get a theory and an observed figure, so neither is left
    # being compared against nothing.
    observed1 = counts["1"] / max(shots, 1)
    compare = st.columns(5)
    compare[0].metric("Theory P(0)", f"{p0:.1%}")
    compare[1].metric("Observed P(0)", f"{observed:.1%}",
                      f"{(observed - p0) * 100:+.1f} pts")
    compare[2].metric("Theory P(1)", f"{1 - p0:.1%}")
    compare[3].metric("Observed P(1)", f"{observed1:.1%}",
                      f"{(observed1 - (1 - p0)) * 100:+.1f} pts")
    compare[4].metric("Shots", shots)

    viz.histogram({"counts": counts})
    st.caption(
        "The gap between theory and observation is sampling error. Try 1 shot, "
        "then 4096, and watch it shrink."
    )


# --------------------------------------------------------------------------- #
# 05 deutsch-jozsa / 06 grover
# --------------------------------------------------------------------------- #
def interference_lab(key: str) -> None:
    """Amplitudes add before they are squared."""
    st.caption(
        "Two paths lead to the same outcome. Quantum mechanics adds their "
        "amplitudes first and squares afterwards — which is how an outcome can "
        "be cancelled entirely."
    )
    cols = st.columns(2)
    amp_a = cols[0].slider("Path A amplitude", -1.0, 1.0, pg.SQRT1_2, 0.01,
                           key=f"{key}_a")
    amp_b = cols[1].slider("Path B amplitude", -1.0, 1.0, -pg.SQRT1_2, 0.01,
                           key=f"{key}_b")

    result = pg.interference(amp_a, amp_b)
    st.code(
        f"  Path A : {amp_a:+.3f}\n"
        f"  Path B : {amp_b:+.3f}\n"
        f"  ─────────────────\n"
        f"  Total  : {result['amplitude']:+.3f}\n\n"
        f"  Quantum   = ({result['amplitude']:+.3f})² = {result['probability']:.3f}\n"
        f"  Classical = {result['classical']:.3f}",
        language="text",
    )

    outcome = st.columns(2)
    outcome[0].metric("Quantum P", f"{result['probability']:.3f}")
    outcome[1].metric("Classical P", f"{result['classical']:.3f}",
                      f"{result['probability'] - result['classical']:+.3f}")

    if result["probability"] < 0.01:
        st.success(
            "**Perfect destructive interference.** Two real paths lead here and "
            "the outcome never occurs. Classically impossible: two non-negative "
            "probabilities can never sum to zero."
        )
    elif result["probability"] > result["classical"] + 0.01:
        st.info("**Constructive interference** — the paths reinforce each other.")

    st.caption(
        "Grover's algorithm is this on repeat: destructive interference on the "
        "wrong answers, constructive on the right one."
    )


# --------------------------------------------------------------------------- #
# 03 entanglement / 11 bell states
# --------------------------------------------------------------------------- #
def state_space_growth(key: str) -> None:
    """Why simulating quantum computers gets hard so fast."""
    st.caption(
        "A classical n-bit register holds ONE of 2ⁿ values. An n-qubit state "
        "needs ALL 2ⁿ amplitudes at once."
    )
    n_qubits = st.slider("Number of qubits", 1, 30, 10, key=f"{key}_n")
    states = 2**n_qubits
    memory = states * 16 / 1e6

    cols = st.columns(3)
    cols[0].metric("Amplitudes to track", f"{states:,}")
    cols[1].metric("Memory for the state", f"{memory:,.2f} MB")
    cols[2].metric("Classical bits for one value", n_qubits)

    rows = pg.state_space_rows(min(n_qubits, 20))
    st.bar_chart({"amplitudes": [row["states"] for row in rows]},
                 x_label="qubits", y_label="amplitudes")

    if n_qubits >= 20:
        st.warning(
            f"At {n_qubits} qubits the amplitudes alone need {memory:,.0f} MB. "
            "This platform caps static simulation at 20 qubits for exactly this "
            "reason — the cost doubles with every qubit."
        )


# --------------------------------------------------------------------------- #
# 04 measurement / 12 control flow
# --------------------------------------------------------------------------- #
def bit_ordering(key: str) -> None:
    """Qiskit convention: qubit 0 is the rightmost character."""
    st.caption(
        "This platform follows the Qiskit convention. Reading a bitstring the "
        "wrong way round is a common mistake, and it fails silently."
    )
    cols = st.columns(2)
    n_bits = cols[0].slider("Qubits", 2, 5, 3, key=f"{key}_n")
    value = cols[1].slider("Bitstring value", 0, 2**n_bits - 1, 1, key=f"{key}_v")

    bits = format(value, f"0{n_bits}b")
    st.code(f"bitstring:  {bits}", language="text")
    st.dataframe(
        [
            {
                "Qubit": row["qubit"],
                "Value": row["value"],
                "Position in string": row["position"],
                "Is qubit 0?": "← yes, rightmost" if row["rightmost"] else "",
            }
            for row in pg.bitstring_table(value, n_bits)
        ],
        hide_index=True, use_container_width=True,
    )
    st.info(
        f"`{bits}` means q0 = **{bits[-1]}**. Reading left to right would "
        f"wrongly give q0 = {bits[0]}."
    )


# --------------------------------------------------------------------------- #
# Circuit lab: the real composer, inside the lesson
# --------------------------------------------------------------------------- #
def circuit_lab(key: str) -> None:
    """Embed the actual drag-and-drop composer so the reader can build here.

    This is the same React component the Composer page uses, sharing the same
    session circuit, so a circuit built in a lesson is still there when the
    learner opens the Composer for the full run/export tooling.

    It deliberately does NOT call ``composer.render()``: that helper lays the
    Operations list out as one row of ``st.columns`` per operation, and these
    demos already sit inside a tab, so nesting would risk the column limit.
    """
    from lib import composer as composer_lib

    if not (_composer_available() and circuit_composer is not None):
        st.info(
            "The drag-and-drop grid is not built in this deployment. Open the "
            "**Composer** page to build circuits there."
        )
        return

    st.caption(
        "The real composer, right here. Drag a gate onto the grid, or click a "
        "gate then a cell. This shares the same circuit as the Composer page, "
        "so you can carry your work over to run and export it."
    )

    ir = composer_lib.get_circuit()
    edited = circuit_composer(
        value=ir.to_dict(), n_qubits=ir.n_qubits, key=f"{key}_grid"
    )
    if edited:
        try:
            from app.quantum.ir import CircuitIR

            composer_lib.set_circuit(CircuitIR.from_dict(edited))
            ir = composer_lib.get_circuit()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Composer returned an invalid circuit: {exc}")

    summary = st.columns(3)
    summary[0].metric("Qubits", ir.n_qubits)
    summary[1].metric("Operations", len(ir.ops))
    summary[2].metric("Depth", ir.depth())

    if st.button("↺ Clear this circuit", key=f"{key}_clear"):
        from app.quantum.ir import CircuitIR

        composer_lib.set_circuit(CircuitIR(name="untitled", n_qubits=2, n_clbits=2))
        st.rerun()

    st.caption(
        "Open the **Composer** page to run this on a simulator, inspect the "
        "state, or export it as Qiskit, Cirq, PennyLane or OpenQASM."
    )


# --------------------------------------------------------------------------- #
# Registry: which demos belong with which lesson
# --------------------------------------------------------------------------- #
#: (title, help text, render function). Titles are what the learner sees.
DEMO_REGISTRY: dict[str, tuple[str, str, object]] = {
    "bit_vs_qubit": ("A bit versus a qubit", "Discrete choice against a continuum", bit_vs_qubit),
    "build_a_qubit": ("Amplitude is not probability", "Square the amplitude to get the probability", build_a_qubit),
    "bloch": ("Explore the Bloch sphere", "Move θ and φ and watch the state follow", bloch_explorer),
    "gates": ("Gate sandbox", "Stack gates and watch the state rotate", gate_sandbox),
    "plus_minus": ("|+⟩ versus |−⟩", "Same histogram, different physics", plus_vs_minus),
    "measure": ("Measurement and sampling error", "Theory against a finite number of shots", measurement_lab),
    "interference": ("Interference lab", "Amplitudes add before they are squared", interference_lab),
    "state_space": ("Exponential state space", "Why 2ⁿ gets out of hand", state_space_growth),
    "bit_order": ("Bit ordering", "Which character is qubit 0?", bit_ordering),
    "circuit_lab": ("Build a circuit here", "The real drag-and-drop composer, in the lesson", circuit_lab),
}

#: Lesson slug -> demo keys, in the order they should appear.
DEMOS_FOR_LESSON: dict[str, list[str]] = {
    "01_qubits": ["bit_vs_qubit", "build_a_qubit", "bloch", "circuit_lab"],
    "02_gates": ["gates", "plus_minus", "circuit_lab"],
    "03_entanglement": ["state_space"],
    "04_measurement": ["measure", "bit_order"],
    "05_deutsch_jozsa": ["interference"],
    "06_grover": ["interference"],
    "10_gates_bootcamp": ["gates", "bloch", "circuit_lab"],
    "11_bell_states": ["plus_minus", "state_space", "circuit_lab"],
    "12_control_flow": ["bit_order", "circuit_lab"],
    "13_classical_bit_vs_qubit": ["bit_vs_qubit", "build_a_qubit", "measure", "circuit_lab"],
}


def demos_for(slug: str) -> list[str]:
    return DEMOS_FOR_LESSON.get(slug, [])


def render_for_lesson(slug: str) -> int:
    """Render every demo attached to ``slug``. Returns how many were drawn.

    Demos go in tabs rather than expanders. An expander here would be a
    nesting hazard -- a demo that ever needed its own expander would crash the
    page -- and tabs also keep every demo one click away instead of hidden.
    """
    keys = [key for key in demos_for(slug) if key in DEMO_REGISTRY]
    if not keys:
        return 0

    st.divider()
    st.subheader("🧪 Try it yourself")
    st.caption(
        "These are live: every control computes a real quantum state, and the "
        "visualisations are the same ones the Composer uses."
    )

    titles = [DEMO_REGISTRY[key][0] for key in keys]
    for tab, key in zip(st.tabs(titles), keys):
        title, blurb, render = DEMO_REGISTRY[key]
        with tab:
            st.caption(blurb)
            render(f"demo_{slug}_{key}")
    return len(keys)


__all__ = ["DEMO_REGISTRY", "DEMOS_FOR_LESSON", "demos_for", "render_for_lesson"]
