# Entanglement

Entanglement is the property of quantum mechanics that most resists classical
intuition, and it is the resource behind quantum teleportation, superdense
coding and most quantum speed-ups. Two qubits are entangled when the pair has a
definite description but neither qubit does. This lesson defines that precisely,
builds the canonical examples, and is careful about what entanglement does *not*
give you.

## Learning objectives

By the end of this lesson you should be able to:

- **Define** a product state and state the condition for a state to be
  entangled.
- **Construct** each of the four Bell states and give the circuit that prepares
  it.
- **Explain** why Bell measurement outcomes are random individually yet
  perfectly correlated.
- **Describe** how GHZ states generalise entanglement to three or more qubits.
- **State** the no-signalling principle and explain why entanglement does not
  permit faster-than-light communication.

## Product states and entangled states

Two qubits are in a **product state** when the joint state factorises:

$$|\Psi\rangle_{AB} = |\psi\rangle_A \otimes |\phi\rangle_B$$

If a state can be written this way, each qubit has its own independent
description, and measuring one tells you nothing new about the other.

A state is **entangled** when no such factorisation exists — when the whole has
a description that the parts do not.

### The canonical example

$$|\Phi^+\rangle = \frac{|00\rangle + |11\rangle}{\sqrt2}$$

Try to write this as $(a|0\rangle + b|1\rangle) \otimes (c|0\rangle + d|1\rangle)$.
Expanding gives $ac|00\rangle + ad|01\rangle + bc|10\rangle + bd|11\rangle$, so
you would need $ad = 0$ and $bc = 0$ (to kill the $|01\rangle$ and $|10\rangle$
terms) while $ac \neq 0$ and $bd \neq 0$. From $ad = 0$ either $a$ or $d$ is
zero; if $a = 0$ then $ac = 0$, contradiction. If $d = 0$ then $bd = 0$,
contradiction. No assignment works, so the state is entangled.

## Preparing a Bell state

The recipe for $|\Phi^+\rangle$ is **H on q0, then CNOT with q0 as control and
q1 as target**. You learned in [Quantum Gates](02_gates.md) that CNOT flips the
target iff the control is $|1\rangle$; here is why that generates entanglement:

1. Start in $|00\rangle$.
2. Apply H to q0: the state becomes $\tfrac{1}{\sqrt2}(|00\rangle + |10\rangle)$.
   Still a product state — only q0 is in superposition.
3. Apply CNOT(q0 $\to$ q1): the $|10\rangle$ branch flips q1, giving
   $\tfrac{1}{\sqrt2}(|00\rangle + |11\rangle)$.

The CNOT has copied q0's *indeterminacy* onto the relationship between the two
qubits. Neither qubit now has a state of its own.

Verified against Qiskit 1.2.4, `seed_simulator=1234`, 2048 shots:

| Outcome | Counts |
|---------|--------|
| `00` | 1022 |
| `01` | 0 |
| `10` | 0 |
| `11` | 1026 |

The individual results are random — you cannot predict whether *this* shot gives
`00` or `11`. But they are perfectly **correlated**: whatever q0 does, q1 does
too.

## The four Bell states

The Bell states form an orthonormal basis of the two-qubit space:

$$|\Phi^\pm\rangle = \frac{|00\rangle \pm |11\rangle}{\sqrt2}, \qquad |\Psi^\pm\rangle = \frac{|01\rangle \pm |10\rangle}{\sqrt2}$$

All four are prepared by the same skeleton — H then CNOT — with extra Pauli
gates before it to choose which one:

| State | Preparation | Distinguishing feature |
|-------|-------------|------------------------|
| $\Phi^+$ | H(q0), CNOT(0$\to$1) | Correlated, even parity |
| $\Phi^-$ | X(q0), H(q0), CNOT(0$\to$1) | Correlated, with a relative minus sign |
| $\Psi^+$ | X(q1), H(q0), CNOT(0$\to$1) | Anti-correlated |
| $\Psi^-$ | X(q0), X(q1), H(q0), CNOT(0$\to$1) | Anti-correlated, with a minus sign |

$\Phi^+$ and $\Phi^-$ give *identical* measurement statistics in the
computational basis, exactly as $|+\rangle$ and $|-\rangle$ did in
[Qubits and Superposition](01_qubits.md). The difference lives in the phase and
is revealed by measuring in a different basis.

## GHZ states

Entanglement scales beyond two qubits. Apply H to q0, then CNOT from q0 onto
each remaining qubit:

$$|GHZ\rangle = \frac{|00\cdots0\rangle + |11\cdots1\rangle}{\sqrt2}$$

Verified with three qubits, 2048 shots: `000` → 1009 counts, `111` → 1039
counts, and every other outcome zero. Every qubit agrees with every other, all
at once.

GHZ states are maximally fragile in a specific sense: lose one qubit to noise
and the remaining pair is left in a classical mixture, with no entanglement at
all. This contrasts with other multipartite states that retain some
entanglement after losing a party.

## What entanglement is not

**Entanglement does not allow faster-than-light communication.** This is the
single most misused idea in popular treatments, so be precise:

- Alice measures her qubit and gets a uniformly random result — `0` or `1`, with
  no way to choose which.
- Bob, measuring his qubit, also sees uniform randomness. His statistics are
  *identical* whether or not Alice has measured.
- Only when they compare notes over an ordinary classical channel do the
  correlations become visible.

Because Alice cannot steer her own outcome, she cannot encode a message in it.
This is the **no-signalling** principle, and it is a theorem, not a limitation
of current technology.

It is also why quantum teleportation still requires **two classical bits** sent
the ordinary way. Teleportation transmits an unknown quantum state using shared
entanglement plus a classical channel; the classical channel is what enforces
the speed limit.

