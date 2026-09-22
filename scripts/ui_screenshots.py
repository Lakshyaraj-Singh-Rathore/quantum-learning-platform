"""Capture a screenshot of every page for the UI audit report.

Run this against a stack that is already up:

    docker compose up -d --build
    pip install playwright && playwright install chromium
    python scripts/ui_screenshots.py

Images land in reports/screenshots/ and are referenced by
reports/UI_AUDIT.md.

Written to run on your machine rather than in CI: the sandbox this was
developed in cannot download a browser, so the capture step is deliberately a
local one-liner instead of a hidden dependency.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

BASE = "http://localhost:8501"
EMAIL = "instructor@local.dev"
PASSWORD = "instructor123"

OUT = Path(__file__).resolve().parents[1] / "reports" / "screenshots"

#: (filename, page label in the sidebar nav, what to do before shooting)
SHOTS: list[tuple[str, str, str]] = [
    ("01_home", "Home", "Landing page and sign-in state"),
    ("02_learn", "Learn", "Lesson reader, demos and AI tutor"),
    ("03_composer", "Composer", "Circuit editor, run controls, results"),
    ("04_challenges", "Challenges", "Coding challenge list"),
    ("05_dashboard", "Dashboard", "Learner and instructor views"),
    ("06_code_lab", "Code Lab", "Editor with live diagnostics"),
    ("07_games", "Games", "Game catalogue"),
    ("08_playground", "Playground", "Interactive single-qubit demos"),
]


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1100})

        page.goto(BASE, wait_until="networkidle")
        time.sleep(3)

        # Sign in. Streamlit renders the form in the sidebar.
        try:
            page.get_by_placeholder("you@example.com").fill(EMAIL)
            page.get_by_placeholder("••••••••").fill(PASSWORD)
            page.get_by_role("button", name="Sign in").click()
            time.sleep(4)
        except Exception as exc:  # noqa: BLE001
            print(f"  (sign-in step skipped: {exc})")

        for filename, label, _description in SHOTS:
            try:
                page.get_by_role("link", name=label).first.click()
                time.sleep(4)
            except Exception:  # noqa: BLE001
                print(f"  (could not navigate to {label})")
            page.screenshot(path=str(OUT / f"{filename}.png"), full_page=True)
            print(f"  captured {filename}.png")

        # A game level, where the controls being audited live.
        try:
            page.get_by_role("button", name="Play").first.click()
            time.sleep(4)
            page.screenshot(path=str(OUT / "09_game_level.png"), full_page=True)
            print("  captured 09_game_level.png")
        except Exception:  # noqa: BLE001
            print("  (could not open a game level)")

        browser.close()

    print(f"\nScreenshots written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
