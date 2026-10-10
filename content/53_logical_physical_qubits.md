# Logical and Physical Qubits, and Overhead

A device advertised as having "1000 qubits" is not advertising 1000 qubits you
can compute with. Almost all of them would be spent protecting a handful of real
ones. This lesson makes that trade-off quantitative: given a physical error rate
and a target logical error rate, how many physical qubits does one logical qubit
cost?

## Learning objectives

By the end of this lesson you should be able to:

- **Define** a logical qubit in terms of the physical qubits and stabilisers that
  realise it, and distinguish the data-qubit count from the full physical cost.
- **Compute** the physical-to-logical ratio for a code family, including the
  ancillas and syndrome rounds the ratio alone omits.
- **Explain** how overhead scales with the target error rate, and why that
  scaling — not the ratio at one fixed size — is what makes a code family
  practical.

## Prerequisites

[Surface Codes](52_surface_codes.md). This lesson uses $[[n,k,d]]$ notation and
the rotated-surface-code result $[[d^2, 1, d]]$ directly.

## What "one logical qubit" means

A **physical qubit** is a controllable two-level quantum system: a transmon, a
trapped ion, an atom in a tweezer. It decoheres, and its gates are imperfect.

A **logical qubit** is not an object. It is a **subspace**: the code space of an
error-correcting code, together with the machinery that keeps the state in it.
Concretely, for a stabiliser code on $n$ physical qubits with $r$ independent
generators, the logical qubit is the $2^{n-r}$-dimensional code space, and

$$k = n - r$$

is the number of logical qubits. When $k = 1$, that subspace is one logical
qubit, and the physical-to-logical ratio is $n/1 = n$.

The definition matters because two things are easy to conflate. A logical qubit
is *not* "one of the physical qubits, but protected" — no individual physical
qubit holds the logical state, and measuring any one of them reveals nothing
about it. And $n$ is *not* the whole cost, as the next section shows.

## The ratio, for the codes met so far

| Code | $[[n, k, d]]$ | Ratio $n/k$ | Corrects |
|---|---|---|---|
| Bit flip | $[[3,1,1]]$ | 3 | bit flips only |
| Phase flip | $[[3,1,1]]$ | 3 | phase flips only |
| Five-qubit | $[[5,1,3]]$ | 5 | any single error |
| Steane | $[[7,1,3]]$ | 7 | any single error |
| Shor | $[[9,1,3]]$ | 9 | any single error |
| Rotated surface, $d=3$ | $[[9,1,3]]$ | 9 | any single error |
| Rotated surface, $d=5$ | $[[25,1,5]]$ | 25 | any two errors |
| Rotated surface, $d=7$ | $[[49,1,7]]$ | 49 | any three errors |
| Rotated surface, $d=11$ | $[[121,1,11]]$ | 121 | any five errors |

The small codes have tiny ratios and fixed power. The surface code has a much
worse ratio at every size — and is still the one used, because it is the only
entry whose power you can dial up indefinitely.

## The ratio understates the cost

Three things are missing from $n$.

**Ancillas.** Measuring a stabiliser needs an ancilla, and a distance-$d$
rotated surface patch has $d^2 - 1$ stabilisers. Giving each its own ancilla
takes the physical count from $d^2$ to roughly

$$n_{\text{phys}} \approx d^2 + (d^2 - 1) = 2d^2 - 1$$

so the distance-3 patch is 17 physical qubits for one logical qubit, not 9.
Shared and reset ancillas can reduce this in some architectures, but the
approximate doubling is the right order of magnitude.

**Time.** A logical qubit is not protected once; it is protected continuously.
One round of syndrome extraction does not stabilise a state, it samples the
errors that happened during that round. A logical operation lasting many rounds
needs a stream of syndromes, and the decoder works on all of them together.

**Space–time volume.** Putting those together, the cost of a logical operation
is qubits multiplied by rounds. For a patch of distance $d$, one logical
operation needs about $d$ rounds, so

$$\text{cost} \approx d^2 \times d = d^3 \text{ qubit-rounds}$$

