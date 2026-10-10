# Quantum Fourier Transform

The QFT is the workhorse inside most of the algorithms that made quantum
computing famous. Phase estimation uses it. Shor's algorithm is phase
estimation wearing a different hat. Amplitude estimation is phase estimation
again. It is worth understanding properly, both because the circuit is elegant
and because what it does *not* do is just as important as what it does.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** the QFT circuit on $n$ qubits, and state its gate count.
- **State** the asymptotic advantage over the classical FFT, and explain the
  important sense in which that advantage is *not* a general speed-up.
- **Explain** what the QFT does to a periodic superposition, and why that is
  the property every application actually exploits.
- **Identify** the bit-ordering convention of a QFT implementation, and predict
  what happens if the final swaps are omitted.

## Prerequisites

This lesson assumes you know the single-qubit gates $H$, $Z$, $S$ and $T$, and
what a controlled gate is. It also assumes the controlled-phase gate
$\text{CP}(\lambda) = \text{diag}(1, 1, 1, e^{i\lambda})$, which applies a
phase only when both qubits are $|1\rangle$.

## Intuition

### What a Fourier transform does

Take a sequence of $N$ numbers and re-express it as a sum of waves of
different frequencies. A signal that repeats with period $r$ has energy at
frequencies that are multiples of $N/r$. The classical FFT finds those
frequencies in $O(N\log N)$ operations.

### What the quantum version does differently

The QFT does not output $N$ numbers. It takes a quantum state whose amplitudes
encode $N$ numbers and maps them to a state whose amplitudes are the Fourier
coefficients — all $2^n$ of them, stored in superposition in $n$ qubits:

$$\text{QFT}|j\rangle = \frac{1}{\sqrt{2^n}}\sum_{k=0}^{2^n-1} e^{2\pi i jk/2^n}|k\rangle$$

That is the whole trick, and it is also the whole limitation. You get
$O(n^2)$ gates instead of $O(n2^n)$, but you cannot read out all $2^n$
coefficients — measuring destroys the superposition and gives you one $k$.

So the QFT is not a drop-in replacement for the FFT. It is useful when you
need a *sample* from the spectrum, or when the spectrum has structure you can
extract with few measurements. Period finding is exactly that case, which is
why the QFT sits at the centre of Shor's algorithm.

## The circuit

### Structure

For $n$ qubits with qubit 0 as the most significant bit, the QFT is built from
$n$ Hadamards and $\binom{n}{2}$ controlled-phase gates:

For each qubit $i$ from $0$ to $n-1$:

1. Apply $H$ to qubit $i$.
2. For each qubit $j > i$, apply a controlled phase of $2\pi/2^{k}$ where
   $k = j - i + 1$, with qubit $j$ as the control and qubit $i$ as the target.

Then reverse the qubit order with $\lfloor n/2 \rfloor$ SWAPs.

The phase angle shrinks with distance: nearest neighbour gets $\pi$, next gets
$\pi/2$, then $\pi/4$, and so on. Gates beyond a few qubits away become
negligibly small, which is why an **approximate QFT** that drops the small
rotations is nearly as good and much cheaper on hardware.

### Gate count

Building the circuit and counting:

| $n$ | Gates built | $n(n+1)/2$ | SWAPs | Classical FFT $\sim n2^n$ |
|---|---|---|---|---|
| 3 | 6 | 6 | 1 | 24 |
| 4 | 10 | 10 | 2 | 64 |
| 5 | 15 | 15 | 2 | 160 |
| 8 | 36 | 36 | 4 | 2048 |
| 10 | 55 | 55 | 5 | 10240 |
| 20 | 210 | 210 | 10 | 20,971,520 |

The count is exactly $n(n+1)/2 = O(n^2)$, against $O(n2^n)$ for the FFT. At
$n = 20$ that is 210 gates against about 21 million — five orders of magnitude.

### Verification and bit ordering

The circuit above was compared against the DFT matrix

$$[\text{DFT}]_{jk} = \frac{1}{\sqrt{2^n}}e^{2\pi i jk/2^n}$$

and matches **exactly** for $n = 2, 3, 4$, with qubit 0 as the most significant
bit of $j$.

If the final SWAPs are omitted, the circuit produces the correct amplitudes in
**reversed qubit order** — comparing it against the DFT with bit-reversed rows
also matches exactly. This is worth knowing, because several implementations
skip the swaps and expect you to reinterpret the output, and getting this
wrong produces answers that look plausible and are subtly incorrect.

## The effect on a periodic superposition

### The property that matters

