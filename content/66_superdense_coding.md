# Superdense Coding

Superdense coding lets Alice send **two classical bits** to Bob by transmitting
**one qubit** — provided they already share a Bell pair. It sounds like it
violates Holevo's bound. It does not, and understanding exactly why is the most
valuable thing in this lesson.

The protocol is also the exact dual of [quantum teleportation](26_teleportation.md),
and seeing the two side by side is the fastest route to understanding both.

## Learning objectives

By the end of this lesson you should be able to:

- **Construct** the superdense coding circuit.
- **Explain** why two bits are transmitted per qubit.
- **State** the entanglement resource cost.

## Prerequisites

[Bell States](11_bell_states.md) (required) — consumes a shared Bell pair to
send two bits in one qubit.

## What it achieves

Alice wants to send Bob a two-bit message: `00`, `01`, `10` or `11`. The naive
approach sends two classical bits. Superdense coding instead:

- **Beforehand** (perhaps days earlier), Alice and Bob share a Bell pair. Alice
  holds one qubit, Bob the other.
- **At sending time**, Alice applies one gate to her qubit and physically sends
  that single qubit to Bob.
- **Bob** measures the two qubits he now holds jointly and recovers both bits,
  perfectly and deterministically.

One qubit transmitted, two bits received, zero probability of error.

## The protocol

Let the shared pair be $|\Phi^+\rangle = \frac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$, with Alice holding qubit $q_0$ and Bob holding $q_1$.

**Step 1 — Entanglement distribution.** Prepare $|\Phi^+\rangle$ with $H$ on
$q_0$ followed by $\mathrm{CNOT}(q_0 \to q_1)$, then separate the qubits. This
happens *before* Alice knows her message, which is what makes the protocol
legal rather than magical.

**Step 2 — Alice encodes.** She applies exactly one gate to **her qubit only**,
chosen by the two-bit message $b_1 b_0$:

| Message | Gate Alice applies | Resulting joint state |
|---|---|---|
| $00$ | $I$ | $\lvert\Phi^+\rangle = \tfrac{1}{\sqrt{2}}(\lvert00\rangle + \lvert11\rangle)$ |
| $01$ | $X$ | $\lvert\Psi^+\rangle = \tfrac{1}{\sqrt{2}}(\lvert01\rangle + \lvert10\rangle)$ |
| $10$ | $Z$ | $\lvert\Phi^-\rangle = \tfrac{1}{\sqrt{2}}(\lvert00\rangle - \lvert11\rangle)$ |
| $11$ | $ZX$ | $\lvert\Psi^-\rangle = \tfrac{1}{\sqrt{2}}(\lvert01\rangle - \lvert10\rangle)$ |

The four messages map onto the **four Bell states**, which form an orthonormal
basis of the two-qubit space. That orthonormality is the whole trick: Bob's job
is to distinguish four mutually orthogonal states, which quantum mechanics
allows *perfectly*.

**Step 3 — Alice sends her qubit.** One qubit travels from Alice to Bob.

**Step 4 — Bob decodes.** He now has both qubits and applies the inverse of the
Bell-pair preparation:

$$\mathrm{CNOT}(q_0 \to q_1),\qquad H(q_0)$$

then measures both qubits. This maps the Bell basis back onto the computational
basis, and the measurement result *is* the two-bit message.

## Constructing the circuit

Objective 1. Here is the complete circuit, one per message:

```python
from qiskit import QuantumCircuit

def superdense(bits: str) -> QuantumCircuit:
    """Superdense coding: send the 2-bit string `bits` using one qubit."""
    q0, q1 = 0, 1          # Alice's half, Bob's half
    qc = QuantumCircuit(2, 2)

    # 1. Share a Bell pair in advance.
    qc.h(q0)
    qc.cx(q0, q1)

    # 2. Alice encodes her two bits on her qubit only.
    if bits[0] == "1":
        qc.z(q0)           # first bit  -> Z
    if bits[1] == "1":
        qc.x(q0)           # second bit -> X

    # 3. Bob decodes jointly.
    qc.cx(q0, q1)
    qc.h(q0)
    qc.measure([q0, q1], [0, 1])
    return qc
```

