# Reading Quantum Results

A quantum computer does not return an answer; it returns **counts**. You run a
circuit $N$ times and get a histogram of bit strings, and every number you
report has to be estimated from that histogram. This lesson is about doing that
honestly: converting counts to probabilities, propagating the uncertainty,
computing marginals and expectation values, and recognising the several ways a
histogram can mislead you.

## Learning objectives

By the end of this lesson you should be able to:

- **Convert** raw shot counts into estimated probabilities with standard errors.
- **Compute** marginal probabilities for individual qubits from joint counts.
- **Evaluate** expectation values and correlators such as $\langle Z_0\rangle$
  and $\langle Z_0 Z_1\rangle$ from a histogram.
- **Identify** the bit-ordering convention, and explain the errors it causes
  when misapplied.
- **Choose** a shot count sufficient to resolve a target difference, and state
  what a zero count does and does not imply.

## From counts to probabilities

### The estimate

If outcome $k$ appears $n_k$ times in $N$ shots, the estimated probability is

$$\hat{p}_k = \frac{n_k}{N}$$

with standard error

$$\sigma_k = \sqrt{\frac{\hat{p}_k(1 - \hat{p}_k)}{N}}$$

This is the formula derived in the probability lesson, applied to real
hardware output.

### Worked example

A two-qubit Bell circuit, sampled at three shot counts:

| Shots | $\hat{p}(00)$ | $\hat{p}(11)$ |
|---|---|---|
| 100 | $0.5500 \pm 0.0497$ | $0.4500 \pm 0.0497$ |
| 1000 | $0.4860 \pm 0.0158$ | $0.5140 \pm 0.0158$ |
| 4096 | $0.4866 \pm 0.0078$ | $0.5134 \pm 0.0078$ |

The true values are $0.5$ and $0.5$. At 100 shots the estimate is off by about
one standard error and the uncertainty is 5% — enough to make an ideal result
look imperfect. At 4096 shots the error bar is under 1%.

The $01$ and $10$ outcomes never appear, which is the signature of entanglement:
the two qubits always agree.

### Always report the error bar

A probability without an uncertainty is not a result. $\hat{p} = 0.55$ at 100
shots and $\hat{p} = 0.55$ at 10000 shots are wildly different claims, and only
the error bar distinguishes them.

## Marginals

### Definition

The **marginal** for one qubit is obtained by summing the joint counts over
all values of the other qubits:

$$P(q_i = 1) = \sum_{\text{strings with bit } i = 1} \hat{p}(\text{string})$$

### Worked example

From the 4096-shot Bell run, $P(q_0 = 1) = 0.5076$ and $P(q_1 = 1) = 0.5076$.
Both are close to $0.5$, which says: **each qubit individually looks like a
fair coin.** All the structure is in the correlation, not in the marginals.

This is a recurring trap. Checking only the marginals of an entangled state
tells you nothing — a maximally entangled pair and a maximally mixed pair of
independent qubits have identical marginals.

## Expectation values

### From counts

For an observable diagonal in the computational basis, the expectation value is
the count-weighted average of the eigenvalues. For $Z$ on qubit 0, the
eigenvalue is $+1$ when the bit is 0 and $-1$ when it is 1:

$$\langle Z_0 \rangle = \frac{1}{N}\sum_{\text{strings}} (-1)^{\text{bit}_0} \, n(\text{string})$$

### Worked values

From the Bell run:

$$\langle Z_0 \rangle \approx -0.0151 \quad (\text{theory } 0)$$

$$\langle Z_0 Z_1 \rangle = \frac{1}{N}\sum_{\text{strings}} (-1)^{\text{bit}_0 + \text{bit}_1} \, n(\text{string}) \approx 1.0000 \quad (\text{theory } +1)$$

The single-qubit expectation is zero, consistent with the flat marginals. The
two-qubit correlator is $+1$: the outcomes always agree, which is the
entanglement. Measuring only $\langle Z_0\rangle$ would have shown nothing.

This is why real experiments estimate *many* Pauli expectation values rather
than one — the interesting structure is usually in the correlators.

## Pitfalls

### Bit ordering

The leftmost bit in a bit string is qubit 0 in most textbook conventions, but
Qiskit maps the *rightmost* character to the lowest index when converting a
string to an integer. So `01` as an integer is $1$, and it is qubit 0 (not
qubit 1) that is in state $|1\rangle$.

Concretely: for the string `10`, qubit 0 is $1$ and qubit 1 is $0$ — the
opposite of what a left-to-right reading of the integer suggests. Getting this
backwards silently swaps every marginal and every expectation value you
compute. When in doubt, verify against a known state.

### Zero counts are not zero probability

An outcome appearing zero times in $N$ shots does **not** mean its probability
is zero. The rule of three gives a 95% upper bound:

$$p \lesssim \frac{3}{N}$$

So 0 counts in 100 shots is consistent with a probability up to about $0.03$,
and 0 counts in 1000 shots up to about $0.003$. Reporting "probability 0" from
finite shots is a real error — it is how people conclude a noisy device is
perfect.

### Reading too much into small differences

To resolve a difference of size $d$ at $p = 0.5$:

$$N \gtrsim \frac{0.25}{(d/2)^2}$$

| Target difference | Shots needed |
|---|---|
| 5% | 400 |
| 1% | 10000 |

