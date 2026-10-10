# Approximation Ratios

QAOA does not return the optimal answer to a combinatorial problem. It returns a
sample from a distribution that is *biased toward* good answers. The natural
question is therefore not "is it correct?" but "how close does it get?" — and the
standard measure of that is the **approximation ratio**.

## Learning objectives

By the end of this lesson you should be able to:

- **Define** the approximation ratio for a maximisation problem.
- **Compute** the ratio achieved by a given QAOA output, and distinguish the
  expected value from a single sample.
- **Interpret** the known worst-case ratio for QAOA at depth one, and state the
  class of graphs it applies to.

## Prerequisites

This lesson assumes [QAOA](07_vqe_qaoa.md) — the alternating phase-separation
and mixer structure, and the parameters $\gamma$ and $\beta$.

## Why a ratio

### Optimisation is hard, approximation is the goal

MaxCut on a general graph is NP-hard. Finding the true optimum is believed to
require exponential time. So the useful question for any heuristic — classical or
quantum — is how well it approximates the optimum in polynomial time.

For a **maximisation** problem with cost $C$, the approximation ratio of a
solution $x$ is

$$\alpha = \frac{C(x)}{C_{\max}}$$

where $C_{\max}$ is the optimal cost. It lies in $[0, 1]$, and $1$ means optimal.
For randomised algorithms the quantity of interest is the **expected** ratio,
$\mathbb{E}[C]/C_{\max}$, over the algorithm's output distribution.

### The classical benchmark to beat

The best known classical polynomial-time algorithm for MaxCut is the
Goemans–Williamson semidefinite programming relaxation, achieving an expected
ratio of about **0.878** on general graphs. Under the Unique Games Conjecture
this is optimal for polynomial-time classical algorithms.

That number is the bar. Any claim that QAOA is competitive has to be measured
against 0.878, and — this is the crux — for larger $p$, not for $p = 1$.

## Computing a ratio

### A worked measurement

For MaxCut, $C(x)$ counts the edges crossing the cut. Given a QAOA output
distribution, compute $\langle C \rangle = \sum_x P(x)\,C(x)$ and divide by the
brute-force optimum.

Verified for QAOA at depth $p = 1$, with $(\gamma, \beta)$ optimised on a grid:

| Graph | Vertices | $C_{\max}$ | Best $\langle C\rangle$ | Ratio |
|---|---|---|---|---|
| Triangle | 3 | 2 | 1.9979 | **0.9990** |
| Square (4-cycle) | 4 | 4 | 2.9982 | **0.7495** |
| Path on 4 vertices | 4 | 3 | 2.3782 | **0.7927** |
| Star on 4 vertices | 4 | 3 | 2.3153 | **0.7718** |

Read these carefully, because they illustrate the two things that make
approximation ratios easy to misread.

### Small graphs flatter the algorithm

The triangle reaches a ratio of 0.9990 — essentially optimal. That is a real
number, not an error, but it is a property of a 3-vertex graph where there is
hardly anywhere for the algorithm to go wrong. Ratios measured on tiny instances
do not generalise, and this is the most common way QAOA benchmarks mislead.

### The expected value is not a single sample

These are **expectation** values over the full output distribution. A single
measurement from a QAOA run gives one bit string and one cost, which may be well
above or below $\langle C\rangle$. To *estimate* the ratio on hardware you must
average over many shots, and the estimate itself carries shot noise.

## The depth-one guarantee

### The result

For QAOA at $p = 1$ on **3-regular** graphs, Farhi, Goldstone and Gutmann proved
a worst-case expected approximation ratio of

$$\alpha \;\ge\; 0.6924$$

This is a **guarantee**, not a typical value: no 3-regular graph exists where
$p = 1$ QAOA does worse than this, once $\gamma$ and $\beta$ are optimised.

### What it does and does not say

Three qualifications, all of which matter:

**It applies to 3-regular graphs.** The proof exploits the structure of
3-regular graphs specifically. None of the graphs in the table above is
3-regular — the triangle is 2-regular, the square is 2-regular, the path has
degree-1 endpoints and the star has a degree-3 centre — so the 0.6924 bound
does **not** apply to any of them. This is why the measured ratios above sit
well above 0.6924 without contradicting it.

**It is a floor, not a prediction.** Typical performance on random 3-regular
graphs is usually better than 0.6924. The guarantee is the worst case.

**It is for $p = 1$, which is below the classical bar.** At 0.6924, depth-one
QAOA is *worse* than Goemans–Williamson's 0.878. Depth one is not where QAOA is
competitive; the interest is in whether the ratio improves fast enough with $p$
to surpass 0.878 before the circuit becomes impractical to run. That question is
still open.

### Why depth matters

The ratio is provably non-decreasing in $p$ for MaxCut, and reaches 1 as
$p \to \infty$ — but the circuit depth grows with $p$, and on noisy hardware
deeper circuits produce worse results despite better theory. The practical
question is the value of $p$ at which the theoretical improvement is overtaken
by accumulated error, and that depends entirely on the hardware.

## Limits and caveats

### Worst-case bounds are pessimistic by design

A guarantee of 0.6924 tells you nothing about how QAOA performs on *your*
instance. Empirical studies on small random instances often show much better
behaviour, which is encouraging but not a substitute for a bound.

### No proven quantum advantage for QAOA

As of writing, there is **no** proven instance where QAOA beats the best
classical algorithm for a combinatorial problem. There are results showing
barriers (for example, that low-depth QAOA cannot outperform certain classical
algorithms on specific graph families) and results suggesting promise at higher
depth. Claims of advantage should be treated as open.

### The optimum must be known to measure the ratio

Computing $\alpha$ requires $C_{\max}$, which for interesting instances is
NP-hard to find. So approximation ratios are measured on instances small enough
to brute-force — which is exactly the regime where the numbers flatter the
algorithm, as the table shows.

### Expectation versus samples, again

Estimating $\langle C\rangle$ to a given precision costs shots, and the cost
grows as the inverse square of the target precision. A ratio quoted to four
decimal places on hardware implies a substantial shot budget.

## Practical example

### Brute-force optimum and QAOA expectation

```python
import numpy as np
from itertools import product


def maxcut_value(bits, edges):
    return sum(1 for u, v in edges if bits[u] != bits[v])


def brute_force_max(edges, n):
    return max(maxcut_value(list(bits), edges)
               for bits in product([0, 1], repeat=n))


def qaoa_p1_expectation(edges, n, gamma, beta):
    """<C> for depth-1 QAOA on MaxCut, by direct statevector evolution."""
    dim = 1 << n
    C = np.zeros(dim)
    for idx in range(dim):
        C[idx] = maxcut_value([(idx >> (n - 1 - u)) & 1 for u in range(n)],
                              edges)
    psi = np.ones(dim, dtype=complex) / np.sqrt(dim)
    psi = np.exp(-1j * gamma * C) * psi          # phase separation

    cb, sb = np.cos(beta), np.sin(beta)          # mixer: e^{-i beta X}
    mix = np.array([[cb, -1j * sb], [-1j * sb, cb]], dtype=complex)
    for q in range(n):
        new = np.zeros(dim, dtype=complex)
        for idx in range(dim):
            b = (idx >> (n - 1 - q)) & 1
            for b2 in (0, 1):
                a = mix[b2, b]
                if a:
                    new[(idx & ~(1 << (n - 1 - q)))
                        | (b2 << (n - 1 - q))] += a * psi[idx]
        psi = new
    return float(np.sum(np.abs(psi) ** 2 * C))
```

### Computing the ratios

