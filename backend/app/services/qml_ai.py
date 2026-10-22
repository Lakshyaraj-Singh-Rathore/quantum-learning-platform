"""Gemini-backed explanation of a finished QML Lab experiment.

The model explains numbers it is given. It never computes any, and it never
reaches the database: the caller loads the experiment, this module renders
the stored payload into a prompt, and the reply is returned as prose beside
the same numbers the UI already shows.

**Grounding is structural, not a request.** §2F.2: an LLM asked to "explain
this result" will invent figures that sound right. Three things make that
visible rather than authoritative, and none of them is a politely worded
instruction:

1. ``build_prompt`` renders every number from the stored result, so the
   model is never asked to recall one. ``tests/test_qml_ai.py`` asserts the
   exact figures appear in the prompt string.
2. ``explain`` returns ``grounded_on`` -- the same facts, structured -- so
   the UI can print them next to the prose. A fabricated accuracy sits
   directly above the real one.
3. The system instruction forbids introducing values that were not supplied.

Only (3) depends on the model complying. (1) and (2) hold whatever it says.

Following ``services/codelab_ai.py`` for shape: a module-level ``_SYSTEM``,
a ``MAX_PROMPT_CHARS`` ceiling that **rejects** rather than truncates, and a
thin wrapper over ``ai.gemini_client``.
"""

from __future__ import annotations

from typing import Any

from app.ai import gemini_client

#: Reject anything larger rather than truncating. Truncation is the wrong
#: failure here: the tail of the prompt is the epoch history and the
#: baseline, so a silent cut removes exactly the numbers being grounded on
#: and leaves the model free to invent replacements. Larger than Code Lab's
#: 2,000 because this prompt embeds a whole result payload rather than one
#: sentence of user text; a 30-epoch run renders to roughly 3.5 kB.
MAX_PROMPT_CHARS = 8_000

#: Lower than the platform default of 1.0. The entire risk of this feature
#: is confabulation, and `generate()` hardcoded 1.0 for chat. Passed as a
#: keyword so no existing caller changes (§2F.2).
EXPLAIN_TEMPERATURE = 0.2

_SYSTEM = """\
You explain quantum machine learning results to a student on a teaching
platform. Every number you need is supplied to you.

Hard requirements:
- NEVER introduce a numeric value that is not in the data given to you. Do
  not estimate, round differently, extrapolate, or recall figures from
  elsewhere. If a quantity was not supplied, say it was not measured.
- Do not invent metrics the task does not have. A regression run has no
  accuracy; a classification run has no R squared.
- Quote numbers exactly as given, to the same precision.
- Be honest when the result is poor. A quantum model losing to the
  classical baseline is a normal and interesting outcome, not a failure to
  explain away. A negative R squared means worse than predicting the mean.
- Do not claim quantum advantage. These are small simulated circuits.
- No markdown headings. Two or three short paragraphs, plain prose.
- Address the student directly and plainly.
"""


def _fmt(value: Any) -> str:
    """Render a number the way the prompt and the UI both quote it.

    Four decimals for floats, so "0.7778" is a stable literal a test can
    assert on. Integers stay integers so "18 samples" does not read "18.0".
    """
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _metric_lines(evaluation: dict[str, Any]) -> list[str]:
    """Only the metrics this task actually has.

    Driven by what the payload contains rather than a per-task list, for the
    same reason the UI is (§2E.0): naming metrics here would be a third
    place that has to learn about a new task.
    """
    lines = []
    for key, value in evaluation.items():
        if key == "confusion_matrix":
            lines.append(f"- confusion matrix (rows = actual, cols = predicted): {value}")
        elif key == "n_samples":
            continue
        else:
            lines.append(f"- {key}: {_fmt(value)}")
    return lines


