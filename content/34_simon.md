# Simon's Algorithm

Simon's problem is the first clean **exponential** separation between quantum
and classical query complexity. Bernstein-Vazirani separates by a factor of
$n$; Simon separates by an exponential factor, for a problem where the
classical lower bound is provable. It also happens to be the direct ancestor of
the period-finding core of Shor's algorithm.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** Simon's circuit, and trace what each stage does.
- **Explain** how the measured strings give linear equations over
  $\mathrm{GF}(2)$, and how solving that system reveals the hidden mask.
- **State** the exponential separation it demonstrates, and express it in terms
  of query complexity.

## Prerequisites

This lesson assumes the [Deutsch-Jozsa algorithm](05_deutsch_jozsa.md), the
Hadamard gate, and bitwise XOR written $\oplus$. It assumes Bernstein-Vazirani
only as background, not as a dependency.

## The problem

Someone chooses a secret non-zero $n$-bit string $s$. They give you an oracle
for a function $f$ with the promise that

$$f(x) = f(y) \iff y = x \oplus s$$

So $f$ is exactly **two-to-one**: every output has precisely two preimages,
differing by $s$. Find $s$.

### Why it is hard classically

Every query returns one value $f(x)$. To learn anything you must find a
**collision** — two distinct inputs with the same output — because only then do
you learn $s = x \oplus y$. By the birthday bound, finding a collision among
$2^{n-1}$ pairs requires about $2^{n/2}$ queries. That is a proven lower bound:
no classical algorithm can do substantially better.

## Intuition

### The idea

Query the oracle on a **superposition** of all inputs at once. The resulting
state is a superposition over all the colliding pairs simultaneously. Applying
$H^{\otimes n}$ then produces a string $z$ that is *guaranteed* to satisfy

$$z \cdot s = z_1 s_1 \oplus \cdots \oplus z_n s_n = 0$$

Each run gives one such $z$, which is one linear equation in the $n$ unknown
bits of $s$. Collect $n-1$ independent equations and solve.

### Why the constraint appears

After the oracle, the first register holds a superposition of the form
$|x\rangle + |x \oplus s\rangle$ for a random $x$. Applying $H^{\otimes n}$ to
that pair gives amplitudes proportional to

$$(-1)^{z\cdot x} + (-1)^{z\cdot(x\oplus s)} = (-1)^{z\cdot x}\big(1 + (-1)^{z\cdot s}\big)$$

If $z\cdot s = 1$ the two terms **cancel**. If $z\cdot s = 0$ they **reinforce**.
So only strings orthogonal to $s$ survive, and those are the only ones you ever
measure. The unwanted answers are removed by destructive interference, which is
the same mechanism as everywhere else in this family — but here it carves out a
subspace rather than a single state.

## The circuit

### Structure

Two registers of $n$ qubits each.

| Stage | Operation | Result |
|---|---|---|
| 1 | Start | $|0\rangle^{\otimes n}|0\rangle^{\otimes n}$ |
| 2 | $H^{\otimes n}$ on the first register | uniform superposition over all $x$ |
| 3 | Oracle $U_f$ | $\frac{1}{\sqrt{2^n}}\sum_x \|x\rangle\|f(x)\rangle$ |
| 4 | $H^{\otimes n}$ on the first register | a superposition over $z$ with $z\cdot s = 0$ |
| 5 | Measure the first register | one equation $z\cdot s = 0$ |

Repeat stages 1–5 until you have $n-1$ independent non-zero $z$ values.

### Note on measuring the second register

The textbook presentation often measures the second register first, which
collapses the first register to $|x\rangle + |x\oplus s\rangle$ for a random
$x$. That step is **optional**: the distribution over $z$ is identical whether
or not you measure, because the $z$ you obtain is independent of which $x$ the
collapse selected. The verification below computes the marginal over the first
register without collapsing, and obtains the same constraint.

### Assembling the answer

Each measured non-zero $z$ gives one homogeneous linear equation over
$\mathrm{GF}(2)$. With $n-1$ independent equations, the solution space is
two-dimensional, containing exactly $\{0, s\}$. Since the promise excludes
$s = 0$, the non-zero element **is** $s$.

Verified results:

| $n$ | Secret $s$ | Distinct $z$ observed | All $z\cdot s = 0$ | Independent equations | Candidates |
|---|---|---|---|---|---|
| 2 | $11$ | $\{0, 3\}$ | yes | 1 | $\{0, 3\}$ |
| 3 | $101$ | $\{0, 2, 5, 7\}$ | yes | 2 | $\{0, 5\}$ |
| 3 | $110$ | $\{0, 1, 6, 7\}$ | yes | 2 | $\{0, 6\}$ |
| 4 | $1001$ | $\{0, 2, 4, 6, 9, 11, 13, 15\}$ | yes | 3 | $\{0, 9\}$ |

In every case the constraint held for every one of 200 sampled runs, and
$n-1$ independent equations narrowed the candidates to $\{0, s\}$.

## Complexity and the separation

### The query counts

| | Classical | Quantum |
|---|---|---|
| Queries | $\Theta(2^{n/2})$ | $O(n)$ |

The classical bound is a genuine lower bound, not a failure of imagination —
it follows from the birthday bound on collision finding. The quantum algorithm
needs about $n-1$ successful runs, each using one oracle query, and the
probability of obtaining $n-1$ independent equations is bounded below by a
constant.

That is an **exponential** separation in the query model, and it is the first
one in this course. Bernstein-Vazirani gave a factor of $n$; Simon gives an
exponential.

