# The Estimator Primitive

The Sampler gives you bit strings. The Estimator gives you **numbers**: the
expectation value of an observable, $\langle\psi|O|\psi\rangle$. That single
change of interface is what makes variational algorithms practical — VQE does
not want a histogram, it wants the energy, and it wants it thousands of times
while an optimiser walks a parameter landscape. This lesson covers how
expectation values are actually measured, which basis-change gate each Pauli
needs, and when to reach for Estimator rather than Sampler.

> **A note on this project.** The Composer and the simulators here expose a
> Sampler-style interface: you get counts. There is no Estimator class in this
> codebase. Everything below is therefore implemented directly from counts,
> using the engine that does exist — which is also the clearest way to see what
> the primitive is doing underneath.

## Learning objectives

By the end of this lesson you should be able to:

- **Compute** the expectation value of a Pauli observable from measurement
  counts.
- **Choose** the basis-change gate needed to measure in the $X$, $Y$ or $Z$
  basis, and verify the identity that justifies it.
- **Evaluate** a multi-qubit Pauli string such as $\langle Z_0 Z_1\rangle$ from
  joint counts.
- **Contrast** Estimator with Sampler, and state which is appropriate for a
  given task.
- **Estimate** the shot noise on an expectation value, and choose a shot count
  to achieve a target precision.

## Expectation values from measurements

### The problem

An observable $O$ has eigenvalues $\lambda_k$ and eigenstates $|k\rangle$. Its
expectation value is

$$\langle O \rangle = \langle\psi|O|\psi\rangle = \sum_k \lambda_k \, |\langle k|\psi\rangle|^2$$

To estimate it on hardware you repeatedly prepare $|\psi\rangle$, measure in
$O$'s eigenbasis, and average the eigenvalues you get:

$$\langle O \rangle \approx \frac{1}{N}\sum_{i=1}^{N} \lambda_{k_i}$$

### Why this is not the same as reading a histogram

For a Pauli observable the eigenvalues are $\pm 1$. Every shot contributes
$+1$ or $-1$, and the estimate is their mean. A histogram would tell you the
counts; the Estimator collapses them to one number and, crucially, reports its
**variance**. For a variational loop that number and its uncertainty are the
whole interface.

## Basis changes

### The identity

You can only measure in the computational ($Z$) basis. To measure a different
Pauli $P$, find a unitary $U$ with

$$U^\dagger Z U = P$$

then apply $U$ and measure $Z$. The algebra:

$$\langle\psi|P|\psi\rangle = \langle\psi|U^\dagger Z U|\psi\rangle = \langle U\psi|Z|U\psi\rangle$$

### The three cases

| Observable | Apply before measuring | Justification |
|---|---|---|
| $Z$ | nothing | $I^\dagger Z I = Z$ |
| $X$ | $H$ | $H^\dagger Z H = X$ |
| $Y$ | $S^\dagger$, then $H$ | $(HS^\dagger)^\dagger Z (HS^\dagger) = Y$ |

The $Y$ case is the one people get wrong. The correct sequence is $S^\dagger$
followed by $H$ — not $H$ followed by $S$, which satisfies a different identity
and gives the wrong answer.

### Worked example

For $|\psi\rangle = 0.6|0\rangle + 0.8|1\rangle$:

| Observable | Direct $\langle\psi|P|\psi\rangle$ | Via basis change | From counts |
|---|---|---|---|
| $\langle Z\rangle$ | $-0.28$ | $-0.28$ | $-0.28$ |
| $\langle X\rangle$ | $0.96$ | $0.96$ | $0.96$ |
| $\langle Y\rangle$ | $0.00$ | $0.00$ | $0.00$ |

All three routes agree, which is the check that the basis-change gates are
right. $\langle Y\rangle = 0$ here because the amplitudes are real; a state
with relative phase would give a non-zero value.

## Multi-qubit observables

### Pauli strings

A Hamiltonian is typically a weighted sum of **Pauli strings** — tensor
products such as $Z_0 Z_1$ or $X_0 Y_1 Z_2$. By linearity:

$$\langle H \rangle = \sum_j c_j \langle P_j \rangle$$

so you estimate each Pauli string separately and combine.

### From joint counts

For a product of Paulis on different qubits, measure each qubit in its
respective basis and multiply the $\pm 1$ outcomes per shot, then average:

$$\langle Z_0 Z_1 \rangle = \frac{1}{N}\sum_{i=1}^{N} s_0^{(i)} \, s_1^{(i)}$$

where each $s^{(i)} \in \{+1, -1\}$ is the outcome for that qubit in that shot.

For the Bell state $\tfrac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$:

$$\langle Z_0 Z_1 \rangle = 1.0$$

The outcomes always agree, so every shot contributes $+1$. Note that the
single-qubit values are $\langle Z_0\rangle = \langle Z_1\rangle = 0$ — the
product carries information that neither factor does. This is why correlator
terms matter and why measuring only individual qubits is not enough.

### Commuting groups

Measuring $X_0X_1$ and $Z_0Z_1$ requires different basis changes, so they need
separate runs. But $Z_0Z_1$ and $Z_0$ commute and can be estimated from the
**same** shots. Grouping commuting Pauli strings into shared measurement bases
is the single biggest practical saving in VQE, often cutting the number of
circuits by a large factor.

## Shot noise on expectation values

### The variance

Each shot contributes $\pm 1$, so for a single Pauli

$$\operatorname{Var} = 1 - \langle P\rangle^2$$

and the standard error on $N$ shots is

$$\sigma = \sqrt{\frac{1 - \langle P\rangle^2}{N}}$$

The error is worst when $\langle P\rangle \approx 0$ — the same lesson as for
probabilities, where $p = 0.5$ was hardest to pin down.

### Worked values

For $\langle Z \rangle = 0.5$:

| Shots | Empirical sd (2000 trials) | Theory $\sqrt{0.75/N}$ |
|---|---|---|
| 100 | 0.0862 | 0.0866 |
| 1024 | 0.0267 | 0.0271 |
| 8192 | 0.0094 | 0.0096 |

The error shrinks as $1/\sqrt{N}$: four times the shots halves the
uncertainty. A variational optimiser that needs $\pm 0.01$ on each energy
evaluation is paying roughly 10000 shots per evaluation, which is why shot
budget dominates VQE run time.

## Estimator vs Sampler

### The distinction

| | Sampler | Estimator |
|---|---|---|
| Returns | Bit strings and counts | Expectation values $\langle O\rangle$ |
| Input | A circuit | A circuit **and** an observable |
| Typical use | Distributions, Grover, sampling tasks | Energies, VQE, QAOA, gradients |
| Output size | Grows as $2^n$ | One number per observable |

### When to use which

- **Use Sampler** when you care about the *distribution* — which outcomes are
  likely, how they are spread, anything where the shape of the histogram is the
  answer. Grover, Bernstein–Vazirani and most of the algorithms in this course
  are Sampler-shaped.
- **Use Estimator** when you care about an *average* — an energy, an order
  parameter, a gradient. Requesting the full distribution and averaging it
  yourself works but throws away information: the Estimator can group
  commuting terms, choose measurement bases for you, and report the variance
  alongside the value.

A useful rule of thumb: if you would immediately reduce the counts to a single
number, you wanted Estimator.

## Practical example

### Basis-change identities

```python
import numpy as np

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)
S = np.array([[1, 0], [0, 1j]], dtype=complex)
Sdg = S.conj().T


def measures(U, P, name):
    """Applying U then measuring Z estimates <P> iff U^dag Z U == P."""
    print(f"  {name}: U^dag Z U == {name}? {np.allclose(U.conj().T @ Z @ U, P)}")


print("basis-change identities:")
measures(I2, Z, "Z  (no change)")
measures(H, X, "X  (apply H)")
measures(H @ Sdg, Y, "Y  (apply Sdg then H)")
print("  wrong order, H then S, for Y:", np.allclose((S @ H).conj().T @ Z @ (S @ H), Y))
```

### Expectation values three ways

```python
psi = np.array([0.6, 0.8], dtype=complex)
psi = psi / np.linalg.norm(psi)
print("state:", np.round(psi, 4))

for name, P, U in (("Z", Z, I2), ("X", X, H), ("Y", Y, H @ Sdg)):
    direct = np.vdot(psi, P @ psi).real
    rotated = np.vdot(U @ psi, Z @ (U @ psi)).real
    phi = U @ psi
    probs = np.abs(phi) ** 2
    from_counts = probs[0] * (+1) + probs[1] * (-1)
    print(f"  <{name}>: direct={direct:.6f}  via U={rotated:.6f}"
          f"  from counts={from_counts:.6f}")

bell = np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)
probs2 = np.abs(bell) ** 2
zz = sum(p * ((-1) ** ((i >> 1) & 1)) * ((-1) ** (i & 1))
         for i, p in enumerate(probs2))
print(f"\n<Z0 Z1> for the Bell state: {zz:.4f}")
```

