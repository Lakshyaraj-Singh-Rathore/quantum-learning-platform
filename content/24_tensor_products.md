# Tensor Products

The tensor product is the operation that combines quantum systems, and it is
the reason quantum computing scales the way it does. One qubit needs two
complex amplitudes; $n$ qubits need $2^n$. That exponential is both the source
of quantum computing's power and the reason a 40-qubit state cannot be stored
classicalally. It also produces the one genuinely non-classical feature of the
theory: states of a composite system that are not determined by the states of
their parts.

## Learning objectives

By the end of this lesson you should be able to:

- **Compute** the tensor product of two vectors using the Kronecker product,
  and state the basis ordering convention.
- **Apply** the mixed-product rule $(A \otimes B)(C \otimes D) = AC \otimes BD$
  to simplify operator expressions.
- **Construct** an operator acting on one qubit of a multi-qubit system using
  $A \otimes I$ or $I \otimes A$.
- **Decide** whether a two-qubit state is a product state or entangled, by
  computing the rank of its coefficient matrix.
- **Explain** why $n$ qubits require $2^n$ amplitudes, and what that implies
  for classical simulation.

## Definition

### For vectors

The tensor product of $|\psi\rangle = \begin{pmatrix}a \\ b\end{pmatrix}$ and
$|\phi\rangle = \begin{pmatrix}c \\ d\end{pmatrix}$ is

$$|\psi\rangle \otimes |\phi\rangle = \begin{pmatrix} ac \\ ad \\ bc \\ bd \end{pmatrix}$$

In NumPy this is `np.kron`. The dimension multiplies: two 2-dimensional vectors
give a 4-dimensional one.

### For matrices

For operators, the Kronecker product arranges scaled copies of the second
matrix in the pattern of the first:

$$A \otimes B = \begin{pmatrix} A_{11} B & A_{12} B \\ A_{21} B & A_{22} B \end{pmatrix}$$

With $A = \begin{pmatrix}1 & 2 \\ 3 & 4\end{pmatrix}$ and
$B = \begin{pmatrix}0 & 5 \\ 6 & 7\end{pmatrix}$, the top-left $2 \times 2$
block is $A_{11}B = \begin{pmatrix}0 & 5 \\ 6 & 7\end{pmatrix}$, confirming
the block structure directly.

### Basis ordering

The computational basis of two qubits is

$$|0\rangle \otimes |0\rangle = \begin{pmatrix}1\\0\\0\\0\end{pmatrix}, \quad |0\rangle \otimes |1\rangle = \begin{pmatrix}0\\1\\0\\0\end{pmatrix}, \quad |1\rangle \otimes |0\rangle = \begin{pmatrix}0\\0\\1\\0\end{pmatrix}, \quad |1\rangle \otimes |1\rangle = \begin{pmatrix}0\\0\\0\\1\end{pmatrix}$$

written $|00\rangle, |01\rangle, |10\rangle, |11\rangle$. The **leftmost ket is
the most significant bit**: $|10\rangle$ is the third basis vector, so as an
integer it is 2, not 1. Most quantum software, Qiskit included, uses this
little-endian qubit ordering, and getting it backwards is a standard source of
confusion when comparing a circuit to its matrix.

## Key properties

### Dimensions multiply

$$\dim(A \otimes B) = \dim(A) \cdot \dim(B)$$

Two $2 \times 2$ operators give a $4 \times 4$ one.

### The mixed-product rule

$$(A \otimes B)(C \otimes D) = AC \otimes BD$$

This is the workhorse identity. It lets you simplify a product of tensor
operators without ever forming the large matrices, and it is verified
numerically in the code below.

### Bilinearity

Tensor product is linear in both arguments:

$$A \otimes (\alpha B + \beta C) = \alpha(A \otimes B) + \beta(A \otimes C)$$

which is what makes the algebraic manipulation of multi-qubit circuits
tractable.

## Acting on one subsystem

### The identity does the padding

To apply $X$ to the first qubit and leave the second alone:

$$X \otimes I$$

And to act on the second:

$$I \otimes X$$

Concretely, on $|00\rangle$:

$$(X \otimes I)|00\rangle = |10\rangle, \qquad (I \otimes X)|00\rangle = |01\rangle$$

### Applying a gate to every qubit

The Hadamard on both qubits is $H \otimes H$:

$$(H \otimes H)|00\rangle = |+\rangle \otimes |+\rangle = \tfrac{1}{2}\begin{pmatrix}1 & 1 & 1 & 1\end{pmatrix}^T$$

This is the operation that opens the Grover and Bernstein–Vazirani circuits:
$n$ parallel Hadamards create the uniform superposition over all $2^n$ basis
states from a single $H^{\otimes n}$.

