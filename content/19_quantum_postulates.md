# The Quantum Postulates

Everything in quantum computing follows from four postulates. They state what
a quantum state *is*, how it *changes*, what happens when you *measure* it, and
how *several* systems combine. Most of the confusion people carry into quantum
computing comes from having an informal grip on one or two of these and no
grip at all on the others — particularly the third, which is where the
"measurement is just reading off a value" intuition breaks. This lesson states
all four precisely and works through each with explicit matrices.

## Learning objectives

By the end of this lesson you should be able to:

- **State** the four postulates of quantum mechanics, and name which physical
  operation each one governs.
- **Compute** Born-rule probabilities for a given state and measurement basis.
- **Verify** that a matrix is unitary, and show that unitary evolution
  preserves the norm of a state.
- **Apply** projective measurement, including renormalising the post-measurement
  state, and explain why the state collapses.
- **Construct** the joint state of a composite system using the tensor product.

## Postulate 1 — State space

### Formal statement

The state of an isolated quantum system is described by a **unit vector** in a
complex Hilbert space. For a single qubit:

$$|\psi\rangle = \alpha|0\rangle + \beta|1\rangle = \begin{pmatrix} \alpha \\ \beta \end{pmatrix}, \qquad \alpha, \beta \in \mathbb{C}$$

with the normalisation condition

$$|\alpha|^2 + |\beta|^2 = 1$$

The basis vectors are

$$|0\rangle = \begin{pmatrix} 1 \\ 0 \end{pmatrix}, \qquad |1\rangle = \begin{pmatrix} 0 \\ 1 \end{pmatrix}$$

### What "unit vector" buys you

Normalisation is not cosmetic. It is what makes the numbers $|\alpha|^2$ and
$|\beta|^2$ behave as probabilities in Postulate 3. A state with
$\langle\psi|\psi\rangle \neq 1$ is not a state.

### Global phase is not observable

The states $|\psi\rangle$ and $e^{i\theta}|\psi\rangle$ are **physically
identical**. Multiplying by a global phase changes $\alpha$ and $\beta$ but
leaves $|\alpha|^2$ and $|\beta|^2$ untouched, and those are the only
quantities Postulate 3 ever uses. This is worth stating early, because it is
the source of a very common error: *relative* phase between $\alpha$ and
$\beta$ is measurable, *global* phase is not.

## Postulate 2 — Evolution

### Formal statement

The time evolution of a closed quantum system is described by a **unitary**
operator. A matrix $U$ is unitary when

$$U^\dagger U = UU^\dagger = I$$

and the state transforms as

$$|\psi'\rangle = U|\psi\rangle$$

Unitarity is exactly the condition that preserves normalisation:

$$\langle\psi'|\psi'\rangle = \langle\psi|U^\dagger U|\psi\rangle = \langle\psi|\psi\rangle = 1$$

So evolution maps valid states to valid states — it cannot quietly break
Postulate 1.

### Worked example

The rotation matrix

