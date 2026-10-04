# Measurement and Dynamic Circuits

Measurement is where quantum computing meets the classical world. Up to now the
state evolved smoothly and reversibly; measurement is probabilistic,
irreversible, and the only way to get an answer out. This lesson covers the
Born rule in operation, why results are statistical, and how a measurement taken
*mid-circuit* can steer the rest of the computation — the idea behind dynamic
circuits and, ultimately, quantum error correction.

## Learning objectives

By the end of this lesson you should be able to:

- **State** the Born rule and describe the post-measurement collapsed state.
- **Explain** why results are statistical and estimate the error on a
  probability from the shot count.
- **Distinguish** terminal measurement from mid-circuit measurement.
- **Compare** this platform's two measurement actions and choose the correct one
  for a dynamic circuit.
- **Construct** a `while` loop that uses measurement feedback, and describe the
  cap that keeps it terminating.

## The Born rule and collapse

For a qubit $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$, measurement in
the computational basis yields:

$$0 \text{ with probability } |\alpha|^2, \qquad 1 \text{ with probability } |\beta|^2$$

Measurement is not passive. Afterwards the qubit *is* the observed outcome:

$$|\psi\rangle \longrightarrow |0\rangle \text{ or } |1\rangle$$

All phase information in the measured qubit is **destroyed**. This is the
collapse, and it is why measurement is irreversible — several different input
states map to the same output, so you cannot run it backwards.

The general rule for measuring a state $|\psi\rangle$ and obtaining outcome $m$
is:

$$P(m) = |\langle m|\psi\rangle|^2 = \| \Pi_m |\psi\rangle \|^2$$

where $\Pi_m = |m\rangle\langle m|$ is the projector onto the outcome.

## Shots and statistics

Each run of a circuit yields **one** sample. To estimate a probability you
repeat the circuit many times; the number of repetitions is the **shot count**.

Counts are estimates, not exact values. For $N$ shots, the standard error on an
estimated probability $p$ is

$$\sigma = \sqrt{\frac{p(1-p)}{N}}$$

which scales as $1/\sqrt{N}$. Some concrete consequences:

| Shots | Standard error on a 50/50 estimate |
|-------|------------------------------------|
| 100 | $\pm$ 5% |
| 1024 | $\pm$ 1.6% |
| 4096 | $\pm$ 0.8% |

With 100 shots a true 50/50 split will routinely look like 45/55. With 4096
shots it will look much closer to even. When you compare two candidate circuits,
make sure the difference you are looking at is larger than the error bar.

## Terminal versus mid-circuit measurement

A **terminal** measurement is the last operation touching a qubit. A
**mid-circuit** measurement happens while the circuit continues — and it is the
enabling ingredient for dynamic circuits, because the classical outcome can
steer later operations.

This distinction is why the platform does not simply "add measurements at the
end" and call it done.

## The two measurement actions

This platform deliberately offers two distinct actions:

- **Measure All (Append)** — *dynamic-safe*. Adds terminal measurements for
  every qubit at the end of the top-level timeline and **deletes nothing**.
  Existing mid-circuit measurements that your `if`/`while` logic depends on are
  preserved. **Use this by default.**
- **Normalize Terminal Measurement** — *static convenience*. Removes every
  `measure` in the **top-level** timeline and inserts one clean terminal
  measure-all layer. It never touches measurements nested inside blocks or
  boxes. It will warn you, because removing a mid-circuit measurement can
  silently change the meaning of a dynamic circuit.

The rule of thumb: if your circuit contains any control flow, use **Measure All
(Append)**.

## Dynamic circuits: classical feedback

A **dynamic circuit** uses runtime classical information to decide what to do
next. The supported forms are:

- `if (c[0] == 1) { x q[1]; } else { z q[1]; }`
- `if (c[0:2] == "101") { ... }` — compare a slice of the classical register
- `for i in [0..N)` — $N$ must be a **compile-time constant**, so the loop can
  be unrolled
- `while (c[0] == 1) { ... }` — a genuine runtime loop

### The while cap

A `while` loop whose condition never becomes false would run forever. Every
`while` in this platform is therefore capped at **32 iterations**.

If a shot hits the cap it is truncated, and the result metadata reports
`while_cap_hits`, so you can tell the difference between *"my algorithm
converged"* and *"my loop was cut off"*. Always check that field when a loop is
involved — a silent truncation would otherwise look like a plausible result.

In strict mode the cap raises an error instead of truncating, which is the right
setting when a truncated answer is worse than no answer.

### Execution policy and limits

Static circuits run on any backend: Qiskit Aer, Cirq, PennyLane or qBraid.
Circuits with runtime control flow are automatically routed to the **Qiskit
dynamic engine**, which steps through operations shot by shot, samples and
collapses on each measurement, and evaluates control flow against live classical
bits.

That engine is more expensive than vectorised simulation, so it carries limits:

| Limit | Value |
|-------|-------|
| Maximum qubits (dynamic) | **15** |
| Maximum shots (dynamic) | **4096** |
| `while` iterations per shot | **32** |

## Worked example: forcing a qubit to |0>

This is the canonical feedback loop:

```
h q[0];                      // random 0 or 1
c[0] = measure q[0];
while (c[0] == 1) {          // if we got 1, flip and re-check
  x q[0];
  c[0] = measure q[0];
}
```

**Why it works.** The Hadamard makes the first measurement random. If it yields
1, the loop applies X (flipping $|1\rangle \to |0\rangle$) and measures again.
Since the qubit is now determinately $|0\rangle$, the re-measurement gives 0 and
the loop exits. If the first measurement gave 0, the loop body never runs.

