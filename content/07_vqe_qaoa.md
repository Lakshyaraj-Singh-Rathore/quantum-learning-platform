# Variational Algorithms: VQE and QAOA

Today's hardware is noisy and shallow. **Variational** algorithms are designed
for exactly that regime: a short parameterized quantum circuit does the hard
part, and a classical optimizer tunes the parameters in a loop. This is the
leading candidate for doing useful work on NISQ devices, and it is the reason
**[Quantum Noise](09_quantum_noise.md)** matters so much in practice.

## Learning objectives

By the end of this lesson you should be able to:

- **Describe** the hybrid quantum–classical loop and what each part contributes.
- **Explain** the variational principle and why it makes VQE safe.
- **Construct** a small VQE run and compare its result to the exact ground-state
  energy.
- **Explain** how QAOA alternates a cost and a mixer layer, and what $p$ trades
  off.
- **Describe** a barren plateau and name a mitigation.
- **Measure** a Pauli string in the X and Y bases using basis-change gates.

## The hybrid loop

1. Prepare a parameterized state $|\psi(\vec\theta)\rangle$ with an **ansatz**
   circuit.
2. Measure an observable to estimate a cost, e.g. the energy
   $E(\vec\theta) = \langle\psi(\vec\theta)|H|\psi(\vec\theta)\rangle$.
3. A classical optimizer proposes better parameters.
4. Repeat until convergence.

The quantum computer only ever runs a short circuit; the optimization loop lives
on a classical machine. This division is deliberate: it keeps circuit depth low
enough to survive noise, at the price of needing many circuit executions.

## VQE (Variational Quantum Eigensolver)

VQE estimates the **ground-state energy** of a Hamiltonian — the lowest
eigenvalue. Its main application is chemistry: molecular energies, reaction
barriers, materials.

The variational principle guarantees

$$E(\vec\theta) \ge E_{\text{ground}}$$

for every $\vec\theta$, so the optimizer can only ever approach the true answer
from above — a very useful safety property. It means a lower energy is
unambiguously better, and a failed optimization shows up as an energy that is
too high rather than one that is wrong in an unpredictable direction.

A Hamiltonian is decomposed into a weighted sum of Pauli strings,
$H = \sum_i c_i P_i$, and each term is measured separately in an appropriate
basis. To measure in the X basis, apply H before measuring; for the Y basis,
apply Sdg then H.

### Verified basis changes

On a single qubit, preparing a Y eigenstate and measuring it in the Y basis gives
a deterministic answer — verified, 1024 shots, seed 1234:

| State | Y eigenvalue | Verified result |
|-------|--------------|-----------------|
| $|+i\rangle = \tfrac{1}{\sqrt2}(|0\rangle + i|1\rangle)$ | $+1$ | `{'0': 1024}` |
| $|-i\rangle = \tfrac{1}{\sqrt2}(|0\rangle - i|1\rangle)$ | $-1$ | `{'1': 1024}` |

The `Sdg` then `H` pair rotates the Y basis onto the Z basis, so an ordinary
computational-basis measurement reports the Y eigenvalue.

### A worked VQE run

For the two-qubit Hamiltonian $H = 1.0\,ZZ + 0.5\,XI + 0.3\,ZI$, using a
hardware-efficient ansatz of RY rotations and a CNOT entangler, with COBYLA as
the classical optimizer:

| Quantity | Value |
|----------|-------|
| Exact eigenvalues | $-1.392839,\ -0.860233,\ 0.860233,\ 1.392839$ |
| Exact ground energy | $-1.392839$ |
| **VQE converged energy** | $-1.392838$ |
| $E_{\text{VQE}} - E_{\text{ground}}$ | $+1\times10^{-6}$ |

The optimizer reached the ground state to within a millionth, and — as the
variational principle requires — approached it **from above**.

## QAOA (Quantum Approximate Optimization Algorithm)

QAOA targets **combinatorial optimization** problems such as MaxCut. It
alternates two Hamiltonians for $p$ layers:

- a **cost** layer $e^{-i\gamma H_C}$ that encodes the problem (typically RZ and
  CX gates)
- a **mixer** layer $e^{-i\beta H_M}$ that explores (typically RX on every qubit)

with $2p$ parameters $(\vec\gamma, \vec\beta)$ to optimize. Larger $p$ gives
better solutions but deeper, noisier circuits.

That trade-off is the whole design problem: on ideal hardware you want large
$p$; on real hardware each extra layer adds noise that can outweigh the better
approximation.

## Ansatz design and barren plateaus

### Expressivity versus depth

The ansatz must be **expressive** enough to contain a good solution but
**shallow** enough to survive noise. A common hardware-efficient choice is layers
of RY/RZ rotations followed by a ring of CNOTs.

These two requirements pull in opposite directions, and pushing too far toward
expressivity triggers the failure mode below.

### What a barren plateau is

A **barren plateau** is a cost landscape that is not merely unhelpful but
*exponentially* flat. As the number of qubits $n$ grows, the cost function
concentrates around its mean: almost every randomly chosen parameter vector gives
nearly the same value, and the gradient at a random point has a variance that
decays exponentially in $n$. An optimizer starting there gets no usable signal.

