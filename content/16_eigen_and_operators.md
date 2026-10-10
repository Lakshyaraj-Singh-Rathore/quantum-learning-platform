# Eigenvalues, Eigenvectors and Operator Classes

Measurement, time evolution and every observable quantity in quantum mechanics
are expressed through eigenvalues. If you can find the eigenvalues and
eigenvectors of a matrix, you can predict what a measurement will return and
with what probability; if you cannot, the operator is just an opaque grid of
numbers. This lesson covers how to compute them for the small matrices that
dominate quantum computing, and then classifies the three operator types that
matter — Hermitian, unitary and projector — by what their spectra look like.
It assumes the vector and matrix material from the linear algebra lesson.

## Learning objectives

By the end of this lesson you should be able to:

- **Compute** eigenvalues and eigenvectors of a $2 \times 2$ matrix by solving
  the characteristic equation.
- **Recognise** a Hermitian matrix and state why its eigenvalues must be real.
- **Recognise** a unitary matrix and state why its eigenvalues must have unit
  modulus.
- **Explain** why measurable quantities correspond to Hermitian operators, and
  what the spectral decomposition says about measurement outcomes.
- **Calculate** the expectation value of an observable for a given state.

## Eigenvalues and eigenvectors

### Intuition

When a matrix acts on most vectors, it rotates and stretches them into a new
direction. An **eigenvector** is special: the matrix acts on it by stretching
alone, leaving the direction unchanged. The stretch factor is the
**eigenvalue**.

### Formal definition

A non-zero vector $|v\rangle$ is an eigenvector of $A$ with eigenvalue
$\lambda$ if

$$A|v\rangle = \lambda |v\rangle$$

To find the eigenvalues, rearrange to $(A - \lambda I)|v\rangle = 0$. A
non-zero solution exists only when $A - \lambda I$ is not invertible, which
means its determinant vanishes. This gives the **characteristic equation**:

$$\det(A - \lambda I) = 0$$

### Worked example: the Pauli $Z$ matrix

Take $Z = \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}$. Then

$$Z - \lambda I = \begin{pmatrix} 1 - \lambda & 0 \\ 0 & -1 - \lambda \end{pmatrix}$$

$$\det(Z - \lambda I) = (1-\lambda)(-1-\lambda) - 0 = \lambda^2 - 1 = 0$$

So $\lambda = \pm 1$. Substituting back:

- $\lambda = +1$: $\begin{pmatrix} 0 & 0 \\ 0 & -2 \end{pmatrix}\begin{pmatrix} a \\ b \end{pmatrix} = 0$ forces $b = 0$, giving eigenvector $\begin{pmatrix} 1 \\ 0 \end{pmatrix} = |0\rangle$.
- $\lambda = -1$: $\begin{pmatrix} 2 & 0 \\ 0 & 0 \end{pmatrix}\begin{pmatrix} a \\ b \end{pmatrix} = 0$ forces $a = 0$, giving eigenvector $\begin{pmatrix} 0 \\ 1 \end{pmatrix} = |1\rangle$.

The eigenvectors of $Z$ are exactly the computational basis states, and its
eigenvalues are $+1$ and $-1$.

### Worked example: a non-diagonal matrix

Take $X = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$.

$$\det(X - \lambda I) = \det\begin{pmatrix} -\lambda & 1 \\ 1 & -\lambda \end{pmatrix} = \lambda^2 - 1 = 0$$

Again $\lambda = \pm 1$. For $\lambda = +1$:

$$\begin{pmatrix} -1 & 1 \\ 1 & -1 \end{pmatrix}\begin{pmatrix} a \\ b \end{pmatrix} = 0 \implies a = b$$

so the eigenvector is $\frac{1}{\sqrt{2}}\begin{pmatrix}1\\1\end{pmatrix} = |+\rangle$.
For $\lambda = -1$ it is $|-\rangle$.

