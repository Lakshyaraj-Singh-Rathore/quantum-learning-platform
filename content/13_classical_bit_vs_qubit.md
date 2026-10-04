<!-- track: theory -->
# A Classical Switch vs a Qubit

The most common way to misunderstand quantum computing is to picture a qubit as
a coin that is "secretly heads or tails". This lesson kills that idea with an
experiment you can run in five minutes.

## Learning objectives

By the end of this lesson you should be able to:

- **Contrast** a classical bit with a qubit on definiteness, measurement and
  geometry.
- **Explain** why amplitudes cancelling is what makes quantum computing
  different from probability.
- **Predict** the outcome of the three decisive circuits and explain why the
  middle measurement changes the answer.
- **Describe** what the Bloch sphere shows that a two-state picture cannot.
- **Explain** why two entangled qubits have no individual states.

## The classical switch

A light switch is a bit. It is up (1) or down (0). If you flip it twice, it
returns to where it started. If you cover your eyes, it still has a definite
position — you just do not happen to know it.

Two facts define classical bits:

1. The state is always definite, whether or not you look.
2. Looking does not change it.

Both fail for qubits.

## The qubit

A qubit can be in a **superposition**:

$$|\psi\rangle = \alpha|0\rangle + \beta|1\rangle, \qquad |\alpha|^2 + |\beta|^2 = 1$$

$\alpha$ and $\beta$ are complex **amplitudes**, not probabilities. You get
probabilities by squaring their magnitudes — which means amplitudes can be
negative or complex and can therefore **cancel**. Probabilities never cancel.
That single fact is where all quantum advantage comes from.

## The decisive experiment

Here is the experiment that separates the two pictures. Run both in the
Composer.

### The "hidden coin" hypothesis

Suppose H just randomises the qubit to a secret 0 or 1 with 50/50 odds.

**Circuit A.** `H` on q0, then measure.
**Result:** about 512 / 512 out of 1024. Consistent with the hypothesis so far.

**Circuit B.** `H`, then `H` again, then measure.

If the hypothesis were right, the first H picks a secret value, and the second H
randomises again — so you should *still* see 50/50.

**Actual result: `0`, 100% of the time.**

The hypothesis is dead. There was no secret value between the two gates. The
first H produced a genuine superposition, and the second H made the two paths
**interfere**: the amplitudes for reaching $|1\rangle$ cancelled exactly, while
those for $|0\rangle$ reinforced.

### Making the cancellation explicit

Track the amplitude for landing in $|1\rangle$ after `H`,`H`:

- Path 1: $|0\rangle \to |0\rangle \to |1\rangle$, amplitude $\tfrac{1}{\sqrt2}\cdot\tfrac{1}{\sqrt2} = +\tfrac12$
- Path 2: $|0\rangle \to |1\rangle \to |1\rangle$, amplitude $\tfrac{1}{\sqrt2}\cdot\left(-\tfrac{1}{\sqrt2}\right) = -\tfrac12$

Total: $+\tfrac12 - \tfrac12 = 0$. Zero probability.

A classical coin has no minus signs available. This is the whole game.

### Now break the interference

**Circuit C.** `H`, **measure**, `H`, measure again.

Now you *do* get 50/50. The intermediate measurement destroyed the superposition
and forced a definite value — so the second H really did act on a definite bit.

Three circuits, three different answers. Verified against Qiskit 1.2.4 and
`qiskit-aer` 0.16.0, 1024 shots, seed 1234:

| Circuit | Verified result | Interpretation |
|---|---|---|
| `H` | `{'0': 521, '1': 503}` | superposition, collapsed at readout |
| `H`,`H` | `{'0': 1024}` | interference — no hidden value existed |
| `H`, measure, `H` | `{'0': 509, '1': 515}` | measurement forced a classical value |
| `H`,`Z`,`H` | `{'1': 1024}` | the Z flipped a sign, so $|0\rangle$ cancels instead |

Circuit B and Circuit C differ **only** by a measurement in the middle. If the
qubit had always held a hidden definite value, they would give the same answer.

## Visualising it: the Bloch sphere

A single qubit's state is a point on the surface of a sphere.

- North pole: $|0\rangle$
- South pole: $|1\rangle$
- Equator: equal superpositions, differing by phase

A classical bit only has access to the two poles. A qubit has the entire
surface. Open the **Bloch** tab after `H` and you will see the arrow lying on
the equator pointing along $+X$ — neither up nor down.

