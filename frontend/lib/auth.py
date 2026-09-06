"""Session-state auth helpers for the Streamlit app."""

from __future__ import annotations

import streamlit as st

from lib import api_client
from lib.api_client import ApiError


def is_logged_in() -> bool:
    return bool(st.session_state.get("token") and st.session_state.get("user"))


def current_user() -> dict | None:
    return st.session_state.get("user")


def role() -> str:
    user = current_user()
    return (user or {}).get("role", "")


def is_instructor() -> bool:
    return role() in {"instructor", "admin"}


def _store(payload: dict) -> None:
    st.session_state["token"] = payload["access_token"]
    st.session_state["user"] = {
        "id": payload["user_id"],
        "email": payload["email"],
        "role": payload["role"],
    }


def logout() -> None:
    for key in ("token", "user", "chat_history"):
        st.session_state.pop(key, None)


def login_form() -> None:
    """Render the login/register UI. Call this when the user is signed out."""
    st.subheader("Sign in to continue")
    login_tab, register_tab = st.tabs(["Log in", "Register"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            try:
                _store(api_client.login(email.strip(), password))
                st.success("Signed in.")
                st.rerun()
            except ApiError as exc:
                st.error(str(exc))

        with st.expander("Demo accounts"):
            st.markdown(
                "- **instructor@local.dev** / `instructor123` (instructor dashboard)\n"
                "- **admin@local.dev** / `admin123`\n\n"
                "Or register your own student account."
            )

    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Display name", key="reg_name")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input(
                "Password", type="password", key="reg_password", help="At least 6 characters"
            )
            submitted = st.form_submit_button("Create account", type="primary")
        if submitted:
            if len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                try:
                    _store(api_client.register(email.strip(), password, name.strip()))
                    st.success("Account created.")
                    st.rerun()
                except ApiError as exc:
                    st.error(str(exc))


def require_login() -> bool:
    """Guard a page. Returns True when the user may proceed."""
    if is_logged_in():
        return True
    st.info("Please sign in to use this page.")
    login_form()
    return False


def sidebar_account() -> None:
    """Account panel shown in the sidebar of every page."""
    with st.sidebar:
        st.markdown("### Account")
        if is_logged_in():
            user = current_user() or {}
            st.write(f"**{user.get('email')}**")
            st.caption(f"Role: {user.get('role')}")
            if st.button("Log out", use_container_width=True):
                logout()
                st.rerun()
        else:
            st.caption("Not signed in.")
