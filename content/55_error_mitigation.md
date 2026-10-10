# Error Mitigation: ZNE, PEC and Readout Correction

Error correction asks for the state itself, and the price is the enormous qubit
overhead of the last four lessons. Error mitigation asks for something much
smaller: the correct **number**. If all you need is $\langle O \rangle$ to three
decimal places, you may not need to encode anything — you can run the noisy
circuit, run it again in a deliberately noisier version, and extrapolate.

This is the approach used on essentially every NISQ result that reports a
chemical accuracy or a ground-state energy, and it is the subject of this
lesson.

## Learning objectives

By the end of this lesson you should be able to:

- **Explain** the difference between error mitigation and error correction.
- **Apply** zero-noise extrapolation to a noisy expectation value.
- **Construct and apply** a readout error correction matrix.

## Prerequisites

[Quantum Noise and Decoherence](09_quantum_noise.md). Mitigation
post-processes noisy results; it needs a noise model first.

## Mitigation versus correction

The distinction is not a matter of degree. The two techniques produce different
kinds of object.

|  | Error correction | Error mitigation |
|---|---|---|
| **Output** | the corrected **quantum state** | a corrected **expectation value** |
| **Where it acts** | during the computation | after the measurement, on classical data |
| **Qubit overhead** | large ($d^2$ per logical qubit) | none — same qubits |
| **Shot overhead** | none beyond syndrome extraction | substantial, and grows with depth |
| **Scales to long circuits?** | yes, polylogarithmically | no — cost grows exponentially |
| **Needs a noise model?** | no | yes for PEC and readout; a noise knob for ZNE |
| **Guarantee** | a theorem, below threshold | none — heuristic, unchecked on real output |

The most important row is the first. Error correction gives you back a quantum
state, which you can then keep computing with. Error mitigation gives you a
classical number, and the quantum part of the computation is over. You cannot
mitigate partway through a circuit and carry on.

That is why mitigation does not scale. Every mitigation method below trades
**bias for variance**: it removes a systematic error from the estimate at the
cost of making the estimate noisier. As circuits get deeper the variance cost
grows exponentially, and eventually the method needs more samples than you can
take. Error correction has a theorem behind it; mitigation has an empirical
improvement that must be checked case by case.

## Zero-noise extrapolation

### The idea

Suppose the expectation value you want, as a function of the noise strength
$\lambda$, is smooth:

$$E(\lambda) = E(0) + c_1\lambda + c_2\lambda^2 + \cdots$$

You cannot run at $\lambda = 0$. But you *can* run at $\lambda = 1, 3, 5$,
measure $E$ at each, fit a curve, and evaluate it at $\lambda = 0$. That value is
the zero-noise extrapolation.

The clever part is how to *increase* the noise on demand. **Unitary folding**
replaces the circuit $C$ with

$$C \;\longrightarrow\; C\,(C^\dagger C)^k$$

which applies the unitary $2k+1$ times. Since $C^\dagger C = I$, the folded
circuit computes exactly the same thing — in the absence of noise, folding is
invisible. With noise, running the gates $2k+1$ times as often multiplies the
error by roughly $\lambda = 2k+1$. So folding gives a genuine, calibrated noise
knob.

### A practical warning

Folding is invisible to an optimising compiler. If you fold and then transpile,
the transpiler cancels $C^\dagger C$ back to nothing and the noise scaling
disappears — the extrapolated result is then identical to the raw one. Transpile
first, then fold. This is a real failure mode and it is silent.

### Verified

On a two-qubit circuit (two $RY$ gates, one $RX$, two CNOTs) measured against
$O = 1.0\,ZI + 0.6\,IZ + 0.4\,ZZ$, with depolarising noise at 1% on
single-qubit gates and 3% on CNOTs. The table uses exact expectation values, so
the improvement shown is pure bias correction with no shot noise:

| Method | $\langle O \rangle$ | Error | Improvement |
|---|---|---|---|
| Ideal (no noise) | 1.085661 | — | — |
| Raw ($\lambda = 1$) | 1.011469 | $-0.074192$ | — |
| ZNE linear ($\lambda = 1, 3$) | 1.078276 | $-0.007385$ | 10.0× |
| ZNE quadratic ($\lambda = 1,3,5$) | 1.084856 | $-0.000805$ | 92.2× |
| ZNE cubic ($\lambda = 1,3,5,7$) | 1.085571 | $-0.000091$ | 817× |
| ZNE exponential ($\lambda = 1,3$) | 1.085719 | $+0.000058$ | 1289× |

The underlying noisy values decay as the folding depth grows — $\langle O \rangle$ falls from 1.011469 at $\lambda = 1$ to 0.660987 at $\lambda = 7$ — and
the extrapolation recovers the ideal to five decimal places.

Higher-order extrapolation wins here because the noise model is depolarising and
the true curve happens to be close to exponential. **That is a property of this
example, not a general rule.** With a poorly-matched fit function or a
non-smooth noise landscape, extrapolation can overshoot or amplify error. There
is no guarantee of improvement.

### Implementing it

```python
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Statevector, SparsePauliOp
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

OBS = SparsePauliOp.from_list([("ZI", 1.0), ("IZ", 0.6), ("ZZ", 0.4)])


def base_circuit():
    qc = QuantumCircuit(2)
    qc.ry(0.7, 0); qc.cx(0, 1); qc.rx(0.4, 1); qc.cx(0, 1); qc.ry(0.7, 0)
    return qc


noise = NoiseModel()
noise.add_all_qubit_quantum_error(depolarizing_error(0.01, 1), ["ry", "rx"])
noise.add_all_qubit_quantum_error(depolarizing_error(0.03, 2), ["cx"])
sim = AerSimulator(method="density_matrix", noise_model=noise)

# Transpile FIRST. Folding after transpilation would be undone by the
# optimiser, which cancels the C^dagger C pairs and removes the noise scaling.
base = transpile(base_circuit(), sim, optimization_level=0,
                 basis_gates=noise.basis_gates + ["save_expectation_value"])


def fold(qc, k):
    """C -> C (C^dag C)^k. Same unitary, lambda = 2k+1 times the noise."""
    out = qc.copy()
    for _ in range(k):
        out = out.compose(qc.inverse()).compose(qc)
    return out


def expect(qc):
    m = qc.copy()
    m.save_expectation_value(OBS, qubits=[0, 1], label="exp")
    return sim.run(m, shots=1).result().data()["exp"].real


ideal = Statevector(base_circuit()).expectation_value(OBS).real
lam = [1, 3, 5]
vals = [expect(fold(base, (L - 1) // 2)) for L in lam]
E1, E3, E5 = vals

linear = (3 * E1 - E3) / 2                          # 2-point Richardson
quadratic = (15 / 8) * E1 - (5 / 4) * E3 + (3 / 8) * E5   # 3-point
print(f"ideal {ideal:.6f}  raw {E1:.6f}  "
      f"linear {linear:.6f}  quadratic {quadratic:.6f}")
```

### Why the coefficients sum to one

The coefficients in the quadratic estimator are the Lagrange basis polynomials
evaluated at $\lambda = 0$. They sum to $\tfrac{15}{8} - \tfrac{5}{4} + \tfrac{3}{8} = 1$, which is what makes the extrapolation exact for any quadratic
in $\lambda$.

### The cost

Extrapolation amplifies statistical noise. If each $E(\lambda_i)$ is estimated
from the same number of shots with variance $\sigma^2$, then

$$\mathrm{Var}[E_{\text{ZNE}}] = \sigma^2 \sum_i c_i^2$$

with $c_i$ the extrapolation coefficients. For the estimators above:

| Estimator | Coefficients | $\sum c_i^2$ | Std. error multiplier |
|---|---|---|---|
| Raw | $(1)$ | 1.00 | 1.00× |
| Linear | $(\tfrac32, -\tfrac12)$ | 2.50 | 1.58× |
| Quadratic | $(\tfrac{15}{8}, -\tfrac54, \tfrac38)$ | 5.22 | 2.28× |

