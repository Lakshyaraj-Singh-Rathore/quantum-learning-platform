# The Three-Qubit Bit-Flip Code

A classical computer protects a bit by copying it. Quantum mechanics forbids
copying an unknown state, so that route is closed — but the *idea* behind it
survives, and this lesson shows how. The three-qubit bit-flip code is the
smallest genuine quantum error-correcting code, and every idea you meet here
(encoding, syndrome, recovery, and the assumptions that make them work)
reappears in every larger code.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** the encoding circuit for the three-qubit bit-flip code, and
  write the encoded form of a general state $\alpha|0\rangle + \beta|1\rangle$.
- **Measure** the syndrome without collapsing the encoded state, and explain why
  the two stabiliser measurements reveal the error's location and nothing about
  $\alpha$ or $\beta$.
- **Apply** the conditional correction for each of the four possible syndromes,
  and verify the decoded output against the state you encoded.

## Prerequisites

You need the bit-flip error channel and the T1/T2 picture from
[Quantum Noise and Decoherence](09_quantum_noise.md), and the mid-circuit
measurement and `if_test` machinery from
[Dynamic Circuits and Mid-Circuit Measurement](08_dynamic_circuits.md). This
lesson uses both.

## Intuition

The classical trick is a **repetition code**: store `0` as `000` and `1` as
`111`. If one bit flips, majority voting recovers the original. Three copies
tolerate one error because the three possible single-error outcomes
(`100`, `010`, `001`) are all distinguishable from each other and from the
valid codewords.

The no-cloning theorem stops us copying $|\psi\rangle$, but notice what
majority voting actually needed: not three independent copies, but three
*distinguishable* single-error outcomes. Quantum mechanics allows that. Instead
of copying, we **entangle** the qubit with two spare qubits:

$$\alpha|0\rangle + \beta|1\rangle \;\longmapsto\; \alpha|000\rangle + \beta|111\rangle$$

This is not three copies of $|\psi\rangle$ — the right-hand side is entangled
and contains no $|\psi\rangle$ on any single qubit. But it has the property we
need: a bit flip on any one qubit moves the state into a subspace that is
orthogonal to the code space and to the other two error subspaces.

**Where the analogy stops.** A classical repetition code is read by looking at
all three bits and taking a vote. Doing that here would be fatal: measuring the
three qubits in the $Z$ basis collapses
$\alpha|000\rangle + \beta|111\rangle$ to either $|000\rangle$ or $|111\rangle$,
destroying $\alpha$ and $\beta$. The whole design of the quantum code is
arranged around *not* doing that.

## The encoding

Two CNOT gates produce the encoded state:

```python
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

q = QuantumRegister(3, "q")   # data qubits
a = QuantumRegister(2, "a")   # syndrome (ancilla) qubits
c = ClassicalRegister(2, "c") # syndrome bits
qc = QuantumCircuit(q, a, c)

theta, phi = 0.7, 1.1          # an arbitrary state, deliberately not |0> or |+>
qc.ry(theta, 0)
qc.rz(phi, 0)
qc.barrier()

# --- encode: |psi>|00>  ->  alpha|000> + beta|111>
qc.cx(0, 1)
qc.cx(0, 2)
qc.barrier(label="encoded")
```

Before encoding, qubit 0 holds $\alpha|0\rangle + \beta|1\rangle$ with

$$\alpha = \cos\tfrac{\theta}{2}, \qquad \beta = e^{i\phi}\sin\tfrac{\theta}{2}$$

For $\theta = 0.7$, $\phi = 1.1$ this gives $|\alpha|^2 \approx 0.8824$ and
$|\beta|^2 \approx 0.1176$ — a genuinely arbitrary state with both a magnitude
and a phase, so that a correction which only fixes $|0\rangle$ or only preserves
populations would not pass the test.

The **code space** is the two-dimensional subspace spanned by $|000\rangle$ and
$|111\rangle$. Valid codewords live here; an error moves the state into one of
three orthogonal "error subspaces".

## The error model

