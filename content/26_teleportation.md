# Quantum Teleportation

Teleportation is the clearest illustration of what entanglement is *for*. Two
parties share an entangled pair; one of them performs a measurement on her
qubit together with an unknown state, sends two ordinary classical bits, and
the other party ends up holding that unknown state. The state is destroyed at
the sender and recreated at the receiver. It is not faster-than-light
communication, and it does not violate no-cloning — understanding exactly why
is most of the value of the protocol.

## Learning objectives

By the end of this lesson you should be able to:

- **Describe** the teleportation protocol step by step, naming the gates and
  the two classical bits.
- **Compute** Bob's correction for each of the four measurement outcomes, and
  verify numerically that the final state matches the input.
- **Explain** why the outcome distribution is uniform and independent of the
  teleported state, and what that implies about information leakage.
- **Demonstrate** that Bob's qubit is maximally mixed until the classical bits
  arrive, so teleportation cannot transmit information superluminally.
- **State** the resources consumed, and why teleportation does not violate the
  no-cloning theorem.

## The setup

### Resources

- **Three qubits**: qubit 0 holds $|\psi\rangle$, the unknown state to
  teleport; qubits 1 and 2 are a Bell pair, with Alice holding qubit 1 and Bob
  holding qubit 2.
- **One entangled pair** shared in advance.
- **Two classical bits** sent from Alice to Bob.

The total cost is one ebit plus two classical bits to move one qubit.

### The circuit

1. **Prepare the Bell pair** on qubits 1 and 2: $H$ on qubit 1, then
   CNOT from 1 to 2, giving $|\Phi^+\rangle = \tfrac{1}{\sqrt{2}}(|00\rangle + |11\rangle)$.
2. **Alice entangles her unknown state with her half**: CNOT from qubit 0 to
   qubit 1.
3. **Alice rotates**: $H$ on qubit 0.
4. **Alice measures** qubits 0 and 1 in the computational basis, producing
   classical bits $c_0$ and $c_1$.
5. **Bob corrects**: apply $X$ if $c_1 = 1$, then $Z$ if $c_0 = 1$.

## Why it works

### The algebra

After steps 1–3, the three-qubit state can be rearranged (by expanding in the
Bell basis) into

$$|\psi\rangle_0 |\Phi^+\rangle_{12} = \frac{1}{2}\sum_{c_0, c_1 \in \{0,1\}} |c_0 c_1\rangle_{01} \otimes \left(X^{c_1} Z^{c_0}\right)|\psi\rangle_2$$

Measuring qubits 0 and 1 selects one of the four terms. Bob's qubit is left in
$\left(X^{c_1} Z^{c_0}\right)|\psi\rangle$ — the right state, up to a known
Pauli correction. Applying the inverse Pauli (both $X$ and $Z$ are their own
inverses) recovers $|\psi\rangle$ exactly.

### Verification

Teleporting $|\psi\rangle = 0.6|0\rangle + 0.8|1\rangle$:

| Outcome $c_0c_1$ | Bob's state after correction | Fidelity |
|---|---|---|
| 00 | $(0.6, 0.8)$ | 1.000 |
| 01 | $(0.6, 0.8)$ | 1.000 |
| 10 | $(0.6, 0.8)$ | 1.000 |
| 11 | $(-0.6, -0.8)$ | 1.000 |

The $(1,1)$ case differs by an overall factor of $-1$, which is a global phase
and therefore physically identical. Every outcome has fidelity exactly 1.

The protocol works for arbitrary complex amplitudes, not just real ones.

## Why it is not faster than light

### The classical bits are essential

Bob's qubit before the correction is in the state
$\left(X^{c_1} Z^{c_0}\right)|\psi\rangle$, but he does not know *which* of the
four it is until $c_0$ and $c_1$ arrive. Those travel no faster than light.

### The reduced state is maximally mixed

Tracing out Alice's qubits from the joint state before any measurement
information is used:

$$\rho_2 = \begin{pmatrix} 0.5 & 0 \\ 0 & 0.5 \end{pmatrix} = \frac{I}{2}$$

