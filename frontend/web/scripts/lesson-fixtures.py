"""Capture real curriculum data from a running API into test-fixtures/lessons.json.

The Learn render harness renders the real page against this fixture, so it has
to be real: the lessons are LaTeX- and table-heavy, and a hand-written sample
would not catch a reader that silently drops either.

    API_TARGET=http://localhost:8000 python3 scripts/lesson-fixtures.py
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import httpx

BASE = os.environ.get("API_TARGET", "http://localhost:8000")
OUT = pathlib.Path(__file__).resolve().parents[1] / "test-fixtures" / "lessons.json"

# One lesson with display maths, one with tables, one with dynamic-circuit code.
BODIES = ["01_qubits", "02_gates", "04_measurement"]


def main() -> int:
    email = "fixture-capture@example.com"
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        response = client.post(
            "/auth/register", json={"email": email, "password": "pw123456"}
        )
        if response.status_code != 201:
            response = client.post(
                "/auth/login", json={"email": email, "password": "pw123456"}
            )
        response.raise_for_status()
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

        lessons = client.get("/lessons", headers=headers).json()
        bodies = {}
        for slug in BODIES:
            got = client.get(f"/lessons/{slug}", headers=headers)
            if got.status_code != 200:
                print(f"skip {slug}: HTTP {got.status_code}", file=sys.stderr)
                continue
            detail = got.json()
            bodies[slug] = {
                "slug": detail["slug"],
                "title": detail["title"],
                "tags": detail["tags"],
                "content": detail["content"],
            }

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"lessons": lessons, "bodies": bodies}, indent=2) + "\n")
    print(f"wrote {OUT} ({len(lessons)} lessons, {len(bodies)} bodies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
