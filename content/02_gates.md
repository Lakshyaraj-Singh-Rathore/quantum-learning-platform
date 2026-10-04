# Quantum Gates

If a qubit is the memory of a quantum computer, gates are its instructions. Every
quantum gate is a **unitary matrix**, and that single algebraic fact explains
almost everything about them: they are reversible, they preserve total
probability, and they rotate rather than scramble. This lesson catalogues the
gates you will actually use, shows the matrices behind them, and explains how a
handful of gates becomes a universal toolkit.

## Learning objectives

By the end of this lesson you should be able to:

- **State** the unitarity condition and explain why it implies reversibility.
- **Write** the matrix of X, Y, Z, H, S and T, and predict each one's action on
  $|0\rangle$ and $|1\rangle$.
- **Explain** why $H^2 = I$ and how that reveals interference.
- **Construct** a rotation that prepares a chosen superposition angle using
  `rx`, `ry` or `rz`.
- **Describe** how CNOT creates entanglement and why multi-controlled gates are
  expensive on hardware.
- **Enter** gate parameters in the format this platform accepts, and explain why
  free variables are rejected.

## Why gates must be unitary

A gate is a matrix $U$ acting on the state vector, taking $|\psi\rangle$ to
$U|\psi\rangle$. For the result to be a valid quantum state, probabilities must
still sum to 1:

$$\langle\psi|U^\dagger U|\psi\rangle = \langle\psi|\psi\rangle = 1$$

This holds for every $|\psi\rangle$ exactly when

$$U^\dagger U = I$$

which is the definition of a **unitary** matrix. Two consequences follow
immediately:

1. **Probability is conserved.** Amplitudes get redistributed, never created or
   destroyed.
2. **Every gate is reversible.** $U^{-1} = U^\dagger$ always exists. This is
   quantum computing's sharpest difference from classical logic: there is no
   quantum AND gate, because AND throws information away.

Measurement and reset are the only irreversible operations in the palette, and
they are not unitary — which is exactly why they are not reversible.

## The single-qubit gates

In the computational basis $\{|0\rangle, |1\rangle\}$:

$$X = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix},\quad Y = \begin{pmatrix} 0 & -i \\ i & 0 \end{pmatrix},\quad Z = \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}$$

$$H = \frac{1}{\sqrt2}\begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix},\quad S = \begin{pmatrix} 1 & 0 \\ 0 & i \end{pmatrix},\quad T = \begin{pmatrix} 1 & 0 \\ 0 & e^{i\pi/4} \end{pmatrix}$$

| Gate | Name | Action |
|------|------|--------|
| **X** | Pauli-X / NOT | Bit flip: swaps $|0\rangle \leftrightarrow |1\rangle$ |
| **Y** | Pauli-Y | Bit *and* phase flip; $Y = iXZ$ |
| **Z** | Pauli-Z | Phase flip: $|0\rangle \to |0\rangle$, $|1\rangle \to -|1\rangle$ |
| **H** | Hadamard | Creates superposition; maps the Z-basis to the X-basis |
| **S** / **Sdg** | Phase / its inverse | Quarter turn, phase $\pm i$ on $|1\rangle$ |
| **T** / **Tdg** | $\pi/8$ / its inverse | Eighth turn, phase $e^{\pm i\pi/4}$ on $|1\rangle$ |
| **SX** | Square root of X | Half a bit flip; $SX^2 = X$ |
| **I** | Identity | Does nothing; useful as a placeholder or delay |

### The Hadamard is the workhorse

$$H|0\rangle = \frac{|0\rangle + |1\rangle}{\sqrt2} = |+\rangle, \qquad H|1\rangle = \frac{|0\rangle - |1\rangle}{\sqrt2} = |-\rangle$$

Note the **minus sign** in $H|1\rangle$. It is the reason $H^2 = I$: applying $H$
to $|+\rangle$ sends $|0\rangle$ and $|1\rangle$ back toward each other, and the
amplitudes arriving at $|1\rangle$ are $+\tfrac{1}{2}$ and $-\tfrac{1}{2}$, which
cancel exactly. Applying $H$ twice returns the original state because the two
paths interfere destructively. This is not a coincidence — it is interference
doing the work.

## Rotation and phase gates

**RX($\theta$)**, **RY($\theta$)** and **RZ($\theta$)** rotate the Bloch vector
by $\theta$ radians about the X, Y and Z axes. **P($\lambda$)** applies a
relative phase $e^{i\lambda}$ to $|1\rangle$ only.

Rotations are the continuous knobs. Where $H$ gives you one specific
equal superposition, $RY(\theta)$ gives you any split you like:

$$RY(\theta)|0\rangle = \cos\frac{\theta}{2}\,|0\rangle + \sin\frac{\theta}{2}\,|1\rangle$$

Verified against Qiskit 1.2.4: for $\theta = \pi/3$ the amplitudes are
$(0.8660, 0.5000)$, giving $P(0) = 0.75$ and $P(1) = 0.25$.

Several familiar gates are just special cases of P:

- $Z = P(\pi)$
- $S = P(\pi/2)$
- $T = P(\pi/4)$

(These hold up to a global phase, which as you learned in
[Qubits and Superposition](01_qubits.md) has no physical effect.)

### Parameter entry in this platform

Parameters accept numeric radians or expressions built **only** from `pi`,
numbers and the operators `+ - * / ( )`. Valid: `pi/2`, `3*pi/4`, `-0.5*pi`,
`1.234`. The parser is deliberately restricted — it evaluates your expression
against a character allow-list rather than a general expression evaluator.

**Free variables such as `theta` are rejected.** This is intentional: every
circuit must be numerically executable the moment you press Run. A symbolic
parameter would have no value to simulate with.

## Multi-qubit gates

Single-qubit gates cannot entangle. You need at least one two-qubit gate, and
CNOT is the standard one.

$$\text{CNOT} = \begin{pmatrix} 1&0&0&0 \\ 0&1&0&0 \\ 0&0&0&1 \\ 0&0&1&0 \end{pmatrix}$$

It flips the **target** qubit if and only if the **control** is $|1\rangle$:

| Gate | Behaviour |
|------|-----------|
| **CNOT / CX** | Flips target iff control is $|1\rangle$. The standard entangling gate. |
| **CZ** | Applies phase $-1$ only to $|11\rangle$. Symmetric in its two qubits. |
| **SWAP** | Exchanges the states of two qubits. |
| **Toffoli / CCX** | Flips target iff *both* controls are $|1\rangle$. Universal for classical reversible computation. |
| **MCX** | Multi-controlled X with any number of controls. |

### How controls work in the composer

Drop the gate on its **target** qubit, then click the qubits in the same column
that should act as **controls**. The editor draws the control dots and the
vertical connector.

Internally a controlled gate is stored as a base gate plus a list of control
qubits, so `cx`, `ccx` and a five-controlled X are all the same structure —
which is why the platform can render and execute them uniformly.

**Multi-controlled gates are convenient but expensive.** After transpilation to
a hardware basis, an MCX with many controls decomposes into a long sequence of
two-qubit gates. A 5-controlled X is not one operation; it is dozens.

## Universality and transpilation

A small gate set is **universal** if it can approximate any unitary to arbitrary
accuracy. One such set is $\{H, T, \text{CNOT}\}$: $H$ and $T$ generate all
single-qubit rotations, and CNOT supplies the interaction.

There is a catch: the Solovay–Kitaev theorem guarantees *approximation*, not
exactness, and the number of gates grows. Exact synthesis is possible with
different sets, but hardware does not implement those either.

Real hardware exposes only its own native set, so a compiler must rewrite your
circuit. **This platform transpiles every static circuit to the portable basis
`rx, ry, rz, cx`** before handing it to Cirq, PennyLane or qBraid. That
guarantees all backends execute the *same* normalized program, which is why
their histograms agree.

## Practical example

Verified against **Qiskit 1.2.4** and `qiskit-aer` 0.16.0, `seed_simulator=1234`:

```python
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Operator, Statevector

sim = AerSimulator()

def run(qc, shots=1024):
    return sim.run(transpile(qc, sim), shots=shots,
                   seed_simulator=1234).result().get_counts()

# H^2 = I: two Hadamards return the qubit to |0>
qc = QuantumCircuit(1, 1)
qc.h(0); qc.h(0)
qc.measure(0, 0)
print("H twice:", run(qc))            # {'0': 1024}

# H|1> = |-> : equal magnitudes, opposite signs
sv = QuantumCircuit(1)
sv.x(0); sv.h(0)
print("H|1> amplitudes:", np.round(Statevector(sv).data, 4))   # [0.7071, -0.7071]

# RY(pi/3) prepares a 75/25 split
qc2 = QuantumCircuit(1, 1)
qc2.ry(np.pi / 3, 0)
qc2.measure(0, 0)
print("RY(pi/3):", run(qc2))          # {'0': 768, '1': 256}  -> 0.750

# Z, S, T are phase gates: no effect on computational-basis statistics
for name, gate in [("z", "z"), ("s", "s"), ("t", "t")]:
    c = QuantumCircuit(1, 1)
    c.h(0)
    getattr(c, gate)(0)
    c.h(0)                            # back to Z basis: phase becomes visible
    c.measure(0, 0)
    print(f"H {name.upper()} H:", run(c))

# CNOT turns a superposition into entanglement
bell = QuantumCircuit(2, 2)
bell.h(0)
bell.cx(0, 1)
bell.measure([0, 1], [0, 1])
print("Bell:", run(bell, 2048))       # {'00': 1022, '11': 1026}
```

