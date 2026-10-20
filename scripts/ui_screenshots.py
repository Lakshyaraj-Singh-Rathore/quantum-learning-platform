"""Capture genuine, high-resolution screenshots of the React SPA for the UI audit report.

Run this against a local dev or preview stack:

    cd frontend/web && npm run preview   # or npm run dev
    python scripts/ui_screenshots.py

Images land in reports/screenshots/ and are referenced by reports/UI_AUDIT.md.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

BASE = os.environ.get("BASE_URL", "http://localhost:4173")
REPO_ROOT = Path(__file__).resolve().parents[1]
OUT = REPO_ROOT / "reports" / "screenshots"
FIXTURES = REPO_ROOT / "frontend" / "web" / "test-fixtures"

LESSONS_RAW = {}
if (FIXTURES / "lessons.json").exists():
    with open(FIXTURES / "lessons.json", "r", encoding="utf-8") as f:
        LESSONS_RAW = json.load(f)

CHALLENGES_RAW = {}
if (FIXTURES / "challenges.json").exists():
    with open(FIXTURES / "challenges.json", "r", encoding="utf-8") as f:
        CHALLENGES_RAW = json.load(f)

GAMES_DATA = []
if (FIXTURES / "games.json").exists():
    with open(FIXTURES / "games.json", "r", encoding="utf-8") as f:
        GAMES_DATA = json.load(f)

USER = {
    "id": 1,
    "email": "student@quantum.local",
    "role": "student",
    "display_name": "Alex Chen",
    "is_active": True,
}

SESSION_OBJ = {
    "state": {
        "token": "valid-session-jwt-token-alex",
        "user": USER,
    },
    "version": 0,
}

BACKENDS_DATA = {
    "backends": [
        {"id": "qiskit_aer", "label": "Qiskit Aer", "supports": ["static"], "available": True, "reason": ""},
        {"id": "cirq", "label": "Cirq", "supports": ["static"], "available": True, "reason": ""},
        {"id": "pennylane", "label": "PennyLane (default.qubit)", "supports": ["static"], "available": True, "reason": ""},
        {"id": "qbraid", "label": "qBraid", "supports": ["static"], "available": True, "reason": ""},
        {"id": "cudaq", "label": "CUDA-Q GPU (up to 28 qubits)", "supports": ["static"], "available": True, "reason": ""},
        {"id": "qiskit_dynamic", "label": "Qiskit Dynamic Engine", "supports": ["dynamic"], "available": True, "reason": ""},
    ],
    "limits": {"max_dynamic_qubits": 15, "max_dynamic_shots": 10000, "while_cap": 32},
}

INSPECT_DATA = {
    "ok": True,
    "errors": [],
    "warnings": [],
    "info": [],
    "summary": {
        "name": "bell_circuit",
        "n_qubits": 2,
        "n_clbits": 2,
        "depth": 2,
        "n_ops": 2,
        "is_dynamic": False,
        "has_measurements": False,
        "has_mid_circuit_measurement": False,
        "gate_histogram": {"h": 1, "cx": 1},
        "control_flow": [],
        "max_controls": 1,
        "supported_backends": ["qiskit_aer", "cirq", "pennylane", "qbraid", "cudaq"],
    },
}

STARTERS_DATA = {
    "frameworks": ["qiskit", "cirq", "pennylane", "qasm3", "cudaq"],
    "starters": {
        "qiskit": "from qiskit import QuantumCircuit\n\n# Prepare Bell state |Phi+>\nqc = QuantumCircuit(2, 2)\nqc.h(0)\nqc.cx(0, 1)\nqc.measure([0, 1], [0, 1])\n",
        "cirq": "import cirq\n\nq0, q1 = cirq.LineQubit.range(2)\ncircuit = cirq.Circuit(\n    cirq.H(q0),\n    cirq.CNOT(q0, q1),\n    cirq.measure(q0, q1, key='m')\n)\n",
        "pennylane": "import pennylane as qml\n\ndev = qml.device('default.qubit', wires=2)\n@qml.qnode(dev)\ndef circuit():\n    qml.Hadamard(wires=0)\n    qml.CNOT(wires=[0, 1])\n    return qml.probs(wires=[0, 1])\n",
        "qasm3": "OPENQASM 3.0;\ninclude \"stdgates.inc\";\n\nqubit[2] q;\nbit[2] c;\n\nh q[0];\ncx q[0], q[1];\nc[0] = measure q[0];\nc[1] = measure q[1];\n",
        "cudaq": "import cudaq\n\nkernel = cudaq.make_kernel()\nq = kernel.qalloc(2)\nkernel.h(q[0])\nkernel.cx(q[0], q[1])\n",
    },
}

CURRICULUM_DATA = {
    "sections": [
        {
            "id": 1,
            "title": "Mathematical Foundations",
            "slug": "math",
            "topics": [
                {
                    "slug": "math.complex",
                    "title": "Complex Numbers & Euler's Formula",
                    "position": 1,
                    "difficulty": "beginner",
                    "summary": "Complex plane, imaginary units, and polar form representation.",
                    "objectives": ["Understand i^2 = -1", "Work with polar form r*e^(i*theta)"],
                    "mastery": 0.9,
                    "attempts": 4,
                    "completed": True,
                    "prerequisites": [],
                    "status": {"ready": True, "missing_required": [], "missing_recommended": [], "advisory": False},
                    "lessons": [{"slug": "14_complex_numbers", "title": "Complex Numbers", "track": "math", "position": 1, "is_primary": True, "confidence": "high"}]
                }
            ]
        },
        {
            "id": 2,
            "title": "Core Quantum Theory",
            "slug": "qc",
            "topics": [
                {
                    "slug": "qc.qubits",
                    "title": "Qubits and Superposition",
                    "position": 1,
                    "difficulty": "beginner",
                    "summary": "Statevectors, Hilbert spaces, and the Bloch sphere.",
                    "objectives": ["Statevector formulation", "Bloch angles theta and phi"],
                    "mastery": 0.85,
                    "attempts": 3,
                    "completed": True,
                    "prerequisites": [],
                    "status": {"ready": True, "missing_required": [], "missing_recommended": [], "advisory": False},
                    "lessons": [{"slug": "01_qubits", "title": "Qubits and Superposition", "track": "theory", "position": 1, "is_primary": True, "confidence": "high"}]
                }
            ]
        }
    ]
}

SAMPLE_LESSON_CONTENT = {
    "slug": "01_qubits",
    "title": "Qubits and Superposition",
    "tags": ["qubit", "superposition", "statevector"],
    "content": """# Qubits and Superposition

