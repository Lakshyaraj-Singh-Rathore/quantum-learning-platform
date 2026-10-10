# Classical Optimization Loops and the Parameter-Shift Rule

A variational quantum algorithm is a loop: a classical optimiser proposes
parameters, a quantum processor evaluates the cost, and the optimiser updates.
The quantum part gets the attention, but the classical part decides whether the
whole thing converges. This lesson covers the loop, how to get an **exact**
gradient out of a quantum circuit, and how to choose an optimiser when every
evaluation is noisy.

## Learning objectives

By the end of this lesson you should be able to:

- **Describe** the classical optimisation loop around a parameterised circuit.
- **Apply** the parameter-shift rule to obtain an analytic gradient, and explain
  why it is exact where finite differences are not.
- **Compare** gradient-based and gradient-free optimisers for noisy objectives,
  and state when each is appropriate.

## Prerequisites

This lesson assumes [parameterised circuits and ansatz
construction](07_vqe_qaoa.md) — you have a circuit $U(\theta)$ and a cost built
from expectation values.

## The loop

### Structure

1. **Initialise** parameters $\theta$.
2. **Evaluate** the cost $C(\theta)$ by preparing $U(\theta)|\psi_0\rangle$ and
   estimating the required expectation values on the processor.
3. **Update** $\theta$ using a classical optimiser.
4. **Repeat** until the cost stops improving, or a budget runs out.

The critical difference from ordinary numerical optimisation: **each cost
evaluation is a stochastic estimate**. You do not get $C(\theta)$, you get
$C(\theta)$ plus shot noise. And each evaluation costs real time on scarce
hardware.

### The cost function

Typically the cost is a sum of Pauli expectation values:

$$C(\theta) = \sum_j c_j \,\langle\psi(\theta)|P_j|\psi(\theta)\rangle$$

Each term is estimated from a finite number of shots, so the whole cost carries
sampling error. Reducing that error costs more shots, and shots are the currency
the loop spends.

## The parameter-shift rule

### The problem

Gradient-based optimisers converge far faster than gradient-free ones, but they
need a gradient. You cannot backpropagate through a quantum processor. And
finite differences are a poor substitute here: they are approximate, sensitive
to the step size, and each evaluation is noisy anyway.

### The result

For a circuit containing a gate $e^{-i\theta G/2}$ whose generator $G$ has
eigenvalues $\pm 1$ — which covers $R_x$, $R_y$, $R_z$ and all their controlled
variants — the derivative is exactly

$$\frac{\partial \langle O\rangle}{\partial\theta} = \frac{\langle O\rangle(\theta + \tfrac{\pi}{2}) - \langle O\rangle(\theta - \tfrac{\pi}{2})}{2}$$

Two circuit evaluations, and the answer is **exact** — not an approximation.

### Why it is exact

The expectation value as a function of $\theta$ is a sinusoid: for a generator
with eigenvalues $\pm1$ the dependence is $a\cos(\theta + b) + c$. Sampling that
sinusoid at $\theta \pm \pi/2$ and taking half the difference recovers the
derivative identically, because a shifted sine is an exact derivative formula
for this functional form. No step size appears, so no step-size error exists.

### Verified against the analytic derivative

For a single-qubit circuit $R_y(\theta)|0\rangle$ with cost
$\langle Z\rangle = \cos\theta$, the exact derivative is $-\sin\theta$:

| $\theta$ | Parameter-shift | Analytic | Difference |
|---|---|---|---|
| 0.0 | 0.0000000000 | 0.0000000000 | $0$ |
| 0.3 | $-0.2955202067$ | $-0.2955202067$ | $5.6\times10^{-17}$ |
| 0.7 | $-0.6442176872$ | $-0.6442176872$ | $1.1\times10^{-16}$ |
| 1.2 | $-0.9320390860$ | $-0.9320390860$ | $2.2\times10^{-16}$ |
| 2.0 | $-0.9092974268$ | $-0.9092974268$ | $0$ |

The agreement is at machine precision — the rule is exact, not a good
approximation.

### Compared with finite differences

The same derivative by central finite differences, at $\theta = 0.7$:

| Step $h$ | FD estimate | Absolute error |
|---|---|---|
| $10^{-1}$ | $-0.643144527813$ | $1.07\times10^{-3}$ |
| $10^{-2}$ | $-0.644206950330$ | $1.07\times10^{-5}$ |
| $10^{-4}$ | $-0.644217686164$ | $1.07\times10^{-9}$ |
| $10^{-5}$ | $-0.644217687218$ | $1.98\times10^{-11}$ |
| $10^{-7}$ | $-0.644217686419$ | $8.19\times10^{-10}$ |
| $10^{-10}$ | $-0.644218012269$ | $3.25\times10^{-7}$ |
| $10^{-12}$ | $-0.644206910039$ | $1.08\times10^{-5}$ |

The error falls as $h^2$ down to about $h = 10^{-5}$, then **rises again** as
floating-point roundoff takes over. The best finite differences can do here is
about $10^{-11}$; the parameter-shift rule achieves $10^{-16}$.

That U-shaped curve is the practical argument. In simulation you can pick a
sensible $h$, but on hardware the evaluation noise swamps the difference between
two nearby parameter values entirely, and finite differences become useless. The
parameter-shift rule evaluates at $\pm\pi/2$ — points far enough apart that the
difference stands clear of the noise.

### Cost in circuit evaluations

| Method | Evaluations per gradient | Exact? |
|---|---|---|
| Parameter-shift | $2p$ for $p$ parameters | yes |
| Finite differences | $2p$ | no |
| SPSA | 2, independent of $p$ | no (stochastic) |

For 1000 parameters, parameter-shift costs 2000 evaluations per gradient step
against SPSA's 2 — which is exactly why SPSA and other stochastic methods are
used at scale despite being noisier.

## Choosing an optimiser

### The noise changes everything

Standard gradient descent assumes you can evaluate the cost and its gradient
accurately. Here every evaluation is an average over $N$ shots, with error
falling only as $1/\sqrt{N}$. A gradient-based method that works on a clean
simulator can be led badly astray on hardware.

### Gradient-based methods

**Gradient descent** and its variants (Adam, L-BFGS) use the parameter-shift
gradient. They converge in few iterations but need an accurate gradient, and
each gradient costs $2p$ evaluations.

Verified on the toy cost $\langle Z\rangle = \cos\theta$ starting from
$\theta = 0.4$ with learning rate 0.3, the exact gradient drives the cost from
$0.87$ to $-0.97$ over 12 iterations — converging toward the true minimum of
$-1$ at $\theta = \pi$.

**Best when:** evaluations are cheap enough or accurate enough that the gradient
signal exceeds the noise; you have few parameters; you are working in
simulation.

### Gradient-free methods

**Nelder-Mead** and **COBYLA** use only cost values. They are robust to noise
and need no gradient evaluations, but scale badly with parameter count —
typically requiring many more evaluations.

**SPSA** (simultaneous perturbation stochastic approximation) estimates a
gradient from just **two** evaluations per step by perturbing all parameters at
once with a random vector. It is explicitly designed for noisy objectives and
costs the same regardless of parameter count.

**Best when:** the objective is noisy, parameters are many, or evaluations are
expensive.

### The comparison table

| Optimiser | Uses gradient | Evaluations per step | Noise tolerance | Scales to many parameters |
|---|---|---|---|---|
| Gradient descent / Adam | yes | $2p$ | low | poor |
| L-BFGS | yes | $2p$ | low | moderate |
| Nelder-Mead | no | $\sim p$ | moderate | poor |
| COBYLA | no | $\sim 1$ | moderate | moderate |
| SPSA | stochastic | 2 | high | good |

### Practical guidance

- **Start in simulation** with a gradient-based method to check the ansatz is
  expressive enough. If it cannot converge without noise, it will not converge
  with noise.
- **Move to SPSA or COBYLA on hardware**, where shot noise dominates.
- **Budget shots deliberately.** More shots per evaluation means a cleaner
  signal but fewer iterations for the same wall-clock time. There is an optimum,
  and it is usually at a modest shot count.
- **Watch for barren plateaus.** If gradients vanish, no optimiser will help —
  see the discussion in [VQE and QAOA](07_vqe_qaoa.md).

## Practical example

### The parameter-shift rule, verified

```python
import numpy as np

Z = np.array([[1, 0], [0, -1]], dtype=complex)


def ry(t):
    c, s = np.cos(t / 2), np.sin(t / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def expectation(theta):
    """<Z> for Ry(theta)|0>  --  equals cos(theta)."""
    psi = ry(theta) @ np.array([1, 0], dtype=complex)
    return np.vdot(psi, Z @ psi).real


def parameter_shift(theta):
    return (expectation(theta + np.pi / 2)
            - expectation(theta - np.pi / 2)) / 2


def analytic(theta):
    return -np.sin(theta)


print("theta   parameter-shift      analytic        difference")
for th in (0.0, 0.3, 0.7, 1.2, 2.0):
    ps, an = parameter_shift(th), analytic(th)
    print(f"{th:5.2f}   {ps:16.10f}   {an:14.10f}   {abs(ps - an):.2e}")
```

