# Neutral Atoms

Neutral atoms held in optical tweezers have become the platform that scales most
easily: arrays of thousands of atoms have been demonstrated, and the largest
logical-qubit experiments on any platform have been run on them. The qubit is a
single atom in its electronic ground state, the entangling mechanism is the
**Rydberg blockade**, and the geometry is reconfigurable — atoms can be moved
while the computation runs.

## Learning objectives

By the end of this lesson you should be able to:

- **Describe** how neutral atoms encode qubits.
- **Explain** the Rydberg blockade mechanism for entangling gates.
- **State** the scaling advantage of atom arrays.

## Prerequisites

[Quantum Noise and Decoherence](../qiskit/quantum_noise.md) (recommended). Same
per-platform metrics.

## The physical system

Individual neutral atoms — usually alkali atoms such as $^{87}$Rb, or alkaline
earth atoms such as $^{88}$Sr or $^{171}$Yb — are held in **optical tweezers**:
tightly focused laser beams whose intensity gradient creates a potential well
that traps a single atom. A spatial light modulator or acousto-optic deflector
splits one laser into hundreds or thousands of independent traps.

Assembling the array takes two steps. Atoms are loaded from a magneto-optical
trap into tweezers at random, with roughly 50% occupancy per site; then a
**rearrangement** procedure moves the occupied tweezers into a defect-free
target pattern. This is what makes large defect-free arrays possible despite
probabilistic loading.

The atoms are neutral, so unlike [trapped ions](57_trapped_ions.md) they do not
repel each other and can be packed closely. But they also do not interact at
all — which is the problem the Rydberg blockade solves.

## How neutral atoms encode qubits

The qubit is a pair of long-lived internal states of the atom's **electronic
ground state**. Two encodings are common:

| Encoding | States used | Splitting | Coherence |
|---|---|---|---|
| **Hyperfine** | Two hyperfine ground levels, e.g. $^{87}$Rb $5S_{1/2}$ $|F=1, m_F=0\rangle \leftrightarrow |F=2, m_F=0\rangle$ | $\sim 6.8$ GHz (microwave) | Seconds |
| **Nuclear spin** | Nuclear spin sublevels, often in alkaline-earth atoms | MHz | Very long — the nucleus is well screened |

Both are ground states, so there is no spontaneous decay and no excited-state
lifetime limit. **Idle atoms are exceptionally good qubits**: they do not
interact with one another, they sit in a stable internal state, and reported
coherence times in large arrays exceed a second, with some measurements above
ten seconds.

That last point deserves emphasis. On this platform, doing nothing is nearly
free. Errors happen when you drive the atoms, not while they wait.

**Single-qubit gates** are driven by microwave pulses or two-photon Raman
transitions, with reported fidelities above $99.9\%$. A global microwave field
can address every atom in the array at once, which makes global single-qubit
rotations essentially free.

**Measurement** is fluorescence imaging: illuminate the atoms and collect the
scattered light. Atoms in one qubit state scatter brightly, atoms in the other
do not. Reported detection fidelities exceed $99\%$.

## The Rydberg blockade

Ground-state atoms barely interact. Excited atoms interact enormously.

A **Rydberg state** is a highly excited electronic state with a large principal
quantum number $n$ — typically $n = 50$ to $100$. The electron orbits far from
the nucleus, and the atom becomes, by atomic standards, enormous. Its electric
dipole moment is huge, and two such atoms interact through a van der Waals
interaction

$$V(r) = \frac{C_6}{r^6}$$

with $C_6 \propto n^{11}$. The interaction grows extraordinarily fast with $n$
and falls off extraordinarily fast with distance.

The consequence is the **blockade**. Suppose a laser is tuned to drive
$|1\rangle \to |r\rangle$ on two nearby atoms. For the second atom to be
excited while the first is already in $|r\rangle$, the doubly-excited state
$|rr\rangle$ must be reached — but that state is shifted in energy by $V(r)$. If
$V \gg \hbar\Omega$, where $\Omega$ is the drive Rabi frequency, the laser is
off resonance for the second excitation and it simply does not happen.

