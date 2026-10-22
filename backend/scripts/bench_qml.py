"""Benchmark the QML Lab engine and derive resource limits from the result.

    python scripts/bench_qml.py --quick          # ~2 minutes
    python scripts/bench_qml.py --full           # ~20-40 minutes
    python scripts/bench_qml.py --quick --json out.json --md out.md

Run it from ``backend/`` with ``PYTHONPATH=.``; on Windows PowerShell use
``;`` to chain, never ``&&``.

----------------------------------------------------------------------------
Why this script exists in this shape
----------------------------------------------------------------------------

**It measures the engine directly.** Not through FastAPI, not through Celery
in eager mode. Eager mode folds request validation, DB writes and task
serialisation into the number; that overhead is real but it is a *different*
measurement, and averaging it into a scaling curve makes the curve mean
nothing.

**It reports a median and a spread over N repetitions**, discarding a warm-up
run. The first PennyLane call in a process pays import, tracing and cache
costs that no later call pays, so a single timing is systematically wrong in
a direction that flatters nothing.

**It separates what is portable from what is not.** Wall-clock seconds
measured in a Linux container do not transfer to an i5-13450HX laptop running
Windows. What does transfer is the *shape*: the exponent on the scaling curve,
the ratio between gradient methods, and the closed-form execution count, which
is a property of the algorithm rather than the machine. The JSON is designed
so a user can run this on the target machine and have the absolute numbers
fall out, with the laws already established.

**It never tunes a limit from a crashed run.** A configuration that is killed
is a data point about the ceiling, not a timing, and is recorded as such.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import resource
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

# Importing the real engine is the whole point: a benchmark of a
# reimplementation measures the reimplementation.
_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import numpy as np  # noqa: E402
import pennylane as qml  # noqa: E402
from pennylane import numpy as pnp  # noqa: E402

from app.quantum.qml_lab import limits  # noqa: E402
from app.quantum.qml_lab.datasets import build_dataset  # noqa: E402
from app.quantum.qml_lab.models import (  # noqa: E402
    CircuitConfig,
    DatasetConfig,
    QmlExperimentConfig,
    TrainingConfig,
)
from app.quantum.qml_lab.trainer import square_loss, train  # noqa: E402
from app.quantum.qml_lab.vqc import VQC  # noqa: E402

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


def cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def total_ram_gib() -> float | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal"):
                return round(int(line.split()[1]) / 1024 / 1024, 2)
    except OSError:
        pass
    try:  # Windows / macOS fallback
        import psutil  # type: ignore

        return round(psutil.virtual_memory().total / 1024**3, 2)
    except Exception:
        return None


def environment() -> dict[str, Any]:
    import scipy

    try:
        from importlib.metadata import version as _v

        lightning = _v("pennylane-lightning")
    except Exception:
        lightning = None

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "os": f"{platform.system()} {platform.release()}",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_model": cpu_model(),
        "cpu_count": os.cpu_count(),
        "total_ram_gib": total_ram_gib(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "pennylane": qml.__version__,
        "pennylane_lightning": lightning,
        "shots": None,  # every measurement below is analytic
        "measured_through": "engine-direct (no FastAPI, no Celery)",
    }


# ---------------------------------------------------------------------------
# Closed-form predictions — computed before anything is measured
# ---------------------------------------------------------------------------


def n_circuit_parameters(n_qubits: int, n_layers: int) -> int:
    """RY+RZ per wire per layer. The bias is classical and is excluded."""
    return limits.n_parameters(n_qubits, n_layers)


def predicted_executions_per_step(n_qubits: int, n_layers: int, batch: int, diff_method: str) -> int:
    """Circuit executions for one gradient step.

    ``decision_values`` loops one QNode call per sample — there is no
    parameter broadcasting — so the batch multiplies everything.

    * backprop differentiates through the simulated state in a single pass,
      so the cost is one execution per sample.
    * parameter-shift evaluates each circuit parameter twice, plus the forward
      value: ``batch * (2P + 1)``.
    """
    p = n_circuit_parameters(n_qubits, n_layers)
    if diff_method == "backprop":
        return batch
    return batch * (2 * p + 1)


def state_bytes(n_qubits: int, density_matrix: bool = False) -> int:
    """complex128 state size. 2^n for a state vector, 4^n for a density matrix."""
    amplitudes = (4**n_qubits) if density_matrix else (2**n_qubits)
    return amplitudes * 16


def steps_for(n_samples: int, test_fraction: float, batch_size: int, epochs: int) -> dict[str, int]:
    n_train = int(round(n_samples * (1.0 - test_fraction)))
    batches = max(1, math.ceil(n_train / batch_size))
    return {"n_train": n_train, "batches_per_epoch": batches, "steps": batches * epochs}


def predictions() -> dict[str, Any]:
    """The arithmetic §2B.3 requires before any measurement."""
    max_cfg = {
        "n_qubits": limits.MAX_QUBITS,
        "n_layers": limits.MAX_LAYERS,
        "n_samples": limits.MAX_SAMPLES,
        "batch_size": limits.MAX_BATCH_SIZE,
        "epochs": limits.MAX_EPOCHS,
        "test_fraction": 0.3,
    }
    sched = steps_for(
        max_cfg["n_samples"], max_cfg["test_fraction"], max_cfg["batch_size"], max_cfg["epochs"]
    )
    p = n_circuit_parameters(max_cfg["n_qubits"], max_cfg["n_layers"])
    per_step = {
        dm: predicted_executions_per_step(
            max_cfg["n_qubits"], max_cfg["n_layers"], max_cfg["batch_size"], dm
        )
        for dm in ("backprop", "parameter-shift")
    }
    return {
        "max_config": max_cfg,
        "schedule": sched,
        "circuit_parameters_at_max": p,
        "parameters_formula": "P = 2 * n_qubits * n_layers  (RY+RZ per wire per layer; bias is classical)",
        "executions_per_step": per_step,
        "executions_per_step_formula": {
            "backprop": "B",
            "parameter-shift": "B * (2P + 1)",
        },
        # Gradient-step executions only. Uses n_train directly rather than
        # steps*batch: the trainer's last batch of each epoch is partial
        # (trainer.py:191 slices, it does not pad), so exactly n_train samples
        # are differentiated per epoch.
        "gradient_executions_max_run": {
            dm: max_cfg["epochs"] * sched["n_train"] * (1 if dm == "backprop" else 1 + 2 * p)
            for dm in per_step
        },
        # trainer.py:220-221 evaluates BOTH splits at the end of EVERY epoch,
        # forward-only, so the cost is the same for either gradient method.
        "evaluation_executions_max_run": max_cfg["epochs"] * max_cfg["n_samples"],
        "total_executions_max_run": {
            dm: max_cfg["epochs"] * sched["n_train"] * (1 if dm == "backprop" else 1 + 2 * p)
            + max_cfg["epochs"] * max_cfg["n_samples"]
            for dm in per_step
        },
        "total_formula": "epochs*n_train*per_sample + epochs*n_samples",
        "ratio_pshift_over_backprop": per_step["parameter-shift"] / per_step["backprop"],
        "ratio_formula": "2P + 1  (per gradient step; the evaluation pass is method-independent)",
        "memory": {
            "statevector_max_qubits_bytes": state_bytes(limits.MAX_QUBITS),
            "density_matrix_cap_bytes": state_bytes(limits.DENSITY_MATRIX_MAX_QUBITS, True),
            "note": (
                "Both are kilobytes. Raw state size is not the constraint at these qubit "
                "counts; the constraint is the number of circuit executions."
            ),
        },
    }


# ---------------------------------------------------------------------------
# Timing harness
# ---------------------------------------------------------------------------


@dataclass
class Timing:
    label: str
    n_qubits: int
    n_layers: int
    batch: int
    diff_method: str
    device: str
    reps: int
    median_s: float | None = None
    min_s: float | None = None
    max_s: float | None = None
    stdev_s: float | None = None
    executions_measured: int | None = None
    executions_predicted: int | None = None
    forward_per_sample_s: float | None = None
    peak_rss_mib: float | None = None
    status: str = "ok"
    note: str = ""


def peak_rss_mib() -> float:
    """Peak RSS of THIS process. Linux reports kB, macOS reports bytes."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(raw / 1024, 1) if sys.platform != "darwin" else round(raw / 1024**2, 1)


