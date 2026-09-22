"""Quantum Password Search — the Grover module on the Games tab.

Presentation only. Every number shown comes from ``lib.grover_lab``, which
simulates a real 2**n state vector; nothing here invents a percentage.

Two framings the module is deliberate about:

* Grover is never described as "trying all 64 passwords at once". The pipeline
  shown is superposition, oracle, amplification, measurement.
* The optimal iteration count is floor(pi/4*sqrt(N)), not sqrt(N). The module
  lets the learner overshoot on purpose and watch the probability fall, which
  is the part that makes the distinction stick.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from lib import grover_lab as gl


def _search_space_grid(n_qubits: int, target: int, probabilities, top: int = 64) -> None:
    """Show every basis state with its current probability."""
    n_states = 2**n_qubits
    rows = []
    for index in range(min(n_states, top)):
        rows.append({
            "State": ("🎯 " if index == target else "") + gl.label(index, n_qubits),
            "Probability": float(probabilities[index]),
        })
    frame = pd.DataFrame(rows)
    st.dataframe(
        frame,
        hide_index=True,
        use_container_width=True,
        height=min(420, 40 + 28 * len(rows)),
        column_config={
            "Probability": st.column_config.ProgressColumn(
                "Probability", min_value=0.0, max_value=1.0, format="%.4f",
            )
        },
    )


def render() -> None:
    st.markdown("### 🔐 Quantum Password Search")
    st.caption(
        "A teaching simulation of Grover's algorithm. The password is a toy "
        "binary string that never leaves your browser session, and nothing "
        "here touches a real system."
    )

    st.info(
        "**Quantum computers do not magically crack passwords.** Grover's "
        "algorithm gives a *quadratic* speedup for searching an unstructured "
        "space — O(√N) oracle queries instead of O(N) — and only when you "
        "already have an oracle that can recognise a correct answer."
    )

    # ---------------------------------------------------------------- setup
    setup = st.columns([1, 1, 2])
    n_qubits = setup[0].slider(
        "Password length (qubits)", gl.MIN_QUBITS, gl.MAX_QUBITS, 6,
        key="grover_n",
        help="Capped at 6 so the whole 64-state space stays visible.",
    )
    n_states = 2**n_qubits
    default = "1" * n_qubits if n_qubits < 6 else "101101"
    raw = setup[1].text_input(
        "Toy password (binary)", value=default, max_chars=n_qubits, key="grover_pw"
    )
    setup[2].metric("Search space", f"2^{n_qubits} = {n_states} states")

    target, error = gl.parse_password(raw, n_qubits)
    if target is None:
        st.warning(error)
        return

    optimal = gl.optimal_iterations(n_qubits)

    # ------------------------------------------------------------- predict
    with st.expander("🤔 Predict first — what will Grover do?", expanded=False):
        guess = st.radio(
            "Before you run it:",
            [
                "It checks every password one by one, just faster",
                "It amplifies the amplitude of the target state",
                "Every state disappears except the target",
                "The computer simply knows the answer",
            ],
            key="grover_guess",
        )
        if st.button("Reveal", key="grover_reveal"):
            if guess.startswith("It amplifies"):
                st.success(
                    "Correct. The oracle marks the target with a phase flip, and "
                    "the diffusion operator turns that phase difference into a "
                    "larger amplitude. Nothing is checked one at a time."
                )
            else:
                st.error(
                    "Not quite. Grover prepares a superposition, marks the target "
                    "with a **phase flip**, then amplifies that marked amplitude. "
                    "It never reads candidates one by one, and the other states "
                    "do not vanish — they just end up with small amplitudes."
                )

    # ----------------------------------------------------------- the run
    frames = gl.run(n_qubits, target, optimal)

    st.markdown("#### The pipeline")
    st.code(
        "superposition  →  oracle (phase flip)  →  diffusion (amplify)  →  measure",
        language="text",
    )

    step = st.slider(
        "Grover iteration", 0, optimal, optimal, key="grover_step",
        help=f"Optimal for {n_states} states is ⌊π/4·√N⌋ = {optimal}.",
    )
    frame = frames[step]

    metrics = st.columns(4)
    metrics[0].metric("Iteration", f"{step} / {optimal}")
    metrics[1].metric("P(target)", f"{frame['target_probability']:.2%}")
    others = (1 - frame["target_probability"]) / max(1, n_states - 1)
    metrics[2].metric("P(any other state)", f"{others:.2%}")
    metrics[3].metric(
        "Target amplitude", f"{frame['amplitudes'][target].real:+.4f}"
    )

    if step == 0:
        st.caption(
            f"Every state starts with amplitude 1/√{n_states} = "
            f"{1 / np.sqrt(n_states):.4f}, so each is equally likely."
        )

    # ------------------------------------------------- amplification curve
    st.markdown("#### How the target's probability grows")
    curve = pd.DataFrame({
        "iteration": [f["iteration"] for f in frames],
        "target": [f["target_probability"] for f in frames],
        "each other state": [
            (1 - f["target_probability"]) / max(1, n_states - 1) for f in frames
        ],
    }).set_index("iteration")
    st.line_chart(curve)

    # The over-rotation lesson: going past the optimum makes it worse.
    if st.toggle(
        "Show what happens if you keep going past the optimum",
        key="grover_over",
        help="A common misconception is that more iterations is always better.",
    ):
        extra = gl.run(n_qubits, target, optimal * 2 + 2)
        over = pd.DataFrame({
            "iteration": [f["iteration"] for f in extra],
            "P(target)": [f["target_probability"] for f in extra],
        }).set_index("iteration")
        st.line_chart(over)
        peak = max(extra, key=lambda f: f["target_probability"])
        st.warning(
            f"The probability peaks at iteration **{peak['iteration']}** "
            f"({peak['target_probability']:.1%}) and then **falls again**. "
            "Grover rotates the state toward the target; keep rotating and you "
            "go past it. This is why the optimal count is ⌊π/4·√N⌋ and not √N — "
            f"for N={n_states} that is {optimal}, not {int(np.sqrt(n_states))}."
        )

    # --------------------------------------------------------- state space
    st.markdown("#### The search space right now")
    _search_space_grid(n_qubits, target, frame["probabilities"])

    # -------------------------------------------------------- measurement
    st.markdown("#### Measure")
    measure_cols = st.columns([1, 3])
    shots = measure_cols[0].select_slider(
        "Shots", options=[1, 10, 100, 1024], value=100, key="grover_shots"
    )
    seed = st.session_state.get("grover_seed", 0)
    if measure_cols[0].button("🎲 Measure", key="grover_measure", use_container_width=True):
        seed = st.session_state["grover_seed"] = seed + 1

    counts = gl.measure(frame["amplitudes"], shots, seed=seed)
    hits = counts.get(target, 0)
    with measure_cols[1]:
        st.metric(
            f"Measured the target in {hits}/{shots} shots",
            f"{hits / max(shots, 1):.1%}",
            f"theory {frame['target_probability']:.1%}",
        )
        top = sorted(counts.items(), key=lambda kv: -kv[1])[:6]
        st.dataframe(
            [{"State": gl.label(i, n_qubits), "Shots": c,
              "Is target": "🎯" if i == target else ""} for i, c in top],
            hide_index=True, use_container_width=True,
        )

    # ------------------------------------------------------- the comparison
    st.markdown("#### Classical search versus Grover")
    classical = gl.classical_attempts(n_qubits, target)
    st.dataframe(
        [
            {"": "How it searches",
             "Classical brute force": "One candidate at a time",
             "Grover": "Marks the target, amplifies its amplitude"},
            {"": "Queries needed",
             "Classical brute force": f"up to {classical['worst_case']}",
             "Grover": f"about ⌊π/4·√{n_states}⌋ = {optimal}"},
            {"": "Complexity",
             "Classical brute force": "O(N)",
             "Grover": "O(√N)"},
            {"": "For this password",
             "Classical brute force": f"{classical['checked_to_find']} checks scanning in order",
             "Grover": f"{optimal} iterations → {frames[-1]['target_probability']:.1%}"},
            {"": "Result",
             "Classical brute force": "Certain",
             "Grover": "Probabilistic — very likely, not guaranteed"},
        ],
        hide_index=True, use_container_width=True,
    )

    with st.expander("Why 6 qubits is only a demonstration"):
        st.markdown(
            f"""
This search space is **{n_states} states**. A real 12-character password drawn
from 94 printable characters is about 10²³ possibilities — Grover would reduce
that to roughly 10¹¹ *oracle queries*, which is still far beyond any machine
that exists or is planned.

Real systems also defend in ways this model ignores: passwords are salted and
hashed, attempts are rate-limited, and multi-factor authentication means the
password alone is not enough.

**The honest takeaway.** Grover halves the effective key length, so a scheme
that needs 128 bits of classical security needs about 256 bits to keep the same
margin against a quantum attacker. That is a real consideration for the design
of future cryptography — not a way to break into accounts.
            """
        )


__all__ = ["render"]
