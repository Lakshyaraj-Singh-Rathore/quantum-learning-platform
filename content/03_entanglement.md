# Entanglement

A two-qubit state is **entangled** if it cannot be written as a product
$|\psi\rangle_A \otimes |\phi\rangle_B$ of independent single-qubit states.

## The Bell states

The canonical example is
$$|\Phi^+\rangle = \frac{|00\rangle + |11\rangle}{\sqrt2}$$

Recipe: **H on q0, then CNOT with q0 as control and q1 as target.**

Measuring gives `00` half the time and `11` half the time - and *never* `01` or `10`.
The individual outcomes are random, but they are perfectly **correlated**. Neither qubit
has a definite state of its own; only the pair does.

The four Bell states form a basis for two-qubit space:
$$|\Phi^\pm\rangle = \frac{|00\rangle \pm |11\rangle}{\sqrt2}, \qquad
|\Psi^\pm\rangle = \frac{|01\rangle \pm |10\rangle}{\sqrt2}$$

## GHZ states

Entanglement scales to more qubits. Applying H to q0 and then CNOTs onto q1, q2, ... gives
$$|GHZ\rangle = \frac{|00\cdots0\rangle + |11\cdots1\rangle}{\sqrt2}$$
Every qubit agrees with every other, all at once.

## What entanglement is not

Entanglement does **not** allow faster-than-light communication. Alice's measurement
outcome is random; Bob sees random results too. Only when they compare notes over a
classical channel does the correlation become visible. This is the *no-signalling*
principle, and it is why quantum teleportation still needs two classical bits sent the
ordinary way.

## Detecting entanglement in the platform

Run a Bell circuit and look at the histogram: two peaks of equal height at `00` and `11`,
with nothing in between, is the signature. If you see all four outcomes at 25%, your
CNOT is missing or your control/target are wrong.

The statevector view shows amplitudes $\tfrac{1}{\sqrt2}$ on indices 0 and 3 and zero on
indices 1 and 2.
