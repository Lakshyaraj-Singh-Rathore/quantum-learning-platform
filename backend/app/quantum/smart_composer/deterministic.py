"""Deterministic Qiskit optimization baseline and circuit characterization."""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any

from qiskit import QuantumCircuit, transpile

from app.quantum.ir import CircuitIR, Op, Param
from app.quantum.normalize import to_qiskit
from app.quantum.smart_composer.models import CircuitMetrics, OptimizationObjective

TWO_QUBIT_GATES = {"cx", "cz", "cy", "swap", "cp", "crz"}


def compute_circuit_hash(ir: CircuitIR) -> str:
    """Compute a stable SHA-256 hash of the circuit instructions."""
    normalized_ops = []
    for op in ir.ops:
        normalized_ops.append({
            "kind": op.kind,
            "gate": op.gate,
            "qubits": op.qubits,
            "controls": op.controls,
            "params": [round(p.value, 6) for p in op.params],
            "clbits": op.clbits,
        })
    raw = json.dumps({"n_qubits": ir.n_qubits, "ops": normalized_ops}, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def compute_circuit_metrics(ir: CircuitIR) -> CircuitMetrics:
    """Extract gate count, depth, 2Q gate count, and estimated hardware fidelity."""
    total_gates = 0
    two_q_gates = 0
    gate_counts: dict[str, int] = {}
    max_layer = 0

    for op in ir.walk():
        if op.kind == "gate":
            total_gates += 1
            name = op.gate or "gate"
            gate_counts[name] = gate_counts.get(name, 0) + 1
            if len(op.controls) > 0 or len(op.qubits) > 1 or name in TWO_QUBIT_GATES:
                two_q_gates += 1
            max_layer = max(max_layer, op.layer + 1)

    # Depth approximation from layer or gate density
    depth = max(max_layer, 1 if total_gates > 0 else 0)

    # Hardware noise score estimate: standard transmon rates (1Q=0.1%, 2Q=1.0%)
    one_q_gates = total_gates - two_q_gates
    est_fid = ((1.0 - 0.001) ** one_q_gates) * ((1.0 - 0.010) ** two_q_gates)

    return CircuitMetrics(
        n_qubits=ir.n_qubits,
        total_gates=total_gates,
        depth=depth,
        two_qubit_gates=two_q_gates,
        gate_counts=gate_counts,
        estimated_fidelity=round(est_fid, 5),
        circuit_hash=compute_circuit_hash(ir),
    )


def rule_based_cancellation(ir: CircuitIR) -> tuple[CircuitIR, list[str]]:
    """Apply deterministic identity and rotation rules directly on the IR."""
    ops = list(ir.ops)
    changed = True
    notes: list[str] = []

    self_inverse_1q = {"h", "x", "y", "z"}
    inverse_pairs_1q = {("s", "sdg"), ("sdg", "s"), ("t", "tdg"), ("tdg", "t")}

    while changed:
        changed = False
        new_ops: list[Op] = []
        i = 0
        while i < len(ops):
            op1 = ops[i]

            # 1. Trivial identity or zero-angle removal (R07_REDUNDANT_GATE)
            if op1.kind == "gate":
                if op1.gate == "id":
                    notes.append("Eliminated explicit Identity gate.")
                    changed = True
                    i += 1
                    continue
                if op1.gate in {"rx", "ry", "rz", "p"} and op1.params:
                    val = op1.params[0].value
                    if abs(val % (2 * math.pi)) < 1e-7 or abs(val) < 1e-7:
                        notes.append(f"Eliminated trivial zero-rotation gate {op1.gate}({val:.3g}).")
                        changed = True
                        i += 1
                        continue

            if i + 1 < len(ops):
                op2 = ops[i + 1]

                # Check if gates act on the same qubits
                same_qubits = (
                    op1.kind == "gate"
                    and op2.kind == "gate"
                    and op1.qubits == op2.qubits
                    and op1.controls == op2.controls
                    and op1.neg_controls == op2.neg_controls
                )

                if same_qubits:
                    # 2. Self-inverse cancellation (R01_INV_CANCEL)
                    if (
                        op1.gate == op2.gate
                        and (op1.gate in self_inverse_1q or (op1.gate == "x" and len(op1.controls) == 1))  # CX·CX = I
                    ):
                        notes.append(f"Cancelled adjacent self-inverse pair: {op1.gate} · {op2.gate}")
                        changed = True
                        i += 2
                        continue

                    # 3. Mutual inverse cancellation (S·Sdg = I, T·Tdg = I)
                    if (op1.gate, op2.gate) in inverse_pairs_1q:
                        notes.append(f"Cancelled inverse pair: {op1.gate} · {op2.gate}")
                        changed = True
                        i += 2
                        continue

                    # 4. Parametric rotation merging (R02_ROT_MERGE)
                    if (
                        op1.gate in {"rx", "ry", "rz", "p"}
                        and op1.gate == op2.gate
                        and op1.params
                        and op2.params
                    ):
                        v1 = op1.params[0].value
                        v2 = op2.params[0].value
                        sum_val = v1 + v2
                        norm_sum = sum_val % (2 * math.pi)
                        if abs(norm_sum) < 1e-7 or abs(norm_sum - 2 * math.pi) < 1e-7:
                            notes.append(f"Merged rotations {op1.gate}({v1:.3g}) + {op2.gate}({v2:.3g}) -> collapsed to identity.")
                            changed = True
                            i += 2
                            continue
                        else:
                            merged_op = Op(
                                kind="gate",
                                gate=op1.gate,
                                qubits=list(op1.qubits),
                                controls=list(op1.controls),
                                params=[Param.from_expr(f"{sum_val:.6g}")],
                                layer=op1.layer,
                            )
                            new_ops.append(merged_op)
                            notes.append(f"Merged rotations {op1.gate}({v1:.3g}) + {op2.gate}({v2:.3g}) -> {op1.gate}({sum_val:.3g}).")
                            changed = True
                            i += 2
                            continue

                    # 5. Phase consolidation: S·S = Z, T·T = S (R06_PHASE_CONSOL)
                    if op1.gate == "s" and op2.gate == "s" and not op1.controls:
                        new_ops.append(Op(kind="gate", gate="z", qubits=list(op1.qubits), layer=op1.layer))
                        notes.append("Consolidated S · S -> Z gate.")
                        changed = True
                        i += 2
                        continue
                    if op1.gate == "t" and op2.gate == "t" and not op1.controls:
                        new_ops.append(Op(kind="gate", gate="s", qubits=list(op1.qubits), layer=op1.layer))
                        notes.append("Consolidated T · T -> S gate.")
                        changed = True
                        i += 2
                        continue

            new_ops.append(op1)
            i += 1

        ops = new_ops

    # Reassign compact layers
    compact_ops = []
    layer_map: dict[int, int] = {}
    for op in ops:
        q_max = max((layer_map.get(q, 0) for q in op.involved_qubits()), default=0)
        compact_ops.append(op.model_copy(update={"layer": q_max}))
        for q in op.involved_qubits():
            layer_map[q] = q_max + 1

    result_ir = CircuitIR(
        name=ir.name,
        n_qubits=ir.n_qubits,
        n_clbits=ir.n_clbits,
        ops=compact_ops,
    )
    return result_ir, notes


def optimize_deterministic(
    ir: CircuitIR,
    objective: OptimizationObjective = OptimizationObjective.MIN_GATES,
) -> tuple[CircuitIR, list[str]]:
    """Run baseline deterministic optimization passes."""
    notes: list[str] = []

    # 1. Direct rule-based pass on IR
    simplified_ir, rule_notes = rule_based_cancellation(ir)
    notes.extend(rule_notes)

    # 2. Qiskit Transpiler Level 2 pass if purely unitary
    if not ir.is_dynamic():
        try:
            circ = to_qiskit(simplified_ir, include_measurements=True)
            # Optimization level based on objective
            opt_level = 2 if objective != OptimizationObjective.MIN_DEPTH else 3
            compiled = transpile(circ, optimization_level=opt_level)
            
            # Check if transpiler reduced gate count further
            if compiled.size() < len(simplified_ir.ops):
                notes.append(f"Qiskit PassManager (opt_level={opt_level}) reduced operations {len(simplified_ir.ops)} -> {compiled.size()}.")
        except Exception:
            pass

    return simplified_ir, notes
