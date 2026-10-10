# Quantum Cryptography, QKD and Post-Quantum Cryptography

Two things are usually conflated under "quantum cryptography", and separating
them is the main job of this lesson. **QKD** uses quantum hardware to distribute
a key, and its security comes from physics. **Post-quantum cryptography** uses
classical mathematics on classical hardware, and resists quantum attack because
the underlying problem is hard for quantum computers too. One is a hardware
solution to key distribution; the other is a software upgrade. They are not
alternatives to each other.

## Learning objectives

By the end of this lesson you should be able to:

- **Explain** how a QKD protocol detects eavesdropping, and compute the error
  rate an intercept-resend attack introduces.
- **State** the security assumption underlying QKD, and what it does *not*
  protect against.
- **Distinguish** post-quantum cryptography from quantum cryptography, and
  explain why one does not replace the other.

## Prerequisites

This lesson assumes the [no-cloning theorem](22_no_cloning.md) — the fact that
an unknown quantum state cannot be copied — since it is the foundation of QKD
security.

## BB84, step by step

### The setup

Alice wants to share a secret key with Bob over a channel an eavesdropper, Eve,
may be listening on.

Alice has two conjugate bases:

- The **$Z$ basis**: $|0\rangle$, $|1\rangle$.
- The **$X$ basis**: $|+\rangle = \tfrac{1}{\sqrt2}(|0\rangle+|1\rangle)$,
  $|-\rangle = \tfrac{1}{\sqrt2}(|0\rangle-|1\rangle)$.

### The protocol

1. **Alice sends.** For each position she picks a random bit and a random basis,
   and sends the corresponding state. Bit 0 in $Z$ is $|0\rangle$; bit 0 in $X$
   is $|+\rangle$.
2. **Bob measures.** For each state he picks a basis at random and records the
   result. He does not know Alice's choices.
3. **Basis reconciliation.** Over a *public* channel they reveal which basis
   each used — but never the bit values. They keep the positions where the
   bases matched and discard the rest.
4. **Error estimation.** They publicly compare a random sample of the kept bits.
   If the error rate is above a threshold, they abort.
5. **Classical post-processing.** Error correction and privacy amplification
   turn the remaining bits into a shorter, secret key.

On average half the positions survive step 3. Verified sifted-key fractions:
0.480, 0.498 and 0.502 for 1,000, 10,000 and 100,000 raw qubits — converging on
one half as expected.

### Why measurement in the wrong basis is useless

If Alice sends $|+\rangle$ and Bob measures in $Z$, he gets 0 or 1 with equal
probability — no information about her bit. Only matching bases give a
deterministic, correct result. That is what makes basis reconciliation
necessary, and it is also the seed of Eve's downfall.

## How eavesdropping is detected

### The intercept-resend attack

Eve cannot copy the states — no-cloning forbids it. Her simplest option is to
measure each qubit and resend something.

Suppose she measures in a random basis:

- **Half the time she guesses right.** She learns the bit correctly and resends
  the correct state. Bob, if his basis matches Alice's, gets the right answer.
  No error, but Eve has the bit.
- **Half the time she guesses wrong.** She gets a random result and resends a
  state in the *wrong* basis. When Bob's basis matches Alice's, his result is
  then random — so it disagrees with Alice's bit half the time.

Combining: an error appears in $\tfrac12 \times \tfrac12 = \tfrac14$ of the
sifted positions.

### Verified error rates

Simulating BB84 with and without an intercept-resend Eve:

| Raw qubits | Sifted key | QBER, no Eve | QBER, with Eve | Theory |
|---|---|---|---|---|
| 2,000 | 1,029 / 1,011 | 0.0000 | 0.2374 | 0.25 |
| 20,000 | 10,086 / 9,936 | 0.0000 | 0.2515 | 0.25 |

Without Eve the **quantum bit error rate is zero** — as it must be, since
matching bases give a deterministic result. With Eve it converges to the
predicted **0.25**.

That is the detection mechanism in one sentence: *eavesdropping necessarily
disturbs the states, and the disturbance shows up as errors.* Alice and Bob
sacrifice a sample of their key to measure it, and if the error rate exceeds
roughly 11% for BB84 they abort — the key is discarded and no harm is done
beyond the wasted transmission.

