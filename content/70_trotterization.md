# Trotterization

[Quantum simulation](69_quantum_simulation.md) gives us a Hamiltonian as a sum
of Pauli strings. What it does not give us is a circuit. The Hamiltonian
evolution $e^{-iHt}$ is not something a gate-based computer executes directly —
it has to be **compiled into gates**. Trotterization is the simplest and most
widely used way to do that, and its central trade-off — accuracy against
circuit depth — is the defining constraint of near-term quantum simulation.

## Learning objectives

By the end of this lesson you should be able to:

- **Apply** the first-order Trotter formula.
- **Bound** the Trotter error in terms of the time step.
- **Trade off** step size against circuit depth.

## Prerequisites

[Quantum Simulation and Many-Body Systems](69_quantum_simulation.md) (required)
— Trotterization is how a simulated Hamiltonian evolution is broken into gates.

## The problem

Given $H = \sum_k c_k P_k$ in Pauli-string form, we want to implement the
evolution operator

$$U(t) = e^{-iHt} = e^{-i(c_1 P_1 + c_2 P_2 + \cdots)t}$$

as a circuit. Each individual term is easy: $e^{-i c_k P_k \theta}$ has a
standard circuit, because $P_k$ is a tensor product of Paulis. The difficulty is
entirely in the **sum inside the exponential**.

## Why the naive split fails

If the terms commuted, everything would be easy:

$$e^{-i(A+B)t} = e^{-iAt}\,e^{-iBt} \quad \text{only when } [A,B] = 0.$$

They generally do not commute, and the splitting is then an approximation.
Verified numerically for two overlapping terms of a 4-qubit Ising model at
$t = 1$:

$$\big\lVert [H_a, H_b] \big\rVert_2 = 1.0, \qquad \big\lVert e^{-i(A+B)t} - e^{-iAt}e^{-iBt} \big\rVert = 0.434645 .$$

That is a large error — 43% — from a single split.

The contrast is instructive: two terms acting on **disjoint qubits** do commute,
and they split **exactly**. Measured: $\lVert[A,B]\rVert = 0$ and a splitting
error of $2.8 \times 10^{-16}$, i.e. zero to machine precision.

This is not a curiosity. It is the basis of real implementation practice:
**group commuting terms together**, since they can be applied in parallel with
no Trotter error between them, and the error comes only from the genuinely
non-commuting remainder.

## The first-order Trotter formula

Objective 1.

The **Lie–Trotter product formula** splits the evolution into $r$ short steps of
duration $\Delta t = t/r$, and within each step applies every term separately:

$$e^{-iHt} \;\approx\; \Big(\prod_k e^{-i c_k P_k \Delta t}\Big)^{r}, \qquad \Delta t = \frac{t}{r}.$$

Read it inside-out: for one step, apply $e^{-i c_1 P_1 \Delta t}$, then
$e^{-i c_2 P_2 \Delta t}$, and so on through every term. Then repeat the whole
sequence $r$ times.

The intuition is that for a **short** time $\Delta t$, the non-commuting parts
have little room to disagree, so the split is nearly right. Repeating $r$ times
accumulates the full evolution, at the cost of accumulating a small error each
time.

### Worked example

Take the 4-qubit transverse-field Ising model

$$H = -J(Z_0Z_1 + Z_1Z_2 + Z_2Z_3) - h(X_0 + X_1 + X_2 + X_3)$$

with $J = 1$, $h = 0.5$. One Trotter step of size $\Delta t$ applies, in
sequence:

$$e^{iJ Z_0Z_1 \Delta t},\; e^{iJ Z_1Z_2 \Delta t},\; e^{iJ Z_2Z_3 \Delta t},\; e^{i h X_0 \Delta t},\; \ldots,\; e^{i h X_3 \Delta t}$$

The $ZZ$ terms are two CNOTs and an $R_Z$ rotation each; the $X$ terms are
single-qubit $R_X$ rotations. All of them are elementary gates.

## Bounding the error

Objective 2.

### The commutator bound

The standard first-order bound is

