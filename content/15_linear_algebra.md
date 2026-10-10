# Vectors, Matrices and Linear Algebra

A quantum state is a vector, and every operation performed on it — a gate, a
measurement, a noise channel — is a matrix acting on that vector. This is not
an analogy: it is the actual mathematical definition used by the simulators
you will run. This lesson covers the linear algebra the rest of the course
assumes, starting from column vectors and finishing with the change of basis,
which is the mechanism behind every quantum algorithm's final step. Complex
numbers from the previous lesson are used throughout, and the eigenvalue
lesson that follows builds directly on what is here.

## Learning objectives

By the end of this lesson you should be able to:

- **Represent** a quantum state as a column vector in a chosen basis, and
  compute its norm using the inner product.
- **Multiply** a matrix by a vector and by another matrix, and state why the
  order of multiplication matters.
- **Construct** the tensor (Kronecker) product of two vectors or matrices and
  predict the dimension of the result.
- **Transform** a vector between two orthonormal bases using a change-of-basis
  matrix.
- **Identify** the Hermitian conjugate $A^\dagger$ of a matrix and compute it
  for a $2 \times 2$ example.

## Why vectors and matrices

A classical bit is a single number, 0 or 1. A qubit is described by *two*
complex amplitudes, so it needs two numbers — a vector. Two qubits need four
amplitudes, three need eight, and $n$ qubits need $2^n$. The natural container
for that is a column vector of length $2^n$, and the natural operations on it
are matrices.

This is why linear algebra is not optional background for quantum computing.
It is the data structure.

## Vectors and the inner product

### Intuition

A **ket** $|\psi\rangle$ is a column vector of complex amplitudes. The
corresponding **bra** $\langle\psi|$ is its Hermitian conjugate — a row vector
with the entries complex-conjugated. Putting a bra next to a ket,
$\langle\phi|\psi\rangle$, is the **inner product**: it multiplies matching
entries and sums, giving a single complex number.

### Formal definition

For column vectors $\phi, \psi \in \mathbb{C}^n$,

$$\langle \phi | \psi \rangle = \sum_{k=0}^{n-1} \phi_k^* \, \psi_k$$

The inner product **conjugates the first argument**. Two consequences matter
constantly:

$$\langle \psi | \phi \rangle = \langle \phi | \psi \rangle^*$$

$$\langle \psi | \psi \rangle = \sum_k |\psi_k|^2 \ge 0$$

The quantity $\langle\psi|\psi\rangle$ is the squared **norm** of the state.
For a physical quantum state it must equal 1, which is exactly the
normalisation condition already met in the qubits lesson.

Crucially, when the entries are real the inner product is symmetric and the
conjugation is invisible. With complex entries it is not: this is the one
place where a habit formed from real-valued vectors will produce a wrong
answer.

### Worked example: an inner product

Let $|v\rangle = \begin{pmatrix} 1 \\ 2 \end{pmatrix}$ and
$|w\rangle = \begin{pmatrix} 3 \\ 4 \end{pmatrix}$.

$$\langle v | w \rangle = 1 \cdot 3 + 2 \cdot 4 = 11$$

Now let $|a\rangle = \begin{pmatrix} 1 \\ i \end{pmatrix}$ and
$|b\rangle = \begin{pmatrix} i \\ 1 \end{pmatrix}$. Here conjugation matters:

$$\langle a | b \rangle = (1)^*(i) + (i)^*(1) = i + (-i)(1) = i - i = 0$$

The two vectors are **orthogonal**. Had we forgotten the conjugation, we
would have computed $i + i = 2i$ and wrongly concluded they were not.

## Matrices as operators

### Formal definition

An $m \times n$ matrix maps a vector in $\mathbb{C}^n$ to a vector in
$\mathbb{C}^m$:

$$(A\psi)_i = \sum_{j} A_{ij} \, \psi_j$$

Applying a matrix to a vector is just repeated inner products: row $i$ of $A$
is dotted with $\psi$ to give entry $i$ of the result.

### Matrix multiplication is not commutative

The product $AB$ means "apply $B$ first, then $A$":

$$(AB)\psi = A(B\psi)$$

