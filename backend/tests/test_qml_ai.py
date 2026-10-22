"""Grounding, the unconfigured path, and a clearly-labelled fake transport.

What these tests do and do not prove (§2F.1, said plainly so the report can
repeat it):

- They prove the prompt contains the experiment's real numbers, that the
  unconfigured path is useful rather than broken, that a Gemini failure is
  translated instead of escaping, and that no key is ever echoed.
- They do **not** prove Gemini answers well, or that the live call works at
  all. ``GEMINI_API_KEY`` is absent in this environment and
  ``is_configured()`` also needs an importable SDK, so the live path cannot
  be exercised here. It is registered as MT-010 instead.

The payloads are the ones captured from real worker-path runs for Phase 5c
(``frontend/web/test-fixtures/qml-task-payloads.json``) rather than dicts
written to match the code -- Phase 3's fixture invented four keys that
``/qml/describe`` never returned, and the rule since is to derive fixtures
from a real response.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from app.ai import gemini_client
from app.services import qml_ai

_FIXTURE = (
    pathlib.Path(__file__).resolve().parents[2]
    / "frontend"
    / "web"
    / "test-fixtures"
    / "qml-task-payloads.json"
)


def _payload(algorithm: str) -> tuple[dict, list[dict]]:
    data = json.loads(_FIXTURE.read_text())
    detail = data[algorithm]["detail"]
    return detail["result"], detail["history"]


# ---------------------------------------------------------------------------
# The fixture must still be adversarial
# ---------------------------------------------------------------------------


def test_the_captured_fixtures_still_carry_the_hazards_these_tests_rely_on():
    """A regenerated fixture that lost its nulls would make the rest vacuous."""
    _, regression_history = _payload("quantum_regression")
    _, kernel_history = _payload("quantum_kernel")

    assert regression_history, "regression fixture has no epochs"
    assert all(row["train_accuracy"] is None for row in regression_history), (
        "regression epochs are supposed to store NULL accuracy"
    )
    assert kernel_history == [], "the kernel is supposed to write zero epoch rows"


# ---------------------------------------------------------------------------
# WP1 -- grounding is in the prompt, asserted on literals
# ---------------------------------------------------------------------------


def test_classification_prompt_contains_the_exact_stored_metrics():
    """The numbers are hardcoded here on purpose.

    Asserting via ``qml_ai._fmt`` would pass even if ``_fmt`` were wrong --
    the test would be restating the implementation. These literals were
    read off the captured payload by hand.
    """
    result, history = _payload("vqc")
    prompt = qml_ai.build_prompt(result, history)

    assert "0.7778" in prompt, "test accuracy missing from the prompt"
    assert "0.6923" in prompt, "precision missing"
    assert "0.8182" in prompt, "f1 missing"
    assert "[[5, 4], [0, 9]]" in prompt, "confusion matrix missing"
    assert "0.9048" in prompt, "baseline train accuracy missing"
    assert "logistic_regression" in prompt
    assert "moons" in prompt
    assert "16" in prompt, "trainable parameter count missing"


def test_regression_prompt_carries_signed_r2_and_no_accuracy():
    result, history = _payload("quantum_regression")
    prompt = qml_ai.build_prompt(result, history)

    assert "0.5954" in prompt, "MAE missing"
    assert "0.6679" in prompt, "RMSE missing"
    assert "0.1582" in prompt, "R2 missing"
    assert "ridge" in prompt
    # the negative R2 hazard must survive into the prompt with its sign
    assert "-2.0602" in prompt, "epoch-1 train R2 lost its sign or its value"
    # Over the WHOLE prompt, not a slice. An earlier version of this test
    # split on "TASK" and lowercased first, which silently matched
    # "- task: regression" on line 3 and inspected 45 of 847 characters --
    # it would have passed on a prompt full of accuracies.
    assert "accuracy" not in prompt.lower(), (
        "a regression prompt must not offer the model an accuracy to talk about"
    )


def test_kernel_prompt_states_zero_epochs_is_correct_not_missing():
    """The zero-in-the-fixture blindness, addressed directly.

    `epochs_completed` is genuinely 0 here, so asserting "0 appears" proves
    nothing. Assert instead on the non-zero evaluation counts and on the
    sentence that tells the model the absence is by design.
    """
    result, history = _payload("quantum_kernel")
    prompt = qml_ai.build_prompt(result, history)

    assert history == []
    assert "1617" in prompt or "1,617" in prompt, "measured kernel evaluations missing"
    assert "2520" in prompt or "2,520" in prompt, "naive full-matrix count missing"
    assert "no training loop" in prompt
    assert "not missing data" in prompt
    assert "LSSVM" in prompt


def test_prompt_never_invents_a_metric_the_task_lacks():
    """Each task's prompt offers only its own metrics."""
    classification, c_hist = _payload("vqc")
    regression, r_hist = _payload("quantum_regression")

    c_prompt = qml_ai.build_prompt(classification, c_hist)
    r_prompt = qml_ai.build_prompt(regression, r_hist)

    # Whole-prompt containment in both directions. The two metric
    # vocabularies are disjoint, so this is exact rather than approximate.
    for classification_only in ("accuracy", "precision", "recall", "f1", "confusion"):
        assert classification_only not in r_prompt.lower(), (
            f"regression prompt leaked the classification metric {classification_only!r}"
        )
    for regression_only in ("r2", "mae", "rmse"):
        assert regression_only not in c_prompt.lower(), (
            f"classification prompt leaked the regression metric {regression_only!r}"
        )


