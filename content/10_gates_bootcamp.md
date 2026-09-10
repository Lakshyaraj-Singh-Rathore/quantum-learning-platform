<!-- track: circuit -->
# Gates Bootcamp: Every Gate, Step by Step

A hands-on tour of the whole palette. For each gate: what it does, the smallest
circuit that shows it, what you should see, and the mistake people usually make.

Work through this with the **Composer** open in another tab. Use the
**Timeline** panel to step through each circuit gate by gate.

> **Bit order.** This platform follows Qiskit: in a bitstring like `011`,
> **qubit 0 is the rightmost character**. So `001` means q0 is excited.

---

## 1. Identity (I)

**What it does.** Nothing. It is a placeholder that occupies one time slot.

**Circuit.** `I` on q0.

**Expect.** `0` with 100% probability.

**Why it exists.** It documents idle time. On real hardware an idle qubit is
still decohering, so an explicit identity makes that visible.

**Common mistake.** Expecting `I` to reset a qubit. It does not — it leaves the
state exactly as it was.

---

## 2. X — the quantum NOT

**What it does.** Swaps $|0\rangle$ and $|1\rangle$.

$$X = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$$

**Circuit.** `X` on q0, then measure.

**Expect.** `1` with 100% probability.

**Common mistake.** Thinking X is "random". It is fully deterministic and
reversible: two X gates return you to the start.

---

## 3. H — Hadamard, the superposition maker

**What it does.** Maps $|0\rangle \to \tfrac{1}{\sqrt2}(|0\rangle + |1\rangle)$
and $|1\rangle \to \tfrac{1}{\sqrt2}(|0\rangle - |1\rangle)$.

**Circuit.** `H` on q0, measure, 1024 shots.

**Expect.** Roughly 512 / 512. Not exactly — that is sampling noise, and the
**Born vs shots** tab shows it shrinking as you raise the shot count.

**The important experiment.** Now apply **two** Hadamards in a row with no
measurement between them. You get `0` with certainty. The randomness was never
"already there" — it appeared only at measurement, and interference removed it.
This is the single most important demonstration in quantum computing.

**Common mistake.** Believing H makes the qubit "secretly 0 or 1 with a coin
flip". If that were true, H·H could not return a definite answer.

---

## 4. Z — phase flip

**What it does.** Leaves $|0\rangle$, sends $|1\rangle \to -|1\rangle$.

**Circuit.** `H`, then `Z`, then measure.

**Expect.** Still 50/50. **The histogram does not change at all.**

**Now see it.** Turn on **Colour bars by relative phase** on the histogram tab.
The bar heights are identical but the colours differ. Or run `H`, `Z`, `H`: you
get `1` with certainty, where `H`,`H` gave `0`. The phase was invisible until
interference converted it into a population difference.

**Common mistake.** Concluding Z "does nothing" because the counts are
unchanged. Phase is real and becomes observable the moment you interfere.

---

## 5. Y

**What it does.** A bit flip and a phase flip together, with a factor of $i$.
$Y = iXZ$.

**Circuit.** `Y` on q0.

**Expect.** `1` with 100% probability — same counts as X. The difference from X
lives in the phase, visible on the phase disk.

---

## 6. S and S-dagger

**What it does.** $S$ adds a $+90°$ phase to $|1\rangle$; $S^\dagger$ adds
$-90°$. Note $S = T^2$ and $Z = S^2$.

**Circuit.** `H` then `S`.

**Expect.** 50/50 counts. On the **phase disk**, $|1\rangle$ now sits 90° away
from $|0\rangle$.

---

## 7. T and T-dagger

**What it does.** A $\pm45°$ phase on $|1\rangle$.

**Why it matters.** H, S, CNOT and friends form the *Clifford* group, which is
efficiently simulable on a classical computer (Gottesman–Knill). **T is what
breaks that.** Without T-type gates you have no quantum advantage. T is also the
most expensive gate in fault-tolerant architectures.

**Circuit.** `H`, `T`, `H`. The output is no longer 50/50 or 0/100 — it is
approximately 85/15, because a 45° phase interferes only partially.

---

## 8. SX — square root of X

**What it does.** Half a bit flip: `SX` twice equals `X`.