So $X$ has the same eigenvalues as $Z$ but completely different eigenvectors.
The eigenvalues alone do not identify an operator; the eigenbasis matters just
as much.

## Hermitian operators

### Definition

A matrix is **Hermitian** (or self-adjoint) if

$$A^\dagger = A$$

### Why the eigenvalues are real

Let $A|v\rangle = \lambda|v\rangle$ with $A$ Hermitian. Consider
$\langle v|A|v\rangle$ computed two ways:

$$\langle v|A|v\rangle = \langle v|\lambda v\rangle = \lambda \langle v|v\rangle$$

and, using $A = A^\dagger$,

$$\langle v|A|v\rangle = \langle Av|v\rangle = \langle \lambda v|v\rangle = \lambda^* \langle v|v\rangle$$

Since $\langle v|v\rangle \neq 0$ for a non-zero vector, $\lambda = \lambda^*$,
which means $\lambda$ is real.

This is the whole reason observables are Hermitian: a laboratory measurement
returns a real number, and only a Hermitian operator is guaranteed to do so.

### Examples

All three Pauli matrices are Hermitian, as is $H$. You can verify each by
checking that the matrix equals its conjugate transpose.

## Unitary operators

### Definition

A matrix is **unitary** if

$$U^\dagger U = UU^\dagger = I$$

Equivalently, $U^\dagger = U^{-1}$.

### Why the eigenvalues have unit modulus

Unitary matrices preserve inner products, and therefore preserve norms:

$$\|U\psi\|^2 = \langle U\psi | U\psi \rangle = \langle \psi | U^\dagger U | \psi \rangle = \langle \psi | \psi \rangle = \|\psi\|^2$$

If $U|v\rangle = \lambda|v\rangle$, then $\|U v\|^2 = |\lambda|^2 \|v\|^2$, and
preservation of the norm forces $|\lambda|^2 = 1$, so

$$|\lambda| = 1$$

Every eigenvalue of a unitary matrix lies on the unit circle, so it can be
written $\lambda = e^{i\theta}$.

This is exactly why quantum gates must be unitary: the total probability must
remain 1, and unitarity is the precise statement that it does.

### Worked example: the phase gate

The gate $S = \begin{pmatrix} 1 & 0 \\ 0 & i \end{pmatrix}$ is unitary, since
$S^\dagger S = \begin{pmatrix} 1 & 0 \\ 0 & -i \end{pmatrix}\begin{pmatrix} 1 & 0 \\ 0 & i \end{pmatrix} = I$.
Its eigenvalues are $1$ and $i$, both of modulus 1.

The $T$ gate, $T = \begin{pmatrix} 1 & 0 \\ 0 & e^{i\pi/4} \end{pmatrix}$, has
eigenvalues $1$ and $e^{i\pi/4} \approx 0.7071 + 0.7071i$, again both of
modulus 1.

## Projectors and the spectral decomposition

### Definition

A **projector** $P$ satisfies $P^2 = P$ and $P^\dagger = P$. Its eigenvalues
are only 0 and 1, because $P^2 = P$ implies $\lambda^2 = \lambda$.

### Spectral decomposition

Any Hermitian operator can be written as a weighted sum of projectors onto its
eigenvectors:

$$A = \sum_k \lambda_k \, |\lambda_k\rangle\langle\lambda_k|$$

where $|\lambda_k\rangle\langle\lambda_k|$ is the outer product — a projector
onto the $k$-th eigenspace. For $Z$:

$$Z = (+1)|0\rangle\langle 0| + (-1)|1\rangle\langle 1|$$

Written out, $|0\rangle\langle 0| = \begin{pmatrix}1&0\\0&0\end{pmatrix}$ and
$|1\rangle\langle 1| = \begin{pmatrix}0&0\\0&1\end{pmatrix}$, and the weighted
sum does reproduce $Z$.

