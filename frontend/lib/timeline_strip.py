"""Circuit timeline strip.

Rendered directly above the composer, the way IBM Quantum Composer puts its
Inspect transport bar above the circuit. Deliberately NOT inside an expander:
the user asked for the timeline and the operations list to stay visible.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from lib import api_client
from lib.api_client import ApiError


def render(ir_dict: dict[str, Any]) -> None:
    """Draw the Inspect-style transport bar and the current step's state."""
    header = st.columns([1.2, 3.2])
    with header[0]:
        st.markdown("#### 🎞 Timeline")
    with header[1]:
        if st.button(
            "Build / refresh timeline", key="build_timeline", use_container_width=True
        ):
            try:
                st.session_state["timeline"] = api_client.circuit_timeline(ir_dict)
            except ApiError as exc:
                st.error(str(exc))

    timeline = st.session_state.get("timeline")
    if not timeline:
        st.caption(
            "Step through the circuit gate by gate and watch the state evolve. "
            "Press **Build / refresh timeline** after editing the circuit."
        )
        return
    if not timeline.get("supported"):
        st.info(timeline.get("reason", "Timeline unavailable."))
        return

    steps = timeline["steps"]
    last = len(steps) - 1
    st.session_state.setdefault("tl_step", last)
    st.session_state["tl_step"] = min(st.session_state["tl_step"], last)

    nav = st.columns(4)
    if nav[0].button("|< Reset", use_container_width=True, key="tl_reset"):
        st.session_state["tl_step"] = 0
    if nav[1].button("< Prev", use_container_width=True, key="tl_prev"):
        st.session_state["tl_step"] = max(0, st.session_state["tl_step"] - 1)
    if nav[2].button("Next >", use_container_width=True, key="tl_next"):
        st.session_state["tl_step"] = min(last, st.session_state["tl_step"] + 1)
    if nav[3].button("End >|", use_container_width=True, key="tl_end"):
        st.session_state["tl_step"] = last

    # A slider needs a range; a circuit with no gates has only step 0.
    if last > 0:
        st.session_state["tl_step"] = st.slider(
            "Step", 0, last, st.session_state["tl_step"]
        )
    entry = steps[st.session_state["tl_step"]]

    head = st.columns(4)
    head[0].metric("Step", f"{entry['step']} / {last}")
    head[1].metric("Gate", entry["label"])
    head[2].metric("Depth", entry["depth"])
    if entry.get("entanglement_entropy") is not None:
        head[3].metric("Entanglement S", f"{entry['entanglement_entropy']:.3f}")

    st.info(entry["narration"])

    if entry.get("state_unavailable"):
        st.warning(entry["state_unavailable"])
    elif entry.get("top_states"):
        st.dataframe(
            [
                {
                    "State": f"|{row['state']}>",
                    "Probability": round(row["probability"], 5),
                    "Percent": f"{row['probability'] * 100:.2f}%",
                    "Rel. phase (deg)": round(row["phase_deg"], 2),
                }
                for row in entry["top_states"]
            ],
            use_container_width=True,
            hide_index=True,
        )
        if entry.get("entangled"):
            extra = ""
            if entry.get("concurrence") is not None:
                extra = f"  Concurrence = {entry['concurrence']:.2f}."
            st.success("These qubits are **entangled** at this step." + extra)


__all__ = ["render"]
