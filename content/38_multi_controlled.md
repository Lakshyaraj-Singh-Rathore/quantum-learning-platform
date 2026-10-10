# Toffoli, Multi-Controlled Gates and Controlled Rotations

The gates you build circuits from are not the gates the hardware runs. A
processor gives you a small native set — typically a couple of two-qubit gates
and arbitrary single-qubit rotations — and everything else has to be built from
those. This lesson is about the gates that are most expensive to build:
Toffoli, multi-controlled $X$, and controlled rotations. Understanding their
cost is what separates a circuit that looks elegant on paper from one that
finishes before your qubits decohere.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** Toffoli and general multi-controlled $X$ circuits.
- **Apply** controlled rotation gates, and decompose a controlled rotation into
  native gates.
- **Count** the native gates a many-control operation costs, with and without
  ancilla qubits.
- **Explain** why the ancilla-assisted construction is linear rather than
  quadratic in the number of controls.

## Toffoli

### Definition

The **Toffoli** gate — also written CCX or CCNOT — flips its target if and only
if both controls are $|1\rangle$:

$$\text{CCX} : |a, b, c\rangle \mapsto |a, b, c \oplus (a \land b)\rangle$$

As an $8\times 8$ matrix it is the identity except for a swap of the last two
columns. It is its own inverse, and it is the workhorse of quantum arithmetic:
reversible adders, multipliers and comparators are largely built from it.

Two properties make it special. It is **universal for classical reversible
computation** — any classical circuit can be built from Toffolis alone. And it
is **not** universal for quantum computation by itself, because with
control-control-$X$ and $X$ alone you never leave the real-amplitude subspace.
Add $H$ and you get full universality.

### Decomposition into native gates

A native gate set of arbitrary single-qubit rotations plus CNOT cannot run a
Toffoli directly. The standard decomposition uses **6 CNOTs, 7 gates from the
$T$ family, and 2 Hadamards — 15 native gates in total**:

$$H(t),\; \text{CX}(b,t),\; T^\dagger(t),\; \text{CX}(a,t),\; T(t),\; \text{CX}(b,t),\; T^\dagger(t),\; \text{CX}(a,t),\; T(b),\; T(t),\; H(t),\; \text{CX}(a,b),\; T(a),\; T^\dagger(b),\; \text{CX}(a,b)$$

This was verified by building the matrix directly and comparing it against the
definition: they agree exactly, not merely up to a phase.

The $T$ count matters more than the total. On a fault-tolerant machine $T$
gates are the expensive resource — they are the ones that need magic state
distillation — so "7 $T$ gates" is the number a resource estimate cares about.

## Controlled rotations

### The pattern

A **controlled rotation** applies a rotation to the target only when the control
is $|1\rangle$. For $R_z$ and $R_y$ the decomposition into native gates is
elegant and cheap. Both follow the same shape:

$$CR_z(\theta) = \text{CX}(c,t)\; R_z(-\tfrac{\theta}{2})\; \text{CX}(c,t)\; R_z(\tfrac{\theta}{2})$$

reading right to left as written, so the circuit applies the two half-rotations
with a CNOT either side. The same identity holds with $R_y$ in place of $R_z$:

$$CR_y(\theta) = \text{CX}(c,t)\; R_y(-\tfrac{\theta}{2})\; \text{CX}(c,t)\; R_y(\tfrac{\theta}{2})$$

Both were verified against the block-diagonal definition across several angles.

### Why this works

The conjugation identity $\text{CX}\, (I \otimes R)\,\text{CX}$ produces a
rotation conditional on the control. Splitting the rotation into two halves and
sandwiching them between CNOTs makes the two branches of the control differ by
exactly $\theta$ rather than $2\theta$, which is what cancels the unwanted
rotation on the $|0\rangle$ branch.

For $R_z$ there is a further simplification: because $R_z$ is diagonal, a
controlled-$R_z$ is symmetric in the two qubits, so you may swap which wire you
call the control. That is not true of $R_y$ or $R_x$.

Controlled rotations cost **2 CNOTs and 2 rotations** — dramatically cheaper
than a Toffoli. They appear constantly in variational circuits, and inside
Grover and amplitude amplification, where the rotation angle encodes the
quantity being amplified.

## Multi-controlled $X$

### The problem

$C^k X$ flips a target conditional on $k$ controls all being $|1\rangle$. This
gate is everywhere: Grover's oracle, the phase kickback step in Shor's
algorithm, and the arithmetic subroutines in Hamiltonian simulation.

The cost depends critically on whether you can spare **ancilla** qubits.

### Without ancillas

If no scratch qubits are available, the cost grows **quadratically** in the
number of controls. The standard constructions give
$\Theta(k^2)$ two-qubit gates. The quadratic factor comes from having to
recompute intermediate AND values rather than storing them.

We present the quadratic scaling as established theory rather than as something
demonstrated in this lesson — building those circuits explicitly is beyond what
we verify here.

### With clean ancillas: linear

