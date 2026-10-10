# Threshold Theorem and Fault Tolerance

Everything in the previous two lessons assumed something quietly impossible:
that errors happen to the data, and that the circuits we use to find and fix
those errors work perfectly. They do not. A syndrome extraction circuit is made
of the same faulty gates as everything else, and a single fault inside it can
spread one error into several — which is precisely what a distance-3 code cannot
handle.

The threshold theorem is the result that makes the whole programme viable
anyway. This lesson states it, states what it assumes, and shows what goes wrong
when a construction is merely error-correcting rather than fault-tolerant.

## Learning objectives

By the end of this lesson you should be able to:

- **State** the threshold theorem and its assumptions.
- **Explain** why arbitrarily long computation becomes possible below threshold.
- **Distinguish** fault-tolerant from merely error-detecting constructions.

## Prerequisites

[Logical and Physical Qubits, and Overhead](53_logical_physical_qubits.md). This
lesson uses the relation $p_L \approx A(p/p_{\text{th}})^{(d+1)/2}$ and the idea
of a physical-to-logical ratio directly.

## The problem

A code with distance $d$ corrects $t = \lfloor (d-1)/2 \rfloor$ errors. That
guarantee is about errors **on the data**. It says nothing about errors in:

- the gates that couple data to ancillas during syndrome extraction;
- the ancilla preparation and measurement, which are far from perfect in
  practice;
- the classical decoder, or the correction operation it triggers.

If those operations can turn one fault into two data errors, no distance-3 code
can recover, because two errors exceed $t = 1$. And if the correction circuit is
noisier than the thing it protects, adding it makes matters worse.

So the guarantee has to be strengthened: we need circuits where a **single
fault anywhere** still leaves a correctable error. That is the fault-tolerance
criterion, stated precisely below.

## The theorem

> **Threshold theorem.** For a family of quantum error-correcting codes with
> increasing distance, subject to noise that is local, Markovian and below a
> certain rate, there exists a threshold $p_{\text{th}} > 0$ such that for any
> physical error rate $p < p_{\text{th}}$ and any target failure probability
> $\varepsilon > 0$, an arbitrary quantum computation can be performed with
> failure probability at most $\varepsilon$, at an overhead that grows only
> polylogarithmically in the size of the computation and in $1/\varepsilon$.

Two clauses carry all the weight, and both are routinely misquoted.

**"Below a certain rate."** The theorem does not say error correction works. It
says it works *if the hardware is already good enough*. Above threshold, adding
more qubits makes things worse, because the extra circuitry introduces more
faults than the code can absorb.

**"Polylogarithmically."** The overhead is not constant, but it grows slowly
enough to be budgetable. That is the clause that licenses "arbitrarily long".

### Why it is true, in one paragraph

Take a code that corrects one error, and suppose a fault-tolerant circuit
realises it. A logical operation fails only if at least $t+1 = 2$ independent
faults occur, so the logical error rate after one encoding level is roughly
$p_1 \approx c\,p^2$ rather than $p$. If $p < 1/c$ then $p_1 < p$: encoding
helped. Encode again, treating each level's logical qubits as the next level's
physical qubits, and the error rate falls as

$$p_L \;\approx\; c^{\,2^L - 1}\, p^{\,2^L}$$

after $L$ levels. The error rate collapses doubly exponentially while the qubit
count grows only as $n_1^L$. This is the concatenated-code proof, and it is
where the polylogarithmic overhead comes from — the same scaling compared
against surface codes in [the overhead lesson](53_logical_physical_qubits.md).

## The assumptions

This is the part most often skipped, and it is where the theorem is most often
over-claimed.

1. **Noise is local.** Each gate fails independently of the others. Correlated
   faults — a drifting calibration, a cosmic ray, a control-glitch that hits a
   whole row — violate this and can defeat a code of any distance.
2. **Noise is Markovian.** Errors do not remember the past. Non-Markovian
   environments, which produce slowly drifting or correlated-in-time errors,
   are not covered.
3. **Gates can be applied in parallel.** The proof allows arbitrary
   parallelism; severe restrictions change the threshold.
4. **Ancillas are available fresh and can be reset.** If a used ancilla is
   recycled without reset, it carries information — and errors — into the next
   round.
5. **Classical decoding is fast and correct.** The decoder must keep up with the
   syndrome stream, or the backlog grows without bound.
