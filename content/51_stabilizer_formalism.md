# Stabilizer Formalism

The two codes you have met so far were built by inventing a circuit and then
working out what it does. That approach does not scale: describing a code by
listing its codewords becomes hopeless long before you reach the sizes that
matter. The stabiliser formalism replaces the description with something far
smaller — a handful of Pauli operators — and in doing so turns code *design*
into linear algebra over $\mathbb{F}_2$.

This lesson is the one the rest of the error-correction section is written in.
Surface codes, logical operators, code distance and decoding are all stated in
this language.

## Learning objectives

By the end of this lesson you should be able to:

- **Define** a stabiliser group and the code space it fixes, and state the two
  conditions a subgroup of the Pauli group must satisfy to qualify.
- **Determine** the stabilisers of a given code, both by reading them off a
  construction and by searching the Pauli group for the operators that fix the
  codewords.
- **Derive** the syndrome from a set of stabiliser measurement outcomes, and
  explain why distinct errors can share one syndrome.

## Prerequisites

[The Three-Qubit Phase-Flip Code](50_phase_flip_code.md), which in turn assumes
[the bit-flip code](49_bit_flip_code.md). Group theory helps — the stabiliser
group is a group, and the code space is defined by a group action — but
[Group Theory for Quantum Computing](18_group_theory.md) is listed as
recommended rather than required, and nothing below depends on results from it.

## Why bother?

Look at what the two three-qubit codes have in common. Neither is described by
its codewords in any useful way; both are described completely by **two Pauli
operators**:

| Code | Codewords | Stabilisers |
|---|---|---|
| Bit flip | $\alpha|000\rangle + \beta|111\rangle$ | $Z_0Z_1$, $Z_1Z_2$ |
| Phase flip | $\alpha|{+}{+}{+}\rangle + \beta|{-}{-}{-}\rangle$ | $X_0X_1$, $X_1X_2$ |

Two operators instead of a continuous family of states. That compression is the
whole point. A code on $n$ qubits encoding $k$ logical qubits is specified by
$n - k$ stabiliser generators, so a code on 100 qubits needs 99 generators
rather than a $2^{100}$-dimensional vector.

It also makes the *questions* easy. "Can this code correct a single error?"
becomes a commutativity check. "What is the distance?" becomes a shortest-weight
search. "What is the syndrome?" becomes a parity computation.

## The Pauli group

The single-qubit Paulis are

$$I = \begin{pmatrix}1 & 0 \\ 0 & 1\end{pmatrix}, \quad X = \begin{pmatrix}0 & 1 \\ 1 & 0\end{pmatrix}, \quad Y = \begin{pmatrix}0 & -i \\ i & 0\end{pmatrix}, \quad Z = \begin{pmatrix}1 & 0 \\ 0 & -1\end{pmatrix}$$

The **Pauli group on $n$ qubits**, $\mathcal{P}_n$, is the set of all
$n$-fold tensor products of these, each with a phase from $\{\pm 1, \pm i\}$:

$$\mathcal{P}_n = \{\pm 1, \pm i\} \times \{I, X, Y, Z\}^{\otimes n}$$

There are $4^n$ Pauli strings up to phase, and $4^{n+1}$ group elements
including phases. Two facts drive everything:

- Every pair of Pauli strings either **commutes** or **anticommutes**. There is
  no third option.
- $X$, $Y$ and $Z$ pairwise anticommute, and $Y = iXZ$.

### Testing commutation without multiplying matrices

This matters more than it sounds, because the obvious test is wrong. Two Pauli
strings anticommute exactly when they **differ at an odd number of positions**
(counting only positions where neither is $I$). The phase of the product does
*not* tell you: $XZ = -iY$ and $ZX = +iY$, and $-i \neq +i$ even though both are
imaginary. Counting positions is the only reliable test.

