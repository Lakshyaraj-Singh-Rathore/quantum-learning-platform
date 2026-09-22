"""Quantum Games: puzzle levels built on the coding-challenge pipeline."""

from __future__ import annotations

import json
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


def _forget_attempt() -> None:
    """Drop a stored result and the circuit stamp that goes with it."""
    for key in ("game_attempt", "game_attempt_circuit", "game_attempt_level"):
        st.session_state.pop(key, None)


def _without_ids(value):
    """Strip op ids from a nested IR structure.

    Deliberately a local copy of the backend's helper rather than an import.
    ``app.quantum.inspect`` pulls in ``app.config``, which needs
    ``pydantic-settings`` -- a backend-only dependency that is not installed in
    the Streamlit image. Importing it here crashed the page with
    ModuleNotFoundError. The frontend may only import backend modules that are
    pure (``app.quantum.ir`` and ``app.quantum.params``).
    """
    if isinstance(value, dict):
        return {k: _without_ids(v) for k, v in value.items() if k != "id"}
    if isinstance(value, list):
        return [_without_ids(v) for v in value]
    return value


def _circuit_stamp(circuit) -> str:
    """Identity of a circuit, ignoring op ids.

    Op ids are regenerated every time the IR is rebuilt, so comparing raw
    dictionaries would report a change on every rerun and hide results that are
    still valid.
    """
    return json.dumps(_without_ids(circuit.to_dict()), sort_keys=True)

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
                        _forget_attempt()
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
        # Remember exactly what was graded. Results persist across reruns, so
        # without this a win banner stays on screen while the learner edits the
        # circuit into something wrong.
        st.session_state["game_attempt_circuit"] = _circuit_stamp(ir)
        st.session_state["game_attempt_level"] = level["slug"]
        st.rerun()
    except ApiError as exc:
        st.error(str(exc))

if action[1].button("↺ Clear circuit", use_container_width=True):
    from app.quantum.ir import CircuitIR

    composer.set_circuit(CircuitIR(name="untitled", n_qubits=2, n_clbits=2))
    _forget_attempt()
    st.rerun()

if level.get("starter_ir") and action[2].button(
    "⟲ Reset to broken", use_container_width=True
):
    from app.quantum.ir import CircuitIR

    composer.set_circuit(CircuitIR.from_dict(level["starter_ir"]))
    _forget_attempt()
    st.rerun()

outcome = st.session_state.get("game_attempt")

# A result describes the circuit that was graded, not whatever is on the grid
# now. Showing a stale "Level complete" beside an edited circuit reads as the
# game accepting a wrong answer.
if outcome is not None:
    same_level = st.session_state.get("game_attempt_level") == level["slug"]
    same_circuit = st.session_state.get("game_attempt_circuit") == _circuit_stamp(ir)
    if not (same_level and same_circuit):
        st.info(
            "You have changed the circuit since the last run. Press "
            "**Run & score** to grade what is on the grid now."
        )
        outcome = None

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

    # Truth table. Always shown, pass or fail: on a win it is the proof that
    # the logic is right, which is exactly when a learner wants to read it.
    if "testcases_total" in extra:
        summary = st.columns(3)
        summary[0].metric(
            "Test cases passed",
            f"{extra['testcases_passed']}/{extra['testcases_total']}",
        )
        if extra.get("superposed"):
            summary[1].metric("Superposed outputs", extra["superposed"])

        if extra.get("superposed"):
            st.warning(
                "Some inputs left the register in a **superposition**, so there "
                "is no single output bitstring to check. This level is about "
                "classical logic — build it from X and controlled-X gates only."
            )

        rows = extra.get("table")
        if not rows:
            # Attempts graded before the full table existed only stored failures.
            rows = extra.get("failures") or []
            if rows:
                st.caption("Showing the failing inputs from this older attempt.")

        if rows:
            st.markdown("**Truth table** — every input the grader checked")
            st.dataframe(
                [
                    {
                        "": "✅" if row.get("passed") else "❌",
                        "Input |c…t⟩": row["input"],
                        "Output": row.get("output", "—"),
                        "Target should be": row["expected_target"],
                        "Target was": row["got_target"],
                        "Controls preserved": (
                            "yes" if row["controls_intact"] else "no"
                        ),
                        "Certainty": (
                            f"{row['certainty']:.0%}" if "certainty" in row else "—"
                        ),
                    }
                    for row in rows
                ],
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "Controls are the left characters, the target is the rightmost. "
                "A correct vault flips the target only when every control is 1, "
                "and leaves the controls untouched."
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

    # Bell Builder and other state-graded levels: the histogram alone cannot
    # distinguish |Phi+> from |Phi->, so surface the fidelity that actually
    # decided the result.
    note = details.get("behaviour_note") or ""
    if "fidelity" in note.lower():
        st.caption(f"Graded on state fidelity — {note}")

    if details.get("counts"):
        st.markdown("**Measurement outcomes**")
        viz.histogram({"counts": details["counts"]})
        if "fidelity" in note.lower():
            st.caption(
                "Two different states can produce this same histogram. That is "
                "why these levels are graded on the state, not the counts."
            )
