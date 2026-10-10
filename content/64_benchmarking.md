# Quantum Benchmarking

How good is a quantum computer? The question sounds simple and is not. Every
answer is a *number extracted by a specific procedure*, and each procedure is
sensitive to some failure modes and blind to others. A device can look excellent
on one benchmark and poor on another without anyone lying.

This lesson covers the two benchmarks you will meet most often — randomised
benchmarking and quantum volume — and how to choose a benchmark that actually
tests a claimed capability.

## Learning objectives

By the end of this lesson you should be able to:

- **Describe** randomised benchmarking and what it measures.
- **Define** quantum volume and its limitations.
- **Choose** a benchmark appropriate to a claimed capability.

## Prerequisites

[NISQ Limitations](62_nisq_limitations.md) (**required**) — benchmarks measure
how close a device is to its limits.
[Calibrated Noise Models and Connectivity Topologies](61_platform_comparison.md)
(recommended) — cross-platform comparison needs comparable metrics.

## Why benchmarking is hard

Three difficulties, and they are worth naming because they explain why so many
benchmarks exist.

**You cannot check the answer.** For more than about 50 qubits, computing the
expected output is exactly the thing that is intractable. A benchmark therefore
cannot simply compare the device's answer to the right answer.

**Errors are not independent.** The convenient model in which each gate fails
with probability $\varepsilon$ is an approximation. Real devices have crosstalk,
correlated errors, and drift. A benchmark that assumes independence will
understate the problem.

**Single numbers invite gaming.** Any scalar benchmark can be optimised against.
Improve the metric without improving the machine, and the number goes up. This
has happened.

## Randomised benchmarking

Randomised benchmarking (RB) is the workhorse, and it is the most trustworthy
number on a spec sheet — provided you know what it measures.

### The protocol

1. Prepare $\lvert 0\cdots 0\rangle$.
2. Apply $m$ gates drawn uniformly at random from the **Clifford group**.
3. Apply the inverse of their product, so the whole sequence is the identity.
4. Measure. Record the **survival probability** — how often you get back to the
   initial state.
5. Repeat for increasing $m$, and for many random sequences at each $m$.

Step 3 is the trick. The ideal composite is the identity, so the correct answer
is always $\lvert 0\cdots 0\rangle$, and *any* deviation is noise. No classical
simulation is needed to know the right answer — which sidesteps the first
difficulty above entirely.

### Why it works

Averaging over random Cliffords **twirls** the noise: any error channel,
averaged over the Clifford group, becomes a depolarising channel with the same
average fidelity. So whatever the physical error mechanism is, RB sees it as
depolarising noise — and the decay is a clean exponential:

$$F(m) = A\,p^{m} + \frac{1}{2^{n}}$$

The $1/2^n$ floor is the probability of getting the right answer by guessing
after complete depolarisation. Fit $A$ and $p$, then convert $p$ to the figure of
merit, the **error per Clifford**:

$$\text{EPC} = \frac{2^{n}-1}{2^{n}}\,(1-p)$$

### Verified: does it recover a known error rate?

The right way to trust a measurement procedure is to run it on a system whose
answer you already know. Injecting depolarising noise with parameter $\lambda$
on one qubit, the theory predicts $p = 1-\lambda$ and
$\text{EPC} = \lambda/2$. Simulating the protocol and fitting:

| $\lambda$ injected | $p$ fitted | $p$ theory | EPC fitted | EPC theory | Relative error |
|---|---|---|---|---|---|
| 0.002 | 0.99800 | 0.99800 | 0.001000 | 0.001000 | 0.00% |
| 0.005 | 0.99500 | 0.99500 | 0.002500 | 0.002500 | 0.00% |
| 0.010 | 0.99000 | 0.99000 | 0.005000 | 0.005000 | 0.00% |
| 0.020 | 0.98000 | 0.98000 | 0.010000 | 0.010000 | 0.00% |

### The full decay curve

The full decay curve at $\lambda = 0.01$, measured, fitted and predicted:

| $m$ | Survival | Fit | Theory |
|---|---|---|---|
| 0 | 1.00000 | 1.00000 | 1.00000 |
| 5 | 0.97550 | 0.97550 | 0.97550 |
| 20 | 0.90895 | 0.90895 | 0.90895 |
| 40 | 0.83449 | 0.83449 | 0.83449 |
| 80 | 0.72376 | 0.72376 | 0.72376 |
| 160 | 0.60014 | 0.60014 | 0.60014 |
| 320 | 0.52006 | 0.52006 | 0.52006 |

**RB recovers the injected error rate exactly.** That is what makes it
trustworthy: it has been checked against a known answer, not merely fitted to a
decay that looked right.

### Running it

