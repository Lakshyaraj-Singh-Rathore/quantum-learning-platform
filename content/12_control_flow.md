<!-- track: circuit -->
# Control Flow: if, for, while and Box

Most quantum circuits are a fixed list of gates. **Dynamic circuits** can look
at a measurement result *mid-circuit* and change what happens next. This lesson
covers the four control-flow blocks this platform supports. For the execution
model and export behaviour, see **[Dynamic Circuits](08_dynamic_circuits.md)**.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** each of the four control-flow blocks and predict its effect.
- **Explain** why a `for` loop is static while a `while` loop is dynamic.
- **Describe** the 32-iteration cap and the three places it is enforced.
- **Interpret** the measurement semantics of a dynamic circuit, including why
  the statevector and Bloch views are unavailable.
- **Choose** the correct measurement action for a dynamic circuit.

## Why dynamic circuits matter

Three things become possible:

- **Measurement-based correction.** Teleportation needs a conditional fix-up.
- **Qubit reuse.** Measure, reset, reuse — a shallow chip runs a deeper circuit.
- **Repeat-until-success.** Retry a probabilistic gate until it works.

Error correction needs all three, which is why dynamic circuits are the current
frontier of hardware capability.

Any circuit using them runs on the **Qiskit dynamic engine** — Cirq, PennyLane
and qBraid are static-only. The platform selects it automatically.

## if / else

Runs a block only when a classical bit (or a group of bits) has a given value.

```
measure q0 -> c[0]
if (c[0] == 1) {
    x q1
}
```

You can also compare a **range of bits** to a value: `if (c[0:2] == 3)` fires
when the bits in that range hold the value 3.

> **Slice bounds are inclusive in OpenQASM 3**, so `c[0:2]` covers bits 0, 1 and
> 2 — three bits, not two. Python-style half-open intuition is the usual source
> of off-by-one bugs here.

**Worked example — conditional correction.** Prepare q0 in superposition with
`H`, entangle it with q1 using `CNOT`, measure q0, then conditionally apply `X`
to q1.

Verified on the dynamic engine, 1024 shots, seed 1234 (remembering that
**qubit 0 is the rightmost** bitstring character):

| Circuit | Counts | Meaning |
|---------|--------|---------|
| **With** the `if` | `{'00': 514, '01': 510}` | q1 is *always* 0; q0 is random |
| **Without** the `if` | `{'00': 514, '11': 510}` | q1 matches q0 exactly |

The leftmost character is q1's result. With the correction it is `0` in every
shot, even though q0's own outcome is a coin flip. Without it, q1 simply copies
q0's randomness. **The conditional correction was doing real work.**

## for loops

Repeats a block a **compile-time constant** number of times.

```
for i in [0..4) {
    h q0
    t q0
}
```

The bound must be a literal integer. It cannot depend on a measurement, because
the circuit is unrolled before execution. If you need a data-dependent count,
use `while`.

Verified: a `for` loop leaves `is_dynamic()` false. An unrolled loop is just a
longer static circuit, so it runs on any backend.

## while loops — and the cap

Repeats **while** a classical bit holds a value.

```
while (c[0] == 1) {
    reset q0
    h q0
    measure q0 -> c[0]
}
```

This is repeat-until-success: keep trying until the measurement gives 0.
Verified: 512 shots all end at `0`, with `while_cap_hits` equal to 0.

**The hard cap is 32 iterations.** A quantum `while` can genuinely fail to
terminate — if the condition never flips, the loop runs forever and the job
hangs. Real hardware has the same problem and solves it the same way. When the
cap is hit, the platform **warns**; it does not silently truncate. Check
`while_cap_hits` in the metadata to tell "my algorithm converged" apart from "my
loop was cut off".

The cap is enforced in three places: at build time, before queueing (HTTP 422),
and again at runtime.

## Box

Groups operations into a named unit.

```
box my_prep {
    h q0
    cx q0, q1
}
```

A box changes no physics. It exists for **organisation** — nesting, reuse, and
keeping the composer readable. It also acts as a scheduling boundary, so the
optimiser will not reorder gates across it. Verified: `box` leaves
`is_dynamic()` false.

## Measurement semantics: the trap

This is where most people go wrong.

A dynamic circuit executes **shot by shot**. Each shot takes its own path through
the branches. That means:

- There is no single statevector for the whole circuit. The Timeline stops
  showing one after the first measurement, and it is right to.
- The **Bloch sphere and phase disk are disabled**. Averaging over branches would
  produce a picture that corresponds to no actual state.
- Only the **histogram** is meaningful, because it aggregates outcomes.

If you see "Statevector not available", that is the correct answer for a dynamic
circuit — not a failure.

## Two measurement buttons

The composer offers two, and they behave very differently.

**Measure All (Append)** adds a measurement layer at the end. It never deletes
anything. Safe on dynamic circuits, because your mid-circuit measurements — the
ones your `if` conditions depend on — survive.

**Normalize Terminal Measurement** strips top-level measurements and puts one
clean layer at the end. Useful for tidying a static circuit before export. It
operates on the **top level only** and never touches measurements nested inside
blocks. On a dynamic circuit it warns you, because removing a measurement that
an `if` depends on changes the circuit's meaning.

