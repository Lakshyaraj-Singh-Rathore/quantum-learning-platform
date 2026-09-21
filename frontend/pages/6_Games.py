"""Quantum Games: puzzle levels built on the coding-challenge pipeline."""

from __future__ import annotations

import time

import streamlit as st

# Streamlit only honours set_page_config from the script it runs, and each
# page can be opened directly. Without this the page falls back to the narrow
# default layout.
st.set_page_config(page_title="QuantumLearn", page_icon="⚛", layout="wide",
                   initial_sidebar_state="expanded")

from lib import api_client, auth, composer, viz  # noqa: E402
from lib.api_client import ApiError  # noqa: E402

# Drag-and-drop is the whole point of a game level, so prefer the React grid
# and fall back to the Python editor only if the bundle is missing.
try:
    from circuit_composer import build_is_consistent, circuit_composer, is_available

    react_available = is_available()
    _bundle_ok, _bundle_problem = build_is_consistent()
except Exception:  # noqa: BLE001
    react_available = False
    _bundle_ok, _bundle_problem = True, ""

st.title("🎮 Quantum Games")
auth.sidebar_account()

if not auth.require_login():
    st.stop()

# A stale bundle renders as a blank white iframe with no console error, so say
# what is wrong rather than leaving the player staring at it.
if react_available and not _bundle_ok:
    st.error(_bundle_problem)
    react_available = False

try:
    catalogue = api_client.games()["games"]
except ApiError as exc:
    st.error(str(exc))
    st.stop()

if not catalogue:
    st.info("No games are seeded yet.")
    st.stop()


# --------------------------------------------------------------------------- #
# Level selection
# --------------------------------------------------------------------------- #
active_slug = st.session_state.get("game_level")

if active_slug is None:
    st.caption(
        "Each level is a real circuit puzzle, graded by the same engine as the "
        "coding challenges. Pick one to start."
    )
    for game in catalogue:
        done, total = game["completed"], game["total"]
        with st.container(border=True):
            head = st.columns([6, 2])
            head[0].markdown(f"### {game['icon']} {game['title']}")
            head[0].caption(game["blurb"])
            head[1].metric("Progress", f"{done}/{total}")
            if total:
                head[1].progress(done / total)

            cols = st.columns(min(len(game["levels"]), 4))
            for index, level in enumerate(game["levels"]):
                with cols[index % len(cols)]:
                    mark = "✅" if level["passed"] else "•"
                    st.markdown(f"**{mark} Level {level['level']}**")
                    st.caption(level["title"].split(":", 1)[-1].strip())
                    if level["attempts"]:
                        st.caption(f"best {level['best_score']:.2f} · {level['attempts']} tries")
                    if st.button("Play", key=f"play_{level['slug']}", use_container_width=True):
                        st.session_state["game_level"] = level["slug"]
                        st.session_state.pop("game_attempt", None)
                        # Find the Bug hands the learner a broken circuit.
                        if level.get("starter_ir"):
                            from app.quantum.ir import CircuitIR

                            composer.set_circuit(CircuitIR.from_dict(level["starter_ir"]))
                        st.rerun()
    st.stop()


# --------------------------------------------------------------------------- #
# Playing a level
# --------------------------------------------------------------------------- #
level = None
game = None
for entry in catalogue:
    for candidate in entry["levels"]:
        if candidate["slug"] == active_slug:
            level, game = candidate, entry
if level is None:
    st.session_state.pop("game_level", None)
    st.rerun()

top = st.columns([6, 2])
top[0].markdown(f"### {game['icon']} {level['title']}")
if top[1].button("← All games", use_container_width=True):
    st.session_state.pop("game_level", None)
    st.rerun()

# The objective panel is deliberately NOT a column wrapping the composer.
# composer.render() uses st.columns internally, and Streamlit allows only one
# level of column nesting, so putting the editor inside a column crashes the
# page. Objective on top, full-width editor underneath.
with st.container(border=True):
    st.markdown("#### 🎯 Objective")
    st.write(level["prompt"])

    constraints = level.get("constraints") or {}
    rules = []
    if level.get("allowed_gates"):
        rules.append("**Allowed gates:** " + ", ".join(g.upper() for g in level["allowed_gates"]))
    if constraints.get("max_qubits"):
        rules.append(f"**Max qubits:** {constraints['max_qubits']}")
    if constraints.get("max_depth"):
        rules.append(f"**Max depth:** {constraints['max_depth']}")
    if level.get("max_edits") is not None:
        rules.append(f"**Edit budget:** {level['max_edits']}")
    if level.get("epsilon") is not None:
        rules.append(f"**Tolerance:** {level['epsilon']}")
    if level.get("n_controls"):
        rules.append(f"**Checked over all {2 ** (level['n_controls'] + 1)} basis inputs**")
    if rules:
        st.caption(" &nbsp;•&nbsp; ".join(rules), unsafe_allow_html=True)

    if level["attempts"]:
        st.caption(
            f"Your best: **{level['best_score']:.2f}** "
            f"({'passed' if level['passed'] else 'not passed yet'}) "
            f"over {level['attempts']} attempt(s)."
        )

