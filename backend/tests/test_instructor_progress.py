"""Instructor visibility into learner progress.

The instructor dashboard used to hide almost everyone: /dashboard/students
filtered on ``role == "student"``, so a cohort of instructors/admins trying the
platform rendered as "No students registered yet". There was also no way to
open a single learner and see what they were struggling with.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="module")
def instructor_headers(client):
    response = client.post(
        "/auth/login",
        json={"email": "instructor@local.dev", "password": "instructor123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _take_a_quiz(client, headers):
    quizzes = client.get("/quizzes", headers=headers).json()
    quiz = quizzes[0]
    answers = {
        str(q["id"]): (q.get("options") or ["anything"])[0] for q in quiz["questions"]
    }
    result = client.post(
        f"/quizzes/{quiz['slug']}/submit", json={"answers": answers}, headers=headers
    )
    assert result.status_code == 200, result.text


def test_student_list_includes_non_student_roles(client, instructor_headers):
    """Instructors and admins are learners too; they must not be filtered out."""
    rows = client.get("/dashboard/students", headers=instructor_headers).json()
    roles = {row["role"] for row in rows}
    assert "instructor" in roles or "admin" in roles
    assert len(rows) >= 2


def test_student_list_reports_quiz_activity(client, student_headers, instructor_headers):
    _take_a_quiz(client, student_headers)
    me = client.get("/auth/me", headers=student_headers).json()

    rows = client.get("/dashboard/students", headers=instructor_headers).json()
    row = next(r for r in rows if r["id"] == me["id"])
    assert row["quizzes_taken"] >= 1
    # Columns the dashboard renders.
    for field in (
        "email",
        "role",
        "challenges_attempted",
        "challenges_passed",
        "average_quiz_percentage",
        "simulations_run",
    ):
        assert field in row


def test_student_list_sorted_by_activity(client, instructor_headers):
    rows = client.get("/dashboard/students", headers=instructor_headers).json()
    activity = [
        r["quizzes_taken"] + r["challenges_attempted"] + r["simulations_run"]
        for r in rows
    ]
    assert activity == sorted(activity, reverse=True)


def test_instructor_can_drill_into_one_learner(client, student_headers, instructor_headers):
    _take_a_quiz(client, student_headers)
    me = client.get("/auth/me", headers=student_headers).json()

    detail = client.get(
        f"/dashboard/students/{me['id']}", headers=instructor_headers
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["quizzes_taken"] >= 1
    assert "mastery" in body and "recommendations" in body


def test_drill_down_matches_what_the_learner_sees(client, student_headers, instructor_headers):
    me = client.get("/auth/me", headers=student_headers).json()
    own = client.get("/dashboard/me", headers=student_headers).json()
    seen = client.get(
        f"/dashboard/students/{me['id']}", headers=instructor_headers
    ).json()
    assert own["quizzes_taken"] == seen["quizzes_taken"]
    assert own["average_quiz_percentage"] == seen["average_quiz_percentage"]


def test_students_cannot_read_the_roster(client, student_headers):
    assert client.get("/dashboard/students", headers=student_headers).status_code == 403


def test_students_cannot_drill_into_peers(client, student_headers):
    assert (
        client.get("/dashboard/students/1", headers=student_headers).status_code == 403
    )


def test_unknown_learner_is_404_not_500(client, instructor_headers):
    response = client.get("/dashboard/students/999999", headers=instructor_headers)
    assert response.status_code == 404
