"""Learner progress and the role-gated instructor dashboard."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import api_client, auth
from lib.api_client import ApiError

st.title("📊 Dashboard")
auth.sidebar_account()

if not auth.require_login():
    st.stop()

tabs = ["My progress"]
if auth.is_instructor():
    tabs.append("Instructor")
selected = st.tabs(tabs)

# --------------------------------------------------------------------------- #
# Learner
# --------------------------------------------------------------------------- #
with selected[0]:
    try:
        progress = api_client.my_progress()
    except ApiError as exc:
        st.error(str(exc))
        st.stop()

    columns = st.columns(4)
    columns[0].metric("Quizzes taken", progress["quizzes_taken"])
    columns[1].metric("Challenges attempted", progress["challenges_attempted"])
    columns[2].metric("Challenges passed", progress["challenges_passed"])
    columns[3].metric("Average quiz score", f"{progress['average_quiz_percentage']}%")

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Concept mastery")
        mastery = progress.get("mastery") or []
        if mastery:
            frame = pd.DataFrame(mastery)
            st.bar_chart(frame.set_index("tag")["score"], height=280)
            st.dataframe(frame, use_container_width=True, hide_index=True)
        else:
            st.info("Take a quiz or submit a challenge to start tracking mastery.")

    with right:
        st.subheader("Recommended next")
        for item in progress.get("recommendations") or []:
            icon = "📘" if item["kind"] == "lesson" else "🧩"
            st.markdown(f"{icon} **{item.get('title', item['slug'])}**")
            st.caption(item["reason"])
        if not progress.get("recommendations"):
            st.info("No recommendations yet.")

    st.divider()
    st.subheader("Recent simulations")
    try:
        jobs = api_client.list_jobs(15)
        if jobs:
            st.dataframe(pd.DataFrame(jobs), use_container_width=True, hide_index=True)
        else:
            st.info("No simulations yet.")
    except ApiError as exc:
        st.warning(str(exc))

# --------------------------------------------------------------------------- #
# Instructor
# --------------------------------------------------------------------------- #
if auth.is_instructor():
    with selected[1]:
        try:
            overview = api_client.instructor_overview()
        except ApiError as exc:
            st.error(str(exc))
            st.stop()

        columns = st.columns(2)
        columns[0].metric("Students", overview["total_students"])
        columns[1].metric("Simulation jobs", overview["total_jobs"])

        st.divider()
        st.subheader("Quiz completion")
        if overview["quiz_completion"]:
            st.dataframe(
                pd.DataFrame(overview["quiz_completion"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No quiz attempts yet.")

        st.subheader("Challenge completion")
        if overview["challenge_completion"]:
            st.dataframe(
                pd.DataFrame(overview["challenge_completion"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No challenge attempts yet.")

        left, right = st.columns(2)
        with left:
            st.subheader("Common errors")
            if overview["common_errors"]:
                st.dataframe(
                    pd.DataFrame(overview["common_errors"]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No errors recorded.")
        with right:
            st.subheader("Weakest concepts (cohort)")
            if overview["weakest_tags"]:
                frame = pd.DataFrame(overview["weakest_tags"])
                st.bar_chart(frame.set_index("tag")["average_score"], height=260)
            else:
                st.info("Not enough data yet.")

        st.subheader("Leaderboard")
        if overview["leaderboard"]:
            st.dataframe(
                pd.DataFrame(overview["leaderboard"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No completed challenges yet.")

        st.divider()
        st.subheader("Students")
        try:
            students = api_client.student_list()
            if students:
                st.dataframe(
                    pd.DataFrame(students), use_container_width=True, hide_index=True
                )
            else:
                st.info("No students registered yet.")
        except ApiError as exc:
            st.warning(str(exc))