def time_it(fn: Callable[[], Any], reps: int) -> tuple[list[float], Any]:
    """Run `fn` once as warm-up (discarded), then `reps` timed repetitions."""
    out = fn()  # warm-up: pays import, tracing and cache costs no later call pays
    samples: list[float] = []
    for _ in range(reps):
        t0 = time.perf_counter()
        out = fn()
        samples.append(time.perf_counter() - t0)
    return samples, out


def make_gradient_step(
    n_qubits: int, n_layers: int, batch: int, diff_method: str, device: str, seed: int = 7
):
    """One Adam-free gradient evaluation, exactly as the trainer computes it."""
    cfg = CircuitConfig(n_qubits=n_qubits, n_layers=n_layers, rotation="Y", entanglement="ring")
    model = VQC(cfg, n_features=2, diff_method=diff_method)
    if device != "default.qubit":
        # Swap the device but keep everything else identical, so the only
        # variable is the simulator.
        model.device = qml.device(device, wires=n_qubits)
        model._qnode = model._build_qnode()  # noqa: SLF001 - deliberate, see report

    rng = np.random.default_rng(seed)
    p = n_circuit_parameters(n_qubits, n_layers)
    theta = pnp.array(rng.normal(scale=0.1, size=p + 1), requires_grad=True)
    x = rng.uniform(0.0, np.pi, size=(batch, 2))
    y = np.where(rng.random(batch) > 0.5, 1.0, -1.0)

    def cost(t):
        return square_loss(model.decision_values(x, t), y)

    grad_fn = qml.grad(cost, argnums=0)
    # Forward-only pass over the same batch. The trainer runs one of these over
    # BOTH splits at the end of every epoch (trainer.py:220-221), and under
    # backprop that evaluation is the majority of all circuit executions, so a
    # projection built from gradient steps alone understates the wall clock.
    forward = lambda: model.decision_values(x, np.asarray(theta, dtype=float))  # noqa: E731
    return model, (lambda: grad_fn(theta)), forward


