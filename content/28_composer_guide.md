# The Quantum Composer

The Composer is this project's circuit editor: a grid where you place gates on
qubit wires, choose a backend and shot count, run the circuit, and read the
resulting histogram. Everything you have learned so far meets here — the gates
from the gate lessons, the measurement statistics from the probability lesson,
and the noise model from the noise lesson. This lesson documents what the
Composer actually does, including the limits it enforces and why.

## Learning objectives

By the end of this lesson you should be able to:

- **Build** a circuit programmatically using the circuit IR, and place gates on
  specific qubits and layers.
- **Select** an appropriate backend for a static or dynamic circuit, and state
  the qubit limits that apply.
- **Configure** a noise model, and name which gates pick up thermal error and
  which do not.
- **Read** the run metadata, including bit ordering and the entanglement
  metrics it reports.
- **Explain** what the inspector checks before a job is accepted, and interpret
  its errors and warnings.

## The circuit model

### The grid

A circuit is a list of **ops** placed at **(qubit, layer)** coordinates. Layers
are vertical slices: ops in the same layer act in parallel. The Composer
compacts layers automatically, so you rarely need to place them manually.

### Ops and kinds

Every op has a `kind`:

| Kind | Meaning |
|---|---|
| `gate` | A quantum gate on one or more qubits |
| `measure` | Measure a qubit into a classical bit |
| `reset` | Reset a qubit to $|0\rangle$ |
| `barrier` | A scheduling boundary; no effect on the state |
| `if` / `for` / `while` / `box` | Control flow (dynamic circuits) |

### The gate set

Single-qubit gates:

$$\texttt{h, x, y, z, id, s, sdg, t, tdg, sx, p, rx, ry, rz, swap}$$

Multi-qubit gates are built by attaching **controls** to one of these, so
`x` with one control is CNOT and with two is Toffoli. Convenience aliases are
accepted and normalised:

| Alias | Resolves to |
|---|---|
| `not` | `x` |
| `hadamard` | `h` |
| `identity`, `i` | `id` |
| `phase`, `u1` | `p` |
| `cx`, `cnot` | `x` with 1 control |
| `ccx`, `toffoli` | `x` with 2 controls |
| `mcx` | `x` with any number of controls |
| `cz`, `cy`, `cp`, `crz` | the base gate with 1 control |
| `cswap`, `fredkin` | `swap` with 1 control |

Four gates take a parameter: `p`, `rx`, `ry`, `rz`. Everything else is
parameterless.

## Backends

### The catalogue

| Backend | Supports | Notes |
|---|---|---|
| `qiskit_aer` | static, noise | The default simulator |
| `cirq` | static | Cirq engine |
| `pennylane` | static | PennyLane `default.qubit` |
| `qbraid` | static | Requires the qBraid extra |
| `cudaq` | static, noise | GPU accelerated; needs a GPU |
| `qiskit_dynamic` | dynamic | Mid-circuit measurement and control flow |

A **static** circuit has no mid-circuit measurement or classical control. A
**dynamic** one branches on measurement outcomes, and only
`qiskit_dynamic` runs those.

### Limits

| Limit | Value |
|---|---|
| Static qubits | 20 |
| Dynamic qubits | 15 |
| GPU qubits | 28 |
| Dynamic shots | 4096 |
| `while` iterations | 32 |
| `for` iterations | 1024 |

The GPU ceiling is higher because the statevector fits in GPU memory; the
dynamic ceiling is lower because branching circuits are unrolled and cost more
per shot. The loop caps exist because a `for` loop is expanded into real gates
during execution — without a ceiling, one op could build a circuit large enough
to hang the worker.

### Shot counts

The Composer offers 128, 256, 512, 1024, 2048, 4096 and 8192 shots. Recalling
the probability lesson, the standard error at $p = 0.5$ is
$\sqrt{0.25/N}$: 4.4% at 128 shots and 0.55% at 8192. If you need to resolve a
1% difference you need around 10000 shots, so the largest preset is the right
choice for precision work and the smallest is fine for checking that a circuit
is wired up correctly.

## Noise

### The model

Noise is optional and available on `qiskit_aer` and `cudaq`. It is a
thermal-plus-readout model with five knobs:

| Parameter | Default | Meaning |
|---|---|---|
| T1 relaxation | 50 µs | Energy loss |
| T2 dephasing | 30 µs | Loss of phase coherence |
| Readout error | 2% | Probability of a wrong bit on measurement |
| 1-qubit pulse | 0.10 µs | Duration of a single-qubit gate |
| 2-qubit pulse | 0.40 µs | Duration of a two-qubit gate |
| 3-qubit pulse | 1.00 µs | Duration of a three-qubit gate |

