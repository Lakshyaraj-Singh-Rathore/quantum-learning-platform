# The Three-Qubit Phase-Flip Code

The bit-flip code protects against $X$. It is completely blind to $Z$, which
matters because phase errors are the more common failure on real hardware. This
lesson builds the code that handles them — and the nice part is that it is not a
new construction at all. It is the bit-flip code viewed in a different basis, so
you already know how it works.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** the encoding circuit for the phase-flip code, and show that it
  maps $\alpha|0\rangle + \beta|1\rangle$ onto $\alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$.
- **Show** that the phase-flip code is the bit-flip code conjugated by
  $H^{\otimes 3}$, and derive its stabilisers from that relation.
- **Verify** that a single phase error on any qubit is detected and corrected,
  and state precisely which errors the code cannot see.

## Prerequisites

[The Three-Qubit Bit-Flip Code](49_bit_flip_code.md). Everything here is that
lesson with a basis change applied, so read it first. You also need the
observation from [Quantum Noise and Decoherence](09_quantum_noise.md) that
dephasing changes no $Z$-basis measurement probability — which is exactly why
phase errors are hard to spot.

## Why phase errors are the harder problem

A bit flip is loud. Prepare $|+\rangle$, let an $X$ error through, and the state
becomes $-|+\rangle$ up to nothing at all — but prepare $|1\rangle$ and the
population visibly moves to $|0\rangle$. You can detect it with a $Z$-basis
measurement.

A phase flip is quiet. It maps

$$\alpha|0\rangle + \beta|1\rangle \;\longmapsto\; \alpha|0\rangle - \beta|1\rangle$$

and both states give **exactly the same** $Z$-basis probabilities,
$|\alpha|^2$ and $|\beta|^2$. Nothing in a computational-basis histogram moves.
The damage only becomes visible when you interfere the branches again — apply a
second Hadamard to $|+\rangle$ and a phase flip turns the expected $|0\rangle$
into $|1\rangle$.

This is why the bit-flip code's stabilisers, $Z_0Z_1$ and $Z_1Z_2$, cannot see
phase errors at all: $Z$ commutes with $Z$, so a $Z$ error leaves both
eigenvalues untouched and the syndrome stays $(0, 0)$. The code reports "no
error" while the state is wrong.

On superconducting hardware, dephasing is usually the dominant error channel
anyway, so a code that ignores it is not much use.

## The idea: change basis

Here is the whole trick. The Hadamard conjugates the two Pauli errors into each
other:

$$HZH = X, \qquad HXH = Z$$

So if you wrap every qubit of the bit-flip code in a Hadamard — one before the
encoding and one after — a $Z$ error in the middle is turned into an $X$ error,
which the bit-flip machinery already knows how to handle. Nothing else has to be
reinvented.

Concretely, the phase-flip encoder is the bit-flip encoder **followed** by
$H^{\otimes 3}$.

```python
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

theta, phi = 0.7, 1.1          # same arbitrary state used in the bit-flip lesson
q = QuantumRegister(3, "q")
a = QuantumRegister(2, "a")
c = ClassicalRegister(2, "c")
qc = QuantumCircuit(q, a, c)

qc.ry(theta, 0)
qc.rz(phi, 0)

# --- encode: bit-flip encoder, then H on every qubit
qc.cx(0, 1)
qc.cx(0, 2)
qc.h(0)
qc.h(1)
qc.h(2)
qc.barrier(label="encoded")
```

### What the encoding produces

The bit-flip stage gives $\alpha|000\rangle + \beta|111\rangle$. Applying
$H^{\otimes 3}$ turns $|000\rangle$ into $|{+}{+}{+}\rangle$ and $|111\rangle$
into $|{-}{-}{-}\rangle$, so the codeword is

$$|\psi\rangle_L = \alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$$

Verified: the circuit above produces a state whose fidelity against
$\alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$ is **1.000000000000**, with
$\alpha = \cos 0.35 \approx 0.939373$ and
$\beta = e^{1.1i}\sin 0.35 \approx 0.155537 + 0.305593i$.

Two more checks that pin the relationship down:

- the intermediate state, before the Hadamards, matches
  $\alpha|000\rangle + \beta|111\rangle$ to fidelity **1.000000000000**;
- the final codeword equals $H^{\otimes 3}$ applied to that bit-flip codeword,
  to fidelity **1.000000000000**.