## Product states and entanglement

### The separability test

A two-qubit state $|\psi\rangle$ with amplitudes $\alpha_{ij}$ is a **product
state** if it can be written $|\psi\rangle = |a\rangle \otimes |b\rangle$. The
computational test: reshape the amplitudes into a $2 \times 2$ matrix and check
its rank.

- **Rank 1** $\implies$ product state.
- **Rank 2** $\implies$ entangled.

### Worked comparison

| State | Coefficient matrix rank | Singular values | Product? |
|---|---|---|---|
| $\|+\rangle\|+\rangle$ | 1 | $(1, 0)$ | Yes |
| $\|\Phi^+\rangle$ Bell | 2 | $(0.707, 0.707)$ | No |

For $|+\rangle|+\rangle$ one singular value is 1 and the other is 0: a single
term suffices, and the state factorises. For the Bell state both singular
values are $1/\sqrt{2}$: two terms are genuinely needed, and no factorisation
exists.

The singular values here are exactly the Schmidt coefficients from the
entanglement measures lesson, so rank is the Schmidt rank and the test is the
same one.

### Why this matters computationally

A product state is describable with $2n$ numbers — $n$ for each qubit. A
general state needs $2^n$. Entangled states are precisely the ones that cannot
be compressed that way, which is why simulating highly entangled circuits
classically is expensive and why entanglement is treated as a resource.

## Building CNOT

### From projectors

CNOT flips the second qubit when the first is $|1\rangle$. Written with
projectors onto the control:

$$\text{CNOT} = |0\rangle\langle 0| \otimes I + |1\rangle\langle 1| \otimes X$$

This is a direct expression of "if control is 0 do nothing, if control is 1
apply $X$", and it evaluates to

$$\text{CNOT} = \begin{pmatrix} 1 & 0 & 0 & 0 \\ 0 & 1 & 0 & 0 \\ 0 & 0 & 0 & 1 \\ 0 & 0 & 1 & 0 \end{pmatrix}$$

Checking it: $\text{CNOT}|10\rangle = |11\rangle$ and
$\text{CNOT}|00\rangle = |00\rangle$, as expected.

The projector form generalises: any controlled-$U$ is
$|0\rangle\langle 0| \otimes I + |1\rangle\langle 1| \otimes U$.

## The exponential

### Amplitude counting

$$n \text{ qubits} \implies 2^n \text{ amplitudes}$$

Three qubits give 8 amplitudes; $|010\rangle$ is the vector with a 1 in
position 2. Twenty qubits need about a million; forty need about $10^{12}$;
storing fifty in double precision would need on the order of nine petabytes.
That is the practical wall that classical simulation hits, and the reason the
simulators in this project cap their qubit counts.

## Practical example

### Basis vectors and the Kronecker product

```python
import numpy as np

ket0 = np.array([1, 0], dtype=complex)
ket1 = np.array([0, 1], dtype=complex)
plus = (ket0 + ket1) / np.sqrt(2)
I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)

print("|00> =", np.kron(ket0, ket0).real.astype(int))
print("|01> =", np.kron(ket0, ket1).real.astype(int))
print("|10> =", np.kron(ket1, ket0).real.astype(int))
print("|11> =", np.kron(ket1, ket1).real.astype(int))

A = np.array([[1, 2], [3, 4]], dtype=complex)
B = np.array([[0, 5], [6, 7]], dtype=complex)
print("\ntop-left block of A (x) B:\n", np.kron(A, B)[:2, :2].real)
print("  should equal A[0,0] * B:\n", (A[0, 0] * B).real)
```

### The mixed-product rule and single-subsystem gates

```python
C = np.array([[1, 0], [0, -1]], dtype=complex)
D = np.array([[0, 1], [1, 0]], dtype=complex)
print("(A(x)B)(C(x)D) == AC (x) BD:",
      np.allclose(np.kron(A, B) @ np.kron(C, D), np.kron(A @ C, B @ D)))

ket00 = np.kron(ket0, ket0)
print("\n(X(x)I)|00> == |10>:", np.allclose(np.kron(X, I2) @ ket00,
                                            np.kron(ket1, ket0)))
print("(I(x)X)|00> == |01>:", np.allclose(np.kron(I2, X) @ ket00,
                                            np.kron(ket0, ket1)))
print("(H(x)H)|00> =", np.round(np.kron(H, H) @ ket00, 6))
print("  == |++>:", np.allclose(np.kron(H, H) @ ket00, np.kron(plus, plus)))
```

### Separability and CNOT