6. **No leakage.** Qubits are assumed to stay in the computational subspace.
   Real transmons leak into $|2\rangle$, and leaked qubits do not behave like
   errors the code can detect.
7. **The noise strength is known or bounded.** The decoder and the threshold
   estimate both assume a noise model.

Every one of these is violated to some degree by real hardware. That does not
make the theorem false; it makes it a statement about a model, and the model is
an approximation.

## What "fault-tolerant" means

The operative definition:

> A gadget is **fault-tolerant** if, for any single fault occurring anywhere in
> it, the error produced on each output block is correctable — that is, has
> weight at most $t$ on a code that corrects $t$ errors.

The key phrase is *on each output block*. A single fault may produce several
errors in total; what matters is that no single block receives more than $t$. A
fault that deposits two errors in one block is fatal; the same fault depositing
one error in each of two blocks is fine.

This is why the criterion is about **error propagation**, and why the whole
design problem is arranging circuits so that faults do not spread.

## Verified: a fault-tolerant gadget

The canonical fault-tolerant operation is the **transversal** gate: qubit $i$ of
one block interacts only with qubit $i$ of the other. For two Steane
$[[7,1,3]]$ blocks $A$ and $B$, a logical CNOT is seven physical CNOTs,
$\text{CNOT}(A_i, B_i)$ for $i = 0 \ldots 6$.

Verified on the Steane stabilisers from
[the stabiliser lesson](51_stabilizer_formalism.md), with $X_L = XXXIIII$ and
$Z_L = ZZZIIII$ (both in $N(S)$, neither in $S$, anticommuting):

| Input | Output |
|---|---|
| $X_L \otimes I$ | $X_L \otimes X_L$ |
| $I \otimes X_L$ | $I \otimes X_L$ |
| $Z_L \otimes I$ | $Z_L \otimes I$ |
| $I \otimes Z_L$ | $Z_L \otimes Z_L$ |

That is exactly logical CNOT with $A$ as control.

The fault-tolerance property follows from the wiring: each physical CNOT touches
exactly one qubit in each block, so a single faulty CNOT deposits at most one
error per block. And all 21 weight-1 errors on a Steane block are correctable —
verified exhaustively. So:

$$\text{one fault} \;\Rightarrow\; \le 1 \text{ error per block} \;\Rightarrow\; \text{always correctable}$$

A logical failure therefore requires **two** independent faults.

### Verifying the criterion

```python
import itertools


STAB = ["IIIXXXX", "IXXIIXX", "XIXIXIX",     # X-type Steane checks
        "IIIZZZZ", "IZZIIZZ", "ZIZIZIZ"]     # Z-type Steane checks
N = 7


def symvec(s):
    """(x-part | z-part) over GF(2)."""
    x = [1 if c in "XY" else 0 for c in s]
    z = [1 if c in "ZY" else 0 for c in s]
    return x + z


def anticommutes(u, v):
    return (sum(a & b for a, b in zip(u[:N], v[N:])) +
            sum(a & b for a, b in zip(u[N:], v[:N]))) % 2


def syndrome(p):
    v = symvec(p)
    return tuple(anticommutes(v, symvec(g)) for g in STAB)


def product(a, b):
    """Pauli string product, discarding the global phase."""
    out = []
    for x, y in zip(a, b):
        if x == "I":
            out.append(y)
        elif y == "I":
            out.append(x)
        elif x == y:
            out.append("I")
        else:
            out.append({"XZ": "Y", "ZX": "Y",
                        "YZ": "X", "ZY": "X",
                        "YX": "Z", "XY": "Z"}[x + y])
    return "".join(out)


def in_stabiliser_group(p):
    """|S| = 2**6 = 64 for Steane, so enumeration is cheap here."""
    for bits in itertools.product((0, 1), repeat=6):
        acc = "I" * N
        for b, g in zip(bits, STAB):
            if b:
                acc = product(acc, g)
        if acc == p:
            return True
    return False
```

With that toolkit, the criterion is a two-line check. A decoder, given an
error, computes its syndrome and applies the lowest-weight Pauli with the same
syndrome; recovery succeeds when what remains is a stabiliser, since a
stabiliser acts trivially on the code space.

### Applying it

