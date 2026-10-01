"""Capture real Challenges/Dashboard data into test-fixtures/challenges.json.

    API_TARGET=http://localhost:8000 python3 scripts/challenge-fixtures.py

Read-only: it lists quizzes, challenges, learner progress and the instructor
overview. It does NOT submit a quiz or a challenge, so it is safe to point at a
real deployment -- the fixture simply records whatever that database holds, and
the render harness asserts against the values it finds.

It needs BOTH a learner and an instructor login, since /dashboard/instructor is
role-gated. The bootstrap accounts in .env.example work out of the box.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import httpx

BASE = os.environ.get("API_TARGET", "http://localhost:8000")
OUT = pathlib.Path(__file__).resolve().parents[1] / "test-fixtures" / "challenges.json"

STUDENT = os.environ.get("FIXTURE_STUDENT", "fixture-student@example.com")
INSTRUCTOR = os.environ.get("FIXTURE_INSTRUCTOR", "instructor@local.dev")
INSTRUCTOR_PW = os.environ.get("FIXTURE_INSTRUCTOR_PASSWORD", "instructor123")
PASSWORD = os.environ.get("FIXTURE_PASSWORD", "pw123456")


def token(client: httpx.Client, email: str, password: str) -> str:
    response = client.post("/auth/register", json={"email": email, "password": password})
    if response.status_code != 201:
        response = client.post("/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    return response.json()["access_token"]


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        learner = {"Authorization": f"Bearer {token(client, STUDENT, PASSWORD)}"}
        try:
            staff = {"Authorization": f"Bearer {token(client, INSTRUCTOR, INSTRUCTOR_PW)}"}
        except httpx.HTTPStatusError as exc:
            print(f"instructor login failed: {exc}", file=sys.stderr)
            staff = None

        data = {
            "quizzes": client.get("/quizzes", headers=learner).json(),
            "challenges": client.get("/challenges", headers=learner).json(),
            "progress": client.get("/dashboard/me", headers=learner).json(),
            "quiz_result": None,
        }
        if staff is not None:
            data["overview"] = client.get("/dashboard/instructor", headers=staff).json()
            students = client.get("/dashboard/students", headers=staff).json()
            data["students"] = students
            data["student_detail"] = (
                client.get(f"/dashboard/students/{students[0]['id']}", headers=staff).json()
                if students
                else None
            )
        else:
            data["overview"] = None
            data["students"] = []
            data["student_detail"] = None

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {OUT} ({len(data['quizzes'])} quizzes, {len(data['challenges'])} challenges)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
