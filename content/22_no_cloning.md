# The No-Cloning Theorem

Copying a bit is trivial and invisible; classical computing would be
unrecognisable without it. Quantum computing has no equivalent, and this is
not an engineering gap that better hardware will close — it is a theorem. The
no-cloning theorem follows from linearity and unitarity alone, and it has
consequences in both directions: it forbids some things you might want, and it
is precisely what makes quantum cryptography secure.

## Learning objectives

By the end of this lesson you should be able to:

- **State** the no-cloning theorem, and identify the two assumptions it rests
  on.
- **Reproduce** the proof by contradiction, showing that a cloner would force
  $\langle\psi|\phi\rangle = \langle\psi|\phi\rangle^2$ for arbitrary states.
- **Explain** why the equation $x = x^2$ forces $x \in \{0, 1\}$, and connect
  that to orthogonality.
- **Demonstrate** that CNOT copies computational basis states but not
  superpositions, and compute what it produces instead.
- **Describe** why no-cloning underpins the security of quantum key
  distribution.

## Statement of the theorem

### Formal statement

There is **no unitary operator** $U$ that, for an arbitrary unknown state
$|\psi\rangle$ and a fixed blank state $|0\rangle$, produces

$$U\big(|\psi\rangle \otimes |0\rangle\big) = |\psi\rangle \otimes |\psi\rangle$$

for all $|\psi\rangle$.

### What it does and does not forbid

The theorem forbids copying an **unknown arbitrary** state. It does not forbid:

- **Copying a known state.** If you know $|\psi\rangle$, you can prepare as many
  copies as you like by running the preparation again.
- **Copying from a known orthogonal set.** A set of mutually orthogonal states
  can be copied by a single unitary — this is exactly how quantum error
  correction copies the syndrome, not the data.
- **Preparing many copies from one classical description.** If the description
  of $|\psi\rangle$ is classical information, it copies fine.

## Proof by contradiction

### Setup

Suppose a unitary $U$ clones two states $|\psi\rangle$ and $|\phi\rangle$:

$$U(|\psi\rangle|0\rangle) = |\psi\rangle|\psi\rangle, \qquad U(|\phi\rangle|0\rangle) = |\phi\rangle|\phi\rangle$$

### Step 1: unitary operators preserve inner products

Take the inner product of the two input states:

$$\langle\psi|\phi\rangle \cdot \langle 0|0\rangle = \langle\psi|\phi\rangle$$

since $\langle 0|0\rangle = 1$.

### Step 2: apply the same to the outputs

$$\langle\psi\psi|\phi\phi\rangle = \langle\psi|\phi\rangle \cdot \langle\psi|\phi\rangle = \langle\psi|\phi\rangle^2$$

### Step 3: unitarity forces them equal

Because $U$ is unitary it preserves inner products, so

$$\langle\psi|\phi\rangle = \langle\psi|\phi\rangle^2$$

### Step 4: the only solutions are 0 and 1

Writing $x = \langle\psi|\phi\rangle$, the equation $x = x^2$ has solutions
$x = 0$ and $x = 1$ only. In quantum terms:

- $x = 0$: the states are **orthogonal**.
- $x = 1$: the states are **identical**.

So $U$ could only clone states drawn from a set whose members are all mutually
orthogonal. An arbitrary unknown state is not from such a set, and no universal
cloner exists.

### A concrete contradiction

Take $|\psi\rangle = |0\rangle$ and $|\phi\rangle = |+\rangle$. These are not
orthogonal:

$$\langle 0|+\rangle = \frac{1}{\sqrt{2}} \approx 0.707107$$

But if both were cloned:

$$\langle 00|{+}{+}\rangle = \langle 0|+\rangle^2 = 0.5$$

Unitarity demands $\langle 0|+\rangle = \langle 00|{+}{+}\rangle$, i.e.
$0.707107 = 0.5$. That is false, so the cloner cannot exist.

## What linearity actually gives you

### The Bell state that appears instead

A cloner must be linear. Apply it to $|+\rangle|0\rangle$: since
$|+\rangle = \tfrac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$, linearity gives

$$\tfrac{1}{\sqrt{2}}\big(|0\rangle|0\rangle + |1\rangle|1\rangle\big)$$

That is the Bell state $|\Phi^+\rangle$, **not** $|+\rangle|+\rangle$, which
would be