$$\big\lVert U_\text{exact} - U_\text{Trotter} \big\rVert \;\leq\; \frac{t^2}{2r} \sum_{j < k} \big\lVert [H_j, H_k] \big\rVert,$$

where $H_j = c_j P_j$. Every part of this is informative:

- **$1/r$** — double the steps, halve the error. First order.
- **$t^2$** — simulating for twice as long costs four times the error, at fixed
  step size.
- **$\sum_{j<k}\lVert[H_j,H_k]\rVert$** — the error is driven by how much the
  terms *fail to commute*. A Hamiltonian whose terms all commute has **zero**
  Trotter error, no matter how large $\Delta t$ is.

### Verified: the bound holds, and it is loose

For the 4-qubit TFIM at $t = 1$, the commutator sum is $S = 6.0$:

| $r$ | Bound $\frac{t^2}{2r}S$ | Actual error | Ratio |
|---|---|---|---|
| 4 | $7.50 \times 10^{-1}$ | $2.904 \times 10^{-1}$ | 2.58× |
| 8 | $3.75 \times 10^{-1}$ | $1.440 \times 10^{-1}$ | 2.60× |
| 16 | $1.875 \times 10^{-1}$ | $7.187 \times 10^{-2}$ | 2.61× |
| 32 | $9.375 \times 10^{-2}$ | $3.591 \times 10^{-2}$ | 2.61× |
| 64 | $4.688 \times 10^{-2}$ | $1.796 \times 10^{-2}$ | 2.61× |
| 128 | $2.344 \times 10^{-2}$ | $8.977 \times 10^{-3}$ | 2.61× |

The bound is satisfied at every $r$, and it overestimates the true error by a
steady factor of about $2.6$. That is expected and worth stating plainly: the
commutator bound is a **guarantee**, not an estimate. It tells you the worst
case. Real errors are typically smaller — sometimes much smaller, since the
bound ignores cancellation between terms.

Use the bound to *size* a simulation; use numerics to *tune* it.

### Verified: the scaling is exactly as claimed

The clean way to confirm the $O(\Delta t)$ behaviour is to multiply the measured
error by $r$. If the error is $O(t^2/r)$, then error $\times$ $r$ should be
constant:

| $r$ | $\Delta t$ | Error | Error $\times\ r$ |
|---|---|---|---|
| 1 | 1.00000 | $1.391$ | 1.3907 |
| 2 | 0.50000 | $6.004 \times 10^{-1}$ | 1.2009 |
| 4 | 0.25000 | $2.904 \times 10^{-1}$ | 1.1615 |
| 8 | 0.12500 | $1.440 \times 10^{-1}$ | 1.1522 |
| 16 | 0.06250 | $7.187 \times 10^{-2}$ | 1.1498 |
| 32 | 0.03125 | $3.591 \times 10^{-2}$ | 1.1493 |
| 64 | 0.01562 | $1.796 \times 10^{-2}$ | 1.1491 |
| 128 | 0.00781 | $8.977 \times 10^{-3}$ | 1.1491 |
| 256 | 0.00391 | $4.489 \times 10^{-3}$ | 1.1491 |

The product locks onto **1.1491**. First-order convergence, cleanly confirmed.

### Second order: a cheap improvement

The **second-order Strang splitting** applies the terms forwards, then backwards,
each for half a step:

$$U_2(\Delta t) = \Big(\prod_k e^{-i c_k P_k \Delta t/2}\Big) \Big(\prod_k^{\text{rev}} e^{-i c_k P_k \Delta t/2}\Big)$$

The symmetric arrangement cancels the leading error term, giving error
$O(\Delta t^2)$ for barely more work. Verified — this time error $\times r^2$
should be constant:

| $r$ | $\Delta t$ | Error | Error $\times\ r^2$ |
|---|---|---|---|
| 1 | 1.00000 | $6.743 \times 10^{-1}$ | 0.6743 |
| 4 | 0.25000 | $2.975 \times 10^{-2}$ | 0.4760 |
| 8 | 0.12500 | $7.331 \times 10^{-3}$ | 0.4692 |
| 16 | 0.06250 | $1.826 \times 10^{-3}$ | 0.4675 |
| 32 | 0.03125 | $4.561 \times 10^{-4}$ | 0.4671 |
| 64 | 0.01562 | $1.140 \times 10^{-4}$ | 0.4670 |
| 128 | 0.00781 | $2.850 \times 10^{-5}$ | 0.4669 |

Again it locks on, at **0.4669**. Note the practical payoff: at $r = 32$,
second order gives error $4.6 \times 10^{-4}$ where first order gives
$3.6 \times 10^{-2}$ — roughly **78× better for about twice the gates**.

Higher-order Suzuki formulas push this further, but each order needs more
exponentials per step, and on noisy hardware the extra gates usually cost more
than the accuracy is worth. Second order is the common practical choice.

## Trading step size against circuit depth

Objective 3, and the reason this lesson matters in practice.

Smaller $\Delta t$ reduces Trotter error. But $\Delta t = t/r$, so smaller
$\Delta t$ means **more steps**, and more steps means a **deeper circuit** —
which on real hardware accumulates **gate error**.

These pull in opposite directions, and the total error is roughly

$$\varepsilon_\text{total} \;\approx\; \underbrace{C\,\frac{t^2}{r}}_{\text{Trotter}} \;+\; \underbrace{G\,r\,\varepsilon_\text{gate}}_{\text{noise}}$$

where $G$ is the gate count per step and $\varepsilon_\text{gate}$ the error per
gate. The first term **falls** with $r$; the second **grows**. The sum has a
**minimum**.

### Verified: there is an optimal step size

For the 4-qubit TFIM at $t = 1$, with 13 gates per step and a per-gate error of
$10^{-4}$:

| $r$ | Trotter error | Gate error | Total | Depth (gates) |
|---|---|---|---|---|
| 4 | $2.904 \times 10^{-1}$ | $5.2 \times 10^{-3}$ | $2.956 \times 10^{-1}$ | 52 |
| 16 | $7.187 \times 10^{-2}$ | $2.08 \times 10^{-2}$ | $9.267 \times 10^{-2}$ | 208 |
| **32** | $3.591 \times 10^{-2}$ | $4.16 \times 10^{-2}$ | $\mathbf{7.751 \times 10^{-2}}$ | **416** |
| 64 | $1.796 \times 10^{-2}$ | $8.32 \times 10^{-2}$ | $1.012 \times 10^{-1}$ | 832 |
| 128 | $8.977 \times 10^{-3}$ | $1.664 \times 10^{-1}$ | $1.754 \times 10^{-1}$ | 1664 |
| 512 | $2.244 \times 10^{-3}$ | $6.656 \times 10^{-1}$ | $6.678 \times 10^{-1}$ | 6656 |

**The optimum is at $r = 32$.** Below it, Trotter error dominates and more steps
help. Above it, gate error dominates and more steps actively hurt — by
$r = 512$ the "more accurate" simulation is nearly **nine times worse**.

This is the single most important practical lesson here: **on a noisy device,
there is a best step size, and refining past it makes the answer worse.** The
temptation to drive Trotter error toward zero is a trap.

The optimum moves with hardware quality. Halve $\varepsilon_\text{gate}$ and the
optimal $r$ rises, letting you afford a smaller $\Delta t$. This is why
Trotterization is considered a [NISQ-era](62_nisq_limitations.md) technique:
the error does not vanish asymptotically, it bottoms out at a floor set by the
hardware.

### What replaces it

Fault-tolerant machines use fundamentally better algorithms — notably
**quantum signal processing** and **qubitization** — whose cost scales like
$t \cdot \lVert H\rVert / \varepsilon$ with only **logarithmic** dependence on
$1/\varepsilon$, versus Trotter's polynomial $1/\varepsilon$. They require far
deeper coherent circuits, which is why they are not usable yet.

The comparison:

| Method | Error scaling | Circuit depth | Usable now? |
|---|---|---|---|
| First-order Trotter | $O(\Delta t)$ | Shallow | Yes |
| Second-order Trotter | $O(\Delta t^2)$ | Shallow | Yes |
| Higher-order Suzuki | $O(\Delta t^k)$ | Deeper | Rarely |
| QSP / qubitization | $\log(1/\varepsilon)$ | Deep | Needs fault tolerance |

### Implementation notes

Three things that matter in practice:

**Order the terms well.** Group commuting terms so they can be applied in
parallel. Since disjoint terms commute exactly, a good grouping reduces both the
error and the depth.

**Exploit the structure of the hardware.** Terms acting on qubits that are far
apart on a device require [SWAPs or routing](42_compilation.md), and those
extra gates cost more than the Trotter error you are trying to reduce.

**Validate against something known.** Trotter error is systematic, not random.
Run at two different step sizes and check that the result moves the way the
$O(\Delta t)$ or $O(\Delta t^2)$ scaling predicts. If it does not, your
implementation has a bug, not a convergence problem. On a small system,
compare against exact diagonalisation as done above.

## Common misconceptions

- **"Trotter error is like sampling noise, so more shots fix it."** It is a
  **systematic** error — a wrong unitary, not a noisy estimate. Averaging more
  shots converges to the wrong answer.
- **"Smaller steps are always more accurate."** Only on a noise-free device.
  On real hardware the total error has a **minimum**, and refining past it is
  worse. Verified: $r = 512$ is nine times worse than $r = 32$ here.
- **"The commutator bound tells me the actual error."** It is an **upper
  bound**; measured error was consistently about 2.6× smaller.
- **"If terms commute, Trotterization still costs something."** No — the error
  is exactly zero. Verified to $2.8 \times 10^{-16}$ for disjoint terms.
- **"Second order costs twice as much and helps a little."** It costs about
  twice the gates and helped by a factor of **78** at $r = 32$ here. It is
  usually worth it.
- **"Trotterization is how fault-tolerant machines will simulate."** It is the
  near-term method. Fault-tolerant machines will use QSP or qubitization, whose
  dependence on the target error is exponentially better.

## Exercises

1. Write the first-order Trotter step for $H = Z_0Z_1 + X_0 + X_1$ with step
   size $\Delta t$.

2. You halve the step size. By what factor does the first-order Trotter error
   fall? By what factor does the second-order error fall?

3. Using the bound with commutator sum $S = 6$, what is the guaranteed error
   for $t = 2$ and $r = 50$?

4. Why is there an optimal number of Trotter steps on a real device?

5. Two terms act on completely disjoint sets of qubits. What is the Trotter
   error from splitting them, and why?

6. You double the simulation time $t$ while keeping $\Delta t$ fixed. What
   happens to the error and to the circuit depth?

### Answers to 1–3

**1.** One step applies each term in turn:

$$e^{-i Z_0Z_1 \Delta t}\; e^{-i X_0 \Delta t}\; e^{-i X_1 \Delta t}$$

In gates: the $Z_0Z_1$ term is CNOT, $R_Z$, CNOT; the $X$ terms are $R_X$
rotations. Repeat $r = t/\Delta t$ times. Note that $Z_0Z_1$ and $X_0$ do **not**
commute, so the order matters and this is genuinely an approximation.

**2.** **First order: 2×.** Error is $O(\Delta t)$, so halving $\Delta t$ halves
the error. **Second order: 4×.** Error is $O(\Delta t^2)$, so halving $\Delta t$
divides the error by four. Both are confirmed numerically above — the products
error $\times r$ and error $\times r^2$ were constant at 1.1491 and 0.4669.

**3.**

$$\varepsilon \leq \frac{t^2}{2r}S = \frac{4}{2 \times 50} \times 6 = \frac{24}{100} = 0.24 .$$

This is a **guarantee**, not a prediction. Based on the measurements above, the
actual error would likely be around 2.6× smaller, roughly $0.09$. Use the bound
for safety, numerics for tuning.

### Answers to 4–6

