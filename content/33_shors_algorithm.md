# Shor's Algorithm

Shor's algorithm is the reason quantum computing became a funded research
field. It factors integers in polynomial time, and the security of RSA rests on
factoring being hard. This lesson covers the reduction from factoring to order
finding, how phase estimation performs order finding, and — at least as
important — the fine print about what the algorithm does and does not imply.

## Learning objectives

By the end of this lesson you should be able to:

- **Reduce** factoring to order finding, and state the conditions under which
  the reduction succeeds.
- **Explain** how phase estimation performs order finding, including why the
  eigenvalues of the modular multiplication operator are roots of unity.
- **State** the assumptions behind the algorithm and its impact on public-key
  cryptography.

## Prerequisites

This lesson assumes [Quantum Phase Estimation](32_phase_estimation.md) and
therefore the [Quantum Fourier Transform](31_qft.md). It assumes modular
arithmetic and what a greatest common divisor is.

## Part 1: from factoring to order finding

### The reduction

To factor an odd composite $N$, pick a random $a$ with $1 < a < N$.

1. Compute $g = \gcd(a, N)$. If $g > 1$, you have already found a factor.
2. Otherwise, find the **order** $r$ of $a$ modulo $N$: the smallest positive
   $r$ such that

   $$a^r \equiv 1 \pmod N$$

3. If $r$ is odd, start again with a different $a$.
4. If $a^{r/2} \equiv -1 \pmod N$, start again.
5. Otherwise, $\gcd(a^{r/2} - 1, N)$ and $\gcd(a^{r/2} + 1, N)$ are **non-trivial
   factors** of $N$.

### Why it works

If $a^r \equiv 1$ then $(a^{r/2})^2 \equiv 1$, so
$(a^{r/2}-1)(a^{r/2}+1) \equiv 0 \pmod N$. Thus $N$ divides the product. Unless
$a^{r/2} \equiv \pm 1$, $N$ divides neither factor alone, so each shares a
non-trivial common factor with $N$ — and the Euclidean algorithm finds it
instantly.

### Verified

| $N$ | $a$ | Order $r$ | $a^{r/2} \bmod N$ | $\gcd(a^{r/2}-1, N)$ | $\gcd(a^{r/2}+1, N)$ | Factors |
|---|---|---|---|---|---|---|
| 15 | 2 | 4 | 4 | 3 | 5 | $3 \times 5$ |
| 21 | 2 | 6 | 8 | 7 | 3 | $7 \times 3$ |
| 35 | 2 | 12 | 29 | 7 | 5 | $7 \times 5$ |

The reduction succeeds with probability at least $1/2$ over a random choice of
$a$, so a few attempts suffice. Everything difficult has now been moved into
step 2: **finding the order**.

### What remains hard

Finding $r$ classically is believed to be as hard as factoring itself. There is
no known classical polynomial-time algorithm. This is where the quantum part
enters.

## Part 2: order finding by phase estimation

### The operator

Define the modular multiplication operator

$$U|y\rangle = |ay \bmod N\rangle$$

It is a permutation, hence unitary. Applying it $r$ times returns every $y$ to
itself, so $U^r = I$. Therefore every eigenvalue $\lambda$ satisfies
$\lambda^r = 1$ — the eigenvalues are $r$-th roots of unity, of the form
$e^{2\pi i k/r}$.

**That is the whole insight.** The order $r$ is hidden in the *phases* of the
eigenvalues, and extracting phases is exactly what phase estimation does.

### Verified eigenvalues

For $N = 15$, $a = 2$ the order is $r = 4$, and the eigenvalues of $U$ are:

| Eigenvalue | Phase |
|---|---|
| $1$ | $0$ |
| $i$ | $1/4$ |
| $-1$ | $1/2$ |
| $-i$ | $-1/4$ |

All four are 4th roots of unity, as required.

### The catch: you need an eigenstate, and you do not have one

Phase estimation returns the phase of whichever eigenstate you supply. The
computational basis state $|1\rangle$ is **not** an eigenstate of $U$ — it is a
superposition of all the eigenstates with eigenvalue $e^{2\pi i k/r}$.

This turns out to be fine. Running phase estimation on $|1\rangle$ returns
$k/r$ for a **uniformly random** $k \in \{0, \ldots, r-1\}$ . Each run gives a
random $k$, and we only need one that is coprime to $r$.

### From the measured phase back to $r$

Phase estimation gives an estimate of $k/r$ to $t$ bits. The **continued
fraction expansion** of that estimate recovers the rational $k/r$ in lowest
terms, whose denominator is $r$ — provided $\gcd(k, r) = 1$.

Verified for $r = 4$:

| Measured $k/r$ | Recovered denominator | Equals $r$? | $\gcd(k, r)$ |
|---|---|---|---|
| $1/4$ | 4 | yes | 1 |
| $2/4 = 1/2$ | 2 | **no** | 2 |
| $3/4$ | 4 | yes | 1 |

When $k$ and $r$ share a factor, the fraction reduces and you recover a proper
**divisor** of $r$. This is not a bug to hide — it is a real feature of the
algorithm and it is handled in two ways:

- **Repeat.** For a uniformly random $k \in \{0,\ldots,r-1\}$, the probability
  that $\gcd(k,r) = 1$ is $\varphi(r)/r$. Measured values: $0.5$ for $r = 4$,
  $0.333$ for $r = 6$ and $r = 12$, and $0.5$ for $r = 1024$. Since
  $\varphi(r)/r$ is bounded below by roughly $1/(e^\gamma \log\log r)$,
  $O(\log r)$ repetitions give $r$ with high probability.
- **Combine.** Take the least common multiple of the denominators from several
  runs. This is *usually* enough but is **not guaranteed** — if every sampled
  $k$ happens to share a factor with $r$, the LCM falls short. Measured success
  rates over 4000 trials, sampling $k$ uniformly from $\{1,\ldots,r-1\}$:

  | Samples | $r = 4$ | $r = 12$ | $r = 60$ |
  |---|---|---|---|
  | 1 | 0.670 | 0.357 | 0.275 |
  | 2 | 0.888 | 0.716 | 0.646 |
  | 3 | 0.960 | 0.885 | 0.843 |
  | 5 | 0.995 | 0.976 | 0.971 |

  The rate climbs quickly with the number of samples, but a single run is
  genuinely unreliable — which is why practical treatments repeat the whole
  procedure and verify the result by checking $a^r \equiv 1 \pmod N$.

## Complexity

### The cost

Factoring an $n$-bit number with Shor's algorithm costs roughly $O(n^3)$ gates
for the arithmetic, with the modular exponentiation dominating. The classical
general number field sieve runs in
$\exp\big(O(n^{1/3}\log^{2/3} n)\big)$ — superpolynomial.

That gap is the exponential speed-up, and it is real.

### But: the resource estimate

To factor a cryptographically relevant 2048-bit RSA modulus, published
estimates put the requirement at roughly **20 million physical qubits** running
for about 8 hours, assuming realistic error rates and error correction. The
largest quantum processors today have on the order of a thousand physical
qubits, with no error correction.

So the algorithm is polynomial and the hardware is nowhere near. The practical
threat timeline depends on engineering progress, not on the algorithm.

## Impact on cryptography

### What breaks

RSA, Diffie-Hellman and elliptic-curve cryptography all rely on problems that
Shor's algorithm solves in polynomial time — integer factoring and discrete
logarithms. A sufficiently large fault-tolerant quantum computer breaks all of
them.

Note that **symmetric** cryptography is not broken, only weakened: Grover's
algorithm gives a quadratic speed-up against a brute-force key search, which
doubling the key length comfortably counters. AES-256 remains fine.

### The response

Two distinct things, often conflated:

- **Post-quantum cryptography (PQC)** — classical algorithms, run on classical
  hardware, believed hard for quantum computers too. Lattice-based,
  code-based, hash-based and multivariate schemes. NIST has standardised
  several. This is a software upgrade.
- **Quantum cryptography** — protocols such as QKD that use quantum hardware to
  distribute keys. Different mechanism, different trust assumptions, and it
  does not replace PQC.

### An honest caveat on urgency

"Harvest now, decrypt later" is the realistic concern: encrypted traffic
captured today can be decrypted once a capable machine exists. That is why
migration to PQC is underway now, despite no such machine existing. It is a
data-longevity problem more than an imminent-break problem.

## Practical example

### The reduction, verified

```python
import math


def order(a, N):
    """Smallest r with a^r = 1 (mod N)."""
    if math.gcd(a, N) != 1:
        return None
    r, v = 1, a % N
    while v != 1:
        v = (v * a) % N
        r += 1
        if r > N:
            return None
    return r


print("factoring via order finding:")
for N in (15, 21, 35):
    for a in range(2, N):
        r = order(a, N)
        if r is None or r % 2 != 0:
            continue
        x = pow(a, r // 2, N)
        if x == N - 1:
            continue
        p, q = math.gcd(x - 1, N), math.gcd(x + 1, N)
        if 1 < p < N or 1 < q < N:
            print(f"  N={N}: a={a}, r={r}, a^(r/2)={x}"
                  f" -> factors {p} and {q}")
            break
```

### Eigenvalues and continued fractions