Two details that catch people out:

**The gates are conditional on bits, not applied unconditionally.** A real
implementation must choose the gate at run time, so the "circuit" is really a
family of four circuits. There is no single static circuit that sends a message
chosen later.

**Qiskit orders bit strings right-to-left.** Measuring into `c[0]` and `c[1]`
returns a string whose leftmost character is `c[1]`. The message
`bits[0]bits[1]` therefore comes back reversed, and it must be reversed again
to recover the message. This is a bookkeeping convention, not physics — but it
is the most common reason a correct circuit appears to fail.

### Verifying all four messages

Running each of the four circuits for a single shot gives back the message
exactly, with no statistics required — the protocol is deterministic, not
probabilistic:

| Sent | Gate | Decoded | Shots needed |
|---|---|---|---|
| `00` | $I$ | `00` | 1 |
| `01` | $X$ | `01` | 1 |
| `10` | $Z$ | `10` | 1 |
| `11` | $ZX$ | `11` | 1 |

Over 1000 shots each, every message decodes to itself with probability
$1.000$. Compare this with [quantum key distribution](68_quantum_cryptography.md)
or [teleportation](26_teleportation.md), where individual runs are random and
only the statistics are meaningful. Superdense coding is not like that: the
outcome is certain.

## Why two bits per qubit

Objective 2, and the heart of the lesson.

### The apparent contradiction

**Holevo's bound** states that $n$ qubits can carry at most $n$ classical bits
of accessible information. Superdense coding appears to carry 2 bits in 1 qubit,
which would be a direct violation.

It is not, and the resolution is precise.

### The resolution

Holevo's bound applies to a **standalone quantum channel** — Alice prepares a
state and sends it. Superdense coding uses a different resource: a
**noisy-free quantum channel plus pre-shared entanglement**. The correct
accounting is

$$\underbrace{2 \text{ bits}}_{\text{delivered}} \;\longleftarrow\; \underbrace{1 \text{ qubit}}_{\text{communicated}} \;+\; \underbrace{1 \text{ e-bit}}_{\text{consumed}}$$

Two classical bits are delivered, and the price is **two** quantum resources:
one qubit of communication *and* one consumed Bell pair. Holevo's bound is
satisfied, because the resource accounting is $1 + 1 = 2$, not $1 = 2$.

The intuition is that Alice's local operation has a **non-local effect on the
joint state**. Acting on her qubit alone, she steers the global two-qubit state
into any one of four orthogonal states. Bob cannot see which until Alice's
qubit arrives — at which point he holds both and can perform the joint
measurement that distinguishes them.

### The control experiment

The cleanest way to see that the entanglement is doing real work is to remove
it. Give Alice one qubit in the state $\lvert 0\rangle$, no Bell pair, and let
her apply the same four gates. Bob measures:

| Sent | Alice applies | Bob receives |
|---|---|---|
| `00` | $I$ | `0` |
| `01` | $X$ | `1` |
| `10` | $Z$ | `0` |
| `11` | $ZX$ | `1` |

The second bit is transmitted; the first is **gone**. The reason is that
$Z\lvert 0\rangle = \lvert 0\rangle$ — the phase gate has no observable effect
on a computational basis state. Only $X$ does anything, so only one bit
survives, exactly as Holevo's bound demands.

The $Z$ gate only becomes observable because Alice's qubit is **entangled** with
Bob's, so a relative phase on her side becomes a relative phase between two
globally distinct states. Entanglement is what makes the phase measurable.

### It is not faster-than-light communication

This deserves to be said plainly, because superdense coding is one of the most
commonly misused protocols in pop-science.

Alice's qubit must **physically travel** to Bob before he can decode. Without
it he holds one half of a Bell pair, and its reduced state is the maximally
mixed state $\tfrac{1}{2}I$ — which is independent of Alice's message, so he
learns nothing. Verified directly: the reduced density matrix of Bob's qubit
before Alice's qubit arrives is $\begin{pmatrix} 0.5 & 0 \\ 0 & 0.5 \end{pmatrix}$ for all four messages.