This is why the QFT appears in every period-finding algorithm. Take a state
with period $r$:

$$|\psi\rangle = \frac{1}{\sqrt{m}}\sum_{t=0}^{m-1} |s + tr\rangle$$

with $m$ terms and offset $s$. Its QFT is concentrated **uniformly** on
multiples of $N/r$, where $N = 2^n$.

### Verified example

For $n = 6$ ($N = 64$):

| Period $r$ | Offset $s$ | Output support | Probability per peak |
|---|---|---|---|
| 4 | 0 | $\{0, 16, 32, 48\}$ | $1/4$ each |
| 8 | 0 | $\{0, 8, 16, 24, 32, 40, 48, 56\}$ | $1/8$ each |
| 4 | 3 | $\{0, 16, 32, 48\}$ | $1/4$ each |

Two things to read off this table:

**The peaks land on multiples of $N/r$.** For $r=4$, $N/r = 16$, and the
support is exactly $\{0, 16, 32, 48\}$. Measure and you get a multiple of
$N/r$; do that a few times and you can recover $r$.

**The offset $s$ does not change the probabilities.** Shifting the input by 3
leaves the support and the probabilities identical. The offset only shifts the
*phases*, and phases are invisible to a computational-basis measurement. That
is extremely convenient: you do not need to know where the period starts.

### Where the quadratic speed-up comes from

A classical algorithm must evaluate the function at many points to find the
period. Here the QFT extracts it from a single periodic state using $O(n^2)$
gates. That is the source of the dramatic cost figures quoted for Shor's
algorithm — and it is why the caveat in the next section matters so much.

## Limits and caveats

### You cannot read out the full spectrum

The QFT prepares $2^n$ Fourier coefficients in $O(n^2)$ gates, but measuring
returns a single $k$ and destroys the rest. If your task genuinely needs all
$2^n$ coefficients, the QFT gives you no advantage — you would need
exponentially many repetitions. The speed-up is real only for tasks solvable
from a few samples, or from a property of the distribution.

### Output precision is limited by the register

The output register has $n$ qubits, so phases are resolved to roughly $1/2^n$.
More precision means more qubits, not more gates.

### Small rotations are the hardware problem

The controlled phases $2\pi/2^k$ for large $k$ are tiny. On real hardware they
may be below the gate-precision floor and contribute mainly error, which is why
approximate QFT — truncating rotations below some threshold — is standard
practice and usually loses very little.

### It is a basis change, not a search

The QFT does not find structure by itself. It reveals periodicity that is
already present in the amplitudes. Feed it a structureless state and you get a
structureless spectrum.

## Practical example

### Building blocks

```python
import numpy as np

H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)


def cp(lam):
    """Controlled-phase diag(1, 1, 1, e^{i lam}), control = more significant."""
    return np.diag([1, 1, 1, np.exp(1j * lam)]).astype(complex)


def expand(U, n, targets, controls=()):
    """Lift a small unitary onto an n-qubit register (qubit 0 = MSB)."""
    dim = 1 << n
    M = np.zeros((dim, dim), dtype=complex)
    for col in range(dim):
        if not all((col >> (n - 1 - c)) & 1 for c in controls):
            M[col, col] = 1
            continue
        k = 0
        for t in targets:
            k = (k << 1) | ((col >> (n - 1 - t)) & 1)
        for k2 in range(1 << len(targets)):
            a = U[k2, k]
            if not a:
                continue
            bits = [(k2 >> (len(targets) - 1 - i)) & 1
                    for i in range(len(targets))]
            r = col
            for t, b in zip(targets, bits):
                r = (r & ~(1 << (n - 1 - t))) | (b << (n - 1 - t))
            M[r, col] += a
    return M


def swap_mat(a, b, n):
    M = np.zeros((1 << n, 1 << n), dtype=complex)
    for col in range(1 << n):
        ba, bb = (col >> (n - 1 - a)) & 1, (col >> (n - 1 - b)) & 1
        r = (col & ~(1 << (n - 1 - a))) | (bb << (n - 1 - a))
        r = (r & ~(1 << (n - 1 - b))) | (ba << (n - 1 - b))
        M[r, col] = 1
    return M
```

### Assembling the circuit and verifying it