The `H Z H` result is worth staring at: with the bare $Z$ you saw no change in
measurement statistics, but sandwiching it between two Hadamards moves the phase
difference into the computational basis, where it becomes a visible bit flip.

**Try it.** In the Composer, place **H** then **Z** then **H** on q0 and run
with 1024 shots. You should get all `1`, demonstrating that $HZH = X$.

## Common misconceptions

- **"A quantum gate can implement any classical function."** Only if you make it
  reversible. Unitary gates cannot erase, so irreversible classical operations
  must be embedded in a reversible form.
- **"Z does nothing."** It does nothing to $|0\rangle$ and $|1\rangle$ measured
  in the computational basis — but it changes $|+\rangle$ into $|-\rangle$.
  Phase is invisible until you choose a basis that reveals it.
- **"More controls is just slightly more expensive."** Decomposition cost grows
  steeply with control count; a large MCX can dominate a whole circuit.
- **"Gates act on qubits independently."** Two-qubit gates are precisely where
  that stops being true, and where quantum computing gets its power.

## Exercises

**1. Unitarity.** Show that $H$ is unitary by computing $H^\dagger H$.

**2. Prediction.** What state results from applying $X$ then $H$ to $|0\rangle$?
What are the measurement probabilities in the computational basis?

**3. Rotations.** What angle $\theta$ makes $RY(\theta)|0\rangle$ give $P(1) = 0.5$?
What about $P(1) = 1$?

**4. Phase gates.** Verify that $S$ and $T$ differ only in the size of the phase
they apply, and state each phase in radians.

**5. Coding.** Build a circuit that applies $H$ to q0, then CNOT with q0 as
control and q1 as target, and measure. Report the outcome distribution.

### Answers

**1.** $H$ is real and symmetric, so $H^\dagger = H$. Then
$H^\dagger H = H^2 = \tfrac12\begin{pmatrix}1&1\\1&-1\end{pmatrix}^2 = \begin{pmatrix}1&0\\0&1\end{pmatrix} = I$.

**2.** $H X |0\rangle = H|1\rangle = |-\rangle = \tfrac{1}{\sqrt2}(|0\rangle - |1\rangle)$.
Both $|0\rangle$ and $|1\rangle$ have probability $\tfrac12$.

**3.** $P(1) = \sin^2(\theta/2)$. For $P(1) = 0.5$: $\sin(\theta/2) = 1/\sqrt2$, so
$\theta/2 = \pi/4$ and $\theta = \pi/2$. For $P(1) = 1$:
$\sin(\theta/2) = 1$, so $\theta = \pi$.

**4.** $S$ applies $e^{i\pi/2} = i$; $T$ applies $e^{i\pi/4}$. Both leave
$|0\rangle$ untouched and multiply only $|1\rangle$, so they differ solely in
phase magnitude: a quarter turn versus an eighth turn.

**5.**

```python
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])
print(run(qc, 2048))   # {'00': 1022, '11': 1026}
```

Only `00` and `11` appear, never `01` or `10`. That absence is the signature of
entanglement, explained in **[Entanglement](03_entanglement.md)**.

## Summary

- Gates are unitary matrices: $U^\dagger U = I$, giving reversibility and
  probability conservation.
- X, Y, Z are the Paulis; H creates superposition; S and T add finer phases.
- RX/RY/RZ give continuous control; P($\lambda$) phases $|1\rangle$ only, and
  $Z = P(\pi)$, $S = P(\pi/2)$, $T = P(\pi/4)$.
- CNOT is the standard entangling gate; multi-controlled gates are costly.
- $\{H, T, \text{CNOT}\}$ is universal in the approximate sense.
- This platform transpiles to the portable basis `rx, ry, rz, cx`, and accepts
  parameters built only from `pi`, numbers and `+ - * / ( )`.

Next, **[Entanglement](03_entanglement.md)** uses CNOT to build states with no
classical analogue.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §4.2–4.5.
- Qiskit documentation, "Quantum gates and circuits":
  https://docs.quantum.ibm.com/
- IBM Quantum Learning, "Quantum gates and circuits":
  https://learning.quantum.ibm.com/
- Solovay, R. & Kitaev, A. Yu. on universal gate approximation, in Kitaev, A.
  Yu., *Russian Mathematical Surveys* 52 (1997) 1191.