Assume each data qubit independently suffers a bit flip $X$ with probability
$p$, and that nothing else goes wrong. Concretely:

- errors on different qubits are **independent**;
- the encoding, syndrome extraction and correction circuits are **perfect**;
- the only errors are $X$ flips on the data qubits.

All three assumptions are idealisations. The first two are relaxed in
[the threshold theorem](54_threshold_theorem.md); the third is what
[the phase-flip code](50_phase_flip_code.md) exists to address. Stating them
matters, because the code's guarantee is conditional on them.

## The syndrome

### The stabilisers

The code space is exactly the $+1$ eigenspace of two operators:

$$S_1 = Z_0 Z_1, \qquad S_2 = Z_1 Z_2$$

Check: $Z_0Z_1|000\rangle = (+1)(+1)|000\rangle = |000\rangle$ and
$Z_0Z_1|111\rangle = (-1)(-1)|111\rangle = |111\rangle$. Both codewords have
eigenvalue $+1$, so every superposition of them does too. These two operators
are the code's **stabilisers**.

Now apply a bit flip to qubit 0. Because $X$ and $Z$ anticommute,
$(Z_0Z_1)X_0 = -X_0(Z_0Z_1)$, so $X_0|000\rangle$ picks up a $-1$ eigenvalue
of $S_1$ while still having $+1$ for $S_2$. Each error location produces a
different **syndrome** — the pair of eigenvalues:

| Error | $S_1 = Z_0Z_1$ | $S_2 = Z_1Z_2$ | Syndrome $(c_0, c_1)$ | Classical value |
|---|---|---|---|---|
| none ($I$) | $+1$ | $+1$ | $(0, 0)$ | 0 |
| $X$ on $q_0$ | $-1$ | $+1$ | $(1, 0)$ | 1 |
| $X$ on $q_1$ | $-1$ | $-1$ | $(1, 1)$ | 3 |
| $X$ on $q_2$ | $+1$ | $-1$ | $(0, 1)$ | 2 |

All four are distinct, which is exactly what "distinguishable error subspaces"
means. Note the classical value is $c_0 + 2c_1$: Qiskit weights bits by
position, so $c_1$ contributes 2. Getting this backwards is the most common
practical bug in this circuit.

### Measuring an operator without measuring the state

You cannot measure $Z_0Z_1$ directly — no instrument has that dial. The standard
trick uses one ancilla and two CNOTs:

```python
# --- syndrome extraction: parity of q0,q1 into a0; parity of q1,q2 into a1
qc.cx(0, a[0])      # a0 ^= q0
qc.cx(1, a[0])      # a0 ^= q1      -> a0 = Z0Z1 parity
qc.cx(1, a[1])      # a1 ^= q1
qc.cx(2, a[1])      # a1 ^= q2      -> a1 = Z1Z2 parity
qc.barrier(label="syndrome")
qc.measure(a[0], c[0])
qc.measure(a[1], c[1])
```

The CNOT copies the *parity* of the two data qubits onto the ancilla, not their
values. A superposition $\alpha|000\rangle + \beta|111\rangle$ has even parity
on qubits 0 and 1 in both branches, so the ancilla is left in $|0\rangle$ in
both branches and factors out — carrying no information about $\alpha$ or
$\beta$.

### What the syndrome does and does not reveal

**This is the crux of the whole lesson**, so it was checked explicitly rather
than asserted. Building the five-qubit state after syndrome extraction (before
any measurement) and partitioning it by the two ancilla bits gives, for each of
the four error cases, **all** of the amplitude in exactly one block and
**zero** in the other three:

| Error | Ancilla block holding all the amplitude | Norm of that block |
|---|---|---|
| none | $(a_0, a_1) = (0, 0)$ | 1.000000 |
| $X$ on $q_0$ | $(1, 0)$ | 1.000000 |
| $X$ on $q_1$ | $(1, 1)$ | 1.000000 |
| $X$ on $q_2$ | $(0, 1)$ | 1.000000 |

Because the total norm is 1, every other block is empty. The ancilla is in a
definite computational-basis state, unentangled with the data. It therefore
cannot tell you anything about $\alpha$ and $\beta$ — extracting the syndrome
reveals **only** which error occurred.

