"""Turnkey Backend Test Suite Runner for Newest Quantum Features.

Runs in-depth tests for:
1. Qudit Lab (Beta): Multi-level quantum mechanics, Kraus noise, partial traces, resource caps.
2. Noise Lab: Open quantum system models, T1/T2 decoherence, SPAM, parameter sweeps.
3. Smart Composer: AI circuit generation, pattern-rule simplification, 4-tier verification.
4. Deep Verification: Edge cases, physical laws, group invariants, and FastAPI contracts.

Usage:
    python backend/scripts/run_new_features_backend_tests.py
"""

from __future__ import annotations

import os
import sys
import time
import subprocess
from pathlib import Path

# Fix terminal encoding on Windows
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

TEST_FILES = [
    ("Qudit Lab Comprehensive", "tests/test_qudit_lab_comprehensive.py"),
    ("Noise Lab Comprehensive", "tests/test_noise_lab_comprehensive.py"),
    ("Smart Composer Comprehensive", "tests/test_smart_composer_comprehensive.py"),
    ("Deep Mathematical & API Invariants", "tests/test_new_features_deep_verification.py"),
]


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)


def run_suite():
    print_header("QUANTUM PLATFORM: NEW FEATURES IN-DEPTH BACKEND TEST SUITE")
    print(f"Working Directory: {BACKEND_DIR}")
    print(f"Python Executable: {sys.executable}")
    print(f"Target Features:   Qudit Lab (Beta), Noise Lab, Smart Composer AI Studio\n")

    total_passed = 0
    total_failed = 0
    total_time = 0.0
    results_summary = []

    for name, rel_path in TEST_FILES:
        full_path = BACKEND_DIR / rel_path
        if not full_path.exists():
            print(f"[!] Warning: Test file not found: {full_path}")
            continue

        print(f"--> Running: {name} ({rel_path})...")
        t0 = time.time()
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(full_path), "-v", "--tb=short"],
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        elapsed = time.time() - t0
        total_time += elapsed

        # Parse test outcomes
        stdout = proc.stdout
        passed = stdout.count(" PASSED")
        failed = stdout.count(" FAILED")
        errors = stdout.count(" ERROR")

        status = "PASS" if proc.returncode == 0 else "FAIL"
        if status == "PASS":
            total_passed += passed
            print(f"    [OK] {passed} tests passed in {elapsed:.2f}s")
        else:
            total_failed += (failed + errors)
            print(f"    [FAIL] {failed} failed, {errors} errors in {elapsed:.2f}s")
            print("\n" + "-" * 70)
            print(proc.stdout[-1500:])
            print("-" * 70)

        results_summary.append({
            "name": name,
            "file": rel_path,
            "status": status,
            "passed": passed,
            "failed": failed + errors,
            "time": elapsed,
        })

    print_header("BACKEND TEST SUITE EXECUTION SUMMARY")
    print(f"{'Feature Test Module':<38} | {'Status':<6} | {'Passed':<6} | {'Failed':<6} | {'Time (s)':<8}")
    print("-" * 80)
    for res in results_summary:
        print(f"{res['name']:<38} | {res['status']:<6} | {res['passed']:<6} | {res['failed']:<6} | {res['time']:<8.2f}")
    print("-" * 80)
    print(f"{'TOTAL':<38} | {'PASS' if total_failed == 0 else 'FAIL':<6} | {total_passed:<6} | {total_failed:<6} | {total_time:<8.2f}")

    if total_failed == 0:
        print("\n[SUCCESS] All backend unit, physics, and API contracts verified green!")
        return 0
    else:
        print(f"\n[FAILURE] {total_failed} backend test(s) failed. See diagnostics above.")
        return 1


if __name__ == "__main__":
    code = run_suite()
    sys.exit(code)