Longer pulses mean more decoherence per gate, which is why two-qubit gates
dominate the error budget on real hardware.

### Virtual gates

$Z$, $S$, $T$ and $RZ$ are implemented as **frame changes in software** rather
than physical pulses, so they pick up no thermal error. In the Composer this
shows up as these gates contributing nothing to decoherence. That is not a
simplification — it is how real superconducting hardware works, and it is why
circuit optimisers try to push single-qubit rotations into the virtual set.

## Reading the result

### What comes back

A run returns counts, probabilities, the statevector, and metadata. The
metadata is worth reading:

```
backend:  qiskit_aer
shots:    1024
bit_order: qiskit (qubit 0 = rightmost)
metrics:  entanglement_entropy, concurrence, entangled,
          fidelity, purity, total_variation, shot_leakage
```

Two things there matter a great deal:

- **`bit_order`** confirms the convention described in the results lesson:
  qubit 0 is the **rightmost** character of the bit string. Getting this wrong
  swaps every marginal you compute.
- **`metrics`** reports entanglement entropy, concurrence, fidelity and purity
  directly — the quantities defined in the density matrix and entanglement
  lessons, computed for you.

### A worked comparison

Running a Bell circuit with 1024 shots, seed 7:

| | Ideal | With default noise |
|---|---|---|
| $p(00)$ | 0.4912 | 0.4951 |
| $p(11)$ | 0.5088 | 0.4492 |
| $p(01) + p(10)$ | 0.0000 | 0.0557 |
| Fidelity | 1.0000 | 0.9813 |
| Purity | 1.0000 | 0.9631 |

The noise does something instructive: it creates **5.6% of outcomes that are
impossible in the ideal circuit**. A Bell pair can only ever produce `00` or
`11`. Seeing `01` or `10` at all is a direct measurement of error, and the
metadata reports it as `shot_leakage`. On real hardware this is one of the
cleanest ways to estimate how noisy a run was, because you know the ideal
answer has zero weight there.

## Validation before running

### The inspector

Before a job is accepted, the circuit is inspected. It reports:

- **Errors**, which block the run: unknown gate names, wrong parameter counts,
  a backend that does not support the circuit's features, too many qubits.
- **Warnings**, which do not block: for example, a circuit with no measurements
  gets all qubits measured automatically.

Common errors and their causes:

| Error | Cause |
|---|---|
| Unknown gate | Name not in the gate set or alias table |
| Wrong parameter count | A parameterised gate given no parameter, or vice versa |
| Qubit limit exceeded | More qubits than the selected backend allows |
| Static-only backend | A dynamic circuit sent to a static engine |

The inspector is also available directly from the Composer without running the
job, which is the fastest way to find out why a circuit will not execute.

## Exporting code

### Generating runnable source

The Composer exports the circuit as source for Qiskit, Cirq, PennyLane and
qBraid. This is the bridge from the visual editor to real scripts, and it is
the best way to learn a framework: build something you understand in the grid,
then read the generated code.

A Bell circuit exports as:

```python
"""Generated by QuantumLearn - Qiskit (static circuit)."""

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from numpy import pi


qc = QuantumCircuit(2, 2)

qc.h(0)
qc.cx(0, 1)
qc.measure(0, 0)
qc.measure(1, 1)

sim = AerSimulator()
compiled = transpile(qc, sim)
result = sim.run(compiled, shots=1024).result()
print(result.get_counts())
```

Note `qc.cx(0, 1)` — in Qiskit's own convention the first argument is the
control. The IR stores this as an `x` gate with a control list, and the
generator renders it in the target framework's syntax.

## Practical example

### Building a circuit with the IR

```python
from app.quantum.ir import Op, empty_circuit

# The grid is a list of ops placed at (qubit, layer).
circuit = empty_circuit(2, name="bell")
circuit.place(Op(kind="gate", gate="h", qubits=[0], layer=0), 0)
circuit.place(Op(kind="gate", gate="x", qubits=[1], controls=[0], layer=1), 1)
circuit.append_measure_all()

print("ops:", [(o.kind, o.gate, o.qubits, o.controls) for o in circuit.walk()])
print("depth:", circuit.depth(), " qubits:", circuit.n_qubits)
print("dynamic:", circuit.is_dynamic())

# Aliases are normalised on construction.
print("cnot ->", Op(kind="gate", gate="cnot", qubits=[1], controls=[0]).gate)
print("hadamard ->", Op(kind="gate", gate="hadamard", qubits=[0]).gate)
```

### Running it, with and without noise