```python
def correctable(error):
    """Ideal syndrome extraction + minimum-weight recovery succeeds?"""
    syn = syndrome(error)
    for w in (0, 1, 2):
        for supp in itertools.combinations(range(N), w):
            for pauli in "XYZ":
                cand = ["I"] * N
                for q in supp:
                    cand[q] = pauli
                cand = "".join(cand)
                if syndrome(cand) == syn:
                    return in_stabiliser_group(product(error, cand))
    return False


# Every weight-1 error on a block is correctable, so a gadget that deposits
# at most one error per block is fault-tolerant for [[7,1,3]].
print(all(correctable("".join(p if i == q else "I" for i in range(N)))
          for q in range(N) for p in "XYZ"))
```

## Verified: a gadget that is not fault-tolerant

Now the contrast. Measuring a weight-$w$ stabiliser with a single bare ancilla
is the obvious circuit and it is **not** fault-tolerant.

For an $X$-type stabiliser the ancilla must be the control: prepare $|+\rangle$,
then $\text{CNOT}(a, q_i)$ for each qubit $i$ in the support, then Hadamard and
measure. An $X$ fault on the ancilla control propagates to **every** data qubit
it is coupled to *after* the fault — so a single fault becomes a data error of
weight $w - k$, where $k$ is the number of CNOTs already applied.

Verified on the Steane code for the stabiliser $IIIXXXX$ (support
$\{3,4,5,6\}$), testing each fault position and running ideal syndrome
extraction plus minimum-weight recovery:

| Fault after $k$ CNOTs | Induced error | Weight | Correctable? |
|---|---|---|---|
| 0 | $X$ on $\{3,4,5,6\}$ | 4 | yes — it **is** the stabiliser |
| 1 | $X$ on $\{4,5,6\}$ | 3 | yes — degenerate with $X$ on $\{3\}$ |
| 2 | $X$ on $\{5,6\}$ | 2 | **no** |
| 3 | $X$ on $\{6\}$ | 1 | yes |
| 4 | none | 0 | yes |

The $k = 0$ row is the interesting one: the induced error is the stabiliser
itself, which acts trivially on the code space, so a fault that spreads to all
four qubits is harmless. The $k = 1$ row is saved by **degeneracy** — $X$ on
$\{4,5,6\}$ differs from the weight-1 error $X$ on $\{3\}$ by exactly the
stabiliser, so the two are indistinguishable and correcting either works.

But the $k = 2$ row is fatal. A weight-2 error exceeds $t = 1$, recovery
succeeds in finding a same-syndrome candidate ($X$ on $\{0\}$) but the product
is not a stabiliser, so the state is left logically corrupted.

**One fault defeats the code.** That is the signature of a non-fault-tolerant
construction, and it is exactly what fault tolerance forbids.

### The consequence: $p$ versus $p^2$

This is the quantitative distinction that matters:

| Gadget | Faults needed for failure | Failure probability |
|---|---|---|
| Transversal CNOT | 2 | $P_{\text{fail}} = O(p^2)$ |
| Bare-ancilla weight-4 check | 1 | $P_{\text{fail}} = O(p)$ |

Because only the scaling differs, the gap widens as hardware improves:

| Physical $p$ | $O(p^2)$ gadget | $O(p)$ gadget | Ratio |
|---|---|---|---|
| $10^{-2}$ | $10^{-4}$ | $10^{-2}$ | 100 |
| $10^{-3}$ | $10^{-6}$ | $10^{-3}$ | 1000 |
| $10^{-4}$ | $10^{-8}$ | $10^{-4}$ | 10000 |
| $10^{-5}$ | $10^{-10}$ | $10^{-5}$ | 100000 |

The constants are illustrative; the exponents are structural. Below threshold
the fault-tolerant gadget's advantage grows as $1/p$, and no amount of extra
distance rescues the other one, because the linear term never goes away.

### How the failure is fixed

Several constructions restore fault tolerance to syndrome extraction:

- **Verified cat states (Shor).** Prepare the ancilla in a GHZ state, *verify*
  it with an extra ancilla before coupling to data, and discard and retry if the
  parity is wrong. Verification catches the faults that would spread.
- **Steane ancillas.** Prepare the ancilla block in an encoded state, verify it,
  and couple transversally, so ancilla faults do not spread within the data
  block.
- **Flag qubits.** Add an extra qubit that detects when a single fault has
  produced a multi-qubit error, so the syndrome can be reinterpreted.