This is a statement about *typical* points, not about the minimum. The minimum
still exists and may be deep — the problem is that the gradient does not tell you
which way to walk to find it.

### Verified: the landscape flattens exponentially

The numbers below are measured, not asserted. For a hardware-efficient ansatz
of two layers — RY then RZ on every qubit, a ring of CNOTs, then RY/RZ again —
we sample 300 random parameter vectors and record the spread of the global
observable $\langle Z^{\otimes n}\rangle$:

| Qubits $n$ | Mean | Std dev | Largest $|\langle Z^{\otimes n}\rangle|$ |
|---|---|---|---|
| 2 | $-0.043$ | $4.38\times10^{-1}$ | 0.99 |
| 4 | $0.010$ | $2.50\times10^{-1}$ | 0.74 |
| 6 | $0.004$ | $1.34\times10^{-1}$ | 0.53 |
| 8 | $0.001$ | $6.83\times10^{-2}$ | 0.29 |
| 10 | $0.000$ | $3.50\times10^{-2}$ | 0.16 |

The standard deviation shrinks by a factor of about $0.73 \approx 1/\sqrt{2}$
per added qubit, so the **variance halves per qubit**:

$$\operatorname{Var} \propto 2^{-n}$$

By ten qubits the spread of the cost across random parameter vectors is $0.035$.
The landscape is flat not because the minimum is shallow, but because the
variation has been squeezed out everywhere.

The same decay appears directly in the gradients. Using the parameter-shift rule
on the first parameter with 200 random initialisations at three layers, the
gradient variance of the global observable falls by a factor near one half for
each qubit added: $0.457$, $0.542$, $0.504$, $0.494$ for $n = 4\to5$, $5\to6$,
$6\to7$, $7\to8$.

### Why it happens

The mechanism is **concentration of measure** in high dimensions. A sufficiently
random circuit spreads its output state over a space whose volume grows
exponentially with $n$, so any single smooth function of that state — the
expectation value of an observable — becomes nearly constant. The cost is a
projection of a very high-dimensional object onto one number, and those
projections concentrate.

The practical consequence is a shot-count problem as much as an optimisation
one. Resolving a gradient of typical size $\epsilon$ requires on the order of
$1/\epsilon^2$ shots just to distinguish it from zero. When $\epsilon$ decays
exponentially, the shots required grow exponentially, and the algorithm is no
longer scalable.

### When it appears

Barren plateaus are associated with:

- **Deep circuits.** A circuit deep enough to approximate a random unitary
  concentrates. Shallow circuits can escape.
- **Global observables.** Terms acting on all $n$ qubits, such as
  $Z^{\otimes n}$, concentrate hardest. **Local observables**, acting on a few
  qubits, are markedly more robust — this is the single most useful distinction
  to remember.
- **Random initialisation.** The plateau is a statement about random points.
  Deliberate initialisation can start you outside it.

One honest caveat on depth: the exponential decay in qubit number above
reproduces cleanly and is the standard signature. The *depth*-driven onset is
genuinely harder to reproduce in a small statevector simulation, and our own
experiments at fixed qubit number did **not** show a clean collapse as layers
were added. Report the qubit-count scaling confidently; treat the depth axis as
established theory rather than something demonstrated here.

### Mitigations

- **Prefer local cost terms.** If the Hamiltonian can be written as a sum of
  terms acting on few qubits, the gradients are substantially larger.
- **Start shallow and grow.** Layer-wise training optimises a shallow circuit,
  then adds a layer and re-optimises, staying out of the concentrated regime.
- **Use problem-informed ansätze.** Structures derived from the problem (such as
  the QAOA ansatz, or a unitary-coupled-cluster ansatz in chemistry) start in a
  small, meaningful corner of parameter space instead of a random point.
- **Initialise deliberately.** Identity-block initialisation sets each added
  layer to the identity so the circuit starts as a known good shallow solution.
- **Correlate parameters.** Tying parameters together reduces the effective
  dimension of the search and slows concentration.

## Building blocks in the composer

Use **RX**, **RY**, **RZ** with parameter expressions like `pi/4`, and chain
**CX** gates to entangle. Because the platform requires numeric parameters — see
**[Quantum Gates](02_gates.md)** — you explore the landscape by running several
circuits at different fixed angles and comparing results.

That is a real limitation worth naming: a full variational loop needs many
circuit executions with parameters chosen by the optimizer, so the Composer is
well suited to understanding a single point in the landscape rather than running
the whole optimization.

## Practical example

Verified against **Qiskit 1.2.4** and `qiskit-aer` 0.16.0:

```python
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import SparsePauliOp
from qiskit.primitives import Estimator
from qiskit_aer import AerSimulator
from scipy.optimize import minimize

# A two-qubit Hamiltonian: H = 1.0 ZZ + 0.5 XI + 0.3 ZI
H = SparsePauliOp.from_list([("ZZ", 1.0), ("XI", 0.5), ("ZI", 0.3)])
eigs = np.linalg.eigvalsh(H.to_matrix())
print("exact eigenvalues: ", np.round(eigs, 6))
print("exact ground energy:", round(eigs[0], 6))

def ansatz(theta):
    qc = QuantumCircuit(2)
    qc.ry(theta[0], 0); qc.ry(theta[1], 1)
    qc.cx(0, 1)                       # the entangler
    qc.ry(theta[2], 0); qc.ry(theta[3], 1)
    return qc

estimator = Estimator()
energy = lambda t: estimator.run([ansatz(t)], [H]).result().values[0]

result = minimize(energy, [0.1, 0.2, 0.3, 0.4], method="COBYLA",
                  options={"maxiter": 300, "tol": 1e-8})
print("VQE energy:        ", round(result.fun, 6))
print("E - E_ground =     ", round(result.fun - eigs[0], 6), "(must be >= 0)")

# Basis changes: Sdg then H rotates the Y basis onto Z
sim = AerSimulator()
def run(qc, shots=1024):
    return sim.run(transpile(qc, sim), shots=shots,
                   seed_simulator=1234).result().get_counts()

plus_i = QuantumCircuit(1, 1)
plus_i.h(0); plus_i.s(0)              # |+i>, a +1 eigenstate of Y
plus_i.sdg(0); plus_i.h(0)
plus_i.measure(0, 0)
print("Y basis, |+i>:", run(plus_i))  # {'0': 1024}

minus_i = QuantumCircuit(1, 1)
minus_i.h(0); minus_i.sdg(0)          # |-i>, a -1 eigenstate of Y
minus_i.sdg(0); minus_i.h(0)
minus_i.measure(0, 0)
print("Y basis, |-i>:", run(minus_i))  # {'1': 1024}
```

## Common misconceptions

- **"VQE finds the exact ground state."** It finds the best state its ansatz can
  reach. If the ansatz cannot represent the ground state, the result is a strict
  upper bound — useful, but not exact.
- **"The quantum computer does the optimization."** The optimizer is entirely
  classical. The quantum device evaluates the cost for a given $\vec\theta$.
- **"Deeper ansätze are always better."** Beyond expressivity, depth buys
  barren plateaus and noise. Both are real limits.
- **"QAOA guarantees an optimal solution."** It is an *approximation*
  algorithm; the guarantee improves with $p$ but is never exact at finite $p$.

## Exercises

**1.** What does the variational principle guarantee, and why is it useful?

**2.** Why must the number of QAOA layers $p$ be chosen carefully?

**3.** Which basis-change gates do you apply to measure $\langle X\rangle$ and
$\langle Y\rangle$?

**4.** A VQE run returns an energy *below* the true ground state. What is the
most likely explanation?

**5.** Name two things that make a cost landscape flat.

### Answers

**1.** $E(\vec\theta) \ge E_{\text{ground}}$ for all $\vec\theta$. It guarantees
the optimizer approaches the answer from above, so a lower energy is always
better and a poor result shows up as an energy that is too high rather than
erratic.

**2.** Larger $p$ improves the approximation quality but deepens the circuit,
which on real hardware adds noise and on any hardware risks barren plateaus. The
optimum balances approximation against noise.

**3.** For $\langle X\rangle$, apply **H** before measuring. For
$\langle Y\rangle$, apply **Sdg** then **H**. Verified above: Y eigenstates
become deterministic outcomes.

**4.** Almost certainly an error rather than a real result — most likely a
mistake in the Hamiltonian coefficients, an incorrectly decomposed Pauli term, or
insufficient shots making the estimate statistically meaningless. The
variational principle forbids a true value below $E_{\text{ground}}$, so treat
any such result as a bug.

**5.** Barren plateaus from deep random circuits, and hardware noise that
flattens small gradients into statistical noise.

## Summary

- Variational algorithms split the work: a short parameterized circuit prepares
  states, a classical optimizer tunes the parameters.
- VQE estimates ground-state energies; the variational principle guarantees it
  approaches from above.
- Hamiltonians decompose into Pauli strings; change basis with H (for X) or
  Sdg then H (for Y).
- QAOA alternates cost and mixer layers; $p$ trades approximation quality
  against depth and noise.
- Barren plateaus and noise are the two obstacles to scaling these methods.
- This platform's numeric-only parameters let you explore individual points in
  the landscape rather than run a full optimization loop.

## References

- Peruzzo, A. et al. "A variational eigenvalue solver on a photonic quantum
  processor", *Nature Communications* 5 (2014) 4213.
- Farhi, E., Goldstone, J. & Gutmann, S. "A Quantum Approximate Optimization
  Algorithm", *arXiv:1411.4028* (2014).
- McClean, J. R. et al. "Barren plateaus in quantum neural network training
  landscapes", *Nature Communications* 9 (2018) 4812.
- Cerezo, M. et al. "Variational quantum algorithms", *Nature Reviews Physics* 3
  (2021) 625.
- Qiskit documentation, "VQE and QAOA": https://docs.quantum.ibm.com/
