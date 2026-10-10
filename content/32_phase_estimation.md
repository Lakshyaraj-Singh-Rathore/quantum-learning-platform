# Quantum Phase Estimation

If the QFT is the workhorse, phase estimation is the reason anyone cares. It
extracts the eigenphase of a unitary into a readable register, and it is the
engine inside Shor's algorithm, amplitude estimation and HHL. Understand this
one circuit and a large fraction of the quantum algorithms literature becomes
legible.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** the phase estimation circuit, and explain what each stage does.
- **Explain** why the inverse QFT is the final stage, and what happens if it is
  replaced with a forward QFT.
- **State** the precision and success probability in terms of the estimation
  register size $t$.
- **Predict** the outcome for a phase that is exactly representable in $t$ bits
  versus one that is not.

## Prerequisites

This lesson assumes the [Quantum Fourier Transform](31_qft.md) and its circuit,
the Hadamard gate, and the idea of a controlled unitary. It also assumes what an
eigenvalue is: if $U|\psi\rangle = e^{2\pi i\varphi}|\psi\rangle$, then
$\varphi$ is the **phase** we want to learn.

## The problem

You are given a unitary $U$ and an eigenstate $|\psi\rangle$ whose eigenvalue
is $e^{2\pi i\varphi}$. You may prepare $|\psi\rangle$ and apply controlled
powers of $U$. Find $\varphi$.

Classically this is hard: estimating $\varphi$ to $t$ bits generally requires
$O(2^t)$ applications of $U$. Phase estimation does it with $O(2^t)$ *controlled*
applications too — but that is the point: the gate count is $O(t^2)$ once the
controlled operations are available, and the real win is that it produces the
answer as a readable bit string in one coherent run.

## Intuition: phase kickback

### The core trick

A controlled-$U$ with the control in superposition does something surprising.
If the control is $\tfrac{1}{\sqrt2}(|0\rangle + |1\rangle)$ and the target is
the eigenstate $|\psi\rangle$, then

$$\tfrac{1}{\sqrt2}\big(|0\rangle + |1\rangle\big)|\psi\rangle \;\longrightarrow\; \tfrac{1}{\sqrt2}\big(|0\rangle + e^{2\pi i\varphi}|1\rangle\big)|\psi\rangle$$

The target is **unchanged** — it is an eigenstate, so $U$ only multiplies it by
a phase. But that phase has been *kicked back* onto the control qubit. The
target never moves; the information lands on the wire we can read.

This is the same mechanism as in Deutsch–Jozsa and Bernstein–Vazirani, and it
is the single most reused idea in quantum algorithms.

### Turning one phase into many bits

One control qubit gives one bit's worth of phase. Applying controlled-$U^{2^k}$
gives phase $e^{2\pi i 2^k\varphi}$, which is the $k$-th binary digit of
$\varphi$. Do this for $k = 0, 1, \ldots, t-1$ on $t$ control qubits and the
estimation register ends up holding

$$\frac{1}{\sqrt{2^t}}\sum_{j=0}^{2^t-1} e^{2\pi i \varphi j}|j\rangle$$

That is exactly the state the QFT produces from $|2^t\varphi\rangle$. So
applying the **inverse** QFT turns it into $|2^t\varphi\rangle$, and measuring
gives you $\varphi$ to $t$ bits.

## The circuit

### Three stages

The circuit needs two registers: $t$ estimation qubits and a target register
holding $|\psi\rangle$.

1. **Prepare.** Apply $H$ to every estimation qubit, giving a uniform
   superposition over all $j$.
2. **Kick back phase.** For each estimation qubit $q$, apply controlled-$U^{2^k}$
   targeting the eigenstate register, where $k$ is the binary weight of that
   qubit.
3. **Read out.** Apply the inverse QFT to the estimation register and measure
   it.

### A convention that trips people up