```python
import warnings
warnings.filterwarnings('ignore')
import numpy as np
from scipy.optimize import curve_fit

H = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
S = np.array([[1, 0], [0, 1j]], dtype=complex)
SDG = S.conj().T
GEN = {"H": H, "S": S, "Sdg": SDG}


def random_clifford(rng, length=4):
    """A random single-qubit Clifford as a 2x2 unitary."""
    U = np.eye(2, dtype=complex)
    for _ in range(length):
        U = GEN[rng.choice(list(GEN))] @ U
    return U


def depolarize_1q(rho, lam):
    """Depolarising channel: rho -> (1-lam) rho + lam Tr(rho) I/2."""
    return (1 - lam) * rho + lam * np.trace(rho) * np.eye(2) / 2
```

Two primitives: a random Clifford and the depolarising channel.

### The sequence and the fit

```python
def rb_survival(lam, lengths, trials, seed=0):
    """Mean survival probability at each sequence length m."""
    rng = np.random.default_rng(seed)
    out = []
    for m in lengths:
        total = 0.0
        for _ in range(trials):
            rho = np.array([[1, 0], [0, 0]], dtype=complex)   # |0><0|
            U = np.eye(2, dtype=complex)
            for _ in range(m):
                C = random_clifford(rng)
                U = C @ U                       # accumulate the product
                rho = C @ rho @ C.conj().T
                rho = depolarize_1q(rho, lam)   # noise after each Clifford
            rho = U.conj().T @ rho @ U          # invert the whole sequence
            total += np.real(rho[0, 0])         # survival probability
        out.append(total / trials)
    return np.array(out)


def fit_rb(lengths, surv, n=1):
    """Fit F(m) = A p^m + 1/2^n and return A, p and error per Clifford."""
    B = 1.0 / 2 ** n
    popt, _ = curve_fit(lambda m, A, p: A * p ** m + B, lengths, surv,
                        p0=[1 - B, 0.99], bounds=([0, 0], [1, 1]))
    A, p = popt
    return A, p, (2 ** n - 1) * (1 - p) / 2 ** n


```

With those four functions the whole experiment is five lines, and the point is
the last one: the fitted error rate is compared against the one that was
deliberately injected.

### Checking it against the known answer

```python
lengths = np.array([0, 2, 5, 10, 20, 40, 80, 160, 320])
surv = rb_survival(0.01, lengths, trials=200, seed=11)
A, p, epc = fit_rb(lengths, surv)
print(f"injected lambda = 0.01  ->  p = {p:.6f} (theory 0.990000), "
      f"EPC = {epc:.6f} (theory 0.005000)")
```

### What RB does not measure

This matters as much as what it does measure.

- **State preparation and measurement error is absorbed into $A$.** RB is
  deliberately insensitive to SPAM — which is a feature, since SPAM would
  otherwise dominate, but it means a device with terrible readout can report an
  excellent RB number.
- **It reports an average.** Twirling destroys the distinction between error
  mechanisms. A device with rare catastrophic errors and one with uniform small
  errors can give the same RB number, and they behave very differently in a real
  circuit.
- **It is blind to correlated and non-Markovian errors.** Twirling over
  *independent* random Cliffords cannot see errors that persist across gates.
- **It measures gates, not applications.** A good EPC does not imply a useful
  circuit will run.

For the last two reasons, RB is a **calibration** tool more than a capability
measure. It tells you the gates are good. It does not tell you the machine is
useful.

## Quantum volume

Quantum volume (QV) was proposed to fix exactly that: a single number capturing
whether a device can *run a circuit*.

### The definition

A device has $\text{QV} = 2^{d}$ if the largest **square** circuit it can run
reliably is $d$ qubits wide and $d$ layers deep — and $d+1$ fails.

The test circuits are random: each layer pairs the qubits randomly and applies a
random two-qubit gate to each pair. The pass criterion is that the
**heavy-output probability** — the probability of sampling an output whose ideal
probability is above the median — exceeds $2/3$ with $2\sigma$ confidence.

Because it is a power of two, the scale is steep:

| $d$ | $\text{QV} = 2^{d}$ |
|---|---|
| 4 | 16 |
| 6 | 64 |
| 8 | 256 |
| 10 | 1,024 |
| 16 | 65,536 |
| 20 | 1,048,576 |
| 32 | 4,294,967,296 |
| 64 | 18,446,744,073,709,551,616 |

A difference of 5 in $d$ is a factor of 32. It is worth internalising that scale
before comparing QV numbers.

### Verified: what QV actually demands

A $d \times d$ square circuit contains roughly $d^{2}/2$ two-qubit gates.
Requiring 90% success gives the per-gate error a device must achieve:

| $d$ | $\sim$ two-qubit gates | $\varepsilon$ needed for 90% |
|---|---|---|
| 4 | 8 | $1.31\times10^{-2}$ |
| 8 | 32 | $3.28\times10^{-3}$ |
| 16 | 128 | $8.20\times10^{-4}$ |
| 32 | 512 | $2.05\times10^{-4}$ |
| 64 | 2048 | $5.13\times10^{-5}$ |

Reaching $\text{QV} = 2^{64}$ requires per-gate errors near $5\times10^{-5}$ —
better than any device has sustained across a full register.

### The limitations

QV was a genuine advance and it has real weaknesses.

**It conflates three things.** Qubit count, gate fidelity, and connectivity all
feed the number. A device can improve connectivity and lose fidelity without QV
moving, and you cannot tell which from the number.

**It is a single number for a multi-dimensional capability.** Two devices with
the same QV can be good at completely different things.

**It saturates and is slow to move.** Because it demands $d$ good qubits *and*
depth $d$ *and* arbitrary connectivity, progress is gated on the worst of the
three.

**It is gameable.** QV rewards depth and width together; a device tuned for the
test does better on the test.

**It still does not certify usefulness.** Passing QV means the device ran a
random square circuit. That is a stronger statement than an RB number, and still
not a statement about any application.

The community has largely moved on to layer fidelity, CLOPS (circuit layer
operations per second), and application-oriented benchmarks — but QV remains
widely quoted, so it is worth understanding rather than dismissing.

## Choosing a benchmark

Objective 3, and the practical skill. The rule is: **match the benchmark to the
claimed capability.**

| Benchmark | Measures | Blind to |
|---|---|---|
| **T1 / T2** | Idle coherence | Gate quality entirely |
| **Randomised benchmarking** | Average gate fidelity | SPAM, correlated errors, usefulness |
| **Gate set tomography** | Full gate characterisation | Scales terribly — a few qubits only |
| **Quantum volume** | Width × depth on random circuits | Which of width/fidelity/connectivity limits |
| **Cross-entropy benchmarking** | Fidelity of a sampled distribution | Usefulness; needs classical comparison |
| **Application benchmarks** | Whether a real workload runs | Generality — tuned to one task |

### Given a claim

Given a claim, ask what would distinguish a true instance from a false one, and
pick the benchmark that discriminates:

**"Our gates are 99.9%."** Use RB, and ask for *two-qubit* RB on *all pairs*,
not the best pair. A mean over pairs hides the tail — as the
[calibration table](61_platform_comparison.md) showed, the worst qubit was ten
times worse than the median.

**"Our machine can run deep circuits."** QV or layer fidelity. RB will not
answer this, because RB sequences contain no structure and no depth-dependent
error accumulation.

**"Our machine solves problem X faster."** An application benchmark on X,
against the best known classical algorithm — not a proxy. This is the hardest
claim to verify and the one most often overclaimed; see
[the complexity lesson](63_complexity_classes.md) for what a speed-up
demonstration does and does not establish.

**"Our machine is better than theirs."** No single number settles this. Use a
suite, matched to the workload, and report the individual metrics rather than a
composite.

**"Our error-corrected logical qubit works."** A logical-error-versus-code-distance
curve, showing the logical error rate *falling* as the code grows. Below
threshold, bigger is better; above it, bigger is worse. The sign of that slope is
the whole result.

## Common misconceptions

- **"A 99.9% gate fidelity means a 1000-gate circuit works."** Only for
  independent errors. The [NISQ budget](62_nisq_limitations.md) is
  $Nd\varepsilon$; at $N=50$, $d=10$ and $\varepsilon=10^{-3}$ the success
  probability is about $0.7\%$.
- **"RB measures everything about the gates."** It measures the *average*
  fidelity after twirling. It is deliberately blind to SPAM and cannot see
  correlated errors.
- **"Quantum volume is the qubit count."** It is $2^{d}$ where $d$ is a circuit
  dimension, and it depends on fidelity and connectivity too.
- **"Higher QV means a more useful machine."** QV certifies a random square
  circuit. Two machines with equal QV can differ wildly on a real workload.
- **"Benchmarks are objective."** They are procedures with assumptions. The
  assumptions are what you should read.

## Exercises

1. In randomised benchmarking, why is the inverse of the sequence applied at
   the end? What would happen without it?

2. A device gives an RB decay with $p = 0.98$ on two qubits. Compute the error
   per Clifford.

3. From the verified table, roughly what per-gate error does $\text{QV} = 2^{16}$
   require?

4. Why is RB blind to state-preparation-and-measurement error, and is that a
   strength or a weakness?

5. You are told a device has excellent RB numbers but fails at QV. What is the
   most likely explanation?

6. A vendor claims their machine "solves optimisation problems faster than a
   classical computer." Which benchmark, and what comparison?

### Answers to 1–3

