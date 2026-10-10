# Dirac Notation

Dirac notation — "bra-ket" — is the standard notation of quantum mechanics,
and nearly every paper, textbook and Qiskit tutorial uses it without
explanation. It is not decoration: the notation is designed so that the
algebra you want to do is the algebra the symbols suggest. Once it is
internalised, manipulations that look like symbol-pushing in matrix form
become almost mechanical. This lesson builds it from vector operations you
already know, then uses it to do change of basis and read off matrix elements.

## Learning objectives

By the end of this lesson you should be able to:

- **Translate** between Dirac notation and column vectors, in both directions.
- **Compute** inner products $\langle\phi|\psi\rangle$ and outer products
  $|\psi\rangle\langle\phi|$, and state what each produces.
- **Apply** the completeness relation to expand a state in any orthonormal
  basis.
- **Evaluate** matrix elements $\langle i|A|j\rangle$ to recover an operator's
  matrix in a chosen basis.
- **Explain** why the same operator can be off-diagonal in one basis and
  diagonal in another, using $X$ as the example.

## Kets, bras and the inner product

### Kets are column vectors

A **ket** $|\psi\rangle$ is a column vector. The symbol is a label; the object
is a vector:

$$|0\rangle = \begin{pmatrix} 1 \\ 0 \end{pmatrix}, \qquad |1\rangle = \begin{pmatrix} 0 \\ 1 \end{pmatrix}, \qquad |\psi\rangle = \begin{pmatrix} \alpha \\ \beta \end{pmatrix}$$

### Bras are the adjoint

A **bra** $\langle\psi|$ is the conjugate transpose of the corresponding ket:

$$\langle\psi| = |\psi\rangle^\dagger = \begin{pmatrix} \alpha^* & \beta^* \end{pmatrix}$$

So a bra is a row vector with conjugated entries. The point of the
conjugation is to make $\langle\psi|\psi\rangle$ the squared norm, which must
be real and non-negative.

### The inner product

Putting a bra and a ket together gives the **inner product**, a scalar:

$$\langle\phi|\psi\rangle = \sum_k \phi_k^* \psi_k$$

Two properties matter constantly:

- **Conjugate symmetry**: $\langle\phi|\psi\rangle = \langle\psi|\phi\rangle^*$.
  Swapping the order conjugates the result.
- **Positive definiteness**: $\langle\psi|\psi\rangle \ge 0$, with equality only
  for the zero vector. The norm is $\||\psi\rangle\| = \sqrt{\langle\psi|\psi\rangle}$.

### Worked example

With $|\phi\rangle = |+\rangle$ and $|\psi\rangle = 0.6|0\rangle + 0.8|1\rangle$:

$$\langle\phi|\psi\rangle = \frac{0.6 + 0.8}{\sqrt{2}} \approx 0.989949$$

and $\langle\psi|\phi\rangle$ is the same value here because it happens to be
real; in general it is the complex conjugate.

### Cauchy–Schwarz

$$|\langle\phi|\psi\rangle|^2 \le \langle\phi|\phi\rangle \langle\psi|\psi\rangle$$

For the example above, $0.98 \le 1.0$. This inequality is what guarantees that
$|\langle\phi|\psi\rangle|^2$ can be read as a probability: it can never
exceed 1.

## Outer products

### Definition

Where $\langle\phi|\psi\rangle$ produces a scalar, the **outer product**
produces an operator:

$$|\psi\rangle\langle\phi|$$

For $|\psi\rangle = \begin{pmatrix}a \\ b\end{pmatrix}$ and
$\langle\phi| = \begin{pmatrix}c^* & d^*\end{pmatrix}$:

$$|\psi\rangle\langle\phi| = \begin{pmatrix} a c^* & a d^* \\ b c^* & b d^* \end{pmatrix}$$

### Why it matters

The outer product is how you build operators from states. The projector onto
$|0\rangle$ is $|0\rangle\langle 0|$, and the operator that maps
$|1\rangle \mapsto |0\rangle$ and annihilates $|0\rangle$ is $|0\rangle\langle 1|$:

$$|0\rangle\langle 1| = \begin{pmatrix} 0 & 1 \\ 0 & 0 \end{pmatrix}, \qquad (|0\rangle\langle 1|)|1\rangle = |0\rangle$$

## Completeness

### The relation

For any orthonormal basis $\{|i\rangle\}$:

$$\sum_i |i\rangle\langle i| = I$$

This is the **completeness relation** (or resolution of the identity). It holds
for *every* orthonormal basis, not just the computational one:

$$|0\rangle\langle 0| + |1\rangle\langle 1| = I$$

