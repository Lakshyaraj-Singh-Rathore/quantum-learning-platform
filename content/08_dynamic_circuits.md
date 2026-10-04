# Dynamic Circuits and Classical Control Flow

A **dynamic circuit** contains classical logic that executes *during* the quantum
computation. It measures, reads the result, and branches — all before the circuit
ends. This lesson explains why that matters, what this platform supports, and how
the engine executes it. For a block-by-block walkthrough of the four constructs,
see **[Control Flow](12_control_flow.md)**.

## Learning objectives

By the end of this lesson you should be able to:

- **Define** a dynamic circuit and say which constructs make one.
- **Explain** why error correction, teleportation and qubit reuse all require
  mid-circuit feedback.
- **Describe** how the Qiskit dynamic engine executes a circuit shot by shot.
- **State** the qubit, shot and loop limits, and where each is enforced.
- **Explain** what each export target can and cannot express.

## Why they matter

- **Quantum error correction**: syndrome measurements determine which correction
  to apply. Without feed-forward there is no fault tolerance.
- **Teleportation**: Bob's two corrective gates depend on Alice's two measured
  bits.
- **Repeat-until-success**: retry a probabilistic gadget until it succeeds.
- **Resource savings**: measuring and resetting a qubit lets you reuse it instead
  of allocating another.

Error correction needs all of these at once, which is why dynamic circuits are
the current frontier of hardware capability.

## What makes a circuit dynamic

This is worth being precise about, because the answer is narrower than most
people guess. Verified against `CircuitIR.is_dynamic()`:

| Construct | Dynamic? | Why |
|-----------|----------|-----|
| Plain gates | No | Fully known before the run |
| Terminal measurement | No | Nothing reads the result mid-circuit |
| `if` / `else` | **Yes** | Branch depends on a runtime bit |
| `while` | **Yes** | Trip count depends on a runtime bit |
| `for` | No | Bound is a compile-time constant, so it can be unrolled |
| `box` | No | Purely organisational; changes no physics |

The test is **not** "does it contain a measurement". It is *does anything read a
classical bit and change behaviour because of it*. A mid-circuit measurement that
nothing branches on leaves the circuit static.

A gate carrying a classical condition also makes a circuit dynamic, for the same
reason.

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

The slice bound is inclusive in OpenQASM 3, so `c[0:2]` covers bits 0, 1 and 2 —
three bits, not two. This is a common source of off-by-one errors when moving
between OpenQASM 3 and Python-style half-open ranges.

### for loops

```
for int i in [0:3] {
  h q[0];
}
```

The bound must be a **compile-time constant**, which lets the compiler unroll the
loop. A `for` loop alone does not make a circuit dynamic — it is fully known ahead
of time.

### while loops

```
while (c[0] == 1) {
  x q[0];
  c[0] = measure q[0];
}
```

A `while` depends on runtime state, so it *does* make the circuit dynamic. Every
`while` is capped at **32 iterations** to guarantee termination.

### box

A `box` groups operations into a named sub-block. It is organisational: it does
not by itself introduce classical control, and it changes no physics. It does act
as a scheduling boundary, so the optimiser will not reorder gates across it.

## How this platform executes dynamic circuits

Dynamic circuits always run on the **Qiskit dynamic engine**, which:

1. runs **shot by shot** (no shortcuts — each shot has its own classical register)
2. evolves a statevector through unitary gates
3. on measurement, samples an outcome, **collapses** the state and writes the
   classical bit
4. evaluates `if`/`else`, unrolls `for`, and re-checks `while` conditions against
   live bits
5. enforces the 32-iteration cap and reports `while_cap_hits` in the metadata

Limits: **15 qubits**, **4096 shots**, plus a worker timeout of 8 seconds soft and
15 seconds hard. All of these are read from application settings, not hard-coded
in the engine.

If you select Cirq, PennyLane or qBraid for a dynamic circuit, the platform will
tell you it is routing the job to the Qiskit engine instead — those backends
cannot express runtime feedback natively. The list of dynamic-capable backends
contains exactly one entry: `qiskit_dynamic`.

## Exporting dynamic circuits

- **OpenQASM 3** expresses `if`/`else`, `for` and `while` directly.
- **Qiskit** export uses the control-flow builders `if_test`, `for_loop` and
  `while_loop`.
- **Cirq** has no native runtime control flow, so the export ships a **Cirq
  circuit plus a Python driver**. The driver simulates segment by segment, samples
  mid-circuit measurements, collapses the state and evaluates the branching in
  Python — reproducing the same distribution as the platform's engine.

The Cirq case is worth pausing on: the *circuit* alone cannot express what the
program does. The exported Python is part of the artifact, not a convenience
wrapper.

## A caution about the two measurement buttons

**Normalize Terminal Measurement** strips top-level measurements. If your `while`
loop depends on one of them, normalizing will change the circuit's meaning —
which is why the platform warns you. For dynamic circuits, prefer **Measure All
(Append)**, which adds measurements without deleting anything.