That second line is the objective in one sentence: **the phase-flip code is the
bit-flip code in the $X$ basis.** In the $X$ basis, where $|+\rangle$ plays the
role of $|0\rangle$ and $|-\rangle$ plays the role of $|1\rangle$, the codeword
$\alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$ is literally the repetition
code $\alpha|000\rangle + \beta|111\rangle$ with the labels changed, and a $Z$
error is literally a bit flip, because $Z$ swaps $|+\rangle$ and $|-\rangle$.

## The stabilisers

Conjugation moves the stabilisers too. Verified by direct matrix multiplication:

$$H^{\otimes 3}\,(Z_0Z_1)\,H^{\otimes 3} = X_0X_1, \qquad H^{\otimes 3}\,(Z_1Z_2)\,H^{\otimes 3} = X_1X_2$$

So the stabilisers of the phase-flip code are

$$S_1 = X_0X_1, \qquad S_2 = X_1X_2$$

and the code space is their common $+1$ eigenspace. Measured on the codeword
itself:

| Operator | $\langle S \rangle$ on the codeword | Role |
|---|---|---|
| $X_0X_1$ | $+1.000000000000$ | stabiliser |
| $X_1X_2$ | $+1.000000000000$ | stabiliser |
| $Z_0Z_1$ | $0.000000000000$ | **not** a stabiliser |
| $Z_1Z_2$ | $0.000000000000$ | **not** a stabiliser |

The zeros in the last two rows are the point. An expectation value of exactly 0
means the codeword is not an eigenvector of $Z_0Z_1$ at all — it is a
superposition of the $+1$ and $-1$ eigenspaces. The old stabilisers are not
merely unhelpful here; they are not stabilisers of this code.

## The syndrome

Because $X$ and $Z$ anticommute, a $Z$ error flips the eigenvalue of any
stabiliser that touches the same qubit. The arithmetic is identical to the
bit-flip case, and so is the table:

| Error | $S_1 = X_0X_1$ | $S_2 = X_1X_2$ | Syndrome $(c_0, c_1)$ | Classical value |
|---|---|---|---|---|
| none | $+1$ | $+1$ | $(0, 0)$ | 0 |
| $Z$ on $q_0$ | $-1$ | $+1$ | $(1, 0)$ | 1 |
| $Z$ on $q_1$ | $-1$ | $-1$ | $(1, 1)$ | 3 |
| $Z$ on $q_2$ | $+1$ | $-1$ | $(0, 1)$ | 2 |

Verified by computing the expectation values of $X_0X_1$ and $X_1X_2$ on the
errored codeword: $\pm 1.000000$ to six decimal places in every cell.

### Measuring an $X$-type stabiliser

The bit-flip lesson measured $Z$-type parity with CNOTs from the data to the
ancilla. An $X$-type stabiliser needs the controlled operation the other way
round: put the ancilla in $|+\rangle$, use it as the **control**, and apply
$X$ to each data qubit it touches.

```python
# --- syndrome extraction for the X-type stabilisers
for (qs, anc) in [((0, 1), a[0]), ((1, 2), a[1])]:
    qc.h(anc)              # ancilla into |+>
    for t in qs:
        qc.cx(anc, t)      # controlled-(X X): the ancilla is the CONTROL
    qc.h(anc)
    qc.barrier()

qc.measure(a[0], c[0])
qc.measure(a[1], c[1])
```

Getting the CNOT direction wrong here is an easy mistake, and it is silent: with
the control and target swapped the ancilla measures a $Z$-type parity instead of
an $X$-type one, which on this code gives an uninformative result and a
correction that does nothing useful. (It was caught while preparing this lesson
by checking the decoded output, which is the only reliable way to notice.)

## The correction

The recovery is a conditional $Z$, chosen by the same mapping as before, and
decoding is the encoder run backwards.

```python
# --- conditional recovery
with qc.if_test((c, 1)):      # syndrome 01 -> Z on q0
    qc.z(0)
with qc.if_test((c, 3)):      # syndrome 11 -> Z on q1
    qc.z(1)
with qc.if_test((c, 2)):      # syndrome 10 -> Z on q2
    qc.z(2)
qc.barrier(label="corrected")

# --- decode: H on all three, then undo the CNOTs
qc.h(0)
qc.h(1)
qc.h(2)
qc.cx(0, 1)
qc.cx(0, 2)
```

Note that syndrome 0 applies **no** correction. It is tempting to write the
mapping as a dictionary with an entry for every value including 0; doing so
applies an unwanted $Z_0$, which silently becomes a logical error.

### Verified: the recovery works

Running the full circuit on the Aer simulator, 4000 shots, seed 1234, injecting
each single phase error in turn:

| Injected error | Outcomes on $(q_0, q_1, q_2)$ | Spare qubits |
|---|---|---|
| none | `000`: 3540, `100`: 460 | $q_1 = q_2 = 0$ in every shot |
| $Z$ on $q_0$ | `000`: 3540, `100`: 460 | $q_1 = q_2 = 0$ in every shot |
| $Z$ on $q_1$ | `000`: 3540, `100`: 460 | $q_1 = q_2 = 0$ in every shot |
| $Z$ on $q_2$ | `000`: 3540, `100`: 460 | $q_1 = q_2 = 0$ in every shot |

Identical to the bit-flip lesson, and identical to the no-error baseline. The
3540 : 460 split reproduces $|\alpha|^2 : |\beta|^2 = 0.8824 : 0.1176$
(expected 3530 : 470, within sampling noise of $\sigma \approx 20$).

The statevector check is stronger, because shot statistics on $q_0$ alone cannot
distinguish $|\psi\rangle$ from a state with the same populations and a different
phase. Tracing out the spare qubits after decoding and comparing the reduced
state of $q_0$ against $|\psi\rangle$:

| Injected error | Syndrome | Correction | $F(q_0, |\psi\rangle)$ |
|---|---|---|---|
| none | 0 | — | **1.000000000** |
| $Z$ on $q_0$ | 1 | $Z_0$ | **1.000000000** |
| $Z$ on $q_1$ | 3 | $Z_1$ | **1.000000000** |
| $Z$ on $q_2$ | 2 | $Z_2$ | **1.000000000** |

All four decode to the *same* state, not merely to states with the same
measurement statistics.

### Verified: skipping the correction leaves a trace

With the syndrome measured but no correction applied, the error survives and
shows up on the spare qubits. The probability distribution over $(q_1, q_2)$
after decoding:

| Injected error | $(q_1, q_2)$ after decode | $F(q_0, |\psi\rangle)$ |
|---|---|---|
| none | $(0, 0)$ with probability 1.0000 | 1.000000000 |
| $Z$ on $q_0$ | $(1, 1)$ with probability 1.0000 | 0.085389 |
| $Z$ on $q_1$ | $(1, 0)$ with probability 1.0000 | 1.000000000 |
| $Z$ on $q_2$ | $(0, 1)$ with probability 1.0000 | 1.000000000 |

Read this carefully, because it contains a trap. For $q_1$ and $q_2$ the logical
state on $q_0$ is undamaged, and only the spares reveal that anything happened.
For $q_0$ the logical state is genuinely corrupted — the fidelity 0.085389 is
$|\langle\psi|X|\psi\rangle|^2$, so the decoded qubit is $X|\psi\rangle$, not
$|\psi\rangle$. **Checking the logical qubit alone is not a valid test of
whether a correction worked**; you must check the spares too.

## What this code cannot do

### Bit flips are invisible

$X$ commutes with $X$, so a bit flip leaves both stabiliser eigenvalues at $+1$
and produces syndrome $(0, 0)$. Measured, exactly:

| Error | $\langle X_0X_1\rangle$ | $\langle X_1X_2\rangle$ | Syndrome |
|---|---|---|---|
| $X$ on $q_0$ | $+1.000000$ | $+1.000000$ | $(0, 0)$ |
| $X$ on $q_1$ | $+1.000000$ | $+1.000000$ | $(0, 0)$ |
| $X$ on $q_2$ | $+1.000000$ | $+1.000000$ | $(0, 0)$ |

The code reports "nothing happened" and applies no correction. The state is
still damaged: after decoding, $F(q_0, |\psi\rangle) = 0.584984$ for an $X$
error on any of the three qubits. That number is
$(|\alpha|^2 - |\beta|^2)^2 = 0.764842^2 = 0.584983$, which is
$|\langle\psi|Z|\psi\rangle|^2$ — the signature of a **logical $Z$** error. An
$X$ error on this code is an undetected logical $Z$.

So the two codes are exactly complementary: the bit-flip code corrects $X$ and
is blind to $Z$; the phase-flip code corrects $Z$ and is blind to $X$. **Neither
one protects a general qubit.** Handling both at once needs more qubits and more
stabilisers, which is where [the stabiliser formalism](51_stabilizer_formalism.md)
and ultimately [surface codes](52_surface_codes.md) come in.

### Two phase flips fail, and fail as a logical $X$

The failure structure mirrors the bit-flip code but is worth stating precisely,
because the operator that appears is not the one you might guess. Injecting two
or three phase errors and applying whatever correction the syndrome selects:

| Phase errors | Syndrome | Correction | $F(q_0, |\psi\rangle)$ | $F(q_0, X|\psi\rangle)$ |
|---|---|---|---|---|
| $q_0, q_1$ | 2 | $Z_2$ | 0.085389 | **1.000000000** |
| $q_0, q_2$ | 3 | $Z_1$ | 0.085389 | **1.000000000** |
| $q_1, q_2$ | 1 | $Z_0$ | 0.085389 | **1.000000000** |
| $q_0, q_1, q_2$ | 0 | — | 0.085389 | **1.000000000** |

Every failure is the same **logical $X$**, not a logical $Z$. The reason is that
the logical operators of this code are the bit-flip code's logical operators
conjugated by $H^{\otimes 3}$:

$$X_L = Z_0Z_1Z_2, \qquad Z_L = X_0$$

Verified: $Z_0Z_1Z_2$ maps the codeword $\alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$
onto one with the amplitudes exchanged, and $X_0$ maps it onto
$\alpha|{+}{+}{+}\rangle - \beta|{-}{-}{-}\rangle$. So the error plus correction
multiplies out to $Z_0Z_1Z_2 = X_L$ in every failing row, which is why the
decoded qubit comes back as $X|\psi\rangle$.

## Limitations and assumptions

The assumptions are the same family as the bit-flip code's, and they matter just
as much:

- **One error only.** Two or more phase errors produce a silent logical $X$.
- **Phase errors only.** Bit flips are invisible and become logical $Z$ errors.
- **Perfect syndrome extraction.** The ancillas, the three CNOTs per stabiliser
  and the measurements are all assumed noiseless.
- **Independent errors.** Correlated dephasing across qubits violates the model.
- **Overhead.** Three physical qubits plus two ancillas for one logical qubit
  that is protected against only half of the possible single-qubit errors.

## Common misconceptions

- **"It is a different code, so I have to learn it from scratch."** It is the
  bit-flip code conjugated by $H^{\otimes 3}$. Everything — the syndrome table,
  the correction mapping, the failure structure — carries over unchanged.
- **"The stabilisers are still $Z_0Z_1$ and $Z_1Z_2$."** They are $X_0X_1$ and
  $X_1X_2$. The codeword is not even an eigenvector of $Z_0Z_1$; the expectation
  value is exactly 0.
- **"Measuring $X_0X_1$ uses the same CNOT pattern as measuring $Z_0Z_1$."** The
  control and target swap. Copying the $Z$-type gadget gives an ancilla that
  carries no useful information.
- **"A syndrome of $(0,0)$ means the state is fine."** An $X$ error gives
  syndrome $(0,0)$ and leaves the decoded state at fidelity 0.584984. A
  three-phase-flip error also gives $(0,0)$.
- **"This code protects a qubit."** It protects against phase errors only. You
  need both codes' worth of stabilisers to protect against a general error.

## Exercises

1. Show that $HZH = X$ by writing out both $2\times2$ matrices and multiplying
   them.

2. Apply $H^{\otimes 3}$ to $|000\rangle$ and to $|111\rangle$, and hence verify
   that the encoder sends $\alpha|0\rangle + \beta|1\rangle$ to
   $\alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$.

3. A single $Z$ error occurs on $q_1$. What is the syndrome, which correction is
   applied, and what is the net operator acting on the codeword?

4. Compute $\langle X_0X_1\rangle$ on the codeword $\alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$
   directly, by acting on each of $|{+}{+}{+}\rangle$ and $|{-}{-}{-}\rangle$
   separately.

5. An $X$ error on $q_0$ goes undetected. Explain in one sentence why the
   stabilisers miss it, and state what logical error it produces.

6. The code's logical operators are $X_L = Z_0Z_1Z_2$ and $Z_L = X_0$. Verify
   that $Z_L$ as written really does act as $Z$ on the logical basis, by
   computing its action on $|{+}{+}{+}\rangle$ and on $|{-}{-}{-}\rangle$.

### Answers to 1–3

**1.** With
$H = \tfrac{1}{\sqrt2}\begin{pmatrix}1 & 1 \\ 1 & -1\end{pmatrix}$ and
$Z = \begin{pmatrix}1 & 0 \\ 0 & -1\end{pmatrix}$:

$$HZ = \tfrac{1}{\sqrt2}\begin{pmatrix}1 & -1 \\ 1 & 1\end{pmatrix}$$

and

$$HZH = \tfrac12\begin{pmatrix}1 & -1 \\ 1 & 1\end{pmatrix}\begin{pmatrix}1 & 1 \\ 1 & -1\end{pmatrix} = \begin{pmatrix}0 & 1 \\ 1 & 0\end{pmatrix} = X$$