def bench_cell(
    n_qubits: int,
    n_layers: int,
    batch: int,
    diff_method: str,
    device: str,
    reps: int,
    budget_s: float,
) -> Timing:
    t = Timing(
        label=f"{n_qubits}q/{n_layers}L/B{batch}/{diff_method}/{device}",
        n_qubits=n_qubits,
        n_layers=n_layers,
        batch=batch,
        diff_method=diff_method,
        device=device,
        reps=reps,
        executions_predicted=predicted_executions_per_step(n_qubits, n_layers, batch, diff_method),
    )
    try:
        model, step, forward = make_gradient_step(n_qubits, n_layers, batch, diff_method, device)
    except Exception as exc:  # unsupported device/diff_method combination
        t.status = "unsupported"
        t.note = f"{type(exc).__name__}: {str(exc)[:160]}"
        return t

    # One untimed probe first: if a single step already blows the budget,
    # record the fact and skip the repetitions rather than stalling the run.
    try:
        t0 = time.perf_counter()
        with qml.Tracker(model.device) as tracker:
            step()
        probe = time.perf_counter() - t0
        t.executions_measured = int(tracker.totals.get("executions", 0))
    except Exception as exc:
        t.status = "error"
        t.note = f"{type(exc).__name__}: {str(exc)[:160]}"
        return t

    if probe > budget_s:
        t.status = "over-budget"
        t.median_s = round(probe, 4)
        t.note = f"single step took {probe:.2f}s > budget {budget_s}s; repetitions skipped"
        t.peak_rss_mib = peak_rss_mib()
        return t

    fwd, _ = time_it(forward, reps)
    t.forward_per_sample_s = round(statistics.median(fwd) / batch, 8)

    samples, _ = time_it(step, reps)
    t.median_s = round(statistics.median(samples), 6)
    t.min_s = round(min(samples), 6)
    t.max_s = round(max(samples), 6)
    t.stdev_s = round(statistics.stdev(samples), 6) if len(samples) > 1 else 0.0
    t.peak_rss_mib = peak_rss_mib()
    return t


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def determinism_check() -> dict[str, Any]:
    """Same seed twice must give bit-identical gradients."""
    results = []
    for seed in (11, 12):
        _, step, _fwd = make_gradient_step(3, 2, 8, "backprop", "default.qubit", seed=seed)
        results.append(np.asarray(step(), dtype=float))
    _, step_a, _fa = make_gradient_step(3, 2, 8, "backprop", "default.qubit", seed=11)
    repeat = np.asarray(step_a(), dtype=float)
    return {
        "same_seed_bit_identical": bool(np.array_equal(results[0], repeat)),
        "different_seeds_differ": bool(not np.array_equal(results[0], results[1])),
        "max_abs_delta_same_seed": float(np.max(np.abs(results[0] - repeat))),
    }