Give the circuit $k-2$ clean ancillas and the construction becomes simple and
cheap. Compute the AND of all controls into the ancilla chain, apply one final
Toffoli onto the target, then **uncompute** the chain so the ancillas are
returned to $|0\rangle$:

1. Toffoli$(q_0, q_1, a_0)$ — so $a_0 = q_0 \land q_1$
2. For $i = 2, \ldots, k-2$: Toffoli$(q_i, a_{i-2}, a_{i-1})$
3. Toffoli$(q_{k-1}, a_{k-3}, t)$ — the flip
4. Uncompute steps 2 then 1, in reverse order

Counting: $(k-2)$ Toffolis forward, $1$ in the middle, $(k-2)$ to uncompute:

$$\boxed{\text{Toffolis} = 2k-3}$$

At 15 native gates per Toffoli, that is $15(2k-3)$ native gates.

### Verified costs

The construction above was built as an explicit matrix and compared against the
definition of $C^k X$ on the subspace where the ancillas start at $|0\rangle$:

| Controls $k$ | Toffolis | $2k-3$ | Native gates | Correct |
|---|---|---|---|---|
| 2 | 1 | 1 | 15 | yes |
| 3 | 3 | 3 | 45 | yes |
| 4 | 5 | 5 | 75 | yes |
| 5 | 7 | 7 | 105 | yes |
| 6 | 9 | 9 | 135 | yes |

The count is exactly $2k-3$ and the construction is verified correct at every
size tested. The growth is **linear**: each extra control costs 2 Toffolis, or
30 native gates.

### Why the uncompute matters

The reverse pass is not optional tidiness. If the ancillas are left holding
$q_0 \land q_1 \land \cdots$, they remain **entangled** with the controls, and
the interference your algorithm depends on is destroyed. Uncomputing disentangles
them and restores the ancillas to $|0\rangle$, ready for reuse. Leaving ancillas
dirty is one of the most common bugs in hand-written quantum circuits.

## Practical example

### Shared helpers

```python
import numpy as np

X = np.array([[0, 1], [1, 0]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
T = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)
Td = T.conj().T


def single(U, q, n):
    """U on qubit q of an n-qubit register (bit position n-1-q)."""
    M = np.zeros((1 << n, 1 << n), dtype=complex)
    for col in range(1 << n):
        k = (col >> (n - 1 - q)) & 1
        for k2 in (0, 1):
            a = U[k2, k]
            if a:
                M[(col & ~(1 << (n - 1 - q))) | (k2 << (n - 1 - q)), col] += a
    return M


def cnot(c, t, n):
    M = np.zeros((1 << n, 1 << n), dtype=complex)
    for col in range(1 << n):
        if (col >> (n - 1 - c)) & 1:
            M[col ^ (1 << (n - 1 - t)), col] = 1
        else:
            M[col, col] = 1
    return M


def controlled(U, n, targets, controls=()):
    dim = 1 << n
    M = np.zeros((dim, dim), dtype=complex)
    for col in range(dim):
        if not all((col >> (n - 1 - c)) & 1 for c in controls):
            M[col, col] = 1
            continue
        k = 0
        for t in targets:
            k = (k << 1) | ((col >> (n - 1 - t)) & 1)
        for k2 in range(1 << len(targets)):
            a = U[k2, k]
            if not a:
                continue
            bits = [(k2 >> (len(targets) - 1 - i)) & 1
                    for i in range(len(targets))]
            r = col
            for t, b in zip(targets, bits):
                r = (r & ~(1 << (n - 1 - t))) | (b << (n - 1 - t))
            M[r, col] += a
    return M


def toffoli(n, c1, c2, t):
    """Nielsen & Chuang: 6 CNOTs, 7 T-family, 2 H."""
    m = np.eye(1 << n, dtype=complex)
    for op in [("H", t), ("cx", c2, t), ("Td", t), ("cx", c1, t), ("T", t),
               ("cx", c2, t), ("Td", t), ("cx", c1, t), ("T", c2), ("T", t),
               ("H", t), ("cx", c1, c2), ("T", c1), ("Td", c2), ("cx", c1, c2)]:
        if op[0] == "H":
            m = single(H, op[1], n) @ m
        elif op[0] == "T":
            m = single(T, op[1], n) @ m
        elif op[0] == "Td":
            m = single(Td, op[1], n) @ m
        else:
            m = cnot(op[1], op[2], n) @ m
    return m


```

### Verifying the Toffoli decomposition

```python
print("Toffoli decomposition matches CCX:",
      np.allclose(toffoli(3, 0, 1, 2), controlled(X, 3, [2], [0, 1])))
```

### Controlled rotations