**One atom in $|r\rangle$ blocks all its neighbours.** That is a conditional
operation, and a conditional operation is a gate.

### The blockade radius

The distance at which the blockade becomes effective — conventionally where the
interaction shift equals the drive strength — is

$$r_b = \left(\frac{C_6}{\hbar\Omega}\right)^{1/6}$$

The sixth root makes this number remarkably insensitive to parameters:

| $C_6/\hbar\Omega$ (μm⁶) | $r_b$ (μm) |
|---|---|
| 1 | 1.00 |
| 10 | 1.47 |
| 100 | 2.15 |
| 1000 | 3.16 |
| $10^4$ | 4.64 |
| $10^6$ | 10.00 |
| $10^8$ | 21.54 |

A factor of 64 in $C_6/\hbar\Omega$ changes the blockade radius by only a factor
of 2, and a factor of $10^6$ changes it by 10. The radius is set mostly by the
exponent 6, not by the details of the Rydberg state.

The flip side is the sharpness of the falloff. With a representative
$C_6/h = 100$ MHz·μm⁶:

| $r$ (μm) | $V/h$ (MHz) | $V/h$ relative to $\Omega/2\pi = 5$ MHz |
|---|---|---|
| 1.0 | 100.0 | 20.00 |
| 2.0 | 1.5625 | 0.31 |
| 3.0 | 0.1372 | 0.03 |
| 5.0 | 0.0064 | 0.001 |
| 10.0 | 0.0001 | $2\times10^{-5}$ |

At $r = 10$ μm the interaction is a million times weaker than at $r = 1$ μm.
This is why atom arrays use micron-scale spacing, and why the connectivity is
**local within a blockade radius** rather than global.

### Verified: the blockade gate

The standard protocol (Jaksch et al.) is a three-pulse sequence on two atoms:
a $\pi$ pulse on the control, a $2\pi$ pulse on the target, and a $\pi$ pulse to
return the control. If the control is in $|1\rangle$ it is promoted to
$|r\rangle$, and the target's $2\pi$ pulse is then blockaded — the target
acquires no phase. If the control is in $|0\rangle$ the target completes its
full $2\pi$ cycle and picks up a minus sign.

Simulating that sequence with the Hamiltonian

$$H = \frac{\Omega}{2}\left(|r\rangle\langle 1| + |1\rangle\langle r|\right) + V\,|rr\rangle\langle rr|$$

and scoring the result against a controlled-Z **up to local $z$-rotations**
gives:

| $V/\Omega$ | $F$ (vs CZ) | $|\phi_{\text{cond}}|$ | Phase error | Off-diagonal | $|u_{11}|$ |
|---|---|---|---|---|---|
| 0 | 0.500000 | 0.000000 | 3.141593 | $0$ | 1.0000 |
| 1 | 0.795933 | 1.943211 | 1.198382 | $0$ | 0.7317 |
| 2 | 0.948303 | 2.455153 | 0.686440 | $0$ | 0.9533 |
| 5 | 0.993276 | 2.836183 | 0.305410 | $0$ | 0.9982 |
| 10 | 0.998421 | 2.985669 | 0.155924 | $0$ | 0.9999 |
| 20 | 0.999527 | 3.063199 | 0.078393 | $0$ | 1.0000 |
| 100 | 0.999954 | 3.125886 | 0.015707 | $0$ | 1.0000 |

### Reading the table

Three things are worth reading out of that table.

**The conditional phase is what makes the gate.** At $V = 0$ the fidelity is
$0.5$ and $\phi_{\text{cond}} = 0$: the sequence is a perfectly good *local*
gate and entangles nothing. As $V/\Omega$ grows, $\phi_{\text{cond}} \to \pi$,
which is exactly the CZ condition. Both columns are needed — fidelity alone
would call the $V=0$ local gate perfect, and the phase alone would hide leakage.

**The phase error falls off cleanly as $1/V$.** The fourth column is
approximately $(\pi/2)\,\Omega/V$: at $V/\Omega = 10$ the error is $0.156 = \pi/20$; at $V/\Omega = 100$ it is $0.0157 = \pi/200$. Halving the error costs a
doubling of the interaction strength. This is the quantitative form of the
statement "the blockade must be strong".

