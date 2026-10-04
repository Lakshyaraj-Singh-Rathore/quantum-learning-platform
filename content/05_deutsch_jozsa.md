# Deutsch-Jozsa and Quantum Parallelism

The Deutsch-Jozsa algorithm is the classic first demonstration that a quantum
computer can beat a classical one *with certainty* rather than on average. Its
real lesson is not the problem it solves — nobody needs to classify toy
functions — but the mechanism it exposes: **the speed-up comes from engineering
interference, not from trying many inputs at once.** Understanding that
distinction is what separates quantum intuition from a misleading slogan.

## Learning objectives

By the end of this lesson you should be able to:

- **State** the Deutsch-Jozsa promise and the classical query complexity it beats.
- **Derive** the phase-kickback identity and explain why the target must be
  prepared in $|-\rangle$.
- **Construct** the circuit for a given oracle and predict the measurement outcome.
- **Explain** why the speed-up is interference rather than parallel evaluation.
- **Identify** the mistake that makes a would-be Deutsch-Jozsa circuit return a
  constant answer.

## The problem

You are given a black-box function $f: \{0,1\}^n \to \{0,1\}$ with a **promise**:
it is either

- **constant** — the same output for every input, or
- **balanced** — output 0 for exactly half the inputs and 1 for the other half.

Decide which, using as few queries as possible.

Classically, after $2^{n-1}$ queries that all agree you still cannot be sure:
one untested input could flip the verdict. So the worst case needs
$2^{n-1} + 1$ queries. Deutsch-Jozsa needs **exactly one**.

The promise is essential. Without it — if $f$ could be anything — the problem is
exponentially hard for quantum computers too. Never drop the promise when
describing this algorithm.

## Phase kickback

A classical function is irreversible, so we implement it reversibly as an oracle:

$$U_f: |x\rangle|y\rangle \mapsto |x\rangle|y \oplus f(x)\rangle$$

The trick is to choose the target state so that $f(x)$ lands in the **phase**
instead of the bit value. Prepare the target in
$|-\rangle = (|0\rangle - |1\rangle)/\sqrt2$:

$$U_f|x\rangle|-\rangle = |x\rangle|-\rangle \oplus f(x)\ \text{(shifted)} = (-1)^{f(x)}|x\rangle|-\rangle$$

**Why this works.** The state $|-\rangle$ is an eigenstate of X with eigenvalue
$-1$. Applying X to it (which is what the oracle does when $f(x) = 1$) multiplies
the state by $-1$ rather than flipping it:

$$X|-\rangle = -|-\rangle$$

So the target is left completely unchanged, and the function value appears as a
phase on the *control* register. That is **phase kickback**, and it reappears in
Grover, phase estimation and Shor.

> **The eigenstate requirement is the whole ballgame.** Kickback happens because
> $|-\rangle$ is a $\pm 1$ eigenstate of the flip. Had you used $|+\rangle$ — also
> a superposition — you would get $X|+\rangle = +|+\rangle$, no phase at all, and
> the algorithm would silently fail. This is the single most common way to build
> a broken Deutsch-Jozsa circuit.

## The algorithm

1. Start with $n$ query qubits in $|0\rangle$ and one target in $|1\rangle$.
2. Apply H to all of them. The query register becomes uniform; the target becomes
   $|-\rangle$.
3. Apply the oracle **once**.
4. Apply H to the query register.
5. Measure the query register.

**Interpreting the result:** measure **all zeros** $\Rightarrow$ constant.
**Anything else** $\Rightarrow$ balanced.

## Why it works

After step 3, phase kickback has tagged every branch with its function value:

$$\frac{1}{\sqrt{2^n}}\sum_x (-1)^{f(x)}|x\rangle$$

The final Hadamards compute a Fourier transform over $\{0,1\}^n$, concentrating
the answer into the $|0\cdots0\rangle$ amplitude:

$$\text{amplitude of } |0\cdots0\rangle = \frac{1}{2^n}\sum_x (-1)^{f(x)}$$

Now the two cases:

- **Constant $f$:** every term has the same sign. The sum is $\pm 2^n$, so the
  amplitude is $\pm 1$ and $|0\cdots0\rangle$ has probability 1 —
  **constructive interference**.
- **Balanced $f$:** exactly half the terms are $+1$ and half are $-1$. They cancel
  to zero, so $|0\cdots0\rangle$ has probability 0 — **destructive interference**.

The algorithm never "reads" $f(x)$ for any particular $x$. It arranges for all
$2^n$ values to vote at once, with the wrong answer's votes cancelling.

## Practical example

Verified against **Qiskit 1.2.4** and `qiskit-aer` 0.16.0, `seed_simulator=1234`.
The target is prepared in $|-\rangle$ with `x(1)` before `h(1)`:

```python
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.quantum_info import Statevector

sim = AerSimulator()

def run(qc, shots=1024):
    return sim.run(transpile(qc, sim), shots=shots,
                   seed_simulator=1234).result().get_counts()

# The mistake: target in |+> instead of |->. CNOT leaves |+> unchanged,
# so there is no kickback and no entanglement.
broken = QuantumCircuit(2)
broken.h([0, 1])
broken.cx(0, 1)
print("no kickback:", np.round(Statevector(broken).data, 4))  # all 0.5 -> |+>|+>

# Correct: prepare the target in |-> with x(1) before h(1).
def deutsch_jozsa(oracle):
    qc = QuantumCircuit(2, 1)
    qc.x(1)                 # target starts in |1> ...
    qc.h([0, 1])            # ... so H puts it in |->
    oracle(qc)              # the oracle, applied once
    qc.h(0)                 # Hadamard the query qubit
    qc.measure(0, 0)
    return run(qc)

# Balanced: f(x) = x  -> oracle is a CNOT from query to target
print("balanced f(x)=x:  ", deutsch_jozsa(lambda qc: qc.cx(0, 1)))   # {'1': 1024}
# Balanced: f(x) = 1 - x -> flip the target, then CNOT
print("balanced f(x)=1-x:",
      deutsch_jozsa(lambda qc: (qc.x(1), qc.cx(0, 1))))              # {'1': 1024}
# Constant: f(x) = 0  -> no oracle gate at all
print("constant f(x)=0:  ", deutsch_jozsa(lambda qc: None))          # {'0': 1024}
# Constant: f(x) = 1  -> just flip the target
print("constant f(x)=1:  ", deutsch_jozsa(lambda qc: qc.x(1)))       # {'0': 1024}
```

