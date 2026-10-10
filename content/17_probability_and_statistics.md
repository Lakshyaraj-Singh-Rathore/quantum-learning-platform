# Probability, Expectation and Sampling Statistics

A quantum computer does not hand you the answer. It hands you a sample: you
run a circuit $N$ times, count the outcomes, and *estimate* probabilities from
the counts. That means every number a quantum computer reports carries an error
bar, and knowing how large that error bar is — and how many shots it takes to
shrink it — is a practical skill, not a theoretical nicety. This lesson covers
discrete probability, expectation and variance, and then derives the standard
error of an estimated probability, which is the formula behind every histogram
you will read in this course.

## Learning objectives

By the end of this lesson you should be able to:

- **Compute** the expectation and variance of a discrete probability
  distribution, including via $\operatorname{E}[X^2] - \operatorname{E}[X]^2$.
- **Derive** the standard error $\sigma = \sqrt{p(1-p)/N}$ of an estimated
  probability from $N$ shots.
- **Choose** a shot count large enough that a target effect exceeds its own
  error bar.
- **Interpret** a measurement histogram with its uncertainty, and state a 95%
  confidence interval for an estimated probability.
- **Explain** why increasing precision is expensive, and what the square-root
  scaling implies for run time.

## Discrete probability

### Formal definition

A **discrete probability distribution** assigns a probability $p_k \ge 0$ to
each outcome $x_k$ of a finite set, subject to

$$\sum_k p_k = 1$$

In quantum mechanics the probabilities come from the Born rule: for a state
$|\psi\rangle$ and an observable with eigenbasis $\{|k\rangle\}$, the
probability of outcome $k$ is

$$p_k = |\langle k | \psi \rangle|^2$$

The normalisation condition $\langle\psi|\psi\rangle = 1$ is exactly what
guarantees the $p_k$ sum to 1.

### Independence

Two events $A$ and $B$ are **independent** if

$$P(A \cap B) = P(A)\,P(B)$$

Sequential independent measurements factorise this way. Quantum measurements
are *not* generally independent of each other, because measuring collapses the
state — a point that surprises people who carry over the intuition from
flipping coins.

## Expectation and variance

### Definitions

The **expectation** (mean) of a discrete random variable $X$ is the
probability-weighted average:

$$\operatorname{E}[X] = \sum_k x_k \, p_k$$

The **variance** measures spread around the mean:

$$\operatorname{Var}(X) = \operatorname{E}\left[(X - \mu)^2\right] = \sum_k (x_k - \mu)^2 p_k, \qquad \mu = \operatorname{E}[X]$$

The **standard deviation** is $\sigma_X = \sqrt{\operatorname{Var}(X)}$, which
has the same units as $X$ and is therefore easier to interpret.

### The computational shortcut

Expanding the square gives a form that is usually faster by hand:

$$\operatorname{Var}(X) = \operatorname{E}[X^2] - \operatorname{E}[X]^2$$

### Worked example

Let $X$ take values $\{0, 1, 2\}$ with probabilities $\{\tfrac{1}{4}, \tfrac{1}{2}, \tfrac{1}{4}\}$.

$$\operatorname{E}[X] = 0 \cdot \tfrac{1}{4} + 1 \cdot \tfrac{1}{2} + 2 \cdot \tfrac{1}{4} = 1$$

$$\operatorname{E}[X^2] = 0^2 \cdot \tfrac{1}{4} + 1^2 \cdot \tfrac{1}{2} + 2^2 \cdot \tfrac{1}{4} = 0.5 + 1 = 1.5$$

$$\operatorname{Var}(X) = 1.5 - 1^2 = 0.5$$

Verifying directly: $\tfrac{1}{4}(0-1)^2 + \tfrac{1}{2}(1-1)^2 + \tfrac{1}{4}(2-1)^2 = 0.25 + 0 + 0.25 = 0.5$. Both routes agree.

## Estimating a probability from shots