**The gate stays diagonal.** The off-diagonal elements of the computational
subspace are zero at every $V$: the basis states never mix. The failure mode at
intermediate $V$ is not mixing but **leakage** — seen in the dip of $|u_{11}|$
to $0.73$ at $V/\Omega = 1$, where the blockaded pulse is only partly blockaded
and leaves amplitude stranded in $|r\rangle$.

### Beyond two qubits

Because the blockade suppresses *all* excitation within the radius, it naturally
implements multi-qubit gates. A single Rydberg pulse applied to a group of atoms
excites at most one of them, which is the content of a multi-qubit controlled
gate. Three-qubit CCZ fidelities around $98\%$ have been reported, and such
native multi-qubit gates shorten circuits that would otherwise need long
two-qubit decompositions.

## Why atom arrays scale

This is the platform's distinctive advantage, and it is worth stating precisely.

**Qubits are cheap and identical.** Every $^{87}$Rb atom is the same as every
other. There is no fabrication step per qubit, so no fabrication variance and no
per-device calibration.

**The footprint is tiny.** With atoms spaced roughly 4 μm apart, a $100\times100$
array of 10,000 qubits spans about 400 μm. Thousands of qubits fit on one
optical table. Compare a superconducting chip, where each qubit and its control
wiring occupy macroscopic area.

**Adding traps is an optical problem, not a fabrication problem.** More qubits
means more tweezer beams, generated by the same modulator that already makes
them.

**The geometry is reconfigurable.** Atoms can be moved during the computation by
steering their tweezers. Two qubits that need to interact but are far apart can
be brought together, gated, and moved back. This gives connectivity that is
better than fixed nearest-neighbour wiring without being all-to-all, and it is
unique among the platforms covered here.

Idle atoms are also nearly free of error, since they sit in the ground state and
do not interact.

Demonstrated scale is the largest of any platform: a 6,100-atom array was
reported in 2025, and a 3,000-qubit array was run continuously for more than two
hours using **mid-computation replenishment** — replacing atoms as they are
lost, rather than stopping to reload.

## Limitations

- **Two-qubit fidelity lags.** Reported values around $99.5\%$ are below
  [trapped ions](57_trapped_ions.md) and below what the platform needs for
  comfortable fault-tolerant overhead.
- **Atom loss is a real and distinctive failure mode.** Atoms escape their traps
  during Rydberg excitation through anti-trapping and photoionization. The good
  news is that loss is **heralded** — a missing atom is visible on the next
  image — so it is an erasure rather than an unknown error, which is much easier
  to correct. The bad news is that it requires the machinery to replenish atoms
  continuously.
- **Gates are microseconds, not nanoseconds.** Rydberg gates run at roughly
  $0.5$ μs, far slower than superconducting gates but comparable to or faster
  than trapped ions.
- **Connectivity is local, not global.** The blockade radius is a few microns.
  Reconfigurability mitigates this but does not eliminate it.
- **Rydberg states are fragile.** Spontaneous emission and blackbody-induced
  transitions out of $|r\rangle$ limit how long an atom can sit excited, which
  caps gate time.
- **Control hardware scales with qubit count.** Thousands of individually
  addressed tweezers and addressing beams need beam steering, modulation, and
  calibration.

## Device parameters

Vendor- and group-reported figures for specific systems, not platform
constants.

| System | Reported figures |
|---|---|
| Harvard / QuEra (2023) | Two-qubit CZ fidelity $99.5\%$ across 60 parallel gates; gate duration $\sim 0.5$ μs |
| Single-qubit | $>99.9\%$ (reported up to $99.97\%$) via Raman or microwave, $\sim 100$ ns |
| Multi-qubit | Three-qubit CCZ $\sim 98\%$, $\sim 1$ μs |
| Caltech (2025) | 6,100-atom array |
| Harvard / MIT (2025) | 3,000-qubit array, continuous operation $>2$ hours with atom replenishment |
| QuEra (Nature, Jan 2026) | 96 logical qubits from 448 physical qubits using a $[[16,6,4]]$ code, a $4.7{:}1$ ratio |
| Pasqal | 140-qubit system deployed; 200+ planned |

