# GHZ versus W States

With two qubits there is essentially one kind of entanglement. With three or
more there are genuinely different *classes*, and the two states that define
them are GHZ and W. They are both maximally entangled in some sense, they are
both easy to write down, and they behave completely differently when something
goes wrong. Losing one qubit destroys all the entanglement in a GHZ state and
leaves a W state still entangled. That single difference drives which state you
choose for a given task.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** GHZ and W states for three qubits, and give a preparation
  circuit for each.
- **Compute** the reduced state after losing one qubit, and show that GHZ
  entanglement is destroyed while W entanglement survives.
- **Contrast** the two states using a measurable witness, and state which
  expectation values distinguish them.
- **Explain** why GHZ and W cannot be converted into each other by local
  operations, and what that implies for using them.

## The two states

### GHZ

The **GHZ** state (Greenberger–Horne–Zeilinger) is an equal superposition of
all-zeros and all-ones:

$$|\text{GHZ}\rangle = \frac{|000\rangle + |111\rangle}{\sqrt{2}}$$

It generalises to $n$ qubits as $(|0\rangle^{\otimes n} + |1\rangle^{\otimes n})/\sqrt{2}$.
It is prepared by a Hadamard followed by a
chain of CNOTs:

$$|\text{GHZ}\rangle = \text{CX}_{1\to2}\,\text{CX}_{0\to1}\,(H \otimes I \otimes I)\,|000\rangle$$

This was verified to reproduce the target amplitudes exactly.

### W

The **W** state is the equal superposition over states with exactly **one**
excitation:

$$|W\rangle = \frac{|001\rangle + |010\rangle + |100\rangle}{\sqrt{3}}$$

It generalises to the equal superposition over all $n$ single-excitation
states. Preparation is less obvious than GHZ, because you need amplitudes of
$1/\sqrt{3}$ rather than $1/\sqrt{2}$. One circuit that works, verified
numerically:

1. $R_y(\theta_1)$ on qubit 0, with $\sin^2(\theta_1/2) = \tfrac{1}{3}$, so
   $\theta_1 = 2\arcsin(1/\sqrt{3}) \approx 1.2310$ rad.
2. A controlled $R_y(\pi/2)$ on qubit 1, controlled on qubit 0 being
   $|0\rangle$, splitting the remaining amplitude in two.
3. An $X$ on qubit 2, controlled on qubits 0 and 1 both being $|0\rangle$.

Step 3 is a Toffoli with both controls conditioned on zero, which is why the W
state costs noticeably more to prepare than GHZ.

## Losing a qubit

### The setup

Suppose one qubit is lost — it leaks, it decoheres beyond recovery, or it is
simply traced out because you no longer have access to it. The question is how
much two-qubit entanglement survives in the remaining pair.

Mathematically, trace out one qubit and measure the **concurrence** of what is
left. Concurrence is 0 for an unentangled state and 1 for a maximally
entangled pair.

### The result

Tracing out qubit 0 and computing the concurrence of the remaining pair:

| State | Reduced $\rho$ diagonal | Purity | Concurrence |
|---|---|---|---|
| GHZ | $(0.5,\ 0,\ 0,\ 0.5)$ | 0.500 | **0.000** |
| W | $(\tfrac13,\ \tfrac13,\ \tfrac13,\ 0)$ | 0.556 | **0.667** |

The difference could not be sharper. **GHZ retains no entanglement at all.**
**W retains two-thirds of a maximally entangled pair.**

### Why GHZ collapses

The reduced state of GHZ is

$$\rho_{12} = \tfrac{1}{2}\big(|00\rangle\langle 00| + |11\rangle\langle 11|\big)$$

This is a classical coin flip: the remaining qubits agree, but that
correlation is exactly what a shared random bit gives you. There is no
coherence between $|00\rangle$ and $|11\rangle$ left, because the coherence
lived in the qubit that was lost. All the entanglement was *global*, stored in
the relationship between all three qubits at once, so removing one qubit
destroys it entirely.

### Why W survives

Write the W state grouping by qubit 0:

$$|W\rangle = \sqrt{\tfrac{2}{3}}\,|0\rangle\,\frac{|01\rangle + |10\rangle}{\sqrt{2}} \;+\; \sqrt{\tfrac{1}{3}}\,|1\rangle\,|00\rangle$$

Tracing out qubit 0 then gives

$$\rho_{12} = \tfrac{2}{3}|\psi^+\rangle\langle\psi^+| \;+\; \tfrac{1}{3}|00\rangle\langle 00|$$

