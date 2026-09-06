"""Circuit composer: build, inspect, run, visualize and export."""

from __future__ import annotations

import time

import streamlit as st

from lib import api_client, auth, composer, viz
from lib.api_client import ApiError

st.title("🛠 Composer & Playground")
auth.sidebar_account()

if not auth.require_login():
    st.stop()

# --------------------------------------------------------------------------- #
# Editor: React component when built, Python grid otherwise
# --------------------------------------------------------------------------- #
try:
    from circuit_composer import build_instructions, circuit_composer, is_available

    react_available = is_available()
except Exception:  # noqa: BLE001
    react_available = False

    def build_instructions() -> str:
        return "React composer module not found; using the Python grid composer."


ir = composer.get_circuit()

if react_available:
    st.caption("Drag gates from the palette onto the grid. Drop on the target, then pick controls.")
    edited = circuit_composer(value=ir.to_dict(), n_qubits=ir.n_qubits, key="react_composer")
    if edited:
        try:
            from app.quantum.ir import CircuitIR

            composer.set_circuit(CircuitIR.from_dict(edited))
            ir = composer.get_circuit()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Composer returned an invalid circuit: {exc}")
    # NB: composer.render() opens its own expanders, and Streamlit forbids
    # nesting them -- so this section must not be wrapped in one.
    st.divider()
    st.subheader("Measurement buttons and block editing")
    composer.render("grid")
else:
    with st.expander("About the drag-and-drop component", expanded=False):
        st.info(build_instructions())
    ir = composer.render("grid")

st.divider()

# --------------------------------------------------------------------------- #
# Inspection and run controls
# --------------------------------------------------------------------------- #
ir_dict = ir.to_dict()
is_dynamic = ir.is_dynamic()

try:
    catalogue = api_client.backends()
except ApiError as exc:
    st.error(str(exc))
    st.stop()

backend_options = [b for b in catalogue["backends"] if ("dynamic" if is_dynamic else "static") in b["supports"]]
if not backend_options:
    backend_options = catalogue["backends"]

controls = st.columns([2, 1.2, 1.2, 1.4])

with controls[0]:
    labels = {b["id"]: b["label"] + ("" if b["available"] else "  (unavailable)") for b in backend_options}
    backend = st.selectbox(
        "Backend",
        [b["id"] for b in backend_options],
        format_func=lambda i: labels[i],
    )
    chosen = next(b for b in backend_options if b["id"] == backend)
    if not chosen["available"]:
        st.warning(chosen["reason"])

with controls[1]:
    max_shots = catalogue["limits"]["max_dynamic_shots"] if is_dynamic else 8192
    shots = st.number_input("Shots", 1, max_shots, min(1024, max_shots))

with controls[2]:
    st.metric("Qubits", ir.n_qubits)
    st.metric("Depth", ir.depth())

with controls[3]:
    if is_dynamic:
        st.info("**Dynamic circuit** — execution uses the Qiskit dynamic engine.")
    else:
        st.success("**Static circuit** — runnable on all backends.")

try:
    report = api_client.inspect_circuit(ir_dict, backend, int(shots))
    for error in report["errors"]:
        st.error(error)
    for warning in report["warnings"]:
        st.warning(warning)
    with st.expander("Circuit analysis"):
        st.json(report["summary"])
except ApiError as exc:
    report = {"ok": False}
    st.error(str(exc))

run_disabled = not report.get("ok") or not chosen["available"]
if st.button("▶ Run simulation", type="primary", disabled=run_disabled, use_container_width=True):
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
        st.session_state["last_job_id"] = job["id"]
    except ApiError as exc:
        st.error(str(exc))

# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
job_id = st.session_state.get("last_job_id")
if job_id:
    st.divider()
    st.subheader(f"Results — job #{job_id}")
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

        tabs = st.tabs(
            ["Histogram", "Probabilities", "Phase disk", "Bloch", "Amplitudes", "Diagram"]
        )
        with tabs[0]:
            viz.histogram(result)
        with tabs[1]:
            viz.probability_table(result)
        with tabs[2]:
            viz.phase_disk(result)
        with tabs[3]:
            viz.bloch_sphere(result, report.get("summary"))
        with tabs[4]:
            viz.amplitude_table(result)
        with tabs[5]:
            viz.circuit_diagram(ir_dict)

        st.divider()
        st.subheader("Explain these results")
        question = st.text_input(
            "Ask the tutor about this run",
            "Explain what this histogram tells me about my circuit.",
        )
        if st.button("Ask the AI tutor"):
            with st.spinner("Thinking..."):
                try:
                    response = api_client.ai_chat(question, ir=ir_dict, job_id=job_id)
                    st.markdown(response["reply"])
                    if response.get("tools_used"):
                        st.caption("Tools used: " + ", ".join(response["tools_used"]))
                except ApiError as exc:
                    st.error(str(exc))
    elif payload:
        st.info(f"Job status: {payload['status']}")

# --------------------------------------------------------------------------- #
# Code view and exports
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Code & export")

code_tabs = st.tabs(["OpenQASM 3", "Qiskit", "Cirq", "Import QASM3", "Save"])

with code_tabs[0]:
    try:
        qasm = api_client.export_qasm(ir_dict)
        st.code(qasm, language="text")
        st.download_button("Download .qasm", qasm, f"{ir.name}.qasm", "text/plain")
    except ApiError as exc:
        st.error(str(exc))

with code_tabs[1]:
    try:
        code = api_client.export_code("qiskit", ir_dict, int(shots))
        st.code(code, language="python")
        st.download_button("Download qiskit .py", code, f"{ir.name}_qiskit.py", "text/x-python")
    except ApiError as exc:
        st.error(str(exc))

with code_tabs[2]:
    try:
        code = api_client.export_code("cirq", ir_dict, int(shots))
        if is_dynamic:
            st.info(
                "Dynamic circuit: the export bundles a Cirq circuit **plus a Python driver** "
                "that implements if/else, for and while around the simulation."
            )
        st.code(code, language="python")
        st.download_button("Download cirq .py", code, f"{ir.name}_cirq.py", "text/x-python")
    except ApiError as exc:
        st.error(str(exc))

with code_tabs[3]:
    uploaded = st.file_uploader("Upload a .qasm file", type=["qasm", "txt"])
    pasted = st.text_area("...or paste OpenQASM 3 here", height=180)
    if st.button("Import"):
        source = uploaded.read().decode() if uploaded else pasted
        if not source.strip():
            st.warning("Nothing to import.")
        else:
            try:
                imported = api_client.import_qasm(source, "imported")
                from app.quantum.ir import CircuitIR

                composer.set_circuit(CircuitIR.from_dict(imported["circuit_ir"]))
                st.success("Circuit imported.")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

with code_tabs[4]:
    name = st.text_input("Circuit name", ir.name)
    if st.button("Save circuit"):
        try:
            ir.name = name
            composer.set_circuit(ir)
            api_client.save_circuit(name, ir.to_dict())
            st.success(f"Saved '{name}'.")
        except ApiError as exc:
            st.error(str(exc))

    try:
        saved = api_client.list_circuits()
        if saved:
            st.markdown("**Your saved circuits**")
            for entry in saved:
                columns = st.columns([3, 1])
                columns[0].write(
                    f"{entry['name']} — {'dynamic' if entry['is_dynamic'] else 'static'}"
                )
                if columns[1].button("Load", key=f"load_{entry['id']}"):
                    from app.quantum.ir import CircuitIR

                    composer.set_circuit(CircuitIR.from_dict(entry["circuit_ir"]))
                    st.rerun()
    except ApiError:
        pass
