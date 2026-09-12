"""Write a quantum program, run it on any backend, inspect the result.

The composer teaches circuits by dragging gates. This page teaches the same
circuits as *code* -- which is how they are actually written in practice. The
learner's program is compiled to the platform IR, so everything downstream
(execution, noise, metrics, visualisations) is shared with the composer.
"""

from __future__ import annotations

import time

import streamlit as st

from lib import api_client, auth, viz
from lib.api_client import ApiError

st.title("Code Lab")
auth.sidebar_account()

if not auth.is_logged_in():
    st.info("Sign in to write and run quantum programs.")
    auth.login_form()
    st.stop()

st.caption(
    "Write a program that builds a circuit, then run it on any backend. "
    "Assign your finished circuit to a variable named **`circuit`**."
)

try:
    starters = api_client.codelab_starters()
except ApiError as exc:
    st.error(str(exc))
    st.stop()

frameworks = starters["frameworks"]

# --------------------------------------------------------------------------- #
# Editor
# --------------------------------------------------------------------------- #
framework = st.selectbox(
    "Language",
    frameworks,
    format_func=lambda f: {
        "qiskit": "Qiskit",
        "cirq": "Cirq",
        "pennylane": "PennyLane",
        "qasm3": "OpenQASM 3",
    }.get(f, f),
)

# Reset the editor when the learner switches language, otherwise they are
# staring at Qiskit code under a Cirq heading.
if st.session_state.get("codelab_framework") != framework:
    st.session_state["codelab_framework"] = framework
    st.session_state["codelab_code"] = starters["starters"][framework]
    # The previously built circuit came from the old language's code, so
    # leaving it on screen shows results that no longer match the editor.
    st.session_state.pop("codelab_built", None)

code = st.text_area(
    "Your program",
    value=st.session_state.get("codelab_code", starters["starters"][framework]),
    height=320,
    key="codelab_code",
)

action = st.columns([1, 1, 3])
build_clicked = action[0].button("Build circuit", use_container_width=True)
if action[1].button("Reset to example", use_container_width=True):
    st.session_state["codelab_code"] = starters["starters"][framework]
    st.rerun()

with st.expander("What am I allowed to write?"):
    st.markdown(
        """
Your code runs in a **sandbox**: a separate process with a time limit and no
access to files, the network, or other programs. You can import `qiskit`,
`cirq`, `pennylane`, `numpy`, `math` and other maths libraries.

**The one rule:** assign your circuit to a variable named `circuit`.

- **Qiskit** - a `QuantumCircuit`
- **Cirq** - a `cirq.Circuit`
- **PennyLane** - a `QNode` (the decorated function)
- **OpenQASM 3** - no Python at all: write QASM directly and it is parsed
  as-is (this is the platform's native format)

Beyond the quantum SDKs you can import `qiskit_aer`, `matplotlib`, `pandas`,
`networkx`, `scipy`, `sympy` and the pure-computation parts of the standard
library (`time`, `itertools`, `heapq`, `textwrap`, ...). Anything that
reaches the filesystem, network or other processes stays blocked.

Angles must be concrete numbers: bind a Qiskit `Parameter` with
`qc.assign_parameters({theta: 3.14159 / 2})` before returning the circuit.

Your program's `print()` output is shown back to you, so you can debug.
Circuits are converted to OpenQASM 3 internally, so a gate outside the
supported set will be reported rather than silently dropped.
        """
    )

if build_clicked:
    try:
        built = api_client.codelab_build(code, framework)
        st.session_state["codelab_built"] = built
        st.session_state.pop("codelab_job_id", None)
    except ApiError as exc:
        st.session_state.pop("codelab_built", None)
        st.error(str(exc))

built = st.session_state.get("codelab_built")

# --------------------------------------------------------------------------- #
# Built circuit + run controls
# --------------------------------------------------------------------------- #
if built:
    st.success("Circuit built.")

    if built.get("stdout"):
        with st.expander("Your program's output", expanded=True):
            st.code(built["stdout"], language="text")

    info = st.columns(3)
    info[0].metric("Qubits", built["n_qubits"])
    info[1].metric("Depth", built["depth"])
    info[2].metric("Type", "Dynamic" if built["is_dynamic"] else "Static")

    ir_dict = built["circuit_ir"]

    view = st.tabs(["Diagram", "OpenQASM 3"])
    with view[0]:
        viz.circuit_diagram(ir_dict)
    with view[1]:
        st.code(built["qasm3"], language="text")

    st.divider()
    st.subheader("Run it")

    try:
        catalogue = api_client.backends()
    except ApiError as exc:
        st.error(str(exc))
        st.stop()

    kind = "dynamic" if built["is_dynamic"] else "static"
    options = [b for b in catalogue["backends"] if kind in b["supports"]]
    if not options:
        options = catalogue["backends"]

    controls = st.columns(2)
    with controls[0]:
        labels = {
            b["id"]: b["label"] + ("" if b["available"] else "  (unavailable)")
            for b in options
        }
        backend = st.selectbox(
            "Backend", [b["id"] for b in options], format_func=lambda i: labels[i]
        )
    with controls[1]:
        max_shots = (
            catalogue["limits"]["max_dynamic_shots"] if built["is_dynamic"] else 8192
        )
        shots = st.select_slider(
            "Shots",
            options=[s for s in (128, 256, 512, 1024, 2048, 4096, 8192) if s <= max_shots],
            value=min(1024, max_shots),
        )

    chosen = next(b for b in options if b["id"] == backend)
    if not chosen["available"]:
        st.warning(chosen["reason"])

    if st.button(
        "Run simulation",
        type="primary",
        disabled=not chosen["available"],
        use_container_width=True,
    ):
        try:
            job = api_client.submit_job(ir_dict, backend, int(shots))
            placeholder = st.empty()
            for _ in range(120):
                status = api_client.job_status(job["id"])
                if status["status"] in {"completed", "failed"}:
                    break
                placeholder.info(f"Job {job['id']}: {status['status']}...")
                time.sleep(0.5)
            placeholder.empty()
            st.session_state["codelab_job_id"] = job["id"]
        except ApiError as exc:
            st.error(str(exc))

# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
job_id = st.session_state.get("codelab_job_id")
if job_id:
    st.divider()
    st.subheader(f"Results - job #{job_id}")
    try:
        payload = api_client.job_result(job_id)
    except ApiError as exc:
        st.error(str(exc))
        payload = None

    if payload and payload["status"] == "failed":
        st.error(payload.get("error") or "Simulation failed.")
    elif payload and payload.get("result"):
        result = payload["result"]
        viz.backend_badge(result)
        viz.metric_meters(result)

        tabs = st.tabs(
            ["Histogram", "Probabilities", "Phase table", "Q-sphere", "Bloch"]
        )
        with tabs[0]:
            viz.histogram(result)
        with tabs[1]:
            viz.probability_table(result)
        with tabs[2]:
            viz.phase_table(result)
        with tabs[3]:
            viz.qsphere(result)
        with tabs[4]:
            viz.bloch_sphere(result)
    else:
        st.info("No result yet.")