with $|\psi^+\rangle = (|01\rangle + |10\rangle)/\sqrt{2}$. This was verified to
match the reduced state exactly. The result is a **mixture** of a maximally
entangled Bell state and a product state, and mixtures of an entangled state
with a product state can still be entangled. Here it is, with concurrence
$2/3$.

The entanglement in W is distributed *pairwise*: every pair of qubits is
entangled, so losing one qubit leaves the other two still entangled.

## A measurable witness

### Distinguishing the states

The two states are told apart by measuring Pauli expectation values. Verified
values for three qubits:

| Observable | GHZ | W |
|---|---|---|
| $\langle XXX\rangle$ | $+1.000$ | $0.000$ |
| $\langle ZZZ\rangle$ | $0.000$ | $-1.000$ |

$\langle XXX\rangle = 1$ is the clean GHZ signature: applying $X$ to all three
qubits maps $|000\rangle$ to $|111\rangle$ and back, so the state is an
eigenstate with eigenvalue $+1$. For W, $XXX$ maps each single-excitation
state to a two-excitation state orthogonal to everything in the superposition,
giving exactly 0.

$\langle ZZZ\rangle$ separates them in the other direction. For GHZ the two
branches $|000\rangle$ and $|111\rangle$ have opposite parity, so the
expectation cancels to 0. For W every component has exactly one $|1\rangle$,
so every term contributes $-1$.

### What makes this a witness

A **witness** is an observable whose expectation value certifies a property.
Here $\langle XXX\rangle$ near 1 certifies GHZ-type entanglement. Because the
two states give values 1 and 0, a single measurement setting separates them —
and that is experimentally cheap compared with full state tomography.

The contrast is also the practical point: if your application needs genuine
multipartite correlation, use GHZ and accept the fragility. If it needs
robustness, use W and accept that its correlations are weaker.

## Why they are inequivalent

GHZ and W belong to different entanglement classes: **no sequence of local
operations and classical communication** can convert one into the other, even
probabilistically with nonzero chance. This follows directly from the loss
result above — LOCC cannot increase entanglement, so an operation that turned
W into GHZ would have to create global entanglement from purely pairwise
entanglement, which it cannot do.

This is a structural fact, not a practical limitation. It is why "how
entangled is this state?" has no single-number answer once you go beyond two
qubits.

## Practical example

### Building both states

```python
import numpy as np

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)


def ry(t):
    c, s = np.cos(t / 2), np.sin(t / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def expand(U, n, targets, controls=(), control_on=1):
    """U on targets, conditional on control qubits equalling control_on."""
    dim = 1 << n
    M = np.zeros((dim, dim), dtype=complex)
    for col in range(dim):
        if not all(((col >> (n - 1 - c)) & 1) == control_on for c in controls):
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


psi0 = np.zeros(8, dtype=complex)
psi0[0] = 1                                    # |000>

# GHZ: H on q0, then a chain of CNOTs
ghz = expand(X, 3, [2], [1]) @ expand(X, 3, [1], [0]) @ expand(H, 3, [0]) @ psi0
ghz_ref = np.zeros(8, dtype=complex)
ghz_ref[0] = ghz_ref[7] = 1 / np.sqrt(2)
print("GHZ circuit correct:", np.allclose(ghz, ghz_ref))

# W: Ry, controlled Ry, then X conditioned on both controls being 0
theta1 = 2 * np.arcsin(1 / np.sqrt(3))
Wc = (expand(X, 3, [2], [0, 1], control_on=0)
      @ expand(ry(np.pi / 2), 3, [1], [0], control_on=0)
      @ expand(ry(theta1), 3, [0]))
w = Wc @ psi0
w_ref = np.zeros(8, dtype=complex)
w_ref[1] = w_ref[2] = w_ref[4] = 1 / np.sqrt(3)
print(f"W circuit correct (theta1 = {theta1:.6f} rad):", np.allclose(w, w_ref))
```

### Losing one qubit