Order matters, and this is not a technicality. The Pauli matrices provide a
one-line demonstration. With

$$X = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}, \qquad Y = \begin{pmatrix} 0 & -i \\ i & 0 \end{pmatrix}$$

we get

$$XY = \begin{pmatrix} i & 0 \\ 0 & -i \end{pmatrix}, \qquad YX = \begin{pmatrix} -i & 0 \\ 0 & i \end{pmatrix}$$

So $XY = -YX$. Applying $X$ then $Y$ is genuinely different from applying $Y$
then $X$. In circuit terms, the gate on the left of a product is the one
applied **later** in time.

### The Hermitian conjugate

The **Hermitian conjugate** (or adjoint) $A^\dagger$ is the transpose with
every entry conjugated:

$$(A^\dagger)_{ij} = A_{ji}^*$$

It satisfies $(AB)^\dagger = B^\dagger A^\dagger$ — note the reversal, the same
phenomenon as with matrix inversion.

### Worked example: a gate acting on a state

Apply $X$ to $|0\rangle = \begin{pmatrix} 1 \\ 0 \end{pmatrix}$:

$$X|0\rangle = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix} \begin{pmatrix} 1 \\ 0 \end{pmatrix} = \begin{pmatrix} 0\cdot 1 + 1\cdot 0 \\ 1\cdot 1 + 0\cdot 0 \end{pmatrix} = \begin{pmatrix} 0 \\ 1 \end{pmatrix} = |1\rangle$$

This is the matrix form of the NOT gate, and it is why $X$ is called the
quantum NOT.

## Bases and change of basis

### Intuition

A vector does not come with coordinates attached; coordinates only mean
something relative to a chosen **basis**. The same physical state can be
written many ways. Choosing a different basis is not changing the state — it
is changing the description.

### Formal definition

A **basis** of $\mathbb{C}^n$ is a set of $n$ linearly independent vectors
that span the space. A basis is **orthonormal** if

$$\langle e_i | e_j \rangle = \delta_{ij}$$

where $\delta_{ij}$ is 1 when $i = j$ and 0 otherwise. Every basis used in
this course is orthonormal.

The **computational basis** (or $Z$ basis) for one qubit is

$$|0\rangle = \begin{pmatrix} 1 \\ 0 \end{pmatrix}, \qquad |1\rangle = \begin{pmatrix} 0 \\ 1 \end{pmatrix}$$

The **Hadamard basis** (or $X$ basis) is

$$|+\rangle = \frac{1}{\sqrt{2}}\begin{pmatrix} 1 \\ 1 \end{pmatrix}, \qquad |-\rangle = \frac{1}{\sqrt{2}}\begin{pmatrix} 1 \\ -1 \end{pmatrix}$$

You can check orthonormality directly: $\langle + | - \rangle = \frac{1}{2}(1\cdot 1 + 1 \cdot (-1)) = 0$.

### Changing basis

To express a state in a new orthonormal basis, take the inner product of the
state with each new basis vector. The Hadamard matrix

$$H = \frac{1}{\sqrt{2}}\begin{pmatrix} 1 & 1 \\ 1 & -1 \end{pmatrix}$$

is precisely the change-of-basis matrix from the computational basis to the
Hadamard basis:

$$H|0\rangle = \frac{1}{\sqrt{2}}\begin{pmatrix} 1 \\ 1 \end{pmatrix} = |+\rangle, \qquad H|1\rangle = \frac{1}{\sqrt{2}}\begin{pmatrix} 1 \\ -1 \end{pmatrix} = |-\rangle$$

This is the reason $H$ appears at the start and end of so many algorithms: it
moves a state into a basis where a property of interest becomes measurable in
the standard $Z$ basis.

### Worked example: rewriting $|0\rangle$ in the Hadamard basis

Since $H$ is its own inverse ($H^2 = I$), we can also go backwards:

$$|0\rangle = \frac{1}{\sqrt{2}}\left(|+\rangle + |-\rangle\right)$$

Verifying by substitution:

$$\frac{1}{\sqrt{2}}\left(\frac{1}{\sqrt{2}}\begin{pmatrix}1\\1\end{pmatrix} + \frac{1}{\sqrt{2}}\begin{pmatrix}1\\-1\end{pmatrix}\right) = \frac{1}{2}\begin{pmatrix}2\\0\end{pmatrix} = \begin{pmatrix}1\\0\end{pmatrix}$$

So $|0\rangle$ is an equal superposition in the Hadamard basis, even though it
is a single basis state in the computational basis. "Superposition" is
basis-dependent — a point returned to in the measurement lesson.

## Combining systems: the tensor product

### Formal definition

If system $A$ has an $m$-dimensional space and system $B$ an $n$-dimensional
one, the combined system has dimension $mn$. The **tensor product** (Kronecker
product) builds it:

$$|a\rangle \otimes |b\rangle = \begin{pmatrix} a_0 b_0 \\ a_0 b_1 \\ a_1 b_0 \\ a_1 b_1 \end{pmatrix} \quad \text{for} \quad |a\rangle = \begin{pmatrix} a_0 \\ a_1 \end{pmatrix}, \; |b\rangle = \begin{pmatrix} b_0 \\ b_1 \end{pmatrix}$$

Note the ordering: the **first** factor's index varies slowest. This
convention is what produces the standard two-qubit basis ordering.

### The two-qubit computational basis

$$|00\rangle = \begin{pmatrix}1\\0\\0\\0\end{pmatrix}, \quad |01\rangle = \begin{pmatrix}0\\1\\0\\0\end{pmatrix}, \quad |10\rangle = \begin{pmatrix}0\\0\\1\\0\end{pmatrix}, \quad |11\rangle = \begin{pmatrix}0\\0\\0\\1\end{pmatrix}$$

The exponential growth is the reason classical simulation of quantum systems
is hard: 50 qubits requires a vector of $2^{50} \approx 1.13 \times 10^{15}$
complex amplitudes.

### Separable versus entangled

A two-qubit state built as a single tensor product $|a\rangle \otimes |b\rangle$
is called **separable**. A general two-qubit state is a sum of such products,
and states that cannot be written as a single product are **entangled** — the
subject of the entanglement lesson.

## Practical example

```python
import numpy as np

ket0 = np.array([1, 0], dtype=complex)
ket1 = np.array([0, 1], dtype=complex)

X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)

# --- a gate acting on a state ----------------------------------------------
print("X|0> =", X @ ket0)                 # [0.+0.j 1.+0.j]
print("X|1> =", X @ ket1)                 # [1.+0.j 0.+0.j]

# --- inner product conjugates the FIRST argument ---------------------------
a = np.array([1, 1j], dtype=complex)
b = np.array([1j, 1], dtype=complex)
print("<a|b> =", np.vdot(a, b))           # 0j  -> orthogonal
print("naive sum(a*b) =", np.sum(a * b))  # 2j  -> WRONG, no conjugation

# --- normality of a superposition ------------------------------------------
psi = np.array([1, 1j], dtype=complex) / np.sqrt(2)
print("<psi|psi> =", np.vdot(psi, psi).real)   # 1.0

# --- non-commutativity ------------------------------------------------------
print("XY =\n", X @ Y)
print("YX =\n", Y @ X)
print("XY == YX ?", np.allclose(X @ Y, Y @ X))  # False

# --- Hermitian conjugate ----------------------------------------------------
print("H dagger == H ?", np.allclose(H.conj().T, H))  # True (H is Hermitian)

# --- change of basis --------------------------------------------------------
print("H|0> =", np.round(H @ ket0, 6))    # [0.707107 0.707107] = |+>
print("H|1> =", np.round(H @ ket1, 6))    # [0.707107 -0.707107] = |->
plus = (ket0 + ket1) / np.sqrt(2)
minus = (ket0 - ket1) / np.sqrt(2)
print("<+|+> =", np.vdot(plus, plus).real)
print("<+|-> =", np.vdot(plus, minus))    # ~0 -> orthonormal

# --- tensor products --------------------------------------------------------
print("|00> =", np.kron(ket0, ket0))
print("|01> =", np.kron(ket0, ket1))
print("|10> =", np.kron(ket1, ket0))
print("|11> =", np.kron(ket1, ket1))
print("dim of 4 qubits:", 2 ** 4)
```