This form is what makes measurement concrete: the possible outcomes are the
eigenvalues $\lambda_k$, and the probability of outcome $k$ is
$\langle\psi|P_k|\psi\rangle$.

### Trace and determinant

Two useful shortcuts, both verifiable on $Z$:

$$\operatorname{tr}(A) = \sum_k \lambda_k, \qquad \det(A) = \prod_k \lambda_k$$

For $Z$: the trace is $1 + (-1) = 0$ and the determinant is $1 \cdot (-1) = -1$.

## Expectation values

The **expectation value** of an observable $A$ in state $|\psi\rangle$ is

$$\langle A \rangle_\psi = \langle \psi | A | \psi \rangle$$

It is the average result of many measurements, not the result of any single
one. Because $A$ is Hermitian, $\langle A\rangle$ is always real.

### Worked example

For $|\psi\rangle = |0\rangle$ and $A = Z$:

$$\langle 0|Z|0\rangle = \begin{pmatrix}1 & 0\end{pmatrix}\begin{pmatrix}1&0\\0&-1\end{pmatrix}\begin{pmatrix}1\\0\end{pmatrix} = 1$$

Every measurement returns $+1$, as expected: $|0\rangle$ is an eigenvector.

For $|\psi\rangle = |+\rangle$:

$$\langle +|Z|+\rangle = \frac{1}{2}\begin{pmatrix}1 & 1\end{pmatrix}\begin{pmatrix}1&0\\0&-1\end{pmatrix}\begin{pmatrix}1\\1\end{pmatrix} = \frac{1}{2}(1 - 1) = 0$$

The average is 0 because $|+\rangle$ is an equal superposition: half the
measurements give $+1$ and half give $-1$. Note that 0 is not itself a
possible outcome — it is the average of $+1$ and $-1$.

## Practical example

```python
import numpy as np

Z = np.array([[1, 0], [0, -1]], dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
S = np.array([[1, 0], [0, 1j]], dtype=complex)
T = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)

def report(name, A):
    herm = np.allclose(A.conj().T, A)
    unit = np.allclose(A.conj().T @ A, np.eye(A.shape[0]))
    eigs = np.linalg.eigvals(A)
    print(f"{name}: Hermitian={herm}  unitary={unit}  "
          f"eigenvalues={np.round(eigs, 6)}  |lambda|={np.round(np.abs(eigs), 6)}")

for name, A in (("Z", Z), ("X", X), ("Y", Y), ("H", H), ("S", S), ("T", T)):
    report(name, A)

# --- eigen-decomposition of Z ----------------------------------------------
vals, vecs = np.linalg.eig(Z)
print("\nZ eigenvalues:", vals)
print("Z eigenvectors (columns):\n", vecs)

# --- spectral decomposition rebuilt from projectors -------------------------
order = np.argsort(vals)          # sort so the projectors line up
rebuilt = sum(vals[i] * np.outer(vecs[:, i], vecs[:, i].conj()) for i in order)
print("rebuilt from projectors == Z ?", np.allclose(rebuilt, Z))

# --- trace and determinant shortcuts ---------------------------------------
print("tr(Z) =", np.trace(Z), " sum of eigenvalues =", np.sum(np.linalg.eigvals(Z)))
print("det(Z) =", np.round(np.linalg.det(Z), 6),
      " product of eigenvalues =", np.round(np.prod(np.linalg.eigvals(Z)), 6))

# --- expectation values -----------------------------------------------------
ket0 = np.array([1, 0], dtype=complex)
plus = np.array([1, 1], dtype=complex) / np.sqrt(2)
print("<0|Z|0>  =", np.vdot(ket0, Z @ ket0).real)   # 1.0
print("<+|Z|+>  =", np.vdot(plus, Z @ plus).real)   # 0.0
print("<0|X|0>  =", np.vdot(ket0, X @ ket0).real)   # 0.0
```

