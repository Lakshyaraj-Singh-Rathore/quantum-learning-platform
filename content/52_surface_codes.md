# Surface Codes

The codes in the previous lessons were chosen because they are small enough to
write down. None of them is what a real machine would use. Surface codes are:
they combine a high threshold, stabilisers that touch only a handful of
neighbouring qubits, and a layout that fits on a flat chip. Every major
superconducting and neutral-atom error-correction programme today is built on
some variant of them.

## Learning objectives

By the end of this lesson you should be able to:

- **Describe** the stabiliser layout of a rotated surface code: where the data
  qubits sit, which plaquettes carry $X$-type and which carry $Z$-type checks,
  and how many generators a distance-$d$ patch has.
- **Explain** how the code distance sets the error-correcting power, and what a
  syndrome actually tells you about where an error chain began and ended.
- **State** why surface codes suit nearest-neighbour hardware, and what that
  claim does and does not guarantee.

## Prerequisites

[Stabilizer Formalism](51_stabilizer_formalism.md). This lesson uses
$[[n,k,d]]$ notation, the normaliser $N(S)$, and the binary symplectic
commutation test without re-explaining them.

## Why a lattice?

Every code you have met so far has a fixed size: three qubits, five, seven, nine.
Once you pick one, its error-correcting power is fixed, and improving it means
switching to a different construction.

Surface codes are a **family**. You pick a distance $d$, lay out a $d \times d$
patch of qubits, and read off the performance. Bigger patch, better protection —
with no change to the rules. That tunability is what makes them engineering
material rather than a textbook example.

The second attraction is locality. Every stabiliser acts on qubits that sit next
to each other on the lattice. That is the difference between a code you can
actually measure on a chip and one that requires wiring every qubit to every
other.

## A convention, stated up front

"Surface code" names a family, not one object, and the variants differ in qubit
counts and layouts. Mixing them produces wrong numbers, so this lesson fixes one
convention and uses it throughout.

| Variant | Data qubits for distance $d$ | Topology |
|---|---|---|
| **Rotated surface code** (used here) | $d^2$ | planar patch, one logical qubit |
| Unrotated (planar) surface code | $2d^2 - 2d + 1$ | planar patch, one logical qubit |
| Toric code | $2d^2$ | closed torus, **two** logical qubits |

This lesson uses the **rotated** surface code: the most compact planar version,
and the one behind most recent hardware demonstrations. The toric code is its
closed-surface cousin and encodes two logical qubits because a torus has no
boundary — do not carry that count over to the planar case.

## The layout

Place $d^2$ **data qubits** on a $d \times d$ grid, with odd $d$. Qubit $(r, c)$
sits at row $r$, column $c$, indexed $r \cdot d + c$.

A **stabiliser** sits at the centre of each square cell of the grid and acts on
the data qubits at that cell's corners. There are two kinds:

- **$Z$-type plaquettes** — the product of $Z$ on the four corners. These detect
  $X$ (bit-flip) errors.
- **$X$-type plaquettes** — the product of $X$ on the four corners. These detect
  $Z$ (phase-flip) errors.

The two kinds alternate in a checkerboard: a cell at $(r, c)$ is $Z$-type where
$r + c$ is even and $X$-type where $r + c$ is odd. That alternation is what makes
the code work — two neighbouring plaquettes share exactly two qubits, so their
operators overlap in two positions and commute.

At the edges of the patch a cell has no fourth corner, so the stabiliser is cut
down to the two qubits that exist: a **weight-2 boundary plaquette**. $X$-type
pairs sit on the top and bottom rows; $Z$-type pairs sit on the left and right
columns.

Counting gives the generator total:

$$(d-1)^2 \text{ bulk} \;+\; 4\cdot\tfrac{d-1}{2} \text{ boundary} \;=\; (d-1)^2 + 2(d-1) \;=\; d^2 - 1$$

which is exactly $n - k$ for $n = d^2$ and $k = 1$.

## Worked example: the distance-3 patch

Nine data qubits, eight stabilisers. Verified below as $[[9,1,3]]$.

```
        column 0   1   2
row 0     q0     q1  q2
row 1     q3     q4  q5
row 2     q6     q7  q8
```

The eight generators, with qubit coordinates as $(r, c)$:

| Generator | Kind | Type | Acts on |
|---|---|---|---|
| $g_0$ | bulk | $Z$ | $(0,0)\ (0,1)\ (1,0)\ (1,1)$ |
| $g_1$ | bulk | $X$ | $(0,1)\ (0,2)\ (1,1)\ (1,2)$ |
| $g_2$ | bulk | $X$ | $(1,0)\ (1,1)\ (2,0)\ (2,1)$ |
| $g_3$ | bulk | $Z$ | $(1,1)\ (1,2)\ (2,1)\ (2,2)$ |
| $g_4$ | boundary | $X$ | $(0,0)\ (0,1)$ |
| $g_5$ | boundary | $X$ | $(2,1)\ (2,2)$ |
| $g_6$ | boundary | $Z$ | $(1,0)\ (2,0)$ |
| $g_7$ | boundary | $Z$ | $(0,2)\ (1,2)$ |

Four $X$-type and four $Z$-type. Check one commutation by hand: $g_0$ is
$Z$-type on $\{q_0, q_1, q_3, q_4\}$ and $g_1$ is $X$-type on
$\{q_1, q_2, q_4, q_5\}$. They differ at $q_1$ and $q_4$ — two positions, which
is even, so they commute. Two $X$-type or two $Z$-type generators always commute.

## Verifying the parameters

Enumerating the stabiliser group is the wrong tool here: for $d = 5$ it has
$2^{24}$ elements. Everything below is decided with binary linear algebra over
$\mathbb{F}_2$, which is polynomial time.

```python
import numpy as np
from itertools import combinations


def rotated_surface(d):
    """Generators of the rotated [[d^2, 1, d]] surface code.

    Data qubit (r, c) -> index r*d + c.  Bulk plaquettes act on the four
    corners of each unit cell, Z-type where (r+c) is even and X-type where it
    is odd.  Boundary plaquettes are weight 2: X-type pairs on the top and
    bottom rows, Z-type pairs on the left and right columns.
    """
    n = d * d
    idx = lambda r, c: r * d + c
    def mk(qs, P):
        s = ["I"] * n
        for q in qs:
            s[q] = P
        return "".join(s)

    gens = []
    for r in range(d - 1):
        for c in range(d - 1):
            P = "X" if (r + c) % 2 == 1 else "Z"
            gens.append(mk([idx(r, c), idx(r, c + 1),
                            idx(r + 1, c), idx(r + 1, c + 1)], P))
    for c in range(0, d - 1, 2):
        gens.append(mk([idx(0, c), idx(0, c + 1)], "X"))
    for c in range(1, d - 1, 2):
        gens.append(mk([idx(d - 1, c), idx(d - 1, c + 1)], "X"))
    for r in range(1, d - 1, 2):
        gens.append(mk([idx(r, 0), idx(r + 1, 0)], "Z"))
    for r in range(0, d - 1, 2):
        gens.append(mk([idx(r, d - 1), idx(r + 1, d - 1)], "Z"))
    return n, gens
```

### Checking the construction with GF(2) linear algebra

Each Pauli is stored as a $2n$-bit vector $(a \mid b)$: $a_i = 1$ when qubit $i$
carries $X$ or $Y$, $b_i = 1$ when it carries $Z$ or $Y$. Two Paulis anticommute
exactly when the symplectic inner product $a \cdot b' + b \cdot a'$ is odd.

```python
def symvec(s):
    """(x-part | z-part) over GF(2)."""
    a = np.array([1 if ch in "XY" else 0 for ch in s], dtype=np.uint8)
    b = np.array([1 if ch in "ZY" else 0 for ch in s], dtype=np.uint8)
    return np.concatenate([a, b])


def anticommutes(u, v):
    """1 iff the two Paulis anticommute."""
    n = len(u) // 2
    return int((u[:n] @ v[n:] + u[n:] @ v[:n]) % 2)


def rref(M):
    M = np.array(M, dtype=np.uint8).copy()
    rows, cols = M.shape
    rank, piv = 0, []
    for c in range(cols):
        p = next((r for r in range(rank, rows) if M[r, c]), None)
        if p is None:
            continue
        M[[rank, p]] = M[[p, rank]]
        for r in range(rows):
            if r != rank and M[r, c]:
                M[r] ^= M[rank]
        piv.append(c)
        rank += 1
    return M[:rank], piv
```

