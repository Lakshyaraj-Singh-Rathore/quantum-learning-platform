"""Step-by-step circuit evolution for the Timeline view.

Builds one snapshot per top-level operation so a learner can walk a circuit
gate by gate and watch the state change. Only meaningful while the circuit is
unitary: a measurement or reset collapses the state, and control-flow blocks
branch per shot, so we stop emitting statevectors at that point and say why
rather than showing a number that is not the real state.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from app.quantum.ir import CircuitIR, Op
from app.quantum.noise import entanglement_entropy
from app.quantum.normalize import to_qiskit

MAX_TIMELINE_QUBITS = 8

#: Operations after which a single statevector no longer describes the register.
COLLAPSING = {"measure", "reset", "if", "while", "for"}


def _describe(op: Op) -> str:
    """Plain-language narration for one operation."""
    targets = ", ".join(f"q{q}" for q in op.qubits)
    controls = ", ".join(f"q{c}" for c in op.controls)

    if op.kind == "measure":
        return f"Measure {targets} into the classical register."
    if op.kind == "reset":
        return f"Reset {targets} back to |0>."
    if op.kind == "barrier":
        return "Barrier: a scheduling divider, no effect on the state."
    if op.kind == "if":
        return "Conditional block: runs only when the classical condition holds."
    if op.kind == "for":
        return f"For loop over {op.loop_n} iterations."
    if op.kind == "while":
        return "While loop (capped at 32 iterations)."
    if op.kind == "box":
        return f"Box '{op.box_name or 'unnamed'}': a grouped sub-circuit."

    gate = (op.gate or "").lower()
    angle = ""
    if op.params:
        angle = f"({op.params[0].expr})"

    plain = {
        "h": f"Hadamard on {targets}: creates an equal superposition.",
        "x": f"X on {targets}: flips |0> and |1>.",
        "y": f"Y on {targets}: bit flip plus a phase flip.",
        "z": f"Z on {targets}: flips the phase of |1>, probabilities unchanged.",
        "s": f"S on {targets}: adds a +90 degree phase to |1>.",
        "sdg": f"S-dagger on {targets}: adds a -90 degree phase to |1>.",
        "t": f"T on {targets}: adds a +45 degree phase to |1>.",
        "tdg": f"T-dagger on {targets}: adds a -45 degree phase to |1>.",
        "sx": f"Square-root of X on {targets}.",
        "swap": f"SWAP exchanges {targets}.",
        "id": f"Identity on {targets}: does nothing.",
    }
    base = plain.get(gate, f"{gate.upper()}{angle} on {targets}.")

    if controls:
        if gate == "x":
            return (
                f"Controlled-X: flips {targets} only when {controls} is |1>. "
                "On a superposed control this creates entanglement."
            )
        return f"Controlled-{gate.upper()}{angle}: applies to {targets} when {controls} is |1>."
    return base


def _state_payload(amplitudes: np.ndarray, n_qubits: int) -> dict[str, Any]:
    probabilities = np.abs(amplitudes) ** 2
    significant = np.flatnonzero(probabilities > 1e-9)
    reference = np.angle(amplitudes[significant[0]]) if significant.size else 0.0
    relative = np.angle(amplitudes * np.exp(-1j * reference))
    entropy, concurrence = entanglement_entropy(amplitudes, n_qubits)
    # Diagonalising a separable state leaves ~1e-16 of numerical dust. Showing
    # "S = 3.2e-16" where the honest answer is "not entangled" is just noise.
    if abs(entropy) < 1e-12:
        entropy = 0.0
    if concurrence is not None and abs(concurrence) < 1e-12:
        concurrence = 0.0

    top = sorted(
        (
            {
                "state": format(int(i), f"0{n_qubits}b"),
                "probability": float(probabilities[i]),
                "phase_deg": float(np.degrees(relative[i])),
            }
            for i in significant
        ),
        key=lambda row: -row["probability"],
    )[:8]

    return {
        "statevector": [[float(z.real), float(z.imag)] for z in amplitudes],
        "top_states": top,
        "entanglement_entropy": entropy,
        "concurrence": concurrence,
        "entangled": entropy > 0.05,
    }


def build_timeline(ir: CircuitIR) -> dict[str, Any]:
    """Return one snapshot per step, starting from the empty circuit."""
    if ir.n_qubits > MAX_TIMELINE_QUBITS:
        return {
            "supported": False,
            "reason": (
                f"Timeline is limited to {MAX_TIMELINE_QUBITS} qubits "
                f"(this circuit has {ir.n_qubits})."
            ),
            "steps": [],
        }

    ops = list(ir.ops)
    steps: list[dict[str, Any]] = []
    still_unitary = True

    for index in range(len(ops) + 1):
        prefix = CircuitIR.model_validate(
            {
                "n_qubits": ir.n_qubits,
                "n_clbits": ir.n_clbits,
                "name": ir.name,
                "ops": [op.model_dump() for op in ops[:index]],
            }
        )

        if index == 0:
            label = "Initial state"
            narration = (
                f"All {ir.n_qubits} qubit(s) start in |0>. "
                "Nothing has been applied yet."
            )
        else:
            op = ops[index - 1]
            label = (op.gate or op.kind).upper()
            narration = _describe(op)
            if op.kind in COLLAPSING:
                still_unitary = False

        entry: dict[str, Any] = {
            "step": index,
            "label": label,
            "narration": narration,
            "depth": prefix.depth(),
            "gate_count": index,
        }

        if still_unitary:
            try:
                from qiskit.quantum_info import Statevector

                circuit = to_qiskit(prefix, include_measurements=False)
                amplitudes = np.asarray(
                    Statevector.from_instruction(circuit).data, dtype=complex
                )
                entry.update(_state_payload(amplitudes, ir.n_qubits))
            except Exception as exc:  # noqa: BLE001
                entry["state_unavailable"] = f"Statevector unavailable: {exc}"
        else:
            entry["state_unavailable"] = (
                "A measurement, reset or control-flow block has run, so the "
                "register is no longer one pure state. Run the circuit to see "
                "measurement statistics instead."
            )

        steps.append(entry)

    return {"supported": True, "reason": "", "steps": steps}


__all__ = ["build_timeline", "MAX_TIMELINE_QUBITS"]
