# Entanglement Measures

The density matrices lesson ended with a striking fact: for a Bell pair, each
qubit on its own is maximally mixed even though the pair is in a definite pure
state. That gives a *yes/no* test for entanglement. But "is it entangled?"
quickly stops being the interesting question. A state can be a little
entangled or a lot, and algorithms differ in how much they need. This lesson
builds two quantitative measures — entanglement entropy and concurrence — and
shows that for pure states they are two faces of the same thing: the Schmidt
decomposition.

## Learning objectives

By the end of this lesson you should be able to:

- **Compute** the Schmidt decomposition of a bipartite pure state, and read off
  the Schmidt coefficients.
- **Evaluate** the von Neumann entropy of a reduced density matrix, and
  interpret it as an entanglement measure in bits.
- **Calculate** the concurrence of a two-qubit pure state, and state its range
  for product and maximally entangled states.
- **Compare** two states by their entanglement, including partially entangled
  ones where the answer is not simply 0 or 1.
- **Explain** why a pure state's entanglement is determined entirely by its
  Schmidt coefficients.

## The Schmidt decomposition

### Formal statement

For any pure state $|\psi\rangle$ of a bipartite system $A \otimes B$, there
exist orthonormal bases $\{|u_k\rangle\}$ for $A$ and $\{|v_k\rangle\}$ for
$B$, and non-negative real numbers $s_k$, such that

$$|\psi\rangle = \sum_k s_k \, |u_k\rangle \otimes |v_k\rangle$$

The $s_k$ are the **Schmidt coefficients**, satisfying $\sum_k s_k^2 = 1$. They
are uniquely determined by $|\psi\rangle$ even though the bases are not.

### How to compute them

Reshape the state into a matrix $M$ whose rows index $A$'s basis and columns
index $B$'s, then take the singular values. For two qubits:

$$M = \begin{pmatrix} \alpha_{00} & \alpha_{01} \\ \alpha_{10} & \alpha_{11} \end{pmatrix}, \qquad (s_0, s_1) = \text{svd}(M)$$

### The key consequence

The reduced density matrix of either side has eigenvalues $s_k^2$:

$$\rho_A = \sum_k s_k^2 \, |u_k\rangle\langle u_k|$$

So **the number of non-zero Schmidt coefficients — the Schmidt rank — is 1 for
a product state and greater than 1 for an entangled one.** A product state has
one coefficient; a maximally entangled two-qubit state has two equal ones.

## Entanglement entropy

### Von Neumann entropy

For a density matrix $\rho$ with eigenvalues $\lambda_k$:

$$S(\rho) = -\operatorname{tr}(\rho \log_2 \rho) = -\sum_k \lambda_k \log_2 \lambda_k$$

with the convention $0 \log 0 = 0$.

### As an entanglement measure

For a bipartite **pure** state, the entanglement entropy is the von Neumann
entropy of either reduced state:

$$E(|\psi\rangle) = S(\rho_A) = S(\rho_B) = -\sum_k s_k^2 \log_2 s_k^2$$

Both sides give the same answer, because the non-zero eigenvalues of $\rho_A$
and $\rho_B$ are the same $s_k^2$.

### Worked values

| State | Schmidt coefficients | $S(\rho_A)$ | Entangled? |
|---|---|---|---|
| $\|00\rangle$ | $(1, 0)$ | $0$ bits | No |
| $\|+\rangle\|+\rangle$ | $(1, 0)$ | $0$ bits | No |
| $\cos(0.3)\|00\rangle + \sin(0.3)\|11\rangle$ | $(0.955, 0.296)$ | $0.428$ bits | Yes |
| $\cos(\tfrac{\pi}{8})\|00\rangle + \sin(\tfrac{\pi}{8})\|11\rangle$ | $(0.924, 0.383)$ | $0.601$ bits | Yes |
| $\|\Phi^+\rangle$ Bell | $(0.707, 0.707)$ | $1$ bit | Maximally |

For the Bell state the reduced eigenvalues are $(\tfrac{1}{2}, \tfrac{1}{2})$, so

$$S = -\left(\tfrac{1}{2}\log_2\tfrac{1}{2} + \tfrac{1}{2}\log_2\tfrac{1}{2}\right) = -2 \cdot \tfrac{1}{2} \cdot (-1) = 1 \text{ bit}$$

That is the maximum possible for two qubits: one bit of entanglement,
corresponding to one maximally entangled pair.

### Why the reduced state being mixed signals entanglement