With those in place the structural facts are three lines each. `n = 9`,
`len(gens) = 8`, and all 28 pairs commute; the eight generators are linearly
independent over $\mathbb{F}_2$, so $k = n - r = 9 - 8 = 1$.

### Verified parameters

The table below is what those checks return.

| $d$ | $n = d^2$ | Generators | All commute | $\mathbb{F}_2$ rank | Independent | $k$ | Locality | $d_X$ | $d_Z$ |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 9 | 8 | yes | 8 | yes | 1 | every check inside a $2\times2$ block | 3 | 3 |
| 5 | 25 | 24 | yes | 24 | yes | 1 | every check inside a $2\times2$ block | 5 | 5 |
| 7 | 49 | 48 | yes | 48 | yes | 1 | every check inside a $2\times2$ block | — | — |
| 9 | 81 | 80 | yes | 80 | yes | 1 | every check inside a $2\times2$ block | — | — |
| 11 | 121 | 120 | yes | 120 | yes | 1 | every check inside a $2\times2$ block | — | — |
| 13 | 169 | 168 | yes | 168 | yes | 1 | every check inside a $2\times2$ block | — | — |

The generator count is $d^2 - 1$ and the rank matches it in every row, so the
generators are independent and $k = 1$ throughout. Distance is listed only where
it was computed exhaustively, at $d = 3$ and $d = 5$.

### How the distance was computed

For a CSS code the search for a logical operator splits in two, and neither half
needs the stabiliser group. A $Z$-type logical operator is a set of qubits $z$
such that

$$H_X z = 0 \pmod 2 \quad\text{and}\quad z \notin \mathrm{rowspan}(H_Z)$$

where $H_X$ is the binary matrix whose rows are the supports of the $X$-type
stabilisers, and $H_Z$ likewise for the $Z$-type ones. The first condition says
"commutes with every $X$ check"; the second says "is not itself a product of
$Z$ checks", which is the row-space test that replaces enumerating $2^{24}$
group elements. The $X$-distance is the mirror image. Searching supports by
increasing weight and stopping at the first hit gives $d_X = d_Z = 3$ for $d = 3$
and $d_X = d_Z = 5$ for $d = 5$ — the whole computation runs in under a second.

For larger $d$ the same search becomes expensive, and the distance follows
instead from the geometry: any $Z$-type logical operator must form a chain
stretching from one $Z$-boundary to the other, and on a $d \times d$ patch no
such chain can use fewer than $d$ qubits. An explicit chain of exactly weight
$d$ exists, so the bound is tight.

## Logical operators

The minimum-weight logical operators the search returns are beautifully simple:

| $d$ | $X_L$ | $Z_L$ | Weight each | Anticommute? |
|---|---|---|---|---|
| 3 | $X$ on column 0 | $Z$ on row 0 | 3 | yes, overlap at $(0,0)$ |
| 5 | $X$ on column 0 | $Z$ on row 0 | 5 | yes, overlap at $(0,0)$ |
| 7 | $X$ on column 0 | $Z$ on row 0 | 7 | yes, overlap at $(0,0)$ |
| 9 | $X$ on column 0 | $Z$ on row 0 | 9 | yes, overlap at $(0,0)$ |
| 11 | $X$ on column 0 | $Z$ on row 0 | 11 | yes, overlap at $(0,0)$ |
| 13 | $X$ on column 0 | $Z$ on row 0 | 13 | yes, overlap at $(0,0)$ |

```
d = 5, X_L (a vertical chain)          d = 5, Z_L (a horizontal chain)

   X . . . .                              Z Z Z Z Z
   X . . . .                              . . . . .
   X . . . .                              . . . . .
   X . . . .                              . . . . .
   X . . . .                              . . . . .
```

Verified for each $d$ in the table: both operators commute with **all**
stabilisers, they anticommute with each other (they meet at exactly one qubit,
$(0,0)$), and neither lies in the row space of its own type's check matrix, so
neither is a stabiliser.

The geometric picture is the point. $X_L$ is a chain of $X$ operators running
from the top boundary to the bottom; $Z_L$ runs from the left boundary to the
right. Each has to span the whole patch. Any operator that fails to span it is
either a stabiliser or something the stabilisers detect. The distance $d$ is
literally the length of the shortest chain that crosses the patch.

This is also why the boundary placement matters. $X$-type checks sit on the top
and bottom rows, so a vertical $X$ chain terminates on them and is invisible;
$Z$-type checks sit on the left and right columns, so a horizontal $Z$ chain
terminates on them. Swap the boundaries and these chains would be detected.