```python
import itertools
import numpy as np

# A Pauli string is a tuple of characters from "IXYZ"; index 0 is qubit 0.
# Phases are tracked separately where they matter and ignored elsewhere, since
# a global phase has no effect on commutation or on the +1 eigenspace.
_PAULI = {
    "I": np.eye(2, dtype=complex),
    "X": np.array([[0, 1], [1, 0]], dtype=complex),
    "Y": np.array([[0, -1j], [1j, 0]], dtype=complex),
    "Z": np.diag([1, -1]).astype(complex),
}


def matrix(s: str) -> np.ndarray:
    """Kronecker product of the single-qubit Paulis in ``s``."""
    out = np.eye(1, dtype=complex)
    for ch in s:
        out = np.kron(out, _PAULI[ch])
    return out


def commutes(a: str, b: str) -> bool:
    """True iff the two Pauli strings commute.

    They anticommute exactly when they differ (with neither one the identity)
    at an ODD number of positions. Do NOT test this via the phase of the
    product: X.Z = -iY and Z.X = +iY are both imaginary but differ by a sign.
    """
    differing = sum(1 for x, y in zip(a, b) if x != "I" and y != "I" and x != y)
    return differing % 2 == 0


def weight(s: str) -> int:
    """Number of qubits the operator acts on non-trivially."""
    return sum(1 for ch in s if ch != "I")
```

### Enumerating the group from its generators

To build the group $\langle g_1, \ldots, g_r\rangle$ you only need to close the
set of generators under multiplication, discarding phases. Starting from the
identity and repeatedly multiplying by each generator until nothing new appears
produces all $2^r$ elements:

```python
def generated(gens: list[str]) -> set[str]:
    """Closure of the generators under multiplication, phases discarded."""
    n = len(gens[0])
    elems = {"I" * n}
    frontier = {"I" * n}
    _MUL = {}
    for a in "IXYZ":
        for b in "IXYZ":
            m = _PAULI[a] @ _PAULI[b]
            for c, C in _PAULI.items():
                if np.allclose(m, C):
                    _MUL[(a, b)] = (1, c); break
                if np.allclose(m, -C):
                    _MUL[(a, b)] = (-1, c); break
                if np.allclose(m, 1j * C):
                    _MUL[(a, b)] = (1j, c); break
                if np.allclose(m, -1j * C):
                    _MUL[(a, b)] = (-1j, c); break
    while frontier:
        new = set()
        for e in frontier:
            for g in gens:
                prod = "".join(_MUL[(x, y)][1] for x, y in zip(e, g))
                if prod not in elems:
                    new.add(prod)
        elems |= new
        frontier = new
    return elems
```

## The stabiliser group

### Definition

A **stabiliser group** $S$ is a subgroup of $\mathcal{P}_n$ satisfying two
conditions:

1. **$S$ is abelian** — every pair of elements commutes.
2. **$-I \notin S$.**

The second condition is not decoration. If $-I$ were in $S$, every vector $v$ in
the code space would have to satisfy $-v = v$, forcing $v = 0$: the code space
would be empty. Any subgroup generated by commuting Paulis can accidentally
produce $-I$ (for instance $\langle iX, iY\rangle$ contains
$(iX)(iY) = -i^2 Z \cdot i = \ldots$), which is why it is checked rather than
assumed.

The **code space** $\mathcal{C}$ is the simultaneous $+1$ eigenspace of every
element of $S$:

$$\mathcal{C} = \{|\psi\rangle : M|\psi\rangle = |\psi\rangle \text{ for all } M \in S\}$$

### How big is the code space?

Suppose $S$ has $r$ **independent** generators — no generator is a product of
the others. Then

$$\dim \mathcal{C} = 2^{\,n - r}$$

so the code is written $[[n, k]]$ with $k = n - r$, and $|S| = 2^r$.

The clean way to see it, and the way to compute it, is the **projector** onto
the code space:

$$\Pi = \frac{1}{|S|}\sum_{M \in S} M$$

Its dimension is its trace. Every non-identity Pauli is traceless, and the only
element of $S$ with a non-zero trace is the identity, so

$$\dim \mathcal{C} = \mathrm{Tr}(\Pi) = \frac{1}{|S|}\,\mathrm{Tr}(I) = \frac{2^n}{2^r} = 2^{n-r}$$

Verified numerically for every code in this lesson: the trace of $\Pi$ comes out
at exactly $2.000000$ in each case, matching $k = 1$.

