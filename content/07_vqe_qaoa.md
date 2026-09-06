# Variational Algorithms: VQE and QAOA

Today's hardware is noisy and shallow. **Variational** algorithms are designed for exactly
that regime: a short parameterized quantum circuit does the hard part, and a classical
optimizer tunes the parameters in a loop.

## The hybrid loop

1. Prepare a parameterized state $|\psi(\vec\theta)\rangle$ with an **ansatz** circuit.
2. Measure an observable to estimate a cost, e.g. the energy
   $E(\vec\theta) = \langle\psi(\vec\theta)|H|\psi(\vec\theta)\rangle$.
3. A classical optimizer proposes better parameters.
4. Repeat until convergence.

The quantum computer only ever runs a short circuit; the optimization loop lives on a
classical machine.

## VQE (Variational Quantum Eigensolver)

VQE estimates the **ground-state energy** of a Hamiltonian - the lowest eigenvalue. Its
main application is chemistry: molecular energies, reaction barriers, materials.

The variational principle guarantees
$$E(\vec\theta) \ge E_{\text{ground}}$$
for every $\vec\theta$, so the optimizer can only ever approach the true answer from
above - a very useful safety property.

A Hamiltonian is decomposed into a weighted sum of Pauli strings,
$H = \sum_i c_i P_i$, and each term is measured separately in an appropriate basis. To
measure in the X basis, apply H before measuring; for the Y basis, apply Sdg then H.

## QAOA (Quantum Approximate Optimization Algorithm)

QAOA targets **combinatorial optimization** problems such as MaxCut. It alternates two
Hamiltonians for $p$ layers:

- a **cost** layer $e^{-i\gamma H_C}$ that encodes the problem (typically RZ and CX gates)
- a **mixer** layer $e^{-i\beta H_M}$ that explores (typically RX on every qubit)

with $2p$ parameters $(\vec\gamma, \vec\beta)$ to optimize. Larger $p$ gives better
solutions but deeper, noisier circuits.

## Ansatz design and barren plateaus

The ansatz must be **expressive** enough to contain a good solution but **shallow** enough
to survive noise. A common hardware-efficient choice is layers of RY/RZ rotations followed
by a ring of CNOTs.

A real difficulty is the **barren plateau**: for deep, randomly initialized circuits the
cost landscape becomes exponentially flat, gradients vanish, and the optimizer gets no
signal. Mitigations include problem-informed ansätze, smart initialization and layer-wise
training.

## Building blocks in the composer

Use **RX**, **RY**, **RZ** with symbolic parameters like `pi/4`, and chain **CX** gates to
entangle. Because the platform requires numeric parameters, you explore the landscape by
running several circuits at different fixed angles and comparing results.