```python
import numpy as np
from fractions import Fraction
from math import gcd


def modular_mult_matrix(a, N, bits):
    dim = 1 << bits
    M = np.zeros((dim, dim), dtype=complex)
    for y in range(dim):
        M[(a * y) % N if y < N else y, y] = 1
    return M


N, a = 15, 2
r = order(a, N)
U = modular_mult_matrix(a, N, 4)
print(f"\nN={N}, a={a}, order r={r}")
print("  eigenvalues of U:")
for e in sorted(set(np.round(np.linalg.eigvals(U), 6)),
                key=lambda z: round(np.angle(z), 6)):
    print(f"    {np.round(e, 6)}  phase={np.angle(e) / (2 * np.pi):+.6f}")

print("\n  continued-fraction recovery of r:")
for k in range(1, r):
    got = Fraction(k / r).limit_denominator(N).denominator
    print(f"    k/r={k}/{r} -> denominator {got}"
          f"{'  == r' if got == r else '  (divisor only)'}")

print(f"\n  P(gcd(k,r)=1) = phi(r)/r:")
for rr in (4, 6, 12, 1024):
    good = sum(1 for k in range(1, rr + 1) if gcd(k, rr) == 1)
    print(f"    r={rr:5d}: {good}/{rr} = {good / rr:.4f}")

def lcm_recover(order_r, samples):
    l = 1
    for k in samples:
        d = Fraction(k / order_r).limit_denominator(10 ** 6).denominator
        l = l * d // gcd(l, d)
    return l


print("\n  combining denominators by LCM recovers r:")
import random
random.seed(1)
for _ in range(4):
    ks = [random.randrange(1, r) for _ in range(3)]
    dens = [Fraction(k / r).limit_denominator(N).denominator for k in ks]
    print(f"    r={r}, k={ks} -> {dens} -> lcm {lcm_recover(r, ks)}")
# a case where individual samples give only divisors of r
print("    r=12, where single samples often give 2, 3, 4 or 6:")
for _ in range(3):
    ks = [random.randrange(1, 12) for _ in range(3)]
    dens = [Fraction(k / 12).limit_denominator(10 ** 6).denominator for k in ks]
    print(f"      k={ks} -> {dens} -> lcm {lcm_recover(12, ks)}")

print("\n  LCM success rate over 4000 trials (NOT guaranteed on one run):")
random.seed(7)
for rr in (4, 12, 60):
    row = []
    for n_samp in (1, 2, 3, 5):
        ok = sum(1 for _ in range(4000)
                 if lcm_recover(rr, [random.randrange(1, rr)
                                     for _ in range(n_samp)]) == rr)
        row.append(f"{n_samp}:{ok / 4000:.3f}")
    print(f"    r={rr:3d}  " + "  ".join(row))
```

Running the blocks in order factors 15, 21 and 35; confirms the eigenvalues of
$U$ are 4th roots of unity; shows the reduced-fraction case; and demonstrates
the LCM fix.

## Common misconceptions

- **"Shor's algorithm breaks all encryption."** It breaks public-key schemes
  based on factoring and discrete log. Symmetric ciphers are only weakened by
  Grover's quadratic speed-up, and doubling the key length compensates.
- **"It can already factor large numbers."** Published demonstrations have
  factored small composites such as 15 and 21. Factoring RSA-sized moduli needs
  millions of error-corrected qubits.
- **"Finding the order is the same as factoring."** Factoring reduces to order
  finding, and order finding is where the quantum speed-up lives.
- **"Each run gives the order."** Each run gives $k/r$ for a random $k$; when
  $k$ shares a factor with $r$ you get a divisor, not $r$.
- **"Quantum cryptography is the fix."** The fix is post-quantum cryptography —
  classical algorithms resistant to quantum attack. QKD is a different thing.

## Exercises

1. Factor $N = 15$ by hand using $a = 4$. What is the order, and what factors
   do you get?
2. Why must $r$ be even for the reduction to produce factors?
3. Show that the eigenvalues of $U$ are $r$-th roots of unity.
4. For $r = 12$, list the $k$ that give $r$ exactly and those that give a
   divisor. What fraction succeed?
5. Explain why repeating the order-finding step $O(\log r)$ times gives $r$
   with high probability.
6. Which parts of Shor's algorithm are classical, and which are quantum?

## Summary

- Factoring reduces to **order finding**: find the smallest $r$ with
  $a^r \equiv 1 \pmod N$, then $\gcd(a^{r/2}\pm1, N)$ gives the factors.
- The reduction succeeds with probability at least $1/2$ per random $a$;
  verified on $N = 15, 21, 35$.
- The operator $U|y\rangle = |ay \bmod N\rangle$ satisfies $U^r = I$, so its
  eigenvalues are $r$-th **roots of unity** — verified for $N=15$, $a=2$.
- Phase estimation returns $k/r$ for a uniformly random $k$; continued fractions
  recover the rational.
- When $\gcd(k,r) \neq 1$ you recover a **divisor** of $r$. Repeat
  ($\varphi(r)/r$ success per run) or take the LCM of several denominators.
- Complexity is polynomial, roughly $O(n^3)$ — but factoring RSA-2048 is
  estimated at about 20 million qubits for 8 hours.
- RSA, DH and ECC are broken by a large enough machine; symmetric ciphers are
  only weakened. The response is **post-quantum cryptography**, not QKD.

## References

- Shor, P. W. (1997), "Polynomial-time algorithms for prime factorization and
  discrete logarithms on a quantum computer".
- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  §5.3 — the order-finding circuit.
- Gidney, C. & Ekerå, M. (2021), "How to factor 2048 bit RSA integers in 8
  hours using 20 million noisy qubits" — the resource estimate quoted here.
- The [Quantum Phase Estimation](32_phase_estimation.md) lesson — the subroutine
  that performs order finding.

---

**Previous:** [Quantum Phase Estimation](32_phase_estimation.md)
