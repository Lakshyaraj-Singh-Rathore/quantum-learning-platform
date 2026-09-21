"""Quantum Playground: change a qubit and watch everything respond.

The design principle is cause and effect, not decoration. Move a slider and
the state, the Bloch sphere, the amplitudes, the probabilities and the
measurement histogram all update together, so the learner builds a mental
model of state -> measurement.

All maths is local (``lib.playground``) so dragging a slider does not wait on
the API, and all drawing goes through ``lib.viz``, whose Bloch and phase
helpers are already verified against analytic physics.
"""

from __future__ import annotations

import math

import streamlit as st

# Streamlit only honours set_page_config in the script it runs, and pages can
# be opened directly, so every page needs its own call or it renders narrow.
st.set_page_config(page_title="QuantumLearn", page_icon="⚛", layout="wide",
                   initial_sidebar_state="expanded")

from lib import auth, playground as pg, viz  # noqa: E402

st.title("🧪 Quantum Playground")
auth.sidebar_account()

if not auth.require_login():
    st.stop()

st.caption(
    "Every control here changes a real quantum state. Nothing is pre-recorded: "
    "the Bloch sphere, amplitudes, probabilities and histogram are all computed "
    "from the state you build."
)
st.info(
    "These same demonstrations appear inside the lessons that teach them, under "
    "**Try it yourself**. This page collects them in one place for when you "
    "want to experiment without reading."
)

tabs = st.tabs(
    [
        "Bit vs Qubit",
        "Build a Qubit",
        "Measure",
        "Interference",
        "|+⟩ vs |−⟩",
        "Many Qubits",
        "Bit Order",
    ]
)


# --------------------------------------------------------------------------- #
# 1. Classical bit vs qubit
# --------------------------------------------------------------------------- #
with tabs[0]:
    st.subheader("A bit picks a side. A qubit lives on a sphere.")
    left, right = st.columns(2)

    with left:
        st.markdown("#### Classical bit")
        bit = st.radio("A bit has exactly two options", [0, 1], horizontal=True,
                       key="pg_bit")
        st.metric("Value", bit)
        st.caption("There is nothing in between. Reading it changes nothing.")

    with right:
        st.markdown("#### Qubit")
        theta = st.slider(
            "θ — how far from |0⟩ toward |1⟩ (degrees)", 0.0, 180.0, 60.0, 1.0,
            key="pg_intro_theta",
        )
        state = pg.state_from_angles(theta, 0.0)
        p0, p1 = pg.probabilities(state)
        st.latex(r"|\psi\rangle = " + f"{state[0].real:.3f}" + r"|0\rangle + "
                 + f"{state[1].real:.3f}" + r"|1\rangle")
        bar = st.columns(2)
        bar[0].metric("P(0)", f"{p0:.1%}")
        bar[1].metric("P(1)", f"{p1:.1%}")
        st.caption(
            "Slide it anywhere. The qubit is genuinely in between — until you "
            "measure, which forces one of the two answers."
        )


# --------------------------------------------------------------------------- #
# 2. Build a qubit: amplitudes vs probabilities
# --------------------------------------------------------------------------- #
with tabs[1]:
    st.subheader("Amplitudes are not probabilities")
    st.caption(
        "Amplitudes can be negative. Probabilities never are. Square the "
        "amplitude and the sign disappears — but the sign still matters, as the "
        "Interference tab shows."
    )

    mode = st.radio(
        "Describe the state by", ["Amplitudes", "Bloch angles"],
        horizontal=True, key="pg_build_mode",
    )

    if mode == "Amplitudes":
        cols = st.columns(2)
        alpha = cols[0].slider("Amplitude of |0⟩", -1.0, 1.0, 0.8, 0.01, key="pg_a")
        beta = cols[1].slider("Amplitude of |1⟩", -1.0, 1.0, 0.6, 0.01, key="pg_b")
        state = pg.state_from_amplitudes(alpha, beta)
        if abs(math.hypot(alpha, beta) - 1.0) > 0.01:
            st.info(
                f"Your numbers had length {math.hypot(alpha, beta):.3f}, so they "
                "were rescaled to length 1. Probabilities must sum to 100%."
            )
    else:
        cols = st.columns(2)
        theta = cols[0].slider("θ (degrees)", 0.0, 180.0, 90.0, 1.0, key="pg_theta")
        phi = cols[1].slider("φ (degrees)", 0.0, 360.0, 0.0, 1.0, key="pg_phi")
        state = pg.state_from_angles(theta, phi)

    gates = st.multiselect(
        "Then apply gates, left to right",
        list(pg.GATES),
        key="pg_gates",
        help="; ".join(f"{g}: {h}" for g, h in pg.GATE_HELP.items()),
    )
    if gates:
        state = pg.apply_gates(state, gates)

    p0, p1 = pg.probabilities(state)
    theta_out, phi_out = pg.bloch_angles_of(state)

    st.markdown("#### The state")
    st.code(f"|ψ⟩ = {pg.ket_string(state)}", language="text")

    metrics = st.columns(4)
    metrics[0].metric("P(0)", f"{p0:.1%}")
    metrics[1].metric("P(1)", f"{p1:.1%}")
    metrics[2].metric("θ", f"{theta_out:.1f}°")
    metrics[3].metric("φ", f"{phi_out:.1f}°")

    st.dataframe(
        [
            {"Basis": "|0⟩", "Amplitude": f"{state[0]:.4f}", "Probability": f"{p0:.2%}"},
            {"Basis": "|1⟩", "Amplitude": f"{state[1]:.4f}", "Probability": f"{p1:.2%}"},
        ],
        hide_index=True, use_container_width=True,
    )

    st.markdown("#### On the Bloch sphere")
    # Reuse the verified renderer rather than drawing a second sphere that
    # might disagree with the Composer's.
    viz.bloch_sphere(pg.as_result(state))