**1.** The inverse makes the ideal composite the identity, so the correct output
is always the initial state and no classical simulation is needed to know the
right answer. Without it, the expected output of a random Clifford sequence is a
random state that must be computed — which is precisely the exponentially hard
simulation RB is designed to avoid.

**2.** With $n = 2$: $\text{EPC} = \frac{2^2-1}{2^2}(1-p) = \frac{3}{4}\times 0.02 = 0.015$, so $1.5\%$ per Clifford.

**3.** From the verified table, $d = 16$ needs about $8.2\times10^{-4}$. (The
table gives the value for 90% success on a $d\times d$ circuit with roughly
$d^{2}/2$ two-qubit gates.)

### Answers to 4–6

**4.** SPAM error affects the survival probability identically at every sequence
length $m$, so it is absorbed into the prefactor $A$ and does not affect the
fitted decay rate $p$. It is a **strength** — otherwise readout error, which can
be several percent, would swamp the gate error being measured. It is also a
**weakness**, because a device with excellent RB and terrible readout will
nonetheless fail on real circuits. The number is correct about what it measures
and silent about what it does not.

**5.** The most likely explanation is that the gates are good in isolation but
something else limits circuit execution: crosstalk between simultaneous gates,
restricted connectivity forcing SWAPs, or errors that accumulate with depth.
RB sequences are unstructured and shallow in effect; QV charges for width and
depth together. Both numbers can be right at once — this is the standard
situation, not a contradiction.

**6.** An application benchmark: run the vendor's actual optimisation workload
on their machine and compare against the **best known classical algorithm** for
that same problem, on comparable time budgets — not against a brute-force
baseline, and not against a different quantum machine. Report wall-clock time
and solution quality. Neither RB nor QV speaks to this claim at all; see
[the complexity lesson](63_complexity_classes.md) for the questions you should
ask before accepting any speed-up claim.

## Summary

- **Benchmarking is hard** because you cannot check the answer, errors are not
  independent, and scalar metrics invite gaming.
- **Randomised benchmarking** applies $m$ random Cliffords then the inverse, so
  the ideal output is always the initial state. Fit $F(m) = A p^{m} + 2^{-n}$ and
  report $\text{EPC} = \frac{2^n-1}{2^n}(1-p)$.
- Verified: RB **recovers an injected depolarising parameter exactly** —
  $p = 1-\lambda$ and $\text{EPC} = \lambda/2$ to 0.00% across four error rates,
  with the decay curve matching theory at every point. That is why it is
  trusted.
- **RB is blind to SPAM** (absorbed into $A$), reports an **average** (twirling
  destroys the error mechanism), and **cannot see correlated errors**. It
  calibrates gates; it does not certify usefulness.
- **Quantum volume** is $2^{d}$ for the largest successful square $d\times d$
  circuit, passing at heavy-output probability above $2/3$. Verified: $\text{QV} = 2^{64}$ needs per-gate errors near $5\times10^{-5}$.
- **QV's limitations**: it conflates qubit count, fidelity and connectivity; it
  is a scalar for a multi-dimensional capability; it is gameable; and it still
  does not certify an application.
- **Choose the benchmark that discriminates the claim.** Gate quality → RB on all
  pairs. Depth → QV or layer fidelity. Application → the application, against the
  best classical algorithm. Error correction → logical error versus code
  distance, with the sign of the slope as the result.

## References

- Knill, E. et al., "Randomized benchmarking of quantum gates" (PRA, 2008) — the
  protocol.
- Magesan, E., Gambetta, J. M. & Emerson, J., "Scalable and robust randomized
  benchmarking of quantum processes" (PRL, 2011) — the $2^{n}$ floor and the
  EPC conversion.
- Cross, A. W., Bishop, L. S., Sheldon, J. A., Nation, P. D. & Gambetta, J. M.,
  "Validating quantum computers using randomized model circuits" (2019) — the
  quantum volume definition.
- Emerson, J., Alicki, R. & Życzkowski, K., "Scalable noise estimation with
  random unitary operators" — the twirling argument.
- Proctor, T. et al., "Measuring the capabilities of quantum computers"
  (Nature Physics, 2022) — application-oriented benchmarks and a critique of
  volumetric metrics.
- [NISQ Limitations](62_nisq_limitations.md) — the $Nd\varepsilon$ budget that
  benchmarks feed into.
- [Calibrated Noise Models and Connectivity Topologies](61_platform_comparison.md)
  — where the per-gate error figures come from, and the spread across a device.
- [BQP, P, NP and BPP](63_complexity_classes.md) — what a speed-up claim does
  and does not establish.
- [Error Mitigation](55_error_mitigation.md) — what to do with a device whose
  benchmark numbers are not yet good enough.

---

**Next:** [Quantum Ecosystem](65_quantum_ecosystem.md)