$$\begin{pmatrix} 0.5 & 0.5 & 0.5 & 0.5 \end{pmatrix}^T$$

versus the $\begin{pmatrix}0.707 & 0 & 0 & 0.707\end{pmatrix}^T$ that linearity
produces. The attempt does not fail gracefully — it produces an entangled
state in which neither register holds a copy of $|+\rangle$.

### Both copies are degraded

Tracing out the second register of the Bell state gives

$$\rho_1 = \begin{pmatrix} 0.5 & 0 \\ 0 & 0.5 \end{pmatrix}$$

with purity $0.5$. Each "copy" is maximally mixed — it has lost all the
information about the relative phase that defined $|+\rangle$. This is the
general pattern: any attempt to spread one qubit's unknown state across two
necessarily degrades it.

## CNOT is not a cloner

### What CNOT does

CNOT with control $|c\rangle$ and target $|0\rangle$ maps
$|c\rangle|0\rangle \mapsto |c\rangle|c\rangle$, for $c \in \{0, 1\}$:

$$\text{CNOT}|0\rangle|0\rangle = |0\rangle|0\rangle \quad \checkmark$$

$$\text{CNOT}|1\rangle|0\rangle = |1\rangle|1\rangle \quad \checkmark$$

So it *does* copy the computational basis states. Many people conclude from
this that cloning is possible. It is not:

$$\text{CNOT}|+\rangle|0\rangle = \tfrac{1}{\sqrt{2}}(|00\rangle + |11\rangle) \neq |+\rangle|+\rangle$$

### Why this matters

CNOT copies **classical information** perfectly and **superpositions** not at
all. That is exactly the content of the theorem, and it is why CNOT appears
everywhere in quantum error correction: there it is used to copy syndrome
information, which is classical by design, never the unknown data state.

## Consequences

### Quantum key distribution

The security of BB84 and related protocols rests directly on no-cloning. An
eavesdropper who wants to learn a qubit in transit must measure it, and
measuring disturbs a non-orthogonal state in a way the legitimate parties can
detect as an elevated error rate. If the eavesdropper could clone the qubit,
they could measure one copy and forward the other untouched, and the
interception would be invisible.

### No backup copies

There is no way to make a spare copy of a quantum state against the
possibility that something goes wrong. Quantum error correction works around
this by spreading information across entanglement rather than by copying it —
which is why it needs many physical qubits per logical qubit.

### Measure-and-prepare is not cloning

Given one copy of an unknown $|\psi\rangle$, measuring it and preparing the
outcome again yields fidelity well below 1. For $|+\rangle$ measured in the
computational basis the average fidelity is $0.5$ — the state is destroyed and
you get a classical guess.

## Practical example

### The contradiction

```python
import numpy as np

ket0 = np.array([1, 0], dtype=complex)
ket1 = np.array([0, 1], dtype=complex)
plus = (ket0 + ket1) / np.sqrt(2)

x = np.vdot(ket0, plus)
print(f"<0|+>      = {x.real:.6f}   (non-orthogonal)")
print(f"<0|+>^2    = {x.real**2:.6f}")
print(f"<00|++>    = {np.vdot(np.kron(ket0, ket0), np.kron(plus, plus)).real:.6f}")
print(f"unitarity requires them equal: "
      f"{np.allclose(x, np.vdot(np.kron(ket0, ket0), np.kron(plus, plus)))}")

print("x = x^2 has solutions only at 0 and 1:")
for xv in (0.0, 1 / np.sqrt(2), 1.0):
    print(f"  x={xv:.6f}  x^2={xv**2:.6f}  equal={abs(xv - xv**2) < 1e-12}")
```

### What linearity produces instead

```python
a = b = 1 / np.sqrt(2)
linearity = a * np.kron(ket0, ket0) + b * np.kron(ket1, ket1)
wanted = np.kron(plus, plus)
print("linearity on |+>|0> gives:", np.round(linearity, 4))
print("a clone would need:       ", np.round(wanted, 4))
print("identical?", np.allclose(linearity, wanted))

rho1 = np.trace(np.outer(linearity, linearity.conj()).reshape(2, 2, 2, 2),
                axis1=1, axis2=3)
print("reduced state of the first 'copy':\n", np.round(rho1, 4))
print(f"purity = {np.trace(rho1 @ rho1).real:.4f}   (1.0 would be a faithful copy)")
```

### CNOT, and why measure-and-prepare is not cloning