# --------------------------------------------------------------------------- #
# 3. Measurement and sampling error
# --------------------------------------------------------------------------- #
with tabs[2]:
    st.subheader("Measurement collapses the state")
    st.caption(
        "You cannot predict a single shot. You can predict the distribution — "
        "and only approximately, from a finite number of shots."
    )

    cols = st.columns([1, 1, 2])
    theta = cols[0].slider("θ (degrees)", 0.0, 180.0, 90.0, 1.0, key="pg_m_theta")
    shots = cols[1].select_slider(
        "Shots", options=[1, 10, 100, 1024, 4096], value=1024, key="pg_shots"
    )
    state = pg.state_from_angles(theta, 0.0)
    p0, p1 = pg.probabilities(state)

    seed = st.session_state.get("pg_seed", 0)
    if cols[2].button("🎲 Run the experiment again", use_container_width=True):
        seed = st.session_state["pg_seed"] = seed + 1

    counts = pg.sample(state, shots, seed=seed)
    observed0 = counts["0"] / max(shots, 1)

    compare = st.columns(4)
    compare[0].metric("Expected P(0)", f"{p0:.1%}")
    compare[1].metric("Observed", f"{observed0:.1%}",
                      f"{(observed0 - p0) * 100:+.1f} pts")
    compare[2].metric("Expected P(1)", f"{p1:.1%}")
    compare[3].metric("Shots", shots)

    viz.histogram({"counts": counts})
    st.caption(
        f"With {shots} shot(s) the observed split rarely matches the theory "
        "exactly. That gap is sampling error, and it shrinks as shots grow — "
        "try 1 shot, then 4096."
    )


# --------------------------------------------------------------------------- #
# 4. Interference
# --------------------------------------------------------------------------- #
with tabs[3]:
    st.subheader("Amplitudes add before they are squared")
    st.caption(
        "This is the step with no classical counterpart, and the reason quantum "
        "algorithms can beat classical ones."
    )

    cols = st.columns(2)
    amp_a = cols[0].slider("Path A amplitude", -1.0, 1.0, pg.SQRT1_2, 0.01, key="pg_ia")
    amp_b = cols[1].slider("Path B amplitude", -1.0, 1.0, -pg.SQRT1_2, 0.01, key="pg_ib")

    result = pg.interference(amp_a, amp_b)

    st.code(
        f"  Path A : {amp_a:+.3f}\n"
        f"  Path B : {amp_b:+.3f}\n"
        f"  ─────────────────\n"
        f"  Total  : {result['amplitude']:+.3f}\n\n"
        f"  Quantum probability   = ({result['amplitude']:+.3f})² = {result['probability']:.3f}\n"
        f"  Classical probability = {result['classical']:.3f}",
        language="text",
    )

    outcome = st.columns(2)
    outcome[0].metric("Quantum P(outcome)", f"{result['probability']:.3f}")
    outcome[1].metric("Classical P(outcome)", f"{result['classical']:.3f}",
                      f"{result['probability'] - result['classical']:+.3f}")

    if result["probability"] < 0.01:
        st.success(
            "**Perfect destructive interference.** Two real paths lead here and "
            "the outcome never happens. Classically this is impossible: adding "
            "two non-negative probabilities can never give zero."
        )
    elif result["probability"] > result["classical"] + 0.01:
        st.info("**Constructive interference** — the paths reinforce.")

    st.caption(
        "Grover's algorithm is this idea repeated: arrange destructive "
        "interference on the wrong answers and constructive on the right one."
    )