Running it confirms each claim: `X|0>` is `[0.+0.j 1.+0.j]`, `np.vdot(a, b)`
is `0j` while the conjugation-free `np.sum(a * b)` gives `2j`, `XY == YX` is
`False`, and the tensor products reproduce the four basis vectors above with
the first factor's index varying slowest.

## Common misconceptions

- **"The inner product is symmetric."** It is conjugate-symmetric:
  $\langle\phi|\psi\rangle = \langle\psi|\phi\rangle^*$. With real entries the
  two agree, which is why the error is easy to miss. Always use `np.vdot`,
  which conjugates the first argument, rather than `np.dot` or `np.sum(a*b)`.
- **"A superposition is an absolute property."** It is basis-relative.
  $|0\rangle$ is a single basis state in the computational basis and an equal
  superposition in the Hadamard basis.
- **"Matrices commute, like numbers."** They generally do not. $XY = -YX$.
  In a circuit diagram the leftmost matrix acts last.
- **"$\langle\psi|\psi\rangle$ is the norm."** It is the squared norm. The
  norm itself is $\sqrt{\langle\psi|\psi\rangle}$, and normalisation requires
  the squared norm to be 1.
- **"A two-qubit state is two vectors."** It is one vector of length 4. The
  tensor product is how you *build* it from two single-qubit states, but the
  result lives in a single, larger space.

## Exercises

1. Compute $\langle v|w\rangle$ and $\langle w|v\rangle$ for
   $|v\rangle = \begin{pmatrix}1 \\ i\end{pmatrix}$,
   $|w\rangle = \begin{pmatrix}2 \\ 3i\end{pmatrix}$, and confirm they are
   complex conjugates of each other.
2. Show that $Z|+\rangle = |-\rangle$ and $Z|-\rangle = |+\rangle$ by matrix
   multiplication.
3. Compute $HZH$ and confirm it equals $X$. Interpret this: conjugating a
   $Z$ operation by Hadamards turns it into an $X$ operation.
4. Let $|\psi\rangle = \frac{1}{2}\begin{pmatrix}1 \\ 1 \\ 1 \\ 1\end{pmatrix}$.
   Verify it is normalised, and decide whether it is separable or entangled.
   If separable, give the two single-qubit factors.
5. Compute the Hermitian conjugate of
   $A = \begin{pmatrix} 1 & 2i \\ 3 & 4 \end{pmatrix}$ and verify that
   $(A^\dagger)^\dagger = A$.
6. In Python, build the $8 \times 8$ matrix for $X$ acting on qubit 0 of a
   three-qubit register using `np.kron`, and check its shape.

## Summary

- A ket is a column vector of amplitudes; the bra is its conjugate transpose;
  the inner product $\langle\phi|\psi\rangle = \sum_k \phi_k^*\psi_k$
  conjugates the **first** argument.
- Normalisation is $\langle\psi|\psi\rangle = 1$, the squared norm.
- Matrices are operators; $(AB)\psi$ means "$B$ first, then $A$"; matrix
  multiplication is not commutative ($XY = -YX$).
- The Hermitian conjugate is $A^\dagger = (A^*)^T$ and reverses product order:
  $(AB)^\dagger = B^\dagger A^\dagger$.
- An orthonormal basis satisfies $\langle e_i|e_j\rangle = \delta_{ij}$;
  $H$ converts between the computational and Hadamard bases.
- The tensor product combines systems, giving dimension $2^n$ for $n$ qubits,
  with the first factor's index varying slowest.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §2.1 — the linear algebra of quantum mechanics, stated in the
  same notation used here.
- Qiskit textbook, *Representing Qubit States* — the vector conventions the
  simulator actually uses.
- NumPy documentation — `np.vdot` (conjugating inner product), `np.kron`
  (tensor product), `ndarray.conj().T` (Hermitian conjugate).

---

**Previous:** [Complex Numbers and Euler's Formula](14_complex_numbers.md) ·
**Next:** [Eigenvalues, Eigenvectors and Operator Classes](16_eigen_and_operators.md)
