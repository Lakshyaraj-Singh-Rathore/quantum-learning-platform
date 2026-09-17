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


def _signature(ir_dict: dict[str, Any]) -> str:
    """Identity of the circuit a cached timeline was built from."""
    import json

    return json.dumps(ir_dict, sort_keys=True)


def render(ir_dict: dict[str, Any]) -> None:
    """Draw the Inspect-style transport bar and the current step's state.

    The timeline builds itself automatically and refreshes whenever the circuit
    changes. It used to sit behind a "Build / refresh timeline" button, but
    pressing that button adds four transport controls and a table to the page,
    and Streamlit reacts to a change in the number of elements above a custom
    component by destroying and recreating its iframe -- which left the
    drag-and-drop composer as a blank white box. Rendering unconditionally
    keeps the element count above the composer stable.
    """
    header = st.columns([1.2, 3.2])
    with header[0]:
        st.markdown("#### 🎞 Timeline")

    signature = _signature(ir_dict)
    cached_for = st.session_state.get("timeline_signature")
    timeline = st.session_state.get("timeline")

    if timeline is None or cached_for != signature:
        try:
            timeline = api_client.circuit_timeline(ir_dict)
            st.session_state["timeline"] = timeline
            st.session_state["timeline_signature"] = signature
            # A new circuit means the old step index may not exist any more.
            st.session_state.pop("tl_step", None)
        except ApiError as exc:
            with header[1]:
                st.caption(f"Timeline unavailable: {exc}")
            return

    if not timeline:
        st.caption("Step through the circuit gate by gate and watch the state evolve.")
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
