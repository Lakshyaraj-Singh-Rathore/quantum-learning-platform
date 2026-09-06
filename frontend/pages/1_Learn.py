"""Lesson browser with an AI tutor grounded in the curriculum."""

from __future__ import annotations

import streamlit as st

from lib import api_client, auth
from lib.api_client import ApiError

st.title("📘 Learn")
auth.sidebar_account()

try:
    lessons = api_client.lessons()
except ApiError as exc:
    st.error(str(exc))
    st.stop()

if not lessons:
    st.warning(
        "No lessons are loaded yet. The API ingests `/content/*.md` on startup — "
        "check that the content folder is mounted."
    )
    st.stop()

titles = [lesson["title"] for lesson in lessons]
selected = st.sidebar.radio("Lessons", range(len(lessons)), format_func=lambda i: titles[i])
chosen = lessons[selected]

try:
    detail = api_client.lesson(chosen["slug"])
except ApiError as exc:
    st.error(str(exc))
    st.stop()

if detail.get("tags"):
    st.caption("Concepts: " + ", ".join(f"`{tag}`" for tag in detail["tags"]))

st.markdown(detail["content"])

st.divider()
st.subheader("Ask the AI tutor")

if not auth.is_logged_in():
    st.info("Sign in to ask questions about this lesson.")
    auth.login_form()
    st.stop()

history_key = f"chat_{chosen['slug']}"
st.session_state.setdefault(history_key, [])

for turn in st.session_state[history_key]:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])

question = st.chat_input(f"Ask about {chosen['title']}...")
if question:
    st.session_state[history_key].append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = api_client.ai_chat(
                    question, history=st.session_state[history_key][:-1][-6:]
                )
                st.markdown(response["reply"])
                if response.get("citations"):
                    with st.expander("Sources from the curriculum"):
                        for citation in response["citations"]:
                            st.caption(f"**{citation['lesson_slug']}**")
                            st.text(citation["text"][:400] + "...")
                st.session_state[history_key].append(
                    {"role": "assistant", "content": response["reply"]}
                )
            except ApiError as exc:
                st.error(str(exc))
