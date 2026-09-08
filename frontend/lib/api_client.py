"""HTTP client for the QuantumLearn API, with the JWT attached automatically."""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
TIMEOUT = 60.0


class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: int = 0, detail: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


def _headers(auth: bool = True) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    token = st.session_state.get("token")
    if auth and token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request(
    method: str,
    path: str,
    *,
    json: Any = None,
    auth: bool = True,
    raw: bool = False,
) -> Any:
    url = f"{API_BASE_URL}{path}"
    try:
        response = httpx.request(
            method, url, json=json, headers=_headers(auth), timeout=TIMEOUT
        )
    except httpx.TimeoutException as exc:
        # Distinguish "no answer in time" from "nothing is listening". Blaming a
        # down backend for what is usually a slow upstream (Gemini) sends people
        # to restart healthy containers.
        raise ApiError(
            f"The API did not respond within {TIMEOUT:.0f}s. The backend is "
            "probably up but the request is slow -- AI answers depend on the "
            "Gemini API, which can be slow or rate limited on a free-tier key. "
            f"Check `docker compose logs --tail=50 api`. ({type(exc).__name__})"
        ) from exc
    except httpx.RequestError as exc:
        raise ApiError(
            f"Cannot reach the API at {API_BASE_URL}. Is the backend running? ({exc})"
        ) from exc

    if response.status_code == 401:
        st.session_state.pop("token", None)
        st.session_state.pop("user", None)
        raise ApiError("Your session expired. Please log in again.", 401)

    if response.status_code >= 400:
        detail: Any
        try:
            detail = response.json().get("detail", response.text)
        except Exception:  # noqa: BLE001
            detail = response.text
        raise ApiError(_format_detail(detail), response.status_code, detail)

    if raw:
        return response.text
    if not response.content:
        return None
    return response.json()


def _format_detail(detail: Any) -> str:
    if isinstance(detail, dict) and "errors" in detail:
        return "\n".join(f"- {e}" for e in detail["errors"])
    if isinstance(detail, list):
        return "; ".join(str(d.get("msg", d)) for d in detail)
    return str(detail)


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def register(email: str, password: str, display_name: str = "") -> dict:
    return _request(
        "POST",
        "/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
        auth=False,
    )


def login(email: str, password: str) -> dict:
    return _request(
        "POST", "/auth/login", json={"email": email, "password": password}, auth=False
    )


def me() -> dict:
    return _request("GET", "/auth/me")


# --------------------------------------------------------------------------- #
# Circuits, jobs and exports
# --------------------------------------------------------------------------- #
def backends() -> dict:
    return _request("GET", "/backends", auth=False)


def inspect_circuit(ir: dict, backend: Optional[str] = None, shots: Optional[int] = None) -> dict:
    return _request(
        "POST", "/inspect", json={"circuit_ir": ir, "backend": backend, "shots": shots}
    )


def submit_job(ir: dict, backend: str, shots: int, mode: str = "auto") -> dict:
    return _request(
        "POST",
        "/jobs",
        json={"circuit_ir": ir, "backend": backend, "shots": shots, "mode": mode},
    )


def job_status(job_id: int) -> dict:
    return _request("GET", f"/jobs/{job_id}")


def job_result(job_id: int) -> dict:
    return _request("GET", f"/jobs/{job_id}/result")


def list_jobs(limit: int = 20) -> list[dict]:
    return _request("GET", f"/jobs?limit={limit}")


def export_qasm(ir: dict) -> str:
    return _request("POST", "/qasm/export", json={"circuit_ir": ir}, raw=True)


def import_qasm(qasm: str, name: str = "imported") -> dict:
    return _request("POST", "/qasm/import", json={"qasm3": qasm, "name": name})


def export_code(framework: str, ir: dict, shots: int = 1024) -> str:
    return _request(
        "POST", f"/export/{framework}", json={"circuit_ir": ir, "shots": shots}, raw=True
    )


def save_circuit(name: str, ir: dict, description: str = "") -> dict:
    return _request(
        "POST",
        "/circuits",
        json={"name": name, "circuit_ir": ir, "description": description},
    )


def list_circuits() -> list[dict]:
    return _request("GET", "/circuits")


# --------------------------------------------------------------------------- #
# Learning content and assessments
# --------------------------------------------------------------------------- #
def lessons() -> list[dict]:
    return _request("GET", "/lessons", auth=False)


def lesson(slug: str) -> dict:
    return _request("GET", f"/lessons/{slug}", auth=False)


def quizzes() -> list[dict]:
    return _request("GET", "/quizzes", auth=False)


def submit_quiz(slug: str, answers: dict[str, str]) -> dict:
    return _request("POST", f"/quizzes/{slug}/submit", json={"answers": answers})


def challenges() -> list[dict]:
    return _request("GET", "/challenges", auth=False)


def submit_challenge(slug: str, ir: dict, shots: int = 1024) -> dict:
    return _request(
        "POST", f"/challenges/{slug}/submit", json={"circuit_ir": ir, "shots": shots}
    )


def attempt(attempt_id: int) -> dict:
    return _request("GET", f"/attempts/{attempt_id}")


# --------------------------------------------------------------------------- #
# AI and dashboards
# --------------------------------------------------------------------------- #
def ai_chat(
    message: str,
    ir: Optional[dict] = None,
    job_id: Optional[int] = None,
    history: Optional[list[dict]] = None,
) -> dict:
    return _request(
        "POST",
        "/ai/chat",
        json={
            "message": message,
            "circuit_ir": ir,
            "job_id": job_id,
            "history": history or [],
        },
    )


def ai_generate_code(ir: dict, framework: str = "qiskit", shots: int = 1024) -> dict:
    return _request(
        "POST",
        "/ai/generate_code",
        json={"circuit_ir": ir, "framework": framework, "shots": shots},
    )


def my_progress() -> dict:
    return _request("GET", "/dashboard/me")


def my_recommendations() -> list[dict]:
    return _request("GET", "/dashboard/recommendations")


def instructor_overview() -> dict:
    return _request("GET", "/dashboard/instructor")


def student_list() -> list[dict]:
    return _request("GET", "/dashboard/students")