**Why it matters.** On real superconducting hardware SX is often a *native*
gate, and X is compiled into two of them.

---

## 9. P, RX, RY, RZ — the parameterised gates

These take an angle. This platform accepts `pi`, numbers, and `+ - * / ( )` —
for example `pi/4` or `2*pi/3`. Symbolic names like `theta` are rejected,
because the value must be known at build time.

| Gate | Rotates about | Effect at angle $\theta$ |
|---|---|---|
| `RX(θ)` | X axis | partial bit flip |
| `RY(θ)` | Y axis | partial bit flip, real amplitudes |
| `RZ(θ)` | Z axis | pure phase, no population change |
| `P(θ)` | — | phase $e^{i\theta}$ on $|1\rangle$ only |

**Circuit.** `RY(pi/2)` on q0 gives 50/50 — the same distribution as H but a
different phase convention.

**Try.** Sweep `RY` from `0` to `pi` and watch probability move smoothly from
all-`0` to all-`1`. Rotations are continuous; X and H are just specific angles.

**Common mistake.** Assuming `RX(pi)` is exactly `X`. It equals X **up to a
global phase** of $-i$. Global phase is unobservable, so the two are physically
identical.

---

## 10. CNOT — the entangler

**What it does.** Flips the target **only if** the control is $|1\rangle$.

**Circuit A (classical).** `X` on q0, then CNOT with control q0, target q1.
Result: `11`. Purely classical copying.

**Circuit B (quantum).** `H` on q0, then the same CNOT. Result: 50%
`00`, 50% `11`, and **never** `01` or `10`.

This is entanglement. The control was in superposition, so the CNOT could not
"decide" whether to flip — it did both, and the two qubits became correlated.

**Check it.** Open the **Bloch** tab. Both arrows have collapsed to the centre,
and the app reports maximum entropy. That is not a bug: an entangled qubit has
**no state of its own**. Use the **Q-sphere** to see the register as a whole.

**Common mistake.** Believing CNOT copies a qubit. It cannot — the no-cloning
theorem forbids it. It copies *classical basis states* only; on a superposition
it entangles instead.

---

## 11. SWAP

**What it does.** Exchanges two qubits. Equivalent to three CNOTs.

**Circuit.** `X` on q0, then SWAP q0 and q1. Result: `10` — the excitation moved
to q1.

**Why it matters.** Real chips do not have all-to-all connectivity, so the
compiler inserts SWAPs to bring distant qubits together. They are expensive and
a major source of error.

---

## 12. Toffoli (CCX) and general MCX

**What it does.** Flips the target only when **all** controls are $|1\rangle$.

**Circuit.** `X` on q0, `X` on q1, then CCX with controls q0, q1 and target q2.
Result: `111`.

**Why it matters.** Toffoli is *classically universal* — AND, OR and NOT can all
be built from it. It is the bridge between classical and quantum logic, and it
appears in every Grover oracle.

In this platform, build one by dropping the gate on the target qubit, then
clicking the control qubits in the same column.

---

## 13. Measure, Reset, Barrier

- **Measure** collapses a qubit and writes a classical bit. **Irreversible** —
  everything after it sees a definite value.
- **Reset** forces a qubit back to $|0\rangle$, letting you recycle it.
- **Barrier** is a scheduling divider. It changes no physics, but it prevents
  the optimiser from moving gates across it.

Once you place a measure or reset, the Timeline stops showing a statevector —
correctly, because the register is no longer a single pure state.

---

## Self-check

1. Which single gate creates superposition from $|0\rangle$?
2. Why does `Z` leave the histogram unchanged, and how can you reveal it?
3. Why is `T` special compared to `H` and `S`?
4. In the Bell circuit, why are both Bloch arrows zero-length?
5. What is the difference between `I` and `Reset`?

<details>
<summary>Answers</summary>

1. `H`.
2. Z only changes phase; make it visible by interfering (`H`,`Z`,`H`) or by
   colouring the histogram by phase.
3. H and S are Clifford gates and are classically simulable; T is non-Clifford
   and is required for quantum advantage.
4. Because each qubit is maximally entangled, its reduced state is maximally
   mixed and has no Bloch vector.
5. `I` leaves the state untouched; `Reset` forces it to $|0\rangle$ regardless
   of what it was.

</details>