Bob's qubit is maximally mixed — it carries no information about $|\psi\rangle$
whatsoever, and no measurement he performs on it alone can reveal anything.
Only in combination with Alice's two classical bits does the state become
useful. This is the **no-signalling** property, and it is why teleportation is
consistent with relativity.

### The outcomes are uniformly random

The measurement outcome distribution is $(0.25, 0.25, 0.25, 0.25)$ — uniform,
and the same regardless of what $|\psi\rangle$ is. If the outcomes depended on
$|\psi\rangle$, Bob could learn something from the statistics alone. They do
not, so he cannot.

## Why it does not violate no-cloning

The no-cloning theorem forbids producing a *second* copy while keeping the
first. Teleportation never does that: Alice's measurement destroys her copy,
and Bob's qubit becomes the state only after receiving the classical bits.

At every instant there is exactly one copy of $|\psi\rangle$. The state has
moved, not been duplicated. Alice's original qubit ends up in one of the
computational basis states, holding no remnant of the amplitude information.

This is also why the protocol is consistent with no-cloning being *necessary*
for QKD security: an eavesdropper cannot split a transmitted qubit and keep a
copy for later.

## Practical example

### Building the circuit

```python
import numpy as np

ket0 = np.array([1, 0], dtype=complex)
ket1 = np.array([0, 1], dtype=complex)
I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)


def embed(ops, n=3):
    """Build an n-qubit operator from {qubit index: 2x2 matrix}."""
    M = np.eye(1, dtype=complex)
    for q in range(n):
        M = np.kron(M, ops.get(q, I2))
    return M


def cnot(control, target, n=3):
    M = np.zeros((2**n, 2**n), dtype=complex)
    for idx in range(2**n):
        bits = [(idx >> (n - 1 - i)) & 1 for i in range(n)]
        if bits[control] == 1:
            bits[target] ^= 1
        M[sum(b << (n - 1 - i) for i, b in enumerate(bits)), idx] = 1
    return M


def teleport(psi):
    """Run Alice's half of the protocol; return the pre-measurement state."""
    s = np.kron(psi, np.kron(ket0, ket0))
    s = embed({1: H}) @ s          # prepare the Bell pair on qubits 1, 2
    s = cnot(1, 2) @ s
    s = cnot(0, 1) @ s             # Alice entangles |psi> with her half
    s = embed({0: H}) @ s          # Alice rotates
    return s
```

### Bob's correction, for each outcome

```python
def bob_state(s, c0, c1):
    """Project onto Alice's outcome, apply Bob's correction, return his qubit."""
    t = s.copy()
    for idx in range(8):
        bits = [(idx >> (2 - i)) & 1 for i in range(3)]
        if bits[0] != c0 or bits[1] != c1:
            t[idx] = 0
    t = t / np.linalg.norm(t)
    correction = I2
    if c1:
        correction = correction @ X
    if c0:
        correction = correction @ Z
    t = embed({2: correction}) @ t
    return t.reshape(2, 2, 2)[c0, c1, :]


psi = 0.6 * ket0 + 0.8 * ket1
s = teleport(psi)
print("teleporting |psi> =", np.round(psi, 4))
print("\noutcome   Bob's state after correction   fidelity")
for c0 in (0, 1):
    for c1 in (0, 1):
        b = bob_state(s, c0, c1)
        print(f"  {c0}{c1}       {str(np.round(b, 4)):28s} "
              f"{abs(np.vdot(psi, b))**2:.6f}")
```

### No-signalling and the resource accounting