### The Bernoulli model

Suppose the true probability of an outcome is $p$, and you run $N$
independent shots. Let $K$ be the number of times the outcome appears. Then $K$
follows a **binomial distribution**, and your estimate of the probability is

$$\hat{p} = \frac{K}{N}$$

The estimate $\hat{p}$ is a random variable: run the same circuit again and
you get a slightly different answer.

### Deriving the standard error

For a single shot, define an indicator variable $X_i$ that is 1 if the outcome
occurs and 0 otherwise. Then

$$\operatorname{E}[X_i] = p, \qquad \operatorname{Var}(X_i) = p(1-p)$$

Since $\hat{p} = \frac{1}{N}\sum_{i=1}^N X_i$ and the shots are independent,
variances add:

$$\operatorname{Var}(\hat{p}) = \frac{1}{N^2}\sum_{i=1}^N \operatorname{Var}(X_i) = \frac{1}{N^2} \cdot N p(1-p) = \frac{p(1-p)}{N}$$

Taking the square root gives the **standard error**:

$$\sigma_{\hat{p}} = \sqrt{\frac{p(1-p)}{N}}$$

This is the single most useful formula in practical quantum computing. Two
things follow immediately: the error shrinks as $1/\sqrt{N}$, and it is largest
at $p = 1/2$.

### Worked table at the worst case

At $p = 0.5$, where the error is maximal:

| Shots $N$ | $\sigma_{\hat{p}}$ | As a percentage | 95% CI half-width |
|---|---|---|---|
| 100 | 0.050000 | 5.00% | 9.80% |
| 1024 | 0.015625 | 1.56% | 3.06% |
| 4096 | 0.007812 | 0.78% | 1.53% |

The 95% half-width is $1.96\,\sigma$, using the normal approximation, which is
reasonable when both $Np$ and $N(1-p)$ exceed about 5.

### The cost of precision

Because the error scales as $1/\sqrt{N}$, **halving** the error requires
**four times** the shots. Going from 5% to 0.78% costs 40 times the run time.
This square-root law is the reason sampling-based algorithms are expensive to
push to high precision, and the reason quantum algorithms that concentrate
amplitude — rather than merely sampling — are valuable.

### Worked example: choosing a shot count

Suppose you must distinguish $p = 0.50$ from $p = 0.52$. The gap is 0.02. For
the error bar to be meaningfully smaller than the gap, require
$\sigma_{\hat{p}} \le 0.005$:

$$\sqrt{\frac{0.25}{N}} \le 0.005 \implies \frac{0.25}{N} \le 2.5 \times 10^{-5} \implies N \ge 10000$$

So resolving a two-point difference needs on the order of ten thousand shots
per setting. This is a real constraint on experiment design, not a footnote.

## Practical example

```python
import math
import numpy as np

# --- standard error at the worst case (p = 0.5) ----------------------------
p = 0.5
for N in (100, 1024, 4096):
    sigma = math.sqrt(p * (1 - p) / N)
    print(f"N={N:5d}  sigma={sigma:.6f}  ({100*sigma:.2f}%)"
          f"  95% CI +/-{1.96*sigma:.5f}")

# --- the theory against an actual simulation -------------------------------
rng = np.random.default_rng(1234)
TRIALS = 4000
print()
for N in (100, 1024, 4096):
    estimates = rng.binomial(N, p, size=TRIALS) / N
    print(f"N={N:5d}  empirical sd={estimates.std(ddof=1):.6f}"
          f"   theory={math.sqrt(p*(1-p)/N):.6f}")

# --- expectation and variance of a discrete distribution -------------------
outcomes = np.array([0.0, 1.0, 2.0])
probs = np.array([0.25, 0.50, 0.25])
mean = np.sum(outcomes * probs)
var_direct = np.sum((outcomes - mean) ** 2 * probs)
var_shortcut = np.sum(outcomes ** 2 * probs) - mean ** 2
print(f"\nE[X]={mean}   Var (direct)={var_direct}   Var (shortcut)={var_shortcut}")

# --- how many shots to resolve a two-point difference ----------------------
gap = 0.02
target_sigma = 0.005
N_needed = 0.25 / target_sigma ** 2
print(f"shots needed for sigma <= {target_sigma}: {N_needed:.0f} (gap {gap})")
```

