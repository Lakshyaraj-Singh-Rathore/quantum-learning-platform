"""Quantum Games: level definitions and the three extra grading modes.

A game level is an ordinary CodingChallenge with ``game_meta`` populated, so
these tests also guard the promise that games reuse the existing attempt and
grading pipeline rather than a parallel one.
"""

from __future__ import annotations

import pytest

from app.games import (
    BELL_LEVELS,
    FIND_BUG_LEVELS,
    GAME_LEVELS,
    GAMES,
    MULTI_CONTROL_LEVELS,
    SHOT_DETECTIVE_LEVELS,
)
from app.quantum.ir import CircuitIR
from app.services import game_graders as g


def _c(n, ops):
    return CircuitIR.from_dict({"n_qubits": n, "n_clbits": n, "ops": ops})


# ------------------------------------------------------------- level catalogue
def test_every_level_declares_a_game_and_position():
    for level in GAME_LEVELS:
        meta = level["game_meta"]
        assert meta["game_id"] in GAMES, f"{level['slug']} has an unknown game_id"
        assert meta["level"] >= 1


def test_level_slugs_are_unique():
    slugs = [level["slug"] for level in GAME_LEVELS]
    assert len(slugs) == len(set(slugs))


def test_levels_are_numbered_consecutively_within_each_game():
    by_game: dict[str, list[int]] = {}
    for level in GAME_LEVELS:
        meta = level["game_meta"]
        by_game.setdefault(meta["game_id"], []).append(meta["level"])
    for game_id, numbers in by_game.items():
        assert sorted(numbers) == list(range(1, len(numbers) + 1)), game_id


def test_levels_stay_small_enough_to_grade_quickly():
    for level in GAME_LEVELS:
        max_qubits = (level["constraints"] or {}).get("max_qubits")
        assert max_qubits is not None, f"{level['slug']} has no qubit cap"
        assert max_qubits <= 5


# --------------------------------------------------------------- truth table
def test_toffoli_passes_its_truth_table():
    meta = MULTI_CONTROL_LEVELS[1]["game_meta"]
    ir = _c(3, [{"kind": "gate", "gate": "x", "qubits": [2], "controls": [0, 1], "layer": 0}])
    score, note, details = g.grade_truth_table(ir, meta)
    assert score == 1.0
    assert details["testcases_passed"] == details["testcases_total"] == 8


def test_single_control_fails_a_toffoli_level():
    """The classic mistake: one control instead of two."""
    meta = MULTI_CONTROL_LEVELS[1]["game_meta"]
    ir = _c(3, [{"kind": "gate", "gate": "x", "qubits": [2], "controls": [0], "layer": 0}])
    score, _, details = g.grade_truth_table(ir, meta)
    assert score < 0.8, "a wrong circuit must not reach the pass threshold"
    assert details["failures"]


def test_unconditional_flip_fails():
    """A bare X on the target is right for half the inputs and wrong for half."""
    meta = MULTI_CONTROL_LEVELS[1]["game_meta"]
    ir = _c(3, [{"kind": "gate", "gate": "x", "qubits": [2], "layer": 0}])
    score, _, _ = g.grade_truth_table(ir, meta)
    assert score < 0.8


def test_circuit_that_disturbs_its_controls_fails():
    """Flipping the target is not enough; controls must survive."""
    meta = MULTI_CONTROL_LEVELS[0]["game_meta"]
    ir = _c(2, [
        {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [0], "layer": 1},
    ])
    score, _, _ = g.grade_truth_table(ir, meta)
    assert score < 1.0


@pytest.mark.parametrize("n_controls", [1, 2, 3])
def test_mcx_of_each_size_passes(n_controls):
    meta = {"n_controls": n_controls}
    ir = _c(n_controls + 1, [{
        "kind": "gate", "gate": "x",
        "qubits": [n_controls], "controls": list(range(n_controls)), "layer": 0,
    }])
    score, _, _ = g.grade_truth_table(ir, meta)
    assert score == 1.0


def test_truth_table_refuses_oversized_circuits():
    ir = _c(6, [{"kind": "gate", "gate": "x", "qubits": [0], "layer": 0}])
    score, note, _ = g.grade_truth_table(ir, {"n_controls": 5})
    assert score == 0.0
    assert "limited to" in note


