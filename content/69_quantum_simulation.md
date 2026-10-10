# Quantum Simulation and Many-Body Systems

Feynman's original argument for a quantum computer was not about factoring. It
was this: nature is quantum, so simulating nature on a classical computer is
hopelessly expensive, while a quantum computer does it naturally. That remains
the strongest motivation for the whole field.

This lesson covers how a physical Hamiltonian becomes a qubit Hamiltonian, why
the classical version scales exponentially, and — the part most often skipped —
what you can actually *extract* from a simulation once you have run it.

## Learning objectives

By the end of this lesson you should be able to:

- **Map** a Hamiltonian onto a qubit Hamiltonian.
- **Explain** why classical simulation scales exponentially.
- **State** what observables are accessible from a simulation.

## Prerequisites

[Quantum Phase Estimation](../algo/phase_estimation.md) (recommended) — energy
estimation is the original simulation application.

[VQE](../nisq/vqe.md) (recommended) — VQE is the NISQ-era alternative for the
same task.

## The task

Given a Hamiltonian $H$ describing a physical system and an initial state
$\lvert\psi(0)\rangle$, find properties of

$$\lvert\psi(t)\rangle = e^{-iHt}\lvert\psi(0)\rangle \qquad \text{or}\qquad \lvert E_0\rangle,$$

the time-evolved state or the ground state. The applications are concrete:
reaction rates in catalysis, superconductivity, nuclear physics, materials
design, and [quantum chemistry](../adv/quantum_chemistry.md).

## Mapping a Hamiltonian onto a qubit Hamiltonian

Objective 1.

### The recipe

Everything reduces to one standard form. A qubit Hamiltonian is a **weighted
sum of Pauli strings**:

$$H = \sum_k c_k P_k, \qquad P_k \in \{I, X, Y, Z\}^{\otimes n}.$$

The mapping problem is: given a physical Hamiltonian, express it in that form.
Three steps:

1. **Choose a basis.** What does $\lvert 0\rangle$ and $\lvert 1\rangle$ mean
   physically? For a spin, up and down. For a fermionic mode, empty and
   occupied.
2. **Rewrite the operators.** Express each physical operator (creation and
   annihilation operators, spin operators) as a combination of Paulis.
3. **Read off the Pauli strings.** Collect terms.

The reason this form matters is that a Pauli string is directly measurable and
directly simulable — every term exponentiates to a simple circuit. That is what
[Trotterization](70_trotterization.md) exploits.

### Example 1: the transverse-field Ising model

The TFIM is the workhorse model of quantum magnetism:

$$H = -J\sum_{i=0}^{n-2} Z_i Z_{i+1} \;-\; h\sum_{i=0}^{n-1} X_i$$

Here the mapping is immediate, because spins *are* two-level systems:
$\lvert 0\rangle$ is spin-up, $\lvert 1\rangle$ is spin-down, and the spin
operators are already Pauli operators. The interaction $Z_iZ_{i+1}$ is the
coupling, and the transverse field $h$ enters as $X_i$.

For $n = 4$ the Hamiltonian is

$$H = -J(Z_0Z_1 + Z_1Z_2 + Z_2Z_3) - h(X_0 + X_1 + X_2 + X_3),$$

which is $2n - 1 = 7$ Pauli terms. **The number of terms grows only
polynomially** in $n$.

Note the tension that drives the whole subject: 7 terms, polynomial — but a
$16 \times 16$ matrix. The *description* is cheap; the *state space* is not.

### Example 2: fermions and Jordan–Wigner

Electrons are the interesting case, and here the mapping is not free. Fermionic
operators obey the anticommutation relations

$$\{c_i, c_j^\dagger\} = \delta_{ij}, \qquad \{c_i, c_j\} = \{c_i^\dagger, c_j^\dagger\} = 0 .$$

Pauli operators on different qubits **commute**, so they cannot represent
fermions directly. The **Jordan–Wigner transformation** fixes this by attaching
a "string" of $Z$ operators:

$$c_j = \Big(\prod_{k < j} Z_k\Big)\,\sigma_j^-, \qquad c_j^\dagger = \Big(\prod_{k < j} Z_k\Big)\,\sigma_j^+,$$

where $\sigma^\pm = \tfrac{1}{2}(X \pm iY)$.

**Verified:** with this definition, $\{c_i, c_j^\dagger\} = \delta_{ij}$ and
$\{c_i, c_j\} = \{c_i^\dagger, c_j^\dagger\} = 0$ hold exactly for all $i, j$ at
$n = 3$. As an independent check, the two-site Hubbard dimer

$$H = -t(c_0^\dagger c_1 + c_1^\dagger c_0) + U\, n_0 n_1$$

at $t = 1$, $U = 2$ gives spectrum $[-1, 0, 1, 2]$ whether built via Jordan–Wigner
Pauli strings or constructed independently in Fock space. The two agree.

### The price: operator weight

Jordan–Wigner works, but it costs locality. Because of the $Z$-string,
$c_j^\dagger$ touches **every qubit with index below $j$**:

| Operator | Qubits touched | Weight |
|---|---|---|
| $c_0^\dagger$ | 0 | 1 |
| $c_1^\dagger$ | 0, 1 | 2 |
| $c_2^\dagger$ | 0, 1, 2 | 3 |
| $c_3^\dagger$ | 0, 1, 2, 3 | 4 |

So a **two-body** fermionic term can map to a qubit operator of weight
$O(n)$ — a single physical interaction becomes a long chain of gates. This is
the Jordan–Wigner overhead, and it is why alternatives such as the
**Bravyi–Kitaev transformation** exist: they reduce the weight to $O(\log n)$ at
the cost of a more complicated mapping.

Choosing a mapping is therefore a real engineering decision, not a formality.

## Why classical simulation scales exponentially

Objective 2.

### The Hilbert space is exponential

$n$ qubits live in a space of dimension $2^n$. Every additional qubit **doubles**
the dimension. This is not a limitation of classical algorithms or engineering;
it is the structure of the problem.

The state vector has $2^n$ complex amplitudes. At 16 bytes per
complex128 amplitude:

| Qubits | Amplitudes | State-vector memory |
|---|---|---|
| 10 | $1.0 \times 10^{3}$ | 16.4 KB |
| 20 | $1.0 \times 10^{6}$ | 16.8 MB |
| 30 | $1.1 \times 10^{9}$ | 17.2 GB |
| 40 | $1.1 \times 10^{12}$ | 17.6 TB |
| 50 | $1.1 \times 10^{15}$ | 18.0 PB |
| 100 | $1.3 \times 10^{30}$ | $2.0 \times 10^{19}$ TB |

At $n = 50$, storing **one** state vector requires 16 petabytes. There is no
clever data structure that fixes this in general — the exponential is in the
physics, not the representation.

### Measured: exact diagonalisation

Finding the ground state by exact diagonalisation costs $O(D^3)$ for a $D \times D$ matrix, so with $D = 2^n$ the cost grows as $8\times$ per added qubit.
Measured wall-clock times for the transverse-field Ising model:

| $n$ | Dimension | Time | Ratio to previous |
|---|---|---|---|
| 2 | 4 | 0.00049 s | — |
| 4 | 16 | 0.00078 s | 1.31× |
| 6 | 64 | 0.00305 s | 2.54× |
| 8 | 256 | 0.04618 s | 6.51× |
| 10 | 1024 | 0.71363 s | 3.19× |
| 11 | 2048 | 2.96853 s | 4.16× |
| 12 | 4096 | **21.04 s** | **7.09×** |

The ratio converges toward the predicted $8\times$ per qubit once the matrices
are large enough for the asymptotics to dominate.