So the quadratic fit cuts the bias by 92× but multiplies the statistical error by
2.28×, meaning about $5.22$ times as many shots to reach the same precision. That
is usually a good trade — but it is a trade, and the bias reduction is only worth
it while the bias is larger than the noise you are amplifying.

## Probabilistic error cancellation

ZNE removes bias by extrapolation, which assumes the noise curve is smooth. PEC
removes it *exactly*, at the cost of randomness.

### The idea

Suppose the noisy implementation of a gate $G$ is $\Lambda \circ G$, where
$\Lambda$ is the noise channel. If you could apply $\Lambda^{-1}$ you would
recover $G$ perfectly. $\Lambda^{-1}$ is not a physical channel — it is not
completely positive — but it **can** be written as a linear combination of
physical operations with coefficients that may be negative:

$$\Lambda^{-1} = \sum_i a_i\,\mathcal{B}_i, \qquad \sum_i a_i = 1, \quad a_i \in \mathbb{R}$$

Negative coefficients cannot be probabilities, hence *quasi*-probabilities. The
trick is to sample the operation $\mathcal{B}_i$ with probability
$|a_i|/\gamma$, where

$$\gamma = \sum_i |a_i| \;\ge\; 1$$

and multiply the measured outcome by $\gamma\,\mathrm{sign}(a_i)$. The result is
an unbiased estimator of the ideal expectation value.

### Verified coefficients

For the depolarising channel, the coefficients can be computed exactly. In the
Pauli transfer matrix representation $\Lambda$ is $\mathrm{diag}(1, 1-p, 1-p, 1-p)$, and conjugation by a Pauli is also diagonal, so everything decouples:

$$\Lambda = (1 - \tfrac{3p}{4})[\mathbb{1}] + \tfrac{p}{4}\big([X] + [Y] + [Z]\big)$$

$$\Lambda^{-1} = \Big(1 + \tfrac{3p}{4(1-p)}\Big)[\mathbb{1}] - \tfrac{p}{4(1-p)}\big([X] + [Y] + [Z]\big)$$

$$\gamma = 1 + \frac{3p}{2(1-p)}$$

Verified numerically — $\Lambda^{-1}\Lambda$ equals the identity to machine
precision:

| $p$ | $a_{\mathbb{1}}$ | $a_{X,Y,Z}$ | $\gamma$ | $\gamma^2$ |
|---|---|---|---|---|
| 0.01 | $+1.007576$ | $-0.002525$ | 1.015152 | 1.030533 |
| 0.05 | $+1.039474$ | $-0.013158$ | 1.078947 | 1.164127 |
| 0.10 | $+1.083333$ | $-0.027778$ | 1.166667 | 1.361111 |

### Computing the coefficients

```python
import numpy as np


def pec_coefficients(p):
    """Quasi-probability weights for the inverse of a depolarising channel.

    In the Pauli transfer matrix basis, depolarising is diag(1, 1-p, 1-p, 1-p)
    and conjugation by P is diagonal too, so the inverse decomposes over the
    four Pauli conjugations.  gamma is the one-norm of the weights and sets
    the sampling cost: reaching a fixed precision needs gamma**2 more shots.
    """
    a_identity = 1 + 3 * p / (4 * (1 - p))
    a_pauli = -p / (4 * (1 - p))
    return a_identity, a_pauli


def gamma(p):
    a_identity, a_pauli = pec_coefficients(p)
    return abs(a_identity) + 3 * abs(a_pauli)


for p in (0.01, 0.05, 0.10):
    a_identity, a_pauli = pec_coefficients(p)
    print(f"p={p:.2f}  a_I={a_identity:+.6f}  a_P={a_pauli:+.6f}  "
          f"gamma={gamma(p):.6f}  gamma^2={gamma(p) ** 2:.6f}")
```

