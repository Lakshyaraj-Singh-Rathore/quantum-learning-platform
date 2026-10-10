# Quantum Walks

A classical random walk spreads like gossip: slowly, with distance growing as
the square root of time. A quantum walk spreads like a wavefront: linearly,
because amplitudes that would cancel do so and amplitudes that reinforce add
coherently. That difference in spreading is the engine behind a whole family of
quantum algorithms, including optimal ones for searching graphs and for
element distinctness.

## Learning objectives

By the end of this lesson you should be able to:

- **Define** a discrete-time quantum walk with a coin operator, and state the
  two registers it acts on.
- **Contrast** quantum walk spreading with classical diffusion, using the
  standard deviation as the measure.
- **State** an algorithmic application of quantum walks, and explain why the
  speed-up arises.

## Prerequisites

This lesson assumes the [Grover's Algorithm](06_grover.md) background — not as a
formal dependency, but because the connection to search is the payoff. It
assumes the Hadamard gate and the idea of a conditional operation.

## Intuition

### Classical diffusion

Flip a coin. Heads, step right; tails, step left. After $t$ steps you are
typically about $\sqrt{t}$ away from where you started. The distribution is
Gaussian, centred on the origin, and spreading slows down relative to the number
of steps.

### Quantum interference changes the shape

In a quantum walk the "coin" is a unitary that puts the walker into a
superposition of directions, and the shift moves it conditionally. Because the
walker's state is a set of **amplitudes** rather than probabilities, paths
interfere. Paths that wander cancel; paths that go ballistically outward
reinforce. The result is a distribution that spreads **linearly** in time, with
most of its weight near the two moving wavefronts rather than at the centre.

## The discrete-time walk

### Two registers

A discrete-time quantum walk acts on two registers:

- A **position** register $|x\rangle$, holding the walker's location.
- A **coin** register $|\!\uparrow\rangle, |\!\downarrow\rangle$, holding the
  direction.

One step is the composition of two operations:

1. **Coin.** Apply a unitary to the coin register — the Hadamard $H$ is the
   standard choice, since it is the fair-coin analogue.
2. **Shift.** Move the walker conditionally on the coin:
   $|\!\uparrow\rangle|x\rangle \mapsto |\!\uparrow\rangle|x+1\rangle$ and
   $|\!\downarrow\rangle|x\rangle \mapsto |\!\downarrow\rangle|x-1\rangle$.

Both are unitary, so the composition is unitary and the walk is reversible.

### Why the starting state matters

The Hadamard coin is symmetric, but the shift treats the two directions
differently, so the walk is not symmetric unless the initial coin state is
chosen carefully. The standard symmetric choice is

$$|\psi_0\rangle = \tfrac{1}{\sqrt2}\big(|\!\downarrow\rangle + i|\!\uparrow\rangle\big)|0\rangle$$

This produces the balanced distribution used in the measurements below. With
the naive choice $|\!\downarrow\rangle|0\rangle$ the walk is lopsided — a
detail worth knowing, because it is an easy way to get a wrong-looking
distribution.

## Ballistic versus diffusive spreading

### The measurement

Run both walks for $t$ steps and compute the standard deviation $\sigma$ of the
position distribution. Verified results:

| Steps $t$ | Quantum $\sigma$ | Classical $\sigma$ | $\sigma_Q/t$ | $\sigma_C/\sqrt{t}$ |
|---|---|---|---|---|
| 5 | 2.828 | 2.236 | 0.566 | 1.000 |
| 10 | 5.473 | 3.162 | 0.547 | 1.000 |
| 20 | 10.844 | 4.472 | 0.542 | 1.000 |
| 40 | 21.659 | 6.325 | 0.541 | 1.000 |
| 60 | 32.479 | 7.746 | 0.541 | 1.000 |

Read the last two columns. The ratio $\sigma_C/\sqrt{t}$ is **exactly 1.000** at
every $t$ — that is textbook diffusion. The ratio $\sigma_Q/t$ settles to a
constant near $0.54$, confirming $\sigma_Q \propto t$.

So:

$$\sigma_{\text{classical}} \sim \sqrt{t} \qquad\qquad \sigma_{\text{quantum}} \sim t$$

At $t = 60$ the quantum walker has spread $32.5$ positions against the
classical $7.7$ — a factor of about $4.2$, and the ratio grows as $\sqrt{t}$.

### The distribution looks nothing alike

The classical distribution is a single Gaussian hump at the origin. The quantum
distribution at $t = 40$ has its largest peaks near the **edges**, around
$x \approx \pm 27$, with a nearly flat plateau in between:

| Position $x$ | Probability |
|---|---|
| $-28$ | 0.0830 |
| $-26$ | 0.1235 |
| $-22$ | 0.0550 |
| $0$ | 0.0155 |
| $+22$ | 0.0550 |
| $+26$ | 0.1235 |
| $+28$ | 0.0830 |

Most of the probability sits in two outward-moving lobes. That is the
wavefront, and it is why quantum walks reach distant parts of a graph
quadratically faster than classical random walks.

A parity detail: at even times the walker occupies only even positions, so the
distribution is supported on $x = 0, \pm2, \pm4, \ldots$

## An algorithmic application

### Search on a graph

The flagship application is **spatial search**: finding a marked vertex in a
graph. Using a quantum walk, Ambainis's algorithm finds a marked item among $N$
in $O(\sqrt{N})$ steps, matching Grover's optimal bound — and it works on
structured graphs where Grover's flat oracle does not apply.

The reason the walk helps is exactly the spreading behaviour above. A classical
random walk needs $O(N)$ steps to cover a graph, because it diffuses. A quantum
walk mixes in $O(\sqrt{N})$, because it moves ballistically.

### Element distinctness

Ambainis's element-distinctness algorithm decides whether a list of $N$ numbers
contains a duplicate in $O(N^{2/3})$ queries, beating the classical
$\Omega(N \log N)$ sorting lower bound for this formulation. It uses a quantum
walk on a Johnson graph. This was one of the first quantum algorithms to beat
the best known classical method for a natural problem, and the walk structure is
essential to it.

### Continuous-time walks

There is a second formulation with no coin at all: a **continuous-time** walk
evolves under $e^{-iHt}$ where $H$ is the adjacency matrix of the graph. It is
simpler to analyse and to simulate, and it is the natural model for
Hamiltonian-based hardware. Childs's algorithm uses a continuous-time walk to
traverse a glued-trees graph exponentially faster than any classical algorithm —
a genuinely exponential separation, though for a contrived graph.

## Limits and caveats

### Measurement destroys the walk

You cannot watch the walker. Measuring the position collapses the state and
restarts the walk from a classical distribution. The speed-up requires running
coherently and measuring once at the end.

### The coin choice matters

The Hadamard coin is the canonical choice on a line, but other coins give
different distributions, and on other graphs the coin must be redesigned. A
"quantum walk" is not one algorithm but a family.

### Decoherence turns it classical

If the position register decoheres, the interference that produces ballistic
spreading is lost and the walk reverts to diffusive behaviour. Quantum walks are
therefore sensitive to exactly the noise that affects every other quantum
algorithm.

### The speed-up is problem-dependent

Ballistic spreading guarantees faster *mixing*. Whether that yields a faster
algorithm depends on the graph and the task — it is not automatic.

## Practical example

### Both walks on a line

```python
import numpy as np

H_COIN = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)


def quantum_walk_line(steps, size=129):
    """Hadamard coin + conditional shift. Returns the 2 x size amplitude array."""
    c = size // 2
    psi = np.zeros((2, size), dtype=complex)
    psi[0, c] = 1 / np.sqrt(2)          # |down>
    psi[1, c] = 1j / np.sqrt(2)         # |up>  (symmetric start)

    for _ in range(steps):
        new = np.zeros_like(psi)
        new[0] = (psi[0] + psi[1]) / np.sqrt(2)     # coin
        new[1] = (psi[0] - psi[1]) / np.sqrt(2)
        shift = np.zeros_like(new)
        shift[0, :-1] = new[0, 1:]                  # down -> x-1
        shift[1, 1:] = new[1, :-1]                  # up   -> x+1
        psi = shift
    return psi


def classical_walk_line(steps, size=129):
    c = size // 2
    p = np.zeros(size)
    p[c] = 1.0
    for _ in range(steps):
        q = np.zeros(size)
        q[:-1] += 0.5 * p[1:]
        q[1:] += 0.5 * p[:-1]
        p = q
    return p


def sigma(dist, size=129):
    c = size // 2
    xs = np.arange(size) - c
    mean = np.sum(xs * dist)
    return np.sqrt(np.sum(xs ** 2 * dist) - mean ** 2)


print("steps   quantum_sigma  classical_sigma   q/t     c/sqrt(t)")
for t in (5, 10, 20, 40, 60):
    qd = np.sum(np.abs(quantum_walk_line(t)) ** 2, axis=0)
    sq, sc = sigma(qd), sigma(classical_walk_line(t))
    print(f"{t:5d}   {sq:13.4f}  {sc:15.4f}   {sq / t:.4f}   "
          f"{sc / np.sqrt(t):.4f}")
```

### The shape of the quantum distribution

```python
psi = quantum_walk_line(40)
qd = np.sum(np.abs(psi) ** 2, axis=0)
xs = np.arange(129) - 64
print("\nquantum walk distribution at t=40 (probabilities above 0.05):")
for i in range(129):
    if qd[i] > 0.05:
        print(f"   x={xs[i]:+4d}   P={qd[i]:.5f}")
print(f"\nprobability at the centre: {qd[64]:.5f}")
print("note the peaks sit near the EDGES, not the centre")
```

Running the blocks in order reproduces the spreading table — including
$\sigma_C/\sqrt{t} = 1.0000$ exactly at every step — and shows the two
outward-moving lobes of the quantum distribution.

## Common misconceptions

- **"A quantum walk is a random walk on a quantum computer."** There is nothing
  random until measurement. The dynamics are unitary and reversible.
- **"The walker spreads to $\sqrt{t}$ like a classical walk."** It spreads
  linearly; that is the whole point.
- **"You can watch the walker move."** Measuring collapses it and destroys the
  coherent spreading.
- **"Any coin works."** The coin determines the distribution, and a naive
  starting state produces a lopsided walk.
- **"Faster mixing automatically means a faster algorithm."** It depends on the
  graph and the task.

## Exercises

1. Run the walk with the naive starting state $|\!\downarrow\rangle|0\rangle$
   and describe how the distribution differs.
2. Verify that $\sigma_C = \sqrt{t}$ exactly for the classical walk.
3. Why does the quantum walk occupy only even positions at even times?
4. What happens to the spreading if you apply a phase flip to the coin at one
   specific position (a "marked" vertex)?
5. Explain why decoherence in the position register restores diffusive
   spreading.
6. Compare discrete-time and continuous-time walks: what does each require?

## Summary

- A discrete-time quantum walk acts on a **position** and a **coin** register,
  alternating a coin unitary (usually $H$) with a conditional shift.
- The symmetric starting state
  $\tfrac{1}{\sqrt2}(|\!\downarrow\rangle + i|\!\uparrow\rangle)$ avoids a
  lopsided walk.
- **Quantum spreading is ballistic, $\sigma \sim t$; classical is diffusive,
  $\sigma \sim \sqrt{t}$.** Verified: $\sigma_Q/t$ settles near $0.54$ while
  $\sigma_C/\sqrt{t}$ is exactly $1.000$.
- The quantum distribution peaks near the **edges** with a flat middle, unlike
  the classical Gaussian.
- Applications include spatial search in $O(\sqrt{N})$ and element distinctness
  in $O(N^{2/3})$.
- Measurement collapses the walk, and decoherence restores classical diffusion.

## References

- Ambainis, A. (2007), "Quantum walk algorithm for element distinctness" — the
  $O(N^{2/3})$ algorithm.
- Childs, A. M. et al. (2003), "Exponential algorithmic speedup by a quantum
  walk" — the glued-trees exponential separation.
- Kempe, J. (2003), "Quantum random walks: an introductory overview".
- The [Grover's Algorithm](06_grover.md) lesson — the search bound quantum walks
  match on graphs.

---

**Previous:** [Amplitude Estimation](36_amplitude_estimation.md)