## Distance and error-correcting power

As always,

$$t = \left\lfloor \frac{d-1}{2} \right\rfloor$$

arbitrary errors are corrected and $d - 1$ are detected. For the rotated code:

| $d$ | Physical qubits $d^2$ | Corrects $t$ | Detects |
|---|---|---|---|
| 3 | 9 | 1 | 2 |
| 5 | 25 | 2 | 4 |
| 7 | 49 | 3 | 6 |
| 9 | 81 | 4 | 8 |
| 11 | 121 | 5 | 10 |
| 21 | 441 | 10 | 20 |
| 31 | 961 | 15 | 30 |

Doubling the error-correcting power costs four times the qubits, since
$n = d^2$ and $t \approx d/2$. That quadratic overhead is the price of the
code's locality, and it is why [the overhead lesson](53_logical_physical_qubits.md)
is a separate topic.

## Syndromes: the endpoints of a chain

Measuring all $d^2 - 1$ stabilisers gives $d^2 - 1$ bits. For a CSS code an $X$
error anticommutes only with $Z$-type checks and a $Z$ error only with $X$-type
checks, so the two error types never mix in the syndrome.

Verified on the $d = 5$ patch, listing which stabilisers light up:

| Injected error | Plaquettes that light up |
|---|---|
| $X$ on $(0,0)$ | $g_0$ (bulk $Z$) |
| $X$ on $(2,2)$ | $g_5$, $g_{10}$ (both bulk $Z$) |
| $X$ on $(4,4)$ | $g_{15}$ (bulk $Z$) |
| $X$ on $(2,0)$ | $g_8$ (bulk $Z$), $g_{20}$ (boundary $Z$) |

A single error in the bulk lights up the two plaquettes sharing that qubit. A
single error on the boundary can light up only one.

### Chains and their endpoints

Now the important case — two adjacent errors:

| Injected errors | Plaquettes that light up |
|---|---|
| $X$ on $(2,2)$ | $g_5$, $g_{10}$ |
| $X$ on $(2,3)$ | $g_7$, $g_{10}$ |
| $X$ on **both** | $g_5$, $g_{7}$ — and **not** $g_{10}$ |

$g_{10}$ is touched by both errors, and $1 + 1 = 0$ over $\mathbb{F}_2$, so it
cancels. The syndrome of a chain is only its **two endpoints**; everything in
the middle of the chain is invisible.

That single fact is the whole theory of surface-code decoding. The syndrome
never tells you where the errors are. It tells you where error chains *end*, and
the decoder's job is to pair those endpoints up with the shortest, most likely
chains that could have produced them. For this code that matching problem is
solvable efficiently (minimum-weight perfect matching), which is a large part of
why surface codes are practical.

It is also where the notion of "correcting $t$ errors" gets subtle. Correction
succeeds as long as the decoder's guessed chain differs from the true chain by a
closed loop — a product of stabilisers, which acts trivially on the code space.
A decoder can therefore recover from more than $t$ errors, sometimes; it is just
never *guaranteed* to beyond $t$. Once chains grow long enough to connect
opposite boundaries, the decoder guesses wrong and a logical error is applied
silently.

## Why nearest-neighbour hardware

This is the property that separates surface codes from everything else in the
family, and it is verified rather than asserted: **every stabiliser generator
acts only on qubits inside a single $2 \times 2$ block of the grid.** Across all
$d$ from 3 to 13, the largest row span and the largest column span of any
generator are both exactly 1.

Three consequences follow.

**Syndrome extraction needs only local gates.** Each plaquette gets one ancilla
placed at its centre and interacts with the four data qubits around it — its
immediate neighbours. No gate spans the chip. Repeated SWAPs to bring distant
qubits together are unnecessary, and those SWAPs are exactly what would
otherwise eat the error budget.

**The layout is planar.** All qubits and all couplers sit in a flat two-
dimensional grid with no crossings. Real superconducting and neutral-atom
processors are laid out this way because that is what lithography and optical
tweezers can build.

**The threshold is comparatively high.** Because each check is local and
weight-4, a fault in the extraction circuit corrupts only a few qubits, and the
code tolerates a physical error rate around the $10^{-2}$ mark under a
circuit-level noise model. That number is a property of the *decoder and noise
model used in the analysis*, not a physical constant — see
[the threshold theorem](54_threshold_theorem.md) for what it does and does not
promise.