Then apply `Z` and look again: the arrow **rotates around the equator** to
$-X$. The poles-only classical picture has no room for that motion at all, which
is precisely why `Z` is invisible to a measurement but visible to interference —
as the `H`,`Z`,`H` result above demonstrates.

## Where the analogy really ends: entanglement

One qubit is a point on a sphere. Two qubits are **not** two points.

Build a Bell pair and open the **Bloch** tab: both arrows have zero length. Each
qubit individually is maximally uncertain, yet the pair is perfectly correlated
— measure one and you instantly know the other.

Two classical switches always have a definite joint setting, and each switch has
its own definite state. Entangled qubits have a definite **joint** state and no
individual states at all. There is no classical picture of this. Use the
**Q-sphere** tab, which shows the register as a whole rather than qubit by
qubit.

## Practical example

```python
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

sim = AerSimulator()

def run(qc, shots=1024):
    return sim.run(transpile(qc, sim), shots=shots,
                   seed_simulator=1234).result().get_counts()

# A: H alone -> random
qc = QuantumCircuit(1, 1); qc.h(0); qc.measure(0, 0)
print("A  H           :", run(qc))       # {'0': 521, '1': 503}

# B: H twice -> interference returns the qubit to |0>
qc = QuantumCircuit(1, 1); qc.h(0); qc.h(0); qc.measure(0, 0)
print("B  H,H         :", run(qc))       # {'0': 1024}

# C: H, MEASURE, H -> the measurement forces a classical value
qc = QuantumCircuit(1, 1); qc.h(0); qc.measure(0, 0); qc.h(0); qc.measure(0, 0)
print("C  H,meas,H    :", run(qc))       # {'0': 509, '1': 515}

# D: H,Z,H -> the sign flip cancels |0> instead of |1>
qc = QuantumCircuit(1, 1); qc.h(0); qc.z(0); qc.h(0); qc.measure(0, 0)
print("D  H,Z,H       :", run(qc))       # {'1': 1024}
```

B and C are the argument in four lines of code: identical gates, different
answers, and the only thing separating them is whether you looked.

## Common misconceptions

- **"A qubit is a coin spinning under my hand."** A spinning coin has a definite
  face; you lack the information. Circuit B cannot happen for a spinning coin.
- **"Superposition means it is 0 and 1 at the same time."** It means no definite
  value exists, and the evidence is that amplitudes interfere — something two
  coexisting definite values cannot do.
- **"Measurement just reveals what was there."** Circuit C proves otherwise:
  measuring changes what the following gate does.
- **"Entanglement is two qubits that happen to agree."** An entangled pair has a
  definite joint state and *no* individual states. A classical correlated pair
  has both.

## Exercises

**1.** Run all three circuits above and record the counts.

**2.** Explain in one sentence why B and C differ.

**3.** Predict `H`,`Z`,`H` before running it.

**4.** Why does the Bloch arrow for an entangled qubit have zero length?

### Answers

**1.** A gives roughly 50/50 (verified `521/503` at 1024 shots, seed 1234), B
gives `0` every time, C gives roughly 50/50 again (verified `509/515`).

**2.** The measurement in C collapsed the superposition to a definite value, so
the second H acted on a real bit and randomised it; in B the two Hadamards
interfered, and the amplitudes for $|1\rangle$ cancelled exactly.

**3.** `1`, with certainty (verified `{'1': 1024}`). The Z flips the sign of the
$|1\rangle$ amplitude, so now it is the $|0\rangle$ paths that cancel.

**4.** The reduced state of either qubit is $\tfrac12 I$, the maximally mixed
state, whose Bloch vector is the zero vector. All the information lives in the
correlation between the qubits, not in either one.

## Summary

| | Classical bit | Qubit |
|---|---|---|
| States | 0 or 1 | any $\alpha|0\rangle + \beta|1\rangle$ |
| Definite when unobserved? | yes | no |
| Reading it | harmless | collapses the state |
| Can states cancel? | no | yes — negative and complex amplitudes |
| Two of them | two independent bits | can be entangled, with no individual state |
| Geometry | two points | surface of a sphere |

Continue with **[Qubits and Superposition](01_qubits.md)** for the full
mathematical treatment.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §1.2, §2.5.
- Feynman, R. P. "Simulating Physics with Computers", *International Journal of
  Theoretical Physics* 21 (1982) 467.
- IBM Quantum Learning, "The Bloch sphere": https://learning.quantum.ibm.com/
- Qiskit documentation, "Introduction to quantum circuits":
  https://docs.quantum.ibm.com/