Step 2 depends on how you number qubits. This project's circuit IR — and the
Qiskit convention — treats **qubit 0 as the most significant bit**. Under that
convention, estimation qubit $q$ carries binary weight $2^{t-1-q}$, so qubit
$q$ must control $U^{2^{t-1-q}}$, not $U^{2^q}$.

Getting this backwards produces an estimate whose bits are reversed: it looks
like a plausible answer and is wrong. Getting the convention wrong is one of
the most common bugs in hand-written phase estimation.

### Why the inverse QFT

The estimation register after stage 2 holds a state whose amplitudes are
$e^{2\pi i\varphi j}$ — the QFT *of* $|2^t\varphi\rangle$. To recover
$|2^t\varphi\rangle$ you must undo the QFT, hence the **inverse** QFT. Using a
forward QFT instead gives you $|{-2^t\varphi}\rangle$ in a reflected sense: the
bits come out negated and reversed.

## Precision and success probability

### When the phase is exactly representable

If $\varphi = m/2^t$ for an integer $m$, the inverse QFT produces $|m\rangle$
**with certainty**. Verified:

| $t$ | $\varphi$ | Estimate $j$ | $j/2^t$ | $P(\text{best})$ |
|---|---|---|---|---|
| 3 | $5/8$ | 5 | 0.625 | **1.0000** |
| 4 | $5/8$ | 10 | 0.625 | **1.0000** |

Note the estimate is the integer $j$, and you recover $\varphi$ as $j/2^t$. At
$t=3$ it is $5$; at $t=4$ it is $10$ — the same value $0.625$, at higher
resolution.

### When it is not

Most phases are not dyadic rationals, so the answer cannot be exact and the
distribution spreads over neighbouring integers. Verified for $\varphi = 1/3$:

| $t$ | Best $j$ | $j/2^t$ | $P(\text{best})$ |
|---|---|---|---|
| 3 | 3 | 0.375 | 0.6878 |
| 5 | 11 | 0.34375 | 0.6842 |
| 6 | 21 | 0.328125 | 0.6840 |
| 8 | 85 | 0.332031 | 0.6839 |

The best estimate converges toward $1/3$ as $t$ grows, and the probability of
hitting it stays around $0.684$ rather than decaying.

### The guarantee

The standard result is that phase estimation returns the closest $t$-bit
approximation with probability at least

$$P \;\ge\; \frac{4}{\pi^2} \;\approx\; 0.4053$$

no matter what $\varphi$ is. Verified probability of landing within $1/2^t$ of
the true phase:

| $t$ | $\varphi$ | $P(|\hat\varphi - \varphi| \le 2^{-t})$ |
|---|---|---|
| 3 | $1/3$ | 0.8628 |
| 6 | $1/3$ | 0.8550 |
| 8 | $1/3$ | 0.8549 |
| 6 | $0.7$ | 0.9299 |
| 8 | $0.21$ | 0.9065 |

Every row comfortably exceeds the $4/\pi^2$ bound. The bound is a **worst
case**; typical phases do much better, and you can push the success probability
arbitrarily close to 1 by adding a few extra estimation qubits and rounding.

### The cost

$t$ estimation qubits give $t$ bits of precision and require $2^t - 1$
controlled applications of $U$ in total (since
$\sum_{k=0}^{t-1}2^k = 2^t - 1$). The QFT contributes $O(t^2)$ gates. So the
precision is exponential in the qubit count while the gate count is
polynomial — that is the source of the speed-ups in the algorithms built on
top of this.

## Limits and caveats

### You need an eigenstate

Phase estimation returns the phase of whichever eigenstate you supply. If you
prepare a superposition $\sum_i c_i |\psi_i\rangle$, you get a superposition of
outcomes and measuring samples $\varphi_i$ with probability $|c_i|^2$. That is
sometimes exactly what you want, and sometimes a problem.

### Exact powers of $U$ must be available

