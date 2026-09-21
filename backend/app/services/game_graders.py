"""Extra grading modes for Quantum Games.

A "game level" is an ordinary :class:`CodingChallenge` with ``game_meta``
populated, so everything here plugs into the existing attempt and grading
pipeline rather than duplicating it. Each grader returns the same
``(score, note, details)`` shape the autograder already understands.

Three modes:

``truth_table``
    Functional correctness of a multi-controlled gate, checked over every
    computational basis input with exact statevector evolution. No sampling,
    so no shot noise and no flaky pass/fail.

``shot_detective``
    Teaches sampling error. Grades one high-shot run by subsampling prefixes
    of the shot stream, which gives a whole convergence curve from a single
    simulation instead of one job per shot count.

``find_bug``
    Correctness plus an edit budget, measured against the broken circuit the
    learner started from.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from app.quantum.ir import CircuitIR

#: Evaluating a truth table costs 2**n statevector evolutions, so cap it.
MAX_TRUTH_TABLE_QUBITS = 5


# --------------------------------------------------------------------------- #
# Multi-Control Challenge
# --------------------------------------------------------------------------- #
def truth_table(ir: CircuitIR) -> list[dict[str, Any]]:
    """Evolve every basis input through the circuit.

    Each row records the input bits, the most likely output bits, and the
    probability of that output. The probability matters: a circuit containing
    a Hadamard leaves the register in a superposition with no single answer,
    and silently reporting the ``argmax`` basis state as "the output" produces
    a truth table that looks authoritative but means nothing.

    Index ``k`` is qubit ``k`` (Qiskit ordering, qubit 0 least significant).
    """
    from qiskit.quantum_info import Statevector

    from app.quantum.normalize import to_qiskit

    if ir.n_qubits > MAX_TRUTH_TABLE_QUBITS:
        raise ValueError(
            f"Truth-table grading is limited to {MAX_TRUTH_TABLE_QUBITS} qubits "
            f"(got {ir.n_qubits}); it evaluates 2**n inputs."
        )

    circuit = to_qiskit(ir, include_measurements=False)
    n = ir.n_qubits
    rows: list[dict[str, Any]] = []
    for value in range(2**n):
        evolved = Statevector.from_int(value, dims=2**n).evolve(circuit)
        weights = np.abs(evolved.data) ** 2
        out = int(np.argmax(weights))
        rows.append(
            {
                "in_bits": [(value >> k) & 1 for k in range(n)],
                "out_bits": [(out >> k) & 1 for k in range(n)],
                "certainty": float(weights[out]),
            }
        )
    return rows


def grade_truth_table(
    ir: CircuitIR, meta: dict[str, Any]
) -> tuple[float, str, dict[str, Any]]:
    """Score an MCX-style circuit: flip the target iff every control is 1.

    Controls must also come back unchanged -- a circuit that scrambles its
    controls is not a multi-controlled NOT, even if the target looks right.

    Returns the COMPLETE table, pass or fail. A learner who just solved the
    level wants to see the logic they built, and hiding it on success is the
    one moment the table is most worth reading.
    """
    n_controls = int(meta.get("n_controls", max(1, ir.n_qubits - 1)))
    controls = list(range(n_controls))
    target = n_controls

    if ir.n_qubits <= n_controls:
        return 0.0, (
            f"This level needs {n_controls + 1} qubits "
            f"({n_controls} controls plus a target); the circuit has {ir.n_qubits}."
        ), {}

    try:
        rows = truth_table(ir)
    except ValueError as exc:
        return 0.0, str(exc), {}

    passed = 0
    table: list[dict[str, Any]] = []
    superposed = 0

    for row in rows:
        in_bits, out_bits = row["in_bits"], row["out_bits"]
        certainty = row["certainty"]
        all_controls_set = all(in_bits[c] == 1 for c in controls)
        want_target = in_bits[target] ^ (1 if all_controls_set else 0)
        controls_intact = all(out_bits[c] == in_bits[c] for c in controls)
        # A superposed output has no definite bitstring, so it cannot be a
        # correct classical truth-table row however the argmax happens to fall.
        definite = certainty > 0.99
        ok = definite and out_bits[target] == want_target and controls_intact
        if ok:
            passed += 1
        if not definite:
            superposed += 1

        table.append(
            {
                "input": "".join(str(b) for b in reversed(in_bits)),
                "output": "".join(str(b) for b in reversed(out_bits)),
                "expected_target": want_target,
                "got_target": out_bits[target],
                "controls_intact": controls_intact,
                "certainty": round(certainty, 4),
                "definite": definite,
                "passed": ok,
            }
        )

    total = len(rows)
    score = passed / total if total else 0.0
    note = f"Truth table: {passed}/{total} inputs behave correctly."

    if superposed:
        note += (
            f" {superposed} input(s) left the register in a superposition, so "
            "there is no definite output. This level is about classical logic: "
            "use only X and controlled-X gates."
        )
    else:
        first_failure = next((r for r in table if not r["passed"]), None)
        if first_failure is not None:
            note += (
                f" First failure on input |{first_failure['input']}⟩: target "
                f"should be {first_failure['expected_target']}, got "
                f"{first_failure['got_target']}."
            )

    return score, note, {
        "testcases_total": total,
        "testcases_passed": passed,
        "superposed": superposed,
        "table": table,
        # Kept for older attempts stored before the full table existed.
        "failures": [r for r in table if not r["passed"]][:4],
    }


# --------------------------------------------------------------------------- #
# Shot Detective
# --------------------------------------------------------------------------- #
def subsample_curve(
    counts: dict[str, int], ideal: dict[str, float], shot_points: list[int], seed: int = 0
) -> list[dict[str, float]]:
    """Convergence curve from a single high-shot run.

    Rebuilds a shot stream from the counts, shuffles it once, then measures
    prefixes. One simulation yields the whole curve, which matters because a
    job per shot count would be slow and would spend real backend time.
    """
    stream: list[str] = []
    for outcome, n in counts.items():
        stream.extend([outcome] * int(n))
    if not stream:
        return []

    rng = np.random.default_rng(seed)
    rng.shuffle(stream)

    curve: list[dict[str, float]] = []
    for point in sorted(shot_points):
        take = min(point, len(stream))
        observed: dict[str, int] = {}
        for outcome in stream[:take]:
            observed[outcome] = observed.get(outcome, 0) + 1
        keys = set(observed) | set(ideal)
        tvd = 0.5 * sum(
            abs(observed.get(k, 0) / take - ideal.get(k, 0.0)) for k in keys
        )
        curve.append({"shots": take, "tvd": round(tvd, 5)})
    return curve


def grade_shot_detective(
    counts: dict[str, int], meta: dict[str, Any], chosen_shots: int
) -> tuple[float, str, dict[str, Any]]:
    """Reward hitting the accuracy target with as few shots as possible."""
    ideal = {k: float(v) for k, v in (meta.get("ideal") or {}).items()}
    if not ideal:
        return 0.0, "This level has no ideal distribution configured.", {}

    epsilon = float(meta.get("epsilon", 0.05))
    total = sum(counts.values()) or 1
    observed = {k: v / total for k, v in counts.items()}
    keys = set(observed) | set(ideal)
    tvd = 0.5 * sum(abs(observed.get(k, 0.0) - ideal.get(k, 0.0)) for k in keys)

    points = [p for p in (128, 256, 512, 1024, 2048, 4096) if p <= max(total, 128)]
    curve = subsample_curve(counts, ideal, points)

    details = {
        "tvd": round(tvd, 5),
        "epsilon": epsilon,
        "chosen_shots": chosen_shots,
        "curve": curve,
        "ideal": ideal,
    }

    if tvd > epsilon:
        return 0.0, (
            f"Distribution error {tvd:.4f} exceeds the tolerance of {epsilon:.4f}. "
            "Use more shots."
        ), details

    # Inside tolerance: fewer shots is better. log2 keeps the penalty gentle,
    # because halving the shots is the meaningful step, not saving 100 of them.
    cheapest, dearest = 128, 4096
    span = math.log2(dearest) - math.log2(cheapest)
    used = min(max(chosen_shots, cheapest), dearest)
    efficiency = 1.0 - (math.log2(used) - math.log2(cheapest)) / span
    score = 0.6 + 0.4 * efficiency
    details["efficiency"] = round(efficiency, 4)
    return score, (
        f"Within tolerance: error {tvd:.4f} <= {epsilon:.4f} using {chosen_shots} shots."
    ), details


# --------------------------------------------------------------------------- #
# Find the Bug
# --------------------------------------------------------------------------- #
def _op_signature(op: dict[str, Any]) -> tuple:
    return (
        op.get("kind"),
        op.get("gate"),
        tuple(op.get("qubits") or []),
        tuple(op.get("controls") or []),
        tuple(op.get("clbits") or []),
        tuple(str(p) for p in (op.get("params") or [])),
        op.get("layer"),
    )


def count_edits(starter: dict[str, Any], submitted: dict[str, Any]) -> dict[str, int]:
    """Practical edit distance between two circuits.

    Not a minimal edit script -- that is a graph problem and overkill here.
    Signatures are multiset-compared, so reordering identical operations is
    free while changing a gate, a qubit, a parameter or a layer counts.
    """
    from collections import Counter

    before = Counter(_op_signature(o) for o in (starter.get("ops") or []))
    after = Counter(_op_signature(o) for o in (submitted.get("ops") or []))

    removed = sum((before - after).values())
    added = sum((after - before).values())
    # A changed op shows up as one removal plus one addition; call that a
    # single modification so the learner is not charged twice for one fix.
    modified = min(removed, added)
    return {
        "added": added - modified,
        "removed": removed - modified,
        "modified": modified,
        "total": max(added, removed),
    }


def grade_find_bug(
    submitted_ir: CircuitIR,
    meta: dict[str, Any],
    correctness: float,
) -> tuple[float, str, dict[str, Any]]:
    """Correctness first, then an edit budget.

    Correctness dominates: a working circuit that used too many edits still
    scores, it just scores less. A broken circuit scores zero however few
    edits it took.
    """
    starter = meta.get("starter_ir") or {}
    edits = count_edits(starter, submitted_ir.to_dict())
    max_edits = int(meta.get("max_edits", 3))

    details = {"edits": edits, "max_edits": max_edits, "correctness": round(correctness, 4)}

    if correctness <= 0.0:
        return 0.0, "The circuit still does not produce the expected behaviour.", details

    used = edits["total"]
    over = max(0, used - max_edits)
    # 15% off per edit over budget, never below half the correctness score.
    penalty = min(0.5, 0.15 * over)
    score = correctness * (1.0 - penalty)

    note = f"Fixed with {used} edit{'s' if used != 1 else ''} (budget {max_edits})."
    if over:
        note += f" {over} over budget, {int(penalty * 100)}% deducted."
    return score, note, details


# --------------------------------------------------------------------------- #
# Shared efficiency term
# --------------------------------------------------------------------------- #
def efficiency_bonus(ir: CircuitIR, meta: dict[str, Any]) -> tuple[float, str]:
    """Optional gate-count/depth term, blended in at a low weight.

    Deliberately small. Scoring hard on gate count teaches students to game
    the metric -- cramming operations into fewer layers produces circuits that
    are harder to read and no better physically.
    """
    weight = float(meta.get("efficiency", 0.0))
    if weight <= 0:
        return 1.0, ""

    par = int(meta.get("par_gates", 0)) or None
    gates = sum(1 for op in ir.walk() if op.kind == "gate")
    if par is None:
        return 1.0, ""
    if gates <= par:
        return 1.0, f"Gate count {gates} meets par ({par})."
    excess = gates - par
    factor = max(0.0, 1.0 - 0.1 * excess)
    return factor, f"Gate count {gates} is {excess} over par ({par})."


__all__ = [
    "MAX_TRUTH_TABLE_QUBITS",
    "truth_table",
    "grade_truth_table",
    "subsample_curve",
    "grade_shot_detective",
    "count_edits",
    "grade_find_bug",
    "efficiency_bonus",
]