```python
from app.quantum.backends import qiskit_aer
from app.quantum.noise import NoiseParams

clean = qiskit_aer.run(circuit, shots=1024, seed=7)
counts = clean["counts"]
total = sum(counts.values())
print("ideal counts:", counts)
print(f"  p(00)={counts.get('00', 0) / total:.4f}"
      f"  p(11)={counts.get('11', 0) / total:.4f}")
print("  bit order:", clean["metadata"]["bit_order"])
print("  metrics:", {k: round(v, 4) if isinstance(v, float) else v
                     for k, v in clean["metadata"]["metrics"].items()})

noisy = qiskit_aer.run(circuit, shots=1024, seed=7,
                       noise=NoiseParams(enabled=True))
n = noisy["counts"]
nt = sum(n.values())
leak = (nt - n.get("00", 0) - n.get("11", 0)) / nt
print(f"\nnoisy p(00)={n.get('00', 0) / nt:.4f}"
      f"  p(11)={n.get('11', 0) / nt:.4f}"
      f"  impossible outcomes={leak:.4f}")
print("  fidelity:", round(noisy["metadata"]["metrics"]["fidelity"], 4))
print("  purity:  ", round(noisy["metadata"]["metrics"]["purity"], 4))
```

Building the circuit prints the ops as `h` on qubit 0, then `x` on qubit 1 with
qubit 0 as control, then the two measurements — depth 3, since
`append_measure_all` adds its own layer — and `dynamic: False`. The aliases
resolve to `x` and `h`.

Running it ideal gives counts `{'00': 503, '11': 521}` — that is 0.4912 and
0.5088 — with bit order `qiskit (qubit 0 = rightmost)` and metrics showing
entanglement entropy 1.0, concurrence 1.0, fidelity 1.0 and purity 1.0. With
the default noise model the same circuit gives `p(00)=0.4951`, `p(11)=0.4492`
and **5.57% of shots landing on outcomes the ideal circuit cannot produce**,
with fidelity dropping to 0.9813 and purity to 0.9631.

## Common misconceptions

- **"More qubits is just a slower run."** The state grows as $2^n$, and the
  limits differ per backend: 20 static, 15 dynamic, 28 on GPU.
- **"Noise is applied uniformly to every gate."** Two-qubit gates are four
  times slower than one-qubit gates and dominate; $Z$, $S$, $T$ and $RZ$ are
  virtual and pick up no thermal error at all.
- **"A circuit with no measurements is invalid."** It is legal; the engine
  measures everything automatically and warns you.
- **"The histogram is the state."** It is a sample. The `statevector` and
  `probabilities` fields in the result are the exact values; the counts are
  draws from them.
- **"Dynamic circuits run anywhere."** Only `qiskit_dynamic` supports
  mid-circuit measurement and control flow.

## Exercises

1. Build a three-qubit GHZ circuit with the IR and verify its depth.
2. Add `rx` with a parameter to a circuit and confirm the IR accepts it. What
   happens if you give `h` a parameter?
3. Explain why `p(01) + p(10)` is a useful noise diagnostic for a Bell circuit
   but not for a circuit whose ideal output includes those outcomes.
4. Which gates in the set contribute no thermal error, and why?
5. A circuit has 18 qubits and uses mid-circuit measurement. Which backends can
   run it, and what shot ceiling applies?
6. Using the standard error formula, compute the uncertainty at 128 and 8192
   shots. Which preset would you use to verify a 2% effect?

## Summary

- The Composer's circuit model is ops at (qubit, layer) coordinates, with kinds
  `gate`, `measure`, `reset`, `barrier` and control flow.
- The gate set has 15 base gates; multi-qubit gates are base gates plus
  controls, and aliases such as `cnot` and `toffoli` are normalised.
- Six backends: five static (`qiskit_aer`, `cirq`, `pennylane`, `qbraid`,
  `cudaq`) and one dynamic (`qiskit_dynamic`). Qubit limits are 20 static,
  15 dynamic, 28 GPU.
- Noise is thermal plus readout, available on `qiskit_aer` and `cudaq`;
  $Z/S/T/RZ$ are virtual and pick up no thermal error.
- Run metadata reports bit ordering (qubit 0 is rightmost) and entanglement
  metrics including fidelity, purity and shot leakage.
- The inspector blocks runs with errors and warns on auto-fixes; code export
  targets Qiskit, Cirq, PennyLane and qBraid.

## References

- The project's own `backend/app/quantum/ir.py` — the circuit model this lesson
  documents.
- Qiskit documentation, *QuantumCircuit* — the export target shown above.
- The [Reading Quantum Results](27_reading_results.md) lesson — bit ordering,
  standard errors and how to interpret counts.

---

**Previous:** [Reading Quantum Results](27_reading_results.md) ·
**Next:** [The Estimator Primitive](29_primitives.md)
