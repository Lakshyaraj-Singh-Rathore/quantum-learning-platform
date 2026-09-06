"""Quizzes and autograded coding challenges."""

from __future__ import annotations

import time

import streamlit as st

from lib import api_client, auth, composer, viz
from lib.api_client import ApiError

st.title("🧩 Challenges")
auth.sidebar_account()

if not auth.require_login():
    st.stop()

quiz_tab, coding_tab = st.tabs(["Quizzes", "Coding challenges"])

# --------------------------------------------------------------------------- #
# Quizzes
# --------------------------------------------------------------------------- #
with quiz_tab:
    try:
        quizzes = api_client.quizzes()
    except ApiError as exc:
        st.error(str(exc))
        quizzes = []

    if not quizzes:
        st.info("No quizzes available.")
    else:
        titles = [q["title"] for q in quizzes]
        index = st.selectbox("Quiz", range(len(quizzes)), format_func=lambda i: titles[i])
        quiz = quizzes[index]
        if quiz.get("tags"):
            st.caption("Concepts: " + ", ".join(f"`{t}`" for t in quiz["tags"]))

        with st.form(f"quiz_{quiz['slug']}"):
            answers: dict[str, str] = {}
            for number, question in enumerate(quiz["questions"], start=1):
                st.markdown(f"**{number}. {question['prompt']}**")
                key = f"q_{quiz['slug']}_{question['id']}"
                if question["qtype"] == "mcq" and question.get("options"):
                    answers[str(question["id"])] = st.radio(
                        "Choose one",
                        question["options"],
                        key=key,
                        label_visibility="collapsed",
                        index=None,
                    ) or ""
                else:
                    answers[str(question["id"])] = st.text_input(
                        "Your answer", key=key, label_visibility="collapsed"
                    )
                st.write("")
            submitted = st.form_submit_button("Submit answers", type="primary")

        if submitted:
            try:
                result = api_client.submit_quiz(quiz["slug"], answers)
                percentage = result["percentage"]
                if percentage >= 80:
                    st.success(f"Score: {result['score']}/{result['max_score']} ({percentage}%)")
                elif percentage >= 50:
                    st.warning(f"Score: {result['score']}/{result['max_score']} ({percentage}%)")
                else:
                    st.error(f"Score: {result['score']}/{result['max_score']} ({percentage}%)")

                for item in result["feedback"]:
                    icon = "✅" if item["correct"] else "❌"
                    with st.expander(f"{icon} {item['prompt']}"):
                        st.write(f"Your answer: `{item['your_answer'] or '(blank)'}`")
                        if not item["correct"]:
                            st.write(f"Correct answer: `{item['correct_answer']}`")
                        if item.get("explanation"):
                            st.info(item["explanation"])
            except ApiError as exc:
                st.error(str(exc))

# --------------------------------------------------------------------------- #
# Coding challenges
# --------------------------------------------------------------------------- #
with coding_tab:
    try:
        challenges = api_client.challenges()
    except ApiError as exc:
        st.error(str(exc))
        challenges = []

    if not challenges:
        st.info("No coding challenges available.")
    else:
        titles = [c["title"] for c in challenges]
        index = st.selectbox(
            "Challenge", range(len(challenges)), format_func=lambda i: titles[i]
        )
        challenge = challenges[index]

        st.markdown(f"### {challenge['title']}")
        st.markdown(challenge["prompt"])

        columns = st.columns(3)
        columns[0].caption("Allowed gates: " + ", ".join(f"`{g}`" for g in challenge["allowed_gates"]))
        constraints = challenge.get("constraints") or {}
        if constraints:
            columns[1].caption(
                "Constraints: "
                + ", ".join(f"{k}={v}" for k, v in constraints.items())
            )
        if challenge["is_dynamic"]:
            columns[2].info("Requires runtime control flow")

        st.divider()
        st.markdown(
            "Build your solution in the **Composer** page, then submit it here. "
            "Your current circuit is shown below."
        )

        ir = composer.get_circuit()
        viz.circuit_diagram(ir.to_dict())
        st.caption(
            f"Current circuit: {ir.n_qubits} qubits, depth {ir.depth()}, "
            f"{'dynamic' if ir.is_dynamic() else 'static'}"
        )

        if st.button("Submit this circuit", type="primary"):
            try:
                submission = api_client.submit_challenge(challenge["slug"], ir.to_dict())
                attempt_id = submission["attempt_id"]
                placeholder = st.empty()
                outcome = None
                for _ in range(120):
                    outcome = api_client.attempt(attempt_id)
                    if outcome["status"] == "graded":
                        break
                    placeholder.info(f"Grading... ({outcome['status']})")
                    time.sleep(0.5)
                placeholder.empty()

                if outcome and outcome["status"] == "graded":
                    if outcome["passed"]:
                        st.success(outcome["feedback"])
                        st.balloons()
                    else:
                        st.error(outcome["feedback"])
                    st.progress(min(1.0, float(outcome["score"])), text=f"Score {outcome['score']:.2f}")

                    details = outcome.get("details") or {}
                    if details.get("counts"):
                        viz.histogram({"counts": details["counts"]})
                    with st.expander("Grading details"):
                        st.json(details)
                else:
                    st.warning("Grading is taking longer than expected; check back shortly.")
            except ApiError as exc:
                st.error(str(exc))