```python
graphs = [("triangle", 3, [(0, 1), (1, 2), (0, 2)]),
          ("square", 4, [(0, 1), (1, 2), (2, 3), (3, 0)]),
          ("path-4", 4, [(0, 1), (1, 2), (2, 3)]),
          ("star-4", 4, [(0, 1), (0, 2), (0, 3)])]

print("graph      n  C_max   best <C>   ratio")
for name, n, edges in graphs:
    cmax = brute_force_max(edges, n)
    best = 0.0
    for gamma in np.linspace(0, np.pi, 60):
        for beta in np.linspace(0, np.pi / 2, 30):
            best = max(best, qaoa_p1_expectation(edges, n, gamma, beta))
    print(f"{name:10s} {n}   {cmax:5d}   {best:8.4f}   {best / cmax:.4f}")

print("\nworst-case guarantee, p=1 on 3-regular graphs: 0.6924")
print("classical Goemans-Williamson benchmark:       0.8786")
print("NOTE: none of the graphs above is 3-regular, so the 0.6924")
print("      bound does not apply to any of these rows.")
```

Running the blocks in order reproduces the ratio table and prints the two
reference numbers with the caveat that the bound does not apply to these
particular graphs.

## Common misconceptions

- **"A ratio of 1.0 on the triangle means QAOA solves MaxCut."** It means QAOA
  solves MaxCut on a 3-vertex graph. Small instances flatter every heuristic.
- **"0.6924 is what QAOA achieves."** It is a **worst-case floor** for 3-regular
  graphs at $p=1$. Typical performance is better; the bound is a guarantee.
- **"The bound applies to my graph."** Only if your graph is 3-regular. Check
  before quoting it.
- **"QAOA provably beats classical algorithms."** It does not, yet. The 0.878
  classical benchmark stands.
- **"$\langle C\rangle$ is what one run gives."** It is an expectation over the
  distribution; a single sample varies.

## Exercises

1. Compute the approximation ratio for a bit string that cuts 3 of 4 edges on a
   square.
2. Why is the triangle's ratio so high? Would you expect the same on a
   100-vertex 3-regular graph?
3. Verify that all four test graphs are not 3-regular, by computing vertex
   degrees.
4. What is the Goemans–Williamson ratio, and why is it the number to beat?
5. Explain why measuring an approximation ratio requires solving the problem
   exactly first, and what that implies about which instances can be
   benchmarked.
6. If the ratio is provably non-decreasing in $p$, why not simply take $p$ very
   large?

## Summary

- The approximation ratio for a maximisation problem is
  $\alpha = C(x)/C_{\max}$; for randomised algorithms the quantity is
  $\mathbb{E}[C]/C_{\max}$.
- Verified $p=1$ ratios: triangle **0.9990**, square **0.7495**, path-4
  **0.7927**, star-4 **0.7718** — expectation values over the full distribution,
  not single samples.
- QAOA at $p=1$ on **3-regular** graphs is guaranteed at least **0.6924** — a
  worst-case floor, and below the classical Goemans–Williamson 0.878.
- None of the test graphs above is 3-regular, so that bound does not apply to
  them, which is why their ratios exceed it.
- The ratio is non-decreasing in $p$ and reaches 1 in the limit, but depth costs
  error on real hardware.
- **No proven quantum advantage exists for QAOA** against the best classical
  algorithms.

## References

- Farhi, E., Goldstone, J. & Gutmann, S. (2014), "A quantum approximate
  optimization algorithm" — including the 0.6924 bound for 3-regular graphs.
- Goemans, M. X. & Williamson, D. P. (1995), "Improved approximation algorithms
  for maximum cut and satisfiability problems" — the 0.878 benchmark.
- Hastings, M. B. (2019), "Classical and quantum bounded depth approximation
  algorithms" — barriers for low-depth QAOA.
- The [VQE and QAOA](07_vqe_qaoa.md) lesson — the algorithm being measured.

---

**Previous:** [Optimization Loops and the Parameter-Shift Rule](45_optimization_loops.md)