- **Repeat and decode in space–time.** Surface-code extraction repeats every
  check for many rounds and the decoder works on the full three-dimensional
  syndrome history, so correlated events become identifiable patterns rather
  than fatal coincidences.

## Why arbitrarily long computation becomes possible

This is the second clause of the theorem, and the one that answers the obvious
objection: if every logical gate has some non-zero failure probability, does a
long computation not fail with certainty?

It does, unless you shrink the per-gate failure rate as the computation grows.
Here is the arithmetic.

A computation of $T$ logical gates, each failing independently with probability
$p_L$, fails overall with probability about $T p_L$ (union bound, valid when
$T p_L \ll 1$). Demanding this be at most $\varepsilon$ gives

$$p_L \;\le\; \frac{\varepsilon}{T}$$

That is the target. Now invert the surface-code relation from
[the overhead lesson](53_logical_physical_qubits.md) to find the distance that
achieves it, at $p_{\text{th}} = 10^{-2}$, $A = 0.1$, $p = 10^{-3}$,
$\varepsilon = 10^{-2}$:

| Logical operations $T$ | Required $p_L$ | Distance $d$ | Qubits per logical qubit |
|---|---|---|---|
| $10^{3}$ | $10^{-5}$ | 7 | 49 |
| $10^{6}$ | $10^{-8}$ | 13 | 169 |
| $10^{9}$ | $10^{-11}$ | 19 | 361 |
| $10^{12}$ | $10^{-14}$ | 25 | 625 |
| $10^{15}$ | $10^{-17}$ | 31 | 961 |
| $10^{20}$ | $10^{-22}$ | 41 | 1681 |

### What the table shows

This is the result. Making the computation **$10^{17}$ times longer** — a
thousand gates to a hundred quintillion — raises the cost per logical qubit from
49 qubits to 1681, a factor of about 34.

The distance grows **linearly in $\log T$**: 7, 13, 19, 25, 31, 41, adding 6 for
every three orders of magnitude of computation length. So

$$\text{overhead} \;\sim\; d^2 \;\sim\; (\log T)^2$$

Polylogarithmic in the length of the computation. That is what "arbitrarily
long" means: there is no wall. Any target can be met, and the price grows slowly
enough to remain finite.

The intuition is that reliability is bought once, in the distance, and then
amortised over the whole computation. Each extra unit of distance multiplies the
logical error rate by a constant factor $p/p_{\text{th}}$, which is a fixed
improvement paid for once, not a cost per gate.

## How big is the threshold?

The theorem guarantees $p_{\text{th}} > 0$ but says nothing about its value, and
the value is not a property of nature — it depends on the code, the decoder and
the noise model.

| Noise model | Approximate threshold (surface code) |
|---|---|
| Code capacity (perfect measurements, data errors only) | $\sim 10\%$ |
| Phenomenological (noisy measurements, no circuit detail) | $\sim 3\%$ |
| Circuit-level (every operation fails) | $\sim 0.5\text{–}1\%$ |

Treat these as order-of-magnitude figures for a specific decoder under a
specific depolarising model, not as constants. The number that matters for
hardware is the circuit-level one, because it is the only model in which
extraction itself can fail.

The practical consequence is stark. At $p = 10^{-3}$ against a $10^{-2}$
threshold you are at $p/p_{\text{th}} = 0.1$; at $p = 5 \times 10^{-3}$ you are
at $0.5$, and
[the overhead lesson](53_logical_physical_qubits.md) shows that moving from the
former to the latter multiplies the qubit count by more than ten.

## The price: Eastin–Knill

Fault tolerance is not free, and one restriction is a theorem rather than an
engineering difficulty.

> **Eastin–Knill.** No quantum error-correcting code admits a universal set of
> gates that are all transversal.

Transversal gates are the ones that come free with fault tolerance, because they
cannot spread errors within a block. The theorem says you cannot build a
universal computer out of them alone. Every fault-tolerant architecture
therefore needs an additional resource, and in practice that resource is
**magic state distillation**: prepare a noisy non-Clifford state, distil many
into one of higher fidelity using only Clifford operations, and consume it to
implement a $T$ gate.

Distillation is expensive — typically the dominant cost in a fault-tolerant
architecture, exceeding the cost of the code patches themselves. The qubit
counts in this lesson and the last are a **floor**, not an estimate of a real
machine.