$$R(\theta) = \begin{pmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{pmatrix}$$

is unitary for every real $\theta$. Taking $\theta = 0.7$ and
$|\psi\rangle = 0.6|0\rangle + 0.8|1\rangle$:

$$\langle\psi|\psi\rangle = 1.0 \quad\text{before},\qquad \langle\psi'|\psi'\rangle = 1.0 \quad\text{after}$$

Up to floating-point representation, the norm is unchanged — which is the
whole point. In quantum computing every gate is unitary, so **every quantum
circuit is reversible**. That is why there is no quantum analogue of the
classical AND gate, and why algorithms have to be built to uncompute their
scratch space.

## Postulate 3 — Measurement

### Formal statement

A measurement is described by a set of **projection operators** $\{P_m\}$ that
partition the identity:

$$\sum_m P_m = I, \qquad P_m P_n = \delta_{mn} P_m$$

The probability of outcome $m$ is given by the **Born rule**:

$$p(m) = \langle\psi|P_m|\psi\rangle$$

and, conditional on outcome $m$, the state becomes

$$|\psi_m\rangle = \frac{P_m|\psi\rangle}{\sqrt{p(m)}}$$

### Computational-basis measurement

For the standard measurement on one qubit:

$$P_0 = |0\rangle\langle 0| = \begin{pmatrix} 1 & 0 \\ 0 & 0 \end{pmatrix}, \qquad P_1 = |1\rangle\langle 1| = \begin{pmatrix} 0 & 0 \\ 0 & 1 \end{pmatrix}$$

These satisfy $P_0^2 = P_0$, $P_0 P_1 = 0$ and $P_0 + P_1 = I$, as required.

Applying them to $|\psi\rangle = 0.6|0\rangle + 0.8|1\rangle$:

$$p(0) = \langle\psi|P_0|\psi\rangle = |0.6|^2 = 0.36$$

$$p(1) = \langle\psi|P_1|\psi\rangle = |0.8|^2 = 0.64$$

The probabilities sum to 1, as they must.

### Collapse is the part people resist

If the outcome is 0, the post-measurement state is

$$|\psi_0\rangle = \frac{P_0|\psi\rangle}{\sqrt{0.36}} = \frac{1}{0.6}\begin{pmatrix} 0.6 \\ 0 \end{pmatrix} = \begin{pmatrix} 1 \\ 0 \end{pmatrix} = |0\rangle$$

The superposition is **gone**. You do not "partially observe" a qubit and keep
the rest; the state has been projected, and a second measurement in the same
basis returns 0 with probability 1.

This is why quantum algorithms are delicate: information that was in the
amplitudes is destroyed by measuring, so algorithms must arrange for the
answer to survive the measurement that reads it out.

### Expectation values

For an observable with eigenvalues $\lambda_m$ and projectors $P_m$:

$$\langle A \rangle = \sum_m \lambda_m \, p(m) = \langle\psi|A|\psi\rangle$$

For $Z$, with eigenvalues $+1$ and $-1$:

$$\langle Z \rangle = p(0) - p(1) = 0.36 - 0.64 = -0.28$$

which matches $\langle\psi|Z|\psi\rangle$ directly. The general lesson: an
expectation value is a probability-weighted average of outcomes, and
estimating it on hardware means averaging over many shots.

## Postulate 4 — Composite systems

### Formal statement

The state space of a composite system is the **tensor product** of the parts:

$$|\psi\rangle_{AB} = |\psi\rangle_A \otimes |\psi\rangle_B$$

For two qubits, each with basis $\{|0\rangle, |1\rangle\}$, the joint basis is

$$\{|00\rangle, |01\rangle, |10\rangle, |11\rangle\}$$

and a general two-qubit state is

$$|\psi\rangle = \alpha_{00}|00\rangle + \alpha_{01}|01\rangle + \alpha_{10}|10\rangle + \alpha_{11}|11\rangle$$

with $\sum_{ij} |\alpha_{ij}|^2 = 1$.

### Why this matters

The tensor product is what makes quantum computing scale the way it does. One
qubit needs 2 complex amplitudes; two need 4; $n$ qubits need $2^n$. That
exponential is the reason a 50-qubit state cannot be written down
classically — and the reason the *Challenge* and *Grover* labs cap their qubit
counts.

Not every two-qubit state can be written as a product of two one-qubit states.
Those that cannot are **entangled**, and they are the subject of the
entanglement lessons that follow.

## Practical example

```python
import numpy as np

ket0 = np.array([1, 0], dtype=complex)
ket1 = np.array([0, 1], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)

# --- Postulate 1: a normalised state ---------------------------------------
psi = np.array([0.6, 0.8], dtype=complex)
print(f"norm = {np.vdot(psi, psi).real:.4f}")

# --- Postulate 2: unitary evolution preserves the norm ---------------------
theta = 0.7
R = np.array([[np.cos(theta), -np.sin(theta)],
              [np.sin(theta),  np.cos(theta)]], dtype=complex)
print(f"R is unitary: {np.allclose(R.conj().T @ R, np.eye(2))}")
evolved = R @ psi
print(f"norm before = {np.vdot(psi, psi).real:.4f}"
      f"   after = {np.vdot(evolved, evolved).real:.4f}")

# --- Postulate 3: projective measurement -----------------------------------
P0 = np.outer(ket0, ket0)          # |0><0|
P1 = np.outer(ket1, ket1)          # |1><1|
print(f"\nP0^2 == P0: {np.allclose(P0 @ P0, P0)}")
print(f"P0 @ P1 == 0: {np.allclose(P0 @ P1, 0)}")
print(f"P0 + P1 == I: {np.allclose(P0 + P1, np.eye(2))}")

p0 = np.vdot(psi, P0 @ psi).real
p1 = np.vdot(psi, P1 @ psi).real
print(f"p(0) = {p0:.4f}   p(1) = {p1:.4f}   sum = {p0 + p1:.4f}")

# collapse and renormalise
collapsed = P0 @ psi
collapsed = collapsed / np.linalg.norm(collapsed)
print(f"state after outcome 0: {collapsed}")

# expectation value two ways
print(f"\n<psi|Z|psi> = {np.vdot(psi, Z @ psi).real:.4f}")
print(f"p(0) - p(1) = {p0 - p1:.4f}")

# --- global phase is not observable ----------------------------------------
phased = np.exp(1j * 1.3) * psi
print(f"\n|components|^2 unchanged by global phase: "
      f"{np.allclose(np.abs(phased) ** 2, np.abs(psi) ** 2)}")

# --- Postulate 4: composite systems ----------------------------------------
bell = (np.kron(ket0, ket0) + np.kron(ket1, ket1)) / np.sqrt(2)
print(f"\nBell state {bell}")
print(f"amplitudes needed for 2 qubits: {bell.size}"
      f"   (2**2 = {2**2})")
```

Running it prints `norm = 1.0000`, confirms `R is unitary: True`, and shows the
norm is unchanged by evolution. The projectors pass all three defining
tests, and the Born rule gives `p(0) = 0.3600`, `p(1) = 0.6400`, summing to
`1.0000`. After collapsing on outcome 0 the state is `[1.+0.j 0.+0.j]`, the
expectation value is `-0.2800` by both routes, and the global-phase check
returns `True`.

## Common misconceptions

- **"Measurement reveals a pre-existing value."** The state before measurement
  is a superposition; the outcome is created by the measurement, not read off
  a hidden variable. Collapse is real, and it destroys the other amplitudes.
- **"Global and relative phase are the same thing."** Global phase is
  unobservable. Relative phase is what gates manipulate and what interference
  depends on.
- **"Unitary evolution is optional — states just need renormalising."**
  Renormalising after a non-unitary step hides the error: probabilities were
  already wrong in between. Unitarity is the constraint that keeps every
  intermediate state physical.
- **"Two qubits need four times the information of one."** They need $2^n$
  amplitudes, so two qubits need 4 and fifty need about $10^{15}$. The scaling
  is exponential, not linear.
- **"The expectation value is the most likely outcome."** It is the average
  over outcomes, weighted by probability. For $Z$ the possible results are
  $\pm 1$, but $\langle Z \rangle = -0.28$ is neither of them.

## Exercises

1. Verify that $|\psi\rangle = \tfrac{1}{\sqrt{2}}(|0\rangle + i|1\rangle)$ is
   normalised, and compute $p(0)$ and $p(1)$.
2. Show that the Hadamard matrix is unitary by computing $H^\dagger H$.
3. For $|\psi\rangle = 0.6|0\rangle + 0.8|1\rangle$, compute the probabilities
   of $|+\rangle$ and $|-\rangle$ by constructing $P_+ = |+\rangle\langle +|$
   and $P_- = |-\rangle\langle -|$.
4. Explain why no quantum gate can implement the classical map
   $(a, b) \mapsto (a \text{ AND } b)$. Which postulate rules it out?
5. Write out the tensor product $|+\rangle \otimes |1\rangle$ explicitly as a
   four-component vector.
6. A state has $p(0) = 0.5$. What is $\langle Z \rangle$? What does that say
   about the information a single expectation value carries?

## Summary

- **Postulate 1**: states are unit vectors in a complex Hilbert space,
  $|\alpha|^2 + |\beta|^2 = 1$. Global phase is unobservable.
- **Postulate 2**: closed-system evolution is unitary, $U^\dagger U = I$, which
  preserves normalisation and makes every gate reversible.
- **Postulate 3**: measurement uses projectors with $\sum_m P_m = I$; the Born
  rule gives $p(m) = \langle\psi|P_m|\psi\rangle$, and the state collapses to
  $P_m|\psi\rangle / \sqrt{p(m)}$.
- **Postulate 4**: composite systems combine by tensor product, giving $2^n$
  amplitudes for $n$ qubits.
- Expectation values are probability-weighted averages,
  $\langle A \rangle = \langle\psi|A|\psi\rangle$, estimated on hardware by
  averaging shots.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §2.2 — the quantum postulates, stated in full.
- Dirac, P. A. M. *The Principles of Quantum Mechanics* — the original
  development of the bra-ket formalism used throughout.
- Qiskit documentation, *Sampler primitive* — the shot interface through which
  Postulate 3 is observed in practice.

---

**Previous:** [Introductory Group Theory](18_group_theory.md) ·
**Next:** [Density Matrices](20_density_matrices.md)
