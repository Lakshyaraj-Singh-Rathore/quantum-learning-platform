# Density Matrices

A state vector describes a system you know everything about. Real hardware
gives you a system you know *something* about: it is entangled with its
environment, it has decohered, or it was prepared by a noisy process. State
vectors have no way to express "I am 70% sure this qubit is in $|0\rangle$."
The **density matrix** does, and it is the standard language for noise,
decoherence and subsystems throughout the rest of this course — including in
the quantum noise lesson and the error-correction lessons.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** the density matrix $\rho = |\psi\rangle\langle\psi|$ for a pure
  state, and state the three properties every density matrix satisfies.
- **Distinguish** pure from mixed states using the purity $\operatorname{tr}(\rho^2)$.
- **Compute** the Bloch vector of a single-qubit state and reconstruct $\rho$
  from it.
- **Evaluate** a partial trace to obtain the reduced density matrix of a
  subsystem, and explain why the reduced state of an entangled pair is mixed.
- **Apply** a dephasing channel to a density matrix and describe how it
  suppresses the off-diagonal terms.

## Motivation: why state vectors are not enough

Suppose a preparation device produces $|0\rangle$ half the time and $|1\rangle$
the other half, and you are not told which. There is no state vector for this
situation. The attempt $\tfrac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$ is wrong in
a measurable way: measured in the computational basis it is indistinguishable
from the coin flip, but measured in the $|+\rangle/|-\rangle$ basis it always
returns $|+\rangle$, whereas the coin flip gives 50/50.

The two situations differ, so they need different mathematical objects. That
object is the density matrix.

## Definition

### Pure states

For a pure state $|\psi\rangle$:

$$\rho = |\psi\rangle\langle\psi|$$

For $|\psi\rangle = \alpha|0\rangle + \beta|1\rangle$:

$$\rho = \begin{pmatrix} |\alpha|^2 & \alpha\beta^* \\ \alpha^*\beta & |\beta|^2 \end{pmatrix}$$

The diagonal entries are the outcome probabilities. The off-diagonal entries
are called **coherences**, and they are what a mixed state loses.

### Mixed states

A general density matrix is a probabilistic mixture:

$$\rho = \sum_k p_k \, |\psi_k\rangle\langle\psi_k|, \qquad p_k \ge 0, \quad \sum_k p_k = 1$$

This is an ensemble-average description. Crucially, the decomposition is not
unique: different ensembles can produce the same $\rho$, and no measurement
can tell them apart.

### The three defining properties

Every density matrix satisfies:

1. **Unit trace**: $\operatorname{tr}(\rho) = 1$.
2. **Hermitian**: $\rho^\dagger = \rho$, so measurement probabilities are real.
3. **Positive semidefinite**: $\langle\phi|\rho|\phi\rangle \ge 0$ for all
   $|\phi\rangle$, so no probability is negative.

Any matrix satisfying all three is a valid density matrix.

## Purity

### Definition

$$\gamma = \operatorname{tr}(\rho^2)$$

For a pure state, $\rho^2 = \rho$ (it is a projector), so $\gamma = 1$. For any
mixed state, $\gamma < 1$. For a single qubit the minimum is $\tfrac{1}{2}$,
attained by the **maximally mixed state**

$$\rho = \frac{I}{2} = \begin{pmatrix} \tfrac{1}{2} & 0 \\ 0 & \tfrac{1}{2} \end{pmatrix}$$

which is the state of complete ignorance: it returns 0 or 1 with equal
probability in *every* measurement basis.

### Worked values

| State | $\rho$ | Purity |
|---|---|---|
| $\|+\rangle$ | $\begin{pmatrix}0.5 & 0.5 \\ 0.5 & 0.5\end{pmatrix}$ | $1$ |
| Maximally mixed | $\begin{pmatrix}0.5 & 0 \\ 0 & 0.5\end{pmatrix}$ | $0.5$ |

Purity is not directly measurable from a single shot, but it is a useful
diagnostic: hardware that is supposed to prepare $|+\rangle$ and instead
returns purity $0.62$ has partially decohered.

## The Bloch vector

### Definition

Any single-qubit density matrix can be written as

$$\rho = \frac{I + \vec{r}\cdot\vec{\sigma}}{2} = \frac{I + r_x X + r_y Y + r_z Z}{2}$$

where $\vec{r} = (r_x, r_y, r_z)$ is the **Bloch vector** and $\vec{\sigma}$
is the vector of Pauli matrices. The components are recovered by

$$r_i = \operatorname{tr}(\rho\,\sigma_i)$$

### Interpretation

- $|\vec{r}| = 1$: pure state, on the surface of the Bloch sphere.
- $|\vec{r}| = 0$: maximally mixed, at the centre.
- $0 < |\vec{r}| < 1$: mixed, strictly inside.

The purity relates to the Bloch length by

$$\operatorname{tr}(\rho^2) = \frac{1 + |\vec{r}|^2}{2}$$

### Worked example

Taking $\vec{r} = (0.3, -0.5, 0.2)$:

$$\rho = \begin{pmatrix} 0.6 & 0.15 + 0.25i \\ 0.15 - 0.25i & 0.4 \end{pmatrix}$$

and reading the Bloch vector back out via $r_i = \operatorname{tr}(\rho\sigma_i)$
recovers $(0.3, -0.5, 0.2)$. The purity is

$$\frac{1 + |\vec{r}|^2}{2} = \frac{1 + 0.09 + 0.25 + 0.04}{2} = 0.69$$

The state is mixed but not maximally so.

## Reduced density matrices and partial trace

### Why we need them

Given a two-qubit state, what is the state of just the *first* qubit? You
cannot always write down a state vector for it — which is exactly the point.

### Definition

The **reduced density matrix** of subsystem $A$ is obtained by the partial
trace over $B$:

$$\rho_A = \operatorname{tr}_B(\rho_{AB})$$

Concretely, reshape $\rho_{AB}$ into a $2 \times 2 \times 2 \times 2$ array with
indices $(a, b, a', b')$ and contract $b$ with $b'$:

$$\rho_A[a, a'] = \sum_b \rho_{AB}[a, b, a', b]$$

### The signature of entanglement

For the Bell state $|\Phi^+\rangle = \tfrac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$:

$$\rho_A = \begin{pmatrix} 0.5 & 0 \\ 0 & 0.5 \end{pmatrix} = \frac{I}{2}$$

with purity $0.5$. Each qubit on its own is **maximally mixed** — complete
ignorance — even though the pair is in a definite pure state. All the
information lives in the correlations between the qubits, not in either one.

Contrast the product state $|+\rangle|+\rangle$, whose reduced matrix is

$$\rho_A = \begin{pmatrix} 0.5 & 0.5 \\ 0.5 & 0.5 \end{pmatrix}$$

with purity $1$. Tracing out half of a product state leaves a pure state.

**This is the defining computational signature of entanglement:** a pure joint
state whose parts are mixed. The entanglement-measures lesson builds directly
on it.

## Noise as a channel

### The dephasing channel

Noise acts on density matrices as a **quantum channel** — a map that preserves
the three defining properties. The dephasing channel with probability $p$:

$$\rho \mapsto (1 - p)\rho + p \sum_k P_k \rho P_k$$

where $P_k$ are the computational-basis projectors. The effect is to leave the
diagonal alone and scale the coherences by $(1-p)$.

### Worked example

Applying it with $p = 0.5$ to $\rho = |+\rangle\langle+|$:

$$\begin{pmatrix} 0.5 & 0.5 \\ 0.5 & 0.5 \end{pmatrix} \mapsto \begin{pmatrix} 0.5 & 0.25 \\ 0.25 & 0.5 \end{pmatrix}$$

The off-diagonal coherence drops from $0.5$ to $0.25$, and the purity falls
from $1$ to $0.625$. Measurement probabilities in the computational basis are
unchanged — which is precisely why dephasing is easy to miss if you only ever
measure in one basis.

## Practical example

```python
import numpy as np

ket0 = np.array([1, 0], dtype=complex)
ket1 = np.array([0, 1], dtype=complex)
I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
PAULIS = (X, Y, Z)


def purity(rho):
    return np.trace(rho @ rho).real


def bloch(rho):
    return np.array([np.trace(rho @ P).real for P in PAULIS])


# --- pure state -> density matrix ------------------------------------------
plus = (ket0 + ket1) / np.sqrt(2)
rho_plus = np.outer(plus, plus.conj())
print("rho(|+>) =\n", np.round(rho_plus, 4))
print(f"trace = {np.trace(rho_plus).real:.4f}")
print(f"Hermitian: {np.allclose(rho_plus, rho_plus.conj().T)}")
print(f"purity = {purity(rho_plus):.4f}")
print(f"eigenvalues = {np.round(np.linalg.eigvalsh(rho_plus), 6)}")

# --- maximally mixed -------------------------------------------------------
mixed = I2 / 2
print(f"\nmaximally mixed purity = {purity(mixed):.4f}")
for name, rho in (("|+>", rho_plus), ("I/2", mixed)):
    r = bloch(rho)
    print(f"  Bloch({name}) = {np.round(r, 4)}   |r| = {np.linalg.norm(r):.4f}")

# --- Bloch vector -> density matrix and back -------------------------------
r = np.array([0.3, -0.5, 0.2])
rho = (I2 + r[0] * X + r[1] * Y + r[2] * Z) / 2
print("\nrho from Bloch vector:\n", np.round(rho, 4))
print("recovered Bloch:", np.round(bloch(rho), 4))
print(f"(1 + |r|^2)/2 = {(1 + r @ r) / 2:.4f}   tr(rho^2) = {purity(rho):.4f}")

# --- partial trace: entanglement's signature -------------------------------
def partial_trace_b(rho_ab):
    return np.trace(rho_ab.reshape(2, 2, 2, 2), axis1=1, axis2=3)


bell = (np.kron(ket0, ket0) + np.kron(ket1, ket1)) / np.sqrt(2)
rho_bell = np.outer(bell, bell.conj())
rho_a = partial_trace_b(rho_bell)
print("\nreduced rho_A of the Bell state:\n", np.round(rho_a, 4))
print(f"  equals I/2: {np.allclose(rho_a, I2 / 2)}")
print(f"  purity = {purity(rho_a):.4f}")

prod = np.kron(plus, plus)
rho_prod_a = partial_trace_b(np.outer(prod, prod.conj()))
print("\nreduced rho_A of |++> (a product state):\n", np.round(rho_prod_a, 4))
print(f"  purity = {purity(rho_prod_a):.4f}")

# --- dephasing -------------------------------------------------------------
def dephase(rho, p):
    return (1 - p) * rho + p * np.diag(np.diag(rho))


rp = dephase(rho_plus, 0.5)
print("\ndephased |+> at p=0.5:\n", np.round(rp, 4))
print(f"  coherence {rho_plus[0, 1].real:.4f} -> {rp[0, 1].real:.4f}")
print(f"  purity {purity(rho_plus):.4f} -> {purity(rp):.4f}")
```