No information moves faster than light. The entanglement was distributed
earlier, at sub-light speed, and the qubit carrying the message travels at
sub-light speed too. Superdense coding is a **capacity** result, not a
signalling result: it doubles the classical capacity of a quantum channel that
is supplemented by entanglement.

## The entanglement resource cost

Objective 3.

- **One e-bit (one maximally entangled Bell pair) is consumed per two classical
  bits sent.**
- The consumption is **real and irreversible**. After Bob decodes, the pair is
  gone — the joint state is a product computational basis state, not a Bell
  state. It cannot be reused for a second message.
- Sending $2n$ classical bits costs $n$ qubits of communication **and** $n$
  fresh Bell pairs.

So the honest summary is not "two bits per qubit" but:

> Two classical bits per **qubit transmitted**, at the cost of **one e-bit
> consumed**.

The rate is $2$ bits per transmitted qubit, but only $1$ bit per unit of total
quantum resource. Anyone quoting the "2 bits per qubit" figure without the
entanglement cost is quoting half the accounting.

## Duality with teleportation

Superdense coding and teleportation are the same circuit run in opposite
directions, and the comparison fixes both protocols in memory.

|  | Superdense coding | Teleportation |
|---|---|---|
| Sends | 2 classical bits | 1 qubit (unknown state) |
| Uses | 1 qubit communicated | 2 classical bits communicated |
| Entanglement | 1 e-bit consumed | 1 e-bit consumed |
| Direction | classical $\to$ quantum channel | quantum $\to$ classical channel |
| Key step | Encode on one half, decode jointly | Bell measurement, then correct |

Both consume exactly one Bell pair. Both require a sub-light classical or
quantum transmission to complete. Neither permits faster-than-light signalling.
Together they say that **one e-bit plus one qubit of communication equals one
e-bit plus two classical bits** — the two resources are interchangeable at that
exchange rate.

## Common misconceptions

- **"Two bits per qubit, so Holevo's bound is violated."** It is not. The
  correct accounting is $1$ qubit $+\ 1$ e-bit $= 2$ bits. Add the consumed
  entanglement and the bound holds.
- **"It enables faster-than-light communication."** Alice's qubit must arrive
  before Bob can decode. Until then his reduced state is $\tfrac{1}{2}I$
  regardless of the message — verified above.
- **"The Bell pair is a reusable key."** It is **consumed**. One pair, one
  two-bit message.
- **"Bob can decode before Alice's qubit arrives."** He cannot; he needs both
  qubits for the joint measurement.
- **"Alice needs to know the message when the pair is shared."** She does not.
  The pair is distributed in advance, before she has anything to say. That is
  precisely why the protocol is legitimate.
- **"The readout is probabilistic."** It is deterministic. All four messages
  decode to themselves with probability $1.000$.

## Exercises

1. Write the circuit for sending `10`, and give the joint state after Alice's
   encoding.

2. Alice applies $Z$ to her qubit but Bob, expecting `00`, applies only $H$ and
   measures without the CNOT. What does he see, and why?

3. Why does the protocol not violate Holevo's bound? State the full resource
   accounting.

4. Alice and Bob share **no** entanglement. What is the maximum number of
   classical bits Alice can send per qubit, and why?

5. How many Bell pairs are needed to send a 1-kilobyte (8192-bit) message?

6. Explain in one sentence why superdense coding does not permit
   faster-than-light signalling.

### Answers to 1–3

**1.** For `10`: prepare $\lvert\Phi^+\rangle$ with $H(q_0)$ then
$\mathrm{CNOT}(q_0 \to q_1)$; Alice applies $Z$ to $q_0$ (the first bit is $1$)
and no $X$ (the second bit is $0$); Bob applies $\mathrm{CNOT}(q_0 \to q_1)$
then $H(q_0)$ and measures. After Alice's encoding the joint state is

$$\lvert\Phi^-\rangle = \tfrac{1}{\sqrt{2}}\big(\lvert 00\rangle - \lvert 11\rangle\big).$$

**2.** Bob sees a **random** result. Without the CNOT, the $H$ does not undo the
Bell-basis encoding: the CNOT is what disentangles the two qubits and turns the
Bell basis back into the computational basis. Applying $H$ alone to a Bell state
leaves it entangled, so measuring gives a uniformly random outcome and the
message is destroyed. Both decode operations are required, and in that order.