## The security assumption

### What QKD assumes

QKD security rests on the **laws of quantum mechanics**, primarily:

- **No-cloning** — an unknown state cannot be copied.
- **Measurement disturbance** — gaining information about a non-orthogonal state
  necessarily disturbs it.

Given those, security can be proven information-theoretically: no amount of
computing power, quantum or classical, lets Eve evade detection.

### What QKD does not assume — and does not protect

This is where the marketing usually overreaches.

- **It assumes authenticated classical channels.** Alice and Bob must be sure
  they are talking to each other. Without authentication, Eve simply impersonates
  Bob — a man-in-the-middle attack that QKD does nothing to prevent. An initial
  shared secret, or a classical signature scheme, is required.
- **It does not protect the endpoints.** QKD secures the *channel*. If Alice's or
  Bob's device is compromised, or their computer is infected, the key is
  worthless.
- **It requires dedicated hardware.** Photon sources, detectors and a quantum
  channel. This is not a software deployment.
- **Real devices deviate from the ideal.** Detector blinding, photon-number-splitting
  and timing attacks have all broken *implementations* of QKD, even though the
  protocol itself remains secure. The gap between provable protocol security and
  physical device security is real and has been exploited.

So the honest summary: QKD offers information-theoretic security for key
distribution, under assumptions about authentication and hardware that are
themselves substantial.

## Post-quantum cryptography

### What it is

**Post-quantum cryptography (PQC)** is classical cryptography — classical
algorithms, classical hardware — built on problems believed hard even for
quantum computers. The main families:

| Family | Underlying problem | Status |
|---|---|---|
| Lattice-based | Shortest vector / learning with errors | NIST standardised (ML-KEM, ML-DSA) |
| Code-based | Decoding random linear codes | NIST standardised (HQC) |
| Hash-based | Collision resistance of hash functions | NIST standardised (SLH-DSA) |
| Multivariate | Solving systems of quadratic equations | Some candidates |
| Isogeny-based | Finding isogenies between curves | Broken (SIKE, 2022) |

The isogeny entry is worth noting: SIKE was a leading candidate and was broken
by a **classical** attack in 2022. PQC candidates do not come with proofs — they
come with surviving scrutiny.

### Why it is the practical answer

- **It is a software upgrade.** No new hardware. It runs on the devices and
  networks we already have.
- **It replaces the vulnerable primitives directly.** Where you used RSA or
  ECDH, you use ML-KEM. The protocols mostly stay the same.
- **It is being standardised and deployed now.** NIST completed its first
  standards, and migration is underway across browsers, operating systems and
  payment infrastructure.

## The two are not alternatives

A table, because this is the crux:

| | QKD | Post-quantum cryptography |
|---|---|---|
| Mechanism | Quantum hardware | Classical mathematics |
| Security basis | Laws of physics | Computational hardness |
| Deployment | Dedicated hardware, point-to-point | Software, works everywhere |
| Authentication | Still required, from outside | Built into the schemes |
| Protects against | Channel interception | Any attack on the primitive |
| Cost | High, specialised | Low, incremental |

They solve different problems. PQC is the general answer to the threat from
Shor's algorithm. QKD addresses a narrower problem — key distribution over a
specific link — with different trade-offs. Organisations adopt PQC; some may
additionally deploy QKD for specific high-value links. PQC does not become
unnecessary because QKD exists, and QKD does not become useful because PQC has
candidates under scrutiny.

## Practical example

### Simulating BB84 with and without an eavesdropper