### Verified: unbiased, but noisier

Monte Carlo on a single qubit prepared by $RY(\theta)$ with $\theta = 0.9$ and
$p = 0.05$, measuring $\langle Z \rangle$, using two million samples:

|  | Mean | Bias | Variance |
|---|---|---|---|
| Ideal | 0.621610 | — | — |
| Unmitigated | 0.589599 | $-0.032011$ | 0.652373 |
| PEC | 0.621606 | $-0.000004$ | 0.777733 |

The bias is gone — reduced by a factor of about 8000. The variance rose from
0.652 to 0.778, a ratio of 1.192, matching the theoretical prediction
$(\gamma^2 - \langle O \rangle^2)/(1 - \langle O \rangle_{\text{noisy}}^2) = 1.194$. So PEC needs about $1.19\times$ the shots for the same precision at this
$p$.

### The fatal scaling

That $1.19\times$ is *per gate*. For a circuit with $N$ gates the gammas
multiply, and the sampling cost is $\gamma^{2N}$:

| $p$ per gate | $\gamma$ | $N = 10$ | $N = 100$ | $N = 1000$ |
|---|---|---|---|---|
| 0.001 | 1.00150 | 1.02 | 1.16 | 4.48 |
| 0.010 | 1.01515 | 1.16 | 4.50 | $3.40\times 10^{6}$ |
| 0.050 | 1.07895 | 2.14 | $1.995\times 10^{3}$ | $1.00\times 10^{33}$ |

At $p = 0.01$ a hundred-gate circuit costs $4.5\times$ more sampling; at a
thousand gates it costs $3.4\times 10^{6}$. **PEC is exponential in circuit
depth.** Compare with fault-tolerant error correction, whose overhead grows only
polylogarithmically. That is the quantitative form of "mitigation does not
scale".

PEC also requires an accurate noise model — the coefficients are derived from
$\Lambda$, so if your model of $\Lambda$ is wrong the estimator is biased by
exactly the amount you got wrong. This is a qualitatively stronger requirement
than ZNE, which only needs the ability to *scale* the noise.

## Readout error correction

Measurement is often the noisiest operation on a real device, and it is the
easiest to correct — because the errors happen after the quantum part is over.

### The construction

On $n$ qubits, define the $2^n \times 2^n$ **calibration matrix**

$$M_{ij} = P(\text{measure } i \mid \text{prepared } j)$$

Build it column by column: prepare the computational basis state $|j\rangle$,
measure, and the resulting distribution is column $j$. Each column sums to 1 by
construction.

A circuit that would produce the true distribution $p$ instead yields

$$p_{\text{meas}} = M p$$

so correcting is just inverting:

$$p_{\text{corrected}} = M^{-1} p_{\text{meas}}$$

### Verified

Two qubits with $P(1|0) = 0.03$ and $P(0|1) = 0.05$, calibrated with 40000
shots per basis state, tested on a Bell state whose ideal distribution is
$(0.5, 0, 0, 0.5)$:

| Basis | Ideal | Raw | $M^{-1}$ corrected |
|---|---|---|---|
| 00 | 0.5000 | 0.4716 | 0.5000 |
| 01 | 0.0000 | 0.0370 | $-0.0009$ |
| 10 | 0.0000 | 0.0396 | 0.0006 |
| 11 | 0.5000 | 0.4517 | 0.5003 |

Total variation distance from ideal falls from 0.0767 to 0.00087 — an
improvement of 88×.

Two things in that table deserve comment. The corrected distribution still sums
to 1.000000, which is guaranteed: since every column of $M$ sums to 1, the
inverse preserves the sum. But the corrected entry for 01 is **$-0.0009$**. A
negative probability is not a probability. $M^{-1}$ is not a stochastic map and
the output is not guaranteed to be a valid distribution, though the deviation
here is within shot noise of zero.

### Implementing it

