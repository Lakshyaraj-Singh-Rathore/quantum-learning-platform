# Qubits and Superposition

A classical bit is either 0 or 1, and nothing else. A **qubit** is the quantum
version of that idea, and the difference is not a detail: a qubit can sit in a
*superposition* of both values at once, and the numbers describing it are
complex amplitudes that can cancel each other out. That cancellation —
interference — is the engine behind every quantum speed-up you will meet later in
this course. This lesson builds the qubit from scratch: what it is, how to write
one down, how to picture it, and how its behaviour differs from a coin that has
simply not been looked at yet.

## Learning objectives

By the end of this lesson you should be able to:

- **Define** a qubit state as a normalised complex linear combination of the
  computational basis states $|0\rangle$ and $|1\rangle$.
- **Calculate** measurement probabilities from amplitudes using the Born rule.
- **Explain** why superposition is not the same as classical uncertainty.
- **Locate** a single-qubit state on the Bloch sphere from its two angles.
- **Distinguish** a relative phase from a global phase, and state which one is
  physically observable.
- **Construct** an equal superposition in Qiskit and interpret the resulting
  measurement histogram.

## What a qubit is

A qubit is a physical system with two distinguishable states, which we label
$|0\rangle$ and $|1\rangle$. These are the **computational basis states**. The
ket notation $|\cdot\rangle$ just means "a column vector", and the label inside
tells you which one:

$$|0\rangle = \begin{pmatrix} 1 \\ 0 \end{pmatrix}, \qquad |1\rangle = \begin{pmatrix} 0 \\ 1 \end{pmatrix}$$

Unlike a classical bit, a qubit does not have to choose. Its most general state
is a **superposition** — a weighted sum of the two basis states:

$$|\psi\rangle = \alpha|0\rangle + \beta|1\rangle, \qquad \alpha, \beta \in \mathbb{C}$$

As a column vector this is simply

$$|\psi\rangle = \begin{pmatrix} \alpha \\ \beta \end{pmatrix}$$

The coefficients $\alpha$ and $\beta$ are called **amplitudes**.

### The normalisation condition

Amplitudes are *not* probabilities. The probability of an outcome is the square
of the magnitude of its amplitude:

$$P(0) = |\alpha|^2, \qquad P(1) = |\beta|^2$$

Since the qubit must be found in *some* state when measured, the probabilities
sum to 1, giving the **normalisation condition**:

$$|\alpha|^2 + |\beta|^2 = 1$$

This is a constraint on what states can physically exist. $\alpha = \beta = 1$
is not a valid qubit state, because it would give total probability 2.

## Why amplitudes are not probabilities

This is the single most important idea in the lesson, so it is worth being
precise.

For a classical random bit — a coin hidden under your hand — the description is
a probability $p$ of heads. Probabilities are real numbers between 0 and 1, and
they *add*. If two routes lead to heads with probabilities 0.5 and 0.5, the
total is 1.

Amplitudes are **complex numbers**, so they can be negative or imaginary. They
add too, but because of their signs they can **cancel**:

$$\frac{1}{\sqrt{2}} + \left(-\frac{1}{\sqrt{2}}\right) = 0$$

An outcome whose amplitudes sum to zero *never happens*, even though each
individual path to it was perfectly possible. This is **destructive
interference**. The opposite effect, **constructive interference**, makes an
outcome certain.

A classical probability can never do this: two positive numbers cannot sum to
zero. That is the structural difference between superposition and ordinary
ignorance, and it is the reason quantum algorithms work.

> **Where the analogy fails.** "A qubit is like a spinning coin" is a popular
> image and it is misleading. A spinning coin is in a definite classical state
> that you happen not to know. A qubit in superposition has no definite value
> at all — and the evidence for that is interference, which a spinning coin
> cannot exhibit.

## Worked example: probabilities from amplitudes

**Given.** A qubit is in the state

$$|\psi\rangle = \frac{3}{5}|0\rangle + \frac{4}{5}i\,|1\rangle$$

**Step 1 — check normalisation.**

$$|\alpha|^2 + |\beta|^2 = \left|\frac{3}{5}\right|^2 + \left|\frac{4}{5}i\right|^2 = \frac{9}{25} + \frac{16}{25} = 1 \quad \checkmark$$

Note that $|i| = 1$, so the factor of $i$ contributes nothing to the magnitude.

**Step 2 — apply the Born rule.**

$$P(0) = |\alpha|^2 = \frac{9}{25} = 0.36, \qquad P(1) = |\beta|^2 = \frac{16}{25} = 0.64$$

**Step 3 — interpret.** Measuring this qubit 10,000 times, you expect roughly
3,600 zeros and 6,400 ones. The $i$ on the $|1\rangle$ amplitude never shows up
in these measurement statistics — but it is not decoration, as the next section
shows.

## The Bloch sphere

Any normalised single-qubit state can be written using two real angles
$\theta$ and $\varphi$:

$$|\psi\rangle = \cos\frac{\theta}{2}\,|0\rangle + e^{i\varphi}\sin\frac{\theta}{2}\,|1\rangle$$

- $\theta$ is the **polar angle**. $\theta = 0$ is the north pole, $|0\rangle$;
  $\theta = \pi$ is the south pole, $|1\rangle$.
- $\varphi$ is the **azimuthal angle**, the position around the equator. It is
  the **relative phase** between the two basis states.

Note the $\theta/2$: the Bloch sphere uses half-angles, which is why orthogonal
states $|0\rangle$ and $|1\rangle$ sit at opposite poles 180° apart rather than
90°.

### Relative phase versus global phase

Consider the two states

$$|+\rangle = \frac{|0\rangle + |1\rangle}{\sqrt{2}}, \qquad |-\rangle = \frac{|0\rangle - |1\rangle}{\sqrt{2}}$$

Both have $|\alpha|^2 = |\beta|^2 = 1/2$, so **measuring either one in the
computational basis gives exactly the same statistics**: a 50/50 coin flip. On
the Bloch sphere they sit on opposite sides of the equator, differing only in
$\varphi$ ($\varphi = 0$ versus $\varphi = \pi$).

They are nonetheless different states, and the difference is physically real —
apply a Hadamard gate to each and $|+\rangle$ returns to $|0\rangle$ while
$|-\rangle$ goes to $|1\rangle$, which *is* distinguishable. This is what
"phase is information" means.

Now consider multiplying an entire state by a phase:

$$|\psi\rangle \quad\text{versus}\quad e^{i\gamma}|\psi\rangle$$

Every measurement probability is unchanged, because
$|e^{i\gamma}\alpha|^2 = |\alpha|^2$. This is a **global phase**, and it is
unobservable: the two states are physically identical. Only the *relative*
phase between basis states carries information.

## Multiple qubits

A register of $n$ qubits lives in a $2^n$-dimensional space and needs $2^n$
complex amplitudes to describe:

$$|\psi\rangle = \sum_{j=0}^{2^n-1} \alpha_j |j\rangle, \qquad \sum_j |\alpha_j|^2 = 1$$

Three qubits need 8 amplitudes. Fifty qubits need about $10^{15}$ — more
numbers than there are atoms in a small planet. This exponential growth is
precisely why simulating quantum computers classically is hard, and why this
platform caps simulations at a modest qubit count.

## Bit ordering convention

This platform follows the **Qiskit convention**: in a bitstring, **qubit 0 is
the rightmost character**. So `001` means qubit 0 is excited while qubits 1 and
2 are in $|0\rangle$.

Every backend here (Aer, Cirq, PennyLane, qBraid) normalises its output to this
convention so that histograms are directly comparable. Getting this backwards is
one of the most common sources of confusion when reading results.

## Practical example

The Hadamard gate $H$ turns $|0\rangle$ into $|+\rangle$. Verified against
**Qiskit 1.2.4** and `qiskit-aer` 0.16.0, using `seed_simulator=1234`:

```python
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

sim = AerSimulator()

def run(qc, shots=1024):
    return sim.run(transpile(qc, sim), shots=shots,
                   seed_simulator=1234).result().get_counts()

# |+> measured in the computational (Z) basis -> about 50/50
qc = QuantumCircuit(1, 1)
qc.h(0)
qc.measure(0, 0)
print("Z basis:", run(qc))          # {'0': 521, '1': 503}

# |+> measured in the X basis (H before measuring) -> always 0
qc2 = QuantumCircuit(1, 1)
qc2.h(0); qc2.h(0)
qc2.measure(0, 0)
print("X basis:", run(qc2))         # {'0': 1024}

# |-> measured in the X basis -> always 1
qc3 = QuantumCircuit(1, 1)
qc3.x(0); qc3.h(0); qc3.h(0)
qc3.measure(0, 0)
print("|-> X basis:", run(qc3))     # {'1': 1024}

# |-> measured in the Z basis -> still about 50/50
qc4 = QuantumCircuit(1, 1)
qc4.x(0); qc4.h(0)
qc4.measure(0, 0)
print("|-> Z basis:", run(qc4))     # {'0': 521, '1': 503}
```

The third and fourth results are the point of the whole lesson. In the
computational basis $|+\rangle$ and $|-\rangle$ are indistinguishable — both
give 521/503 with this seed. Change the measurement basis and they become
perfectly distinguishable, 1024 to 0 in opposite directions. The information
was in the phase all along; you just have to ask the right question.

**Try it.** In the Composer, place a single **H** gate on q0 and press
**Measure All (Append)**. With 1024 shots you should see roughly 512 counts
each of `0` and `1`, and the phase disk will show both amplitudes equal in
magnitude, real and positive.

## Common misconceptions

- **"Superposition means the qubit is really 0 or 1, we just don't know."**
  No — see the interference argument above. If the qubit had a definite hidden
  value, the $|+\rangle$ versus $|-\rangle$ distinction in the X basis could not
  exist.