def gradient_agreement() -> dict[str, Any]:
    """backprop and parameter-shift must agree — the Phase 1 invariant, re-checked
    here because every timing comparison below assumes they compute the same thing."""
    out = {}
    grads = {}
    for dm in ("backprop", "parameter-shift"):
        _, step, _fwd = make_gradient_step(3, 2, 6, dm, "default.qubit", seed=5)
        grads[dm] = np.asarray(step(), dtype=float)
    delta = float(np.max(np.abs(grads["backprop"] - grads["parameter-shift"])))
    out["max_abs_difference"] = delta
    out["agree_to_1e-9"] = delta < 1e-9
    return out


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def estimator_validation() -> dict[str, Any]:
    """Count a REAL training run and compare it to ``limits.estimate_cost``.

    Everything else in this file measures a single gradient step in isolation.
    This runs the shipped trainer end to end under ``qml.Tracker`` so the
    comparison is against the estimator the product actually ships, not
    against my own arithmetic.

    It exists because the two disagree. ``estimate_cost`` charges one forward
    pass over the dataset for evaluation (``eval_execs = n_samples``), but
    ``trainer.train`` evaluates *both* splits at the end of *every* epoch
    (trainer.py:220-221), which is ``epochs * n_samples`` forward executions.
    """
    out: list[dict[str, Any]] = []
    for diff_method in ("backprop", "parameter-shift"):
        cfg = QmlExperimentConfig(
            dataset=DatasetConfig(name="moons", n_samples=60, noise=0.1, test_fraction=0.3),
            circuit=CircuitConfig(n_qubits=2, n_layers=1, rotation="Y", entanglement="ring"),
            training=TrainingConfig(
                epochs=3, batch_size=16, learning_rate=0.1, diff_method=diff_method
            ),
            seed=1234,
        )
        rng = np.random.default_rng(cfg.seed)
        data = build_dataset(cfg.dataset, rng)
        model = VQC(cfg.circuit, n_features=data.x_train.shape[1], diff_method=diff_method)
        initial = model.initialise(rng)

        with qml.Tracker(model.device) as tracker:
            train(model, data, cfg.training, rng, initial)
        measured = int(tracker.totals.get("executions", 0))

        shipped = int(limits.estimate_cost(cfg)["circuit_executions"])

        n_train = int(data.x_train.shape[0])
        n_all = n_train + int(data.x_test.shape[0])
        per_sample = 1 + 2 * n_circuit_parameters(cfg.circuit.n_qubits, cfg.circuit.n_layers)
        per_sample = per_sample if diff_method == "parameter-shift" else 1
        corrected = cfg.training.epochs * n_train * per_sample + cfg.training.epochs * n_all

        out.append(
            {
                "diff_method": diff_method,
                "config": f"{cfg.circuit.n_qubits}q/{cfg.circuit.n_layers}L/"
                f"B{cfg.training.batch_size}/{cfg.training.epochs}ep/{n_all} samples",
                "measured_executions": measured,
                "limits_estimate_cost": shipped,
                "corrected_closed_form": corrected,
                "corrected_formula": "epochs*n_train*per_sample + epochs*n_samples",
                "shipped_estimate_matches": measured == shipped,
                "corrected_matches": measured == corrected,
                "shipped_understates_by": measured - shipped,
            }
        )
    return {
        "note": (
            "limits.estimate_cost charges one evaluation pass; trainer.train evaluates "
            "both splits every epoch. The shortfall is (epochs-1)*n_samples executions."
        ),
        "cases": out,
    }