**2.** $H|0\rangle = |+\rangle$, so
$H^{\otimes3}|000\rangle = |{+}{+}{+}\rangle$. Likewise $H|1\rangle = |-\rangle$,
so $H^{\otimes3}|111\rangle = |{-}{-}{-}\rangle$. The bit-flip encoder produces
$\alpha|000\rangle + \beta|111\rangle$, and applying $H^{\otimes 3}$ to that
superposition gives $\alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$ by
linearity.

**3.** $Z$ on $q_1$ anticommutes with both $X_0X_1$ (which touches $q_1$) and
$X_1X_2$ (which also touches $q_1$), so the syndrome is $(1, 1)$, classical
value $1 + 2 = 3$, and the correction is $Z$ on $q_1$. The net operator is
$Z_1 Z_1 = I$ — the error is undone exactly.

### Answers to 4–6

**4.** $X|+\rangle = |+\rangle$ and $X|-\rangle = -|-\rangle$. So
$X_0X_1|{+}{+}{+}\rangle = (+1)(+1)|{+}{+}{+}\rangle = |{+}{+}{+}\rangle$, and
$X_0X_1|{-}{-}{-}\rangle = (-1)(-1)|{-}{-}{-}\rangle = |{-}{-}{-}\rangle$. Both
logical basis states have eigenvalue $+1$, so every superposition of them does
too, and $\langle X_0X_1\rangle = +1$ for any codeword.

**5.** $X$ commutes with $X$, so an $X$ error commutes with both $X_0X_1$ and
$X_1X_2$ and changes neither eigenvalue — the syndrome stays $(0,0)$ and no
correction is applied. Undetected, it acts as a logical $Z$ on the encoded
state, leaving the decoded qubit at fidelity 0.584984 against $|\psi\rangle$.

**6.** $Z_L = X_0$ gives $X_0|{+}{+}{+}\rangle = |{+}{+}{+}\rangle$ (since
$X|+\rangle = |+\rangle$), so the $|0_L\rangle$ amplitude is unchanged, and
$X_0|{-}{-}{-}\rangle = -|{-}{-}{-}\rangle$ (since $X|-\rangle = -|-\rangle$),
so the $|1_L\rangle$ amplitude picks up a minus sign. That is exactly the action
of $Z$ on a logical basis — leave $|0_L\rangle$ alone, negate $|1_L\rangle$.
Note that $X_0$ is not the only choice: $X_1$ and $X_2$ act identically on the
code space, because they differ from $X_0$ by the stabiliser-like products
$X_0X_1$ and $X_1X_2$ respectively.

## Summary

- A phase flip leaves every $Z$-basis probability unchanged, which is why the
  bit-flip code's $Z$-type stabilisers cannot see it.
- Since $HZH = X$ and $HXH = Z$, wrapping the bit-flip code in Hadamards turns
  phase errors into bit errors. The encoder is the bit-flip encoder followed by
  $H^{\otimes 3}$, and the codeword is
  $\alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$ — verified to fidelity
  **1.000000000000**, and verified to equal $H^{\otimes 3}$ applied to the
  bit-flip codeword.
- The stabilisers become $X_0X_1$ and $X_1X_2$. The old $Z$-type operators are
  not stabilisers of this code: the codeword gives expectation value exactly
  0 for them.
- The syndrome table and the correction mapping are identical to the bit-flip
  code's. Verified to fidelity **1.000000000** for a single phase error on any
  qubit, and end-to-end on Aer at 4000 shots with the spare qubits returning to
  $|00\rangle$ every time.
- The code is blind to bit flips, which become undetected logical $Z$ errors
  (fidelity 0.584984 $= (|\alpha|^2 - |\beta|^2)^2$). Neither three-qubit code
  protects a general qubit.
- Two or more phase errors fail as a logical **$X$**, because this code's
  $X_L$ is $Z_0Z_1Z_2$ and its $Z_L$ is $X_0$.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  §10.1.2 — the three-qubit phase-flip code and its relation to the bit-flip
  code by basis change.
- [The Three-Qubit Bit-Flip Code](49_bit_flip_code.md) — the construction this
  lesson conjugates.
- [Quantum Noise and Decoherence](09_quantum_noise.md) — why dephasing is
  invisible in the $Z$ basis.
- [Stabilizer Formalism](51_stabilizer_formalism.md) — the language that
  unifies both codes, and the route to protecting against both error types.

---

**Next:** [Stabilizer Formalism](51_stabilizer_formalism.md)
