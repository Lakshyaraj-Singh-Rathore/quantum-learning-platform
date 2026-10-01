"""Capture the game catalogue into test-fixtures/games.json.

    API_TARGET=http://localhost:8000 python3 scripts/game-fixtures.py

Read-only. It records whatever the database holds, including the signed-in
learner's per-level progress.
"""
from __future__ import annotations

import json
import os
import pathlib

import httpx

BASE = os.environ.get("API_TARGET", "http://localhost:8000")
OUT = pathlib.Path(__file__).resolve().parents[1] / "test-fixtures" / "games.json"
EMAIL = os.environ.get("FIXTURE_STUDENT", "p6@example.com")
PASSWORD = os.environ.get("FIXTURE_PASSWORD", "pw123456")


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        response = client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
        if response.status_code != 201:
            response = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
        response.raise_for_status()
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
        data = client.get("/games", headers=headers).json()

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    levels = sum(len(game["levels"]) for game in data["games"])
    print(f"wrote {OUT} ({len(data['games'])} games, {levels} levels)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
