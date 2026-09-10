<!-- track: circuit -->
# The Four Bell States

There are exactly four maximally entangled two-qubit states. They form an
orthonormal basis for the two-qubit space, and every one of them is built from
the *same* two-gate circuit with small modifications.

## The four states

$$|\Phi^+\rangle = \tfrac{1}{\sqrt2}\left(|00\rangle + |11\rangle\right)$$

$$|\Phi^-\rangle = \tfrac{1}{\sqrt2}\left(|00\rangle - |11\rangle\right)$$

$$|\Psi^+\rangle = \tfrac{1}{\sqrt2}\left(|01\rangle + |10\rangle\right)$$

$$|\Psi^-\rangle = \tfrac{1}{\sqrt2}\left(|10\rangle - |01\rangle\right)$$

$\Phi$ states have **correlated** bits (both same). $\Psi$ states have
**anti-correlated** bits (always different). The $\pm$ is the relative phase.

## Building each one

Start from the base circuit: **H on q0, then CNOT (control q0, target q1)**.
That gives $|\Phi^+\rangle$. The other three need one extra gate.

| State | Circuit | Measured outcomes |
|---|---|---|
| $\Phi^+$ | `H q0`, `CNOT q0->q1` | `00` and `11`, 50/50 |
| $\Phi^-$ | `X q0`, `H q0`, `CNOT q0->q1` | `00` and `11`, 50/50 |
| $\Psi^+$ | `H q0`, `CNOT q0->q1`, `X q1` | `01` and `10`, 50/50 |
| $\Psi^-$ | `X q0`, `H q0`, `CNOT q0->q1`, `X q1` | `01` and `10`, 50/50 |

An equivalent route to $\Phi^-$ is `H q0`, `Z q0`, `CNOT q0->q1`.

## The crucial observation

**$\Phi^+$ and $\Phi^-$ produce identical histograms.** Both give 50% `00` and
50% `11`. On counts alone they are indistinguishable.

They are nonetheless completely different states — orthogonal, in fact. The
entire difference is the **relative phase** on the $|11\rangle$ term.

To see it in this platform:

1. Build $\Phi^+$, run it, open the **Phase disk**. Both states sit at 0°.
2. Build $\Phi^-$, run it. $|11\rangle$ now sits at 180°.
3. Or use the **Amplitude / phase table** and read the phase column directly.
4. Or turn on **Colour bars by relative phase** on the histogram — same heights,
   different colours.

This is exactly why a counts-only view of quantum computing is misleading, and
why this platform gives you phase views at all.

## Distinguishing them properly

If phase is invisible to measurement, how does anyone tell $\Phi^+$ from
$\Phi^-$ experimentally? You **undo** the preparation:

Apply `CNOT q0->q1` then `H q0` — the inverse of the Bell circuit. Then measure.

- $\Phi^+$ returns `00` with certainty
- $\Phi^-$ returns `01` with certainty (q0 is 1)
- $\Psi^+$ returns `10`
- $\Psi^-$ returns `11`

This is **Bell basis measurement**, and it is the foundation of quantum
teleportation and superdense coding. Try it: build $\Phi^-$, append the inverse
circuit, and confirm you get a single deterministic outcome.

## Why "maximally entangled"

For all four states, tracing out either qubit leaves the maximally mixed state
$\tfrac{1}{2}I$. Each qubit individually looks like a fair coin; all the
information lives in the correlation.

The platform reports this directly:

- **Entanglement S = 1.000** (one full bit of entropy)
- **Concurrence C = 1.00**
- Both Bloch vectors have length zero
- The **density matrix** shows bright off-diagonal corners — those corners are
  the coherence. A classical 50/50 mixture of `00` and `11` would show the same
  diagonal but **no** corners.

That last comparison is the sharpest way to see the difference between
entanglement and mere classical correlation.

## Exercise

1. Build all four Bell states and record the histogram and phase table for each.
2. Confirm $\Phi^+$ and $\Phi^-$ have identical counts and differing phase.
3. Append the inverse Bell circuit to each and verify the four distinct
   deterministic outcomes.
4. Enable the noise model on $\Phi^+$ with T1 = 5, T2 = 4. Watch the forbidden
   outcomes `01` and `10` appear and concurrence fall.
