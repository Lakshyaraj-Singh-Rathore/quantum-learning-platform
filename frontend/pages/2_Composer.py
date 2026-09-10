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

# Beginner-friendly default: sensible backend + 1024 shots, everything else
# tucked away. A student running their first Bell state should not have to read
# six settings before pressing Run.
default_backend = "qiskit_aer" if not is_dynamic else "qiskit_dynamic"
available_ids = [b["id"] for b in backend_options]
if default_backend not in available_ids:
    default_backend = available_ids[0]

summary = st.columns([1, 1, 2])
summary[0].metric("Qubits", ir.n_qubits)
summary[1].metric("Depth", ir.depth())
with summary[2]:
    if is_dynamic:
        st.info("**Dynamic circuit** - runs on the Qiskit dynamic engine.")
    else:
        st.success("**Static circuit** - runnable on all backends.")

with st.expander("Run settings", expanded=False):
    setting_cols = st.columns(2)
    with setting_cols[0]:
        labels = {
            b["id"]: b["label"] + ("" if b["available"] else "  (unavailable)")
            for b in backend_options
        }
        backend = st.selectbox(
            "Backend",
            available_ids,
            index=available_ids.index(default_backend),
            format_func=lambda i: labels[i],
        )
    with setting_cols[1]:
        max_shots = (
            catalogue["limits"]["max_dynamic_shots"] if is_dynamic else 8192
        )
        shots = st.select_slider(
            "Shots",
            options=[s for s in (128, 256, 512, 1024, 2048, 4096, 8192) if s <= max_shots],
            value=min(1024, max_shots),
            help="More shots means less sampling noise, and a slower run.",
        )

chosen = next(b for b in backend_options if b["id"] == backend)
if not chosen["available"]:
    st.warning(chosen["reason"])

noise_payload = None
with st.expander("Noise model (T1 / T2 / readout)", expanded=False):
    if backend != "qiskit_aer":
        st.info(
            "The noise model runs on **Qiskit Aer** only. Select Qiskit Aer above "
            "to enable it."
        )
    else:
        st.caption(
            "These are **teaching parameters you choose**, not calibration data "
            "from any real quantum computer. They reproduce the *kind* of errors "
            "hardware shows: energy loss (T1), dephasing (T2) and misread bits."
        )
        noise_on = st.toggle("Enable noise", value=False, key="noise_on")
        ncols = st.columns(3)
        with ncols[0]:
            t1 = st.slider("T1 relaxation (us)", 1.0, 200.0, 50.0, key="noise_t1")
        with ncols[1]:
            t2 = st.slider("T2 dephasing (us)", 1.0, 200.0, 30.0, key="noise_t2")
        with ncols[2]:
            readout = st.slider("Readout error (%)", 0.0, 20.0, 2.0, key="noise_ro")
        gcols = st.columns(3)
        with gcols[0]:
            g1 = st.slider("1-qubit pulse (us)", 0.02, 2.0, 0.10, 0.02, key="noise_g1")
        with gcols[1]:
            g2 = st.slider("2-qubit pulse (us)", 0.05, 4.0, 0.40, 0.05, key="noise_g2")
        with gcols[2]:
            g3 = st.slider("3-qubit pulse (us)", 0.10, 6.0, 1.00, 0.10, key="noise_g3")
        if t2 > 2 * t1:
            st.warning(
                f"T2 cannot exceed 2xT1; it will be clamped to {2 * t1:.1f} us."
            )
        st.caption(
            "Longer pulses mean more decoherence per gate. Z / S / T / RZ are "
            "virtual (frame changes in software), so they pick up no thermal error."
        )
        if noise_on:
            noise_payload = {
                "enabled": True,
                "t1_us": float(t1),
                "t2_us": float(t2),
                "readout_error": float(readout) / 100.0,
                "gate_time_1q_us": float(g1),
                "gate_time_2q_us": float(g2),
                "gate_time_3q_us": float(g3),
            }

try:
    report = api_client.inspect_circuit(ir_dict, backend, int(shots))
    for error in report["errors"]:
        st.error(error)
    for warning in report["warnings"]:
        st.warning(warning)
    with st.expander("Circuit analysis", expanded=False):
        st.json(report["summary"])
except ApiError as exc:
    report = {"ok": False}
    st.error(str(exc))

with st.expander("Timeline - step through the circuit", expanded=False):
    if st.button("Build timeline", key="build_timeline"):
        try:
            st.session_state["timeline"] = api_client.circuit_timeline(ir_dict)
        except ApiError as exc:
            st.error(str(exc))

    timeline = st.session_state.get("timeline")
    if not timeline:
        st.caption(
            "Walk the circuit gate by gate and watch the state evolve. "
            "Press **Build timeline** after editing the circuit."
        )
    elif not timeline.get("supported"):
        st.info(timeline.get("reason", "Timeline unavailable."))
    else:
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
            head[3].metric(
                "Entanglement S", f"{entry['entanglement_entropy']:.3f}"
            )

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
                st.success(
                    "These qubits are **entangled** at this step." + extra
                )

run_disabled = not report.get("ok") or not chosen["available"]
if st.button("▶ Run simulation", type="primary", disabled=run_disabled, use_container_width=True):
    try:
        job = api_client.submit_job(ir_dict, backend, int(shots), noise=noise_payload)
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

        viz.metric_meters(result)

        tabs = st.tabs(
            [
                "Histogram",
                "Ideal vs noisy",
                "Born vs shots",
                "Probabilities",
                "Phase table",
                "Phase disk",
                "Q-sphere",
                "Density matrix",
                "Bloch",
                "Diagram",
            ]
        )
        with tabs[0]:
            opts = st.columns(2)
            with opts[0]:
                as_probability = st.checkbox(
                    "Show probability instead of counts",
                    value=False,
                    key="hist_prob",
                )
            with opts[1]:
                color_by_phase = st.checkbox(
                    "Colour bars by relative phase",
                    value=False,
                    help=(
                        "Z, S, T and RZ change the phase without moving any "
                        "counts, so the bars stay the same height and only the "
                        "colour changes."
                    ),
                    key="hist_phase",
                )
            viz.histogram(
                result,
                color_by_phase=color_by_phase,
                as_probability=as_probability,
            )
        with tabs[1]:
            viz.ideal_vs_noisy(result)
        with tabs[2]:
            viz.born_vs_shots(result)
        with tabs[3]:
            viz.probability_table(result)
        with tabs[4]:
            viz.phase_table(result)
        with tabs[5]:
            viz.phase_disk(result)
        with tabs[6]:
            viz.qsphere(result)
        with tabs[7]:
            viz.density_matrix(result)
        with tabs[8]:
            viz.bloch_sphere(result, report.get("summary"))
        with tabs[9]:
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