```python
def rz(t):
    return np.array([[np.exp(-1j * t / 2), 0], [0, np.exp(1j * t / 2)]],
                    dtype=complex)


def ry(t):
    c, s = np.cos(t / 2), np.sin(t / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


for name, R in (("Rz", rz), ("Ry", ry)):
    ok = True
    for th in (0.3, 1.1, 2.5, -0.7):
        # block-diagonal definition of C-R(theta), control = qubit 0
        CR = np.zeros((4, 4), dtype=complex)
        for c in (0, 1):
            for t in (0, 1):
                for t2 in (0, 1):
                    CR[(c << 1) | t2, (c << 1) | t] = (
                        np.eye(2, dtype=complex)[t2, t] if c == 0
                        else R(th)[t2, t]
                    )
        cn = cnot(0, 1, 2)
        built = cn @ single(R(-th / 2), 1, 2) @ cn @ single(R(th / 2), 1, 2)
        ok &= np.allclose(built, CR)
    print(f"C{name} two-CNOT decomposition correct for all angles:", ok)
```

### Counting multi-controlled cost

```python
def build_CkX(k):
    """C^k X using k-2 clean ancillas. Returns (matrix, toffoli_count, n)."""
    n = k + 1 + (k - 2)
    anc = [k + 1 + i for i in range(k - 2)]
    if k == 2:
        toff = [(0, 1, 2)]
    else:
        toff = [(0, 1, anc[0])]
        for i in range(1, k - 2):
            toff.append((i + 1, anc[i - 1], anc[i]))
        toff.append((k - 1, anc[-1], k))
        for i in range(k - 3, -1, -1):
            toff.append((i + 1, anc[i - 1], anc[i]) if i > 0 else (0, 1, anc[0]))
    m = np.eye(1 << n, dtype=complex)
    for a, b, t in toff:
        m = toffoli(n, a, b, t) @ m
    return m, len(toff), n


print("\nk  Toffolis  2k-3  native  correct")
for k in (2, 3, 4, 5):
    m, nt, n = build_CkX(k)
    ideal = controlled(X, n, [k], list(range(k)))
    anc_mask = (1 << (k - 2)) - 1          # ancillas occupy the low bits
    ok = all(np.allclose(m[:, c], ideal[:, c])
             for c in range(1 << n) if not (c & anc_mask))
    print(f"{k}  {nt:8d}  {2 * k - 3:4d}  {nt * 15:6d}  {ok}")
```

Running the blocks in order prints `True` for the Toffoli decomposition, `True`
for both controlled rotations, and the cost table `1/3/5/7` Toffolis against
`15/45/75/105` native gates, all correct.

## Common misconceptions

- **"Toffoli is a native gate."** It is not. On a typical superconducting
  processor it costs 15 native gates, 7 of them from the $T$ family.
- **"Ancillas are free."** They cost qubits, and they must be **returned to
  $|0\rangle$**. Leaving them dirty entangles them with your computation.
- **"More controls just means a slightly bigger gate."** Without ancillas the
  cost is quadratic in the number of controls. That is why a 10-control
  operation is not a minor variation on a 2-control one.
- **"Controlled-$R_z$ and controlled-$R_y$ behave the same."** The two-CNOT
  decomposition works for both, but $R_z$ is diagonal, so its controlled
  version is symmetric in the two wires. $R_y$ and $R_x$ are not.
- **"Uncomputing is optional."** It is required to disentangle the ancillas.

## Exercises

1. Write out the $8\times8$ matrix of CCX and confirm it is its own inverse.
2. Count the $T$ gates in the Toffoli decomposition and explain why that count
   matters more than the total for fault-tolerant costing.
3. Verify that the two-CNOT controlled-rotation identity fails if you use
   $R(\theta/2)$ twice with the same sign. What does the circuit compute?
4. How many native gates does $C^6X$ cost with clean ancillas? How does the
   answer change without them?
5. Explain why the ancilla chain must be uncomputed, in terms of entanglement.
6. Show that controlled-$R_z$ is symmetric under swapping the two qubits, and
   explain why controlled-$R_y$ is not.

## Summary

- Toffoli (CCX) flips its target when both controls are $|1\rangle$; it is
  universal for classical reversible computation but not alone for quantum
  computation.
- It decomposes into **6 CNOTs, 7 $T$-family gates and 2 $H$** — 15 native
  gates, verified to match the definition exactly.
- Controlled $R_z$ and $R_y$ each cost **2 CNOTs and 2 half-rotations**, via
  $R(\theta/2)$—CNOT—$R(-\theta/2)$—CNOT.
- $C^k X$ with $k-2$ clean ancillas costs exactly **$2k-3$ Toffolis**, or
  $15(2k-3)$ native gates — **linear** in $k$, verified for $k = 2$ to $6$.
- Without ancillas the cost is **quadratic**, $\Theta(k^2)$.
- Ancillas must be uncomputed to $|0\rangle$, or they stay entangled with the
  computation.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  §4.3 — the Toffoli decomposition used here.
- Barenco, A. et al. (1995), "Elementary gates for quantum computation" — the
  source of the $\Theta(k^2)$ versus $\Theta(k)$ ancilla result.
- The [Quantum Gates](02_gates.md) lesson — the native gate set these
  decompositions target.
- The [Grover's Algorithm](06_grover.md) lesson — where multi-controlled
  operations appear as oracles.

---

**Next:** [U3, iSWAP and fSim](39_two_qubit_gates.md)