The circuit needs controlled-$U^{2^k}$. For large $k$ that is $2^k$
repetitions of $U$, which is why the total is $O(2^t)$. Any error per
application compounds, so circuit depth — not just the algorithmic scaling —
is usually the binding constraint.

### Precision is bounded by the register

$t$ qubits resolve $\varphi$ to about $2^{-t}$. More precision means more
qubits, and the last bits are the ones most easily destroyed by noise.

### The output is an estimate, not a proof

Even at $P \ge 4/\pi^2$, a single run can return a wrong value. Practical uses
repeat the circuit or verify the answer classically — Shor's algorithm does
exactly that, checking whether the recovered order actually works.

## Practical example

### Building the circuit

```python
import numpy as np

H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)


def cp(lam):
    """Controlled-phase diag(1, 1, 1, e^{i lam}); control is more significant."""
    return np.diag([1, 1, 1, np.exp(1j * lam)]).astype(complex)


def expand(U, n, targets, controls=()):
    """Lift a small unitary onto an n-qubit register (qubit 0 = MSB)."""
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


def swap_mat(a, b, n):
    M = np.zeros((1 << n, 1 << n), dtype=complex)
    for col in range(1 << n):
        ba, bb = (col >> (n - 1 - a)) & 1, (col >> (n - 1 - b)) & 1
        r = (col & ~(1 << (n - 1 - a))) | (bb << (n - 1 - a))
        r = (r & ~(1 << (n - 1 - b))) | (ba << (n - 1 - b))
        M[r, col] = 1
    return M
```

### Running phase estimation

```python
def qpe_matrix(t, phi):
    """t estimation qubits (qubit 0 = MSB) + eigenstate qubit at index t."""
    n = t + 1

    def controlled(target_q, control_q, U):
        C = np.zeros((1 << n, 1 << n), dtype=complex)
        for col in range(1 << n):
            if (col >> (n - 1 - control_q)) & 1:
                bit = (col >> (n - 1 - target_q)) & 1
                for b2 in (0, 1):
                    a = U[b2, bit]
                    if a:
                        C[(col & ~(1 << (n - 1 - target_q)))
                          | (b2 << (n - 1 - target_q)), col] += a
            else:
                C[col, col] = 1
        return C

    M = np.eye(1 << n, dtype=complex)
    for i in range(t):                                  # 1. Hadamards
        M = expand(H, n, [i]) @ M
    for q in range(t):                                  # 2. phase kickback
        # qubit 0 is the MSB, so qubit q carries weight 2^(t-1-q)
        power = 2 ** (t - 1 - q)
        U2k = np.diag([1, np.exp(2j * np.pi * phi * power)]).astype(complex)
        M = controlled(t, q, U2k) @ M
    for i in range(t // 2):                             # 3a. swaps
        M = swap_mat(i, t - 1 - i, n) @ M
    for i in range(t - 1, -1, -1):                      # 3b. inverse QFT
        for j in range(t - 1, i, -1):
            M = expand(cp(-2 * np.pi / 2 ** (j - i + 1)), n, [j, i], []) @ M
        M = expand(H, n, [i]) @ M
    return M


```

### Reading the results