## Worked example: the two three-qubit codes

For the bit-flip code the generators are $Z_0Z_1$ and $Z_1Z_2$, written as
strings `ZZI` and `IZZ` (index 0 is the leftmost character). Running the
analysis:

| Code | Generators | Abelian | $|S|$ | $\dim\mathcal{C}$ | $[[n, k]]$ |
|---|---|---|---|---|---|
| Bit flip | `ZZI`, `IZZ` | yes | 4 | 2.000000 | $[[3, 1]]$ |
| Phase flip | `XXI`, `IXX` | yes | 4 | 2.000000 | $[[3, 1]]$ |

Both give $|S| = 4 = 2^2$, as they must with two independent generators, and
both fix a two-dimensional space — one logical qubit.

## Determining the stabilisers of a given code

The objectives ask you to be able to go the other way: given a code, find its
stabilisers. When you are handed codewords rather than generators, the direct
method is to search the Pauli group for the operators that fix them.

For the bit-flip code, testing all $4^3 = 64$ Pauli strings against
$|000\rangle$ and $|111\rangle$ returns exactly four:

```
['III', 'IZZ', 'ZIZ', 'ZZI']
```

and for the phase-flip code, testing against $|{+}{+}{+}\rangle$ and
$|{-}{-}{-}\rangle$:

```
['III', 'IXX', 'XIX', 'XXI']
```

Four elements in each case: the identity, the two generators, and their product.
That is $S$ in full. The search is exponential in $n$, so it is only practical
for small codes — which is exactly why codes are *specified* by generators
rather than recovered from codewords.

## Logical operators and distance

### The normaliser

Not every Pauli that commutes with $S$ is in $S$. The ones that do but are not
themselves stabilisers are the interesting ones. Define the **normaliser**

$$N(S) = \{P \in \mathcal{P}_n : PM = MP \text{ for all } M \in S\}$$

Elements of $N(S)$ preserve the code space. Those in $S$ act trivially on it.
The rest — $N(S) \setminus S$ — act non-trivially *while remaining inside the
code space*, which is precisely what a **logical operator** is.

So the logical Pauli operators are the elements of $N(S) \setminus S$, taken
modulo $S$ (multiplying by a stabiliser does not change the action on the code
space). For one logical qubit you get a logical $X_L$ and a logical $Z_L$,
anticommuting, just like the physical ones.

You have already met these. For the phase-flip code:

$$X_L = Z_0Z_1Z_2, \qquad Z_L = X_0$$

and for the bit-flip code, $X_L = X_0X_1X_2$ and $Z_L = Z_0$.

### Distance

The **distance** $d$ is the smallest weight of any non-trivial logical operator:

$$d = \min_{P \in N(S) \setminus S} \mathrm{wt}(P)$$

A code with $n$ physical qubits, $k$ logical qubits and distance $d$ is written
$[[n, k, d]]$. The distance controls the error budget:

$$t = \left\lfloor \frac{d - 1}{2} \right\rfloor$$

errors can be **corrected**, and up to $d - 1$ can be **detected**.

For the bit-flip code, $d = 1$: $Z_L = Z_0$ has weight 1, so there is a
weight-1 operator that acts non-trivially on the code while commuting with
everything measured. That single number is the formal statement of what you
already knew — the bit-flip code does not correct a general error.

### Verified distances

Computing $N(S)$ by brute force over all $4^n$ Pauli strings and taking the
minimum weight outside $S$:

| Code | Generators | Abelian | $|S|$ | $\dim\mathcal{C}$ | $d$ | Notation |
|---|---|---|---|---|---|---|
| Bit flip | `ZZI`, `IZZ` | yes | 4 | 2.000000 | 1 | $[[3,1,1]]$ |
| Phase flip | `XXI`, `IXX` | yes | 4 | 2.000000 | 1 | $[[3,1,1]]$ |
| Five-qubit | `XZZXI`, `IXZZX`, `XIXZZ`, `ZXIXZ` | yes | 16 | 2.000000 | 3 | $[[5,1,3]]$ |
| Steane | `IIIXXXX`, `IXXIIXX`, `XIXIXIX`, `IIIZZZZ`, `IZZIIZZ`, `ZIZIZIZ` | yes | 64 | 2.000000 | 3 | $[[7,1,3]]$ |
| Shor | `ZZIIIIIII`, `IZZIIIIII`, `IIIZZIIII`, `IIIIZZIII`, `IIIIIIZZI`, `IIIIIIIZZ`, `XXXXXXIII`, `IIIXXXXXX` | yes | 256 | 2.000000 | 3 | $[[9,1,3]]$ |