```python
CNOT = np.array([[1, 0, 0, 0],
                 [0, 1, 0, 0],
                 [0, 0, 0, 1],
                 [0, 0, 1, 0]], dtype=complex)
for name, v in (("|0>", ket0), ("|1>", ket1), ("|+>", plus)):
    out = CNOT @ np.kron(v, ket0)
    print(f"\nCNOT on {name}|0> = {np.round(out, 4)}")
    print(f"  equals {name}{name}? {np.allclose(out, np.kron(v, v))}")

fidelity = (0.5 * abs(np.vdot(plus, ket0))**2
            + 0.5 * abs(np.vdot(plus, ket1))**2)
print(f"\nmeasure-and-prepare fidelity on |+> = {fidelity:.4f}"
      f"   (a clone would be 1.0)")
```

Running it prints `<0|+> = 0.707107` against `<00|++> = 0.500000`, and the
equality check returns `False` — the contradiction. The $x = x^2$ check shows
`False` for $x = 1/\sqrt{2}$ and `True` only at 0 and 1. The linearity output is
`[0.7071 0 0 0.7071]` against the required `[0.5 0.5 0.5 0.5]`, and the reduced
state of each "copy" is the maximally mixed matrix with `purity = 0.5000`. CNOT
returns `True` for $|0\rangle$ and $|1\rangle$ but `False` for $|+\rangle$, and
measure-and-prepare manages `fidelity = 0.5000`.

## Common misconceptions

- **"No-cloning says nothing can be copied."** Known states and orthogonal
  sets copy fine. Only *unknown arbitrary* states cannot be.
- **"CNOT clones qubits."** It clones computational basis states. Applied to
  $|+\rangle$ it produces an entangled Bell pair, not two copies of $|+\rangle$.
- **"Cloning fails only slightly, so approximate cloning is good enough."**
  Any deterministic cloner fails badly on some states; the best approximate
  cloners drop to fidelity $5/6$, which is measurably wrong and is exactly the
  disturbance QKD detects.
- **"You could clone by measuring carefully first."** Measurement collapses the
  state. Measure-and-prepare on $|+\rangle$ gives fidelity $0.5$.
- **"No-cloning is an obstacle quantum error correction has to defeat."** It is
  the reason QEC is shaped the way it is: error correction copies *syndromes*,
  which are classical, and never the data.

## Exercises

1. Verify numerically that $\langle 0|+\rangle \neq \langle 00|{+}{+}\rangle$,
   and explain which step of the proof this contradicts.
2. Show that a unitary *can* clone the orthogonal pair
   $\{|0\rangle, |1\rangle\}$, and write down a circuit that does it.
3. Solve $x = x^2$ over the reals and confirm the only solutions are 0 and 1.
   What does each mean for the two states?
4. Compute $\text{CNOT}|-\rangle|0\rangle$ and compare it with
   $|-\rangle|-\rangle$. What do you get?
5. Explain in two sentences why no-cloning makes an undetectable
   intercept-resend attack on BB84 impossible.
6. Why does quantum error correction not violate no-cloning, given that it
   protects a logical qubit using several physical ones?

## Summary

- **No-cloning theorem**: no unitary maps $|\psi\rangle|0\rangle$ to
  $|\psi\rangle|\psi\rangle$ for all $|\psi\rangle$.
- The proof needs only linearity and unitarity: a cloner forces
  $\langle\psi|\phi\rangle = \langle\psi|\phi\rangle^2$, whose only solutions
  are 0 (orthogonal) and 1 (identical).
- Concretely, $\langle 0|+\rangle = 0.707$ but $\langle 00|{+}{+}\rangle = 0.5$,
  so a cloner contradicts unitarity.
- Linearity gives the Bell state $\tfrac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$
  rather than $|+\rangle|+\rangle$; each register is then maximally mixed.
- CNOT copies basis states but not superpositions, and no-cloning is what makes
  QKD secure and forces QEC to protect via entanglement rather than copies.

## References

- Wootters, W. K. & Zurek, W. H. *A single quantum cannot be cloned*
  (Nature, 1982) — the original paper.
- Dieks, D. *Communication by EPR devices* (1982) — the independent discovery.
- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §12.1 — no-cloning alongside the other quantum
  information-theoretic limits.

---

**Previous:** [Entanglement Measures](21_entanglement_measures.md) ·
**Next:** [Dirac Notation](23_dirac_notation.md)