```python
# Alice's outcomes are uniform and independent of |psi>.
p = np.abs(s) ** 2
marginal = np.zeros(4)
for idx in range(8):
    bits = [(idx >> (2 - i)) & 1 for i in range(3)]
    marginal[2 * bits[0] + bits[1]] += p[idx]
print("outcome distribution:", np.round(marginal, 4))

# Bob's qubit alone is maximally mixed until the bits arrive.
rho_b = np.einsum("ija,ijb->ab", s.reshape(2, 2, 2), s.reshape(2, 2, 2).conj())
print("Bob's reduced state:\n", np.round(rho_b, 4))
print("  equals I/2:", np.allclose(rho_b, np.eye(2) / 2))

# The protocol works for arbitrary complex amplitudes.
psi2 = (0.3 + 0.4j) * ket0 + (0.5 - 0.2j) * ket1
psi2 = psi2 / np.linalg.norm(psi2)
s2 = teleport(psi2)
ok = all(abs(abs(np.vdot(psi2, bob_state(s2, c0, c1)))**2 - 1) < 1e-9
         for c0 in (0, 1) for c1 in (0, 1))
print("\nworks for a complex state too:", ok)
```

Running the blocks in order prints Bob's corrected state for each of the four
outcomes with `fidelity` `1.000000` every time; the $(1,1)$ outcome differs by
a global sign, which is physically irrelevant. The outcome distribution is
`[0.25 0.25 0.25 0.25]`, Bob's reduced state is $\begin{pmatrix}0.5 & 0 \\ 0 & 0.5\end{pmatrix}$
and the check `equals I/2` returns `True`. The complex-amplitude test also
returns `True`.

## Common misconceptions

- **"Teleportation sends information faster than light."** It cannot. Bob's
  qubit is maximally mixed until the two classical bits arrive, and those are
  limited by the speed of light.
- **"Teleportation is cloning."** Alice's copy is destroyed. At no point do two
  copies of $|\psi\rangle$ exist.
- **"Matter or energy is transported."** Only an unknown *state* moves. Bob
  already possesses his qubit; only its state changes.
- **"The outcome bits encode information about $|\psi\rangle$."** They are
  uniformly random and independent of $|\psi\rangle$. This is exactly why the
  protocol leaks nothing.
- **"Bob can skip the correction if he is lucky."** He cannot know whether he
  was lucky without the classical bits, and an uncorrected qubit gives the
  wrong state half the time.

## Exercises

1. Write out the circuit for teleportation as a sequence of gates on three
   qubits, and identify which qubit each acts on.
2. Verify that $X$ and $Z$ are their own inverses, and explain why that means
   Bob's correction is $X^{c_1}Z^{c_0}$ regardless of order conventions.
3. Compute Bob's state for outcome $c_0c_1 = 01$ if he mistakenly applies $Z$
   instead of $X$. What state does he end up with, and what is the fidelity?
4. Show numerically that Alice's outcome distribution is uniform for two very
   different input states.
5. Explain in two sentences why teleportation is consistent with no-cloning.
6. If Alice and Bob lack a pre-shared Bell pair, can they teleport? What would
   happen if they tried to establish one after Alice received $|\psi\rangle$?

## Summary

- Teleportation moves an unknown qubit state using one shared Bell pair plus
  two classical bits.
- After Alice's CNOT, $H$ and measurement, Bob's qubit is
  $X^{c_1}Z^{c_0}|\psi\rangle$; applying $X^{c_1}Z^{c_0}$ recovers $|\psi\rangle$
  with fidelity 1 for every outcome.
- The outcome distribution is uniform and independent of $|\psi\rangle$, so
  nothing about the state is revealed by the measurement statistics.
- Bob's reduced state is $I/2$ until the classical bits arrive, so the protocol
  cannot signal faster than light.
- Alice's copy is destroyed, so no-cloning is not violated — the state moves,
  it is never duplicated.

## References

- Bennett, C. H. et al. *Teleporting an unknown quantum state via dual classical
  and Einstein-Podolsky-Rosen channels* (PRL, 1993) — the original protocol.
- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum
  Information*, §1.3.7 — teleportation and its relationship to no-cloning.
- The [No-Cloning Theorem](22_no_cloning.md) lesson — why the protocol does not
  contradict it.

---

**Previous:** [Tensor Products](24_tensor_products.md) ·
**Next:** [Reading Quantum Results](27_reading_results.md)