Every row reports $|S| = 2^r$ for its generator count and a code-space dimension
of exactly 2, so all five encode one logical qubit. The smallest code that
corrects an *arbitrary* single-qubit error is the five-qubit one; that is a
provable bound, not a coincidence of construction.

## The error-correction condition

What does it take for a code to correct a set of errors $\mathcal{E}$? The
answer is the **Knill–Laflamme condition**: for every pair $E_a, E_b$ in
$\mathcal{E}$, the operator $E_a^\dagger E_b$ must act on the code space as a
scalar. Writing $|\bar{0}\rangle, |\bar{1}\rangle$ for the logical basis,

$$\langle \bar{i} | E_a^\dagger E_b | \bar{j} \rangle = C_{ab}\,\delta_{ij}$$

Two requirements hide in that one line: the off-diagonal $\langle\bar{0}|\cdots|\bar{1}\rangle$
must vanish (no error may move information between logical states in a way that
depends on which error happened), and the two diagonal entries must be equal
(the errors must not reveal which logical state you are in — which is the
condition that keeps your data secret from the environment).

### Verified on the five-qubit code

Taking $\mathcal{E}$ to be the identity plus all $3 \times 5 = 15$ single-qubit
Paulis, and checking all $16 \times 16 = 256$ pairs:

$$\max\left|\langle\bar{0}|E_a^\dagger E_b|\bar{1}\rangle\right| = 3.1 \times 10^{-16}, \qquad \max\left|\langle\bar{0}|E_a^\dagger E_b|\bar{0}\rangle - \langle\bar{1}|E_a^\dagger E_b|\bar{1}\rangle\right| = 6.7 \times 10^{-16}$$

Both are zero to machine precision, so the five-qubit code corrects any single
error on any qubit — which is what $d = 3$ predicts.

### Verified on the bit-flip code, where it fails

Running the same check on the bit-flip code with the full single-qubit error set:

- **12 of the 100 pairs violate the condition.** The code does not correct a
  general single-qubit error. The first violations are $(I, Z_0)$, $(I, Z_1)$,
  $(I, Z_2)$ — a $Z$ error is indistinguishable from no error, as you already
  knew from the syndrome.
- **Restricting to $\{I, X_0, X_1, X_2\}$ gives 0 violations.** The code
  corrects bit flips.

This is the error-correction condition doing real work: it tells you not just
that a code works, but precisely which error set it works for.

## Deriving the syndrome

Measuring $r = n - k$ independent stabiliser generators produces $r$ bits. The
**syndrome** is the vector of outcomes, one bit per generator: $0$ if the errored
state is in the $+1$ eigenspace of that generator, $1$ if it is in the $-1$
eigenspace.

For a Pauli error $E$ and generator $M_i$, the bit is

$$s_i = \begin{cases} 0 & E \text{ and } M_i \text{ commute} \\ 1 & E \text{ and } M_i \text{ anticommute} \end{cases}$$

which is a single commutativity test per generator — no statevector required.

### Worked: the bit-flip code

With generators `ZZI` and `IZZ`, computing $s_i$ for every weight-1 and weight-2
error gives:

| Error $E$ | Commutes with `ZZI`? | Commutes with `IZZ`? | Syndrome | Value $s_0 + 2s_1$ |
|---|---|---|---|---|
| `III` | yes | yes | $(0, 0)$ | 0 |
| `XII` | no | yes | $(1, 0)$ | 1 |
| `IXI` | no | no | $(1, 1)$ | 3 |
| `IIX` | yes | no | $(0, 1)$ | 2 |
| `XXI` | yes | no | $(0, 1)$ | 2 |
| `XIX` | no | no | $(1, 1)$ | 3 |
| `IXX` | no | yes | $(1, 0)$ | 1 |
| `XXX` | yes | yes | $(0, 0)$ | 0 |
| `ZII` | yes | yes | $(0, 0)$ | 0 |