## Limitations

- **The theorem is about a model.** Local, Markovian, independent noise. Real
  devices have crosstalk, leakage and correlated errors; the threshold computed
  under an idealised model is an upper bound on what the hardware will achieve.
- **The threshold is not a number you can quote without a decoder.** It is a
  joint property of code, decoder and noise model. A better decoder raises it.
- **The constants are not in the theorem.** Polylogarithmic scaling is
  excellent, but the polylog can have a large constant, and the ancilla, time
  and distillation costs multiply it.
- **Below threshold is not the same as practical.** At $p/p_{\text{th}} = 0.9$
  the overhead is astronomically large even though the theorem applies.
- **Fault-tolerant does not mean fault-free.** It means one fault is survivable.
  Two faults in the same place are not.

## Common misconceptions

- **"Error correction means errors are removed."** They are not removed; they
  are tracked and compensated. The entropy leaves the computer only when the
  ancillas are reset.
- **"Below threshold, the logical error rate is zero."** It is exponentially
  small in $d$, not zero.
- **"Any code plus any correction circuit is fault-tolerant."** No. A bare
  ancilla on a weight-4 check turns one fault into an uncorrectable error, as
  verified above. Fault tolerance is a property of the **circuit**, not the
  code.
- **"The threshold is a fixed physical constant like the speed of light."** It
  is a property of a code, a decoder and a noise model. Quoting it without all
  three is meaningless.
- **"More qubits always helps."** Only below threshold. Above it, the extra
  circuitry introduces more faults than it removes, and adding qubits makes the
  logical error rate worse.
- **"Arbitrarily long computation means unlimited computation for free."** The
  overhead grows as $(\log T)^2$. It grows, and the constants behind it are
  large.

## Exercises

1. State in one sentence the difference between a code that corrects $t$ errors
   and a gadget that is fault-tolerant for that code.

2. A gadget for a distance-5 code turns one fault into three errors in a single
   block. Is it fault-tolerant? Why or why not?

3. In the bare-ancilla example, the fault at $k = 0$ produces an error of weight
   4 and is harmless, while the fault at $k = 2$ produces an error of weight 2
   and is fatal. Explain both.

4. Using the $T$-scaling table, how many qubits per logical qubit are needed for
   a computation of $10^{18}$ logical operations at $\varepsilon = 10^{-2}$?
   Give the distance and the qubit count.

5. Why does the fault-tolerant gadget's advantage over the non-fault-tolerant
   one grow as hardware improves, rather than staying constant?

6. Name two assumptions of the threshold theorem that a real superconducting
   device violates, and explain what each violation does.

### Answers to 1–3

**1.** A code that corrects $t$ errors guarantees recovery from up to $t$
errors **on the data**; a fault-tolerant gadget guarantees that a single fault
**anywhere in the gadget itself** leaves at most $t$ errors on each output
block, so the code's guarantee still applies.

**2.** No. A distance-5 code corrects $t = \lfloor (5-1)/2 \rfloor = 2$ errors
per block. Three errors in one block exceeds that, so a single fault defeats the
code. Fault tolerance requires at most $t$ errors per block from any single
fault.

**3.** At $k = 0$ the ancilla $X$ propagates to all four qubits in the support,
$\{3,4,5,6\}$, and the induced operator **is** the stabiliser $IIIXXXX$.
Stabilisers act trivially on the code space, so nothing has happened to the
encoded state. At $k = 2$ it propagates to $\{5,6\}$, a strict subset of the
support. That is not a stabiliser and not degenerate with any weight-1 error, so
it is a genuine weight-2 error — beyond $t = 1$, and therefore fatal. The lesson
is that spreading an error across an *entire* stabiliser support is harmless,
while spreading it across part of one is not.

### Answers to 4–6

**4.** Required $p_L = \varepsilon/T = 10^{-2}/10^{18} = 10^{-20}$. Using
$d = 2\ln(p_L/A)/\ln(p/p_{\text{th}}) - 1$ with $A = 0.1$, $p = 10^{-3}$,
$p_{\text{th}} = 10^{-2}$:

$$d = 2\,\frac{\ln 10^{-19}}{\ln 10^{-1}} - 1 = 2(19) - 1 = 37$$

