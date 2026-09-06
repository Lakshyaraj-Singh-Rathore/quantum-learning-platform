"""QuantumLearn - Streamlit entrypoint."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="QuantumLearn",
    page_icon="⚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

from lib import api_client, auth  # noqa: E402
from lib.api_client import ApiError  # noqa: E402

auth.sidebar_account()

st.title("⚛ QuantumLearn")
st.markdown(
    "#### An AI-based interactive platform for learning quantum algorithms\n"
    "Design circuits by hand, simulate them on four backends, and get grounded AI tutoring."
)

if not auth.is_logged_in():
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.markdown(
            """
### What you can do here

**Learn** - structured lessons from qubits and gates through Grover, VQE/QAOA and
dynamic circuits.

**Compose** - a grid/timeline circuit editor with the full gate palette, general
multi-controlled gates, and `if` / `for` / `while` / `box` control-flow blocks.

**Simulate** - run static circuits on **Qiskit Aer**, **Cirq**, **PennyLane** and
**qBraid**. Circuits with runtime classical feedback are routed automatically to the
**Qiskit dynamic engine**.

**Visualize** - histograms, probability tables, the **phase disk**, Bloch spheres and a
live circuit diagram.

**Practice** - quizzes and autograded coding challenges, with personalized
recommendations based on your weakest concepts.
            """
        )
    with right:
        auth.login_form()
    st.stop()

user = auth.current_user() or {}
st.success(f"Signed in as **{user.get('email')}** ({user.get('role')})")

try:
    progress = api_client.my_progress()
    columns = st.columns(4)
    columns[0].metric("Quizzes taken", progress["quizzes_taken"])
    columns[1].metric("Challenges attempted", progress["challenges_attempted"])
    columns[2].metric("Challenges passed", progress["challenges_passed"])
    columns[3].metric("Average quiz score", f"{progress['average_quiz_percentage']}%")

    recommendations = progress.get("recommendations") or []
    if recommendations:
        st.markdown("### Recommended next")
        for item in recommendations:
            icon = "📘" if item["kind"] == "lesson" else "🧩"
            st.markdown(
                f"{icon} **{item.get('title', item['slug'])}** "
                f"<span style='color:#888'>— {item['reason']}</span>",
                unsafe_allow_html=True,
            )
except ApiError as exc:
    st.warning(f"Could not load your progress: {exc}")

st.divider()
st.markdown(
    "Use the sidebar to open **Learn**, **Composer**, **Challenges** or **Dashboard**."
)

with st.expander("Execution policy and limits"):
    try:
        info = api_client.backends()
        for backend in info["backends"]:
            status = "available" if backend["available"] else f"unavailable — {backend['reason']}"
            st.markdown(
                f"- **{backend['label']}** ({', '.join(backend['supports'])}) — {status}"
            )
        limits = info["limits"]
        st.caption(
            f"Dynamic circuits: max {limits['max_dynamic_qubits']} qubits, "
            f"max {limits['max_dynamic_shots']} shots, "
            f"while loops capped at {limits['while_cap']} iterations."
        )
    except ApiError as exc:
        st.warning(str(exc))