Three things to take from this table.

**The syndrome locates the error, up to the code's design.** For the four
single-bit-flip cases the syndromes are distinct, which is what makes correction
possible.

**Degeneracy is normal.** `IIX` and `XXI` share syndrome $(0,1)$; `IXI` and
`XIX` share $(1,1)$; `XII` and `IXX` share $(1,0)$. They are not the same error —
they differ by $X_0X_1X_2 = X_L$, a logical operator. Applying either correction
gives the same result *on the code space*, so a degenerate code does not need to
distinguish them. This is a feature, not a bug: it is what lets a code correct
more errors than it has syndromes.

**Some errors are invisible.** `XXX` and `ZII` both return $(0,0)$, identical to
no error. `XXX` is a logical operator, so it is "corrected" by doing nothing and
leaves the state logically flipped. `ZII` is a $Z$ error the code was never
designed to see. A zero syndrome means "no correction needed", never "no error
occurred".

### How many syndromes are there?

$r = n - k$ generators give $2^{n-k}$ syndromes. For a non-degenerate code
correcting $t$ errors, every error of weight $\le t$ needs its own syndrome,
giving the **quantum Hamming bound**:

$$2^{\,n-k} \;\ge\; \sum_{j=0}^{t} 3^j \binom{n}{j}$$

The factor $3^j$ counts the three Pauli choices ($X$, $Y$, $Z$) at each of the
$j$ error positions. Verified:

| Code | $n-k$ | Syndromes | Errors of weight $\le t$ | Bound |
|---|---|---|---|---|
| $[[3,1,1]]$ | 2 | 4 | 1 | holds |
| $[[5,1,3]]$ | 4 | 16 | 16 | **saturated** |
| $[[7,1,3]]$ | 6 | 64 | 22 | holds |
| $[[9,1,3]]$ | 8 | 256 | 28 | holds |

The five-qubit code hits the bound exactly, which is why it is called a
**perfect code**: it wastes nothing. No code correcting a single error can use
fewer qubits.

Counting also shows where the budget runs out. On the five-qubit code there are
106 distinct Pauli errors of weight $\le 2$ but only 16 syndromes, so collisions
are unavoidable beyond weight 1 — a counting argument, not a claim about any
particular decoder.

## Degeneracy, in full

Sorting all $4^3 = 64$ Pauli strings on three qubits by their syndrome under the
bit-flip code gives exactly four classes of sixteen:

| Syndrome | Number of Paulis sharing it | Includes |
|---|---|---|
| $(0,0)$ | 16 | `III`, all $Z$-type strings, `XXX` and its $Y$ variants |
| $(1,0)$ | 16 | `XII`, `IXX`, and variants differing by stabilisers |
| $(0,1)$ | 16 | `IIX`, `XXI`, and variants |
| $(1,1)$ | 16 | `IXI`, `XIX`, and variants |

Sixteen per class is not a coincidence: multiplying any error by a stabiliser
leaves its syndrome unchanged, and $|S| = 4$, so each class is a coset of $S$.
The logical operators sit in the $(0,0)$ class, which is why they are invisible.

## Limitations and assumptions

- **Pauli errors only.** The formalism handles errors that are (mixtures of)
  Pauli operators. This is less restrictive than it sounds: any error
  superoperator can be expanded in the Pauli basis, and correcting the Pauli
  components corrects the general error. What the formalism does *not* cover is
  a coherent, non-Pauli error such as a small over-rotation, which is not a
  mixture of Paulis in any useful sense.
- **The syndrome is assumed reliable.** Everything above treats the $r$ measured
  bits as correct. On real hardware the measurement itself is faulty, and a
  single faulty syndrome bit sends the decoder after the wrong error. Handling
  that requires repeated measurement and
  [fault-tolerant](54_threshold_theorem.md) constructions.
