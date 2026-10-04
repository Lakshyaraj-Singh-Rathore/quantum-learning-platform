<!-- track: circuit -->
# The Four Bell States

There are exactly four maximally entangled two-qubit states. They form an
orthonormal basis for the two-qubit space, and every one of them is built from
the *same* two-gate circuit with small modifications. This lesson is the
practical companion to **[Entanglement](03_entanglement.md)**: that one explains
what entanglement is, this one shows you how to build and tell apart all four
states.

## Learning objectives

By the end of this lesson you should be able to:

- **Write** the four Bell states and classify each as correlated or
  anti-correlated.
- **Construct** the circuit that prepares each one from $|00\rangle$.
- **Explain** why $\Phi^+$ and $\Phi^-$ give identical measurement histograms.
- **Distinguish** the four states experimentally by inverting the preparation.
- **Interpret** the entanglement entropy, concurrence and density-matrix
  readouts this platform provides.

## The four states

$$|\Phi^+\rangle = \tfrac{1}{\sqrt2}\left(|00\rangle + |11\rangle\right)$$

$$|\Phi^-\rangle = \tfrac{1}{\sqrt2}\left(|00\rangle - |11\rangle\right)$$

$$|\Psi^+\rangle = \tfrac{1}{\sqrt2}\left(|01\rangle + |10\rangle\right)$$

$$|\Psi^-\rangle = \tfrac{1}{\sqrt2}\left(|10\rangle - |01\rangle\right)$$

$\Phi$ states have **correlated** bits (both same). $\Psi$ states have
**anti-correlated** bits (always different). The $\pm$ is the relative phase.

> **A note on convention.** You will also see $\Psi^-$ written as
> $\tfrac{1}{\sqrt2}(|01\rangle - |10\rangle)$. That differs from the definition
> above by an overall factor of $-1$, which is a **global phase** and has no
> physical effect. Both conventions are correct; this lesson uses the form that
> matches the circuit in the next section.

## Building each one

Start from the base circuit: **H on q0, then CNOT (control q0, target q1)**.
That gives $|\Phi^+\rangle$. The other three need one extra gate.

| State | Circuit | Measured outcomes |
|---|---|---|
| $\Phi^+$ | `H q0`, `CNOT q0->q1` | `00` and `11`, 50/50 |
| $\Phi^-$ | `X q0`, `H q0`, `CNOT q0->q1` | `00` and `11`, 50/50 |
| $\Psi^+$ | `H q0`, `CNOT q0->q1`, `X q1` | `01` and `10`, 50/50 |
| $\Psi^-$ | `X q0`, `H q0`, `CNOT q0->q1`, `X q1` | `01` and `10`, 50/50 |

An equivalent route to $\Phi^-$ is `H q0`, `Z q0`, `CNOT q0->q1`.

**Verified amplitudes**, in the basis order $|00\rangle, |01\rangle, |10\rangle, |11\rangle$:

| State | Amplitudes | Counts (2048 shots) |
|-------|------------|---------------------|
| $\Phi^+$ | $(0.7071, 0, 0, 0.7071)$ | `00`: 1022, `11`: 1026 |
| $\Phi^-$ | $(0.7071, 0, 0, -0.7071)$ | `00`: 1031, `11`: 1017 |
| $\Psi^+$ | $(0, 0.7071, 0.7071, 0)$ | `01`: 1026, `10`: 1022 |
| $\Psi^-$ | $(0, -0.7071, 0.7071, 0)$ | `01`: 1031, `10`: 1017 |

## The crucial observation

**$\Phi^+$ and $\Phi^-$ produce identical histograms.** Both give roughly 50%
`00` and 50% `11`. On counts alone they are indistinguishable — the verified
counts above differ only by sampling noise.

They are nonetheless completely different states — orthogonal, in fact. The
entire difference is the **relative phase** on the $|11\rangle$ term, visible in
the sign of the fourth amplitude.

To see it in this platform:

1. Build $\Phi^+$, run it, open the **Phase disk**. Both states sit at 0°.
2. Build $\Phi^-$, run it. $|11\rangle$ now sits at 180°.
3. Or use the **Amplitude / phase table** and read the phase column directly.
4. Or turn on **Colour bars by relative phase** on the histogram — same heights,
   different colours.

This is exactly why a counts-only view of quantum computing is misleading, and
why this platform gives you phase views at all.

## Distinguishing them properly

If phase is invisible to measurement, how does anyone tell $\Phi^+$ from
$\Phi^-$ experimentally? You **undo** the preparation:

Apply `CNOT q0->q1` then `H q0` — the inverse of the Bell circuit. Then measure.

Verified outcomes, 1024 shots, seed 1234 — **all four are deterministic**:

| State measured | Result after inverting the preparation |
|----------------|----------------------------------------|
| $\Phi^+$ | `00` (1024/1024) |
| $\Phi^-$ | `01` (1024/1024) |
| $\Psi^+$ | `10` (1024/1024) |
| $\Psi^-$ | `11` (1024/1024) |

This is **Bell basis measurement**, and it is the foundation of quantum
teleportation and superdense coding. Each of the four Bell states maps to a
distinct computational basis state, which is precisely what makes an orthonormal
basis *measurable*.

## Why "maximally entangled"

For all four states, tracing out either qubit leaves the maximally mixed state
$\tfrac{1}{2}I$. Each qubit individually looks like a fair coin; all the
information lives in the correlation.

The platform reports this directly:

- **Entanglement S = 1.000** (one full bit of entropy)
- **Concurrence C = 1.00**
- Both Bloch vectors have length zero
- The **density matrix** shows bright off-diagonal corners — those corners are
  the coherence. A classical 50/50 mixture of `00` and `11` would show the same
  diagonal but **no** corners.