## Practical example

Verified against **Qiskit 1.2.4** and `qiskit-aer` 0.16.0, `seed_simulator=1234`:

```python
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector

sim = AerSimulator()

def run(qc, shots=2048):
    return sim.run(transpile(qc, sim), shots=shots,
                   seed_simulator=1234).result().get_counts()

# Bell pair: amplitudes live only on |00> and |11>
bell = QuantumCircuit(2)
bell.h(0)
bell.cx(0, 1)
print("Bell amplitudes:", np.round(Statevector(bell).data, 4))  # [0.7071, 0, 0, 0.7071]

bell_m = QuantumCircuit(2, 2)
bell_m.h(0); bell_m.cx(0, 1); bell_m.measure([0, 1], [0, 1])
print("Bell counts:", run(bell_m))        # {'00': 1022, '11': 1026}

# Without the CNOT there is no entanglement: q1 never leaves |0>
nocx = QuantumCircuit(2, 2)
nocx.h(0)
nocx.measure([0, 1], [0, 1])
print("H only (no CNOT):", run(nocx))     # {'00': 1022, '01': 1026}

# GHZ on three qubits
ghz = QuantumCircuit(3, 3)
ghz.h(0)
ghz.cx(0, 1)
ghz.cx(0, 2)
ghz.measure([0, 1, 2], [0, 1, 2])
print("GHZ counts:", run(ghz))            # {'000': 1009, '111': 1039}
```

The middle case is the diagnostic. With only an H gate you get `00` and `01` —
q0 varies, q1 stays at $|0\rangle$, and the state is a product. The CNOT is what
converts one qubit's superposition into a correlation between two.

**Try it.** In the Composer, place **H** on q0 and **CNOT** with control q0,
target q1. Measure all with 2048 shots. Two equal peaks at `00` and `11` with
nothing between them is the signature of a Bell pair.

## Common misconceptions

- **"Entangled qubits share a hidden instruction set."** Bell's theorem rules
  out local hidden-variable explanations: entangled correlations violate
  inequalities that any such model must satisfy.
- **"Measuring one qubit instantly changes the other."** The joint state
  updates on measurement, but no observable change occurs at the distant qubit.
  Its local statistics are unchanged.
- **"Entanglement means the qubits are the same."** $\Psi^+$ is anti-correlated:
  the qubits always disagree. Correlation is not copying — the no-cloning
  theorem forbids copying an unknown state.
- **"More entanglement is always better."** For many algorithms, yes; but
  entanglement is also what decoherence attacks first, as
  **[Quantum Noise](09_quantum_noise.md)** shows.

## Exercises

**1. Product or entangled?** Classify
$\tfrac{1}{2}(|00\rangle + |01\rangle + |10\rangle + |11\rangle)$.

**2. Bell states.** Give the preparation circuit for $\Psi^+$ starting from
$|00\rangle$.

**3. Factorisation.** Prove that $\tfrac{1}{\sqrt2}(|00\rangle + |01\rangle)$ is
a product state by exhibiting the two single-qubit factors.

**4. Correlations.** For $|\Psi^-\rangle$, list the possible measurement
outcomes and their probabilities in the computational basis.

**5. Coding.** Build a three-qubit GHZ state and verify that only `000` and
`111` appear.

### Answers

**1.** It is a **product state**: it equals
$\tfrac{1}{\sqrt2}(|0\rangle + |1\rangle) \otimes \tfrac{1}{\sqrt2}(|0\rangle + |1\rangle) = |+\rangle \otimes |+\rangle$.
This is exactly what you get from H on each qubit with no entangling gate.

**2.** Apply $X$ to q1 to make $|01\rangle$, then H on q0 and CNOT(q0 $\to$ q1).
Equivalently: X(q1), H(q0), CNOT(0 $\to$ 1).

**3.** $\tfrac{1}{\sqrt2}(|00\rangle + |01\rangle) = |0\rangle \otimes |+\rangle$.
The first qubit is determinately $|0\rangle$; only the second is in
superposition. One qubit having a definite state is enough to make the joint
state a product.

**4.** $|\Psi^-\rangle = \tfrac{1}{\sqrt2}(|01\rangle - |10\rangle)$ gives `01`
with probability $\tfrac12$ and `10` with probability $\tfrac12$; `00` and `11`
never occur. The qubits always disagree.

**5.** H(q0), CNOT(0 $\to$ 1), CNOT(0 $\to$ 2), then measure all three.
Verified output: `{'000': 1009, '111': 1039}` over 2048 shots.

## Summary

- A state is entangled when it cannot be written as $|\psi\rangle_A \otimes |\phi\rangle_B$.
- The Bell states are the four maximally entangled two-qubit states; H then CNOT
  prepares $\Phi^+$, with extra Paulis selecting the others.
- Outcomes are individually random but perfectly correlated.
- GHZ states extend perfect correlation to three or more qubits.
- Entanglement cannot transmit information faster than light — no-signalling is
  a theorem, and teleportation needs a classical channel.

Next, **[Measurement and Dynamic Circuits](04_measurement.md)** explains what
happens when you actually look at an entangled state.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §1.3.6, §2.5.
- Einstein, A., Podolsky, B. & Rosen, N. "Can Quantum-Mechanical Description of
  Physical Reality Be Considered Complete?", *Physical Review* 47 (1935) 777.
- Bell, J. S. "On the Einstein Podolsky Rosen paradox", *Physics* 1 (1964) 195.
- Greenberger, D. M., Horne, M. A. & Zeilinger, A. "Going beyond Bell's
  theorem", in *Bell's Theorem, Quantum Theory and Conceptions of the Universe*
  (1989).
- Qiskit documentation, "Entanglement and Bell states":
  https://docs.quantum.ibm.com/