A 1% claim needs ten thousand shots per setting. Two histograms that differ by
less than their error bars do not differ at all, no matter how the bars look.

### Confusing the histogram with the state

The counts are a sample from the state's probability distribution, not the
distribution itself. Repeating the identical circuit gives different counts.
Only in the limit of many shots do the frequencies converge.

## Practical example

### Estimating probabilities with error bars

```python
import numpy as np

rng = np.random.default_rng(7)
KEYS = ["00", "01", "10", "11"]
TRUE_PROBS = np.array([0.5, 0.0, 0.0, 0.5])   # a Bell state

for N in (100, 1000, 4096):
    counts = rng.multinomial(N, TRUE_PROBS)
    est = {k: c / N for k, c in zip(KEYS, counts)}
    err = {k: np.sqrt(est[k] * (1 - est[k]) / N) for k in KEYS}
    print(f"N={N:5d}: " + "  ".join(
        f"{k}={est[k]:.4f}+-{err[k]:.4f}" for k in KEYS if est[k] > 0))
```

### Marginals and expectation values

```python
counts = rng.multinomial(4096, TRUE_PROBS)
c = dict(zip(KEYS, counts))
N = sum(c.values())

p_q0 = sum(v for k, v in c.items() if k[0] == "1") / N
p_q1 = sum(v for k, v in c.items() if k[1] == "1") / N
print(f"marginal P(q0=1) = {p_q0:.4f}    P(q1=1) = {p_q1:.4f}")

Z0 = sum((1 if k[0] == "0" else -1) * v for k, v in c.items()) / N
ZZ = sum(((1 if k[0] == "0" else -1) * (1 if k[1] == "0" else -1)) * v
         for k, v in c.items()) / N
print(f"<Z0>   = {Z0:.4f}   (theory 0)")
print(f"<Z0Z1> = {ZZ:.4f}   (theory +1)")
```

### How many shots, and what zero counts mean

```python
for d in (0.05, 0.01):
    print(f"shots to resolve a {d:.0%} difference at p=0.5: "
          f"{0.25 / (d / 2) ** 2:.0f}")

print("\nrule of three: 0 counts in N shots implies p <~ 3/N")
for N in (100, 1000):
    print(f"  N={N}: 95% upper bound {3 / N:.4f}")
```

Running the blocks in order prints the three shot counts with their error bars,
converging from `0.5500+-0.0497` at 100 shots to `0.4866+-0.0078` at 4096. The
marginals come out near $0.5$ for both qubits, $\langle Z_0\rangle$ near zero,
and $\langle Z_0Z_1\rangle$ at `1.0000` — the correlator, not the marginal, is
where the entanglement shows up. The shot-count table gives `400` and `10000`,
and the rule of three gives `0.0300` and `0.0030`.

## Common misconceptions

- **"The tallest bar is the answer."** The tallest bar is the most frequent
  sample, which is a noisy estimate. Compare error bars, not heights.
- **"An outcome that never appeared has probability zero."** It has an upper
  bound of about $3/N$. Finite shots can never establish a zero.
- **"More qubits means proportionally more shots."** The number of possible
  outcomes grows as $2^n$, so a fixed shot budget is spread thinner and the
  per-outcome error grows.
- **"Marginals capture what the state does."** For entangled states the
  marginals can be completely flat while the correlators carry all the
  structure.
- **"Re-running the same circuit reproduces the histogram."** Each run is a new
  sample. Only the underlying probabilities are stable.

## Exercises

1. You observe an outcome 230 times in 1000 shots. Estimate its probability and
   give a 95% confidence interval.
2. From the counts `{'00': 480, '01': 20, '10': 15, '11': 485}`, compute the
   marginals for both qubits and $\langle Z_0 Z_1\rangle$.
3. An outcome appears 0 times in 500 shots. What is the 95% upper bound on its
   probability? Explain why "zero" is the wrong answer.
4. How many shots are needed to distinguish $p = 0.50$ from $p = 0.51$?
5. Explain why a Bell pair and two independent maximally mixed qubits have the
   same single-qubit marginals but very different two-qubit correlators.
6. For the string `011` on three qubits, which qubit is in state $|1\rangle$
   under the convention that the leftmost bit is qubit 0? What integer does
   Qiskit assign to this string?

## Summary

- Convert counts with $\hat{p} = n/N$ and standard error
  $\sqrt{\hat{p}(1-\hat{p})/N}$; always report both.
- Marginals sum joint probabilities over the other qubits; for entangled states
  they are often uninformative.
- Expectation values are count-weighted averages of eigenvalues; correlators
  such as $\langle Z_0Z_1\rangle$ carry the structure that marginals miss.
- Bit ordering is a real hazard: check which end of the string is qubit 0
  before computing anything.
- Zero counts imply $p \lesssim 3/N$, not $p = 0$; resolving a difference $d$
  near $p = 0.5$ needs about $0.25/(d/2)^2$ shots.

## References

- Qiskit documentation, *Sampler primitive* — the shot-based interface that
  produces these histograms.
- The [Probability, Expectation and Sampling Statistics](17_probability_and_statistics.md)
  lesson — where the standard error formula is derived.
- The [Entanglement Measures](21_entanglement_measures.md) lesson — why
  correlators, not marginals, reveal entanglement.

---

**Previous:** [Quantum Teleportation](26_teleportation.md) ·
**Next:** [The Quantum Composer](28_composer_guide.md)
