# Amplitude Estimation

Grover's algorithm boosts the probability of finding a good state.
Amplitude estimation answers the harder and more useful question: *how many*
good states are there? It estimates an unknown probability $a$ with a
**quadratic** speed-up over classical sampling, and it does it by turning
Grover's operator into a phase-estimation problem. This is also the component
that makes quantum approaches to Monte Carlo and numerical integration
interesting.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** the amplitude estimation circuit from the Grover operator.
- **Explain** the quadratic improvement in estimation error, and state the query
  counts for both approaches.
- **Relate** amplitude estimation to quantum phase estimation, and identify the
  eigenphase that carries the answer.

## Prerequisites

This lesson assumes [Grover's Algorithm](06_grover.md) — specifically the
Grover operator $Q$ and the idea of amplitude amplification — and
[Quantum Phase Estimation](32_phase_estimation.md).

## The problem

A circuit $A$ prepares a state

$$A|0\rangle = \sin\theta\,|\text{good}\rangle + \cos\theta\,|\text{bad}\rangle$$

where $|\text{good}\rangle$ is the subspace we care about. The probability of
measuring a good outcome is

$$a = \sin^2\theta$$

Estimate $a$.

Classically you prepare and measure repeatedly: after $N$ samples your estimate
has standard error $\sqrt{a(1-a)/N}$, so achieving additive error $\varepsilon$
needs $O(1/\varepsilon^2)$ samples. Amplitude estimation achieves the same error
in $O(1/\varepsilon)$ — a **quadratic** improvement.

## Intuition

### Reusing Grover as a rotation

Grover's operator $Q$ rotates the state within the two-dimensional span of
$|\text{good}\rangle$ and $|\text{bad}\rangle$. A rotation is characterised by
its angle, and that angle is $2\theta$ — determined by exactly the quantity we
want to learn.

So instead of *sampling* the rotation (measure, count, repeat), we *measure its
angle*. Angles are what phase estimation extracts. That substitution — sampling
a probability versus measuring a phase — is where the quadratic speed-up comes
from.

### From eigenphase to amplitude

Take $Q = -A S_0 A^\dagger S_{\text{good}}$, where $S_0$ flips the $|0\rangle$
state and $S_{\text{good}}$ flips the good subspace. Its two eigenvalues are

$$e^{\pm 2i\theta}$$

which was verified directly: for $\theta = 0.3, 0.7, 1.1$ the eigenphases come
out at exactly $\pm0.6$, $\pm1.4$ and $\pm2.2$ respectively — precisely
$\pm 2\theta$.

Run phase estimation on $Q$, recover the eigenphase $\pm2\theta$, halve it, and
$a = \sin^2\theta$ follows.

## The circuit

### Stages

1. Prepare $A|0\rangle$.
2. Apply controlled powers of $Q$ onto a $t$-qubit estimation register.
3. Inverse QFT on the estimation register.
4. Measure to obtain $m$; then $\theta \approx \pi m / 2^t$ and
   $a \approx \sin^2(\pi m/2^t)$.

Note the $\pm$ symmetry: the two eigenvalues are complex conjugates, so the
measurement cannot distinguish $+2\theta$ from $-2\theta$. That is harmless —
we take the absolute value, since $a = \sin^2\theta$ is the same for both
branches.

### Recovering the amplitude

From a measured integer $m$ with $t$ estimation bits:

$$\omega = \frac{m}{2^t}, \qquad \phi = 2\pi\omega, \qquad \theta = \frac{\min(\phi,\, 2\pi - \phi)}{2}, \qquad a = \sin^2\theta$$

The folding by $\min(\phi, 2\pi-\phi)$ handles the $\pm$ symmetry.

### Verified accuracy

Using the exact phase-estimation outcome distribution and taking the most
likely outcome:

| True $\theta$ | True $a$ | $t$ | Best $m$ | Estimated $a$ | Absolute error |
|---|---|---|---|---|---|
| 0.30 | 0.087332 | 4 | 14 | 0.146447 | $5.9\times10^{-2}$ |
| 0.30 | 0.087332 | 6 | 6 | 0.084265 | $3.1\times10^{-3}$ |
| 0.30 | 0.087332 | 10 | 926 | 0.087705 | $3.7\times10^{-4}$ |
| 0.70 | 0.415016 | 6 | 50 | 0.402455 | $1.3\times10^{-2}$ |
| 0.70 | 0.415016 | 8 | 199 | 0.414519 | $5.0\times10^{-4}$ |
| 1.10 | 0.794251 | 8 | 90 | 0.797850 | $3.6\times10^{-3}$ |
| 1.10 | 0.794251 | 10 | 359 | 0.795380 | $1.1\times10^{-3}$ |

The error shrinks as more estimation qubits are added, and the direction of
travel is what matters: each additional bit refines the answer.

## The quadratic speed-up

### Query counts

| Target error $\varepsilon$ | Classical $O(1/\varepsilon^2)$ | Quantum $O(1/\varepsilon)$ |
|---|---|---|
| $0.1$ | 100 | 10 |
| $0.01$ | 10,000 | 100 |
| $0.001$ | 1,000,000 | 1000 |

The quantum column uses $O(1/\varepsilon)$ applications of $Q$, and each
application of $Q$ includes one application of $A$. So the count is measured in
*calls to the state-preparation routine*, which is the right accounting.

### Where the improvement comes from

Classical sampling estimates a probability from the **statistics of outcomes**,
so the error falls as $1/\sqrt{N}$. Amplitude estimation measures a **phase**,
and phase estimation resolves a phase to $1/2^t$ using $O(2^t)$ coherent
applications. Composing: $2^t$ applications give error $1/2^t$, so error
$\varepsilon$ costs $1/\varepsilon$ — one power better.

## Relation to phase estimation

Amplitude estimation *is* phase estimation applied to the Grover operator. The
mapping is:

| Phase estimation | Amplitude estimation |
|---|---|
| Unitary $U$ | Grover operator $Q$ |
| Eigenphase $\varphi$ | $\pm 2\theta$ |
| Register size $t$ | $t$ estimation qubits |
| Output | $m$, giving $\theta$ and hence $a = \sin^2\theta$ |

Everything known about phase estimation carries over: the $4/\pi^2$ worst-case
success bound, the need for $t$ bits to get $t$ bits of precision, and the
requirement of $O(2^t)$ controlled applications.

The one genuine difference is the $\pm$ ambiguity in the eigenphase, which is
resolved trivially here because $a = \sin^2\theta$ is even in $\theta$.

## Limits and caveats

### It needs coherent powers of $Q$

The circuit requires controlled-$Q^{2^k}$, and $Q^{2^k}$ means $2^k$
applications of $Q$ — each containing an application of $A$. The total circuit
depth grows as $O(2^t)$, which on near-term hardware is exactly the resource
you do not have. This is why **amplitude estimation without phase estimation**
(relying on shorter circuits and classical post-processing) is an active
research area: it trades some of the quadratic advantage for feasible depth.

### The state preparation must be repeatable

$A$ must be applicable many times coherently. If preparing the state is itself
expensive, the accounting changes.

### It estimates one number

Amplitude estimation gives you $a$, not the good states themselves. Finding them
still needs Grover search, which is a separate cost.

### The speed-up is quadratic, not exponential

A quadratic improvement is real and valuable — it is the difference between
$10^6$ and $10^3$ evaluations — but it is far more vulnerable to overheads than
an exponential one. Large constant factors in the quantum routine can erase it
entirely.

## Practical example

### The Grover operator and its eigenphases

```python
import numpy as np
from math import pi, sin


def build(theta):
    """A|0> = sin(theta)|good> + cos(theta)|bad>, and Q = -A S0 A^dag S_good."""
    A = np.array([[sin(theta), np.cos(theta)],
                  [np.cos(theta), -sin(theta)]])
    S_good = np.array([[-1, 0], [0, 1]], dtype=complex)
    S0 = np.array([[-1, 0], [0, 1]], dtype=complex)
    return A, -(A @ S0 @ A.conj().T @ S_good)


print("eigenphases of Q are exactly +-2*theta:")
for theta in (0.3, 0.7, 1.1):
    A, Q = build(theta)
    for e in np.linalg.eigvals(Q):
        print(f"  theta={theta}: angle={np.angle(e):+.6f}"
              f"  ratio to 2*theta = {np.angle(e) / (2 * theta):+.4f}")
```

### Running the estimation

```python
def ae_distribution(theta, t):
    """Exact QPE outcome distribution for amplitude estimation."""
    A, Q = build(theta)
    w, V = np.linalg.eig(Q)
    psi = A @ np.array([1, 0], dtype=complex)
    c = np.linalg.solve(V, psi)
    N = 1 << t
    xs = np.arange(N)
    dist = np.zeros(N)
    for j, lam in enumerate(w):
        omega = (np.angle(lam) / (2 * pi)) % 1.0
        for m in range(N):
            amp = np.sum(np.exp(2j * pi * (omega - m / N) * xs)) / N
            dist[m] += abs(c[j]) ** 2 * abs(amp) ** 2
    return dist / dist.sum()


def amplitude_from_m(m, t):
    omega = m / (1 << t)
    phi = 2 * pi * omega
    phi = min(phi, 2 * pi - phi)          # fold using the +- symmetry
    return sin(phi / 2) ** 2


print("\n t   true a      est a      abs error")
for theta in (0.3, 0.7, 1.1):
    a = sin(theta) ** 2
    for t in (4, 6, 8, 10):
        d = ae_distribution(theta, t)
        m = int(np.argmax(d))
        est = amplitude_from_m(m, t)
        print(f"{t:2d}   {a:.6f}   {est:.6f}   {abs(est - a):.6f}")
    print()

print("queries for additive error eps:  classical 1/eps^2   quantum 1/eps")
for eps in (0.1, 0.01, 0.001):
    print(f"  eps={eps:<6}  {1 / eps ** 2:14.0f}  {1 / eps:14.0f}")
```

Running the blocks in order confirms the eigenphases are exactly $\pm 2\theta$,
prints the converging estimates for three amplitudes, and shows the query-count
comparison.

## Common misconceptions

- **"Amplitude estimation is just Grover repeated."** Grover *amplifies*;
  amplitude estimation *measures*. The mechanism is phase estimation on $Q$, not
  repeated search.
- **"It gives an exponential speed-up."** Quadratic. $O(1/\varepsilon)$ against
  $O(1/\varepsilon^2)$.
- **"You need to know $\theta$ in advance."** No — $\theta$ is exactly what the
  algorithm discovers.
- **"The $\pm$ ambiguity breaks it."** It does not, because
  $a = \sin^2\theta$ is the same for $+\theta$ and $-\theta$.
- **"It is practical on near-term hardware."** It needs controlled-$Q^{2^k}$,
  so circuit depth grows as $O(2^t)$ — the main obstacle, and the reason
  phase-estimation-free variants are studied.

## Exercises

1. Show that the eigenvalues of $Q$ are $e^{\pm 2i\theta}$.
2. For $a = 0.25$, what is $\theta$? What eigenphase would phase estimation
   report?
3. How many estimation qubits give error below $10^{-3}$ in the worked
   examples?
4. Why does classical sampling need $O(1/\varepsilon^2)$ samples? Derive it from
   the standard error.
5. Explain why the depth of the controlled-$Q^{2^k}$ operations is the main
   practical obstacle.
6. If amplitude estimation gives $a$ but not the good states, what additional
   cost is needed to find one?

## Summary

- Amplitude estimation estimates $a = \sin^2\theta$, where
  $A|0\rangle = \sin\theta|\text{good}\rangle + \cos\theta|\text{bad}\rangle$.
- It is **phase estimation applied to the Grover operator** $Q$, whose
  eigenvalues are $e^{\pm 2i\theta}$ — verified to be exactly $\pm2\theta$.
- Recovering the amplitude: $\theta = \tfrac{1}{2}\min(\phi,\,2\pi-\phi)$ from
  the measured phase, then $a = \sin^2\theta$.
- Verified accuracy improves with register size, reaching errors near
  $10^{-4}$ at $t = 10$.
- **Quadratic speed-up**: $O(1/\varepsilon)$ quantum against
  $O(1/\varepsilon^2)$ classical — 1000 versus $10^6$ at $\varepsilon = 10^{-3}$.
- The main obstacle is depth: controlled-$Q^{2^k}$ makes the circuit
  $O(2^t)$ deep, which motivates phase-estimation-free variants.

## References

- Brassard, G., Høyer, P., Mosca, M. & Tapp, A. (2002), "Quantum amplitude
  amplification and estimation".
- Suzuki, Y. et al. (2020), "Amplitude estimation without phase estimation" —
  the near-term alternative referenced in the caveats.
- The [Grover's Algorithm](06_grover.md) lesson — the operator $Q$ used here.
- The [Quantum Phase Estimation](32_phase_estimation.md) lesson — the subroutine
  doing the work.

---

**Previous:** [Quantum Phase Estimation](32_phase_estimation.md)