$$|+\rangle\langle +| + |-\rangle\langle -| = I$$

### Using it

Insert the identity anywhere in an expression to change basis or expand a
state. For $|\psi\rangle = 0.6|0\rangle + 0.8|1\rangle$:

$$|\psi\rangle = I|\psi\rangle = \sum_i |i\rangle\langle i|\psi\rangle$$

Both bases reconstruct the same vector $(0.6, 0.8)^T$, which is the
numerically checkable content of the claim.

The coefficients $\langle i|\psi\rangle$ are the **amplitudes** of $|\psi\rangle$
in that basis:

$$\langle 0|\psi\rangle = 0.6, \qquad \langle 1|\psi\rangle = 0.8, \qquad \langle+|\psi\rangle \approx 0.989949$$

## Operators and matrix elements

### Recovering a matrix from an operator

Given an operator $A$ and a basis $\{|i\rangle\}$, the entries of its matrix
are

$$A_{ij} = \langle i|A|j\rangle$$

This is the bridge between the abstract operator and the concrete matrix you
compute with. For $A = \begin{pmatrix}1 & 2 \\ 3 & 4\end{pmatrix}$ in the
computational basis, evaluating $\langle i|A|j\rangle$ returns exactly that
matrix.

### Change of basis

The same operator has different matrices in different bases. For $X$:

**Computational basis** $\{|0\rangle, |1\rangle\}$:

$$X = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$$

**Hadamard basis** $\{|+\rangle, |-\rangle\}$:

$$X = \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}$$

The second matrix is **diagonal**, with entries $+1$ and $-1$ — the
eigenvalues of $X$, with $|+\rangle$ and $|-\rangle$ as the corresponding
eigenvectors. This is the same operator, and nothing about $X$ changed; only
the basis did.

That is the practical reason to care about eigenbases: in its eigenbasis an
operator is diagonal, and diagonal matrices are trivial to work with, to
exponentiate, and to reason about.

## Adjoints in Dirac notation

### Basic rules

- $(|\psi\rangle)^\dagger = \langle\psi|$ and $(\langle\psi|)^\dagger = |\psi\rangle$.
- $(AB)^\dagger = B^\dagger A^\dagger$ — the order reverses.
- $\langle\psi|A|\phi\rangle^* = \langle\phi|A^\dagger|\psi\rangle$.

The reversal in the second rule is the single most common source of sign and
ordering errors. It is verified numerically in the code below.

### Hermitian and unitary, restated

$$A \text{ Hermitian} \iff A^\dagger = A, \qquad U \text{ unitary} \iff U^\dagger U = I$$

In Dirac notation: $\langle\phi|A|\psi\rangle = \langle\psi|A|\phi\rangle^*$
for Hermitian $A$, which is exactly the condition that expectation values be
real.

## Practical example

### Bras, kets and inner products

```python
import numpy as np

ket0 = np.array([1, 0], dtype=complex)
ket1 = np.array([0, 1], dtype=complex)
plus = (ket0 + ket1) / np.sqrt(2)
minus = (ket0 - ket1) / np.sqrt(2)
psi = np.array([0.6, 0.8], dtype=complex)

# <phi|psi> is a scalar; np.vdot conjugates its first argument.
phi = plus
print(f"<phi|psi> = {np.vdot(phi, psi):.6f}")
print(f"conjugate symmetry holds: "
      f"{np.allclose(np.vdot(psi, phi), np.conj(np.vdot(phi, psi)))}")
print(f"<phi|phi> = {np.vdot(phi, phi).real:.6f}")

# Cauchy-Schwarz bounds an inner product by the product of the norms.
lhs = abs(np.vdot(phi, psi)) ** 2
rhs = np.vdot(phi, phi).real * np.vdot(psi, psi).real
print(f"|<phi|psi>|^2 = {lhs:.6f}  <=  {rhs:.6f}  -> {lhs <= rhs + 1e-12}")
```

### Outer products and completeness

```python
outer = np.outer(ket0, ket1)          # |0><1|
print("|0><1| =\n", outer)
print("  (|0><1|)|1> == |0>:", np.allclose(outer @ ket1, ket0))

I2 = np.eye(2, dtype=complex)
print("|0><0| + |1><1| == I:",
      np.allclose(np.outer(ket0, ket0) + np.outer(ket1, ket1), I2))
print("|+><+| + |-><-| == I:",
      np.allclose(np.outer(plus, plus) + np.outer(minus, minus), I2))

# Resolving the identity in either basis reconstructs the same vector.
for name, basis in (("computational", (ket0, ket1)), ("+-", (plus, minus))):
    rebuilt = sum(np.outer(e, e) @ psi for e in basis)
    print(f"rebuilt in the {name} basis: {np.round(rebuilt, 6)}")
```