# --------------------------------------------------------------------------- #
# 5. |+> vs |->
# --------------------------------------------------------------------------- #
with tabs[4]:
    st.subheader("Two states that measure identically, then behave differently")

    plus = pg.state_from_angles(90, 0)
    minus = pg.state_from_angles(90, 180)

    cols = st.columns(2)
    for column, name, state in ((cols[0], "|+⟩", plus), (cols[1], "|−⟩", minus)):
        with column:
            st.markdown(f"#### {name}")
            st.code(f"|ψ⟩ = {pg.ket_string(state)}", language="text")
            p0, p1 = pg.probabilities(state)
            st.write(f"P(0) = **{p0:.0%}**, P(1) = **{p1:.0%}**")

    st.warning(
        "In the computational basis these are indistinguishable — both give "
        "50/50. A histogram alone can never tell them apart."
    )

    if st.toggle("Apply H to both", key="pg_pm_h"):
        cols = st.columns(2)
        for column, name, state in (
            (cols[0], "H|+⟩", pg.apply_gates(plus, ["H"])),
            (cols[1], "H|−⟩", pg.apply_gates(minus, ["H"])),
        ):
            with column:
                st.markdown(f"#### {name}")
                st.code(f"|ψ⟩ = {pg.ket_string(state)}", language="text")
                p0, p1 = pg.probabilities(state)
                st.write(f"P(0) = **{p0:.0%}**, P(1) = **{p1:.0%}**")
        st.success(
            "**H|+⟩ = |0⟩ and H|−⟩ = |1⟩.** The relative phase was real "
            "information all along; one more gate turned it into a difference "
            "you can measure."
        )


# --------------------------------------------------------------------------- #
# 6. Exponential state space
# --------------------------------------------------------------------------- #
with tabs[5]:
    st.subheader("Why simulating quantum computers is hard")

    n_qubits = st.slider("Number of qubits", 1, 30, 10, key="pg_n")
    states = 2**n_qubits
    memory = states * 16 / 1e6

    cols = st.columns(3)
    cols[0].metric("Amplitudes to track", f"{states:,}")
    cols[1].metric("Memory for the state", f"{memory:,.2f} MB")
    cols[2].metric("Classical bits for one value", n_qubits)

    st.caption(
        "A classical n-bit register holds ONE of 2ⁿ values. An n-qubit state "
        "needs ALL 2ⁿ amplitudes at once, each a complex number (16 bytes)."
    )

    rows = pg.state_space_rows(min(n_qubits, 20))
    st.bar_chart({"amplitudes": [row["states"] for row in rows]},
                 x_label="qubits", y_label="amplitudes to store")

    if n_qubits >= 20:
        st.warning(
            f"At {n_qubits} qubits a simulator needs {memory:,.0f} MB just for "
            "the amplitudes. This platform caps static simulation at 20 qubits "
            "for exactly this reason — the cost doubles with every qubit added."
        )


# --------------------------------------------------------------------------- #
# 7. Bit ordering
# --------------------------------------------------------------------------- #
with tabs[6]:
    st.subheader("Which character is qubit 0?")
    st.caption(
        "This platform follows the Qiskit convention: **qubit 0 is the "
        "rightmost character**. Reading a bitstring backwards is one of the "
        "most common beginner mistakes, and it fails silently."
    )

    cols = st.columns(2)
    n_bits = cols[0].slider("Qubits", 2, 5, 3, key="pg_bits_n")
    value = cols[1].slider("Bitstring value", 0, 2**n_bits - 1, 1, key="pg_bits_v")

    bits = format(value, f"0{n_bits}b")
    st.code(f"bitstring:  {bits}", language="text")

    st.dataframe(
        [
            {
                "Qubit": row["qubit"],
                "Value": row["value"],
                "Where in the string": row["position"],
                "Is qubit 0?": "← yes, rightmost" if row["rightmost"] else "",
            }
            for row in pg.bitstring_table(value, n_bits)
        ],
        hide_index=True, use_container_width=True,
    )

    st.info(
        f"`{bits}` means q0 = **{bits[-1]}**. If you read it left to right you "
        f"would wrongly say q0 = {bits[0]}."
    )