- **"The amplitudes *are* the probabilities."** Probabilities are $|\alpha|^2$
  and $|\beta|^2$. The amplitudes are complex square roots of them, and their
  signs and phases are what make interference possible.
- **"Any phase matters."** Only *relative* phase is observable. A global phase
  is a mathematical artefact with no physical consequence.
- **"A qubit stores a real number like 0.37."** A qubit's state is described by
  continuous complex amplitudes, but a single measurement yields exactly one
  classical bit. You cannot read out $\alpha$ and $\beta$ from one copy; you
  estimate them statistically from many identical preparations.

## Exercises

**1. Normalisation.** Which of these are valid qubit states?

(a) $|\psi\rangle = \frac{1}{2}|0\rangle + \frac{\sqrt{3}}{2}|1\rangle$

(b) $|\psi\rangle = \frac{1}{\sqrt{2}}|0\rangle + \frac{1}{\sqrt{2}}|1\rangle$

(c) $|\psi\rangle = \frac{3}{5}|0\rangle + \frac{3}{5}|1\rangle$

**2. Probabilities.** For
$|\psi\rangle = \frac{1}{\sqrt{3}}|0\rangle + \sqrt{\frac{2}{3}}\,i\,|1\rangle$,
compute $P(0)$ and $P(1)$, and state how many zeros you expect in 3,000 shots.

**3. Bloch angles.** Write $|1\rangle$ in the $(\theta, \varphi)$ form. What are
$\theta$ and $\varphi$?

**4. Global phase.** Show that $|\psi\rangle = \frac{1}{\sqrt2}(|0\rangle - |1\rangle)$
and $|\phi\rangle = \frac{i}{\sqrt2}(|1\rangle - |0\rangle)$ differ only by a
global phase.

**5. Coding.** Build a circuit that prepares a state with $P(0) = 0.75$ using
`ry`, run it with 4,096 shots, and check the result against theory.

### Answers

**1.** (a) Valid: $\tfrac14 + \tfrac34 = 1$. (b) Valid: $\tfrac12 + \tfrac12 = 1$.
(c) **Invalid**: $\tfrac{9}{25} + \tfrac{9}{25} = \tfrac{18}{25} \neq 1$.

**2.** $P(0) = |\tfrac{1}{\sqrt3}|^2 = \tfrac13$ and
$P(1) = |\sqrt{\tfrac23}\,i|^2 = \tfrac23$. In 3,000 shots expect about 1,000
zeros and 2,000 ones.

**3.** $|1\rangle$ is the south pole: $\theta = \pi$, and $\varphi$ is
undefined (any value gives the same state, since $\sin(\theta/2) = 1$ but the
$|0\rangle$ coefficient is $\cos(\pi/2) = 0$, leaving no relative phase to
measure).

**4.** Rewrite $|\phi\rangle$ by factoring out $-1$ from the bracket:

$$|\phi\rangle = \frac{i}{\sqrt2}(|1\rangle - |0\rangle) = -\frac{i}{\sqrt2}(|0\rangle - |1\rangle) = -i\,|\psi\rangle$$

A factor of $-i$ multiplies the entire state, so it is a global phase and the
two states are physically identical.

**5.** Use $\theta = 2\arccos(\sqrt{0.75}) \approx 1.0472$, which gives
amplitudes $(0.866, 0.5)$ and $P(0) = 0.75$:

```python
import numpy as np
qc = QuantumCircuit(1, 1)
qc.ry(2 * np.arccos(np.sqrt(0.75)), 0)
qc.measure(0, 0)
print(run(qc, shots=4096))   # {'0': 3099, '1': 997}  -> 3099/4096 = 0.757
```

The measured 0.757 differs from the exact 0.75 because 4,096 shots give a
standard error of about $\sqrt{0.75 \times 0.25 / 4096} \approx 0.0068$; the
gap is well within one standard error.

## Summary

- A qubit's state is $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$ with
  $|\alpha|^2 + |\beta|^2 = 1$.
- Probabilities come from squared magnitudes of amplitudes (the Born rule) —
  amplitudes themselves are complex and can interfere.
- The Bloch sphere parametrises any single-qubit state by polar angle $\theta$
  and relative phase $\varphi$.
- Relative phase is physical; global phase is not.
- Superposition is not classical ignorance: interference is the observable
  difference.
- This platform uses the Qiskit bit-ordering convention, qubit 0 rightmost.

Next, **[Quantum Gates](02_gates.md)** shows how to move a qubit around the
Bloch sphere — which is what every quantum computation is made of.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §1.2.
- Qiskit documentation, "Introduction to Quantum Circuits and Computational
  Basis": https://docs.quantum.ibm.com/
- IBM Quantum Learning, "The Bloch sphere": https://learning.quantum.ibm.com/
- Qiskit 1.2.4 release notes (API changes from 0.x):
  https://docs.quantum.ibm.com/api/qiskit/release-notes