st.markdown("#### 🛠 Build your circuit")

# Same container discipline as the Composer page: reserve the slot first so
# the React component's position in the element tree cannot shift, which would
# remount the iframe and leave it blank.
composer_slot = st.container()
ir = composer.get_circuit()

with composer_slot:
    if react_available:
        st.caption(
            "Drag a gate from the palette onto the grid, or click a gate then "
            "click a cell. For controlled gates, drop on the target first, then "
            "click the control qubits in the same column."
        )
        edited = circuit_composer(
            value=ir.to_dict(), n_qubits=ir.n_qubits, key="react_composer"
        )
        if edited:
            try:
                from app.quantum.ir import CircuitIR

                composer.set_circuit(CircuitIR.from_dict(edited))
                ir = composer.get_circuit()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Composer returned an invalid circuit: {exc}")

        # Secondary Python controls collapse into dropdowns, exactly as on the
        # Composer page, so drag-and-drop stays the primary way to play.
        ir = composer.render(
            "game", secondary=True, allowed_gates=level.get("allowed_gates")
        )
    else:
        ir = composer.render(
            "game", secondary=False, allowed_gates=level.get("allowed_gates")
        )

shots = 1024
if level.get("grader") == "shot_detective":
    shots = st.select_slider(
        "Shots — fewer scores higher, but you must stay within tolerance",
        options=[128, 256, 512, 1024, 2048, 4096],
        value=1024,
        key="game_shots",
    )

action = st.columns([2, 1, 1])
if action[0].button("▶ Run & score", type="primary", use_container_width=True):
    try:
        submission = api_client.submit_challenge(level["slug"], ir.to_dict(), shots)
        attempt_id = submission["attempt_id"]
        placeholder = st.empty()
        outcome_now = None
        for _ in range(60):
            outcome_now = api_client.attempt(attempt_id)
            if outcome_now.get("status") == "graded":
                break
            placeholder.info("Simulating and grading...")
            time.sleep(0.5)
        placeholder.empty()
        st.session_state["game_attempt"] = outcome_now
        st.rerun()
    except ApiError as exc:
        st.error(str(exc))

if action[1].button("↺ Clear circuit", use_container_width=True):
    from app.quantum.ir import CircuitIR

    composer.set_circuit(CircuitIR(name="untitled", n_qubits=2, n_clbits=2))
    st.session_state.pop("game_attempt", None)
    st.rerun()

if level.get("starter_ir") and action[2].button(
    "⟲ Reset to broken", use_container_width=True
):
    from app.quantum.ir import CircuitIR

    composer.set_circuit(CircuitIR.from_dict(level["starter_ir"]))
    st.session_state.pop("game_attempt", None)
    st.rerun()

outcome = st.session_state.get("game_attempt")
if outcome:
    st.divider()
    if outcome.get("passed"):
        st.success(f"**Level complete — score {outcome['score']:.2f}**")
        st.balloons()
    else:
        st.warning(f"**Not yet — score {outcome.get('score', 0):.2f}**")
    st.write(outcome.get("feedback", ""))

    details = outcome.get("details") or {}
    extra = details.get("game") or {}

    # Truth table: show which inputs failed.
    if "testcases_total" in extra:
        st.metric("Test cases passed", f"{extra['testcases_passed']}/{extra['testcases_total']}")
        if extra.get("failures"):
            st.markdown("**First failing inputs**")
            st.dataframe(
                [
                    {
                        "Input |c…t⟩": f["input"],
                        "Target should be": f["expected_target"],
                        "Target was": f["got_target"],
                        "Controls preserved": "yes" if f["controls_intact"] else "no",
                    }
                    for f in extra["failures"]
                ],
                hide_index=True,
                use_container_width=True,
            )

    # Shot Detective: the convergence curve is the whole lesson.
    if extra.get("curve"):
        st.markdown("**How the error shrinks with more shots**")
        st.caption(
            "Measured by subsampling one run, so this whole curve costs a "
            "single simulation."
        )
        st.line_chart(
            {"error (TVD)": [point["tvd"] for point in extra["curve"]]},
            x_label="shots",
            y_label="distance from the true distribution",
        )
        st.dataframe(
            [{"Shots": p["shots"], "Error (TVD)": p["tvd"]} for p in extra["curve"]],
            hide_index=True,
            use_container_width=True,
        )

    # Find the Bug: the edit budget.
    if extra.get("edits"):
        edits = extra["edits"]
        cols = st.columns(4)
        cols[0].metric("Edits used", edits["total"], f"budget {extra['max_edits']}")
        cols[1].metric("Modified", edits["modified"])
        cols[2].metric("Added", edits["added"])
        cols[3].metric("Removed", edits["removed"])

    if details.get("counts"):
        viz.histogram({"counts": details["counts"]})