```python
import numpy as np


def calibration_matrix(p10, p01, n_qubits):
    """M[i][j] = P(measure i | prepared j), assuming independent,
    identical readout errors on every qubit, so M = m^(x)n.

    p10 = P(measure 1 | true 0), p01 = P(measure 0 | true 1).
    """
    m = np.array([[1 - p10, p01],
                  [p10,     1 - p01]])
    M = np.array([[1.0]])
    for _ in range(n_qubits):
        M = np.kron(m, M)
    return M


def readout_correct(measured, M):
    """Invert the readout error.  Note: the result is not guaranteed to be a
    non-negative, normalised probability distribution."""
    return np.linalg.inv(M) @ measured


M = calibration_matrix(p10=0.03, p01=0.05, n_qubits=2)
ideal = np.array([0.5, 0.0, 0.0, 0.5])       # Bell state  (|00> + |11>)/sqrt2
measured = M @ ideal                          # what the device would report

corrected = readout_correct(measured, M)
print("raw      ", np.round(measured, 4))
print("corrected", np.round(corrected, 4))
print("sum of corrected:", round(corrected.sum(), 6))
```

The tensor-product form used in the code assumes readout errors are independent
across qubits. Verified against a full calibration on the simulator: the two
matrices agree to within 0.0017, which is shot noise at 40000 shots. The
assumption is not exact on real hardware, but it is what makes the method
tractable, as the next section shows.

Note that the code above applies the model and then inverts it exactly, so it
recovers the ideal distribution perfectly. That is the mechanism in isolation,
without shot noise. The table earlier came from an actual simulation with a
finite 40000 shots per calibration circuit, which is why it shows a residual
error of 0.00087 and a small negative entry rather than a perfect recovery.

### Why full readout correction does not scale

| Qubits | Calibration circuits | Matrix entries |
|---|---|---|
| 2 | 4 | 16 |
| 5 | 32 | 1024 |
| 10 | 1024 | 1048576 |
| 20 | 1048576 | $1.1\times 10^{12}$ |
| 50 | $1.1\times 10^{15}$ | $1.3\times 10^{30}$ |

Full readout correction needs $2^n$ calibration circuits and a $2^n \times 2^n$
matrix. At 20 qubits that is a million circuits and a trillion-entry matrix —
already impractical. The tensor-product approximation needs only $2n$ circuits
and never forms the big matrix, which is why it is what gets used in practice,
and why it is only an approximation when readout errors are correlated.

## The common thread

All three methods trade the same thing:

| Method | Bias | Variance / cost | Needs |
|---|---|---|---|
| ZNE | reduced, not eliminated | $\sum c_i^2 \approx 2.5\text{–}5.2$ more shots | a noise-scaling knob |
| PEC | eliminated (exactly) | $\gamma^{2N}$ more shots — exponential | an accurate noise model |
| Readout | reduced | modest, but $2^n$ calibration | per-device calibration |

ZNE is cheap and approximate. PEC is exact and exponential. Readout correction
is cheap and works only on the easiest error to fix. None of them gives you back
a quantum state, and none of them scales to deep circuits.

The reason is structural. Mitigation post-processes the output of a computation
that has already been corrupted, and the number of ways a deep circuit can go
wrong grows with its depth. Error correction interrupts the corruption while it
is still small and correctable, and that is the only approach with a theorem
behind it.

## Limitations

- **No theorem.** Every method here is a heuristic. Extrapolation can overshoot;
  PEC is only as good as its noise model; readout correction assumes
  independence.
- **Exponential in depth.** PEC's $\gamma^{2N}$ is the clearest case, but the
  same shape appears in all of them, because the variance cost of correcting a
  circuit grows multiplicatively with its size.
- **Assumes noise is unchanged between calibration and use.** Real devices drift.
  A calibration matrix from this morning may be wrong this afternoon, and a
  $\gamma$ computed from a characterised $\Lambda$ is wrong if $\Lambda$ moved.
- **Only expectation values.** If you need the state — as in most algorithms
  that feed a result into further quantum processing — mitigation gives you
  nothing.
