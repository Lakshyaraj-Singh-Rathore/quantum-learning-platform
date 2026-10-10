# Resource Estimation

Before you run an algorithm you should be able to say whether it can possibly
work. That judgement comes down to three questions: how many qubits, how many
gates, and how deep — then converting those numbers into a success probability
using the hardware's error rates. This lesson makes that arithmetic explicit.
It is the difference between "this algorithm is efficient" and "this algorithm
will finish before my qubits decohere."

## Learning objectives

By the end of this lesson you should be able to:

- **Count** qubits, gate depth and two-qubit gate count for a circuit, using
  both an abstract description and a real circuit representation.
- **Translate** a depth budget into a feasibility judgement, using coherence
  time and gate time.
- **Compute** the success probability of a circuit from per-gate error rates,
  and the number of shots needed to see the right answer at least once.
- **Derive** the error rate a circuit demands, and explain why that number
  drives hardware development.

## The three counts

### What to count

Three numbers determine feasibility:

- **Qubit count $n$** — how many physical qubits the computation touches. This
  is usually the binding constraint on what you can even attempt.
- **Two-qubit gate count $N_{2q}$** — the dominant error source. Two-qubit
  gates are typically 10 to 100 times noisier than single-qubit gates, so this
  number, not the total gate count, predicts failure.
- **Depth $D$** — the length of the longest path through the circuit. This
  bounds the *runtime*, and therefore whether the computation finishes before
  the qubits decohere.

Total gate count is a poor guide. A circuit with 1000 single-qubit gates and
10 two-qubit gates is far more likely to succeed than one with 10
single-qubit gates and 1000 two-qubit gates.

### Counting with a real circuit representation

Abstract gate lists are easy to count by hand, but compiled circuits are not —
you need the representation to tell you. Using this project's circuit IR, a
GHZ circuit built as one $H$ followed by a CNOT chain gives:

| Circuit | Qubits | Gates | Single-qubit | Two-qubit | Depth |
|---|---|---|---|---|---|
| 5-qubit GHZ | 5 | 5 | 1 | 4 | 6 |
| 8-qubit GHZ | 8 | 8 | 1 | 7 | 9 |

The depth exceeds the gate count because the final measurement layer adds its
own step, and because the CNOT chain is sequential — each one depends on the
previous.

Now compare against the same logical structure forced onto badly chosen
physical qubits. A three-gate chain spanning qubits 0, 2 and 4 on a line
counts as just **2** two-qubit gates abstractly, but routing each step costs a
SWAP (three CNOTs), giving **8** two-qubit gates once compiled. The abstract
count understates the real cost fourfold, which is exactly why resource
estimation must be done on the *compiled* circuit.

## From error rates to success probability

### The model

If each two-qubit gate fails independently with probability $p_{2q}$ and each
single-qubit gate with probability $p_{1q}$, the probability that every gate
succeeds is

$$P_{\text{success}} = (1 - p_{2q})^{N_{2q}} \, (1 - p_{1q})^{N_{1q}}$$

For small error rates this is well approximated by

$$P_{\text{success}} \;\approx\; \exp\!\big[-(N_{2q}p_{2q} + N_{1q}p_{1q})\big]$$

The approximation is accurate while the total error budget
$N_{2q}p_{2q} + N_{1q}p_{1q}$ is small, and it is the form worth remembering
because it makes the arithmetic trivial: **multiply gate count by error rate**.

### Worked numbers

At $p_{2q} = 1\%$ and $p_{1q} = 0.1\%$, assuming ten single-qubit gates per
two-qubit gate, the two formulas track each other closely:

| $N_{2q}$ | Exact | $\exp$ approximation |
|---|---|---|
| 10 | 0.8183 | 0.8187 |
| 50 | 0.3669 | 0.3679 |
| 100 | 0.1346 | 0.1353 |
| 200 | 0.0181 | 0.0183 |

Past that the success probability collapses toward zero. The practical
threshold is often quoted as $N_{2q}\,p_{2q} \lesssim 0.1$: keep the total
error budget under about 10% or the output is mostly noise.

### Shots needed

A low success probability is not automatically fatal — you can repeat. But the
cost is brutal, because the number of repetitions grows as the reciprocal:

| $N_{2q}$ | Success probability | Shots for one success |
|---|---|---|
| 100 | $1.3\times10^{-1}$ | 8 |
| 500 | $4.4\times10^{-5}$ | 22,645 |
| 1000 | $2.0\times10^{-9}$ | 512,770,631 |

A thousand two-qubit gates at 1% error needs over half a billion shots for a
single clean run. That is the wall NISQ algorithms hit, and it is why
error-correction overhead dominates every serious resource estimate.

### The error rate a circuit demands

Inverting the relation, to succeed with probability $1/2$ you need

$$p_{2q} \;\lesssim\; \frac{\ln 2}{N_{2q}} \;\approx\; \frac{0.69}{N_{2q}}$$

| $N_{2q}$ | Required $p_{2q}$ |
|---|---|
| $10^2$ | $6.9\times10^{-3}$ |
| $10^3$ | $6.9\times10^{-4}$ |
| $10^4$ | $6.9\times10^{-5}$ |
| $10^6$ | $6.9\times10^{-7}$ |

Useful algorithms need millions of gates, so they need error rates around
$10^{-7}$ or better. Current hardware sits near $10^{-3}$. That gap of four
orders of magnitude is the entire reason fault tolerance is a research field.

## From depth to a feasibility judgement

### The coherence budget

Depth converts to runtime through the gate time, and runtime must fit inside
the coherence time:

$$D \times t_{\text{gate}} \;<\; T_2$$

With $T_2 = 100\,\mu\text{s}$:

| Gate time | Maximum depth |
|---|---|
| 200 ns (fast two-qubit gate) | 500 |
| 1 $\mu$s (slow, or with routing) | 100 |

A circuit of depth 500 is already at the edge of what a 100 µs coherence time
allows. This is a *hard* limit in a way that error rates are not: no amount of
repetition helps if the state has decohered before the circuit finishes.

### Putting it together

A resource estimate reads as follows:

1. Compile the circuit and count $n$, $N_{2q}$ and $D$.
2. Check the coherence budget: is $D \cdot t_{\text{gate}} < T_2$?
3. Compute the error budget: is $N_{2q}p_{2q} + N_{1q}p_{1q} \lesssim 0.1$?
4. If either fails, the circuit needs shallower depth, fewer two-qubit gates,
   or error correction — and is not feasible as written.

Both checks must pass. A circuit can be shallow enough to finish and still
return noise, or accurate per gate and still too deep to complete.

## Practical example

### Counting resources with a real circuit object

```python
from app.quantum.ir import Op, empty_circuit


def build_and_count(nq, spec):
    ir = empty_circuit(nq)
    for i, (g, q, c) in enumerate(spec):
        ir.place(Op(kind="gate", gate=g, qubits=q, controls=c), i)
    ir.append_measure_all()
    ops = list(ir.walk())
    gates = [o for o in ops if o.kind == "gate"]
    two = [g for g in gates if g.controls]
    one = [g for g in gates if not g.controls]
    return nq, len(gates), len(one), len(two), ir.depth()


spec5 = [("h", [0], [])] + [("x", [i + 1], [i]) for i in range(4)]
spec8 = [("h", [0], [])] + [("x", [i + 1], [i]) for i in range(7)]
for label, spec in (("5-qubit GHZ", spec5), ("8-qubit GHZ", spec8)):
    n, g, o, t, d = build_and_count(len(spec), spec)
    print(f"{label}: qubits={n} gates={g} single={o} two-qubit={t} depth={d}")
```

### Error rates to success probability

```python
import math


def success(n2q, p2q, n1q, p1q):
    return (1 - p2q) ** n2q * (1 - p1q) ** n1q


def approx(n2q, p2q, n1q, p1q):
    return math.exp(-(n2q * p2q + n1q * p1q))


p2q, p1q = 0.01, 0.001
print("\nN_2q     exact    exp-approx")
for n in (10, 50, 100, 200):
    print(f"{n:4d}   {success(n, p2q, 10 * n, p1q):7.4f}   "
          f"{approx(n, p2q, 10 * n, p1q):7.4f}")

print("\nshots for one success:")
for n in (100, 500, 1000):
    s = success(n, p2q, 10 * n, p1q)
    print(f"  N_2q={n:5d}: p={s:.3e}  shots ~ {math.ceil(1 / s):,}")

print("\nrequired p_2q for 50% success:")
for n in (10 ** 2, 10 ** 3, 10 ** 6):
    print(f"  N_2q={n:>8,}: p_2q <= {1 - 0.5 ** (1 / n):.2e}")
```

Running the blocks in order gives the resource counts for both GHZ circuits
and the error table above, including that a thousand two-qubit gates at 1%
error needs over half a billion shots per clean run.

## Common misconceptions

- **"Efficient means feasible."** Polynomial scaling says nothing about whether
  the constant and the error rate let you finish.
- **"Gate count is what matters."** *Two-qubit* gate count is what matters;
  single-qubit gates are an order of magnitude cheaper.
- **"I can repeat until it works."** Repetition costs $1/P_{\text{success}}$
  shots, which grows exponentially in circuit size.
- **"Depth is the same as gate count."** Depth is the longest dependency path;
  a circuit with many independent gates can have large count and small depth.
- **"A 99% gate is good enough."** It supports about 70 two-qubit gates before
  the error budget is spent.

## Exercises

1. A circuit has 300 two-qubit gates at 0.5% error. Compute the success
   probability exactly and with the exponential approximation.
2. How many shots are needed for one success in that circuit?
3. What two-qubit error rate would give a 90% success probability on $10^4$
   two-qubit gates?
4. A processor has $T_2 = 80\,\mu\text{s}$ and a 300 ns two-qubit gate time.
   What is the maximum depth? What if routing doubles the effective gate time?
5. Count $n$, $N_{2q}$ and $D$ for a 10-qubit GHZ circuit, and compute its
   success probability at 1% error.
6. Explain why a shallow circuit with many qubits can be more feasible than a
   deep circuit with few.

## Summary

- Count **qubits**, **two-qubit gates** and **depth** — total gate count
  misleads, because two-qubit gates dominate the error.
- $P_{\text{success}} = (1-p_{2q})^{N_{2q}}(1-p_{1q})^{N_{1q}} \approx \exp[-(N_{2q}p_{2q} + N_{1q}p_{1q})]$.
- Keep the error budget $N_{2q}p_{2q} \lesssim 0.1$; beyond that the output is
  mostly noise, and repetition costs $1/P$ shots.
- For 50% success, $p_{2q} \lesssim \ln 2 / N_{2q} \approx 0.69/N_{2q}$.
- Depth is bounded by coherence: $D \cdot t_{\text{gate}} < T_2$.
- **Both** checks must pass, and both must be computed on the **compiled**
  circuit — routing can multiply the two-qubit count several times.

## References

- The [Native Gates, Connectivity and Routing](42_compilation.md) lesson —
  why compiled counts differ from abstract ones.
- The [Quantum Composer](28_composer_guide.md) lesson — the circuit IR used
  for counting above.
- Gidney, C. & Ekerå, M. (2021), "How to factor 2048 bit RSA integers in 8
  hours using 20 million noisy qubits" — resource estimation done seriously.

---

**Previous:** [Native Gates, Connectivity and Routing](42_compilation.md)
