# Circuit Identities and Simplification

Two circuits that compute the same thing are the same circuit, no matter how
differently they are drawn. On real hardware that equivalence is not academic:
every gate you leave in costs time and error, and a circuit that has been
simplified runs better than one that has not. This lesson collects the
identities that make rewriting possible, and shows how to check that a
simplification is correct rather than merely plausible.

## Learning objectives

By the end of this lesson you should be able to:

- **Apply** standard identities: $H^2 = I$, $T^2 = S$, SWAP as three CNOTs, and
  the conjugation rules that move a gate through a basis change.
- **Cancel** adjacent inverse gates, and merge rotations about the same axis.
- **Simplify** a short circuit and **verify** the result by comparing matrices.
- **Recognise** when two gates commute and when they do not, and why that
  determines whether a rewrite is legal.

## Why simplification matters

A compiled circuit is a budget. Each gate spends a little coherence time and
adds a little error, so a circuit with half the gates is roughly twice as
likely to return a meaningful answer. Compilers apply the identities below
automatically, but they cannot always find the rewrites that a human who
understands the structure can see immediately.

The rewrites come in three flavours:

- **Cancellation** — a gate next to its own inverse disappears.
- **Merging** — two rotations about the same axis combine into one.
- **Rewriting** — a pattern is replaced by a cheaper equivalent, such as a
  SWAP replaced by three CNOTs or a CNOT whose direction is reversed.

## Single-qubit identities

### Squares and products

These are the ones worth having at your fingertips. All were verified by
building the matrices and comparing:

| Identity | Meaning |
|---|---|
| $H^2 = I$ | $H$ is its own inverse |
| $X^2 = Y^2 = Z^2 = I$ | the Paulis are self-inverse |
| $S^2 = Z$ | two $S$ gates make a $Z$ |
| $T^2 = S$ | two $T$ gates make an $S$ |
| $(S^\dagger)^2 = Z$ | and likewise in reverse |

The $T^2 = S$ identity is the one that saves real money, because $T$ gates are
the expensive resource on a fault-tolerant machine. Two in a row are just an
$S$, which is far cheaper.

### Conjugation: moving a gate through a basis change

Conjugating by $H$ swaps the $X$ and $Z$ axes:

$$H X H = Z \qquad H Z H = X \qquad H Y H = -Y$$

The minus sign on the third is easy to forget. Conjugating by $S$ cycles
$X$ into $Y$:

$$S X S^\dagger = Y$$

Equivalently, written as commutation relations, $HX = ZH$ and $XH = HZ$. These
are the rules that let you push a gate past a basis change.

### Merging rotations

Rotations about the **same axis** add:

$$R_x(\alpha)R_x(\beta) = R_x(\alpha+\beta)$$

and identically for $R_y$ and $R_z$. This is the single most useful
simplification in variational circuits, where layers of small rotations
accumulate. Rotations about *different* axes do **not** combine this way — that
is precisely why a general single-qubit gate needs three parameters rather
than one.

## Two-qubit identities

### SWAP from three CNOTs

There is no primitive SWAP on most hardware. It is built from three CNOTs, in
either orientation:

$$\text{SWAP} = \text{CX}_{0\to1}\,\text{CX}_{1\to0}\,\text{CX}_{0\to1} = \text{CX}_{1\to0}\,\text{CX}_{0\to1}\,\text{CX}_{1\to0}$$

Both orderings were verified to reproduce SWAP exactly. SWAP is also
self-inverse, so an adjacent pair cancels.

Three CNOTs for one SWAP is expensive, which is why compilers work hard to
avoid them — usually by relabelling qubits logically rather than physically
moving data around.

### Reversing a CNOT

Conjugating both wires with $H$ reverses the direction of a CNOT:

$$(H \otimes H)\,\text{CX}_{0\to1}\,(H \otimes H) = \text{CX}_{1\to0}$$

This matters when connectivity restricts which qubit may act as the control.

### CNOT and CZ

Placing an $H$ on the **target** converts a CNOT into a CZ, and back:

$$(I \otimes H)\,\text{CX}_{0\to1}\,(I \otimes H) = \text{CZ}$$

The $H$ must go on the target wire. Putting it on the control instead does
**not** give CZ — a mistake worth checking numerically rather than assuming.

### Propagating Paulis through a CNOT

These describe how a Pauli on one side of a CNOT moves to the other, and
they are how compilers push gates around to expose cancellations:

$$\text{CX}_{0\to1}\,(X \otimes I) = (X \otimes X)\,\text{CX}_{0\to1}$$

