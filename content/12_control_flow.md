<!-- track: circuit -->
# Control Flow: if, for, while and Box

Most quantum circuits are a fixed list of gates. **Dynamic circuits** can look
at a measurement result *mid-circuit* and change what happens next. This lesson
covers the four control-flow blocks this platform supports.

Any circuit using these runs on the **Qiskit dynamic engine** — Cirq, PennyLane
and qBraid are static-only. The platform selects it automatically.

## Why dynamic circuits matter

Three things become possible:

- **Measurement-based correction.** Teleportation needs a conditional fix-up.
- **Qubit reuse.** Measure, reset, reuse — a shallow chip runs a deeper circuit.
- **Repeat-until-success.** Retry a probabilistic gate until it works.

Error correction needs all three, which is why dynamic circuits are the current
frontier of hardware capability.

## if / else

Runs a block only when a classical bit (or a group of bits) has a given value.

```
measure q0 -> c[0]
if (c[0] == 1) {
    x q1
}
```

You can also compare a **range of bits** to a value:
`if (c[0:2] == 3)` fires when both `c[0]` and `c[1]` are 1.

**Worked example — teleportation-style correction.** Prepare q0 in superposition
with `H`, entangle it with q1 using `CNOT`, measure q0, then conditionally apply
`X` to q1. The result is that q1 ends up deterministically in a known state even
though the measurement outcome was random.

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

**The hard cap is 32 iterations.** A quantum `while` can genuinely fail to
terminate — if the condition never flips, the loop runs forever and the job
hangs. Real hardware has the same problem and solves it the same way. When the
cap is hit, the platform stops and warns; it does not silently truncate.

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
optimiser will not reorder gates across it.

## Measurement semantics: the trap

This is where most people go wrong.

A dynamic circuit executes **shot by shot**. Each shot takes its own path
through the branches. That means:

- There is no single statevector for the whole circuit. The Timeline stops
  showing one after the first measurement, and it is right to.
- The **Bloch sphere and phase disk are disabled**. Averaging over branches
  would produce a picture that corresponds to no actual state.
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

## Exercise

1. Build the conditional-correction circuit above. Run 1024 shots and confirm q1
   is deterministic even though q0's outcome is random.
2. Remove the `if` block and re-run. Now q1 is random — the correction was doing
   real work.
3. Build the repeat-until-success loop. Check the warnings panel for the
   iteration cap.
4. Try to open the Bloch tab on a dynamic circuit and read the explanation.