What the locality claim does **not** give you: it says nothing about whether a
particular device can run a surface code. That depends on the actual gate
fidelities, the measurement fidelity, the ability to reset ancillas and reuse
them, and whether the device can do mid-circuit measurement at all.

## Overhead and limitations

- **Quadratic qubit cost.** One logical qubit costs $d^2$ data qubits, plus one
  ancilla per plaquette if each check is measured with its own — roughly
  $2d^2 - 1$ physical qubits in total. A distance-31 patch needs on the order of
  a thousand physical qubits for one logical qubit.
- **One logical qubit per patch.** The rotated planar code encodes $k = 1$.
  Computation needs many patches and lattice-surgery or braiding operations
  between them; the routing overhead is additional.
- **Measurement is the hard part in practice.** Syndrome extraction is a
  quantum circuit that can itself fail, and it is repeated continuously. The
  extraction circuit, not the code, is usually the bottleneck.
- **Decoding must keep up.** The decoder has to run faster than syndromes
  arrive, or the backlog grows without bound. This is a systems problem, not a
  coding-theory one.
- **The distance is a guarantee, not a forecast.** Real performance depends on
  the noise being local and roughly independent. Correlated error — a cosmic
  ray, a control glitch, a drifting calibration — violates the assumption and
  can defeat a code of any distance.

## Common misconceptions

- **"Distance $d$ means the code corrects $d$ errors."** It corrects
  $\lfloor (d-1)/2\rfloor$ with certainty and detects $d - 1$. A $d = 5$ patch
  guarantees correction of two errors.
- **"The syndrome tells you where the error is."** It tells you where error
  chains *end*. A two-error chain and a single different error can produce the
  identical syndrome.
- **"All surface codes use $d^2$ qubits."** That is the rotated variant. The
  unrotated planar code uses $2d^2 - 2d + 1$ and the toric code uses $2d^2$ —
  and encodes two logical qubits, not one.
- **"Locality means any 2D chip can run one."** It means the code *can* be laid
  out on a 2D grid. Whether it works depends on the device's error rates and
  its ability to measure and reset mid-circuit.
- **"A high threshold means error correction is solved."** The threshold
  concerns an idealised noise model. Real devices add leakage, crosstalk and
  correlated errors that the standard analysis does not include.
- **"A $Z$-type plaquette detects $Z$ errors."** It detects $X$ errors, because
  only $X$ anticommutes with $Z$. The naming refers to the stabiliser's own
  Pauli type, not to what it catches.

## Exercises

1. In the $d = 3$ patch, which stabilisers does a single $X$ error on qubit
   $(1,1)$ anticommute with? Work it out from the generator table and check your
   answer against the rule "the plaquettes containing that qubit".

2. Explain why two neighbouring bulk plaquettes always commute, using the
   overlap count.

3. A rotated surface code uses 169 data qubits. What is its distance, how many
   stabiliser generators does it have, and how many errors does it correct?

4. Why does the syndrome of the two-error chain $X$ on $(2,2)$ and $X$ on
   $(2,3)$ not include $g_{10}$?

5. What is $X_L$ for the $d = 3$ patch, and what is its weight? Verify that it
   commutes with $g_0$ by counting positions.

6. A device offers a 2D grid of qubits with nearest-neighbour coupling only,
   gate fidelity $99.9\%$, and mid-circuit measurement. Is that sufficient to
   run a surface code? Explain what the locality result does and does not
   establish.

### Answers to 1–3

**1.** Qubit $(1,1)$ appears in $g_0$ (bulk $Z$), $g_1$ (bulk $X$),
$g_2$ (bulk $X$) and $g_3$ (bulk $Z$). An $X$ error anticommutes only with
$Z$-type stabilisers, so it flips **$g_0$ and $g_3$** — the two $Z$-plaquettes
sharing the qubit — and leaves the two $X$-plaquettes alone. That is the
expected bulk signature: two adjacent checks light up.

**2.** Two neighbouring bulk plaquettes share the two qubits on their common
edge, and nothing else. Both carry Paulis on those two shared qubits. If they
are the same type they commute trivially; if they differ in type, they differ at
exactly those two shared positions, which is an even number, so they commute.
Even overlap, always.