def test_the_system_instruction_forbids_inventing_values():
    assert "NEVER introduce a numeric value" in qml_ai._SYSTEM
    assert "regression run has no" in qml_ai._SYSTEM


# ---------------------------------------------------------------------------
# WP1 -- the over-length guard rejects, it does not truncate
# ---------------------------------------------------------------------------


def test_an_oversized_history_is_rejected_rather_than_truncated():
    """Truncating would drop the evidence and keep the confidence."""
    result, _ = _payload("vqc")
    huge = [
        {"epoch": i, "train_loss": 0.5, "train_accuracy": 0.8, "elapsed_seconds": 1.0}
        for i in range(1, 4000)
    ]
    assert len(qml_ai.build_prompt(result, huge)) > qml_ai.MAX_PROMPT_CHARS

    with pytest.raises(ValueError, match="too long to explain"):
        qml_ai.explain(result, huge)


def test_a_normal_run_is_comfortably_inside_the_budget():
    """The guard must not fire on real data, or the feature never runs."""
    for algorithm in ("vqc", "quantum_regression", "quantum_kernel"):
        result, history = _payload(algorithm)
        assert len(qml_ai.build_prompt(result, history)) < qml_ai.MAX_PROMPT_CHARS


# ---------------------------------------------------------------------------
# WP3 -- the unconfigured path, which is what CI actually runs
# ---------------------------------------------------------------------------


def test_unconfigured_returns_a_useful_body_and_never_raises(monkeypatch):
    monkeypatch.setattr(gemini_client, "is_configured", lambda: False)
    result, history = _payload("quantum_regression")

    payload = qml_ai.explain(result, history)

    assert payload["configured"] is False
    assert payload["explanation"].strip(), "offline path returned an empty body"
    # it must still carry the real numbers, which is the whole point
    assert "0.5954" in payload["explanation"]
    assert "ridge" in payload["explanation"]
    assert payload["grounded_on"]["evaluation"]["mae"] == pytest.approx(0.5953765266560695)


def test_unconfigured_message_says_what_is_missing_and_what_still_works(monkeypatch):
    monkeypatch.setattr(gemini_client, "is_configured", lambda: False)
    result, history = _payload("vqc")

    text = qml_ai.explain(result, history)["explanation"]

    assert "GEMINI_API_KEY" in text, "must name what is missing"
    assert "baseline" in text.lower(), "must still give the comparison that works"


def test_unconfigured_path_never_echoes_a_key(monkeypatch):
    """A key must not reach the response even when one is set."""
    secret = "AIzaSy-THIS-IS-A-FAKE-TEST-KEY-0000000"

    class _Settings:
        gemini_api_key = secret
        gemini_chat_model = "gemini-2.0-flash"

    monkeypatch.setattr(gemini_client, "get_settings", lambda: _Settings())
    monkeypatch.setattr(gemini_client, "is_configured", lambda: False)
    result, history = _payload("vqc")

    payload = qml_ai.explain(result, history)

    assert secret not in json.dumps(payload)
    assert secret not in qml_ai.build_prompt(result, history)


# ---------------------------------------------------------------------------
# WP4 -- the configured path, against a FAKE transport (named as such)
# ---------------------------------------------------------------------------


def test_configured_path_against_a_fake_gemini_sends_the_grounded_prompt(monkeypatch):
    """FAKE transport. Proves wiring and grounding, not answer quality."""
    seen: dict[str, object] = {}

    def _fake_generate(prompt, system_instruction=None, temperature=1.0, **kwargs):
        seen["prompt"] = prompt
        seen["system_instruction"] = system_instruction
        seen["temperature"] = temperature
        return "  The quantum model tied the baseline at 0.7778.  "

    monkeypatch.setattr(gemini_client, "is_configured", lambda: True)
    monkeypatch.setattr(gemini_client, "generate", _fake_generate)
    result, history = _payload("vqc")

    payload = qml_ai.explain(result, history)

    assert payload["configured"] is True
    assert payload["explanation"] == "The quantum model tied the baseline at 0.7778."
    assert "0.7778" in seen["prompt"], "the real metric never reached the model"
    assert "NEVER introduce a numeric value" in seen["system_instruction"]
    assert seen["temperature"] == qml_ai.EXPLAIN_TEMPERATURE
    assert seen["temperature"] < 1.0, "confabulation risk wants a low temperature"


def test_configured_path_lets_gemini_unavailable_reach_the_route(monkeypatch):
    """FAKE transport raising the real exception type.

    The service deliberately does not swallow this: the route turns it into
    a 503, the way api/jobs.py does.
    """

    def _boom(*args, **kwargs):
        raise gemini_client.GeminiUnavailable("model retired")

    monkeypatch.setattr(gemini_client, "is_configured", lambda: True)
    monkeypatch.setattr(gemini_client, "generate", _boom)
    result, history = _payload("vqc")

    with pytest.raises(gemini_client.GeminiUnavailable):
        qml_ai.explain(result, history)


def test_grounded_on_mirrors_the_payload_so_the_ui_can_print_it(monkeypatch):
    """The half of grounding that does not depend on the model complying."""
    monkeypatch.setattr(gemini_client, "is_configured", lambda: False)
    result, history = _payload("quantum_kernel")

    facts = qml_ai.explain(result, history)["grounded_on"]

    assert facts["task"] == "classification"
    assert facts["algorithm"] == "quantum_kernel"
    assert facts["evaluation"]["accuracy"] == result["evaluation"]["accuracy"]
    assert facts["baseline"]["model"] == "logistic_regression"
    assert facts["n_epoch_rows"] == 0