The QuEra logical-qubit result is worth singling out: it used a **high-rate**
code rather than a surface code, achieving $4.7$ physical qubits per logical
qubit. That is worse than the $2{:}1$ reported for
[trapped ions](57_trapped_ions.md) but far better than the roughly $1000{:}1$
that a surface code needs at comparable physical error rates — and it is the
second-best encoding efficiency among multi-logical-qubit demonstrations.

## Common misconceptions

- **"Neutral atoms don't interact, so they can't be gated."** Ground-state atoms
  do not interact. Rydberg-excited atoms interact very strongly, and that is
  what supplies the gate.
- **"The blockade is all-or-nothing."** The verified table shows a continuum. At
  $V/\Omega = 1$ the gate is poor but not absent — partly blockaded, with
  amplitude stranded in $|r\rangle$ — and the phase error decreases only as
  $1/V$.
- **"A high gate fidelity means the gate is entangling."** At $V = 0$ the
  sequence is a perfect local gate. Conditional phase is the thing to check.
- **"Atom loss is catastrophic."** Detected loss is an erasure, which is among
  the easiest errors to correct. Undetected loss would be catastrophic; detected
  loss is manageable, and continuous replenishment has been demonstrated.
- **"Reconfigurable geometry means all-to-all connectivity."** Moving atoms takes
  time and introduces error. It buys flexible connectivity, not free
  connectivity.
- **"More atoms is automatically better."** The point of the 2026 logical-qubit
  result is that error rates fell as the system grew. That is a property of a
  working error-corrected architecture, not of atom count alone.

## Exercises

1. Explain in one or two sentences why a Rydberg-excited atom blocks its
   neighbours from being excited.

2. Using $r_b = (C_6/\hbar\Omega)^{1/6}$, by what factor does the blockade
   radius change if the Rabi frequency $\Omega$ is increased by a factor of 64?

3. From the verified table, estimate the phase error at $V/\Omega = 200$ using
   the $(\pi/2)\,\Omega/V$ scaling, and state what that implies about the
   fidelity.

4. Why is atom loss on this platform easier to handle than an equivalent rate
   of unknown gate error?

5. Name two reasons atom arrays scale more easily than superconducting chips.

6. A blockade interaction has $C_6/h = 100$ MHz·μm⁶ and the drive is
   $\Omega/2\pi = 5$ MHz. Compute the blockade radius, and the interaction
   strength at twice that radius.

### Answers to 1–3

**1.** Exciting a second atom while the first is already in $|r\rangle$ requires
reaching the doubly-excited state $|rr\rangle$, which is shifted in energy by
$V = C_6/r^6$. When $V \gg \hbar\Omega$ the drive is off resonance for that
transition, so the second excitation does not occur.

**2.** Since $r_b \propto \Omega^{-1/6}$, increasing $\Omega$ by 64 changes the
radius by $64^{-1/6} = (2^6)^{-1/6} = 2^{-1} = 1/2$. The blockade radius
**halves** — which is the reason faster gates shrink the interaction range.

**3.** $(\pi/2)\,\Omega/V = 1.571/200 = 0.00785$ rad. From the table, a phase
error of $0.0157$ at $V/\Omega = 100$ corresponded to $F = 0.999954$; halving
the error again should push $F$ to roughly $0.99999$. The scaling shows why
strong blockade is worth paying for, and why the returns diminish: each factor
of 2 in fidelity improvement costs a factor of 2 in interaction strength.

### Answers to 4–6

**4.** A lost atom is visible on the next fluorescence image, so the error is
**heralded**: you know which qubit is gone and when. That makes it an erasure,
and erasure-correcting codes are substantially more efficient than codes that
must locate and identify an unknown error. Systems have been run continuously
for over two hours by replenishing lost atoms mid-computation.

**5.** Any two of: every atom is identical, so there is no fabrication step per
qubit and no per-device calibration; the footprint is roughly 4 μm per atom, so
10,000 qubits span about 400 μm; extra qubits means extra tweezer beams from the
same modulator rather than new lithography; and idle atoms in the ground state
barely interact, so they are nearly error-free while waiting.

