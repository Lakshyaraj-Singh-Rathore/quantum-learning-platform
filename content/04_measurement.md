# Measurement and Dynamic Circuits

Measurement is the bridge from quantum to classical. It is **probabilistic** and
**irreversible**: the state collapses onto the observed outcome.

For $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$ you get 0 with probability
$|\alpha|^2$ and 1 with probability $|\beta|^2$, and afterwards the qubit *is* that
outcome. All phase information in the measured qubit is destroyed.

## Shots

Because each run yields one sample, we repeat the circuit many times. The number of
repetitions is the **shot count**. Counts are estimates: with $N$ shots the statistical
error on a probability is roughly $1/\sqrt{N}$. With 100 shots a true 50/50 split will
routinely look like 45/55; with 4096 shots it will look much closer to even.

## Terminal vs mid-circuit measurement

A **terminal** measurement is the last thing that touches a qubit. A **mid-circuit**
measurement happens while the circuit continues, and it is the enabling ingredient for
dynamic circuits: the classical outcome can steer later operations.

## The two measurement buttons

This platform deliberately offers two distinct actions, because dynamic circuits are
supported:

- **Measure All (Append)** - *dynamic-safe*. Adds terminal measurements for every qubit
  at the end of the top-level timeline and **deletes nothing**. Existing mid-circuit
  measurements that your `if`/`while` logic depends on are preserved. Use this by default.
- **Normalize Terminal Measurement** - *static convenience*. Removes every `measure` in
  the **top-level** timeline and inserts one clean terminal measure-all layer. It never
  touches measurements nested inside blocks or boxes. It will warn you, because removing
  a mid-circuit measurement can silently change the meaning of a dynamic circuit.

## Dynamic circuits: classical feedback

A **dynamic circuit** uses runtime classical information to decide what to do next:

- `if (c[0] == 1) { x q[1]; } else { z q[1]; }`
- `if (c[0:2] == "101") { ... }` - compare a slice of the classical register
- `for i in [0..N)` - N must be a **compile-time constant**, so the loop can be unrolled
- `while (c[0] == 1) { ... }` - a genuine runtime loop

### The while cap

A `while` loop whose condition never becomes false would run forever. Every `while` in
this platform is therefore capped at **32 iterations**. If a shot hits the cap it is
truncated and the result metadata reports `while_cap_hits`, so you can tell the difference
between "my algorithm converged" and "my loop was cut off".

### Execution policy

Static circuits run on any backend: Qiskit Aer, Cirq, PennyLane or qBraid.
Circuits with runtime control flow are automatically routed to the **Qiskit dynamic
engine**, which steps through operations shot by shot, samples and collapses on each
measurement, and evaluates the control flow against live classical bits. Limits: at most
**15 qubits** and **4096 shots**.

## Worked example: forcing a qubit to |0>

```
h q[0];                      // random 0 or 1
c[0] = measure q[0];
while (c[0] == 1) {          // if we got 1, flip and re-check
  x q[0];
  c[0] = measure q[0];
}
```
Every shot ends with `c[0] == 0`, even though the first measurement was random. This is
measurement-based feedback - the core idea behind quantum error correction, where syndrome
measurements decide which correction to apply.
