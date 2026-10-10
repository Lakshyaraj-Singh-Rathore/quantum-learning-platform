# Quantum Repeaters and the Quantum Internet

Sending a qubit down 1000 km of optical fibre and having it arrive is
completely hopeless — the transmission probability is around $10^{-20}$. Quantum
repeaters are the answer, and the interesting part is that the obvious way to
build one does not work at all.

This lesson explains why direct transmission fails, how entanglement swapping
extends entanglement across a chain of nodes, and what a quantum internet
enables that a point-to-point link does not.

## Learning objectives

By the end of this lesson you should be able to:

- **Explain** why direct transmission fails at long distance.
- **Describe** entanglement swapping and a repeater chain.
- **State** what a quantum internet enables beyond point-to-point links.

## Prerequisites

[Quantum Teleportation](26_teleportation.md) (required) — repeaters are
chained entanglement swapping, which is teleportation between nodes.

## Why direct transmission fails

Objective 1.

### The numbers

Optical fibre at the telecom wavelength of 1550 nm loses about **0.2 dB per
kilometre**. Transmission through a length $L$ is

$$T = 10^{-\alpha L / 10}, \qquad \alpha = 0.2 \text{ dB/km}.$$

| Distance | Loss | Transmission |
|---|---|---|
| 10 km | 2.0 dB | $6.3 \times 10^{-1}$ |
| 50 km | 10.0 dB | $1.0 \times 10^{-1}$ |
| 100 km | 20.0 dB | $1.0 \times 10^{-2}$ |
| 200 km | 40.0 dB | $1.0 \times 10^{-4}$ |
| 500 km | 100.0 dB | $1.0 \times 10^{-10}$ |
| 1000 km | 200.0 dB | $1.0 \times 10^{-20}$ |

The scaling is **exponential in distance**. Doubling the distance does not halve
the signal; it squares the loss.

At 1000 km, one photon in $10^{20}$ arrives. A source firing at 1 MHz would
produce one detection every $10^{14}$ seconds — about **3.2 million years** for
a single photon. This is not a engineering difficulty to be optimised away. It
is the end of the road.

### Why you cannot simply amplify

A classical repeater solves exactly this problem by **amplifying** the signal:
measure it, boost it, retransmit. That is impossible for quantum information,
for two independent reasons.

**The no-cloning theorem** forbids copying an unknown quantum state. An
amplifier that works on arbitrary input would be a universal cloner, which
quantum mechanics does not permit.

**Measurement destroys the state.** You cannot read the qubit and retransmit
what you measured: measuring a superposition collapses it, and the result is one
classical bit, not the amplitude. Unlike
[superdense coding](66_superdense_coding.md), where the message is classical
from the start, here the quantum state itself is the payload.

So the naive fix is unavailable, and the loss is exponential. A quantum repeater
has to work a fundamentally different way.

## Entanglement swapping

Objective 2, first half. The primitive that makes repeaters possible.

### The protocol

Suppose Alice and Bob each hold one half of a Bell pair, and so do Bob and
Carol:

- Pair 1: qubits $A$ (Alice) and $B$ (Bob), in $\lvert\Phi^+\rangle$.
- Pair 2: qubits $C$ (Bob) and $D$ (Carol), in $\lvert\Phi^+\rangle$.

Alice and Carol have never interacted, and their qubits have never met. Now Bob
performs a **Bell measurement** on his two qubits $B$ and $C$ — a CNOT followed
by a Hadamard, then measuring both — and broadcasts the two classical outcome
bits.

The result: **$A$ and $D$ become entangled.**

This is entanglement swapping. It is genuinely strange: entanglement has been
created between two qubits that never interacted, by a measurement performed on
neither of them.

### Verified: it works for every outcome

Simulating the circuit and post-selecting on each of the four Bell-measurement
outcomes gives the state of $A$ and $D$:

| Outcome $m_B m_C$ | Probability | State of $A, D$ |
|---|---|---|
| $00$ | 0.2500 | $\lvert\Phi^+\rangle = \tfrac{1}{\sqrt{2}}(\lvert 00\rangle + \lvert 11\rangle)$ |
| $01$ | 0.2500 | $\lvert\Phi^-\rangle = \tfrac{1}{\sqrt{2}}(\lvert 00\rangle - \lvert 11\rangle)$ |
| $10$ | 0.2500 | $\lvert\Psi^+\rangle = \tfrac{1}{\sqrt{2}}(\lvert 01\rangle + \lvert 10\rangle)$ |
| $11$ | 0.2500 | $\lvert\Psi^-\rangle = \tfrac{1}{\sqrt{2}}(\lvert 01\rangle - \lvert 10\rangle)$ |