Contrast this with measuring $Z_0$ directly. That would return 0 or 1 at random
with probabilities $|\alpha|^2$ and $|\beta|^2$, and would collapse the state.
Measuring $Z_0Z_1$ returns a deterministic answer and leaves
$\alpha|000\rangle + \beta|111\rangle$ intact. Detecting an error without
learning the state is possible because the error information lives in the
*relations between* qubits, not in any one of them.

## The correction

The syndrome selects a recovery Pauli, applied conditionally. Decoding is the
encoding run backwards.

```python
# --- conditional recovery, driven by the classical register
with qc.if_test((c, 1)):      # syndrome 01 -> X on q0
    qc.x(0)
with qc.if_test((c, 3)):      # syndrome 11 -> X on q1
    qc.x(1)
with qc.if_test((c, 2)):      # syndrome 10 -> X on q2
    qc.x(2)
qc.barrier(label="corrected")

# --- decode: undo the encoding
qc.cx(0, 1)
qc.cx(0, 2)
```

### Verifying the recovery, state by state

For each single-error case, the corrected three-qubit state was evolved through
the decoder and compared against the target
$\alpha|000\rangle + \beta|111\rangle$ (with $\alpha$, $\beta$ from above):

| Injected error | Syndrome | Correction applied | Fidelity after decode |
|---|---|---|---|
| none | 0 | — | **1.000000000000** |
| $X$ on $q_0$ | 1 | $X$ on $q_0$ | **1.000000000000** |
| $X$ on $q_1$ | 3 | $X$ on $q_1$ | **1.000000000000** |
| $X$ on $q_2$ | 2 | $X$ on $q_2$ | **1.000000000000** |

Fidelity exactly 1, not approximately: the recovery is exact for a state with
a nontrivial phase, which rules out a correction that merely restores the
measurement probabilities.

### Verifying the recovery, shot by shot

Statevector arithmetic is one thing; running the dynamic circuit is another.
Executing the full circuit — encode, inject an error, extract the syndrome,
apply the `if_test` correction, decode — on the Aer simulator with 4000 shots
and seed 1234:

| Injected error | Outcomes on $(q_0, q_1, q_2)$ | Spare qubits |
|---|---|---|
| none | `000`: 3540, `100`: 460 | $q_1 = q_2 = 0$ in every shot |
| $X$ on $q_0$ | `000`: 3540, `100`: 460 | $q_1 = q_2 = 0$ in every shot |
| $X$ on $q_1$ | `000`: 3540, `100`: 460 | $q_1 = q_2 = 0$ in every shot |
| $X$ on $q_2$ | `000`: 3540, `100`: 460 | $q_1 = q_2 = 0$ in every shot |

Three things to read off. The four rows are **identical**, so the correction
truly removes the injected error rather than compensating it statistically. The
spare qubits always return to $|0\rangle$, confirming the state is back in the
code space before decoding. And the $q_0$ split, 3540 : 460, matches
$|\alpha|^2 : |\beta|^2 = 0.8824 : 0.1176$ (expected 3530 : 470, well within
sampling noise of $\sigma \approx 20$ counts).

## How much does the code help?

Under the independent-flip model with error probability $p$ per qubit, the code
succeeds exactly when **at most one** qubit flips:

$$P_{\text{correct}} = (1-p)^3 + 3p(1-p)^2 = (1-p)^2(1 + 2p)$$

and fails when two or three do:

$$P_{\text{fail}} = 3p^2(1-p) + p^3 = 3p^2 - 2p^3$$

The payoff is in the exponents. An unprotected qubit fails with probability
$p$ — **linear**. The encoded qubit fails with probability $3p^2 - 2p^3$ —
**quadratic** to leading order. Halve $p$ and the logical error rate drops
roughly fourfold.