- **Decoding is not free.** Knowing the syndrome is not the same as knowing the
  correction. For surface codes that is a matching problem; for general codes it
  can be computationally hard.
- **The distance is a worst-case guarantee, not an average.** $t = \lfloor (d-1)/2\rfloor$
  is the number of errors corrected *with certainty*. A code frequently
  recovers from more; it never promises to.

## Common misconceptions

- **"The stabilisers are measured, so the state is measured."** Measuring a
  stabiliser returns an eigenvalue, not the state. All the information obtained
  is $r$ bits identifying an error coset; nothing about the logical
  superposition leaks, because logical operators commute with nothing that is
  measured. This was verified explicitly in
  [the bit-flip lesson](49_bit_flip_code.md): the ancilla ends in a definite
  basis state, unentangled with the data.
- **"A zero syndrome means no error."** It means no *detectable* error. A
  logical operator or an error outside the code's design both give $(0,0)$.
- **"Each error has its own syndrome."** Degenerate codes share syndromes
  between errors that differ by a stabiliser, which is how they beat the
  non-degenerate counting bound.
- **"Distance is the number of errors corrected."** Distance $d$ corrects
  $\lfloor (d-1)/2\rfloor$ and detects $d - 1$. A $[[5,1,3]]$ code corrects one
  error and detects two.
- **"Any set of commuting Paulis defines a code."** The subgroup must also
  exclude $-I$, or the code space is empty.

## Exercises

1. Prove that if $-I \in S$ then the code space contains only the zero vector.

2. The generators `ZZI` and `IZZ` commute. Write out their product and confirm
   that $S = \{III, ZZI, IZZ, ZIZ\}$ is closed under multiplication.

3. A code on 4 qubits has 3 independent stabiliser generators. How many logical
   qubits does it encode, and how many syndrome values are there?

4. Consider the two Paulis `XZ` and `ZX` on two qubits. Do they commute? Show
   your working by counting positions, and separately by computing the phase of
   their product in both orders.

5. A $[[7,1,3]]$ code is used on a device where errors are independent and each
   qubit suffers an error with probability $p = 10^{-4}$. Estimate the
   probability that a given block suffers *more* than one error, and say whether
   the code corrects it.

6. The errors `XXI` and `IIX` give the same syndrome on the bit-flip code.
   Explain why the code does not need to tell them apart.

### Answers to 1–3

**1.** If $-I \in S$ then every $|\psi\rangle$ in the code space satisfies
$(-I)|\psi\rangle = |\psi\rangle$ by definition, i.e. $-|\psi\rangle = |\psi\rangle$,
so $2|\psi\rangle = 0$ and $|\psi\rangle = 0$. The only vector in the space is
zero, so there is no code.

**2.** `ZZI` · `IZZ`: position 0 gives $Z \cdot I = Z$; position 1 gives
$Z \cdot Z = I$; position 2 gives $I \cdot Z = Z$. The product is `ZIZ`, which is
in the set. Multiplying any element by `ZZI` or `IZZ` toggles membership between
these four, and the identity fixes them, so the set is closed. It has 4 elements
with 2 generators, as required.

**3.** $k = n - r = 4 - 3 = 1$ logical qubit. There are $r = 3$ generators, so
$2^3 = 8$ syndrome values.

### Answers to 4–5

**4.** They **commute**. Counting positions: at position 0, $X$ and $Z$ differ
and neither is $I$; at position 1, $Z$ and $X$ differ and neither is $I$. That is
2 differing positions, which is even, so they commute. By direct multiplication,
$(X \otimes Z)(Z \otimes X) = (XZ) \otimes (ZX) = (-iY)\otimes(iY) = (-i)(i)\,Y\otimes Y = I$,
and the reverse order gives the same matrix — verified numerically, both
products are equal.

The trap is worth naming. At a *single* position, $XZ = -iY$ and $ZX = +iY$
differ by a sign, so single-qubit $X$ and $Z$ anticommute (1 differing position,
odd). Here there are two such positions, and the two signs cancel:
$(-i)(+i) = +1$. Reading the phase at one position and concluding
"anticommute" would give the wrong answer. **Count positions.**