Each outcome occurs with probability exactly $1/4$, and **in every case $A$ and
$D$ are maximally entangled** — the numerical residual against the ideal Bell
state is about $10^{-14}$, i.e. exact to machine precision.

So swapping is **deterministic given the outcome**. The measurement result does
not tell you *whether* the swap worked; it tells you which **Pauli correction**
to apply to turn the resulting Bell state into the one you wanted. This is the
same structure as the correction step in
[teleportation](26_teleportation.md).

### Why it matters

Swapping converts a *short-range* resource into a *long-range* one. If you can
distribute entanglement over 100 km, you can swap to get 200 km, and again to
get 400 km. That is the repeater idea.

The next section shows that the naive version of this idea fails completely,
and that the fix is a specific extra ingredient.

## The repeater chain

Objective 2, second half.

### The trap: segmentation alone buys nothing

The obvious design: split 1000 km into $n$ segments, distribute entanglement
across each, then swap. Surely shorter segments are easier?

**No — it is exactly equally hard.** The probability that entanglement is
successfully generated across a segment of length $L/n$ is $10^{-\alpha L/10n}$,
and all $n$ segments must succeed:

$$\Big(10^{-\alpha L / 10n}\Big)^{n} = 10^{-\alpha L / 10}$$

The $n$ cancels **exactly**. Verified numerically: 2, 4, 8 and 16 segments all
give $1.0 \times 10^{-20}$ for 1000 km — identical to the direct link, to six
decimal places.

This is worth internalising, because it is the single most common misconception
about quantum repeaters. **Chopping a link into pieces does not help.** The
reason is that without memory, every segment must succeed *simultaneously*, and
simultaneous independent successes multiply — reproducing the exponential you
were trying to escape.

### What actually works: memory and heralding

The ingredient that breaks the deadlock is **quantum memory combined with
heralding**:

- **Heralding** means each attempt announces success or failure. You always know
  whether a given try worked.
- **Quantum memory** means a segment that succeeded can **store** its
  entanglement and **wait** for its neighbours, instead of the whole chain having
  to succeed at once.

This transforms the problem. Failure is no longer fatal — it just costs another
attempt. The exponential **probability** penalty becomes a polynomial **time**
penalty.

Each segment succeeds after a mean of $1/(p_\text{seg} R)$ attempts, where $R$
is the attempt rate. With $n$ segments retrying independently in parallel and
holding their successes, the expected time for **all** of them is

$$\mathbb{E}[T] = \frac{H_n}{p_\text{seg} R}, \qquad H_n = \sum_{k=1}^{n} \frac{1}{k} \approx \ln n + \gamma .$$

The harmonic number $H_n$ grows only **logarithmically** in $n$, while
$p_\text{seg} = 10^{-\alpha L/10n}$ improves **exponentially**. Exponential
beats logarithmic, decisively.

### Verified: the payoff

For 1000 km at 0.2 dB/km, a 1 MHz attempt rate, ideal memories and perfect
operations:

| Segments | Segment length | $p_\text{seg}$ | Time to establish |
|---|---|---|---|
| 1 (direct) | 1000 km | $1.0 \times 10^{-20}$ | $1.0 \times 10^{14}$ s (**3.2 million years**) |
| 2 | 500 km | $1.0 \times 10^{-10}$ | $1.5 \times 10^{4}$ s (**4.2 hours**) |
| 4 | 250 km | $1.0 \times 10^{-5}$ | $2.1 \times 10^{-1}$ s |
| 8 | 125 km | $3.2 \times 10^{-3}$ | $8.6 \times 10^{-4}$ s |
| 16 | 62.5 km | $5.6 \times 10^{-2}$ | $6.0 \times 10^{-5}$ s |
| 32 | 31.2 km | $2.4 \times 10^{-1}$ | $1.7 \times 10^{-5}$ s |

From **3.2 million years to 0.2 seconds**, by adding three repeater stations
and letting them wait for each other.

Note carefully what produced the gain: not the swapping, and not the
segmentation — but the **memory** that lets a successful segment wait.

### The cost: memory coherence time

The catch is that a stored Bell pair decoheres while it waits. The memory must
hold entanglement for at least as long as the protocol takes.

For the 8-segment case above, the total is $8.6 \times 10^{-4}$ s, so the
memory must maintain entanglement for roughly **0.86 ms**. That is demanding but
not absurd — it is within reach of several
[hardware platforms](61_platform_comparison.md), and it is the central
engineering target of quantum repeater research.