```python
def reduced(psi, keep, n):
    """Trace out every qubit not listed in keep."""
    T = np.outer(psi, psi.conj()).reshape([2] * n + [2] * n)
    for q in sorted([i for i in range(n) if i not in keep], reverse=True):
        T = np.trace(T, axis1=q, axis2=q + n)
    d = 2 ** len(keep)
    return T.reshape(d, d)


def concurrence(rho):
    """Wootters concurrence of a two-qubit density matrix."""
    sy = np.kron(Y, Y)
    ev, V = np.linalg.eigh(rho)
    sq = V @ np.diag(np.sqrt(np.clip(ev, 0, None))) @ V.conj().T
    R = sq @ (sy @ rho.conj() @ sy) @ sq
    e = np.sort(np.sqrt(np.clip(np.linalg.eigvals(R).real, 0, None)))[::-1]
    return max(0.0, e[0] - e[1] - e[2] - e[3])


print("\nafter losing qubit 0:")
for name, psi in (("GHZ", ghz), ("W", w)):
    r = reduced(psi, [1, 2], 3)
    print(f"  {name}: concurrence={concurrence(r):.6f}"
          f"  purity={np.trace(r @ r).real:.4f}"
          f"  diag={np.round(np.diag(r).real, 4)}")
```

### The witnesses

```python
def expval(psi, ops):
    M = ops[0]
    for o in ops[1:]:
        M = np.kron(M, o)
    return np.vdot(psi, M @ psi).real


print("\nPauli witnesses:")
for name, psi in (("GHZ", ghz), ("W", w)):
    print(f"  {name}: <XXX>={expval(psi, [X, X, X]):+.4f}"
          f"   <ZZZ>={expval(psi, [np.diag([1, -1]).astype(complex)] * 3):+.4f}")
```

Running the blocks in order confirms both preparation circuits, prints
concurrence `0.000000` for GHZ and `0.666667` for W after losing a qubit, and
gives $\langle XXX\rangle = +1$ for GHZ against $0$ for W.

## Common misconceptions

- **"Both are maximally entangled, so they are interchangeable."** They belong
  to different entanglement classes; no local operations convert one to the
  other.
- **"Losing a qubit weakens entanglement a bit."** For GHZ it destroys it
  completely — concurrence goes to exactly zero.
- **"W is more entangled than GHZ."** It is *more robust*. GHZ carries stronger
  multipartite correlation; W carries pairwise correlation that survives loss.
- **"The reduced state of W is a pure entangled state."** It is a *mixture* of
  a Bell state and $|00\rangle$. Mixtures of entangled and product states can
  still be entangled, which is why the concurrence is $2/3$, not $1$.
- **"A witness needs full tomography."** A single observable, $\langle XXX\rangle$,
separates the two states.

## Exercises

1. Write the $n$-qubit GHZ and W states, and state how many terms each has.
2. Verify that tracing out qubit 0 of GHZ gives
   $\tfrac12(|00\rangle\langle 00| + |11\rangle\langle 11|)$, and explain why
   that state is separable.
3. Show that $|W\rangle = \sqrt{2/3}\,|0\rangle|\psi^+\rangle + \sqrt{1/3}\,|1\rangle|00\rangle$, and derive
the reduced state.
4. Compute $\langle XXX\rangle$ for the 4-qubit GHZ state. What is the pattern?
5. Explain why no LOCC protocol can convert W into GHZ, using the loss result.
6. Which state would you choose for a quantum network that must tolerate the
   loss of a node, and why?

## Summary

- **GHZ** $=(|000\rangle + |111\rangle)/\sqrt{2}$: one Hadamard and a CNOT
  chain. **W** $=(|001\rangle + |010\rangle + |100\rangle)/\sqrt{3}$: needs
  a rotation with $\sin^2(\theta/2) = 1/3$ and a Toffoli, so it costs more.
- **Losing one qubit**: GHZ concurrence falls to **0.000**, W retains
  **0.667**. GHZ entanglement is global and fragile; W entanglement is
  pairwise and robust.
- The W reduced state is exactly
  $\tfrac{2}{3}|\psi^+\rangle\langle\psi^+| + \tfrac{1}{3}|00\rangle\langle 00|$, a
  mixture that is still entangled.
- **Witnesses**: $\langle XXX\rangle = +1$ for GHZ and $0$ for W;
  $\langle ZZZ\rangle = 0$ for GHZ and $-1$ for W.
- The two states are in different LOCC classes — neither converts to the
  other.

## References

- Greenberger, D. M., Horne, M. A. & Zeilinger, A. — the GHZ argument.
- Dür, W., Vidal, G. & Cirac, J. I. (2000), "Three qubits can be entangled in
  two inequivalent ways" — the classification behind this lesson.
- Wootters, W. K. (1998), "Entanglement of formation of an arbitrary state of
  two qubits" — the concurrence formula used above.
- The [Entanglement Measures](21_entanglement_measures.md) lesson —
  concurrence and how to compute it.

---

**Previous:** [Circuit Identities and Simplification](40_circuit_identities.md)