**6.** $C_6/\hbar\Omega$ in these units is $(100\ \,\mathrm{MHz}{\cdot}\mu\mathrm{m}^6)/(5\ \text{MHz}) = 20$ μm⁶, so

$$r_b = 20^{1/6} = e^{\ln(20)/6} = e^{0.4986} \approx 1.65\ \mu\text{m}$$

At twice that radius, $r = 3.29$ μm, and since $V \propto r^{-6}$ the
interaction is weaker by $2^6 = 64$:

$$V/h = \frac{100}{3.29^6} = \frac{100}{20 \cdot 2^6} = \frac{5}{64} \approx 0.078\ \text{MHz}$$

so about $78$ kHz, against the $5$ MHz drive — a ratio of $0.016$, far too small
to blockade anything. That is the sharpness of the $1/r^6$ falloff in one
number.

## Summary

- A neutral-atom qubit is a pair of **long-lived ground states** — typically
  hyperfine levels split by a few GHz. Idle atoms barely interact and hold
  coherence for seconds.
- **Rydberg blockade** supplies the interaction. Exciting a neighbour requires
  the doubly-excited state, shifted by $V = C_6/r^6$ with $C_6 \propto n^{11}$;
  when $V \gg \hbar\Omega$ the excitation is off resonance and blocked.
- The **blockade radius** is $r_b = (C_6/\hbar\Omega)^{1/6}$. The sixth root
  makes it insensitive to parameters — a factor of 64 changes it by only 2 —
  while the $1/r^6$ falloff outside it is extremely sharp.
- Verified by simulating the three-pulse CZ sequence: the conditional phase
  $\phi_{\text{cond}} \to \pi$ as $V/\Omega \to \infty$, with the phase error
  falling as $(\pi/2)\,\Omega/V$, reaching $F = 0.999954$ at $V/\Omega = 100$.
  At $V = 0$ the same sequence is a perfect **local** gate that entangles
  nothing, which is why fidelity alone is not the right score.
- The gate stays **diagonal** in the computational basis at every $V$; the
  failure mode at intermediate blockade is leakage into $|r\rangle$, seen as
  $|u_{11}|$ dipping to $0.73$ at $V/\Omega = 1$.
- **Scaling is the advantage**: identical qubits, no per-qubit fabrication, a
  footprint of a few microns each, and reconfigurable geometry. Arrays of
  thousands of atoms have been demonstrated, and the largest logical-qubit
  experiments on any platform have run here.
- **Loss is the distinctive error** — and because it is heralded it is an
  erasure, which is far easier to correct than an unknown error.

## References

- Jaksch, D. et al., "Fast quantum gates for neutral atoms" (PRL, 2000) — the
  blockade gate protocol simulated above.
- Urban, E. et al., "Observation of Rydberg blockade between two atoms"
  (2003), and Gaëtan, A. et al. (2009) — the first two-atom blockade gates.
- Saffman, M., Walker, T. G. & Mølmer, K., "Quantum information with Rydberg
  atoms" (Reviews of Modern Physics, 2010) — the standard review, including the
  $C_6 \propto n^{11}$ scaling and blockade-radius treatment.
- Levine, H. et al. and Bluvstein, D. et al. (Harvard/QuEra) — high-fidelity
  parallel gates, zoned architectures, and the logical-qubit results.
- Bluvstein, D. et al. (Nature, January 2026) — 96 logical qubits with a
  $[[16,6,4]]$ code.
- Barredo, D. et al. and Schymik, K. et al. — defect-free assembly and
  rearrangement of large atom arrays.
- Browaeys, A. & Lahaye, T., "Many-body physics with individually controlled
  Rydberg atoms" — context on the interaction physics.
- [Trapped Ions](57_trapped_ions.md) — the platform to compare coherence and
  fidelity against.
- [Photonic Systems](58_photonic_systems.md) — the preceding platform.
- [Spin Qubits](60_spin_qubits.md) — the next platform.
- [Surface Codes](52_surface_codes.md) — the error-correction context for the
  physical-to-logical ratios quoted.

---

**Next:** [Spin Qubits](60_spin_qubits.md)