This is the honest trade: **more segments mean faster entanglement but a longer
wait for the slowest segment**, and the memory must survive the wait. Beyond
some point, decoherence eats the gain, and there is an optimal $n$.

### A complete repeater link

Putting it together, a full repeater chain repeatedly:

1. **Distributes** entanglement across each short segment (probabilistic,
   heralded, retried until success).
2. **Stores** each successful pair in quantum memory.
3. **Swaps** adjacent pairs via Bell measurements at intermediate nodes,
   extending entanglement outward from the middle or inward from the ends.
4. **Corrects** with a Pauli operation determined by the classical broadcast of
   measurement outcomes.
5. **Purifies** if the entangled states are noisy — consuming several low-quality
   pairs to distil fewer high-quality ones, the subject of
   [error correction](52_surface_codes.md).

## What a quantum internet enables

Objective 3. A network of entangled nodes is more than a collection of
point-to-point links, and the applications that need the network are the ones
that justify building it.

**Distributed quantum computing.** Two distant quantum processors linked by
entanglement behave as one larger machine. Gate teleportation lets a controlled
operation act across the link. This is a path to scaling qubit count past what a
single device can hold — which matters enormously given the
[NISQ limits](62_nisq_limitations.md) on individual processors.

**Device-independent quantum key distribution.** On a network, entanglement lets
two parties generate a shared key whose security does not depend on trusting
their own hardware. A Bell-violation test certifies the devices from the outside.
See [quantum cryptography](68_quantum_cryptography.md).

**Blind quantum computation.** A client with minimal quantum capability can have
a server perform a computation without the server learning the input, the
algorithm or the result. This requires only a network link to a client device.

**Clock synchronisation and metrology.** Entangled clocks can be synchronised
beyond the classical limit, and a network of entangled sensors beats the
standard quantum limit in aggregate precision.

**Secure multi-party computation.** Tasks where several parties compute a
function of their joint inputs without revealing them, with security grounded in
quantum mechanics rather than computational assumptions.

The common thread: these are all tasks where the value comes from **correlations
between separated parties**, not from raw point-to-point bandwidth. A network
delivers correlations that no amount of point-to-point communication can
replicate.

## Common misconceptions

- **"Repeaters amplify the signal like classical ones do."** They cannot.
  No-cloning forbids amplification of an unknown state, and measurement
  destroys the payload. The mechanism is entirely different: distribute,
  store, swap, correct.
- **"Splitting the link into segments fixes the loss."** Verified above: it
  changes nothing. $(10^{-\alpha L/10n})^n = 10^{-\alpha L/10}$ exactly.
  The gain comes from **quantum memory**, not from segmentation.
- **"Entanglement swapping is probabilistic, so repeaters fail often."** The
  swap is **deterministic given the outcome** — all four outcomes give a
  maximally entangled state. What is probabilistic is *distributing* the initial
  entanglement, which heralding makes retryable.
- **"Entanglement lets qubits communicate faster than light."** It does not.
  Every swap requires a **classical broadcast** of the measurement outcome to
  apply the correction, and those bits travel at light speed. This is the same
  constraint as in [superdense coding](66_superdense_coding.md).
- **"The internet will route qubits the way it routes packets."** Qubits cannot
  be copied for redundancy or retransmission. Routing means deciding where to
  place entanglement and when to swap, and a lost qubit is gone for good.

## Exercises

1. Calculate the transmission through 300 km of fibre at 0.2 dB/km.

2. Why can a classical repeater not be used for a quantum signal? Give two
   independent reasons.

3. You split a 600 km link into 3 segments of 200 km, with no quantum memory.
   What is the success probability, and how does it compare to the direct link?

4. Two Bell pairs $A$–$B$ and $C$–$D$ are swapped by a Bell measurement on $B$
   and $C$. What is the state of $A$ and $D$ afterwards, and what additional
   information is needed to use it?

5. Why does adding more segments eventually stop helping?

6. Name two applications that need a quantum *network* rather than just a long
   point-to-point link, and say why.

### Answers to 1–3

**1.** Loss $= 0.2 \times 300 = 60$ dB, so
$T = 10^{-60/10} = 10^{-6}$. One photon in a million.

**2.** Two independent reasons: (a) the **no-cloning theorem** forbids copying
an unknown quantum state, so there is no quantum amplifier; (b) **measurement
destroys** the state — reading the qubit collapses it to a single classical bit
and discards the amplitudes that carried the information.

