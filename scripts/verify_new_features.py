#!/usr/bin/env python3
"""Unified Master Test Suite & Verification Orchestrator for Newest Quantum Features.

Coordinates and executes:
1. BACKEND TEST SUITE:
   - Qudit Lab (Beta): Cirq density-matrix engine, dimension-aware gates, partial trace, entropy & purity.
   - Noise Lab: T1/T2 thermal decoherence, SPAM readout error, Kraus channels, parameter sweeps.
   - Smart Composer AI: Gemini RAG generation, pattern simplifier, 4-tier equivalence verifier.
   - Deep Verification: Physical constraints (T2 <= 2T1), non-Clifford invariants, API contracts.
   Total: 141 automated pytest test cases.

2. FRONTEND TYPECHECK & UI/UX RENDER TEST SUITE:
   - TypeScript compilation & strict type safety (`npm run typecheck`).
   - Server-side render & DOM structure checks (`npm run render:new-features`).
   - Qudit Lab Page & Workbench layout (Dimension buttons, Resource status, Canvas, Palette, Inspector).
   - Smart Composer AI Studio Panel (Dual-mode Generator / Simplifier, Objective selectors, Metrics diff).
   - Quantum Noise Lab View (Presets, Sliders, Comparison dashboard, Metric cards).

3. OPTIONAL REAL-BROWSER AUTOMATED E2E SUITE:
   - Playwright + Edge browser verification (`npm run test:new-features:browser`).

Usage:
    python scripts/verify_new_features.py          # Runs Backend + Frontend SSR & Types
    python scripts/verify_new_features.py --backend # Runs only Backend test suites
    python scripts/verify_new_features.py --frontend # Runs only Frontend test suites
    python scripts/verify_new_features.py --browser # Runs Real Browser verification
    python scripts/verify_new_features.py --all    # Runs full verification including browser
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend" / "web"


def banner(text: str, fill: str = "="):
    print("\n" + fill * 80)
    print(f" {text}")
    print(fill * 80)


def run_command(cmd: list[str], cwd: Path, name: str) -> tuple[bool, float, str]:
    print(f"\n--> [EXEC] {name}")
    print(f"    Command: {' '.join(cmd)}")
    print(f"    Cwd:     {cwd}")

    t0 = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=os.name == "nt",
    )
    elapsed = time.time() - t0
    success = proc.returncode == 0

    if success:
        print(f"    [OK] Passed in {elapsed:.2f}s")
    else:
        print(f"    [FAIL] Exited with code {proc.returncode} after {elapsed:.2f}s")
        print("\n--- STDOUT ---")
        print(proc.stdout[-2000:])
        if proc.stderr:
            print("--- STDERR ---")
            print(proc.stderr[-2000:])
        print("--------------")

    output = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
    return success, elapsed, output


def main():
    parser = argparse.ArgumentParser(description="Newest Features Unified Test Orchestrator")
    parser.add_argument("--backend", action="store_true", help="Run only backend tests")
    parser.add_argument("--frontend", action="store_true", help="Run only frontend tests")
    parser.add_argument("--browser", action="store_true", help="Run only real browser tests")
    parser.add_argument("--all", action="store_true", help="Run all verification suites")

    args = parser.parse_args()

    # Default to both backend and frontend if no specific flag passed
    run_all = args.all
    run_backend = args.backend or run_all or (not args.frontend and not args.browser)
    run_frontend = args.frontend or run_all or (not args.backend and not args.browser)
    run_browser = args.browser or run_all

    banner("QUANTUMLEARNAI: NEW FEATURES VERIFICATION & BUG DETECTION SUITE")
    print(f"Repo Root: {REPO_ROOT}")
    print(f"Features:  1. Qudit Lab (Beta)  |  2. Noise Lab  |  3. Smart Composer AI")
    print(f"Plan:      Backend={run_backend}, Frontend={run_frontend}, Browser={run_browser}")

    records: list[dict] = []
    overall_start = time.time()

    # --------------------------------------------------------------------------
    # 1. BACKEND TESTS
    # --------------------------------------------------------------------------
    if run_backend:
        banner("PHASE 1: IN-DEPTH BACKEND TEST EXECUTION (141 TESTS)")

        backend_script = BACKEND_DIR / "scripts" / "run_new_features_backend_tests.py"
        ok, elapsed, out = run_command(
            [sys.executable, str(backend_script)],
            cwd=BACKEND_DIR,
            name="Backend In-Depth Test Runner (Qudit, Noise, Smart Composer, Deep Invariants)",
        )
        records.append({
            "phase": "Backend Tests",
            "name": "141 Comprehensive Pytest Suites",
            "status": "PASS" if ok else "FAIL",
            "time": elapsed,
        })

    # --------------------------------------------------------------------------
    # 2. FRONTEND TESTS (TYPECHECK & UI/UX RENDER)
    # --------------------------------------------------------------------------
    if run_frontend:
        banner("PHASE 2: FRONTEND TYPE SAFETY & UI/UX COMPONENT RENDERING")

        # 2a. Typecheck
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        ok_tc, elapsed_tc, out_tc = run_command(
            [npm_cmd, "run", "typecheck"],
            cwd=FRONTEND_DIR,
            name="Frontend Strict TypeScript Typecheck",
        )
        records.append({
            "phase": "Frontend Types",
            "name": "tsc --noEmit & shared links",
            "status": "PASS" if ok_tc else "FAIL",
            "time": elapsed_tc,
        })

        # 2b. In-depth UI/UX component rendering
        ok_ui, elapsed_ui, out_ui = run_command(
            [npm_cmd, "run", "render:new-features"],
            cwd=FRONTEND_DIR,
            name="UI/UX SSR & Virtual DOM Checks for Newest Features",
        )
        records.append({
            "phase": "Frontend UI/UX",
            "name": "render-new-features.mts (Qudit Lab, Noise Lab, Smart Composer)",
            "status": "PASS" if ok_ui else "FAIL",
            "time": elapsed_ui,
        })

    # --------------------------------------------------------------------------
    # 3. REAL BROWSER E2E TESTS (OPTIONAL / LIVE STACK)
    # --------------------------------------------------------------------------
    if run_browser:
        banner("PHASE 3: AUTOMATED REAL BROWSER QA (EDGE / PLAYWRIGHT)")
        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        ok_br, elapsed_br, out_br = run_command(
            [npm_cmd, "run", "test:new-features:browser"],
            cwd=FRONTEND_DIR,
            name="Live Browser Interaction & Screenshot Capture",
        )
        records.append({
            "phase": "Browser QA",
            "name": "Playwright Edge E2E Journey",
            "status": "PASS" if ok_br else "FAIL",
            "time": elapsed_br,
        })

    # --------------------------------------------------------------------------
    # SUMMARY REPORT
    # --------------------------------------------------------------------------
    overall_elapsed = time.time() - overall_start
    banner("MASTER VERIFICATION SUMMARY")

    all_passed = all(r["status"] == "PASS" for r in records)
    print(f"{'Verification Phase':<18} | {'Test Harness':<42} | {'Status':<6} | {'Time (s)':<8}")
    print("-" * 80)
    for r in records:
        print(f"{r['phase']:<18} | {r['name']:<42} | {r['status']:<6} | {r['time']:<8.2f}")
    print("-" * 80)
    print(f"{'OVERALL':<18} | {'All Target Feature Checks':<42} | {'PASS' if all_passed else 'FAIL':<6} | {overall_elapsed:<8.2f}")

    if all_passed:
        print("\n[SUCCESS] ALL UI/UX AND BACKEND VERIFICATIONS PASSED CLEANLY!")
        return 0
    else:
        print("\n[FAILURE] One or more verification phases reported errors.")
        return 1


if __name__ == "__main__":
    code = main()
    sys.exit(code)