Running it prints `rho(|+>)` as the all-`0.5` matrix with `purity = 1.0000`,
then contrasts it with the maximally mixed state at `purity = 0.5000`. The
Bloch vectors come out `[1. 0. 0.]` and `[0. 0. 0.]`. Reconstructing from
$\vec{r} = (0.3, -0.5, 0.2)$ recovers that same vector and gives
`tr(rho^2) = 0.6900`, matching $(1 + |\vec{r}|^2)/2$.

The partial-trace section is the important one: the Bell state's reduced
matrix is `[[0.5, 0], [0, 0.5]]` with `purity = 0.5000`, while the product
state $|++\rangle$ comes out pure at `purity = 1.0000`. Dephasing at $p = 0.5$
cuts the coherence from `0.5000` to `0.2500` and the purity from `1.0000` to
`0.6250`.

## Common misconceptions

- **"A density matrix is just a state vector with extra notation."** It
  describes something state vectors cannot: a mixture. The Bell pair's
  individual qubits have no state vector at all.
- **"Mixed means entangled."** Not the same. A qubit sitting in a warm
  laboratory is mixed because of its environment, not because it is entangled
  with another qubit. Entanglement specifically makes the *parts* of a *pure*
  whole mixed.
- **"The ensemble decomposition is unique."** It is not. Many different
  preparations produce the same $\rho$, and no measurement distinguishes them.
- **"Purity is measurable in one shot."** It is not; estimating it needs
  tomography or an ancilla-based swap test across many shots.
- **"Dephasing changes measurement outcomes."** In the computational basis it
  does not. It destroys the coherences, which show up only when you measure in
  a different basis — so single-basis testing hides it.

## Exercises

1. Compute $\rho$ for $|\psi\rangle = \tfrac{1}{\sqrt{2}}(|0\rangle + i|1\rangle)$
   and verify that it is Hermitian with unit trace.
2. Show that $\rho^2 = \rho$ for any pure state, and hence that
   $\operatorname{tr}(\rho^2) = 1$.
3. What is the Bloch vector of $|0\rangle$? Of $|1\rangle$? What is the purity
   of each?
4. Compute the reduced density matrix of both qubits of
   $|\Psi^-\rangle = \tfrac{1}{\sqrt{2}}(|01\rangle - |10\rangle)$. Is it the
   same as for $|\Phi^+\rangle$? Explain why that is expected.
5. Apply the dephasing channel with $p = 1$ to $|+\rangle\langle+|$. What state
   results, and what is its purity?
6. A state has purity $0.85$. Is it pure? What is its Bloch vector length?

## Summary

- A density matrix $\rho = \sum_k p_k |\psi_k\rangle\langle\psi_k|$ has unit
  trace, is Hermitian, and is positive semidefinite; those three properties
  characterise it completely.
- Purity $\operatorname{tr}(\rho^2) = 1$ means pure; the minimum for one qubit
  is $\tfrac{1}{2}$, the maximally mixed state $I/2$.
- Any single-qubit state is $\rho = (I + \vec{r}\cdot\vec{\sigma})/2$ with
  $|\vec{r}| \le 1$, and $\operatorname{tr}(\rho^2) = (1 + |\vec{r}|^2)/2$.
- The partial trace gives a subsystem's reduced state. A pure joint state whose
  parts are mixed is entangled — that is the computational signature.
- Dephasing suppresses the off-diagonal coherences while leaving computational
  basis probabilities unchanged.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §2.4 — the density operator, reduced states and the partial
  trace.
- Preskill, J. *Lecture Notes on Quantum Computation*, Chapter 3 — density
  matrices, the Bloch sphere and quantum channels.
- Qiskit documentation, *Estimator primitive* — expectation values estimated
  from noisy states, the practical use of $\operatorname{tr}(\rho A)$.

---

**Previous:** [The Quantum Postulates](19_quantum_postulates.md) ·
**Next:** [Entanglement Measures](21_entanglement_measures.md)