Measured in that currency: $d = 7$ costs 343 qubit-rounds per logical operation,
$d = 11$ costs 1331, and $d = 21$ costs 9261. Tripling the distance multiplies
the space–time cost by about 27.

## How overhead scales with the target error rate

This is the number that decides whether a code family is practical, and it is
the reason the surface code's poor ratio does not matter.

### The model

Below threshold, and for physical error rate $p$ well below the threshold
$p_{\text{th}}$, the logical error rate of a distance-$d$ surface code patch is
modelled as

$$p_L(d) \;\approx\; A\left(\frac{p}{p_{\text{th}}}\right)^{\frac{d+1}{2}}$$

$A$ is a prefactor of order $0.1$ that depends on the decoder and the noise
model. **This is a fitted model, not a theorem** — the exponent $(d+1)/2$ is the
structural part (it reflects that about $(d+1)/2$ errors are needed to build an
undetectable chain across the patch); the value of $A$ is not universal.

Solving for the distance that reaches a target $p_L^\star$:

$$d \;=\; 2\,\frac{\ln\!\left(p_L^\star / A\right)}{\ln\!\left(p / p_{\text{th}}\right)} - 1$$

Both logarithms are negative when $p < p_{\text{th}}$ and $p_L^\star < A$, so
$d$ comes out positive.

### Verified numbers

With $p_{\text{th}} = 10^{-2}$ and $A = 0.1$:

| Physical $p$ | Target $p_L$ | Distance $d$ | Data qubits $d^2$ | With ancillas $2d^2-1$ |
|---|---|---|---|---|
| $10^{-3}$ | $10^{-6}$ | 9 | 81 | 161 |
| $10^{-3}$ | $10^{-9}$ | 15 | 225 | 449 |
| $10^{-3}$ | $10^{-12}$ | 21 | 441 | 881 |
| $10^{-3}$ | $10^{-15}$ | 27 | 729 | 1457 |
| $10^{-3}$ | $10^{-18}$ | 33 | 1089 | 2177 |
| $10^{-4}$ | $10^{-15}$ | 13 | 169 | 337 |
| $10^{-5}$ | $10^{-15}$ | 9 | 81 | 161 |

Read the first column of distances: at $p/p_{\text{th}} = 0.1$, every three
orders of magnitude of extra reliability costs 6 more units of distance. That
is the scaling, and it is remarkably gentle — $d$ grows **linearly** in
$\log(1/p_L)$, so the qubit count grows as its square:

$$n = d^2 \;\sim\; \bigl(\log \tfrac{1}{p_L}\bigr)^2$$

Polylogarithmic overhead. Tenfold better gates are worth far more than twice the
qubits: going from $p = 10^{-3}$ to $p = 10^{-4}$ at a target of $10^{-15}$ cuts
the patch from 729 to 169 qubits, because the hardware improvement enters
through $\ln(p/p_{\text{th}})$ and is then squared.

The result is also robust to the one number in the model that is not
structural. Varying $A$ from $0.01$ to $0.3$ — a factor of 30 — moves the
required distance at $p = 10^{-3}$, target $10^{-15}$, only from 27 to 29.

### Computing the table

```python
import math


def required_distance(p, p_th, target, A=0.1):
    """Distance d with p_L(d) = A (p/p_th)^((d+1)/2) <= target."""
    if p >= p_th:
        return None                      # above threshold: no distance helps
    return 2 * math.log(target / A) / math.log(p / p_th) - 1


def odd_up(d):
    """Smallest odd integer >= d, tolerant of floating-point noise."""
    c = math.ceil(round(d, 9))
    return c if c % 2 == 1 else c + 1


for target in (1e-6, 1e-9, 1e-12, 1e-15, 1e-18):
    d = odd_up(required_distance(1e-3, 1e-2, target))
    print(f"target p_L = {target:.0e}:  d = {d:2d}   "
          f"data = {d * d:4d}   with ancillas = {2 * d * d - 1:4d}")
```

### Approaching the threshold

The picture changes completely as $p$ approaches $p_{\text{th}}$, because
$\ln(p/p_{\text{th}}) \to 0$ and the required distance diverges. At a target of
$10^{-15}$ with $p_{\text{th}} = 10^{-2}$:

| $p/p_{\text{th}}$ | Distance $d$ | Data qubits $d^2$ |
|---|---|---|
| 0.01 | 15 | 225 |
| 0.05 | 21 | 441 |
| 0.10 | 27 | 729 |
| 0.30 | 53 | 2809 |
| 0.50 | 93 | 8649 |
| 0.70 | 181 | 32761 |
| 0.90 | 611 | 373321 |
| 0.95 | 1257 | 1580049 |

Operating at half the threshold costs more than ten times the qubits of
operating at a tenth of it. This is the practical content of the word
"threshold": being below it is not enough, and how far below is the dominant
factor in the bill. It is also the subject of
[the next lesson](54_threshold_theorem.md).

## Concatenated codes, for comparison

Concatenation is the natural alternative: encode each physical qubit of a code
in another copy of the code, recursively. If one level maps a physical error
rate $p$ to a logical one $c\,p^2$ — the squaring is the point, since a
distance-3 code corrects one error and fails on two — then $L$ levels give

$$p_L \;\approx\; c^{\,2^L - 1}\, p^{\,2^L}, \qquad n = n_1^L$$

with $n_1$ the size of the base code. The recursion is the same one printed
below, applied repeatedly.

The error rate falls **doubly exponentially** in $L$, which sounds better than
it is, because the qubit count rises exponentially in $L$. Solving for the
scaling gives

$$n = n_1^L \;\sim\; \bigl(\log \tfrac{1}{p_L}\bigr)^{\log_2 n_1}$$

Compare exponents with the surface code:

| Family | Overhead in target error rate | Exponent |
|---|---|---|
| Rotated surface code | $\sim \log^2(1/p_L)$ | **2.000** |
| Concatenated Steane ($n_1 = 7$) | $\sim \log^{\log_2 7}(1/p_L)$ | 2.807 |
| Concatenated Shor ($n_1 = 9$) | $\sim \log^{\log_2 9}(1/p_L)$ | 3.170 |

The surface code's exponent of 2 beats any base code with $n_1 > 4$. Both are
polylogarithmic, so both "work" in principle; the surface code just gets there
with fewer qubits, and that difference compounds quickly.

### Verified head-to-head

At $p = 10^{-3}$ with the model above ($p_{\text{th}} = 10^{-2}$, $A = 0.1$) and
$c = 100$ for concatenation:

| Family | To reach $p_L = 10^{-15}$ | To reach $p_L = 10^{-18}$ |
|---|---|---|
| Rotated surface code | $d = 27$: **729** data qubits | $d = 33$: **1089** data qubits |
| Concatenated Steane | $L = 4$: 2401 qubits | $L = 5$: 16807 qubits |
| Concatenated Shor | $L = 4$: 6561 qubits | $L = 5$: 59049 qubits |

Roughly $3\times$ better than concatenated Steane and $9\times$ better than
concatenated Shor at $10^{-15}$, and about $15\times$ and $54\times$ at
$10^{-18}$.

### The catch in the comparison

Concatenation has a **pseudo-threshold** of its own. The recursion
$p \mapsto c\,p^2$ only decreases when $c\,p < 1$, so the scheme improves things
only while

$$p < \frac{1}{c}$$

With $c = 100$ that means $p < 10^{-2}$; with $c = 1000$ it means
$p < 10^{-3}$. Verified: at $c = 1000$ and $p = 10^{-3}$, $cp = 1$ exactly and
the recursion does not improve the error rate at all, no matter how many levels
are added. The surface code's threshold is a property of the code and decoder;
concatenation's cut-off depends on the same constant that sets its error
suppression, so improving one worsens the other.

The concatenation numbers also depend strongly on $c$, which is not a constant
of nature but a count of how many error pairs defeat the code. Changing $c$ from
10 to 100 moves the level count by one, which changes the qubit count by a
factor of $n_1$. Treat the table as an order-of-magnitude comparison, not a
prediction.

## Limitations and assumptions

- **The $p_L$ model is a fit.** $p_L \approx A(p/p_{\text{th}})^{(d+1)/2}$ is
  the standard working approximation below threshold. It is not exact, $A$ is
  not universal, and near the threshold it breaks down. Every table above
  inherits that.