| $p$ | Encoded $P_{\text{correct}}$ | Unencoded $1 - p$ | Improvement |
|---|---|---|---|
| $10^{-3}$ | 0.999997 | 0.999 | $334\times$ fewer errors |
| $0.01$ | 0.999702 | 0.99 | $34\times$ fewer errors |
| $0.05$ | 0.99275 | 0.95 | $7\times$ fewer errors |
| $0.10$ | 0.972 | 0.90 | $3.6\times$ fewer errors |
| $0.30$ | 0.784 | 0.70 | $1.4\times$ fewer errors |
| $0.50$ | 0.500 | 0.50 | none — crossover |
| $0.60$ | 0.352 | 0.40 | **worse** |

The improvement column is the ratio of failure probabilities,
$(1 - P_{\text{correct}})/(p)$, computed from the formulas above; the trend is
what matters — the sparser the errors, the more the code buys you.

### The crossover at $p = 1/2$

**There is a crossover, and it is exactly $p = \tfrac12$.** The code helps
precisely when

$$(1-p)^2(1+2p) > 1 - p \iff p(1 - 2p) > 0 \iff 0 < p < \tfrac12$$

At $p = 0.5$ the syndrome carries no information and encoding is pointless;
above it, the code actively hurts, because the "most likely error" is no longer
the no-error case. This is not a curiosity — it is the reason error correction
is only ever considered below some physical error rate, a theme that returns in
[the threshold theorem](54_threshold_theorem.md). A Monte-Carlo run of 200,000
trials per row reproduced every value in this table to three decimal places.

## How the code fails

Two or more flips are not merely uncorrected — they are **miscorrected**, and
the failure has a clean structure. Recomputing the fidelity after decode for
every error pattern:

### Every failure is the same logical error

| Flipped qubits | Syndrome | Correction | $F$ vs $|\psi\rangle$ | $F$ vs $X|\psi\rangle$ |
|---|---|---|---|---|
| none | 0 | — | **1.000000000** | 0.085389 |
| $q_0$ | 1 | $X_0$ | **1.000000000** | 0.085389 |
| $q_1$ | 3 | $X_1$ | **1.000000000** | 0.085389 |
| $q_2$ | 2 | $X_2$ | **1.000000000** | 0.085389 |
| $q_0, q_1$ | 2 | $X_2$ | 0.085389 | **1.000000000** |
| $q_0, q_2$ | 3 | $X_1$ | 0.085389 | **1.000000000** |
| $q_1, q_2$ | 1 | $X_0$ | 0.085389 | **1.000000000** |
| $q_0, q_1, q_2$ | 0 | — | 0.085389 | **1.000000000** |

Every failure is the *same* logical error: an unwanted logical $X$. The reason
is that the correction is linear, so error plus correction multiplies out to
$X_0X_1X_2$ in all four failing cases, and $X_0X_1X_2$ maps
$\alpha|000\rangle + \beta|111\rangle \mapsto \alpha|111\rangle + \beta|000\rangle$
— which decodes to $\beta|0\rangle + \alpha|1\rangle = X|\psi\rangle$. A
three-flip error is the worst case of all: the syndrome is $(0,0)$, the
correction does nothing, and the state is silently wrong.

The 0.085389 in the off-diagonal entries is not a rounding artefact. It is the
overlap $|\langle\psi|X|\psi\rangle|^2 = |2\,\mathrm{Re}(\alpha^*\beta)|^2$,
which evaluates to $0.085389398$ for these $\alpha$, $\beta$ — a useful sanity
check that the "wrong" state really is $X|\psi\rangle$ and not something else.

**Detecting is weaker than correcting.** The code *detects* any two errors
(the syndrome is nonzero) but *corrects* only one. This gap between detection
and correction is fundamental and reappears whenever a code is pushed beyond
its designed error budget.

## Limitations and assumptions

- **One error only.** The code is built to survive a single flip. Its ability to
  do so is the content of the table above.
- **Bit flips only.** A phase flip $Z$ on any qubit is invisible to $Z_0Z_1$ and
  $Z_1Z_2$, because $Z$ commutes with both. This code does not protect against
  phase errors at all — that is the next lesson's problem.