Extrapolating to **100 qubits**: the state vector alone needs
$2^{100} \times 16$ bytes $\approx 2.0 \times 10^{31}$ bytes, or
$2.0 \times 10^{19}$ TB — and the diagonalisation cost grows by a factor of
$2^{3(100-12)} = 2^{264} \approx 3.0 \times 10^{79}$ relative to the 21 seconds
measured at $n = 12$. Both numbers are absurd, which is the point.

This is why 50–100 qubits is the accepted boundary where exact classical
simulation stops, and why [random-circuit sampling](62_nisq_limitations.md)
experiments target that regime.

### What classical methods can still do

It would be dishonest to stop here. Classical physics has powerful approximate
methods that work well in important regimes:

- **Density functional theory** — the workhorse of materials science, scaling
  polynomially, but with uncontrolled approximation error.
- **Quantum Monte Carlo** — excellent, but suffers the **sign problem** for
  fermions and frustrated systems, where the cost becomes exponential.
- **Tensor networks / DMRG** — extremely accurate for 1D and lightly entangled
  systems, because they compress the state efficiently when entanglement is
  limited (area-law states).
- **Coupled cluster** — the standard in quantum chemistry, though it fails for
  strongly correlated systems.

The honest statement is therefore narrower than "classical can't do this":
**classical methods fail precisely for strongly correlated, highly entangled,
fermionic or dynamically evolving systems** — which includes much of the
interesting physics: high-temperature superconductors, catalysts with
transition metals, and real-time dynamics. Those are the targets.

## What observables are accessible

Objective 3, and the most practically important part.

### The good news: local observables are cheap

Suppose the simulation has prepared the ground state $\lvert E_0\rangle$. You do
**not** need to know the state to extract physics from it. You need expectation
values, and the Hamiltonian's Pauli decomposition tells you exactly which ones:

$$\langle H \rangle = \sum_k c_k \langle P_k \rangle .$$

Each $\langle P_k\rangle$ is measured by preparing the state, rotating into the
basis of $P_k$, and sampling. For the TFIM, each term involves only one or two
qubits.

**Verified.** For the 4-qubit TFIM at $J = 1$, $h = 0.5$:

- Ground energy by exact diagonalisation: $-3.4270340889$
- Energy reconstructed from the $(2n-1) = 7$ Pauli expectation values:
  $-3.4270340889$
- **Difference: $6.7 \times 10^{-15}$** — agreement to machine precision.

This is the key practical fact. **The energy is accessible from polynomially
many measurements, each involving only a few qubits.** You never learn the
state; you learn the number you wanted.

### What you can get

- **Energy** $\langle H\rangle$, and from it ground-state energies, reaction
  energies and binding energies.
- **Local order parameters** — $\langle Z_i\rangle$, magnetisation, occupancy.
- **Correlation functions** — $\langle Z_i Z_j\rangle$ as a function of
  separation, which reveal phase transitions and ordering.
- **Structure factors** — Fourier transforms of correlation functions, which are
  what scattering experiments actually measure.
- **Response properties** — via derivatives of the energy with respect to a
  perturbation.
- **Expectation of any Pauli string** $\langle\psi\lvert P\lvert\psi\rangle$.

### What you cannot get

This is where expectations most often go wrong.

- **The full state vector.** Reading out all $2^n$ amplitudes requires full
  state tomography, costing $O(4^n)$ measurements. The state is prepared in
  polynomial time but cannot be *read out* in polynomial time. This is a
  fundamental feature of quantum mechanics, not a technical gap.
- **Arbitrary off-diagonal quantities.** $\langle\psi\lvert A\lvert\phi\rangle$
  for two different states $\lvert\psi\rangle$ and $\lvert\phi\rangle$ is not
  directly measurable; it requires indirect techniques such as the
  Hadamard test or [phase estimation](../algo/phase_estimation.md).
- **Non-linear functionals of the state.** Quantities like entanglement entropy
  are **not** expectation values of any operator. They require multiple
  preparations, tomography, or randomised measurement protocols, and they cost
  far more than a simple $\langle P_k\rangle$.