That last comparison is the sharpest way to see the difference between
entanglement and mere classical correlation.

## Practical example

Verified against **Qiskit 1.2.4** and `qiskit-aer` 0.16.0, `seed_simulator=1234`:

```python
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector

sim = AerSimulator()

def run(qc, shots=1024):
    return sim.run(transpile(qc, sim), shots=shots,
                   seed_simulator=1234).result().get_counts()

PREPARATIONS = {
    "Phi+": lambda c: (c.h(0), c.cx(0, 1)),
    "Phi-": lambda c: (c.x(0), c.h(0), c.cx(0, 1)),
    "Psi+": lambda c: (c.h(0), c.cx(0, 1), c.x(1)),
    "Psi-": lambda c: (c.x(0), c.h(0), c.cx(0, 1), c.x(1)),
}

for name, build in PREPARATIONS.items():
    # amplitudes
    prep = QuantumCircuit(2)
    build(prep)
    amps = np.round(Statevector(prep).data, 4)

    # direct measurement: Phi+/Phi- look the same, as do Psi+/Psi-
    direct = QuantumCircuit(2, 2)
    build(direct)
    direct.measure([0, 1], [0, 1])

    # Bell-basis measurement: undo the preparation, then measure
    basis = QuantumCircuit(2, 2)
    build(basis)
    basis.cx(0, 1)
    basis.h(0)
    basis.measure([0, 1], [0, 1])

    print(f"{name}: amps={amps.tolist()}")
    print(f"   direct {dict(sorted(run(direct, 2048).items()))}"
          f"   -> in basis: {run(basis)}")
```

Output:

```
Phi+: amps=[0.7071, 0, 0, 0.7071]
   direct {'00': 1022, '11': 1026}   -> in basis: {'00': 1024}
Phi-: amps=[0.7071, 0, 0, -0.7071]
   direct {'00': 1031, '11': 1017}   -> in basis: {'01': 1024}
Psi+: amps=[0, 0.7071, 0.7071, 0]
   direct {'01': 1026, '10': 1022}   -> in basis: {'10': 1024}
Psi-: amps=[0, -0.7071, 0.7071, 0]
   direct {'01': 1031, '10': 1017}   -> in basis: {'11': 1024}
```

The left column shows the problem (two pairs of identical histograms) and the
right column shows the solution (four distinct deterministic outcomes).

## Common misconceptions

- **"$\Phi^+$ and $\Phi^-$ are the same state."** They are orthogonal. Identical
  computational-basis statistics are not identical states.
- **"Phase is unobservable, so the $\pm$ is cosmetic."** It is unobservable in
  the basis you prepared it in. Change basis and it becomes a deterministic bit
  value.
- **"Entanglement means the qubits agree."** $\Psi$ states are
  *anti*-correlated: the qubits always disagree.
- **"A 50/50 mixture of `00` and `11` is the same as $\Phi^+$."** No — the
  mixture has no off-diagonal terms in its density matrix and zero entanglement.

## Exercises

**1.** Build all four Bell states and record the histogram and phase table for
each.

**2.** Confirm $\Phi^+$ and $\Phi^-$ have identical counts and differing phase.

**3.** Append the inverse Bell circuit to each and verify the four distinct
deterministic outcomes.

**4.** Enable the noise model on $\Phi^+$ with T1 = 5, T2 = 4. Watch the
forbidden outcomes `01` and `10` appear and concurrence fall.

**5.** Why does inverting the preparation circuit distinguish the states when
measuring directly does not?

### Answers

**1.** See the verified tables above: $\Phi^\pm$ give `00`/`11`, $\Psi^\pm$ give
`01`/`10`, each roughly 50/50.

**2.** Verified: $\Phi^+$ gives `{'00': 1022, '11': 1026}` and $\Phi^-$ gives
`{'00': 1031, '11': 1017}` — the same distribution within sampling noise — while
their amplitude vectors differ in the sign of the $|11\rangle$ component.

**3.** Verified: `00`, `01`, `10` and `11` respectively, each 1024/1024 shots.

**4.** T1 relaxation populates $|00\rangle$ and dephasing erases the off-diagonal
coherence, so `01` and `10` appear and concurrence drops below 1. See
**[Quantum Noise](09_quantum_noise.md)** for the mechanism.

**5.** Measuring in the computational basis projects onto states that are
superpositions of Bell states, so the phase information is averaged away. The
inverse circuit maps each Bell state onto a *distinct computational basis
state*, moving the phase difference into a population difference where a normal
measurement can see it. This is the same trick as `H`,`Z`,`H` revealing a hidden
Z phase.

## Summary

- The four Bell states are an orthonormal, maximally entangled basis for two
  qubits.
- All four come from `H` + `CNOT` plus at most one extra Pauli.
- $\Phi$ states are correlated; $\Psi$ states are anti-correlated.
- $\Phi^+$ and $\Phi^-$ are indistinguishable by counts alone — their difference
  is a relative phase.
- Inverting the preparation implements a Bell basis measurement, giving four
  distinct deterministic outcomes.
- Maximally entangled means each qubit's reduced state is $\tfrac12 I$: zero
  Bloch length, entropy 1, concurrence 1.

Continue with **[Variational Algorithms](07_vqe_qaoa.md)**.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §1.3.6, §2.5.
- Bell, J. S. "On the Einstein Podolsky Rosen paradox", *Physics* 1 (1964) 195.
- Qiskit documentation, "Entanglement and Bell states":
  https://docs.quantum.ibm.com/
- IBM Quantum Learning, "Entanglement in action":
  https://learning.quantum.ibm.com/