```python
bell = (np.kron(ket0, ket0) + np.kron(ket1, ket1)) / np.sqrt(2)
print("state                 rank  singular values        product?")
for name, v in (("|++>", np.kron(plus, plus)), ("Bell", bell)):
    M = v.reshape(2, 2)
    rank = np.linalg.matrix_rank(M)
    s = np.linalg.svd(M, compute_uv=False)
    print(f"  {name:20s} {rank}     {np.round(s, 6)}   {rank == 1}")

P0 = np.outer(ket0, ket0)
P1 = np.outer(ket1, ket1)
CNOT = np.kron(P0, I2) + np.kron(P1, X)
print("\nCNOT =\n", CNOT.real.astype(int))
print("CNOT|10> (expect |11>):", (CNOT @ np.kron(ket1, ket0)).real.astype(int))
print("CNOT|00> (expect |00>):", (CNOT @ ket00).real.astype(int))

three = np.kron(np.kron(ket0, ket1), ket0)
print("\n|010> =", three.real.astype(int), " amplitudes:", three.size)
```

Running the blocks in order prints the four basis vectors, confirming that
$|10\rangle$ is the third (index 2), and shows the Kronecker top-left block
equalling $A_{11}B$. The mixed-product check returns `True`. The
single-subsystem gates give `True` for both $(X \otimes I)|00\rangle = |10\rangle$
and $(I \otimes X)|00\rangle = |01\rangle$, and $(H \otimes H)|00\rangle$ prints
`[0.5 0.5 0.5 0.5]`, matching $|+\rangle|+\rangle$.

The separability table prints rank 1 with singular values `[1. 0.]` for
$|+\rangle|+\rangle$ (a product state) and rank 2 with `[0.707107 0.707107]`
for the Bell state (entangled). CNOT is printed as the expected matrix, maps
$|10\rangle \mapsto |11\rangle$ and fixes $|00\rangle$, and $|010\rangle$ has 8
amplitudes.

## Common misconceptions

- **"$|10\rangle$ means qubit 1 is $|1\rangle$ and qubit 0 is $|0\rangle$."**
  In the standard little-endian convention the leftmost ket is the most
  significant bit, so $|10\rangle$ is the *third* basis vector and the first
  qubit is $|1\rangle$.
- **"Every two-qubit state is a product of two one-qubit states."** Entangled
  states are exactly the counterexamples, and the rank test detects them.
- **"$A \otimes B = B \otimes A$."** Order matters; the tensor product is not
  commutative. Swapping the factors is a different operator (related by a swap
  gate).
- **"A gate on one qubit needs a $2 \times 2$ matrix."** On $n$ qubits it needs
  $2^n \times 2^n$; the $2 \times 2$ gate is embedded by tensoring with
  identities.
- **"Entanglement means the qubits interact."** Entanglement is a property of
  the *state*, not of an ongoing interaction. Once created it persists until
  the state is disturbed.

## Exercises

1. Compute $|+\rangle \otimes |0\rangle$ as an explicit four-component vector.
2. Verify the mixed-product rule numerically with a pair of matrices of your
   choosing.
3. Write down $Z \otimes I$ and $I \otimes Z$ as $4 \times 4$ matrices, and
   compute $(Z \otimes Z)|11\rangle$.
4. Determine whether $\tfrac{1}{2}(|00\rangle + |01\rangle + |10\rangle + |11\rangle)$
   is a product state, using the rank test.
5. Construct the matrix for controlled-$Z$ from projectors, and verify it acts
   as expected on $|11\rangle$.
6. How many amplitudes does a 5-qubit state have? How much memory would it need
   in complex128 (16 bytes per amplitude)?

## Summary

- The tensor product combines systems: $\dim(A \otimes B) = \dim A \cdot \dim B$,
  computed as the Kronecker product.
- Basis ordering is little-endian: $|10\rangle$ is the third basis vector.
- The mixed-product rule $(A \otimes B)(C \otimes D) = AC \otimes BD$ simplifies
  products of tensor operators without forming large matrices.
- A gate on one subsystem is $A \otimes I$ or $I \otimes A$; $H^{\otimes n}$
  creates the uniform superposition.
- A two-qubit state is a product state exactly when its $2 \times 2$ coefficient
  matrix has rank 1; rank 2 means entangled.
- Any controlled-$U$ is $|0\rangle\langle0| \otimes I + |1\rangle\langle1| \otimes U$.
- $n$ qubits need $2^n$ amplitudes, which is the wall classical simulation hits.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §2.1.7 — tensor products and the postulates for composite
  systems.
- Qiskit documentation, *Circuit basics* — the little-endian qubit ordering
  used in its statevector output.
- The [Entanglement Measures](21_entanglement_measures.md) lesson — the Schmidt
  coefficients introduced there are the singular values used in the rank test.

---

**Previous:** [Dirac Notation](23_dirac_notation.md) ·
**Next:** [Quantum Teleportation](26_teleportation.md)