Running it prints `sigma=0.050000 (5.00%)` for 100 shots, `0.015625 (1.56%)`
for 1024 and `0.007812 (0.78%)` for 4096. The simulation column agrees with
theory to three decimal places — for example at $N = 1024$ the empirical
standard deviation is `0.015494` against a theoretical `0.015625`. The
discrete distribution gives `E[X]=1.0` and `Var=0.5` by both routes, and the
shot-count calculation returns `10000`.

## Common misconceptions

- **"Running the circuit twice gives the same answer."** Each run is a fresh
  sample. The *counts* vary; only the underlying probability is fixed.
- **"The standard error is the same at every probability."** It is
  proportional to $\sqrt{p(1-p)}$, so it vanishes as $p$ approaches 0 or 1 and
  peaks at $p = 1/2$. Outcomes near 50% are the hardest to pin down.
- **"Ten times the shots gives ten times the accuracy."** The error falls as
  $1/\sqrt{N}$, so ten times the shots gives about 3.2 times the accuracy.
- **"The normal approximation always applies."** It needs $Np$ and $N(1-p)$
  both reasonably large — around 5 or more. For very rare outcomes, use the
  exact binomial instead.
- **"The confidence interval contains the true value with 95% probability."**
  In the frequentist reading used here, the true $p$ is fixed and the interval
  is random: 95% of intervals built this way contain it. The distinction
  matters when reporting results.

## Exercises

1. A distribution takes values $\{1, 2, 4\}$ with probabilities
   $\{0.2, 0.5, 0.3\}$. Compute $\operatorname{E}[X]$ and
   $\operatorname{Var}(X)$ by both the direct and shortcut methods.
2. Compute $\sigma_{\hat{p}}$ at $p = 0.1$ for $N = 1000$, and compare it with
   the value at $p = 0.5$ for the same $N$. Which is larger, and why?
3. How many shots are needed to make $\sigma_{\hat{p}} \le 0.01$ when the true
   probability is $p = 0.25$?
4. You run 500 shots and observe the outcome 140 times. Give a 95% confidence
   interval for the true probability.
5. Explain in one sentence why quadrupling the shots only halves the error.
6. Is the normal approximation reasonable for $p = 0.002$ with $N = 1000$?
   Justify numerically.

## Summary

- A discrete distribution satisfies $\sum_k p_k = 1$; quantum probabilities
  come from the Born rule $p_k = |\langle k|\psi\rangle|^2$.
- $\operatorname{E}[X] = \sum_k x_k p_k$ and
  $\operatorname{Var}(X) = \operatorname{E}[X^2] - \operatorname{E}[X]^2$.
- Estimating a probability from $N$ shots gives standard error
  $\sigma_{\hat{p}} = \sqrt{p(1-p)/N}$, derived from adding Bernoulli
  variances.
- The error is worst at $p = 1/2$ and shrinks only as $1/\sqrt{N}$: four times
  the shots for half the error.
- A 95% confidence interval is approximately $\hat{p} \pm 1.96\,\sigma$, valid
  when $Np$ and $N(1-p)$ are both reasonably large.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §1.2 — the Born rule and the probabilistic interpretation.
- Qiskit documentation, *Sampler primitive* — the shot-based interface whose
  output this lesson teaches you to read.
- Any introductory statistics text — binomial distribution, standard error and
  normal approximation to the binomial.

---

**Previous:** [Eigenvalues, Eigenvectors and Operator Classes](16_eigen_and_operators.md) ·
**Next:** [Introductory Group Theory](18_group_theory.md)