## Limits

| Limit | Value | Reason |
|---|---|---|
| Max qubits (dynamic) | 15 | shot-by-shot execution is expensive |
| Max shots (dynamic) | 4096 | keeps runs inside the task timeout |
| While-loop cap | 32 | prevents non-terminating jobs |
| Soft / hard timeout | 8 s / 15 s | fair scheduling |

All four are read from application settings rather than hard-coded, so they are
the values the running service actually enforces.

## Practical example

```python
from app.quantum.ir import CircuitIR, Op, Condition
from app.quantum.backends import dynamic_qiskit

def conditional_correction(use_if: bool):
    ir = CircuitIR(name="corr", n_qubits=2, n_clbits=2)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="cx", qubits=[0, 1]), 1)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 2)
    if use_if:
        ir.place(
            Op(
                kind="if",
                condition=Condition(type="bit_eq", bit=0, value=1),
                body=[Op(kind="gate", gate="x", qubits=[1])],
            ),
            3,
        )
    ir.place(Op(kind="measure", qubits=[1], clbits=[1]), 4)
    return ir

# With the correction q1 is always 0; without it q1 just copies q0.
print("with if:   ", dynamic_qiskit.run(
    conditional_correction(True), shots=1024, seed=1234)["counts"])   # {'00': 514, '01': 510}
print("without if:", dynamic_qiskit.run(
    conditional_correction(False), shots=1024, seed=1234)["counts"])  # {'00': 514, '11': 510}

# Repeat-until-success
ir = CircuitIR(name="rus", n_qubits=1, n_clbits=1)
ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 1)
ir.place(
    Op(
        kind="while",
        condition=Condition(type="bit_eq", bit=0, value=1),
        body=[
            Op(kind="reset", qubits=[0]),
            Op(kind="gate", gate="h", qubits=[0]),
            Op(kind="measure", qubits=[0], clbits=[0]),
        ],
    ),
    2,
)
ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 3)
result = dynamic_qiskit.run(ir, shots=512, seed=1234)
print("repeat-until-success:", result["counts"])                       # {'0': 512}
print("while_cap_hits:", result["metadata"]["while_cap_hits"])         # 0
```

## Common misconceptions

- **"A `for` loop is control flow, so my circuit is dynamic."** Its bound is a
  compile-time constant, so the compiler unrolls it and the circuit stays static.
- **"`while_cap_hits` of 0 means my loop ran zero times."** It means no shot hit
  the *cap*. Each shot still ran the loop until its condition went false.
- **"The Bloch sphere is broken on my dynamic circuit."** It is correctly
  disabled: branches produce different states, so no single vector describes the
  run.
- **"`c[0:2]` is two bits, like a Python slice."** In OpenQASM 3 the upper bound
  is inclusive, so it is three.

## Exercises

**1.** Build the conditional-correction circuit above. Run 1024 shots and confirm
q1 is deterministic even though q0's outcome is random.

**2.** Remove the `if` block and re-run. Explain the new distribution.

**3.** Build the repeat-until-success loop. Check the warnings panel for the
iteration cap.

**4.** Try to open the Bloch tab on a dynamic circuit and read the explanation.

**5.** Why can a `for` loop bound not depend on a measurement?

### Answers

**1.** With the correction you should see `{'00': 514, '01': 510}` at 1024 shots
with seed 1234. The leftmost bit (q1) is `0` in every shot, while the rightmost
(q0) splits roughly evenly.

**2.** Without the `if` you get `{'00': 514, '11': 510}`: q1 now equals q0 in
every shot. The qubits are correlated rather than corrected, so q1 is random.
That difference is exactly what the conditional correction buys you.

**3.** All 512 shots should end at `0` with `while_cap_hits` equal to 0. If your
loop body never re-measures the tested bit, every shot hits the cap and the panel
warns.

**4.** The tab explains that a dynamic circuit executes shot by shot, so branches
produce different states and no single Bloch vector describes the run. Only the
aggregated histogram is meaningful.

**5.** A `for` loop is unrolled at compile time, before any measurement has
happened. There is no value to unroll *to*. Use `while`, whose trip count is
decided at runtime against live classical bits.

## Summary

- Four blocks: `if`/`else`, `for`, `while` and `box`.
- `if` and `while` make a circuit dynamic; `for` and `box` do not.
- The `while` cap is 32 iterations, enforced at build time, at queue time
  (HTTP 422) and at runtime, with `while_cap_hits` reported in the metadata.
- Dynamic circuits run shot by shot, so the statevector, Bloch sphere and phase
  disk are correctly unavailable; only the histogram is meaningful.
- Use **Measure All (Append)**, never Normalize Terminal Measurement, on a
  dynamic circuit.
- Limits: 15 qubits, 4096 shots, 32 iterations, 8 s soft / 15 s hard timeout.

Next, **[Grover's Search](06_grover.md)** puts interference to work finding a
marked item.

## References

- OpenQASM 3 specification, control flow:
  https://openqasm.com/language/control_flow.html
- IBM Quantum, "Introduction to dynamic circuits":
  https://quantum.cloud.ibm.com/docs/
- Qiskit documentation, "Dynamic circuits and control flow":
  https://docs.quantum.ibm.com/
- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §4.4.