$$\text{CX}_{0\to1}\,(I \otimes X) = (I \otimes X)\,\text{CX}_{0\to1}$$

$$\text{CX}_{0\to1}\,(I \otimes Z) = (Z \otimes Z)\,\text{CX}_{0\to1}$$

Note the pattern: an $X$ on the **control** spreads to both wires, an $X$ on
the **target** passes straight through, and a $Z$ on the target spreads back
onto the control.

## Commuting gates

Two gates may be swapped in the circuit only if they commute. The rules that
matter in practice:

- Gates on **disjoint qubits** always commute.
- A CNOT commutes with an $X$ on its target, and with a $Z$ on its control.
- Rotations about the **same axis** commute with each other.
- Rotations about **different** axes generally do not.
- A CNOT does **not** commute with an $X$ on its control, or a $Z$ on its
  target — those are exactly the cases where the Pauli spreads.

Getting this wrong is the classic source of a "simplification" that silently
changes the computation, which is why the next section matters.

## Checking a simplification

### The rule

Never trust a rewrite by eye. Build both matrices and compare them. They must
agree **up to a global phase**, since a global phase is physically
unobservable:

$$U_{\text{original}} = e^{i\phi}\, U_{\text{simplified}}$$

Comparing entry by entry will fail even when the circuits are equivalent, so
you compare after factoring out the ratio at one nonzero entry.

### A worked example

Consider this twelve-gate single-qubit circuit:

$$H,\; H,\; T,\; T,\; R_z(0.3),\; R_z(0.4),\; X,\; H,\; Z,\; H,\; S,\; S^\dagger$$

Simplify it one pattern at a time:

| Gates | Rewrite | Result |
|---|---|---|
| $H, H$ | $H^2 = I$ | removed |
| $T, T$ | $T^2 = S$ | one $S$ |
| $R_z(0.3), R_z(0.4)$ | same axis, angles add | $R_z(0.7)$ |
| $X, H, Z, H$ | $HZH = X$, then $X \cdot X = I$ | removed |
| $S, S^\dagger$ | inverse pair | removed |

What remains is **two gates**, $S$ then $R_z(0.7)$, down from twelve.

Verifying the matrices confirms the two circuits are not merely equivalent up
to phase but **exactly equal** — the accumulated global phase happens to be 1
here. That is stronger than required, and a good sign the rewrite is right.

The instructive case is the middle one. $X, H, Z, H$ looks like four gates
that must be kept, but $HZH = X$ turns it into $X \cdot X = I$. Identities pay
off most when they let you see through a pattern rather than cancel an obvious
pair.

## Practical example

### Verifying the single-qubit identities

```python
import numpy as np

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
S = np.array([[1, 0], [0, 1j]], dtype=complex)
T = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)
Sd, Td = S.conj().T, T.conj().T


def rx(t):
    c, s = np.cos(t / 2), np.sin(t / 2)
    return np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)


def rz(t):
    return np.array([[np.exp(-1j * t / 2), 0], [0, np.exp(1j * t / 2)]],
                    dtype=complex)


def same_up_to_phase(A, B):
    """True if A = e^{i*phi} * B for some global phase."""
    nz = [(i, j) for i in range(A.shape[0]) for j in range(A.shape[1])
          if abs(B[i, j]) > 1e-9]
    if not nz:
        return False
    return np.allclose(A, (A[nz[0]] / B[nz[0]]) * B)


checks = [
    ("H^2 = I", H @ H, I2), ("X^2 = I", X @ X, I2), ("S^2 = Z", S @ S, Z),
    ("T^2 = S", T @ T, S), ("H X H = Z", H @ X @ H, Z),
    ("H Z H = X", H @ Z @ H, X), ("H Y H = -Y", H @ Y @ H, -Y),
    ("S X Sdag = Y", S @ X @ Sd, Y), ("H X = Z H", H @ X, Z @ H),
    ("Rz(a)Rz(b) = Rz(a+b)", rz(0.3) @ rz(0.4), rz(0.7)),
    ("Rx(a)Rx(b) = Rx(a+b)", rx(0.3) @ rx(0.4), rx(0.7)),
]
for name, left, right in checks:
    print(f"  {name:24s} {same_up_to_phase(left, right)}")
```

### Two-qubit identities