```python
def qpe_distribution(t, phi):
    n = t + 1
    psi = np.zeros(1 << n, dtype=complex)
    psi[1] = 1                       # eigenstate qubit = |1>
    out = qpe_matrix(t, phi) @ psi
    p = np.abs(out) ** 2
    dist = {}
    for idx in range(1 << n):
        dist[idx >> 1] = dist.get(idx >> 1, 0) + p[idx]
    return dist


print("exact phases come out with certainty:")
for t, phi in ((3, 5 / 8), (4, 5 / 8)):
    d = qpe_distribution(t, phi)
    best = max(d, key=d.get)
    print(f"  t={t} phi={phi}: j={best}  j/2^t={best / 2 ** t}  P={d[best]:.4f}")

print("\nphases that are not dyadic rationals:")
for t in (3, 5, 8):
    d = qpe_distribution(t, 1 / 3)
    best = max(d, key=d.get)
    print(f"  t={t}: j={best}  j/2^t={best / 2 ** t:.6f}  P(best)={d[best]:.4f}")

print(f"\nguaranteed lower bound 4/pi^2 = {4 / np.pi ** 2:.4f}")
for t, phi in ((3, 1 / 3), (8, 1 / 3), (8, 0.21)):
    d = qpe_distribution(t, phi)
    prob = sum(v for k, v in d.items()
               if abs(k / 2 ** t - phi) <= 1 / 2 ** t + 1e-12)
    print(f"  t={t} phi={phi:.4f}: P(within 2^-t) = {prob:.4f}")
```

Running the blocks in order prints $P = 1.0000$ for $\varphi = 5/8$, the
converging estimates for $1/3$, and the within-tolerance probabilities that all
exceed $4/\pi^2$.

## Common misconceptions

- **"Phase estimation measures the target register."** It measures the
  *estimation* register. The target is left unchanged because it is an
  eigenstate.
- **"It works for any input state."** It returns the phase of an eigenstate.
  Give it a superposition and you sample from the eigenvalue distribution.
- **"More qubits make it more accurate, always."** More qubits give more
  *bits*, but each extra bit is more exposed to noise, and the total number of
  $U$ applications grows as $2^t$.
- **"The final QFT is a forward QFT."** It must be the **inverse** QFT.
- **"The success probability is $4/\pi^2$."** That is a worst-case *lower
  bound*. Typical phases do substantially better, and the observed values above
  are around $0.85$.

## Exercises

1. Explain in one sentence why the target register is unchanged by phase
   kickback.
2. For $t = 5$, what integer do you expect if $\varphi = 3/8$? What is the
   probability?
3. Why does estimation qubit $q$ control $U^{2^{t-1-q}}$ rather than $U^{2^q}$
   when qubit 0 is the most significant bit?
4. What happens if you apply a forward QFT instead of the inverse at the end?
5. You need $\varphi$ to 10 bits with success probability at least 0.99.
   Outline how to achieve that.
6. Total controlled-$U$ applications for $t = 10$: compute the sum and explain
   why it is $2^t - 1$.

## Summary

- Phase estimation recovers $\varphi$ where $U|\psi\rangle = e^{2\pi i\varphi}|\psi\rangle$, using **phase kickback** onto a control register.
- The circuit is: Hadamards on the estimation register, controlled-$U^{2^k}$
  for each binary weight, then the **inverse QFT**.
- With qubit 0 as the most significant bit, estimation qubit $q$ must control
  $U^{2^{t-1-q}}$ — reversing this silently yields bit-reversed answers.
- If $\varphi$ is exactly $m/2^t$, the circuit returns $m$ with probability
  **1**. Verified for $5/8$ at $t = 3$ and $t = 4$.
- Otherwise the best estimate is returned with probability at least
  $4/\pi^2 \approx 0.405$; measured values for $1/3$ are about $0.684$, and the
  probability of landing within $2^{-t}$ is about $0.855$.
- Cost: $t$ bits needs $2^t - 1$ controlled applications of $U$ plus $O(t^2)$
  QFT gates.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  §5.2 — phase estimation and the $4/\pi^2$ bound.
- Cleve, R., Ekert, A., Macchiavello, C. & Mosca, M. (1998), "Quantum algorithms
  revisited" — the precision and success-probability analysis.
- The [Quantum Fourier Transform](31_qft.md) lesson — the final stage of this
  circuit.
- The [Shor's Algorithm](33_shors_algorithm.md) lesson — phase estimation
  applied to order finding.

---

**Previous:** [Quantum Fourier Transform](31_qft.md) · **Next:** [Shor's Algorithm](33_shors_algorithm.md)