Recall the result that motivates this lesson: if $|\psi\rangle$ is pure but
$\rho_A$ is mixed, the state is entangled. Entropy quantifies *how* mixed. $S = 0$
means $\rho_A$ is pure and there is no entanglement; $S = 1$ means it is
maximally mixed and the entanglement is maximal.

## Concurrence

### Motivation

Entanglement entropy is defined cleanly for pure bipartite states. For mixed
states it no longer separates entanglement from ordinary classical
uncertainty, and a different measure is used. **Concurrence** is the standard
two-qubit measure, and it extends to mixed states.

### Definition for pure states

For $|\psi\rangle = a|00\rangle + b|01\rangle + c|10\rangle + d|11\rangle$:

$$C(|\psi\rangle) = 2|ad - bc|$$

Equivalently, and more convenient in code:

$$C(|\psi\rangle) = |\langle\psi| (Y \otimes Y) |\psi^*\rangle|$$

where $|\psi^*\rangle$ is the elementwise complex conjugate.

### Range

- $C = 0$: product state, no entanglement.
- $C = 1$: maximally entangled (the Bell states).
- $0 < C < 1$: partially entangled.

### Worked values

| State | Concurrence |
|---|---|
| $\|00\rangle$ | $0.000$ |
| $\|+\rangle\|+\rangle$ | $0.000$ |
| $\cos(0.3)\|00\rangle + \sin(0.3)\|11\rangle$ | $0.565$ |
| $\cos(\tfrac{\pi}{8})\|00\rangle + \sin(\tfrac{\pi}{8})\|11\rangle$ | $0.707$ |
| $\|\Phi^+\rangle$ Bell | $1.000$ |

### How the two measures relate

For pure two-qubit states, concurrence and entanglement entropy are
monotonically related — both are functions of the single Schmidt parameter.
Given Schmidt coefficients $(s_0, s_1)$:

$$C = 2 s_0 s_1, \qquad S = -s_0^2 \log_2 s_0^2 - s_1^2 \log_2 s_1^2$$

They rank states identically, so for pure states choosing between them is a
matter of convenience. They genuinely diverge for mixed states, where
entanglement entropy is no longer a valid entanglement measure at all.

## Practical example

### Building the measures

```python
import numpy as np

ket0 = np.array([1, 0], dtype=complex)
ket1 = np.array([0, 1], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)


def reduced_a(psi):
    """Partial trace over qubit B."""
    rho = np.outer(psi, psi.conj()).reshape(2, 2, 2, 2)
    return np.trace(rho, axis1=1, axis2=3)


def entropy(rho):
    """Von Neumann entropy in bits."""
    ev = np.linalg.eigvalsh(rho)
    ev = ev[ev > 1e-12]
    return max(0.0, float(-np.sum(ev * np.log2(ev))))


def schmidt(psi):
    """Schmidt coefficients = singular values of the coefficient matrix."""
    s = np.linalg.svd(psi.reshape(2, 2), compute_uv=False)
    return s[s > 1e-12]


def concurrence(psi):
    """C = |<psi| (Y (x) Y) |psi*>|."""
    return float(abs(np.vdot(psi, np.kron(Y, Y) @ psi.conj())))
```

### Comparing states

```python
plus = (ket0 + ket1) / np.sqrt(2)
states = {
    "product |00>": np.kron(ket0, ket0),
    "product |++>": np.kron(plus, plus),
    "partially (t=0.3)": np.cos(0.3) * np.kron(ket0, ket0)
                        + np.sin(0.3) * np.kron(ket1, ket1),
    "partially (t=pi/8)": np.cos(np.pi / 8) * np.kron(ket0, ket0)
                          + np.sin(np.pi / 8) * np.kron(ket1, ket1),
    "Bell |Phi+>": (np.kron(ket0, ket0) + np.kron(ket1, ket1)) / np.sqrt(2),
}

print(f"{'state':22s} {'S (bits)':>10s} {'concurrence':>12s}  Schmidt")
for name, psi in states.items():
    print(f"{name:22s} {entropy(reduced_a(psi)):10.6f}"
          f" {concurrence(psi):12.6f}  {np.round(schmidt(psi), 6)}")
```

### Cross-checking entropy against the Schmidt coefficients