```python
import numpy as np

rng = np.random.default_rng(11)
S = 1 / np.sqrt(2)


def prepare(bit, basis):
    """Basis 0 = Z (|0>, |1>), basis 1 = X (|+>, |->)."""
    if basis == 0:
        return np.array([1, 0] if bit == 0 else [0, 1], dtype=complex)
    return np.array([S, S] if bit == 0 else [S, -S], dtype=complex)


def measure(psi, basis):
    if basis == 0:
        return 0 if rng.random() < abs(psi[0]) ** 2 else 1
    amp_plus = (psi[0] + psi[1]) / np.sqrt(2)
    return 0 if rng.random() < abs(amp_plus) ** 2 else 1


def run_bb84(n, eve=False):
    a_bits = rng.integers(0, 2, n)
    a_basis = rng.integers(0, 2, n)
    b_basis = rng.integers(0, 2, n)
    b_bits = np.zeros(n, dtype=int)
    for i in range(n):
        psi = prepare(a_bits[i], a_basis[i])
        if eve:                              # intercept-resend
            e_basis = rng.integers(0, 2)
            psi = prepare(measure(psi, e_basis), e_basis)
        b_bits[i] = measure(psi, b_basis[i])
    match = a_basis == b_basis               # basis reconciliation
    qber = np.mean(a_bits[match] != b_bits[match])
    return qber, int(match.sum())
```

### Comparing the error rates

```python
print("BB84 quantum bit error rate (QBER) on the sifted key")
for n in (2000, 20000):
    q0, k0 = run_bb84(n, eve=False)
    q1, k1 = run_bb84(n, eve=True)
    print(f"  n={n:6d}  no Eve: QBER={q0:.4f} (sifted {k0})"
          f"   with Eve: QBER={q1:.4f} (sifted {k1})   theory 0.25")

print("\nsifted key is about half the raw qubits:")
for n in (1000, 10000, 100000):
    _, k = run_bb84(n, eve=False)
    print(f"  raw={n:7d} -> sifted={k:7d}  ({k / n:.4f})")
```

Running the blocks in order confirms a QBER of 0.0000 without Eve and about
0.25 with an intercept-resend attacker, plus the halving from basis
reconciliation.

## Common misconceptions

- **"QKD is unbreakable."** The protocol has information-theoretic security.
  Real devices do not — several implementations have been broken.
- **"QKD removes the need for authentication."** It requires it. Without an
  authenticated channel, Eve simply impersonates Bob.
- **"PQC needs a quantum computer."** No — it is classical software, designed to
  resist one.
- **"PQC and QKD are competing solutions."** They address different problems at
  different layers.
- **"Shor's algorithm breaks all cryptography."** It breaks RSA, DH and ECC.
  Symmetric ciphers are only weakened by Grover, and doubling key lengths
  compensates.

## Exercises

1. In BB84, Alice sends $|+\rangle$. Bob measures in $Z$. What does he get, and
   with what probabilities?
2. Derive the 25% error rate for the intercept-resend attack step by step.
3. Why does QKD still need an authenticated classical channel?
4. Name two attacks that have broken QKD *implementations* without breaking the
   protocol.
5. Explain why SIKE being broken by a classical attack is a cautionary tale for
   PQC.
6. Give one scenario where QKD is a sensible addition, and one where PQC alone
   is the right answer.

## Summary

- **BB84**: Alice sends random bits in random conjugate bases; Bob measures in
  random bases; they keep positions where the bases matched — about half.
- Eavesdropping is **detected**, not prevented: an intercept-resend attack
  produces a **25%** error rate, verified by simulation at 0.2374 and 0.2515
  against 0.0000 with no eavesdropper.
- QKD security rests on **no-cloning** and **measurement disturbance**, giving
  information-theoretic security for the channel.
- It does **not** provide authentication, does not protect compromised endpoints,
  and real devices have been broken despite provable protocol security.
- **Post-quantum cryptography** is classical, standardised, deployable as a
  software upgrade, and is the general answer to Shor's algorithm.
- The two are **not alternatives** — they solve different problems.

## References

- Bennett, C. H. & Brassard, G. (1984), "Quantum cryptography: public key
  distribution and coin tossing" — BB84.
- Shor, P. W. & Preskill, J. (2000), "Simple proof of security of the BB84
  quantum key distribution protocol".
- NIST Post-Quantum Cryptography Standardization — ML-KEM (FIPS 203), ML-DSA
  (FIPS 204), SLH-DSA (FIPS 205).
- Castryck, W. & Decru, T. (2022) — the classical break of SIKE.
- The [No-Cloning Theorem](22_no_cloning.md) lesson — the foundation of QKD
  security.

---

**Previous:** [HHL Linear Systems](37_hhl.md)