```python
def qft_circuit(n, do_swaps=True):
    """Returns (matrix, gate_count)."""
    M, gates = np.eye(1 << n, dtype=complex), 0
    for i in range(n):
        M = expand(H, n, [i]) @ M
        gates += 1
        for j in range(i + 1, n):
            angle = 2 * np.pi / 2 ** (j - i + 1)
            M = expand(cp(angle), n, [j, i], []) @ M   # [control, target]
            gates += 1
    if do_swaps:
        for i in range(n // 2):
            M = swap_mat(i, n - 1 - i, n) @ M
    return M, gates


def dft(n):
    N = 1 << n
    w = np.exp(2j * np.pi / N)
    return (np.array([[w ** (j * k) for k in range(N)] for j in range(N)],
                     dtype=complex) / np.sqrt(N))


print("QFT circuit vs DFT matrix:")
for n in (2, 3, 4):
    Q, g = qft_circuit(n)
    print(f"  n={n}: exact match={np.allclose(Q, dft(n))}  gates={g}"
          f"  n(n+1)/2={n * (n + 1) // 2}")

# omitting the swaps gives a bit-reversed output
n = 3
Qn, _ = qft_circuit(n, do_swaps=False)
rev = [int(f"{i:0{n}b}"[::-1], 2) for i in range(1 << n)]
print("  no-swap variant == DFT with bit-reversed rows:",
      np.allclose(Qn, dft(n)[rev]))
```

### The periodic superposition

```python
n, N = 6, 64
print("\nQFT of a periodic state (n=6, N=64):")
for r, s in ((4, 0), (8, 0), (4, 3)):
    psi = np.zeros(N, dtype=complex)
    for t in range(N // r):
        psi[(s + t * r) % N] = 1 / np.sqrt(N // r)
    out = qft_circuit(n)[0] @ psi
    p = np.abs(out) ** 2
    peaks = [i for i in range(N) if p[i] > 1e-6]
    print(f"  r={r}, offset={s}: support={peaks}"
          f"  uniform 1/r: {np.allclose(p[peaks], 1 / r)}")
```

Running the blocks in order confirms the circuit reproduces the DFT exactly for
$n = 2,3,4$, that the no-swap variant matches the bit-reversed DFT, and that a
periodic input maps uniformly onto multiples of $N/r$ with the offset affecting
only phases.

## Common misconceptions

- **"QFT is a faster FFT."** It computes the transform in $O(n^2)$ gates but
  cannot output the result. Any task needing all $2^n$ coefficients gains
  nothing.
- **"The exponential gate advantage means exponential speed-up."** Only for
  tasks where a few samples suffice. Period finding qualifies; listing the
  spectrum does not.
- **"QFT finds periods by itself."** It reveals periodicity already present in
  the amplitudes.
- **"The final SWAPs are cosmetic."** Omit them and the output is in reversed
  qubit order — correct amplitudes, wrong positions.
- **"All the controlled phases matter equally."** The distant ones are tiny,
  below hardware precision, and dropping them is standard.

## Exercises

1. Write the QFT matrix for $n = 2$ and verify it is unitary.
2. How many gates does the QFT use on 12 qubits? How does this compare with
   the classical FFT cost?
3. A periodic state has $r = 5$ on $n = 6$ qubits. Where do you expect the
   peaks, and why is this case awkward?
4. Explain why shifting a periodic input by a constant leaves the measurement
   probabilities unchanged.
5. If an implementation omits the final swaps, how must you reinterpret a
   measured bit string?
6. Give a task where the QFT provides no advantage over the classical FFT, and
   explain why.

## Summary

- The QFT maps $|j\rangle$ to a uniform superposition with phases
  $e^{2\pi i jk/2^n}$ — $2^n$ Fourier coefficients held in $n$ qubits.
- The circuit uses $n$ Hadamards, $\binom{n}{2}$ controlled phases and
  $\lfloor n/2\rfloor$ SWAPs: **$n(n+1)/2 = O(n^2)$ gates** against
  $O(n2^n)$ for the FFT.
- It was verified to reproduce the DFT matrix **exactly**, and the no-swap
  variant to reproduce the bit-reversed DFT.
- Applied to a state of period $r$, it concentrates **uniformly on multiples
  of $N/r$**; an offset shifts phases only, leaving probabilities unchanged.
- The advantage is real only when a few samples suffice — you cannot read out
  all $2^n$ coefficients, and the QFT reveals periodicity rather than finding
  it.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  §5.1 — the QFT circuit and its derivation.
- Coppersmith, D. — the approximate QFT and which rotations can be dropped.
- The [Quantum Phase Estimation](32_phase_estimation.md) lesson — the main
  consumer of the QFT.
- The [Native Gates, Connectivity and Routing](42_compilation.md) lesson — why
  the QFT's all-to-all pattern is expensive on real hardware.

---

**Next:** [Quantum Phase Estimation](32_phase_estimation.md)
