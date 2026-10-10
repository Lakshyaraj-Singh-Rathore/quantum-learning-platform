# Bernstein-Vazirani

This is the cleanest demonstration of quantum advantage in the oracle model.
A classical computer needs $n$ queries to recover an $n$-bit string; a quantum
computer needs **one**. The algorithm is three lines of circuit, and the reason
it works is the same phase-kickback trick that powers the whole family.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** the Bernstein-Vazirani circuit and trace it state by state.
- **Explain** why one quantum query suffices where a classical algorithm needs
  $n$, and state the query-complexity separation precisely.
- **Relate** the algorithm to the Deutsch-Jozsa phase-kickback pattern, and
  identify what the two share.

## Prerequisites

This lesson assumes the [Deutsch-Jozsa algorithm](05_deutsch_jozsa.md), the
Hadamard gate, and the idea of an oracle as a black box you may query but not
inspect.

## The problem

Someone chooses a secret $n$-bit string $s = s_1 s_2 \cdots s_n$. You may query
a function

$$f(x) = s \cdot x \pmod 2 = s_1 x_1 \oplus s_2 x_2 \oplus \cdots \oplus s_n x_n$$

where $\oplus$ is addition mod 2. Find $s$.

### Classically

Each query returns **one bit**, $f(x)$. Querying $x = 100\cdots0$ gives $s_1$;
querying $010\cdots0$ gives $s_2$, and so on. You need **$n$ queries**, and you
cannot do better — $n$ bits of information cannot be extracted with fewer than
$n$ single-bit answers.

### Quantumly

One query. The trick is that the oracle is queried on a **superposition** of all
$x$ at once, and the answer comes back as a **phase** rather than a bit.

## Intuition: the answer is a phase

### Making the oracle kick back

The standard oracle acts as
$|x\rangle|y\rangle \mapsto |x\rangle|y \oplus f(x)\rangle$.
Prepare the second register as

$$|{-}\rangle = \frac{|0\rangle - |1\rangle}{\sqrt{2}}$$

Then

$$|x\rangle|{-}\rangle \;\longmapsto\; (-1)^{f(x)}|x\rangle|{-}\rangle$$

The second register is **unchanged** — it merely picks up a minus sign when
$f(x) = 1$. That sign is a *phase* on the first register, and phases are
exactly what interfere.

So the oracle becomes, in effect, a diagonal operator applying
$(-1)^{s\cdot x}$ to $|x\rangle$. This is the same phase-kickback mechanism as
Deutsch-Jozsa; the only difference is what we do with the result.

### Why the second Hadamard layer reveals $s$

Start with $|0\rangle^{\otimes n}$, apply $H^{\otimes n}$ to get a uniform
superposition over all $x$. The oracle writes the phase $(-1)^{s\cdot x}$ onto
each term:

$$\frac{1}{\sqrt{2^n}}\sum_x |x\rangle \;\longrightarrow\; \frac{1}{\sqrt{2^n}}\sum_x (-1)^{s\cdot x}|x\rangle$$

But that state is *exactly* what $H^{\otimes n}$ produces when applied to
$|s\rangle$. Since $H^{\otimes n}$ is its own inverse, applying it again maps
the state straight back to $|s\rangle$. Measure and read off the string.

The whole algorithm is: $H^{\otimes n}$, oracle, $H^{\otimes n}$, measure.

## Circuit walkthrough

| Stage | Operation | State |
|---|---|---|
| 1 | Start | $|0\rangle^{\otimes n}$ |
| 2 | $H^{\otimes n}$ | uniform superposition over all $x$ |
| 3 | Oracle with $|{-}\rangle$ ancilla | each $|x\rangle$ gains phase $(-1)^{s\cdot x}$ |
| 4 | $H^{\otimes n}$ | $|s\rangle$ |
| 5 | Measure | the secret string |

The ancilla qubit is never measured. It is returned to $|{-}\rangle$ and can be
reused, which is why the query count is one.

### A worked example

For $n = 3$ and $s = 101$, writing amplitudes in the computational basis
$|000\rangle, |001\rangle, \ldots, |111\rangle$:

| Stage | Amplitudes |
|---|---|
| After $H^{\otimes 3}$ | $(\tfrac{1}{\sqrt8},\ \tfrac{1}{\sqrt8},\ \tfrac{1}{\sqrt8},\ \tfrac{1}{\sqrt8},\ \tfrac{1}{\sqrt8},\ \tfrac{1}{\sqrt8},\ \tfrac{1}{\sqrt8},\ \tfrac{1}{\sqrt8})$ |
| After the oracle | $(\tfrac{1}{\sqrt8},\ -\tfrac{1}{\sqrt8},\ \tfrac{1}{\sqrt8},\ -\tfrac{1}{\sqrt8},\ -\tfrac{1}{\sqrt8},\ \tfrac{1}{\sqrt8},\ -\tfrac{1}{\sqrt8},\ \tfrac{1}{\sqrt8})$ |
| After $H^{\otimes 3}$ | $(0,\ 0,\ 0,\ 0,\ 0,\ 1,\ 0,\ 0)$ |

The final state has all its amplitude on index 5, which is $|101\rangle$ — the
secret. Note the oracle stage: the amplitudes never change magnitude, only
**sign**. All the information is in the signs, and the final Hadamard layer is
what converts a sign pattern into a single basis state.

This was verified for **every** secret string at $n = 2, 3$ and $4$: all
$4 + 8 + 16 = 28$ cases are recovered exactly, with no sampling and no
probability of error.

## Complexity and what the separation means

### The query counts

| $n$ | Classical queries | Quantum queries |
|---|---|---|
| 3 | 3 | 1 |
| 8 | 8 | 1 |
| 16 | 16 | 1 |
| 64 | 64 | 1 |

The separation is $n$ versus 1 — linear versus constant. In the **query
complexity** model, where you count only oracle calls, that is a genuine and
unconditional separation.

### Being precise about the advantage

Two honest qualifications:

**This is a black-box separation.** It proves no classical algorithm can solve
the problem with fewer queries *to an opaque oracle*. If you know the oracle is
of the form $s\cdot x$, the problem is trivial classically — query the $n$
basis vectors. The separation is about the query model, not about a practical
task where someone hands you a circuit.

**It is linear, not exponential.** Bernstein-Vazirani separates by a factor of
$n$. Simon's algorithm gives an exponential separation, and Shor's gives an
exponential separation for a problem with real-world consequences. BV is the
pedagogically clean case, not the strongest one.

### Gate count

The circuit needs $2n$ Hadamards plus one oracle call. That is $O(n)$ gates —
even the gate count beats the classical $n$ queries, because each quantum
"query" is a single coherent oracle application.

## Relation to Deutsch-Jozsa

Both algorithms use the same two-step pattern:

1. Create a uniform superposition with $H^{\otimes n}$.
2. Let the oracle write its answer into the **phase**, using a $|{-}\rangle$
   ancilla.

They differ only in the last step and in what is promised:

| | Deutsch-Jozsa | Bernstein-Vazirani |
|---|---|---|
| Promise | $f$ is constant or balanced | $f(x) = s\cdot x$ |
| Last step | $H^{\otimes n}$, check for $|0\rangle^{\otimes n}$ | $H^{\otimes n}$, read $|s\rangle$ |
| Output | one bit (constant or balanced) | $n$ bits (the secret) |
| Queries | 1 versus $2^{n-1}+1$ classical | 1 versus $n$ classical |
| Error | none (exact) | none (exact) |

The shared insight is that a function's global structure can be encoded in
phases and extracted by interference. Once you see BV, Simon's algorithm and
the period-finding core of Shor's are variations on the same theme.

## Practical example

### Recovering every possible secret

```python
import numpy as np

H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)


def kron_all(ops):
    r = np.array([[1]], dtype=complex)
    for o in ops:
        r = np.kron(r, o)
    return r


def hadamards(n):
    return kron_all([H] * n)


def oracle_phase(n, s):
    """The oracle in phase-kickback form: |x> -> (-1)^{s.x}|x>."""
    dim = 1 << n
    M = np.zeros((dim, dim), dtype=complex)
    for x in range(dim):
        M[x, x] = (-1) ** (bin(x & s).count("1") % 2)
    return M


def bernstein_vazirani(n, s):
    Hn = hadamards(n)
    psi = np.zeros(1 << n, dtype=complex)
    psi[0] = 1
    return Hn @ oracle_phase(n, s) @ Hn @ psi


print("every secret recovered exactly:")
for n in (2, 3, 4):
    Hn = hadamards(n)
    psi = np.zeros(1 << n, dtype=complex)
    psi[0] = 1
    all_ok = True
    for s in range(1 << n):
        out = Hn @ oracle_phase(n, s) @ Hn @ psi
        expected = np.zeros(1 << n)
        expected[s] = 1
        all_ok &= np.allclose(np.abs(out), expected)
    print(f"  n={n}: all {1 << n} strings correct: {all_ok}")
```