Either way, **every shot ends with `c[0] == 0`**, even though the first
measurement was random.

Verified against this platform's dynamic engine, 256 shots, seed 1234:

| Result | Value |
|--------|-------|
| Counts | `{'0': 256}` |
| `while_cap_hits` | `0` |
| `while_cap` | `32` |

All 256 shots converged and none hit the cap.

This is **measurement-based feedback**, and it is the core idea behind quantum
error correction: measure a syndrome, and let the outcome decide which
correction to apply.

## Practical example

```python
from app.quantum.backends import dynamic_qiskit
from app.quantum.ir import CircuitIR, Condition, Op

# h q[0]; c[0] = measure q[0]; while (c[0] == 1) { x q[0]; c[0] = measure q[0]; }
ir = CircuitIR(name="force0", n_qubits=1, n_clbits=1)
ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 1)
ir.place(
    Op(
        kind="while",
        condition=Condition(type="bit_eq", bit=0, value=1),
        body=[
            Op(kind="gate", gate="x", qubits=[0]),
            Op(kind="measure", qubits=[0], clbits=[0]),
        ],
    ),
    2,
)
ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 3)

result = dynamic_qiskit.run(ir, shots=256, seed=1234)
print(result["counts"])                                  # {'0': 256}
print(result["metadata"]["while_cap_hits"])              # 0
print(result["metadata"]["while_cap"])                   # 32
```

**Try it.** In the Composer, add **H** on q0, then a **Measure** into c[0], then
a **while** block with condition `c[0] == 1` containing **X** on q0 and another
**Measure** into c[0]. Run with 256 shots: every shot reports `0`, and the
metadata shows no cap hits.

## Common misconceptions

- **"Measurement just reveals a pre-existing value."** If it did, the $|+\rangle$
  versus $|-\rangle$ distinction in a rotated basis could not exist. Measurement
  is an active, irreducible process.
- **"I can measure a qubit twice to get more information."** The first
  measurement collapses the state; the second returns the same value with
  certainty. You learn nothing new.
- **"4096 shots means my probability is exact."** It means the error bar is
  about 0.8%. Always quote results with their uncertainty.
- **"Mid-circuit measurement is just an optimization."** No — it changes what is
  computable, enabling feedback that no static circuit can express.

## Exercises

**1. Collapse.** A qubit is in $|+\rangle$. You measure and obtain 0. What is the
state now? What do you get if you measure again immediately?

**2. Error bars.** You run 400 shots and observe 220 zeros. Estimate $P(0)$ and
its standard error. Is this consistent with a true 50/50 split?

**3. Basis.** How would you measure a qubit in the X basis using only the
computational-basis measurement available in hardware?

**4. Feedback.** Explain why the forcing loop terminates after at most
*two* measurements in the body.

**5. Coding.** Modify the forcing loop to force the qubit to $|1\rangle$
instead, and predict the counts.

### Answers

**1.** After obtaining 0 the state is $|0\rangle$. Measuring again gives 0 with
probability 1.

**2.** $\hat{p} = 220/400 = 0.55$. The standard error is
$\sqrt{0.55 \times 0.45 / 400} \approx 0.0249$. A true 50/50 would give
$0.5 \pm 0.025$, so $0.55$ is about two standard errors away — suggestive but
not conclusive. Increase the shot count before drawing a conclusion.

**3.** Apply an H gate immediately before the measurement. This rotates the
X-basis states onto the Z basis ($H|+\rangle = |0\rangle$,
$H|-\rangle = |1\rangle$), so a computational-basis measurement afterwards
reports the X-basis value.

**4.** If the first measurement gives 0 the loop never enters. If it gives 1,
the body applies X — which maps $|1\rangle$ to $|0\rangle$ deterministically —
so the re-measurement inside the body yields 0 with certainty and the condition
fails. The loop body runs at most once.

**5.** Invert the condition to `c[0] == 0` so the loop flips whenever the qubit
is 0:

```python
ir.place(
    Op(
        kind="while",
        condition=Condition(type="bit_eq", bit=0, value=0),
        body=[
            Op(kind="gate", gate="x", qubits=[0]),
            Op(kind="measure", qubits=[0], clbits=[0]),
        ],
    ),
    2,
)
```

Every shot should end at `1`, giving counts `{'1': 256}`.

## Summary

- Measurement yields outcome $m$ with probability $|\langle m|\psi\rangle|^2$
  and collapses the state onto it, destroying phase information.
- Results are statistical: standard error scales as $1/\sqrt{N}$.
- Terminal measurement ends the circuit; mid-circuit measurement enables
  feedback.
- **Measure All (Append)** is dynamic-safe and the default; **Normalize
  Terminal Measurement** rewrites top-level measurements and warns you.
- `while` loops are capped at **32** iterations; check `while_cap_hits` in the
  metadata.
- Dynamic execution is limited to **15 qubits** and **4096 shots**.

Next, **[Deutsch–Jozsa](05_deutsch_jozsa.md)** puts interference to work in the
first algorithm that beats its classical counterpart.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §2.2.
- Qiskit documentation, "Measurement and dynamic circuits":
  https://docs.quantum.ibm.com/
- IBM Quantum, "Introduction to dynamic circuits":
  https://quantum.cloud.ibm.com/docs/
- Qiskit 1.2.4 release notes: https://docs.quantum.ibm.com/api/qiskit/release-notes