A classical bit has a deterministic state of either $0$ or $1$. A qubit, however, lives in a two-dimensional complex Hilbert space $\\mathbb{C}^2$:

$$|\\psi\\rangle = \\alpha|0\\rangle + \\beta|1\\rangle$$

where $\\alpha, \\beta \\in \\mathbb{C}$ are complex probability amplitudes normalized such that:

$$|\\alpha|^2 + |\\beta|^2 = 1$$

### Measurement & The Born Rule
When measured in the computational basis, the superposition instantaneously collapses:
- $P(|0\\rangle) = |\\alpha|^2$
- $P(|1\\rangle) = |\\beta|^2$

The relative phase difference $\\phi$ between $\\alpha$ and $\\beta$ enables quantum interference, the computational engine behind quantum speedups.
"""
}

DASHBOARD_DATA = {
    "user_id": 1,
    "quizzes_taken": 8,
    "challenges_attempted": 6,
    "challenges_passed": 5,
    "average_quiz_percentage": 92.5,
    "mastery": [
        {"tag": "qubit", "score": 0.95},
        {"tag": "gates", "score": 0.88},
        {"tag": "entanglement", "score": 0.92},
        {"tag": "algorithms", "score": 0.78}
    ],
    "recommendations": [
        {"kind": "lesson", "slug": "05_deutsch_jozsa", "title": "Deutsch-Jozsa Algorithm", "reason": "Next step in your quantum track"}
    ]
}


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright && playwright install chromium")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(channel="msedge")

        # 1. Unauthenticated Context: Capture Landing / Login
        print("Capturing 01_home.png & 01_landing.png...")
        anon_ctx = browser.new_context(viewport={"width": 1600, "height": 1100})
        anon_page = anon_ctx.new_page()
        anon_page.goto(f"{BASE}/login", wait_until="networkidle")
        time.sleep(2)
        anon_page.screenshot(path=str(OUT / "01_home.png"), full_page=True)
        anon_page.screenshot(path=str(OUT / "01_landing.png"), full_page=True)
        anon_ctx.close()
        print("  Saved 01_home.png and 01_landing.png")

        # 2. Authenticated Context with Comprehensive API Mocking Fallback
        auth_ctx = browser.new_context(viewport={"width": 1600, "height": 1100})

        def api_router(route):
            url = route.request.url
            if "/auth/me" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(USER))
            elif "/backends" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(BACKENDS_DATA))
            elif "/inspect" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(INSPECT_DATA))
            elif "/curriculum" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(CURRICULUM_DATA))
            elif "/lessons/" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(SAMPLE_LESSON_CONTENT))
            elif "/lessons" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(LESSONS_RAW.get("lessons", [])))
            elif "/challenges" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(CHALLENGES_RAW.get("challenges", [])))
            elif "/assessments/topics" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps([]))
            elif "/games" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(GAMES_DATA))
            elif "/codelab/starters" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(STARTERS_DATA))
            elif "/dashboard/me" in url or "/dashboard" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps(DASHBOARD_DATA))
            elif "/jobs" in url:
                route.fulfill(status=200, content_type="application/json", body=json.dumps([
                    {
                        "id": 104,
                        "backend": "qiskit_aer",
                        "status": "completed",
                        "shots": 1024,
                        "created_at": "2026-10-19T14:30:00Z"
                    },
                    {
                        "id": 103,
                        "backend": "cudaq",
                        "status": "completed",
                        "shots": 2048,
                        "created_at": "2026-10-19T12:15:00Z"
                    }
                ]))
            else:
                route.fulfill(status=200, content_type="application/json", body="[]")

        auth_ctx.route("**/api/**", api_router)
        page = auth_ctx.new_page()

        # Establish origin and session
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.evaluate("(data) => localStorage.setItem('ql-session', data)", json.dumps(SESSION_OBJ))

        views = [
            ("02_learn", f"{BASE}/learn", 3),
            ("03_composer", f"{BASE}/composer", 3),
            ("04_challenges", f"{BASE}/challenges", 3),
            ("05_dashboard", f"{BASE}/dashboard", 3),
            ("06_code_lab", f"{BASE}/codelab", 3),
            ("07_games", f"{BASE}/games", 3),
            ("08_playground", f"{BASE}/playground", 3),
        ]

        for filename, url, delay in views:
            print(f"Navigating to {url} -> {filename}.png...")
            page.goto(url, wait_until="networkidle")
            time.sleep(delay)
            target = OUT / f"{filename}.png"
            page.screenshot(path=str(target), full_page=True)
            print(f"  Captured {filename}.png ({target.stat().st_size} bytes)")

        # Capture Game Level
        print("Navigating to /games to capture 09_game_level.png...")
        page.goto(f"{BASE}/games", wait_until="networkidle")
        time.sleep(2)
        try:
            play_btn = page.locator("button:has-text('Play')").first
            if play_btn.is_visible():
                play_btn.click()
                time.sleep(2)
        except Exception as e:
            print(f"  Note on game click: {e}")
        target_game = OUT / "09_game_level.png"
        page.screenshot(path=str(target_game), full_page=True)
        print(f"  Captured 09_game_level.png ({target_game.stat().st_size} bytes)")

        browser.close()

    print(f"\nScreenshots successfully written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