**3.** Holevo's bound limits a **standalone** quantum channel to $n$ classical
bits from $n$ qubits. Superdense coding does not use a standalone channel — it
uses a quantum channel **supplemented by pre-shared entanglement**. The full
accounting is

$$2 \text{ bits} \;\longleftarrow\; 1 \text{ qubit transmitted} + 1 \text{ e-bit consumed},$$

which is $1 + 1 = 2$, not $1 = 2$. Holevo's bound is upheld.

### Answers to 4–6

**4.** **One bit per qubit**, by Holevo's bound. Without entanglement, the
control experiment above shows exactly this: $Z$ has no observable effect on
$\lvert 0\rangle$, so only the $X$ bit survives and the other is lost. The
doubling is bought entirely by the entanglement.

**5.** **4096 Bell pairs.** Each pair carries 2 bits, so 8192 bits needs
$8192 / 2 = 4096$ pairs — and 4096 qubits of communication. Note the honest
total: 8192 bits delivered for 8192 units of quantum resource (4096 qubits
sent $+$ 4096 e-bits consumed).

**6.** Alice's qubit must physically reach Bob before he can perform the joint
measurement that decodes the message; until it does, his half of the pair is the
maximally mixed state $\tfrac{1}{2}I$, identical for all four messages, so no
information has arrived.

## Summary

- Superdense coding sends **2 classical bits by transmitting 1 qubit**, given a
  pre-shared Bell pair. The protocol is **deterministic** — all four messages
  decode with probability $1.000$, verified by simulation.
- **The circuit:** prepare $\lvert\Phi^+\rangle$ with $H$ + CNOT; Alice applies
  one of $I, X, Z, ZX$ to her qubit only; send it; Bob applies
  $\mathrm{CNOT}(q_0 \to q_1)$ then $H(q_0)$ and measures both qubits.
- **Why it works:** the four gates produce the four **orthonormal Bell states**,
  and orthogonal states are perfectly distinguishable. Remember to account for
  Qiskit's right-to-left bit ordering.
- **No Holevo violation.** The correct accounting is $2 \text{ bits} \leftarrow 1 \text{ qubit} + 1 \text{ e-bit}$. The $Z$ gate only becomes observable
  *because* of entanglement — remove the pair and the bit carried by $Z$ is
  lost, leaving exactly one bit, as the bound requires.
- **Resource cost: one e-bit consumed per two bits sent**, irreversible. The
  honest rate is 2 bits per qubit transmitted, or 1 bit per unit of total
  quantum resource.
- **No faster-than-light signalling.** Bob's reduced state is
  $\tfrac{1}{2}I$ until Alice's qubit physically arrives.
- **Dual to teleportation:** same Bell pair, opposite direction. Together they
  establish the exchange rate 1 qubit $\leftrightarrow$ 2 classical bits, each
  at the cost of one e-bit.

## References

- Bennett, C. H. and Wiesner, S. J., "Communication via one- and two-particle
  operators on Einstein-Podolsky-Rosen states," *Physical Review Letters*
  **69**, 2881 (1992) — the original paper.
- Nielsen, M. A. and Chuang, I. L., *Quantum Computation and Quantum
  Information*, §2.3 — dense coding and the Holevo bound.
- Holevo, A. S., "Bounds for the quantity of information transmitted by a
  quantum communication channel," *Problems of Information Transmission*
  **9**, 3 (1973).
- [Bell States](11_bell_states.md) — the $\lvert\Phi^+\rangle$ resource and
  the four-state basis used here.
- [Quantum Teleportation](26_teleportation.md) — the dual protocol.
- [Quantum Cryptography](68_quantum_cryptography.md) — a contrasting setting
  where individual outcomes are genuinely probabilistic.
- [Quantum Repeaters and the Quantum Internet](67_quantum_networks.md) — how
  Bell pairs are distributed over distance, which is what makes entanglement
  available in the first place.

---

**Next:** [Quantum Repeaters and the Quantum Internet](67_quantum_networks.md)