def collect_facts(result: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    """The exact figures handed to the model, structured for the UI.

    Returned to the client as ``grounded_on`` so the prose can be checked
    against it without a round trip. This is the half of grounding that does
    not depend on the model behaving.
    """
    evaluation = result.get("evaluation") or {}
    baseline = result.get("baseline") or {}
    dataset = result.get("dataset") or {}
    circuit = result.get("circuit") or {}

    return {
        "task": result.get("task"),
        "algorithm": result.get("algorithm"),
        "dataset": {
            "name": dataset.get("name"),
            "n_train": dataset.get("n_train"),
            "n_test": dataset.get("n_test"),
            "n_features": dataset.get("n_features"),
        },
        "circuit": {
            "n_qubits": circuit.get("n_qubits"),
            "n_layers": circuit.get("n_layers"),
            "n_parameters": circuit.get("n_parameters"),
            "encoding": circuit.get("encoding"),
        },
        "evaluation": evaluation,
        "baseline": baseline,
        "epochs_completed": result.get("epochs_completed"),
        "n_epoch_rows": len(history),
    }


def build_prompt(result: dict[str, Any], history: list[dict[str, Any]]) -> str:
    """Render the stored payload into the prompt, numbers and all.

    Deterministic and side-effect free so a test can assert on the exact
    string. Nothing is summarised away: if it is too long, ``explain``
    refuses rather than dropping the tail.
    """
    evaluation = result.get("evaluation") or {}
    baseline = result.get("baseline") or {}
    dataset = result.get("dataset") or {}
    circuit = result.get("circuit") or {}
    kernel = result.get("kernel") or {}

    task = result.get("task", "unknown")
    algorithm = result.get("algorithm", "unknown")

    blocks: list[str] = []

    blocks.append(
        "EXPERIMENT\n"
        f"- algorithm: {algorithm}\n"
        f"- task: {task}\n"
        f"- dataset: {dataset.get('name')} "
        f"({dataset.get('n_train')} train / {dataset.get('n_test')} test samples, "
        f"{dataset.get('n_features')} feature(s))"
    )

    circuit_bits = [
        f"- qubits: {circuit.get('n_qubits')}",
        f"- encoding: {circuit.get('encoding')}",
    ]
    if circuit.get("n_layers") is not None:
        circuit_bits.insert(1, f"- layers: {circuit.get('n_layers')}")
    if circuit.get("n_parameters") is not None:
        circuit_bits.append(f"- trainable parameters: {circuit.get('n_parameters')}")
    if circuit.get("data_reuploading"):
        circuit_bits.append(
            f"- data re-uploading: yes, max frequency {circuit.get('max_frequency')}"
        )
    blocks.append("CIRCUIT\n" + "\n".join(circuit_bits))

    if evaluation:
        blocks.append(
            f"TEST METRICS (held-out, {evaluation.get('n_samples')} samples)\n"
            + "\n".join(_metric_lines(evaluation))
        )

    if baseline:
        name = baseline.get("model", "baseline")
        rest = [f"- {k}: {_fmt(v)}" for k, v in baseline.items() if k != "model"]
        blocks.append(f"CLASSICAL BASELINE ({name})\n" + "\n".join(rest))

    if kernel:
        evaluations = kernel.get("evaluations") or {}
        blocks.append(
            "KERNEL\n"
            f"- classifier: {kernel.get('classifier')}\n"
            f"- support vectors: {kernel.get('n_support')}\n"
            f"- kernel evaluations actually computed: {evaluations.get('total')}\n"
            f"- naive full matrix would need: {evaluations.get('naive_full_matrix')}\n"
            "- solved in closed form; there is no training loop and no epochs"
        )

    if history:
        rows = [
            "epoch "
            + str(row.get("epoch"))
            + ": "
            + " ".join(
                f"{key}={_fmt(value)}"
                for key, value in row.items()
                if key not in {"epoch", "elapsed_seconds"} and value is not None
            )
            for row in history
        ]
        blocks.append(f"EPOCH HISTORY ({len(history)} epochs)\n" + "\n".join(rows))
    else:
        blocks.append(
            "EPOCH HISTORY\n"
            "- none. This algorithm has no training loop, so zero epoch rows is "
            "the correct outcome and not missing data."
        )

    blocks.append(
        "TASK\n"
        "Explain to the student what this result means, whether the quantum "
        "model beat the classical baseline, and what the configuration had to "
        "do with it. Use only the numbers above."
    )

    return "\n\n".join(blocks)


def offline_explanation(facts: dict[str, Any]) -> str:
    """Useful, honest text when no key is configured.

    Follows ``ai/chat.py:_offline_reply``: say what is missing, then give
    the thing that still works. Most checkouts and all of CI run this path,
    so it is a real feature rather than an error string (§2F.4).
    """
    evaluation = facts.get("evaluation") or {}
    baseline = facts.get("baseline") or {}

    lines = [
        "AI explanation is not configured (no GEMINI_API_KEY), so here is the "
        "measured comparison on its own:",
        "",
    ]

    if evaluation:
        lines.append("Your model, on the held-out test set:")
        lines += [f"  {k}: {_fmt(v)}" for k, v in evaluation.items() if k != "confusion_matrix"]
    if baseline:
        lines.append("")
        lines.append(f"The classical baseline ({baseline.get('model', 'baseline')}):")
        lines += [f"  {k}: {_fmt(v)}" for k, v in baseline.items() if k != "model"]

    lines.append("")
    lines.append(
        "Compare the two on the same metric. A quantum model that loses to the "
        "baseline on a small simulated circuit is a normal result."
    )
    return "\n".join(lines)


def explain(result: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    """Explain one finished experiment.

    Never raises for an unconfigured key and never lets a Gemini failure
    escape as a 500: both come back as a payload with ``configured`` or
    ``error`` set, because the UI renders them as states rather than
    exceptions. ``GeminiUnavailable`` is the one exception the route is
    expected to translate, so it is re-raised (§2F.4).
    """
    facts = collect_facts(result, history)
    prompt = build_prompt(result, history)

    if len(prompt) > MAX_PROMPT_CHARS:
        raise ValueError(
            f"experiment summary is {len(prompt)} characters "
            f"(maximum {MAX_PROMPT_CHARS}); too long to explain without "
            "dropping the numbers it would be explaining"
        )

    if not gemini_client.is_configured():
        return {
            "configured": False,
            "explanation": offline_explanation(facts),
            "grounded_on": facts,
        }

    reply = gemini_client.generate(
        prompt,
        system_instruction=_SYSTEM,
        temperature=EXPLAIN_TEMPERATURE,
    )
    return {"configured": True, "explanation": reply.strip(), "grounded_on": facts}


__all__ = [
    "explain",
    "build_prompt",
    "collect_facts",
    "offline_explanation",
    "MAX_PROMPT_CHARS",
    "EXPLAIN_TEMPERATURE",
]