### Shot noise

```python
rng = np.random.default_rng(3)
print("shot noise on <Z> with true value 0.5:")
for N in (100, 1024, 8192):
    estimates = [
        np.mean(np.where(rng.random(N) < 0.75, 1, -1)) for _ in range(2000)
    ]
    print(f"  N={N:5d}: mean={np.mean(estimates):.4f}"
          f"  sd={np.std(estimates, ddof=1):.4f}"
          f"  theory={np.sqrt(0.75 / N):.4f}")
```

Running the blocks in order confirms all three basis-change identities, and
prints `False` for the wrong $Y$ ordering. The three expectation values come
out $-0.28$, $0.96$ and $0.00$ by all three routes, $\langle Z_0Z_1\rangle$ for
the Bell state is `1.0000`, and the shot-noise table gives `0.0862`, `0.0267`
and `0.0094` against theoretical `0.0866`, `0.0271` and `0.0096`.

## Common misconceptions

- **"Estimator measures the observable directly."** It measures in the
  computational basis after a basis change. The observable only enters through
  the choice of $U$.
- **"Measuring $Y$ is $H$ then $S$."** It is $S^\dagger$ then $H$. The other
  order satisfies a different identity and returns the wrong value.
- **"Expectation values are exact."** They are estimates from $N$ shots with
  standard error $\sqrt{(1-\langle P\rangle^2)/N}$.
- **"You can get $\langle Z_0Z_1\rangle$ from the single-qubit values."**
  No — for the Bell state both single-qubit values are zero while the product
  is one. Correlations are not determined by marginals.
- **"Estimator and Sampler are interchangeable."** Sampler gives a
  distribution; Estimator gives an average with a variance. Pick by what your
  algorithm consumes.

## Exercises

1. Verify numerically that $H^\dagger Z H = X$ and
   $(HS^\dagger)^\dagger Z(HS^\dagger) = Y$.
2. For $|\psi\rangle = \tfrac{1}{\sqrt{2}}(|0\rangle + i|1\rangle)$, compute
   $\langle X\rangle$, $\langle Y\rangle$ and $\langle Z\rangle$.
3. Show that $\langle Z_0Z_1\rangle = 1$ for $|\Phi^+\rangle$ but that
   $\langle Z_0\rangle = 0$, and explain the difference.
4. How many shots give a standard error of $0.01$ when $\langle P\rangle = 0$?
   When $\langle P\rangle = 0.9$?
5. Which of $X_0X_1$, $X_0Z_1$, $Z_0X_1$ and $Z_0Z_1$ can be measured from the
   same shots? Explain the grouping rule.
6. Give one task where Sampler is the right choice and one where Estimator is,
   and justify each.

## Summary

- The Estimator returns $\langle\psi|O|\psi\rangle$; the Sampler returns
  counts. Estimator takes a circuit and an observable.
- Only $Z$ is directly measurable. To measure $P$, apply $U$ with
  $U^\dagger Z U = P$: nothing for $Z$, $H$ for $X$, $S^\dagger$ then $H$ for
  $Y$.
- Multi-qubit Pauli strings are estimated by multiplying per-shot $\pm1$
  outcomes and averaging; commuting strings can share measurement bases.
- The standard error is $\sqrt{(1-\langle P\rangle^2)/N}$, worst when the
  expectation is near zero, and shrinks only as $1/\sqrt{N}$.
- Use Sampler for distributions, Estimator for averages — if you would
  immediately reduce counts to one number, you wanted Estimator.

## References

- Qiskit documentation, *Estimator primitive* — the interface this lesson
  describes.
- Qiskit documentation, *Sampler primitive* — the other half of the pair.
- The [VQE and QAOA](07_vqe_qaoa.md) lesson — the algorithm that motivates
  Estimator.
- The [Reading Quantum Results](27_reading_results.md) lesson — bit ordering
  and standard errors for count-based estimates.

---

**Previous:** [The Quantum Composer](28_composer_guide.md)