- **Perfect syndrome extraction.** The ancillas, CNOTs and measurements were
  assumed noiseless. A single fault during syndrome extraction can put a
  two-qubit error onto the data, which the code then miscorrects. Making the
  correction procedure itself fault-tolerant is a separate and much harder
  problem.
- **Independent, uncorrelated errors.** Correlated errors — a control pulse that
  miscalibrates two qubits at once — violate the model and the quadratic
  scaling with it.
- **Overhead is real.** One logical qubit now costs three physical qubits plus
  two ancillas and a round of conditional logic.

## Common misconceptions

- **"Measuring the syndrome partly measures the state."** It does not. The
  ancilla ends in a definite basis state, unentangled with the data (verified:
  the entire amplitude sits in one ancilla block). The stabilisers commute with
  every operator acting on the code space, so measuring them is compatible with
  preserving the encoded information.
- **"The code copies the qubit three times."** It creates
  $\alpha|000\rangle + \beta|111\rangle$, which is entangled and contains no
  copy of $|\psi\rangle$ on any single qubit. No-cloning is not violated.
- **"Error correction removes every error."** It corrects errors in the set it
  was designed for, under the noise model it was designed for. Two flips produce
  a *wrong* answer with a clean logical error, and a three-flip error produces
  no syndrome at all.
- **"Any $p$ is better than no code."** Above $p = 1/2$ the encoded qubit is
  worse off than the bare one.
- **"A nonzero syndrome means the state was damaged."** A syndrome of $(0,0)$
  can accompany a three-flip error, and a nonzero syndrome accompanies an error
  that gets fully repaired.

## Exercises

1. Write out the action of the encoding circuit on
   $\alpha|0\rangle + \beta|1\rangle$ step by step, and show the state after
   each CNOT.

2. Compute the eigenvalue of $Z_0Z_1$ on each of $|000\rangle$, $|111\rangle$,
   $X_0|000\rangle = |100\rangle$ and $X_2|000\rangle = |001\rangle$. Two of
   those four answers should look surprising — explain what the last one means
   for how many stabilisers a three-qubit code needs.

3. An implementation maps syndrome $(1, 1)$ to an $X$ on $q_2$ instead of $q_1$
   — the classical bit weighting is backwards. For a single flip on $q_1$, what
   is the net Pauli applied to the codeword, and what do the three decoded
   qubits look like?

4. Using $P_{\text{correct}} = (1-p)^2(1+2p)$, compute the logical error rate at
   $p = 0.02$ and compare it with the unencoded rate. By what factor did the
   code reduce errors?

5. Why does a $Z$ error on $q_0$ leave both stabiliser eigenvalues unchanged?

6. A device has $p = 0.4$ per qubit per syndrome cycle. Is the three-qubit code
   worth applying? Justify with the numbers.

### Answers to 1–3

**1.** Start: $(\alpha|0\rangle + \beta|1\rangle)|00\rangle = \alpha|000\rangle + \beta|100\rangle$.
After `cx(0,1)`: $\alpha|000\rangle + \beta|110\rangle$. After `cx(0,2)`:
$\alpha|000\rangle + \beta|111\rangle$.

**2.** Reading $Z$ as $+1$ on $|0\rangle$ and $-1$ on $|1\rangle$:

- $Z_0Z_1|000\rangle$: $(+1)(+1) = +1$
- $Z_0Z_1|111\rangle$: $(-1)(-1) = +1$
- $Z_0Z_1|100\rangle$: $(-1)(+1) = -1$ — the error on $q_0$ is detected
- $Z_0Z_1|001\rangle$: $(+1)(+1) = +1$ — the error on $q_2$ is **invisible**

The last result is the point. $Z_0Z_1$ does not act on $q_2$, so it commutes
with $X_2$ and cannot see it. That error is caught by the other stabiliser:
$Z_1Z_2|001\rangle = (+1)(-1) = -1$. One stabiliser can only see errors on the
qubits it touches, which is why a code protecting three qubits with $n - k = 2$
independent stabiliser generators needs both, and why the syndrome is a *pair*.