```python
def cnot(c, t):
    M = np.zeros((4, 4), dtype=complex)
    for col in range(4):
        M[col ^ (1 << (1 - t)) if (col >> (1 - c)) & 1 else col, col] = 1
    return M


CN01, CN10 = cnot(0, 1), cnot(1, 0)
SWAP = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]],
                dtype=complex)
CZ = np.diag([1, 1, 1, -1]).astype(complex)
K = np.kron

print("  SWAP == CNOT01 CNOT10 CNOT01:", np.allclose(CN01 @ CN10 @ CN01, SWAP))
print("  SWAP == CNOT10 CNOT01 CNOT10:", np.allclose(CN10 @ CN01 @ CN10, SWAP))
print("  (H⊗H) CNOT01 (H⊗H) == CNOT10:",
      np.allclose(K(H, H) @ CN01 @ K(H, H), CN10))
print("  (I⊗H) CNOT01 (I⊗H) == CZ:", np.allclose(K(I2, H) @ CN01 @ K(I2, H), CZ))
print("  (H⊗I) CNOT01 (H⊗I) == CZ:", np.allclose(K(H, I2) @ CN01 @ K(H, I2), CZ))
print("  CNOT01 (X⊗I) == (X⊗X) CNOT01:",
      np.allclose(CN01 @ K(X, I2), K(X, X) @ CN01))
print("  CNOT01 (I⊗Z) == (Z⊗Z) CNOT01:",
      np.allclose(CN01 @ K(I2, Z), K(Z, Z) @ CN01))
```

### Simplifying a circuit and checking it

```python
def product(ops):
    """ops in circuit order; the leftmost is applied first."""
    M = np.eye(2, dtype=complex)
    for _, g in ops:
        M = g @ M
    return M


original = [('H', H), ('H', H), ('T', T), ('T', T), ('Rz(0.3)', rz(0.3)),
            ('Rz(0.4)', rz(0.4)), ('X', X), ('H', H), ('Z', Z), ('H', H),
            ('S', S), ('Sdag', Sd)]
simplified = [('S', S), ('Rz(0.7)', rz(0.7))]

M_orig, M_simp = product(original), product(simplified)
print(f"\n  gates: {len(original)} -> {len(simplified)}")
print("  equivalent up to global phase:", same_up_to_phase(M_orig, M_simp))
print("  exactly equal:", np.allclose(M_orig, M_simp))
```

Running the blocks in order confirms every identity in the tables, including
that `(H⊗I)` does **not** turn a CNOT into CZ while `(I⊗H)` does, and that the
twelve-gate circuit reduces to two gates that are exactly equal to the
original.

## Common misconceptions

- **"Two circuits that look different compute different things."** They may be
  identical. Only the matrix decides.
- **"Cancelling requires exact adjacency."** You may first need to commute
  gates past each other, and that is legal only if they actually commute.
- **"Any $H$ turns a CNOT into CZ."** It must be on the **target** wire.
- **"All rotations merge."** Only rotations about the **same axis** add.
- **"Comparing matrices directly is enough."** Compare **up to a global
  phase**, or you will reject correct rewrites.

## Exercises

1. Verify $H^2 = I$, $S^2 = Z$ and $T^2 = S$ by matrix multiplication.
2. Show that $HYH = -Y$, and explain what the minus sign means physically.
3. Simplify $H, Z, Z, H$ and verify the result against the identity matrix.
4. Express SWAP as three CNOTs and confirm both orderings give the same
   matrix.
5. Simplify $R_z(0.5), R_x(0.5), R_z(0.5)$ — can these merge? Explain why or
   why not.
6. Take the twelve-gate circuit above, insert an extra $H$ at the front, and
   determine what the simplified form becomes. Verify numerically.

## Summary

- **Cancellation, merging and rewriting** are the three kinds of
  simplification; each removes gates.
- Key identities: $H^2 = I$, $S^2 = Z$, $T^2 = S$, $HXH = Z$, $HZH = X$,
  $HYH = -Y$, $SXS^\dagger = Y$.
- Rotations about the same axis add: $R_x(\alpha)R_x(\beta) = R_x(\alpha+\beta)$.
- **SWAP is three CNOTs**; $(H\otimes H)$ reverses a CNOT; $(I\otimes H)$
  converts CNOT to CZ, with the $H$ on the target.
- Pauli propagation through a CNOT: an $X$ on the control spreads, an $X$ on
  the target passes through, a $Z$ on the target spreads back.
- **Always verify a rewrite by comparing matrices up to a global phase.**

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  §4.2 — the identities and their proofs.
- Qiskit documentation, *transpiler passes* — how these rewrites are applied
  automatically.
- The [U3, iSWAP and fSim](39_two_qubit_gates.md) lesson — the native gates a
  simplified circuit is ultimately rewritten into.
- The [Quantum Gates](02_gates.md) lesson — the gate set these identities act
  on.

---

**Previous:** [U3, iSWAP and fSim](39_two_qubit_gates.md)