**4.** Because two errors trade against each other. Trotter error falls as
$1/r$, but each extra step adds gates, and gate error grows proportionally to
$r$. The total $\varepsilon \approx C t^2/r + G r \varepsilon_\text{gate}$ has a
minimum: **below it Trotter error dominates, above it noise dominates.** Verified
numerically — the optimum was $r = 32$, and $r = 512$ was nine times worse.

**5.** **Zero.** Disjoint terms act on different qubits and therefore commute,
and for commuting terms $e^{-i(A+B)t} = e^{-iAt}e^{-iBt}$ exactly. Verified: the
commutator norm was $0$ and the splitting error $2.8 \times 10^{-16}$. This is
why grouping commuting terms is worthwhile — it removes error at no cost.

**6.** **Error grows as $t^2$ and depth grows as $t$.** At fixed $\Delta t$,
doubling $t$ means doubling the number of steps $r = t/\Delta t$, so the depth
doubles. The bound $\varepsilon \leq \frac{t^2}{2r}S$ with $r = t/\Delta t$
becomes $\varepsilon \leq \frac{t \Delta t}{2}S$ — linear in $t$ at fixed step
size, but **quadratic in $t$** if you keep $r$ fixed instead. Long simulations
are expensive in a way that is easy to underestimate.

## Summary

- **The problem**: $e^{-iHt}$ must be compiled into gates, and $H = \sum_k c_k P_k$ has non-commuting terms, so the exponential does not factor.
- **First-order Trotter**: $e^{-iHt} \approx (\prod_k e^{-i c_k P_k \Delta t})^r$
  with $\Delta t = t/r$. Error $O(\Delta t)$ — verified, error $\times r$ is
  constant at 1.1491.
- **The commutator bound**, $\varepsilon \leq \frac{t^2}{2r}\sum_{j<k}\lVert [H_j,H_k]\rVert$, holds at every $r$ but overestimates by ~2.6×. It is a
  guarantee, not an estimate.
- **Second order** costs about twice the gates and, at $r = 32$, was **78× more
  accurate** here; error $\times r^2$ constant at 0.4669 confirms $O(\Delta t^2)$.
- **The trade-off is the point**: on real hardware total error $\approx C t^2/r + G r \varepsilon_\text{gate}$ has a **minimum**. Verified — optimum
  at $r = 32$, with $r = 512$ nine times worse. **Refining past the optimum
  makes the answer worse.**
- **Commuting terms split exactly** ($2.8 \times 10^{-16}$ error), so group them
  to reduce both cost and error.
- **Trotter error is systematic**, not sampling noise — more shots will not fix
  it, and better hardware moves the optimum rather than removing it.
- **Fault-tolerant machines** will use QSP or qubitization, with
  $\log(1/\varepsilon)$ dependence versus Trotter's polynomial.

## References

- Trotter, H. F., "On the product of semi-groups of operators," *Proceedings of
  the American Mathematical Society* **10**, 545 (1959).
- Suzuki, M., "Generalized Trotter's formula and systematic approximants of
  exponential operators," *Communications in Mathematical Physics* **51**, 183
  (1976) — higher-order formulas.
- Lloyd, S., "Universal Quantum Simulators," *Science* **273**, 1073 (1996).
- Berry, D. W., Childs, A. M., Cleve, R., Kothari, R. and Somma, R. D.,
  "Simulating Hamiltonian dynamics with a truncated Taylor series,"
  *Physical Review Letters* **114**, 090502 (2015) — beyond Trotter.
- Nielsen, M. A. and Chuang, I. L., *Quantum Computation and Quantum
  Information*, §4.7 — the product formulas and their error bounds.
- [Quantum Simulation and Many-Body Systems](69_quantum_simulation.md) —
  where the Hamiltonian comes from and what to measure.
- [NISQ Limitations](62_nisq_limitations.md) — why the gate-error floor
  dominates.
- [Compilation and Transpilation](42_compilation.md) — the routing and SWAP
  cost of non-local terms.
- [Quantum Phase Estimation](../algo/phase_estimation.md) — the
  fault-tolerant alternative for extracting energies.