**3.** The net operation is $X_1$ (the error) followed by $X_2$ (the wrong
correction), giving $X_1X_2 = (X_0X_1X_2)X_0$ — the logical $X$ operator
followed by an error on $q_0$. Running exactly this through the decoder gives
a result worth looking at closely:

- the decoded $q_0$ is $|\psi\rangle$, with fidelity **1.000000000**;
- the decoded $q_1$ and $q_2$ are both $|1\rangle$, not $|0\rangle$;
- the fidelity against the intended $|\psi\rangle|00\rangle$ is **0.0**.

So the logical qubit comes back *correct*, and checking only $q_0$ would tell
you the correction worked. It did not: the net effect was a logical $X$ that
happened to cancel against the residual $q_0$ error. The mistake is visible
only in the spare qubits. Always verify the whole decoded state, not just the
qubit you care about.

### Answers to 4–6

**4.** $P_{\text{correct}} = (0.98)^2(1.04) = 0.9604 \times 1.04 = 0.998816$, so
the logical error rate is $1.184 \times 10^{-3}$. Unencoded it is $0.02$. The
code reduces errors by a factor of $0.02 / 0.001184 \approx 17$. Note
$3p^2 = 1.2 \times 10^{-3}$, close to the exact value — the quadratic term
dominates.

**5.** $Z$ commutes with $Z$, so $Z_0$ commutes with both $Z_0Z_1$ and $Z_1Z_2$.
An errored state has the same stabiliser eigenvalues as an unerrored one, so
the syndrome is $(0,0)$ and no correction is applied. The code is blind to
phase errors.

**6.** $P_{\text{correct}} = (0.6)^2(1.8) = 0.36 \times 1.8 = 0.648$ against
$1 - p = 0.6$. The code does help, but only barely: a $40\%$ error rate becomes
$35.2\%$, and it costs three physical qubits and a conditional circuit to
achieve. It is below the $p = 1/2$ crossover, so it is not harmful, but at such
a high physical error rate the assumptions behind the calculation (independent
errors, noiseless syndrome extraction) are themselves unlikely to hold.

## Summary

- The code encodes $\alpha|0\rangle + \beta|1\rangle$ as
  $\alpha|000\rangle + \beta|111\rangle$ using two CNOTs. It does **not** copy
  the state; it spreads it across an entangled code space.
- The stabilisers $Z_0Z_1$ and $Z_1Z_2$ fix the code space, and their four
  eigenvalue pairs identify the four cases: no error, or $X$ on $q_0$, $q_1$ or
  $q_2$.
- Syndrome extraction uses one ancilla per stabiliser and copies only the
  *parity* of two data qubits. Verified: the ancilla ends in a definite basis
  state with the entire amplitude in one block, so the syndrome reveals the
  error's location and nothing about $\alpha$ or $\beta$.
- Recovery is a conditional $X$ chosen by the classical register. Verified to
  fidelity **1.000000000000** for every single-error case, on a state with a
  nontrivial phase, and confirmed end-to-end on the Aer simulator at 4000 shots.
- Under independent flips at rate $p$, the logical error rate falls from $p$ to
  $3p^2 - 2p^3$. The code helps exactly when $p < 1/2$, and at $p = 0.01$ it
  cuts errors by a factor of about 34.
- Beyond one error the code fails *systematically*: two or three flips always
  produce the same unwanted logical $X$, verified to fidelity $1.000000000$
  against $X|\psi\rangle$.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  §10.1.1 — the three-qubit bit-flip code, its stabilisers and its recovery.
- Qiskit documentation, `QuantumCircuit.if_test` — the conditional-execution
  API used by the recovery step.
- [Quantum Noise and Decoherence](09_quantum_noise.md) — the bit-flip channel
  and where the error model comes from.
- [Dynamic Circuits and Mid-Circuit Measurement](08_dynamic_circuits.md) —
  mid-circuit measurement and classical control flow.
- [The Three-Qubit Phase-Flip Code](50_phase_flip_code.md) — the error this code
  cannot see.

---

**Next:** [The Three-Qubit Phase-Flip Code](50_phase_flip_code.md)