def test_truth_table_rejects_too_few_qubits():
    ir = _c(2, [{"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 0}])
    score, note, _ = g.grade_truth_table(ir, {"n_controls": 3})
    assert score == 0.0
    assert "needs" in note


# ------------------------------------------------------------ shot detective
def test_subsampling_returns_one_point_per_shot_count():
    counts = {"00": 2048, "11": 2048}
    curve = g.subsample_curve(counts, {"00": 0.5, "11": 0.5}, [128, 512, 4096])
    assert [p["shots"] for p in curve] == [128, 512, 4096]


def test_subsampling_converges_towards_the_ideal():
    counts = {"00": 2048, "11": 2048}
    curve = g.subsample_curve(counts, {"00": 0.5, "11": 0.5}, [128, 4096])
    assert curve[-1]["tvd"] <= curve[0]["tvd"] + 1e-9


def test_fewer_shots_scores_higher_when_accurate():
    meta = SHOT_DETECTIVE_LEVELS[0]["game_meta"]
    counts = {"00": 2048, "11": 2048}
    low, _, _ = g.grade_shot_detective(counts, meta, 128)
    high, _, _ = g.grade_shot_detective(counts, meta, 4096)
    assert low > high


def test_inaccurate_sample_scores_zero_however_few_shots():
    meta = SHOT_DETECTIVE_LEVELS[0]["game_meta"]
    score, note, _ = g.grade_shot_detective({"00": 3900, "11": 196}, meta, 128)
    assert score == 0.0
    assert "exceeds the tolerance" in note


def test_shot_detective_needs_an_ideal_distribution():
    score, note, _ = g.grade_shot_detective({"00": 10}, {}, 128)
    assert score == 0.0
    assert "no ideal distribution" in note


# ----------------------------------------------------------------- find bug
def _fixed_bell():
    starter = FIND_BUG_LEVELS[0]["game_meta"]["starter_ir"]
    fixed = {**starter, "ops": [dict(op) for op in starter["ops"]]}
    fixed["ops"][0]["gate"] = "h"
    return starter, fixed


def test_one_gate_fix_counts_as_one_edit():
    starter, fixed = _fixed_bell()
    edits = g.count_edits(starter, fixed)
    assert edits["total"] == 1
    assert edits["modified"] == 1


def test_identical_circuit_is_zero_edits():
    starter = FIND_BUG_LEVELS[0]["game_meta"]["starter_ir"]
    assert g.count_edits(starter, starter)["total"] == 0


def test_reordering_identical_ops_is_free():
    """Signatures are multiset-compared, so op order alone is not an edit."""
    starter = {"ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [1], "layer": 1},
    ]}
    shuffled = {"ops": list(reversed(starter["ops"]))}
    assert g.count_edits(starter, shuffled)["total"] == 0


def test_within_budget_keeps_full_correctness():
    meta = FIND_BUG_LEVELS[0]["game_meta"]
    _, fixed = _fixed_bell()
    score, _, _ = g.grade_find_bug(CircuitIR.from_dict(fixed), meta, correctness=1.0)
    assert score == pytest.approx(1.0)


def test_over_budget_is_penalised_but_not_zeroed():
    meta = FIND_BUG_LEVELS[0]["game_meta"]
    _, fixed = _fixed_bell()
    wasteful = {**fixed, "ops": fixed["ops"] + [
        {"kind": "gate", "gate": "z", "qubits": [0], "layer": 10 + i} for i in range(4)
    ]}
    score, note, _ = g.grade_find_bug(CircuitIR.from_dict(wasteful), meta, correctness=1.0)
    assert 0.0 < score < 1.0
    assert "over budget" in note


def test_broken_circuit_scores_zero_however_few_edits():
    meta = FIND_BUG_LEVELS[0]["game_meta"]
    starter = CircuitIR.from_dict(meta["starter_ir"])
    score, _, _ = g.grade_find_bug(starter, meta, correctness=0.0)
    assert score == 0.0


# ---------------------------------------------------------------- efficiency
def test_efficiency_is_neutral_at_par():
    ir = _c(2, [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
    ])
    factor, _ = g.efficiency_bonus(ir, {"efficiency": 0.15, "par_gates": 2})
    assert factor == 1.0


def test_efficiency_penalises_excess_gates_gently():
    ir = _c(2, [{"kind": "gate", "gate": "h", "qubits": [0], "layer": i} for i in range(5)])
    factor, note = g.efficiency_bonus(ir, {"efficiency": 0.15, "par_gates": 2})
    assert 0.5 < factor < 1.0, "correctness must still dominate the score"
    assert "over par" in note


def test_efficiency_is_off_by_default():
    ir = _c(1, [{"kind": "gate", "gate": "h", "qubits": [0], "layer": 0}])
    factor, note = g.efficiency_bonus(ir, {})
    assert factor == 1.0 and note == ""


# ----------------------------------------------------- bell levels are sane
def test_bell_levels_are_graded_on_state_not_counts():
    """Phi+ and Phi- have identical histograms; only fidelity separates them."""
    for level in BELL_LEVELS:
        assert level["target"]["type"] == "state"


def test_phi_plus_and_phi_minus_differ_only_by_a_sign():
    plus = BELL_LEVELS[0]["target"]["state"]
    minus = BELL_LEVELS[1]["target"]["state"]
    assert plus[0] == minus[0]
    assert plus[3][0] == pytest.approx(-minus[3][0])


# --------------------------------------------------------------- HTTP surface
def test_games_endpoint_requires_auth(client):
    assert client.get("/games").status_code == 401


def test_games_endpoint_groups_levels(client, student_headers):
    response = client.get("/games", headers=student_headers)
    assert response.status_code == 200
    games = {entry["game_id"]: entry for entry in response.json()["games"]}
    assert "multi_control" in games
    assert games["multi_control"]["total"] == len(MULTI_CONTROL_LEVELS)
    assert all("level" in item for item in games["multi_control"]["levels"])


def test_playing_a_truth_table_level_end_to_end(client, student_headers):
    good = {"n_qubits": 3, "n_clbits": 3, "ops": [
        {"kind": "gate", "gate": "x", "qubits": [2], "controls": [0, 1], "layer": 0}]}
    submitted = client.post(
        "/challenges/game-vault-2/submit",
        json={"circuit_ir": good}, headers=student_headers,
    )
    assert submitted.status_code == 200
    attempt_id = submitted.json()["attempt_id"]
    outcome = client.get(f"/attempts/{attempt_id}", headers=student_headers).json()
    assert outcome["passed"] is True
    assert outcome["score"] == 1.0