## Practical example

```python
from app.quantum.ir import CircuitIR, Op, Condition
from app.quantum.backends import dynamic_qiskit

# if/else: branch on a measured bit
ir = CircuitIR(name="ifelse", n_qubits=2, n_clbits=1)
ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 1)
ir.place(
    Op(
        kind="if",
        condition=Condition(type="bit_eq", bit=0, value=1),
        body=[Op(kind="gate", gate="x", qubits=[1])],
        else_body=[Op(kind="gate", gate="h", qubits=[1])],
    ),
    2,
)
ir.place(Op(kind="measure", qubits=[1], clbits=[0]), 3)
result = dynamic_qiskit.run(ir, shots=1024, seed=1234)
print(result["counts"])   # {'00': 276, '01': 748}

# Which constructs actually make a circuit dynamic?
def build(ops):
    circuit = CircuitIR(name="t", n_qubits=2, n_clbits=2)
    for i, op in enumerate(ops):
        circuit.place(op, i)
    return circuit

print("plain gates:     ", build([Op(kind="gate", gate="h", qubits=[0])]).is_dynamic())
print("terminal measure:", build([
    Op(kind="gate", gate="h", qubits=[0]),
    Op(kind="measure", qubits=[0], clbits=[0]),
]).is_dynamic())

while_op = Op(
    kind="while",
    condition=Condition(type="bit_eq", bit=0, value=1),
    body=[Op(kind="gate", gate="x", qubits=[0])],
)
print("while:           ", build([
    Op(kind="gate", gate="h", qubits=[0]),
    Op(kind="measure", qubits=[0], clbits=[0]),
    while_op,
]).is_dynamic())

for_op = Op(kind="for", loop_n=4, body=[Op(kind="gate", gate="h", qubits=[0])])
print("for:             ", build([for_op]).is_dynamic())
print("box:             ", build([
    Op(kind="box", box_name="prep", body=[Op(kind="gate", gate="h", qubits=[0])])
]).is_dynamic())
# -> False, False, True, False, False
```

The `for` result is the one that surprises people: an unrolled loop is just a
longer static circuit, so it runs on any backend.

## Common misconceptions

- **"Any mid-circuit measurement makes a circuit dynamic."** Only if something
  branches on the result. Verified above: a terminal measure leaves
  `is_dynamic()` false.
- **"A `for` loop is control flow, so it must be dynamic."** Its bound is a
  compile-time constant; the compiler unrolls it before execution.
- **"All four backends can run my dynamic circuit."** Only `qiskit_dynamic` can.
  The others are static-only and the platform reroutes automatically.
- **"`c[0:2]` means two bits."** In OpenQASM 3 the slice is inclusive, so it is
  three bits: 0, 1 and 2.

## Exercises

**1.** Which of these makes a circuit dynamic: a mid-circuit measurement that no
branch reads, or a `for` loop with a constant bound?

**2.** Why does the Cirq export include a Python driver?

**3.** You build a `while` loop and the metadata reports `while_cap_hits: 512`
out of 512 shots. What happened?

**4.** Name three capabilities that quantum error correction requires from
dynamic circuits.

### Answers

**1.** Neither. A measurement nothing reads leaves the circuit static, and a
constant-bound `for` loop is unrolled at compile time. Only `if`, `while`, or a
classically conditioned gate makes a circuit dynamic.

**2.** Cirq has no native runtime control flow, so the circuit alone cannot
express the branching. The Python driver simulates segment by segment, sampling
measurements and evaluating conditions, to reproduce the same distribution.

**3.** Every one of the 512 shots hit the 32-iteration cap, so all of them were
truncated. The loop condition never became false — almost certainly a logic error
that fails to update the tested bit inside the body.

**4.** Mid-circuit syndrome measurement, conditional correction based on the
syndrome, and qubit reuse (measure, reset, reuse) to keep the circuit shallow.

## Summary

- A circuit is dynamic when something reads a classical bit and branches: `if`,
  `while`, or a conditioned gate.
- `for` (constant bound) and `box` (organisation) are **not** dynamic.
- Dynamic circuits run shot by shot on the Qiskit dynamic engine, which samples,
  collapses and evaluates conditions against live classical bits.
- Limits: 15 qubits, 4096 shots, 32 `while` iterations, 8 s soft / 15 s hard
  timeout.
- OpenQASM 3 and Qiskit express control flow natively; Cirq needs a Python
  driver alongside the circuit.
- Use **Measure All (Append)** on dynamic circuits.

Continue with **[Control Flow](12_control_flow.md)** for the four blocks in
detail.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §4.4.
- OpenQASM 3 specification, control flow:
  https://openqasm.com/language/control_flow.html
- IBM Quantum, "Introduction to dynamic circuits":
  https://quantum.cloud.ibm.com/docs/
- Qiskit documentation, "Dynamic circuits and control flow":
  https://docs.quantum.ibm.com/
- Qiskit 1.2.4 release notes: https://docs.quantum.ibm.com/api/qiskit/release-notes