The practical consequence: **decide what you want to measure before you design
the simulation.** A quantum simulation is not a substitute for a classical
one that hands you a wavefunction you can interrogate freely. It answers a
specific list of questions efficiently, and you must choose that list in
advance.

## Common misconceptions

- **"A quantum simulation outputs the wavefunction."** It does not. It gives
  measurement samples. Learning the full state costs $O(4^n)$ — exponentially
  more than preparing it.
- **"Classical computers simply cannot simulate quantum systems."** Overbroad.
  DFT, QMC, DMRG and coupled cluster handle large and important classes. The
  genuine classical failure is **strongly correlated, highly entangled,
  fermionic, or real-time** physics.
- **"More qubits automatically means better chemistry."** Qubit count is
  useless without the [gate fidelity and depth](62_nisq_limitations.md) to
  prepare the state. A noisy 100-qubit simulation of a molecule can be worse
  than a clean 20-qubit one.
- **"Any observable can be measured afterwards."** Observables that are not
  expectation values of Pauli strings — entanglement entropy is the classic
  example — need special protocols and cost far more.
- **"Fermions map to qubits for free."** Jordan–Wigner turns a two-body term
  into an $O(n)$-weight operator. The mapping choice matters.
- **"Quantum advantage in simulation is already achieved for useful
  problems."** Not demonstrated. Current devices are small and noisy; the
  classical algorithms they would have to beat are sophisticated and improving.

## Exercises

1. Write the transverse-field Ising Hamiltonian for $n = 5$ as an explicit sum
   of Pauli strings. How many terms?

2. How much memory does a state vector need for 45 qubits, at 16 bytes per
   amplitude? Give your answer in convenient units.

3. Explain why $n$ qubits require $2^n$ amplitudes, and why this is not
   something a better classical algorithm can avoid.

4. A Hamiltonian decomposes as $H = 2 Z_0 Z_1 - 3 X_0 + X_1$. Given
   $\langle Z_0Z_1\rangle = 0.5$, $\langle X_0\rangle = -0.2$ and
   $\langle X_1\rangle = 0.4$, compute $\langle H\rangle$.

5. Why is entanglement entropy harder to measure than energy?

6. Give one regime where a classical method is still the better choice, and
   say why.

### Answers to 1–3

**1.**

$$H = -J(Z_0Z_1 + Z_1Z_2 + Z_2Z_3 + Z_3Z_4) - h(X_0 + X_1 + X_2 + X_3 + X_4)$$

That is $4$ interaction terms plus $5$ field terms $= 9 = 2n - 1$ terms.

**2.** $2^{45} \times 16$ bytes $= 2^{45} \times 2^4 = 2^{49}$ bytes
$\approx 5.6 \times 10^{14}$ bytes $\approx$ **560 TB**. (Note this is for one
state vector; diagonalising the $2^{45} \times 2^{45}$ Hamiltonian is far
beyond reach.)

**3.** A general $n$-qubit state is
$\sum_{x \in \{0,1\}^n} \alpha_x \lvert x\rangle$ — one complex amplitude for
each of the $2^n$ basis strings, and they are independent. This is intrinsic to
the tensor-product structure of composite quantum systems, not an artefact of a
particular representation. A "better algorithm" cannot avoid it in general; what
classical methods do instead is **approximate** — tensor networks, for example,
work only when entanglement is limited so the state can be compressed.

### Answers to 4–6

**4.**

$$\langle H\rangle = 2(0.5) - 3(-0.2) + 1(0.4) = 1.0 + 0.6 + 0.4 = 2.0 .$$

Three expectation values, each measured on at most two qubits, give the energy.
No knowledge of the state is needed.