- **Circuit-level noise is assumed.** The thresholds quoted in the literature
  assume every operation — gates, measurement, reset, idling — fails
  independently at rate $p$. Real devices add leakage out of the computational
  subspace, crosstalk and correlated errors, none of which the model includes.
- **The algorithm's own structure is ignored.** One logical qubit is not a
  computation. Running
  [Shor's algorithm](33_shors_algorithm.md) needs many logical qubits,
  non-Clifford gates that cannot be executed transversally, and magic-state
  distillation whose overhead can exceed the cost of the surface patches
  themselves.
- **Magic states are the real driver.** For fault-tolerant computing the
  dominant cost is usually producing high-fidelity $T$ states, not storing
  logical qubits. The numbers in this lesson are a floor, not an estimate.
- **Architecture matters.** Lattice surgery, routing between patches, and
  whether ancillas can be shared or reset all shift the constant substantially.

## Common misconceptions

- **"1000 physical qubits means 1000 logical qubits."** At $p = 10^{-3}$ and a
  $10^{-15}$ target, a single logical qubit costs 729 data qubits. A thousand
  physical qubits buys roughly one.
- **"A better ratio means a better code."** The three-qubit codes have a ratio
  of 3 and cannot be scaled at all. The surface code has a ratio of $d^2$ and
  is scalable, which is why it wins.
- **"Below threshold, overhead is bounded."** It is polylogarithmic, which is
  excellent, but it diverges as $p \to p_{\text{th}}$.
  At a ratio $p/p_{\text{th}} = 0.9$ the same target needs 373321 qubits per
  logical qubit.
- **"Concatenation is obsolete."** It has a worse exponent and a
  pseudo-threshold, but it is simple, has no decoding bottleneck, and remains
  the cleanest setting for proving the threshold theorem.
- **"Overhead is just the qubit count."** A logical operation costs qubits
  $\times$ rounds. Tripling $d$ multiplies the space–time cost by about 27.

## Exercises

1. A rotated surface patch uses 441 data qubits. What is its distance, how many
   stabiliser generators does it have, and how many errors does it correct?

2. Using $p_L \approx A(p/p_{\text{th}})^{(d+1)/2}$ with $A = 0.1$ and
   $p_{\text{th}} = 10^{-2}$, what distance is needed at $p = 10^{-3}$ for a
   target of $10^{-9}$? What is the physical cost with ancillas?

3. Why does improving the physical error rate by a factor of 10 cut the qubit
   count by much more than a factor of 10?

4. A concatenation scheme uses $c = 100$ and a base code of $n_1 = 7$. At
   $p = 5 \times 10^{-3}$, does the scheme improve the error rate at all? What
   is the largest $p$ for which it does?

5. Explain why $n \sim \log^2(1/p_L)$ is considered good, even though the qubit
   count still grows without bound as the target improves.

6. A distance-11 rotated surface patch runs a logical operation taking 11
   syndrome rounds. Compute the space–time cost in qubit-rounds, and compare it
   with a distance-7 patch running the same operation.

### Answers to 1–3

**1.** $n = d^2 = 441$, so $d = 21$. Generators: $d^2 - 1 = 440$. Errors
corrected: $t = \lfloor (21-1)/2 \rfloor = 10$. With ancillas the patch costs
about $2 \cdot 441 - 1 = 881$ physical qubits.

**2.** Solving $d = 2\ln(10^{-9}/0.1)/\ln(10^{-3}/10^{-2}) - 1$:

$$d = 2\,\frac{\ln 10^{-8}}{\ln 10^{-1}} - 1 = 2\cdot\frac{-18.42}{-2.303} - 1 = 2(8) - 1 = 15$$

Distance 15, so $d^2 = 225$ data qubits and $2d^2 - 1 = 449$ with ancillas.

**3.** The physical error rate enters through $\ln(p/p_{\text{th}})$, and the
distance is proportional to that logarithm, so the qubit count $d^2$ is
proportional to its **square**. Ten times better gates multiply
$\ln(p/p_{\text{th}})$ by a factor of about 2 (from $\ln 10^{-1}$ to
$\ln 10^{-2}$), and the qubit count falls by roughly $2^2 = 4$, not 10.
Verified in the table: at a target of $10^{-15}$, going from $p = 10^{-3}$ to
$p = 10^{-4}$ takes the patch from 729 to 169 qubits — a factor of 4.3.

### Answers to 4–6

**4.** The recursion improves the error rate only while $cp < 1$. Here
$cp = 100 \times 5\times10^{-3} = 0.5 < 1$, so it does improve, but slowly: the
first level gives $p_1 = 100 \times (5\times10^{-3})^2 = 2.5\times10^{-3}$,
only a factor of 2 better than where it started. The largest $p$ for which the
scheme helps at all is $p = 1/c = 10^{-2}$.

**5.** Because the alternative is worse. Protection by any means requires
resources that grow as the demanded reliability grows — there is no free lunch.
What matters is the *rate*. A polylogarithmic overhead means that each extra
decimal digit of reliability costs a fixed increment in distance, so the
resources grow slowly enough to be budgetable. An exponential or polynomial
overhead in $1/p_L$ would make very high reliability unreachable at any
plausible device size.

**6.** Distance 11: $d^2 = 121$ qubits $\times$ 11 rounds $= 1331$
qubit-rounds. Distance 7: 49 qubits $\times$ 7 rounds $= 343$. The ratio is
$1331/343 \approx 3.88$, essentially $(11/7)^3 \approx 3.88$ — the cubic scaling
$d^3$ that qubit-rounds inherit from $d^2$ qubits and $d$ rounds.

## Summary

- A logical qubit is a **subspace**, not an object: the code space of $n$
  physical qubits under $r$ independent stabilisers, with $k = n - r$.
- The physical-to-logical ratio is 3 for the three-qubit codes, 5 for the
  five-qubit code, 7 for Steane, 9 for Shor, and $d^2$ for a rotated surface
  patch.
- The ratio understates the real cost: ancillas roughly double it to
  $2d^2 - 1$, and a logical operation costs about $d^3$ qubit-rounds.
- Below threshold, $p_L \approx A(p/p_{\text{th}})^{(d+1)/2}$, so
  $d \sim \log(1/p_L)$ and $n = d^2 \sim \log^2(1/p_L)$ — polylogarithmic.
  At $p = 10^{-3}$ and $p_{\text{th}} = 10^{-2}$, reaching $10^{-15}$ needs
  $d = 27$, or 729 data qubits.
- The result is insensitive to the model's prefactor: varying $A$ by a factor
  of 30 moves $d$ from 27 to 29 at that target.
- Overhead diverges as $p \to p_{\text{th}}$. At $p/p_{\text{th}} = 0.5$ the
  same $10^{-15}$ target needs 8649 data qubits; at 0.9 it needs 373321.
- Surface codes beat concatenation because their exponent is 2 against
  $\log_2 n_1 = 2.81$ for Steane and 3.17 for Shor: 729 qubits against 2401 and
  6561 at a $10^{-15}$ target. Concatenation additionally stall unless
  $p < 1/c$.

## References

- Fowler, A. G., Mariantoni, M., Martinis, J. M. & Cleland, A. N. — surface-code
  resource estimates, including the ancilla and time costs.
- Google Quantum AI, "Suppressing quantum errors by scaling a surface code
  logical qubit" — measured logical error rates scaling with distance.
- Gidney, C. & Ekerå, M. — end-to-end factoring resource estimates, and why
  magic-state distillation dominates.
- Knill, E. — concatenated-code overhead and the pseudo-threshold behaviour.
- [Surface Codes](52_surface_codes.md) — the $[[d^2,1,d]]$ construction these
  estimates are built on.
- [Threshold Theorem and Fault Tolerance](54_threshold_theorem.md) — what
  "below threshold" actually guarantees.
- [Shor's Algorithm](33_shors_algorithm.md) — where very small logical error
  rates are demanded.

---

**Next:** [Threshold Theorem and Fault Tolerance](54_threshold_theorem.md)