Distance 37, so $37^2 = 1369$ data qubits per logical qubit. Interpolating the
table: $T = 10^{15}$ needs $d = 31$ and $T = 10^{20}$ needs $d = 41$, so
$d = 37$ at $T = 10^{18}$ is consistent with the $+6$ per three decades pattern.

**5.** The two gadgets differ in the **exponent**, not the constant: $O(p^2)$
against $O(p)$. Their ratio is $p^2/p = p$, so as $p$ falls by a factor of 10
the fault-tolerant gadget becomes 10 times better *relative* to the other.
Improving hardware multiplies the advantage rather than merely preserving it.

**6.** Any two of the following, with the consequence:

- *Leakage.* Transmons populate $|2\rangle$, leaving the computational
  subspace. Leaked qubits are not detected by Pauli stabilisers, so the error
  is invisible to the decoder and accumulates until it becomes a logical
  failure. Mitigated by leakage-reduction units.
- *Crosstalk.* Gates are not independent; operating on one qubit perturbs its
  neighbours. This breaks the locality assumption, and correlated errors can
  defeat a code of any distance since the code's guarantee is about a bounded
  number of independent faults.
- *Non-Markovian noise.* Slowly drifting parameters produce errors correlated
  in time, so the "independent round to round" assumption behind repeated
  syndrome extraction fails and the decoder's noise model is wrong.
- *No fast mid-circuit reset.* The theorem assumes fresh ancillas. If reset is
  slow, the syndrome-extraction rate drops and errors accumulate between
  rounds.

## Summary

- The threshold theorem: for local, Markovian noise below a threshold
  $p_{\text{th}}$, an arbitrary computation can reach any target failure
  probability $\varepsilon$ at polylogarithmic overhead.
- Its assumptions are local, independent, Markovian noise; parallel gates;
  fresh resettable ancillas; fast correct classical decoding; no leakage. Real
  hardware violates several of them, which makes the threshold an upper bound
  rather than a prediction.
- Fault tolerance is a property of the **circuit**, not the code: a single fault
  anywhere must leave at most $t$ errors on each output block.
- Verified: the transversal CNOT on two Steane blocks implements logical CNOT
  and is fault-tolerant — one fault gives at most one error per block, and all
  21 weight-1 errors are correctable, so failure needs two faults ($O(p^2)$).
- Verified: a bare ancilla on the weight-4 stabiliser $IIIXXXX$ is **not**
  fault-tolerant. A fault after 2 of 4 CNOTs gives an uncorrectable weight-2
  error ($O(p)$). Faults at $k = 0$ and $k = 1$ are harmless — the first is the
  stabiliser itself, the second is rescued by degeneracy.
- Verified: below threshold, $p_L \le \varepsilon/T$ is met by
  $d \sim \log T$, so overhead $\sim (\log T)^2$. Growing a computation by
  $10^{17}$ raises the cost per logical qubit from 49 to 1681 qubits.
- The circuit-level threshold for surface codes is of order $10^{-2}$
  (roughly $0.5$–$1\%$), and it is a joint property of code, decoder and noise
  model.
- Eastin–Knill: no code has a universal transversal gate set, so magic-state
  distillation is required, and its cost usually dominates.

## References

- Aharonov, D. & Ben-Or, M. — the threshold theorem for local noise.
- Kitaev, A. Yu. — threshold results for topological codes.
- Knill, E., Laflamme, R. & Zurek, W. H. — the concatenated-code threshold
  argument, $p_L \approx c^{2^L-1}p^{2^L}$.
- Shor, P. W. — cat-state (verified-ancilla) fault-tolerant syndrome extraction.
- Steane, A. M. — ancilla-based fault-tolerant extraction.
- Chao, R. & Reichardt, B. W. — flag-qubit fault-tolerant extraction.
- Eastin, B. & Knill, E. — no universal transversal gate set exists.
- Bravyi, S. & Kitaev, A. — magic-state distillation.
- [Logical and Physical Qubits, and Overhead](53_logical_physical_qubits.md) —
  the $p_L$ model and overhead scaling used throughout.
- [Surface Codes](52_surface_codes.md) — the code family these thresholds are
  usually quoted for.
- [Stabilizer Formalism](51_stabilizer_formalism.md) — the Steane stabilisers
  used in the verification above.

---

**Next:** [Quantum Error Mitigation](55_error_mitigation.md)