**5.** Energy is $\langle H\rangle$ — the expectation value of an operator you
can decompose into Pauli strings and measure term by term. Entanglement entropy
is $-\operatorname{Tr}(\rho_A \log \rho_A)$, a **non-linear functional of the
reduced density matrix**, not the expectation value of any observable. You
cannot measure it by preparing and sampling in one basis; you must either
reconstruct $\rho_A$ by tomography (exponentially expensive) or use specialised
protocols such as randomised measurements, which need many more preparations
than a simple energy estimate.

**6.** Any one of: **DFT** for weakly correlated materials, where it scales
polynomially and is accurate enough that a quantum computer would not beat it in
practice; **DMRG** for one-dimensional and area-law entangled systems, where the
entanglement is limited and the state compresses efficiently; **QMC** for
bosonic or unfrustrated systems without a sign problem. In each case the
classical method wins on speed, cost, or reliability, and reaching for a quantum
computer would be a mistake.

## Summary

- **The mapping** puts any Hamiltonian into Pauli-string form
  $H = \sum_k c_k P_k$, which is what makes it simulable and measurable.
- **Transverse-field Ising** maps directly: $H = -J\sum Z_iZ_{i+1} - h\sum X_i$,
  giving $2n-1$ terms — polynomial description, exponential state space.
- **Fermions need Jordan–Wigner**,
  $c_j = (\prod_{k<j} Z_k)\sigma_j^-$, verified to satisfy the fermionic
  anticommutation relations exactly and to reproduce the two-site Hubbard
  spectrum $[-1,0,1,2]$ obtained independently in Fock space. The price is
  **operator weight $O(n)$**, which motivates Bravyi–Kitaev's $O(\log n)$.
- **Classical cost is exponential** because the space is: $2^n$ amplitudes,
  16 GB at $n=30$ and 16 PB at $n=50$. Measured diagonalisation time rises
  toward $8\times$ per qubit, reaching 21 s at $n=12$.
- **Be honest about classical methods**: DFT, QMC, DMRG and coupled cluster work
  well in large regimes. The classical failure is specifically **strongly
  correlated, highly entangled, fermionic, real-time** physics.
- **Accessible observables**: energy, local order parameters, correlation
  functions, structure factors, any Pauli expectation. Verified — the 4-qubit
  TFIM ground energy is recovered from 7 Pauli expectations to within
  $7 \times 10^{-15}$.
- **Inaccessible**: the full $2^n$ state vector (tomography costs $O(4^n)$),
  off-diagonal $\langle\psi\lvert A\lvert\phi\rangle$, and non-linear
  functionals such as entropy. **Choose what to measure before simulating.**

## References

- Feynman, R. P., "Simulating physics with computers," *International Journal of
  Theoretical Physics* **21**, 467 (1982) — the original argument.
- Lloyd, S., "Universal Quantum Simulators," *Science* **273**, 1073 (1996) —
  the algorithmic foundation.
- Jordan, P. and Wigner, E., "Über das Paulische Äquivalenzverbot,"
  *Zeitschrift für Physik* **47**, 631 (1928) — the fermion-to-qubit mapping.
- Bravyi, S. and Kitaev, A., "Fermionic Quantum Computation," *Annals of
  Physics* **298**, 210 (2002) — the $O(\log n)$-weight alternative.
- Nielsen, M. A. and Chuang, I. L., *Quantum Computation and Quantum
  Information*, §4.7 — quantum simulation.
- [Trotterization](70_trotterization.md) — how $e^{-iHt}$ becomes gates, and
  the error bound.
- [Quantum Phase Estimation](../algo/phase_estimation.md) — the
  fault-tolerant route to energies.
- [VQE](../nisq/vqe.md) — the NISQ route to the same quantity.
- [NISQ Limitations](62_nisq_limitations.md) — the fidelity and depth budget
  that bounds real simulations.
- [BQP, P, NP and BPP](63_complexity_classes.md) — where simulation sits
  complexity-theoretically.

---

**Next:** [Trotterization](70_trotterization.md)
