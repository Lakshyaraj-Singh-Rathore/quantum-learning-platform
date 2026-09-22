"""Coding-challenge autograder.

Grading has two independent halves:
  1. deterministic constraint checks (allowed gates, depth, required gates)
  2. behavioural comparison of the simulation result against the target
     (counts distribution via total variation distance, or state fidelity)
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.models.assessment import AutogradeResult, ChallengeAttempt, CodingChallenge
from app.quantum.inspect import check_challenge_constraints, summarize_circuit
from app.quantum.ir import CircuitIR
from app.services import game_graders

PASS_THRESHOLD = 0.8

#: Games are puzzles with exactly one right answer, so a level is only
#: "solved" at full marks. Partial credit is still reported, and still feeds
#: mastery tracking, but it does not unlock the level.
GAME_PASS_THRESHOLD = 1.0


def grade_counts(
    counts: dict[str, int], target: dict[str, Any]
) -> tuple[float, str]:
    """Score a counts distribution with total variation distance."""
    expected = target.get("counts") or {}
    if not expected:
        return 1.0, "No target distribution defined; behavioural check skipped."

    total = sum(counts.values()) or 1
    observed = {k: v / total for k, v in counts.items()}

    width = max((len(k) for k in list(expected) + list(observed)), default=0)
    exp_norm = {k.zfill(width): float(v) for k, v in expected.items()}
    obs_norm = {k.zfill(width): v for k, v in observed.items()}

    exp_sum = sum(exp_norm.values()) or 1.0
    exp_norm = {k: v / exp_sum for k, v in exp_norm.items()}

    keys = set(exp_norm) | set(obs_norm)
    tvd = 0.5 * sum(abs(obs_norm.get(k, 0.0) - exp_norm.get(k, 0.0)) for k in keys)

    tolerance = float(target.get("tolerance", 0.15))
    score = max(0.0, 1.0 - tvd / max(tolerance, 1e-6)) if tvd > 0 else 1.0
    score = min(1.0, score)
    detail = f"Distribution distance {tvd:.3f} (tolerance {tolerance:.3f})."
    return score, detail


def grade_state(statevector: list[list[float]] | None, target: dict[str, Any]) -> tuple[float, str]:
    """Score state fidelity |<psi_target|psi>|^2."""
    expected = target.get("statevector")
    if not expected or not statevector:
        return 1.0, "No target state defined; fidelity check skipped."
    got = np.array([complex(r, i) for r, i in statevector])
    want = np.array([complex(*pair) if isinstance(pair, list) else complex(pair) for pair in expected])
    if got.shape != want.shape:
        return 0.0, f"State dimension mismatch ({got.size} vs {want.size})."
    got = got / (np.linalg.norm(got) or 1)
    want = want / (np.linalg.norm(want) or 1)
    fidelity = float(abs(np.vdot(want, got)) ** 2)
    tolerance = float(target.get("tolerance", 0.05))
    score = 1.0 if fidelity >= 1 - tolerance else max(0.0, fidelity)
    return score, f"State fidelity {fidelity:.4f}."


def grade(
    ir: CircuitIR,
    challenge: dict[str, Any],
    result: dict[str, Any] | None,
) -> dict[str, Any]:
    """Full grading pass; returns score, pass flag, feedback and details."""
    problems = check_challenge_constraints(ir, challenge)
    target = challenge.get("target") or {}
    details: dict[str, Any] = {
        "constraint_problems": problems,
        "summary": summarize_circuit(ir),
    }

    if problems:
        return {
            "score": 0.0,
            "passed": False,
            "feedback": "Constraints not satisfied:\n- " + "\n- ".join(problems),
            "details": details,
        }

    if result is None:
        return {
            "score": 0.0,
            "passed": False,
            "feedback": "Simulation did not produce a result.",
            "details": details,
        }

    # Game levels are ordinary challenges with game_meta set, so they reuse
    # everything above and only swap the behavioural half of the grade.
    meta = challenge.get("game_meta") or {}
    grader = meta.get("grader")

    if grader == "truth_table":
        score, note, extra = game_graders.grade_truth_table(ir, meta)
        details["game"] = extra
    elif grader == "shot_detective":
        shots = int((result or {}).get("metadata", {}).get("shots", 0))
        score, note, extra = game_graders.grade_shot_detective(
            result.get("counts") or {}, meta, shots
        )
        details["game"] = extra
    elif grader == "find_bug":
        kind = target.get("type", "counts")
        if kind == "state":
            base, base_note = grade_state(result.get("statevector"), target)
        else:
            base, base_note = grade_counts(result.get("counts") or {}, target)
        base = base if base >= PASS_THRESHOLD else 0.0
        score, note, extra = game_graders.grade_find_bug(ir, meta, base)
        note = f"{base_note} {note}"
        details["game"] = extra
    else:
        kind = target.get("type", "counts")
        if kind == "state":
            score, note = grade_state(result.get("statevector"), target)
        else:
            score, note = grade_counts(result.get("counts") or {}, target)

    if meta.get("efficiency"):
        factor, eff_note = game_graders.efficiency_bonus(ir, meta)
        if eff_note:
            score *= factor
            note = f"{note} {eff_note}"

    details["behaviour_note"] = note
    details["counts"] = result.get("counts")

    # Game levels are puzzles with one right answer, so "solved" means solved.
    # A coding challenge can still award partial credit at PASS_THRESHOLD,
    # but a game that congratulates you for a 0.85 is teaching that an
    # almost-right circuit is right.
    if meta:
        passed = score >= GAME_PASS_THRESHOLD
    else:
        passed = score >= PASS_THRESHOLD
    details["pass_threshold"] = GAME_PASS_THRESHOLD if meta else PASS_THRESHOLD

    if passed:
        feedback = f"Passed. {note} Nice work."
    elif meta and score > 0:
        feedback = (
            f"Not solved yet — scored {score:.2f}, and this level needs a "
            f"perfect {GAME_PASS_THRESHOLD:.2f}. {note}"
        )
    else:
        feedback = (
            f"Not quite. {note} Compare your histogram with the expected "
            "distribution."
        )
    return {"score": round(score, 4), "passed": passed, "feedback": feedback, "details": details}


def finalize_attempt(db: Session, attempt_id: int) -> dict[str, Any]:
    """Grade an attempt whose simulation job has completed."""
    from app.models.job import SimulationJob

    attempt = db.get(ChallengeAttempt, attempt_id)
    if attempt is None:
        return {"error": f"attempt {attempt_id} not found"}
    challenge = db.get(CodingChallenge, attempt.challenge_id)
    if challenge is None:
        return {"error": "challenge not found"}

    job = db.get(SimulationJob, attempt.job_id) if attempt.job_id else None
    if job is not None and job.status in {"queued", "running"}:
        return {"status": job.status, "attempt_id": attempt_id}

    ir = CircuitIR.from_dict(attempt.circuit_ir)
    challenge_dict = {
        "allowed_gates": challenge.allowed_gates,
        "target": challenge.target,
        "constraints": challenge.constraints,
        "game_meta": challenge.game_meta,
    }
    outcome = grade(ir, challenge_dict, job.result if job else None)

    if job is not None and job.status == "failed":
        outcome["feedback"] = f"Simulation failed: {job.error}"
        outcome["passed"] = False
        outcome["score"] = 0.0

    attempt.score = outcome["score"]
    attempt.passed = outcome["passed"]
    attempt.feedback = outcome["feedback"]
    db.add(AutogradeResult(attempt_id=attempt.id, details=outcome["details"]))
    db.commit()

    from app.services.recommendations import update_mastery_from_challenge

    update_mastery_from_challenge(db, attempt.user_id, challenge, outcome["passed"])

    return {
        "status": "graded",
        "attempt_id": attempt_id,
        "passed": outcome["passed"],
        "score": outcome["score"],
        "feedback": outcome["feedback"],
        "details": outcome["details"],
    }


__all__ = [
    "grade",
    "grade_counts",
    "grade_state",
    "finalize_attempt",
    "PASS_THRESHOLD",
    "GAME_PASS_THRESHOLD",
]