**3.** $p_\text{seg} = 10^{-0.2 \times 200/10} = 10^{-4}$. All three must
succeed, giving $(10^{-4})^3 = 10^{-12}$. The direct link gives
$10^{-0.2 \times 600/10} = 10^{-12}$. **Identical** — segmentation alone buys
nothing, because $(10^{-\alpha L/10n})^n = 10^{-\alpha L/10}$. You need quantum
memory for the segments to wait for each other.

### Answers to 4–6

**4.** $A$ and $D$ are left in a **maximally entangled Bell state** — one of the
four, depending on the measurement outcome, each with probability $1/4$. To use
it you also need the **two classical bits** broadcast from the measurement,
which tell you which **Pauli correction** to apply. Without those bits the state
is still entangled but is a random Bell state, which is not directly usable.

**5.** Two effects. First, $H_n$ grows only **logarithmically**, so beyond a few
segments each extra station buys less. Second, and decisively, the **memory must
hold entanglement while the slowest segment completes**, so longer chains demand
longer coherence times. Past the point where the required storage time exceeds
the memory lifetime, the stored entanglement decoheres before it can be swapped
and the link quality collapses.

**6.** Any two of: **device-independent QKD** — a Bell test certifies the
devices from outside, which a point-to-point prepare-and-measure link cannot do;
**distributed quantum computing** — entanglement lets separated processors act
as one larger machine, beating the qubit-count limit of a single device;
**blind quantum computation** — the server must not learn the input, which needs
a network client–server structure; **entangled sensor networks** — the advantage
comes from shared correlations across many nodes, not from any single link.

## Summary

- **Direct transmission fails exponentially**: fibre at 1550 nm loses 0.2 dB/km,
  so 1000 km gives $T = 10^{-20}$ — one detection every $10^{14}$ s, about 3.2
  million years at 1 MHz.
- **You cannot amplify**, because of no-cloning and because measurement destroys
  the state. The classical repeater trick is unavailable.
- **Entanglement swapping**: a Bell measurement on the inner halves of two Bell
  pairs entangles the outer halves. Verified — all four outcomes leave $A$ and
  $D$ maximally entangled (residual $\sim 10^{-14}$), so the swap is
  deterministic and the outcome only selects a Pauli correction.
- **Segmentation alone buys nothing**: $(10^{-\alpha L/10n})^n = 10^{-\alpha L/10}$ exactly, verified to six decimals. The gain comes from **quantum memory
  plus heralding**, which turns an exponential probability penalty into a
  logarithmic time penalty, $\mathbb{E}[T] = H_n/(p_\text{seg}R)$.
- **Verified payoff** over 1000 km: 3.2 million years direct, 0.2 seconds with
  four segments, scaling as $H_n$. The cost is a **memory coherence time** of
  roughly a millisecond for an 8-segment chain.
- **A quantum internet** enables distributed quantum computing,
  device-independent QKD, blind quantum computation, and entangled sensor
  networks — all tasks whose value lies in **correlations between separated
  parties** rather than raw bandwidth.
- **No faster-than-light signalling**: every swap needs a classical broadcast of
  the outcome.

## References

- Briegel, H.-J., Dür, W., Cirac, J. I. and Zoller, P., "Quantum Repeaters,"
  *Physical Review Letters* **81**, 5932 (1998) — the original proposal.
-Żukowski, M., Zeilinger, A., Horne, M. A. and Ekert, A. K., "'Event-ready-detectors' Bell experiment via entanglement swapping," *Physical Review Letters* **71**, 4287 (1993).
- Bennett, C. H. et al., "Purification of Noisy Entanglement and Faithful
  Teleportation via Noisy Channels," *Physical Review Letters* **76**, 722
  (1996).
- Nielsen, M. A. and Chuang, I. L., *Quantum Computation and Quantum
  Information*, §12.6 — quantum error correction and repeaters.
- Wootters, W. K. and Zurek, W. H., "A single quantum cannot be cloned,"
  *Nature* **299**, 802 (1982) — the no-cloning theorem.
- [Quantum Teleportation](26_teleportation.md) — the correction-step
  structure reused here.
- [Superdense Coding](66_superdense_coding.md) — the dual protocol and the
  classical-broadcast constraint.
- [NISQ Limitations](62_nisq_limitations.md) — why linking processors is
  attractive.
- [Calibrated Noise Models and Connectivity Topologies](61_platform_comparison.md)
  — memory coherence times across hardware platforms.
- [Surface Codes](52_surface_codes.md) — entanglement purification and
  error correction in a repeater link.

---

**Next:** [Quantum Simulation and Many-Body Systems](69_quantum_simulation.md)