Both balanced oracles return `1` with certainty; both constant oracles return
`0` with certainty. **One query, and the answer is exact** — no probability of
error, no repetition.

**Try it.** In the Composer, place **X** then **H** on q1, **H** on q0, then
**CNOT** with control q0 and target q1, then **H** on q0, and measure q0. With
1024 shots you should see all `1`. Remove the initial **X** on q1 and the result
flips to all `0` — a silently broken circuit, not a random one.

## Scaling to more query qubits

With $n = 2$ and $f(x) = x_0 \oplus x_1$, the oracle is two CNOTs into the
target. Verified with 2048 shots:

| Oracle | Outcome | Verdict |
|--------|---------|---------|
| Balanced, $f = x_0 \oplus x_1$ | `{'11': 2048}` | Balanced (not all zeros) |
| Constant, $f = 0$ | `{'00': 2048}` | Constant (all zeros) |

The structure is identical at any $n$: one oracle call, one layer of Hadamards,
one measurement.

## Common misconceptions

- **"It evaluates $f$ on all $2^n$ inputs at once and reads the answers."**
  No. A measurement would collapse the superposition and return one random
  input. The algorithm extracts a *global* property — the sum of all values —
  which is a different observable entirely.
- **"This proves quantum computers are exponentially faster in general."**
  Deutsch-Jozsa is a promise problem with an artificial structure; it shows a
  separation in the *query* model, not a speed-up for practical computation.
- **"Any superposition in the target works."** Only $|-\rangle$ kicks back. With
  $|+\rangle$ the oracle is the identity and every function looks constant.
- **"Deutsch-Jozsa is probabilistic."** The textbook version is exact. There are
  bounded-error variants, but the promise guarantees a deterministic answer.

## Exercises

**1. Classic** $n$ classical queries are needed to be *sure* for $n = 3$.

**2. Kickback.** Prove $X|-\rangle = -|-\rangle$ by writing $|-\rangle$ in the
computational basis.

**3. Oracle design.** Give the oracle circuit for $f(x_0, x_1) = x_0 \wedge x_1$
over two query qubits. Is this function constant, balanced, or neither?

**4. Prediction.** For $f(x) = 1$ (constant) on one query qubit, what is the
state of the query register just before the final Hadamard?

**5. Debugging.** A student builds H(q0), H(q1), CNOT(0→1), H(q0) and measures
`0` every time for a balanced oracle. What went wrong?

### Answers

**1.** $2^{3-1} + 1 = 5$ queries.

**2.** $X|-\rangle = X\tfrac{1}{\sqrt2}(|0\rangle - |1\rangle) = \tfrac{1}{\sqrt2}(|1\rangle - |0\rangle) = -\tfrac{1}{\sqrt2}(|0\rangle - |1\rangle) = -|-\rangle$.

**3.** Use a **Toffoli (CCX)** with q0 and q1 as controls and the target qubit as
the target. The function is **neither** constant nor balanced: it outputs 1 on
one input out of four. It therefore violates the promise, and Deutsch-Jozsa
makes no guarantee about it.

**4.** The oracle applies a phase of $(-1)^{f(x)} = -1$ to every branch, so the
query register is $\tfrac{1}{\sqrt2}(|0\rangle + |1\rangle) \to \tfrac{1}{\sqrt2}(|0\rangle + |1\rangle)$ multiplied by $-1$ overall — that is, $|+\rangle$ up to
an unobservable global phase. The final H returns $|0\rangle$.

**5.** The target was prepared in $|+\rangle$ rather than $|-\rangle$: there is no
`X` before the `H` on q1. Since $X|+\rangle = +|+\rangle$, the oracle applies no
phase, the query register stays $|+\rangle$, and the final H returns $|0\rangle$.
Every function looks constant. Fix it by adding **X** on q1 before **H** on q1.

## Summary

- Deutsch-Jozsa decides constant versus balanced with **one** query, where
  classical needs $2^{n-1}+1$ in the worst case.
- The oracle is reversible: $U_f|x\rangle|y\rangle = |x\rangle|y \oplus f(x)\rangle$.
- Phase kickback requires the target in $|-\rangle$, a $-1$ eigenstate of X.
- Constant functions interfere constructively at $|0\cdots0\rangle$; balanced
  ones cancel to zero.
- The speed-up is **interference**, not parallel evaluation.
- The promise (constant *or* balanced) is essential to the guarantee.

Next, **[Grover's Search](06_grover.md)** uses the same interference idea to
amplify a single marked answer.

## References

- Deutsch, D. & Jozsa, R. "Rapid solution of problems by quantum computation",
  *Proceedings of the Royal Society of London A* 439 (1992) 553.
- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §1.4.4, §3.3.
- Cleve, R., Ekert, A., Macchiavello, C. & Mosca, M. "Quantum algorithms
  revisited", *Proceedings of the Royal Society of London A* 454 (1998) 339.
- Qiskit documentation, "Deutsch-Jozsa algorithm":
  https://docs.quantum.ibm.com/