def project_full_run(cell: Timing, n_samples: int, test_fraction: float, epochs: int) -> dict[str, Any]:
    """Extrapolate a measured per-step time to a complete training run."""
    sched = steps_for(n_samples, test_fraction, cell.batch, epochs)
    if cell.median_s is None:
        return {"status": cell.status, "note": cell.note}

    # Gradient time. steps*batch slightly overcounts (the trainer's final batch
    # of each epoch is partial), so scale by the true per-epoch sample count.
    per_sample_grad = cell.median_s / cell.batch
    gradient_s = per_sample_grad * sched["n_train"] * epochs

    # Evaluation time: both splits, every epoch, forward-only.
    eval_s = (cell.forward_per_sample_s or 0.0) * n_samples * epochs

    total = gradient_s + eval_s
    return {
        "family": cell.label.split(":")[0] if ":" in cell.label else "",
        "at_max_config": cell.n_qubits == limits.MAX_QUBITS and cell.n_layers == limits.MAX_LAYERS,
        "config": f"{cell.n_qubits}q/{cell.n_layers}L/B{cell.batch}/{cell.diff_method}/{cell.device}",
        "per_step_s": cell.median_s,
        "steps": sched["steps"],
        "gradient_seconds": round(gradient_s, 1),
        "evaluation_seconds": round(eval_s, 1),
        "evaluation_share": round(eval_s / total, 3) if total else None,
        "projected_seconds": round(total, 1),
        "projected_minutes": round(total / 60, 1),
        "projected_hours": round(total / 3600, 2),
    }


# ---------------------------------------------------------------------------
# Grids
# ---------------------------------------------------------------------------

def _projections_from_cells(cells: list[Timing]) -> list[dict[str, Any]]:
    """Project a full run at the maximum allowed configuration.

    Only cells that actually sit at ``MAX_QUBITS x MAX_LAYERS`` answer the
    question §2B.4 asks ("how long does the worst allowed job take?"). If the
    grid never reached there — ``--quick`` does not — fall back to the largest
    cell measured and flag it, so nobody derives a timeout from a small cell
    and believes it covers the maximum.
    """
    ok = [c for c in cells if c.status == "ok" and c.median_s is not None]
    if not ok:
        return []
    at_max = [c for c in ok if c.n_qubits == limits.MAX_QUBITS and c.n_layers == limits.MAX_LAYERS]
    chosen = at_max
    if not chosen:
        top = max(ok, key=lambda c: (c.n_qubits, c.n_layers))
        chosen = [
            c for c in ok if (c.n_qubits, c.n_layers) == (top.n_qubits, top.n_layers)
        ]
    return [project_full_run(c, limits.MAX_SAMPLES, 0.3, limits.MAX_EPOCHS) for c in chosen]


QUICK_GRID = {
    "qubit_scaling": [(q, 2, 8) for q in (2, 3, 4, 5, 6)],
    "layer_scaling": [(4, L, 8) for L in (1, 2, 3, 4)],
    "batch_scaling": [(4, 2, b) for b in (4, 8, 16, 32)],
    "reps": 5,
    "budget_s": 20.0,
    "devices": ["default.qubit", "lightning.qubit"],
}

FULL_GRID = {
    "qubit_scaling": [(q, 2, 16) for q in (2, 3, 4, 5, 6, 7, 8)],
    "layer_scaling": [(8, L, 16) for L in (1, 2, 3, 4)],
    "batch_scaling": [(8, 4, b) for b in (4, 8, 16, 32)],
    "reps": 5,
    "budget_s": 120.0,
    "devices": ["default.qubit", "lightning.qubit"],
}