### Matrix elements and change of basis

```python
X = np.array([[0, 1], [1, 0]], dtype=complex)

def matrix_elements(op, basis):
    return np.array([[np.vdot(i, op @ j) for j in basis] for i in basis])

print("<i|X|j> in the computational basis:\n",
      np.real(matrix_elements(X, (ket0, ket1))))
print("<i|X|j> in the +- basis:\n",
      np.round(np.real(matrix_elements(X, (plus, minus))), 6))
print("X|+> == |+>:", np.allclose(X @ plus, plus))
print("X|-> == -|->:", np.allclose(X @ minus, -minus))

A = np.array([[1, 1j], [0, 2]], dtype=complex)
print("(AB)^dag == B^dag A^dag:",
      np.allclose((A @ X).conj().T, X.conj().T @ A.conj().T))
```

Running the blocks in order prints `<phi|psi> = 0.989949` with conjugate
symmetry confirmed and `|<phi|psi>|^2 = 0.980000 <= 1.000000`. The outer
product $|0\rangle\langle 1|$ is printed as the matrix with a single 1 in the
top-right, and applying it to $|1\rangle$ returns $|0\rangle$. Both
completeness relations hold, and resolving the identity in either basis
rebuilds $(0.6, 0.8)$.

The change-of-basis block is the point of the lesson: $X$ comes out as
$\begin{pmatrix}0 & 1 \\ 1 & 0\end{pmatrix}$ in the computational basis and
$\begin{pmatrix}1 & 0 \\ 0 & -1\end{pmatrix}$ in the $|\pm\rangle$ basis. Both
eigenvalue checks return `True`, and $(AB)^\dagger = B^\dagger A^\dagger$ is
confirmed.

## Common misconceptions

- **"A bra is the same vector written sideways."** It is the conjugate
  transpose. Forgetting the conjugation gives $\langle\psi|\psi\rangle$ wrong
  and breaks normalisation.
- **"$\langle\phi|\psi\rangle$ and $\langle\psi|\phi\rangle$ are equal."**
  They are complex conjugates. Equal only when the value is real.
- **"$\sum_i |i\rangle\langle i| = I$ only for the computational basis."**
  It holds for every orthonormal basis. That is precisely what makes it useful.
- **"Changing basis changes the operator."** It changes only the matrix
  representation. $X$ is $X$ in both bases above.
- **"$(AB)^\dagger = A^\dagger B^\dagger$."** The order reverses:
  $(AB)^\dagger = B^\dagger A^\dagger$.

## Exercises

1. Write $|-\rangle$ as a column vector, and compute $\langle +|-\rangle$ and
   $\langle -|+\rangle$.
2. Compute $|+\rangle\langle +|$ as an explicit matrix, and verify it is a
   projector by squaring it.
3. Using completeness, expand $|\psi\rangle = 0.6|0\rangle + 0.8|1\rangle$ in
   the $|\pm\rangle$ basis and check the reconstruction numerically.
4. Evaluate $\langle i|Z|j\rangle$ in both the computational and $|\pm\rangle$
   bases. In which basis is $Z$ diagonal?
5. Show that $(AB)^\dagger = B^\dagger A^\dagger$ fails in general if you do
   not reverse the order, using a concrete pair of matrices.
6. For a Hermitian $A$, verify numerically that
   $\langle\phi|A|\psi\rangle = \langle\psi|A|\phi\rangle^*$.

## Summary

- A ket is a column vector; a bra is its conjugate transpose;
  $\langle\phi|\psi\rangle$ is a scalar with conjugate symmetry.
- The outer product $|\psi\rangle\langle\phi|$ is an operator, and is how
  projectors and basis-changing maps are built.
- Completeness $\sum_i |i\rangle\langle i| = I$ holds in every orthonormal
  basis, letting you insert the identity to expand or convert.
- Matrix elements are $A_{ij} = \langle i|A|j\rangle$; the same operator has
  different matrices in different bases.
- In its eigenbasis an operator is diagonal — for $X$ that means
  $\mathrm{diag}(1, -1)$ in the $|\pm\rangle$ basis.
- $(AB)^\dagger = B^\dagger A^\dagger$; the order reverses.

## References

- Dirac, P. A. M. *The Principles of Quantum Mechanics* — the notation
  originates here.
- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §2.1 — linear algebra in Dirac notation.
- Qiskit documentation — the notation used throughout its circuit and state
  representations.

---

**Previous:** [The No-Cloning Theorem](22_no_cloning.md) ·
**Next:** [Tensor Products](24_tensor_products.md)