```python
print("entropy from Schmidt coefficients agrees with S(rho_A):")
for name, psi in states.items():
    s = schmidt(psi)
    direct = max(0.0, float(-np.sum(s**2 * np.log2(s**2))))
    print(f"  {name:22s} -sum(s^2 log2 s^2) = {direct:.6f}"
          f"   S(rho_A) = {entropy(reduced_a(psi)):.6f}")

print("theta sweep for cos(t)|00> + sin(t)|11>:")
for t in (0.0, 0.2, 0.5, np.pi / 4, 1.0):
    psi = np.cos(t) * np.kron(ket0, ket0) + np.sin(t) * np.kron(ket1, ket1)
    print(f"  t={t:6.4f}   S={entropy(reduced_a(psi)):.6f}"
          f"   C={concurrence(psi):.6f}")
```

Running it gives `S = 0.000000` and `C = 0.000000` for both product states,
with Schmidt coefficient `[1.]`. The Bell state gives `S = 1.000000`,
`C = 1.000000` and Schmidt coefficients `[0.707107 0.707107]`. The two
partially entangled states sit in between at `0.427502 / 0.564642` and
`0.600876 / 0.707107`. The entropy computed from Schmidt coefficients matches
$S(\rho_A)$ to six decimal places in every case, and the sweep peaks at
$t = \pi/4$ where both measures reach $1$.

## Common misconceptions

- **"Entanglement is all-or-nothing."** It is graded. A state with
  concurrence $0.565$ is genuinely entangled but carries far less than a Bell
  pair, and algorithms that need maximal entanglement will underperform.
- **"Entanglement entropy works for any state."** Only for *bipartite pure*
  states. For a mixed state it cannot distinguish entanglement from classical
  uncertainty — a maximally mixed single qubit has entropy 1 and no
  entanglement at all.
- **"Measuring one qubit sends information to the other."** The correlations
  are already present in the joint state. Measurement reveals an outcome
  correlated with one that will be found later; nothing is transmitted. This
  is why entanglement cannot be used for superluminal signalling.
- **"More entanglement always means a better algorithm."** Not necessarily.
  Some speed-ups come from interference and do not require maximal
  entanglement, and highly entangled states are often harder to prepare and
  more fragile against noise.
- **"The two measures disagree about which state has more entanglement."** For
  pure two-qubit states they rank identically, because both are functions of
  the same Schmidt coefficients.

## Exercises

1. Compute the Schmidt coefficients and entanglement entropy of
   $\tfrac{1}{2}|00\rangle + \tfrac{\sqrt{3}}{2}|11\rangle$.
2. Show that $|\Psi^-\rangle = \tfrac{1}{\sqrt{2}}(|01\rangle - |10\rangle)$ has
   concurrence 1, using both $2|ad - bc|$ and the $(Y \otimes Y)$ formula.
3. For Schmidt coefficients $(s_0, s_1)$, verify numerically that
   $C = 2 s_0 s_1$ matches the $(Y \otimes Y)$ formula on the $t = 0.3$ state.
4. What is the maximum entanglement entropy of a two-qubit state, and why can
   it not exceed one bit?
5. Explain why the entanglement entropy of a three-qubit GHZ state
   $\tfrac{1}{\sqrt{2}}(|000\rangle + |111\rangle)$, traced down to one qubit,
   is 1 bit despite there being three qubits.
6. Give an example of a mixed state with high von Neumann entropy but zero
   entanglement.

## Summary

- The Schmidt decomposition $|\psi\rangle = \sum_k s_k |u_k\rangle|v_k\rangle$
  gives uniquely determined coefficients with $\sum_k s_k^2 = 1$; the Schmidt
  rank is 1 exactly for product states.
- Reduced states have eigenvalues $s_k^2$, so entanglement entropy
  $E = S(\rho_A) = -\sum_k s_k^2 \log_2 s_k^2$, ranging from 0 to 1 bit for two
  qubits.
- Concurrence $C = 2|ad - bc| = |\langle\psi|(Y\otimes Y)|\psi^*\rangle|$ runs
  from 0 (product) to 1 (Bell).
- For pure two-qubit states both measures are functions of the same Schmidt
  coefficients and rank states identically: $C = 2 s_0 s_1$.
- Entanglement entropy is only a valid entanglement measure for bipartite pure
  states; mixed states need concurrence or a related measure.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §2.5 and §8.3 — Schmidt decomposition and entanglement
  measures.
- Wootters, W. K. *Entanglement of Formation of an Arbitrary State of Two
  Qubits* (1998) — the original concurrence derivation.
- Horodecki, R. et al. *Quantum entanglement* (Rev. Mod. Phys., 2009) — the
  standard review, for the mixed-state complications this lesson only sketches.

---

**Previous:** [Density Matrices](20_density_matrices.md) ·
**Next:** [The No-Cloning Theorem](22_no_cloning.md)