**5.** The probability of two or more errors is $1 - (1-p)^7 - 7p(1-p)^6$. With
$p = 10^{-4}$: $P(0) = 0.9999^7 = 0.9993002100$ and
$P(1) = 7\times10^{-4}\times0.9999^6 = 0.0006995801$, so

$$P(\ge 2) = 1 - 0.9993002100 - 0.0006995801 = 2.0993 \times 10^{-7}$$

which matches the leading term $\binom{7}{2}p^2 = 2.10\times10^{-7}$ to three
significant figures. About one block in five million is pushed beyond what a
$d = 3$ code corrects with certainty. Against a bare per-qubit rate of
$10^{-4}$ that is an improvement of $10^{-4} / 2.0993\times10^{-7} \approx 476$,
and it costs seven physical qubits per logical qubit.

### Answer to 6

**6.** Two errors share a syndrome exactly when their product commutes with
every stabiliser. Here `XXI` · `IIX` = `XXX`, and `XXX` commutes with `ZZI`
(positions 0 and 1 differ — two, even) and with `IZZ` (positions 1 and 2 differ
— two, even). So `XXX` lies in $N(S)$. It is not in $S = \{III, ZZI, IZZ, ZIZ\}$,
so it is a **logical operator** — specifically $X_L$ for this code.

That is the whole answer: `XXI` and `IIX` differ by a logical operator, so on
the code space they act the same way up to a known logical $X$. Correcting
either one returns the same encoded state, and the code never needs to
distinguish them. A decoder that picks any correction with the right syndrome is
correct.

## Summary

- A code is specified by an abelian subgroup $S \subset \mathcal{P}_n$ with
  $-I \notin S$. The code space is the simultaneous $+1$ eigenspace, with
  dimension $2^{n-r}$ for $r$ independent generators, computable as the trace
  of the projector $\Pi = |S|^{-1}\sum_{M\in S} M$.
- Stabilisers can be read off a construction or **found** by searching the Pauli
  group for operators fixing the codewords — verified to return
  $\{III, IZZ, ZIZ, ZZI\}$ and $\{III, IXX, XIX, XXI\}$ for the two
  three-qubit codes.
- Logical operators are $N(S) \setminus S$. The distance $d$ is the minimum
  weight there, and $[[n,k,d]]$ corrects $t = \lfloor (d-1)/2\rfloor$ errors.
  Verified: $[[3,1,1]]$ twice, $[[5,1,3]]$, $[[7,1,3]]$, $[[9,1,3]]$.
- Correctability is the Knill–Laflamme condition
  $\langle\bar{i}|E_a^\dagger E_b|\bar{j}\rangle = C_{ab}\delta_{ij}$. Verified
  to $3\times10^{-16}$ for all 256 error pairs on the five-qubit code, and
  verified to **fail** for 12 of 100 pairs on the bit-flip code with a general
  error set but 0 of 16 with bit flips only.
- The syndrome is $r$ commutativity tests. Degeneracy — errors sharing a
  syndrome because they differ by a stabiliser or a logical operator — is
  normal and useful; verified that all 64 three-qubit Paulis split into exactly
  four cosets of sixteen.
- The quantum Hamming bound $2^{n-k} \ge \sum_{j\le t} 3^j\binom{n}{j}$ is
  saturated by the five-qubit code, making it perfect.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  §10.5 — stabiliser codes, the projector onto the code space, and the
  error-correction condition.
- Gottesman, D. *Stabilizer Codes and Quantum Error Correction* — the
  formalism itself, and the group-theoretic treatment of $N(S)/S$.
- Knill, E. & Laflamme, R. — the necessary and sufficient condition for
  error correction used in the verification above.
- Calderbank, A. R. & Shor, P. W.; Steane, A. M. — the two seven-qubit
  constructions.
- [The Three-Qubit Bit-Flip Code](49_bit_flip_code.md) and
  [the phase-flip code](50_phase_flip_code.md) — the two worked examples.
- [Surface Codes](52_surface_codes.md) — the stabiliser formalism on a lattice.

---

**Next:** [Surface Codes](52_surface_codes.md)