### Finite differences and the optimiser

```python
print("\nfinite differences: error falls as h^2, then roundoff takes over")
th = 0.7
print("   h           FD estimate          abs error")
for h in (1e-1, 1e-2, 1e-4, 1e-5, 1e-7, 1e-10, 1e-12):
    fd = (expectation(th + h) - expectation(th - h)) / (2 * h)
    print(f"{h:8.0e}   {fd:20.12f}   {abs(fd - analytic(th)):.2e}")

print("\ngradient descent with the exact parameter-shift gradient:")
theta, lr = 0.4, 0.3
for i in range(12):
    theta -= lr * parameter_shift(theta)
    if i % 3 == 0 or i == 11:
        print(f"  iter {i:2d}: theta={theta:.6f}   cost={expectation(theta):.6f}")

print("\nevaluations per gradient:")
for p in (1, 10, 100, 1000):
    print(f"  p={p:5d}:  parameter-shift {2 * p:6d}   SPSA 2")
```

Running the blocks in order confirms machine-precision agreement between the
parameter-shift rule and the analytic derivative, shows the U-shaped
finite-difference error curve, and demonstrates convergence of gradient descent.

## Common misconceptions

- **"The parameter-shift rule is a finite difference with a big step."** No — it
  is **exact** for gates whose generators have eigenvalues $\pm 1$. A finite
  difference is never exact, however small the step.
- **"Smaller finite-difference steps are always better."** Below about $h = 10^{-5}$ here, roundoff dominates and the error grows again.
- **"Gradients are always worth it."** Each gradient costs $2p$ evaluations. At
  large $p$, SPSA's 2 evaluations may be the better trade.
- **"The optimiser will fix a bad ansatz."** It cannot. If the ansatz cannot
  express a good solution, or gradients have vanished into a barren plateau, no
  optimiser helps.
- **"More shots is always better."** More shots means fewer iterations within a
  fixed budget. There is an optimum.

## Exercises

1. Verify the parameter-shift rule for $R_z$ and for a controlled-$R_y$ gate.
2. Why does the rule require the generator to have eigenvalues $\pm 1$? What
   changes for a generator with eigenvalues $\pm 1/2$?
3. At what step size does your finite-difference error stop improving? Explain
   why.
4. For 500 parameters, compare the evaluation cost of one gradient step using
   parameter-shift versus SPSA.
5. Explain why shot noise makes gradient-based optimisers unreliable on
   hardware.
6. You have a fixed budget of 100,000 circuit evaluations. How would you divide
   it between shots per evaluation and optimiser iterations?

## Summary

- The variational loop alternates a **quantum evaluation** with a **classical
  update**, and every evaluation is a noisy finite-shot estimate.
- The **parameter-shift rule** gives an exact gradient from two evaluations:
  $\partial_\theta\langle O\rangle = [\langle O\rangle(\theta+\pi/2) - \langle O\rangle(\theta-\pi/2)]/2$.
- Verified to machine precision ($\sim10^{-16}$) against the analytic
  derivative; finite differences bottom out near $10^{-11}$ and get worse as
  the step shrinks further.
- Cost: parameter-shift needs $2p$ evaluations for $p$ parameters; SPSA needs 2
  regardless.
- **Gradient-based** methods converge in few steps but need clean gradients.
  **Gradient-free** and **stochastic** methods tolerate noise and scale better.
- Choose in simulation first to validate the ansatz; move to noise-tolerant
  methods on hardware.

## References

- Mitarai, K., Negoro, M., Kitagawa, M. & Fujii, K. (2018), "Quantum circuit
  learning" — the parameter-shift rule.
- Schuld, M. et al. (2019), "Evaluating analytic gradients on quantum hardware".
- Spall, J. C. (1992) — SPSA, the noise-tolerant stochastic optimiser.
- The [VQE and QAOA](07_vqe_qaoa.md) lesson — the ansatz and cost being
  optimised, and the barren-plateau caveat.

---

**Previous:** [Quantum Cryptography](68_quantum_cryptography.md)
