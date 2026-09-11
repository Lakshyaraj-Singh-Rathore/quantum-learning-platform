"""Deterministic circuit inspection.

Used by the AI ``inspect_circuit`` tool, the job submission validator and the
autograder. Contains no LLM calls and no simulation - it is pure analysis.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.config import get_settings
from app.quantum.ir import CircuitIR, Op

#: Backends able to run static circuits.
STATIC_BACKENDS = ["qiskit_aer", "cirq", "pennylane", "qbraid"]
#: Only the Qiskit dynamic engine handles runtime control flow.
DYNAMIC_BACKENDS = ["qiskit_dynamic"]


def compute_run_hash(
    circuit_ir: dict[str, Any],
    backend: str,
    shots: int,
    mode: str,
    noise: dict[str, Any] | None = None,
) -> str:
    """Cache key for a run.

    ``noise`` must participate: two runs of the same circuit with different
    T1/T2/readout are different experiments, and omitting it would serve a
    cached ideal result for a noisy request.
    """
    payload = json.dumps(
        {
            "ir": _strip_ids(circuit_ir),
            "backend": backend,
            "shots": shots,
            "mode": mode,
            "noise": noise or None,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _strip_ids(obj: Any) -> Any:
    """Op ids are random, so exclude them from the cache key."""
    if isinstance(obj, dict):
        return {k: _strip_ids(v) for k, v in obj.items() if k != "id"}
    if isinstance(obj, list):
        return [_strip_ids(v) for v in obj]
    return obj


def gate_histogram(ir: CircuitIR) -> dict[str, int]:
    hist: dict[str, int] = {}
    for op in ir.walk():
        key = op.gate if op.kind == "gate" else op.kind
        if op.kind == "gate" and op.controls:
            key = f"{'mc' if len(op.controls) > 2 else 'c' * len(op.controls)}{op.gate}"
        hist[key] = hist.get(key, 0) + 1
    return hist


def summarize_circuit(ir: CircuitIR) -> dict[str, Any]:
    ops = ir.walk()
    return {
        "name": ir.name,
        "n_qubits": ir.n_qubits,
        "n_clbits": ir.n_clbits,
        "depth": ir.depth(),
        "n_ops": len(ops),
        "is_dynamic": ir.is_dynamic(),
        "has_measurements": ir.has_measurements(),
        "has_mid_circuit_measurement": _has_mid_circuit_measurement(ir),
        "gate_histogram": gate_histogram(ir),
        "control_flow": sorted({o.kind for o in ops if o.kind in {"if", "for", "while", "box"}}),
        "max_controls": max((len(o.controls) for o in ops if o.kind == "gate"), default=0),
        "supported_backends": DYNAMIC_BACKENDS if ir.is_dynamic() else STATIC_BACKENDS,
    }


def _has_mid_circuit_measurement(ir: CircuitIR) -> bool:
    """A measurement is mid-circuit if the qubit is used again afterwards."""
    measured_layers: dict[int, int] = {}
    for op in sorted(ir.ops, key=lambda o: o.layer):
        if op.kind == "measure" and op.qubits:
            measured_layers[op.qubits[0]] = op.layer
    for op in ir.ops:
        if op.kind in {"gate", "reset"}:
            for q in op.involved_qubits():
                if q in measured_layers and op.layer > measured_layers[q]:
                    return True
    # any measurement inside a block is effectively mid-circuit
    nested = [o for o in ir.walk() if o.kind == "measure" and o not in ir.ops]
    return bool(nested)


def inspect_circuit(ir: CircuitIR, backend: str | None = None, shots: int | None = None) -> dict:
    """Return errors/warnings/info for a circuit, optionally against a backend."""
    settings = get_settings()
    errors: list[str] = []
    warnings: list[str] = []
    info: list[str] = []

    summary = summarize_circuit(ir)
    dynamic = summary["is_dynamic"]

    # ---- structural checks
    for layer in range(ir.depth()):
        seen: set[int] = set()
        for op in ir.ops:
            if op.layer != layer:
                continue
            clash = seen & op.involved_qubits()
            if clash:
                errors.append(
                    f"Layer {layer}: qubit(s) {sorted(clash)} carry more than one operation."
                )
            seen |= op.involved_qubits()

    # A classical bit written by two different measurements keeps only the
    # last value. That is legitimate in dynamic circuits (measure, branch,
    # re-measure) but in a static circuit it silently discards a result, and
    # the counts look inexplicably wrong.
    if not dynamic:
        writers: dict[int, list[int]] = {}
        for op in ir.walk():
            if op.kind == "measure":
                for c in op.clbits:
                    writers.setdefault(c, []).extend(op.qubits)
        for cbit, sources in sorted(writers.items()):
            if len(sources) > 1:
                qlist = ", ".join(f"q{q}" for q in sources)
                warnings.append(
                    f"Classical bit c{cbit} is measured into {len(sources)} times "
                    f"({qlist}); only the last measurement survives in the counts."
                )

    # A controlled-X whose control qubit was never touched by anything is
    # almost always a reversed CNOT: the learner meant H(q0) + CX(control=q0,
    # target=q1) but dropped the X on q0 and the control on q1. That produces
    # a separable |00> + |01> instead of a Bell pair, and nothing else in the
    # UI flags it -- the histogram just looks inexplicably wrong.
    if not dynamic:
        touched_before: dict[int, int] = {}
        for op in sorted(ir.ops, key=lambda o: o.layer):
            if op.kind == "gate" and op.controls:
                idle = [
                    c
                    for c in op.controls
                    if touched_before.get(c) is None
                ]
                if idle and len(idle) == len(op.controls):
                    clist = ", ".join(f"q{c}" for c in sorted(idle))
                    tlist = ", ".join(f"q{q}" for q in op.qubits)
                    warnings.append(
                        f"Controlled {(op.gate or '').upper()} at layer {op.layer} is "
                        f"controlled by {clist}, which is still |0> at that point, so "
                        f"the gate never fires and {tlist} is unchanged. Did you mean "
                        f"to swap the control and the target?"
                    )
            if op.kind in {"gate", "measure", "reset"}:
                for q in op.involved_qubits():
                    touched_before.setdefault(q, op.layer)

    if not ir.ops:
        warnings.append("Circuit is empty.")
    if not summary["has_measurements"]:
        warnings.append(
            "No measurements found - counts will be empty. "
            "Use 'Measure All (Append)' before running."
        )

    for op in ir.walk():
        if op.kind == "gate" and op.gate == "swap" and op.controls:
            info.append("Controlled-SWAP (Fredkin) will be decomposed during transpilation.")
        if op.kind == "while":
            info.append(f"While loop is capped at {settings.while_cap} iterations.")
        if op.kind == "for" and (op.loop_n or 0) > 64:
            warnings.append(f"For-loop with N={op.loop_n} will unroll into many operations.")
        if op.kind == "gate" and len(op.controls) > 4:
            warnings.append(
                f"{len(op.controls)}-controlled {op.gate} is expensive after decomposition."
            )

    # ---- execution policy
    if dynamic:
        info.append("Circuit uses runtime control flow - dynamic execution uses the Qiskit engine.")
        if ir.n_qubits > settings.max_dynamic_qubits:
            errors.append(
                f"Dynamic circuits are limited to {settings.max_dynamic_qubits} qubits "
                f"(got {ir.n_qubits})."
            )
        if shots is not None and shots > settings.max_dynamic_shots:
            errors.append(
                f"Dynamic circuits are limited to {settings.max_dynamic_shots} shots (got {shots})."
            )
        if backend and backend not in DYNAMIC_BACKENDS and backend != "auto":
            warnings.append(
                f"Backend '{backend}' cannot run runtime control flow; "
                "the job will be routed to the Qiskit dynamic engine."
            )
    else:
        info.append("Circuit is static - runnable on Qiskit Aer, Cirq, PennyLane and qBraid.")

    if backend == "qbraid":
        if not (settings.qbraid_api_key and settings.qbraid_device_id):
            errors.append("Missing qBraid credentials (QBRAID_API_KEY / QBRAID_DEVICE_ID).")
        if dynamic:
            errors.append("qBraid backend supports static circuits only.")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "summary": summary,
    }


def check_challenge_constraints(ir: CircuitIR, challenge: dict[str, Any]) -> list[str]:
    """Validate a submission against a coding challenge's constraints."""
    problems: list[str] = []
    allowed = {g.lower() for g in (challenge.get("allowed_gates") or [])}
    if allowed:
        for op in ir.walk():
            if op.kind != "gate":
                continue
            name = op.gate or ""
            labelled = f"{'c' * len(op.controls)}{name}" if op.controls else name
            if name not in allowed and labelled not in allowed and "mcx" not in allowed:
                problems.append(f"Gate '{labelled}' is not allowed for this challenge.")
    constraints = challenge.get("constraints") or {}
    max_depth = constraints.get("max_depth")
    if max_depth is not None and ir.depth() > int(max_depth):
        problems.append(f"Circuit depth {ir.depth()} exceeds the limit of {max_depth}.")
    max_qubits = constraints.get("max_qubits")
    if max_qubits is not None and ir.n_qubits > int(max_qubits):
        problems.append(f"Circuit uses {ir.n_qubits} qubits, limit is {max_qubits}.")
    for required in constraints.get("required_gates") or []:
        if required.lower() not in gate_histogram(ir):
            problems.append(f"Circuit must use at least one '{required}' gate.")
    if constraints.get("must_be_dynamic") and not ir.is_dynamic():
        problems.append("This challenge requires runtime control flow (if/while).")
    return sorted(set(problems))


def find_op(ir: CircuitIR, op_id: str) -> Op | None:
    for op in ir.walk():
        if op.id == op_id:
            return op
    return None


__all__ = [
    "inspect_circuit",
    "summarize_circuit",
    "gate_histogram",
    "compute_run_hash",
    "check_challenge_constraints",
    "STATIC_BACKENDS",
    "DYNAMIC_BACKENDS",
]
