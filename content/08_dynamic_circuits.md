# Dynamic Circuits and Classical Control Flow

A **dynamic circuit** contains classical logic that executes *during* the quantum
computation. It measures, reads the result, and branches - all before the circuit ends.

## Why they matter

- **Quantum error correction**: syndrome measurements determine which correction to apply.
  Without feed-forward there is no fault tolerance.
- **Teleportation**: Bob's two corrective gates depend on Alice's two measured bits.
- **Repeat-until-success**: retry a probabilistic gadget until it succeeds.
- **Resource savings**: measuring and resetting a qubit lets you reuse it instead of
  allocating another.

## Supported constructs

### if / else
```
c[0] = measure q[0];
if (c[0] == 1) {
  x q[1];
} else {
  h q[1];
}
```

### Bitstring comparison
Compare a slice of the classical register against a literal:
```
if (c[0:2] == "101") {
  z q[0];
}
```
The slice bound is inclusive in OpenQASM 3, so `c[0:2]` covers bits 0, 1 and 2.

### for loops
```
for int i in [0:3] {
  h q[0];
}
```
The bound must be a **compile-time constant**, which lets the compiler unroll the loop.
A `for` loop alone does not make a circuit dynamic - it is fully known ahead of time.

### while loops
```
while (c[0] == 1) {
  x q[0];
  c[0] = measure q[0];
}
```
A `while` depends on runtime state, so it *does* make the circuit dynamic. Every `while`
is capped at **32 iterations** to guarantee termination.

### box
A `box` groups operations into a named sub-block. It is organizational: it does not by
itself introduce classical control.

## How this platform executes dynamic circuits

A circuit is classified as dynamic if it contains `if` or `while`, or a gate carrying a
classical condition. Dynamic circuits always run on the **Qiskit dynamic engine**, which:

1. runs **shot by shot** (no shortcuts - each shot has its own classical register)
2. evolves a statevector through unitary gates
3. on measurement, samples an outcome, **collapses** the state and writes the classical bit
4. evaluates `if`/`else`, unrolls `for`, and re-checks `while` conditions against live bits
5. enforces the 32-iteration cap and reports `while_cap_hits` in the metadata

Limits: **15 qubits**, **4096 shots**, plus a worker timeout.

If you select Cirq, PennyLane or qBraid for a dynamic circuit, the platform will tell you
it is routing the job to the Qiskit engine instead - those backends cannot express runtime
feedback natively.

## Exporting dynamic circuits

- **OpenQASM 3** expresses `if`/`else`, `for` and `while` directly.
- **Qiskit** export uses the control-flow builders `if_test`, `for_loop` and `while_loop`.
- **Cirq** has no native runtime control flow, so the export ships a **Cirq circuit plus a
  Python driver**. The driver simulates segment by segment, samples mid-circuit
  measurements, collapses the state and evaluates the branching in Python - reproducing the
  same distribution as the platform's engine.

## A caution about the two measurement buttons

**Normalize Terminal Measurement** strips top-level measurements. If your `while` loop
depends on one of them, normalizing will change the circuit's meaning - which is why the
platform warns you. For dynamic circuits, prefer **Measure All (Append)**.