### The worked example, state by state

```python
n, s = 3, 5          # s = 101 in binary
Hn = hadamards(n)
psi = np.zeros(1 << n, dtype=complex)
psi[0] = 1

step1 = Hn @ psi
step2 = oracle_phase(n, s) @ step1
step3 = Hn @ step2

print(f"secret s = {s} = {s:0{n}b}")
print("  after H^n   :", np.round(step1.real, 4))
print("  after oracle:", np.round(step2.real, 4))
print("  after H^n   :", np.round(step3.real, 4))
print("  measured index:", int(np.argmax(np.abs(step3))))
```

Running the blocks in order confirms all 28 cases at $n = 2,3,4$ and prints the
intermediate states, showing that the oracle changes only the **signs** of the
amplitudes.

## Common misconceptions

- **"The oracle is evaluated on all inputs simultaneously, so it is parallel
  computation."** Not quite. One coherent query produces one phase pattern; the
  second Hadamard layer is what converts it into a readable answer. Without the
  interference step you learn nothing.
- **"This means quantum computers are exponentially faster."** The separation
  here is $n$ versus 1 — linear. It is a real separation, but BV is not the
  exponential case.
- **"The ancilla must be measured."** It must not be. It returns to
  $|{-}\rangle$ and simply carries the kickback mechanism.
- **"The oracle needs to be a phase gate."** It can be a standard
  $|x\rangle|y\rangle \mapsto |x\rangle|y\oplus f(x)\rangle$ oracle; the
  $|{-}\rangle$ ancilla turns it into a phase automatically.
- **"One query is enough for any function."** Only for functions with the
  promised structure $f(x) = s\cdot x$.

## Exercises

1. Trace the circuit for $n = 2$, $s = 11$ by hand and confirm the output is
   $|11\rangle$.
2. Show that $H^{\otimes n}$ applied to $|s\rangle$ gives
   $\frac{1}{\sqrt{2^n}}\sum_x(-1)^{s\cdot x}|x\rangle$.
3. Explain why the algorithm is deterministic — where does the probability
   come from in other algorithms but not this one?
4. What happens if you forget the final $H^{\otimes n}$ and measure
   immediately? What would you observe?
5. Compare the query complexity with Deutsch-Jozsa. Which has the larger
   classical lower bound, and why?
6. Suppose the oracle is noisy and flips a sign with probability $\epsilon$.
   How would you make the answer reliable?

## Summary

- Bernstein-Vazirani recovers a hidden string $s$ from $f(x) = s\cdot x$ in **one** quantum query, against **$n$** classical queries.
- The circuit is $H^{\otimes n}$, oracle with a $|{-}\rangle$ ancilla, then $H^{\otimes n}$ and measure.
- The oracle acts as a **phase**: $|x\rangle \mapsto (-1)^{s\cdot x}|x\rangle$, leaving the ancilla untouched.
- The second Hadamard layer works because $H^{\otimes n}|s\rangle$ is precisely the phase state the oracle produced.
- Verified for all 28 secret strings at $n = 2,3,4$ — recovered exactly, with no sampling.
- The separation is $n$ versus 1 in the **query model**: genuine, but linear rather than exponential.

## References

- Bernstein, E. & Vazirani, U. (1997), "Quantum complexity theory" — the
  original algorithm and the recursive Fourier sampling separation.
- The [Deutsch-Jozsa algorithm](05_deutsch_jozsa.md) lesson — the same
  phase-kickback pattern with a different promise.
- The [Simon's Algorithm](34_simon.md) lesson — the exponential version of this
  idea.

---

**Next:** [Simon's Algorithm](34_simon.md)