- **Folding is not free.** Unitary folding multiplies the gate count by
  $\lambda$, so the $\lambda = 7$ point costs seven times the gates and is
  exposed to seven times the decoherence. The noise scaling is only
  approximately linear in $\lambda$.

## Common misconceptions

- **"Mitigation is a cheap version of correction."** It is a different thing.
  Correction returns a state; mitigation returns a number. Mitigation cannot be
  applied mid-circuit.
- **"Mitigation removes the error."** It removes *bias* from an estimator and
  pays for it in variance. The total error can go up if the bias was already
  smaller than the statistical noise.
- **"PEC is exact, so it is the best method."** It is exact only if the noise
  model is exact, and its cost is exponential in circuit depth. For a
  thousand-gate circuit at $p = 0.01$ the overhead is $3.4 \times 10^6$.
- **"Extrapolating to zero noise gives the exact answer."** It gives the value
  your fitted curve predicts at zero. If the true $E(\lambda)$ is not well
  approximated by the fit function, the answer is wrong, and the fit cannot tell
  you.
- **"A negative corrected probability means the code is buggy."** It means
  $M^{-1}$ is not a stochastic map, which is expected. Clipping negatives to
  zero reintroduces bias.
- **"Readout correction scales if I just calibrate more qubits."** It needs
  $2^n$ circuits and a $2^n \times 2^n$ matrix. At 20 qubits that is a million
  circuits.

## Exercises

1. Explain in one sentence why error mitigation cannot be used to protect a
   quantum subroutine that feeds into further quantum processing.

2. A Richardson extrapolation uses $\lambda = 1$ and $\lambda = 3$ and gives
   $E(1) = 0.80$, $E(3) = 0.60$. What is the extrapolated $E(0)$? Show the
   coefficients.

3. Using $\gamma = 1 + 3p/(2(1-p))$, compute $\gamma$ and the per-gate sampling
   overhead $\gamma^2$ at $p = 0.02$. Then compute the total overhead
   $\gamma^{2N}$ for a circuit of 50 such gates.

4. You fold a circuit, transpile it, and then run ZNE. The extrapolated result
   is identical to the raw result. What went wrong, and how do you fix it?

5. A corrected readout distribution contains the entry $-0.004$. Is this a bug?
   What should you do about it, and why is clipping it to zero not free?

6. Why does readout correction need $2^n$ calibration circuits in general, and
   what does the tensor-product approximation assume to avoid that?

### Answers to 1–3

**1.** Mitigation returns a corrected *classical expectation value*, not a
corrected quantum state, so there is nothing quantum left to feed into the next
stage — the computation has already been measured.

**2.** The two-point Richardson estimator is $E(0) = \tfrac32 E(1) - \tfrac12 E(3)$:

$$E(0) = \tfrac32(0.80) - \tfrac12(0.60) = 1.20 - 0.30 = 0.90$$

The coefficients $\tfrac32$ and $-\tfrac12$ sum to 1, which is what makes the
estimator exact for any function that is linear in $\lambda$.

**3.** $\gamma = 1 + 3(0.02)/(2 \times 0.98) = 1 + 0.06/1.96 = 1.030612$. Then
$\gamma^2 = 1.062162$, about $6.2\%$ more shots per gate. For $N = 50$ gates:

$$\gamma^{2N} = (1.030612)^{100} = e^{100 \ln 1.030612} = e^{3.015} \approx 20.4$$

So roughly twenty times the sampling for the whole circuit. Note the base of the
exponential is $\gamma^2$, not $\gamma$ — the cost is the *variance*, and
variance scales as $\gamma^2$ per gate.

### Answers to 4–6

**4.** The transpiler cancelled the folding. $C(C^\dagger C)^k$ is the identity
composition, and an optimising compiler removes $C^\dagger C$ pairs, leaving the
original circuit — so all your "noise-scaled" points were actually run at
$\lambda = 1$ and the extrapolation of three identical numbers is just that
number. Fix: transpile the circuit to the device basis *first*, then apply the
folding, and do not re-optimise afterwards.