def run(grid: dict[str, Any], mode: str) -> dict[str, Any]:
    env = environment()
    pred = predictions()

    print(f"[bench] mode={mode}  reps={grid['reps']}  budget={grid['budget_s']}s", file=sys.stderr)
    print(f"[bench] {env['cpu_model']} / {env['cpu_count']} cores / {env['total_ram_gib']} GiB", file=sys.stderr)

    cells: list[Timing] = []
    for family in ("qubit_scaling", "layer_scaling", "batch_scaling"):
        for (q, L, b) in grid[family]:
            for dm in ("backprop", "parameter-shift"):
                for dev in grid["devices"]:
                    # backprop needs a differentiable simulator; lightning is
                    # a C++ statevector and cannot provide one. Skip rather
                    # than record a misleading "unsupported" for every cell.
                    if dev != "default.qubit" and dm == "backprop":
                        continue
                    c = bench_cell(q, L, b, dm, dev, grid["reps"], grid["budget_s"])
                    c.label = f"{family}:{c.label}"
                    cells.append(c)
                    flag = "" if c.status == "ok" else f"  [{c.status}]"
                    print(
                        f"[bench]   {c.label:<52s} {('%.4fs' % c.median_s) if c.median_s else '-':>10s}"
                        f"  exec={c.executions_measured}{flag}",
                        file=sys.stderr,
                    )

    ok = [c for c in cells if c.status == "ok"]
    law_ok = all(
        c.executions_measured == c.executions_predicted
        for c in cells
        if c.executions_measured is not None
    )

    projections = _projections_from_cells(ok)

    return {
        "mode": mode,
        "environment": env,
        "predictions": pred,
        "execution_law_verified": law_ok,
        "determinism": determinism_check(),
        "gradient_agreement": gradient_agreement(),
        "estimator_validation": estimator_validation(),
        "cells": [asdict(c) for c in cells],
        "projections": projections,
        "peak_rss_mib_process": peak_rss_mib(),
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def to_markdown(r: dict[str, Any]) -> str:
    env = r["environment"]
    p = r["predictions"]
    lines: list[str] = []
    a = lines.append

    a(f"# QML Lab benchmark — `{r['mode']}`\n")
    a(f"Generated {env['timestamp_utc']} by `backend/scripts/bench_qml.py`.\n")

    a("## Machine\n")
    a("| field | value |")
    a("|---|---|")
    for k in ("os", "cpu_model", "cpu_count", "total_ram_gib", "python", "numpy", "scipy",
              "pennylane", "pennylane_lightning", "shots", "measured_through"):
        a(f"| {k} | {env.get(k)} |")
    a("")

    a("## Predicted cost at the maximum allowed configuration\n")
    mc = p["max_config"]
    a(f"`{mc['n_qubits']}` qubits x `{mc['n_layers']}` layers, "
      f"`{mc['n_samples']}` samples, batch `{mc['batch_size']}`, `{mc['epochs']}` epochs.\n")
    a(f"- Circuit parameters: **{p['circuit_parameters_at_max']}** — `{p['parameters_formula']}`")
    a(f"- Train split {p['schedule']['n_train']} -> {p['schedule']['batches_per_epoch']} batches/epoch "
      f"-> **{p['schedule']['steps']} gradient steps**")
    a(f"- Executions per step: backprop `{p['executions_per_step']['backprop']}`, "
      f"parameter-shift `{p['executions_per_step']['parameter-shift']}` "
      f"(`{p['executions_per_step_formula']['parameter-shift']}`)")
    a(f"- Gradient executions: backprop **{p['gradient_executions_max_run']['backprop']:,}**, "
      f"parameter-shift **{p['gradient_executions_max_run']['parameter-shift']:,}**")
    a(f"- Per-epoch evaluation of both splits (method-independent): "
      f"**{p['evaluation_executions_max_run']:,}**")
    a(f"- Total for a full run (`{p['total_formula']}`): "
      f"backprop **{p['total_executions_max_run']['backprop']:,}**, "
      f"parameter-shift **{p['total_executions_max_run']['parameter-shift']:,}**")
    a(f"- Ratio: **{p['ratio_pshift_over_backprop']:.0f}x** (`{p['ratio_formula']}`)")
    a(f"- Statevector at {mc['n_qubits']} qubits: **{p['memory']['statevector_max_qubits_bytes']:,} bytes**; "
      f"density matrix at the cap: **{p['memory']['density_matrix_cap_bytes']:,} bytes**")
    a(f"\n> {p['memory']['note']}\n")

    verdict = "MATCHED exactly" if r["execution_law_verified"] else "DID NOT MATCH"
    a(f"**Measured execution counts {verdict}** against the closed form.\n")

    a("## Timings\n")
    a("| cell | device | method | median s | min | max | stdev | exec (measured) | exec (pred) | status |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for c in r["cells"]:
        fmt = lambda v: f"{v:.4f}" if isinstance(v, float) else (v if v is not None else "-")  # noqa: E731
        a(f"| {c['label']} | {c['device']} | {c['diff_method']} | {fmt(c['median_s'])} | "
          f"{fmt(c['min_s'])} | {fmt(c['max_s'])} | {fmt(c['stdev_s'])} | "
          f"{c['executions_measured']} | {c['executions_predicted']} | {c['status']} |")
    a("")

    a("## Correctness invariants\n")
    d, g = r["determinism"], r["gradient_agreement"]
    a(f"- Same seed is bit-identical: **{d['same_seed_bit_identical']}** "
      f"(max delta {d['max_abs_delta_same_seed']:.3e})")
    a(f"- Different seeds differ: **{d['different_seeds_differ']}**")
    a(f"- backprop vs parameter-shift agree to 1e-9: **{g['agree_to_1e-9']}** "
      f"(max delta {g['max_abs_difference']:.3e})\n")

    ev = r["estimator_validation"]
    a("## `limits.estimate_cost` against a real training run\\n".replace("\\n", "\n"))
    a("| method | config | measured | `estimate_cost` | matches | corrected form | matches |")
    a("|---|---|---|---|---|---|---|")
    for c in ev["cases"]:
        a(f"| {c['diff_method']} | {c['config']} | {c['measured_executions']:,} | "
          f"{c['limits_estimate_cost']:,} | {c['shipped_estimate_matches']} | "
          f"{c['corrected_closed_form']:,} | {c['corrected_matches']} |")
    a(f"\n> {ev['note']}\n")

    if r["projections"]:
        a("## Projected full-run wall clock (this machine)\n")
        at_max = all(pr.get("at_max_config") for pr in r["projections"])
        if not at_max:
            a("> **This grid never reached the maximum allowed configuration.** The rows below "
              "are the largest cell measured and are a LOWER BOUND on the worst allowed job. "
              "Do not derive a timeout from them — use `--full`.\n")
        a("| family | config | per step s | steps | gradient s | eval s | eval share | total min | total h |")
        a("|---|---|---|---|---|---|---|---|---|")
        for pr in r["projections"]:
            if "projected_seconds" in pr:
                a(f"| {pr.get('family','')} | {pr['config']} | {pr['per_step_s']:.4f} | {pr['steps']} | "
                  f"{pr['gradient_seconds']} | {pr['evaluation_seconds']} | "
                  f"{pr['evaluation_share']} | {pr['projected_minutes']} | {pr['projected_hours']} |")
        a("")
        a("> These are **this machine's** seconds. Only the shape transfers; "
          "re-run on the target to set a timeout.\n")

    a(f"Peak RSS of the benchmark process: **{r['peak_rss_mib_process']} MiB**.\n")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--quick", action="store_true", help="small grid, ~2 minutes (default)")
    g.add_argument("--full", action="store_true", help="the full grid up to the allowed maxima")
    ap.add_argument("--json", type=Path, default=None, help="write machine-readable results here")
    ap.add_argument("--md", type=Path, default=None, help="write a markdown table here")
    ap.add_argument("--reps", type=int, default=None, help="override repetition count")
    ap.add_argument(
        "--reproject",
        type=Path,
        default=None,
        help="recompute the projections from a saved results JSON and rewrite the "
        "reports, without re-measuring anything",
    )
    args = ap.parse_args()

    if args.reproject:
        results = json.loads(args.reproject.read_text(encoding="utf-8"))
        cells = [Timing(**c) for c in results["cells"]]
        results["projections"] = _projections_from_cells(cells)
        target_json = args.json or args.reproject
        target_json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"[bench] reprojected -> {target_json}", file=sys.stderr)
        if args.md:
            args.md.write_text(to_markdown(results), encoding="utf-8")
            print(f"[bench] wrote {args.md}", file=sys.stderr)
        return 0

    mode = "full" if args.full else "quick"
    grid = dict(FULL_GRID if args.full else QUICK_GRID)
    if args.reps:
        grid["reps"] = args.reps

    results = run(grid, mode)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        print(f"[bench] wrote {args.json}", file=sys.stderr)
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(to_markdown(results), encoding="utf-8")
        print(f"[bench] wrote {args.md}", file=sys.stderr)
    if not args.json and not args.md:
        print(json.dumps(results, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