### What it does and does not prove

Simon's problem is artificial — nobody needs to find this particular $s$ in
practice. Its importance is structural:

- It was the first proven exponential oracle separation.
- It inspired Shor, who replaced Simon's XOR-mask structure with a
  period-finding structure over integers and applied it to factoring.
- It shows that exponential speed-ups do not require the answer to be a single
  measurement; here the answer is assembled from many partial constraints.

It does **not** prove that quantum computers are exponentially faster for
practical problems. It proves that in the oracle model, this problem is.

### Gate cost

Each run uses $2n$ Hadamards plus one oracle call. The classical post-processing
is Gaussian elimination over $\mathrm{GF}(2)$, which is $O(n^3)$ and entirely
classical.

## Practical example

### One run of the circuit

```python
import numpy as np

H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)


def kron_all(ops):
    r = np.array([[1]], dtype=complex)
    for o in ops:
        r = np.kron(r, o)
    return r


def simon_run(n, s, rng):
    """One run: returns a measured z guaranteed to satisfy z.s = 0 (mod 2)."""
    N = 1 << n
    f = {x: min(x, x ^ s) for x in range(N)}     # 2-to-1, f(x) = f(x ^ s)

    # H^n on the first register, then the oracle
    psi = np.zeros(N * N, dtype=complex)
    for x in range(N):
        psi[x * N + f[x]] += 1 / np.sqrt(N)

    # H^n on the first register only
    A = np.kron(kron_all([H] * n), np.eye(N, dtype=complex))
    p = np.abs(A @ psi) ** 2

    # marginal over the first register (no need to measure the second)
    marg = np.zeros(N)
    for idx in range(N * N):
        marg[idx // N] += p[idx]
    marg /= marg.sum()
    return rng.choice(N, p=marg)
```

### Solving the linear system

```python
def solve_mask(n, zs):
    """Return the candidates s consistent with every z.s = 0 over GF(2)."""
    basis = []
    for z in zs:
        if z == 0:
            continue
        v = z
        for b in basis:
            v = min(v, v ^ b)                    # reduce against the basis
        if v:
            basis.append(v)
    return [t for t in range(1 << n)
            if all(bin(t & b).count("1") % 2 == 0 for b in basis)]


rng = np.random.default_rng(3)
for n, s in ((2, 3), (3, 5), (3, 6), (4, 9)):
    zs = [simon_run(n, s, rng) for _ in range(200)]
    ok = all(bin(z & s).count("1") % 2 == 0 for z in zs)
    # keep taking equations until we have n-1 independent ones
    basis, used = [], []
    for z in zs:
        if z == 0:
            continue
        v = z
        for b in basis:
            v = min(v, v ^ b)
        if v:
            basis.append(v)
            used.append(z)
        if len(basis) == n - 1:
            break
    cand = solve_mask(n, used)
    print(f"n={n} s={s} ({s:0{n}b}): all z.s=0: {ok}"
          f"  candidates after {len(basis)} equations: {cand}")
```

Running the blocks in order confirms that every sampled $z$ satisfies
$z\cdot s = 0$, and that $n-1$ independent equations reduce the candidates to
$\{0, s\}$ in each case.

## Common misconceptions

- **"One run gives the answer."** One run gives one *equation*. You need about
  $n-1$ independent ones.
- **"The measured $z$ is random noise."** It is random, but constrained: always
  orthogonal to $s$. The randomness is uniform over that subspace.
- **"You must measure the second register."** No — the distribution over $z$ is
  the same either way.
- **"This proves quantum computers beat classical ones on real problems."** It
  proves an exponential separation in the **oracle model** for an artificial
  problem.
- **"The speed-up is $2^n$."** The separation is $O(n)$ quantum against
  $\Theta(2^{n/2})$ classical.

## Exercises

1. For $n=3$ and $s=101$, list every $z$ with $z\cdot s = 0$. How many are
   there?
2. Explain why $z = 0$ is always a possible outcome, and why it is useless.
3. Show that $n-1$ independent equations leave exactly two candidates.
4. Why is the classical lower bound $\Theta(2^{n/2})$ rather than
   $\Theta(2^n)$?
5. What is the probability that $n$ consecutive runs fail to produce $n-1$
   independent equations?
6. Compare Simon's separation with Bernstein-Vazirani's. Which is stronger,
   and why?

## Summary

- Simon's problem: find $s$ given a two-to-one $f$ with $f(x) = f(x\oplus s)$.
- The circuit is $H^{\otimes n}$, oracle, $H^{\otimes n}$, measure — giving a
  $z$ with $z\cdot s = 0$.
- The constraint arises by **interference**: terms with $z\cdot s = 1$ cancel
  exactly.
- Collect $n-1$ independent equations and solve over $\mathrm{GF}(2)$; the
  candidates collapse to $\{0, s\}$, and $s$ is the non-zero one.
- Query complexity: **$O(n)$ quantum versus $\Theta(2^{n/2})$ classical** — an
  exponential separation, the first in this course.
- Its importance is structural: it was the template Shor adapted to factoring.

## References

- Simon, D. R. (1997), "On the power of quantum computation" — the original
  algorithm and the exponential oracle separation.
- The [Bernstein-Vazirani](30_bernstein_vazirani.md) lesson — the linear
  separation, using the same interference mechanism.
- The [Shor's Algorithm](33_shors_algorithm.md) lesson — Simon's structure
  adapted from XOR masks to period finding.

---

**Previous:** [Bernstein-Vazirani](30_bernstein_vazirani.md)