**5.** Not a bug. $M^{-1}$ is the inverse of a stochastic matrix, which is not
itself stochastic, so negative entries are expected in principle and appear in
practice — the verified example produced $-0.0009$ for the 01 basis state. The
honest options are to report it, to use a constrained fit that enforces
non-negativity, or to renormalise. Clipping to zero is the common choice but it
is **not free**: it changes the estimate and reintroduces exactly the bias you
were trying to remove, in an amount you have not measured.

**6.** In general, readout errors can be correlated: the probability of
misreading qubit $i$ may depend on the state of qubit $j$. Capturing that
requires a separate column of $M$ for each of the $2^n$ prepared basis states,
and $M$ itself has $2^n \times 2^n = 4^n$ entries. The tensor-product
approximation assumes each qubit's readout error is **independent** of the
others, so $M = m^{\otimes n}$ for the single-qubit matrix $m$. Then $m$ is
calibrated with 2 circuits per qubit, $2n$ in total, and the full matrix never
has to be formed. It is an approximation, and on real hardware with crosstalk
during measurement it is not exact.

## Summary

- **Mitigation returns a corrected number; correction returns a corrected
  state.** That is the whole distinction, and it is why mitigation cannot be
  applied mid-circuit or scaled arbitrarily.
- All three methods trade **bias for variance**. None has a theorem behind it.
- **ZNE** scales the noise by unitary folding, $C \to C(C^\dagger C)^k$ with
  $\lambda = 2k+1$, then extrapolates the fitted $E(\lambda)$ to $\lambda = 0$.
  Verified: bias cut by 10× (linear), 92× (quadratic), 817× (cubic) on a
  two-qubit depolarising example, at a variance cost of 2.5–5.2× the shots.
  Transpile *before* folding, or the optimiser cancels it.
- **PEC** writes $\Lambda^{-1}$ as a quasi-probability sum over physical
  operations, samples with probability $|a_i|/\gamma$, and rescales by
  $\gamma\,\mathrm{sign}(a_i)$. Verified unbiased: bias $-0.0320 \to -0.000004$
  at a variance ratio of 1.192, matching theory. Cost is $\gamma^{2N}$ — at
  $p = 0.01$ and $N = 1000$ that is $3.4 \times 10^6$.
- **Readout correction** builds $M_{ij} = P(i \mid j)$, then applies $M^{-1}$.
  Verified: total variation distance from ideal cut from 0.0767 to 0.00087,
  88×. $M^{-1}$ is not stochastic, so negative entries can appear — one did.
  Full calibration costs $2^n$ circuits and a $4^n$-entry matrix, which is why
  the tensor-product approximation is used in practice.
- Mitigation is the right tool for shallow circuits today. It is not a path to
  scalable quantum computing; [fault tolerance](54_threshold_theorem.md) is.

## References

- Temme, K., Bravyi, S. & Gambetta, J. M. — probabilistic error cancellation.
- Li, Y. & Benjamin, S. C. — unitary folding and Richardson extrapolation.
- Giurgica-Tiron, T., Hindy, Y., LaRose, R., Mari, A. & Zeng, W. J. — a
  comparison of zero-noise extrapolation strategies.
- Van den Berg, E., Minev, Z. K. & Temme, K. — readout error mitigation and the
  tensor-product approximation.
- Endo, S., Cai, Z., Benjamin, S. C. & Yuan, X. — a broad review of mitigation
  methods and their limits.
- Cai, Z. et al. — the exponential cost of error mitigation.
- [Quantum Noise and Decoherence](09_quantum_noise.md) — the noise
  channels these methods invert.
- [Threshold Theorem and Fault Tolerance](54_threshold_theorem.md) — the
  approach whose overhead is polylogarithmic rather than exponential.
- [NISQ Limitations](62_nisq_limitations.md) — where mitigation fits in the
  near-term picture.

---

**Next:** [Superconducting Qubits](56_superconducting_qubits.md)