Running it confirms: `Z`, `X`, `Y` and `H` are all both Hermitian and unitary
with eigenvalues $\pm 1$; `S` has eigenvalues $1$ and $i$; `T` has $1$ and
$0.707107 + 0.707107i$; every unitary's eigenvalues have modulus 1; the
spectral decomposition rebuilt from projectors equals the original $Z$; and
the expectation values are $1$, $0$ and $0$ for the three cases.

## Common misconceptions

- **"The eigenvalues determine the operator."** They do not. $X$ and $Z$ share
  the eigenvalues $\pm 1$ but have different eigenbases, which is why measuring
  them gives different information about the same state.
- **"The expectation value is a possible measurement result."** Not
  necessarily. $\langle +|Z|+\rangle = 0$, but no single measurement of $Z$
  ever returns 0. It is an average over many runs.
- **"Every matrix can be diagonalised."** Only matrices with a full set of
  linearly independent eigenvectors. Hermitian and unitary matrices always can
  be, which is a large part of why quantum mechanics is built from them.
- **"Hermitian and unitary are the same thing."** They are different
  constraints with different spectral consequences: Hermitian gives real
  eigenvalues, unitary gives unit-modulus eigenvalues. Some matrices ($X$, $Y$,
  $Z$, $H$) are both. $S$ and $T$ are unitary but not Hermitian.
- **"Eigenvectors are unique."** Any scalar multiple of an eigenvector is also
  an eigenvector. Convention normalises them to unit length, and even then a
  sign or phase remains free.

## Exercises

1. Find the eigenvalues and normalised eigenvectors of
   $A = \begin{pmatrix} 2 & 0 \\ 0 & 3 \end{pmatrix}$ by inspection, and
   verify $\operatorname{tr}(A) = \lambda_1 + \lambda_2$.
2. Compute the eigenvalues of $H = \frac{1}{\sqrt{2}}\begin{pmatrix}1&1\\1&-1\end{pmatrix}$
   and confirm they are $\pm 1$.
3. Show that $S = \begin{pmatrix}1&0\\0&i\end{pmatrix}$ is unitary but not
   Hermitian, by computing $S^\dagger S$ and comparing $S^\dagger$ with $S$.
4. Verify by direct multiplication that $P = |+\rangle\langle +|$ satisfies
   $P^2 = P$.
5. Compute $\langle 1|Z|1\rangle$ and $\langle -|Z|-\rangle$, and explain why
   the second is 0 even though $|-\rangle$ is an eigenvector of $X$, not $Z$.
6. Prove that if $U$ is unitary, then $|\det(U)| = 1$.

## Summary

- An eigenvector satisfies $A|v\rangle = \lambda|v\rangle$; eigenvalues come
  from $\det(A - \lambda I) = 0$.
- Hermitian ($A^\dagger = A$) operators have **real** eigenvalues — the
  requirement for representing measurable quantities.
- Unitary ($U^\dagger U = I$) operators have eigenvalues of **unit modulus** —
  the requirement for gates, since it preserves total probability.
- A projector satisfies $P^2 = P$, with eigenvalues only 0 and 1; the spectral
  decomposition $A = \sum_k \lambda_k |\lambda_k\rangle\langle\lambda_k|$ is
  built from them.
- $\operatorname{tr}(A)$ is the sum of eigenvalues and $\det(A)$ their product.
- The expectation value $\langle\psi|A|\psi\rangle$ is the average of many
  measurements, and is not itself necessarily a possible outcome.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §2.1.5–2.1.8 — the spectral decomposition and the postulates
  stated in this notation.
- Qiskit textbook, *The Atoms of Computation* — the gate set used above.
- NumPy documentation — `np.linalg.eig`, `np.linalg.eigvals`, `np.linalg.det`.

---

**Previous:** [Vectors, Matrices and Linear Algebra](15_linear_algebra.md) ·
**Next:** [Probability, Expectation and Sampling Statistics](17_probability_and_statistics.md)
