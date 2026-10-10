# BQP, P, NP and BPP

Complexity theory is where the claims about quantum computing get made precise —
and where a great many of them turn out to be unproven. This lesson defines the
classes, states exactly which relationships are theorems and which are
conjectures, and is careful about what a quantum speed-up demonstration does and
does not establish.

The value of this lesson is mostly negative. Knowing what has *not* been proved
is what lets you evaluate a claim.

## Learning objectives

By the end of this lesson you should be able to:

- **Define** BQP, BPP and NP.
- **State** the known inclusions relating these classes.
- **Explain** what quantum speed-up evidence does and does not establish.

## Prerequisites

[Grover's Algorithm](06_grover.md) (recommended) — Grover and Shor
are the separations that motivate BQP.

## The classes

All four are classes of **decision problems** — questions with a yes/no answer,
parameterised by input size $n$.

**P** — solvable by a deterministic classical computer in time polynomial in
$n$. Multiplication, sorting, shortest paths.

**BPP** — *bounded-error probabilistic polynomial time*. Solvable by a
classical computer that may use randomness, in polynomial time, with error
probability at most $1/3$ on every input. The $1/3$ is arbitrary: any constant
below $1/2$ can be amplified to any other by repetition, at only polynomial
cost. BPP is the class of problems a classical computer can *efficiently and
reliably* solve.

**NP** — *nondeterministic polynomial time*. Equivalently, and more usefully: a
"yes" answer has a certificate that can be **verified** in polynomial time. If I
claim a graph has a Hamiltonian cycle, you can check my claimed cycle quickly.
Finding it may be hard. Whether every such problem can also be *solved* quickly
is the P versus NP question.

**BQP** — *bounded-error quantum polynomial time*. Solvable by a quantum
computer in polynomial time, with error probability at most $1/3$ on every
input. This is the class of problems a quantum computer can efficiently and
reliably solve, and it is the central object of study.

Two features of BQP are worth drawing out because they are often missed.

**The error bound is part of the definition.** BQP requires bounded error, not
exactness. A quantum algorithm that gives the right answer with probability
$2/3$ is in BQP; the definition does not require certainty, because repetition
amplifies it. This is the same relaxation BPP makes.

**The gates must be described to polynomial precision.** BQP is defined with
respect to a uniform family of polynomial-size circuits whose gates are
efficiently computable. Without that restriction the class grows unphysically
large.

## What is known

The proven relationships:

$$\text{P} \;\subseteq\; \text{BPP} \;\subseteq\; \text{BQP} \;\subseteq\; \text{PP} \;\subseteq\; \text{PSPACE}$$

Every one of these is a genuine inclusion proof, not a conjecture.

- $\text{P} \subseteq \text{BPP}$: a deterministic machine is a randomised one
  that ignores its coin flips.
- $\text{BPP} \subseteq \text{BQP}$: a quantum computer can simulate classical
  randomness — prepare $|+\rangle$, measure, and you have a fair coin.
- $\text{BQP} \subseteq \text{PP}$: a result of Adleman, DeMarrais and Huang.
  **PP** (probabilistic polynomial time) is the class where a "yes" answer needs
  strictly more than half the computation paths to accept — a very permissive
  class, since it allows unbounded error.
- $\text{PP} \subseteq \text{PSPACE}$: solvable with polynomial memory, given
  enough time.

Tighter upper bounds are known. **BQP $\subseteq$ AWPP**, a subclass of PP, and
$\text{BQP} \subseteq \text{P}^{\#\text{P}}$ — a quantum computation can be
simulated by a classical machine with oracle access to a counting function. Both
say: *quantum computation is not magic; it sits inside counting complexity.*

Also relevant: $\text{NP} \subseteq \text{PP}$, so both NP and BQP live inside
PP. This is the closest thing to a structural relationship between them, and it
is not a containment in either direction.

## What is not known

This is the part that matters for evaluating claims.

**Is BQP larger than BPP?** Almost certainly yes, but **unproven**. It is not
even known whether $\text{BQP} \neq \text{EXP}$.

**Is $\text{P} = \text{PSPACE}$?** Unknown. Since BQP sits between BPP and PP,
proving $\text{BQP} \neq \text{BPP}$ would immediately prove
$\text{P} \neq \text{PSPACE}$ — a separation nobody has achieved. This is why
the question is hard: it is entangled with the central open problems of classical
complexity theory.

**Does BQP contain NP?** Believed **no**. If $\text{NP} \subseteq \text{BQP}$,
then quantum computers could solve NP-complete problems efficiently, which would
be a far stronger claim than anything currently supported by evidence. There is
an oracle relative to which $\text{NP} \not\subseteq \text{BQP}$.

**Is BQP contained in NP?** Also believed **no**, and for a similar reason: a
BQP computation involves amplitudes that interfere, and a single accepting path
does not obviously certify the result.

So the honest picture of the middle:

```
        P  ⊆  BPP  ⊆  BQP  ⊆  PP  ⊆  PSPACE
                              ⊆
                             NP
```

with **no containment known between BQP and NP in either direction**, and
*evidence* that they are incomparable.

### Oracle separations: the evidence that does exist

Since we cannot prove $\text{BQP} \neq \text{BPP}$ outright, the field uses
**oracle separations**: exhibit a hypothetical black box relative to which a
quantum computer provably needs far fewer queries than any classical one.

- **Simon's problem** ([covered here](34_simon.md)) gives an oracle
  relative to which BQP is exponentially faster than **any** bounded-error
  classical algorithm. This is the cleanest exponential separation and the
  inspiration for Shor's algorithm.
- **Bernstein–Vazirani** gives a separation that is only polynomial but is
  exact rather than probabilistic.
- **Raz and Tal (2018)** exhibited an oracle relative to which
  $\text{BQP} \not\subseteq \text{PH}$ — the polynomial hierarchy. This is
  stronger evidence than the BPP separation, because PH contains NP.

An oracle separation is **not** a proof about the real world. An oracle is a
hypothetical subroutine; a separation relative to one shows that certain
classical proof techniques cannot establish $\text{BQP} = \text{BPP}$, but it
does not rule out an efficient classical algorithm that exploits structure the
oracle does not have. Oracle results are evidence about *proof techniques* as
much as about complexity.

### The strongest real-world evidence: factoring

The most concrete evidence that BQP exceeds BPP is
[Shor's algorithm](33_shors_algorithm.md). Factoring is in BQP. It is
not known to be in P. Decades of effort on the fastest classical algorithms have
not produced a polynomial one, and the problem is widely believed not to be
NP-complete either — it sits in the awkward middle, in $\text{NP} \cap \text{coNP}$.

So: either quantum computers are exponentially faster than classical ones for
factoring, or the entire cryptographic assumption underlying RSA is wrong. Most
researchers treat the former as more likely.

## What a quantum speed-up demonstration establishes

This is objective 3, and it is where the most overclaiming happens.

### What has been demonstrated

**Sampling experiments** — random circuit sampling, and Gaussian boson sampling
— have run circuits that would take an implausibly long time to simulate
classically. These are real achievements.

The reason they are hard classically is concrete and worth stating. A state of
$n$ qubits has $2^n$ amplitudes:

| $n$ | Amplitudes | Memory (complex128) |
|---|---|---|
| 20 | $1.05\times10^6$ | 16.8 MB |
| 30 | $1.07\times10^9$ | 17.2 GB |
| 40 | $1.10\times10^{12}$ | 17.6 TB |
| 50 | $1.13\times10^{15}$ | 18.0 PB |
| 60 | $1.15\times10^{18}$ | 18.5 EB |
| 100 | $1.27\times10^{30}$ | — |

Memory doubles with every added qubit. At $n = 50$ the state no longer fits on a
single machine; at $n = 100$ there are more amplitudes than there are atoms in
the observable universe raised to the power of a third. **This exponential
scaling is the resource that makes classical simulation intractable**, and it is
the honest content of a sampling speed-up claim.

Note that this is about *simulating* quantum mechanics, not about solving a
decision problem. Sampling experiments are evidence that nature is not
efficiently simulable classically — which we already had strong reason to
believe.

### What has not been demonstrated

**A demonstration does not prove $\text{BQP} \neq \text{BPP}$.** The sampling
tasks are not decision problems in BQP, and the classical hardness arguments
rest on plausible but unproven complexity assumptions — typically that the
polynomial hierarchy does not collapse. These are the same kind of assumption
that underlies much of complexity theory, but they are assumptions.

**It does not prove the device is doing anything useful.** A sampling
distribution with no known application is not a computation. The experiments
show a machine doing something hard to simulate; they do not show it doing
something *valuable*.

**It does not show a speed-up over the best classical algorithm for a useful
problem.** Repeatedly, improved classical algorithms have closed gaps that
looked large. A claimed speed-up against one classical approach is not a
speed-up against all of them.

**It does not separate BQP from NP, or show anything about NP-complete
problems.** The misconception that quantum computers solve NP-complete
problems efficiently is widespread and unsupported.

### What would count as a real demonstration of quantum advantage

Three things, together:

1. **A computational task with an application** — not just a sampling
   distribution.
2. **A provable or well-supported separation** from the best *known* classical
   algorithm, with the classical side given a genuine effort rather than a
   straw man.
3. **Verification** that the quantum device produced the right answer — which
   is itself hard, since verifying a sampling distribution classically is
   exactly the thing that is intractable.

That is a high bar and has not yet been met. It is worth knowing that, because
the phrase "quantum advantage" is used loosely in public discussion.

## Common misconceptions

- **"Quantum computers solve NP-complete problems efficiently."** No evidence
  for this, and evidence against it. BQP is not believed to contain NP.
- **"Shor's algorithm proves $\text{BQP} \neq \text{BPP}$."** It does not. It
  shows factoring is in BQP; whether factoring is in P is open. It is
  compelling evidence, not a proof.
- **"Quantum supremacy means quantum computers are now better than classical
  ones."** The experiments demonstrate hardness of *simulation* for a
  contrived task, under complexity assumptions, with no application.
- **"BQP contains NP."** Believed false. If true, it would revolutionise
  optimisation, and there is no evidence for it.
- **"An oracle separation settles the question."** It shows a proof technique
  fails. It does not settle the real-world problem.
- **"The $1/3$ error in BQP is a weakness."** It is the same bounded-error
  relaxation BPP makes, and repetition amplifies it at polynomial cost.

## Exercises

1. Define BQP in one sentence, and say why the bounded-error condition is
   included.

2. State the chain $\text{P} \subseteq \text{BPP} \subseteq \text{BQP} \subseteq \text{PP} \subseteq \text{PSPACE}$ and identify which inclusions
   are proven and which are conjectural.

3. If someone proved $\text{BQP} \neq \text{BPP}$, what classical separation
   would follow immediately, and why?

4. Explain why an oracle separation does not settle whether BQP exceeds BPP in
   the real world.

5. A press release says a quantum computer "solved in minutes a problem that
   would take a classical supercomputer 10,000 years." List three questions you
   would ask before accepting the claim.

6. Why is the memory required to simulate $n$ qubits a red herring for
   *usefulness*, even though it is the correct explanation of why simulation is
   hard?

### Answers to 1–3

**1.** BQP is the class of decision problems solvable by a polynomial-size
quantum circuit in polynomial time with error probability at most $1/3$ on every
input. The bounded-error condition is included because requiring exactness would
exclude most quantum algorithms, which are inherently probabilistic — measuring
a superposition gives a random outcome. As in BPP, the constant is arbitrary:
repeating and taking a majority vote drives the error down exponentially at
polynomial cost.

**2.** All four inclusions are **proven theorems**: $\text{P} \subseteq \text{BPP}$ (determinism is a special case of randomness), $\text{BPP} \subseteq \text{BQP}$ (quantum computers can generate classical randomness),
$\text{BQP} \subseteq \text{PP}$ (Adleman–DeMarrais–Huang), and $\text{PP} \subseteq \text{PSPACE}$. What is *conjectural* is whether any of them is
**strict** — in particular whether $\text{BPP} \subsetneq \text{BQP}$.

**3.** $\text{P} \neq \text{PSPACE}$. Since $\text{P} \subseteq \text{BPP} \subseteq \text{BQP} \subseteq \text{PP} \subseteq \text{PSPACE}$, if
$\text{BQP} \neq \text{BPP}$ then the chain cannot be all-equal, so
$\text{P} \neq \text{PSPACE}$ follows immediately. Proving $\text{P} \neq \text{PSPACE}$ is a famous open problem, which is why $\text{BQP} \neq \text{BPP}$ is expected to be extremely hard.

### Answers to 4–6

**4.** An oracle is a hypothetical black box with no internal structure. A
separation relative to an oracle shows that no *relativising* classical
technique can prove the classes equal — it rules out a family of proof methods.
But a real classical algorithm could exploit structure that the oracle lacks.
There are known cases where a statement holds relative to one oracle and fails
relative to another, which is exactly why oracle results are evidence about
techniques rather than about the unrelativised world.

**5.** (i) *What is the classical algorithm being compared against, and was it
the best known?* Comparisons against a naive baseline are common and
meaningless. (ii) *Is the task useful, or a contrived sampling problem?* A
speed-up on a task with no application demonstrates simulation hardness, not
utility. (iii) *How was the answer verified?* If the output is a sampling
distribution that cannot be checked classically, the claim rests on the device
working as intended. Also worth asking: does the quantum time include state
preparation and readout, and is the comparison wall-clock or asymptotic?

**6.** Because the memory blow-up is a statement about *simulating* quantum
dynamics, which is hard, but it says nothing about whether the dynamics compute
anything worth computing. A random circuit is maximally hard to simulate and
maximally useless at the same time. The exponential state space is why we need
quantum computers to simulate quantum systems — Feynman's original motivation —
but hardness of simulation and usefulness of result are independent properties.

## Summary

- **P** (deterministic polynomial time), **BPP** (randomised, bounded error),
  **NP** (verifiable certificate), **BQP** (quantum, bounded error). The $1/3$
  error in BPP and BQP is arbitrary and amplifiable.
- **Proven**: $\text{P} \subseteq \text{BPP} \subseteq \text{BQP} \subseteq \text{PP} \subseteq \text{PSPACE}$, plus $\text{BQP} \subseteq \text{AWPP}$
  and $\text{NP} \subseteq \text{PP}$.
- **Not known**: whether any inclusion is strict; whether BQP exceeds BPP;
  whether NP is in BQP (believed no) or BQP in NP (believed no). The classes are
  believed incomparable in the middle.
- Proving $\text{BQP} \neq \text{BPP}$ would immediately prove
  $\text{P} \neq \text{PSPACE}$, which is why it is so hard.
- **Oracle separations** (Simon, Raz–Tal) are evidence about *proof techniques*,
  not proofs about the real world.
- The strongest real-world evidence is **Shor's algorithm**: factoring is in BQP
  and not known to be in P.
- **A sampling speed-up demonstrates that simulation is hard** — verified: $2^n$
  amplitudes, 16.8 MB at $n=20$ against 18.0 PB at $n=50$ — **but not** that
  BQP $\neq$ BPP, not that the device does anything useful, and not that
  NP-complete problems are within reach.

## References

- Bernstein, E. & Vazirani, U., "Quantum complexity theory" (SIAM J. Comput.,
  1997) — the definition of BQP and $\text{BQP} \subseteq \text{PP}$.
- Adleman, L., DeMarrais, J. & Huang, M.-D., "Quantum computability" (SIAM J.
  Comput., 1997) — $\text{BQP} \subseteq \text{PP}$.
- Simon, D., "On the power of quantum computation" (1997) — the oracle
  separation behind Shor's algorithm.
- Shor, P. W., "Polynomial-time algorithms for prime factorization and discrete
  logarithms on a quantum computer" (SIAM J. Comput., 1997).
- Raz, R. & Tal, A., "Oracle separation of BQP and PH" (2018) — the strongest
  oracle separation to date.
- Aaronson, S., "Quantum computing since Democritus" — an accessible treatment
  of why these questions are hard.
- Aaronson, S. & Chen, L., "Complexity-theoretic foundations of quantum
  supremacy experiments" — what sampling experiments do and do not establish.
- [Grover's Algorithm](06_grover.md) — the quadratic speed-up, and
  why it does not put NP in BQP.
- [Shor's Algorithm](33_shors_algorithm.md) — the strongest
  evidence that BQP exceeds BPP.
- [NISQ Limitations](62_nisq_limitations.md) — the practical constraint that
  separates what is in BQP from what today's hardware can run.

---

**Next:** [Quantum Benchmarking](64_benchmarking.md)