**3.** $n = d^2 = 169$, so $d = 13$. Generators: $d^2 - 1 = 168$. Errors
corrected: $t = \lfloor (13-1)/2 \rfloor = 6$.

### Answers to 4–6

**4.** $g_{10}$ is a $Z$-type plaquette containing both $(2,2)$ and $(2,3)$. An
$X$ error on either qubit flips it; the two flips are added modulo 2 and cancel,
$1 + 1 = 0$. What survives is $g_5$, touched only by the error on $(2,2)$, and
$g_7$, touched only by the error on $(2,3)$. The syndrome reports the two
endpoints of the chain and nothing in between.

**5.** $X_L$ is the product of $X$ over column 0, i.e. qubits $(0,0)$, $(1,0)$
and $(2,0)$, of weight 3. Against $g_0$, which is $Z$-type on
$(0,0), (0,1), (1,0), (1,1)$: the overlap is $(0,0)$ and $(1,0)$ — two
positions, even — so they commute. $X_L$ also commutes with every $X$-type
stabiliser trivially, and with $g_3$ (no overlap) and with the $Z$-type
boundary pair $g_7$ on $(0,2),(1,2)$ (no overlap).

**6.** Locality establishes that the surface code *can be embedded* in that
architecture: every check acts on neighbours, the layout is planar, and no
long-range gates are required. It does **not** establish that the code will
work. That depends on whether the $0.1\%$ error rate sits below the threshold
for this code and decoder, on the measurement and reset fidelity, on whether
ancillas can be reused across rounds, and on whether correlated errors are
small. All of those are device properties that the code's locality says nothing
about. The answer is therefore "the architecture is compatible; whether the
device is good enough is a separate question".

## Summary

- The **rotated** surface code places $d^2$ data qubits on a $d \times d$ grid
  with one logical qubit. The unrotated planar code uses $2d^2 - 2d + 1$ qubits
  and the toric code uses $2d^2$ for two logical qubits — different conventions
  with different counts.
- Stabilisers are plaquettes: $Z$-type where $r + c$ is even, $X$-type where it
  is odd, weight 4 in the bulk and weight 2 on the boundaries. Total:
  $d^2 - 1$ generators.
- Verified with $\mathbb{F}_2$ linear algebra rather than group enumeration:
  $[[9,1,3]]$ and $[[25,1,5]]$ exactly, and $n = d^2$, $d^2 - 1$ independent
  commuting generators, $k = 1$ for $d = 3$ through $13$.
- $X_L = X$ on column 0 and $Z_L = Z$ on row 0, each of weight $d$, commuting
  with every stabiliser, anticommuting with each other, and neither a
  stabiliser — verified for $d = 3, 5, 7, 9, 11, 13$.
- Distance $d$ means $t = \lfloor (d-1)/2 \rfloor$ errors corrected with
  certainty, at a cost of $d^2$ physical qubits per logical qubit.
- A syndrome reports the **endpoints** of error chains, not the errors
  themselves: two adjacent errors cancel on the plaquette they share. Decoding
  is the problem of pairing endpoints.
- Every check acts inside a single $2 \times 2$ block, so the code needs only
  nearest-neighbour gates on a planar chip — but that is a statement about the
  code's geometry, not a guarantee that any given device can run it.

## References

- Kitaev, A. — the toric code, the topological origin of this family.
- Bravyi, S. B. & Kitaev, A. Yu. — the planar surface code on a lattice with
  boundaries.
- Dennis, E., Kitaev, A., Landahl, A. & Preskill, J. — surface-code decoding as
  a matching problem, and the threshold analysis.
- Fowler, A. G., Mariantoni, M., Martinis, J. M. & Cleland, A. N. — surface-code
  implementation details, lattice surgery and the practical overhead.
- Google Quantum AI, "Suppressing quantum errors by scaling a surface code
  logical qubit" — a recent experimental demonstration of the family.
- [Stabilizer Formalism](51_stabilizer_formalism.md) — the language used
  throughout.
- [Logical and Physical Qubits, and Overhead](53_logical_physical_qubits.md) —
  what $d^2$ qubits per logical qubit actually costs.
- [Threshold Theorem and Fault Tolerance](54_threshold_theorem.md) — what the
  threshold does and does not promise.

---

**Next:** [Logical and Physical Qubits, and Overhead](53_logical_physical_qubits.md)
