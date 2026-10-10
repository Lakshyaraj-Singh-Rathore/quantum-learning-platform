# Spin Qubits

Spin qubits are the bet that quantum computing can be manufactured. A quantum
dot is 50–100 nanometres across — three orders of magnitude smaller than a
transmon — and the structures that confine the spins are defined by the same
lithography that makes every classical chip. In 2025, two-qubit gates above
$99\%$ fidelity were demonstrated on devices built in an industrial 300 mm
fabrication line.

The trade is that the qubit lives in a solid, with all the noise that implies.

## Learning objectives

By the end of this lesson you should be able to:

- **Describe** how electron or nuclear spin encodes a qubit.
- **Explain** how exchange interaction produces two-qubit gates.
- **State** the main fabrication and coherence challenges.

## Prerequisites

[Quantum Noise and Decoherence](../qiskit/quantum_noise.md) (recommended). Same
per-platform metrics.

## How spin encodes a qubit

An electron is a spin-$\tfrac12$ particle. In a magnetic field $B_0$ its two spin
states split by the Zeeman energy

$$E_Z = g\mu_B B_0$$

with $g \approx 2$ for a free electron and $\mu_B$ the Bohr magneton. The qubit is

$$|0\rangle = |\uparrow\rangle, \qquad |1\rangle = |\downarrow\rangle$$

At $B_0 = 1$ T the splitting is about $28$ GHz, comfortably in the microwave
range.

There are two broad families, and the difference matters:

| Qubit | What it is | Coherence | Why use it |
|---|---|---|---|
| **Electron spin** | The spin of a single electron confined in a quantum dot or bound to a donor | Milliseconds in purified $^{28}$Si | Fast to drive, couples via exchange, readable |
| **Nuclear spin** | The spin of an atomic nucleus, e.g. $^{31}$P | Seconds to minutes | Extraordinarily well shielded from electrical noise |

A donor in silicon gives you both: the electron spin is the fast interface for
driving and coupling, and the nuclear spin is a long-lived memory. That
electron-plus-nucleus pairing is one of the platform's distinctive features.

Other encodings exist and avoid some problems. **Singlet–triplet** qubits encode
in the joint state of two electrons in one double dot
$(|S\rangle, |T_0\rangle)$, which is insensitive to uniform magnetic-field
noise. **Hole spin** qubits in germanium couple strongly to electric fields,
allowing all-electrical control without a microwave antenna.

### The isotopic purity trick

Natural silicon is $4.7\%$ $^{29}$Si, an isotope with a nuclear spin. Those
nuclear spins form a fluctuating magnetic bath that dephases an electron spin
quickly. **Isotopically enriched $^{28}$Si** — purified to $>99.99\%$ — has zero
nuclear spin and is magnetically silent.

This single materials change takes electron-spin coherence from microseconds to
milliseconds and beyond, and it is the reason the best coherence numbers on this
platform are measured in silicon specifically. It is a striking example of
coherence being won by chemistry rather than by control engineering.

## Single-qubit gates

Rotating a spin means driving it at its Larmor frequency. Two mechanisms:

- **Electron spin resonance (ESR)** applies an oscillating magnetic field
  transverse to $B_0$. Simple in principle, but generating a local, fast
  oscillating field on a chip is awkward.
- **Electric dipole spin resonance (EDSR)** applies an oscillating *electric*
  field instead. Through spin–orbit coupling — or through a deliberately
  engineered magnetic field gradient from a micromagnet — an electric field can
  drive spin rotations. This is far easier to deliver on-chip, and it is why
  EDSR is the workhorse.

## Two-qubit gates: the exchange interaction

Here is the mechanism, and it is the heart of the platform.

Put two electrons in neighbouring quantum dots, separated by a tunnel barrier
whose height is set by a gate voltage. Because electrons are identical
fermions, the total wavefunction must be antisymmetric, and this ties the spin
state to the spatial state. The result is an effective spin–spin coupling:

$$H = J\,\mathbf{S}_1\cdot\mathbf{S}_2 = \frac{J}{4}\,\boldsymbol{\sigma}_1\cdot\boldsymbol{\sigma}_2$$

The coupling $J$ is the **exchange energy**, and it is controlled
electrostatically — lower the barrier and the electrons overlap more, raising
$J$ exponentially. That is the gate knob: a voltage pulse turns the interaction
on for a set time.

### Verified: what the exchange coupling does

Simulating $U = \exp(-iH t)$ on two spins, writing $\int J\,dt$ for the pulse
area:

| $\int J\,dt$ | Operation | Verification |
|---|---|---|
| $\pi$ | SWAP | Deviation $1.1\times10^{-16}$, global phase $+45^\circ$ |
| $\pi/2$ | $\sqrt{\text{SWAP}}$ | $U\cdot U$ reproduces SWAP exactly |

The $\pi/4$ global phase on SWAP is the expected $e^{i\pi/4}$.

**The exchange oscillation** in the $\{\left|\uparrow\downarrow\right\rangle, \left|\downarrow\uparrow\right\rangle\}$ subspace:

| $Jt$ | $P(\left|\uparrow\downarrow\right\rangle)$ | $P(\left|\downarrow\uparrow\right\rangle)$ |
|---|---|---|
| $0$ | 1.000000 | 0.000000 |
| $\pi/4$ | 0.853553 | 0.146447 |
| $\pi/2$ | 0.500000 | 0.500000 |
| $\pi$ | 0.000000 | 1.000000 |
| $3\pi/2$ | 0.500000 | 0.500000 |
| $2\pi$ | 1.000000 | 0.000000 |

Two things to read from it. At $Jt = \pi$ the spins have fully exchanged — that
is SWAP. At $Jt = \pi/2$ the state is an equal superposition, which is a
maximally entangled Bell state.

**The singlet–triplet splitting is exactly $J$.** Verified directly: the
singlet has energy $-\tfrac34 J$ and the triplet $+\tfrac14 J$, a splitting of
$1.000000\,J$. This is the energy scale that must be resolved spectroscopically
and the scale that sets the gate speed.

### What $\sqrt{\text{SWAP}}$ does and does not do

Verified by applying it to each computational basis state:

| Input | Concurrence of output | Output |
|---|---|---|
| $\left|\uparrow\uparrow\right\rangle$ | 0.000000 | $e^{-i\pi/8}\left|\uparrow\uparrow\right\rangle$ — only a phase |
| $\left|\uparrow\downarrow\right\rangle$ | 1.000000 | maximally entangled Bell state |
| $\left|\downarrow\uparrow\right\rangle$ | 1.000000 | maximally entangled Bell state |
| $\left|\downarrow\downarrow\right\rangle$ | 0.000000 | $e^{-i\pi/8}\left|\downarrow\downarrow\right\rangle$ — only a phase |

So $\sqrt{\text{SWAP}}$ **maximally entangles** $\left|\uparrow\downarrow\right\rangle$
and $\left|\downarrow\uparrow\right\rangle$, but leaves the parallel-spin states
untouched apart from a phase, because those are triplet eigenstates of
$\boldsymbol{\sigma}_1\cdot\boldsymbol{\sigma}_2$.

It is therefore entangling, but it is **not** a maximally entangling *gate* in
the CNOT sense — CNOT maps every product input to an entangled output. In
practice $\sqrt{\text{SWAP}}$ (or the exchange gate plus single-qubit rotations,
which gives CZ) is combined with single-qubit rotations to obtain a universal
set. That is a real compiler cost this platform pays.

### Verified: sensitivity to noise on $J$

Because $J$ depends exponentially on the tunnel barrier, charge noise — the
ubiquitous low-frequency noise in solid-state devices — translates directly
into fractional errors in $J$. Verified effect on the $\sqrt{\text{SWAP}}$ gate:

| $\delta J/J$ | Gate error $1-F$ |
|---|---|
| 0.001 | $2\times10^{-7}$ |
| 0.005 | $6\times10^{-6}$ |
| 0.010 | $2.3\times10^{-5}$ |
| 0.020 | $9.3\times10^{-5}$ |
| 0.050 | $5.8\times10^{-4}$ |
| 0.100 | $2.3\times10^{-3}$ |

The error grows **quadratically** in $\delta J/J$: a hundredfold increase in
$\delta J/J$ from $0.01$ to $0.1$ increases the error a hundredfold, from
$2.3\times10^{-5}$ to $2.3\times10^{-3}$.

That quadratic scaling is genuinely good news, and it is an important
architectural fact. Noise on $J$ is not a small perturbation of the gate
amplitude that adds linearly — it is a rotation-angle error, and the leading
term is second order. This is why **symmetric operation** and **dynamical
decoupling** are so effective here, and why the exchange gate is more robust
than the exponential sensitivity of $J$ would suggest. A 1% error in $J$ costs
only about $2\times10^{-5}$ of fidelity.

## Measurement

Spins are small and their magnetic moment is tiny, so spins are not measured
directly. The standard trick is **spin-to-charge conversion**: arrange things so
that the spin state determines whether an electron can move, then measure the
charge, which is easy.

The most common implementation is **Pauli spin blockade**. Two electrons in a
double dot can only form a doubly-occupied singlet configuration if their spins
are antiparallel. A parallel-spin (triplet) configuration is blockaded. So the
spin state controls whether charge moves, and a nearby **charge sensor** — a
single-electron transistor or a sensor quantum dot — reads the result.

Readout is typically the slowest and least accurate operation on this platform,
and getting single-shot readout fast is an active engineering target. Reported
state-preparation-and-measurement fidelities reach about $99.95\%$.

## The scaling argument

The case for spin qubits rests on three things:

**Size.** A quantum dot is 50–100 nm across. Millions of them fit on a chip
where a few thousand transmons would go.

**Manufacturability.** The devices are made with standard lithography. The
2025 Diraq/imec result is the proof point: randomly selected devices from an
industrial 300 mm production wafer, fabricated on a standard process flow,
exceeded $99\%$ two-qubit gate fidelity. No other platform can point to
demonstrated performance out of a commercial fab line.

**CMOS integration potential.** The control electronics could in principle sit
next to the qubits. Intel's Horse Ridge cryo-CMOS control chip addresses up to
128 qubits from a single die, and cryo-CMOS integration is the long-term route
past the wiring bottleneck that every solid-state platform faces.

## The challenges

This is where the platform is weakest, and the honest list is long.

- **Charge noise.** The dominant problem. Low-frequency electrical noise from
  the material and interfaces couples into $J$ and into the qubit frequency
  itself. The verified quadratic scaling helps, but $\delta J/J$ still needs to
  be held to a fraction of a percent.
- **Fabrication variability at the atomic scale.** Unlike atoms, every quantum
  dot is slightly different. $J$ depends exponentially on barrier geometry, so
  nanometre-scale variation produces large variation in coupling. Each device
  needs individual calibration.
- **The wiring bottleneck.** Every dot needs gate lines. Routing thousands of
  control lines into a dilution refrigerator is one of the hardest engineering
  problems in the field, and it is the main thing cryo-CMOS is meant to solve.
- **Valley states in silicon.** The conduction band of silicon has nearly
  degenerate valley degrees of freedom. If the valley splitting is small, the
  qubit can leak into a valley excitation. Splitting must be engineered
  large — another reason interface quality matters so much.
- **Readout speed and fidelity.** Slower and less accurate than the gates.
- **Magnetic-field control.** ESR needs a static field and microwave delivery;
  the field must be stable because the qubit frequency is set by it.

## Device parameters

Vendor- and group-reported figures for specific devices, not platform
constants.

| Result | Figures |
|---|---|
| Diraq / imec (Nature, Sept 2025) | $>99\%$ two-qubit fidelity on randomly selected devices from an industrial 300 mm wafer |
| SQC (Dec 2025) | $99.99\%$ two-qubit gate fidelity, reported as a record across platforms |
| Industry-compatible unit cells (2025) | $T_1 = 9.5$ s, $T_2^* = 40.6$ μs, $T_2^{\text{Hahn}} = 1.9$ ms; SPAM fidelity $99.95\%$ |
| Mobile spin qubits (2025) | $\sim99\%$ two-qubit CZ with conveyor shuttling; shuttling fidelity $99.5\%$ over 10 μm in under 200 ns; exchange $J/h \approx 33$ MHz; CZ in 58 ns |
| Intel Tunnel Falls | 12-qubit silicon spin processor from a 300 mm fab; Horse Ridge II control chip addressing up to 128 qubits |
| Coherence in purified $^{28}$Si | Electron spin coherence reported above 1 s; nuclear spin above 30 s |

Note the spread in the coherence column. $T_2^*$ of tens of microseconds and
$T_2^{\text{Hahn}}$ of milliseconds are different quantities measured
differently, and the difference between them — three orders of magnitude — tells
you that most of the dephasing is slow and refocusable. That is characteristic
of a solid-state environment.

## Common misconceptions

- **"Long $T_1$ means a good qubit."** $T_1$ of 9.5 s is useless if $T_2^*$ is
  40 μs. Coherence time and gate time must be compared, and the relevant
  coherence is the one that applies to the operation being run.
- **"The exchange gate is fragile because $J$ is exponentially sensitive."**
  Verified: the gate error scales *quadratically* with $\delta J/J$, so a 1%
  error in $J$ costs only $\sim2\times10^{-5}$ of fidelity. Exponential
  sensitivity of the coupling is not the same as exponential sensitivity of the
  gate.
- **"$\sqrt{\text{SWAP}}$ is a maximally entangling gate."** Verified: it
  maximally entangles the antiparallel inputs and leaves the parallel inputs
  untouched up to a phase. It is entangling, not maximally entangling.
- **"Silicon is silicon."** Natural silicon has $4.7\%$ spin-carrying $^{29}$Si
  and gives microsecond coherence. Isotopically purified $^{28}$Si gives
  milliseconds or better. The difference is the whole ballgame.
- **"Being small automatically means being scalable."** Small qubits help with
  density but make the wiring problem *harder*, not easier, and make each device
  more sensitive to atomic-scale fabrication variation.

## Exercises

1. Explain why the exchange interaction couples two spins, given that the
   spins do not interact magnetically in any meaningful way at this distance.

2. Verify that the singlet–triplet splitting is $J$. The singlet has
   $\boldsymbol{\sigma}_1\cdot\boldsymbol{\sigma}_2$ eigenvalue $-3$ and the
   triplet $+1$.

3. From the verified table, what pulse area $\int J\,dt$ would give a gate
   whose square is $\sqrt{\text{SWAP}}$?

4. A device has $\delta J/J = 0.03$. Estimate the $\sqrt{\text{SWAP}}$ gate
   error, using the quadratic scaling.

5. Why is isotopically purified $^{28}$Si used rather than natural silicon?

6. Name two reasons spin qubits are attractive for scaling, and two reasons
   they are hard.

### Answers to 1–3

**1.** The coupling is not magnetic — it is electrostatic plus the Pauli
principle. The total two-electron wavefunction must be antisymmetric, so the
spatial part and the spin part are linked: a symmetric spin state (triplet)
must pair with an antisymmetric spatial state, and vice versa. Those two
spatial configurations have different Coulomb energies, so the spin state ends
up with an energy that depends on the joint spin configuration. The result is
an effective $\mathbf{S}_1\cdot\mathbf{S}_2$ coupling with strength $J$ set by
the tunnelling — which is why a gate voltage controls it.

**2.** With $H = \frac{J}{4}\boldsymbol{\sigma}_1\cdot\boldsymbol{\sigma}_2$:
$E_S = \frac{J}{4}(-3) = -\frac34 J$ and $E_{T} = \frac{J}{4}(+1) = +\frac14 J$,
so $E_T - E_S = \frac14 J + \frac34 J = J$. Verified numerically as
$1.000000\,J$.

**3.** Squaring doubles the pulse area, so we need
$2\int J\,dt = \pi/2$, giving $\int J\,dt = \pi/4$. That is the
fourth-root-of-SWAP, and it is exactly why this construction generalises: the
$2^n$-th root of SWAP is obtained at $\int J\,dt = \pi/2^n$.

### Answers to 4–6

**4.** From the table, $\delta J/J = 0.01$ gives $2.3\times10^{-5}$. Scaling
quadratically by $(0.03/0.01)^2 = 9$ gives about $2.1\times10^{-4}$. (The
tabulated value at $0.02$ is $9.3\times10^{-5}$, and $9.3\times10^{-5}\times (0.03/0.02)^2 = 2.1\times10^{-4}$ — consistent.)

**5.** Natural silicon contains $4.7\%$ $^{29}$Si, which carries a nuclear spin.
Those nuclear spins form a fluctuating magnetic bath that rapidly dephases the
electron spin. Isotopically enriched $^{28}$Si at $>99.99\%$ purity has zero
nuclear spin, giving a magnetically silent host and extending electron-spin
coherence from microseconds to milliseconds.

**6.** *Attractive:* any two — quantum dots are 50–100 nm, three orders of
magnitude smaller than transmons; devices are made with standard lithography,
and $>99\%$ fidelity has been demonstrated on an industrial 300 mm line;
isotopically purified silicon gives very long coherence; and cryo-CMOS
integration offers a route past the wiring bottleneck. *Hard:* any two — charge
noise couples directly into the exchange coupling $J$; $J$ depends exponentially
on barrier geometry, so nanometre-scale fabrication variation demands
per-device calibration; the wiring bottleneck means thousands of control lines
into a dilution refrigerator; valley states in silicon provide a leakage
channel; and readout is slower and less accurate than the gates.

## Summary

- A spin qubit is the spin of a single electron (or nucleus) in a
  semiconductor. Electron spins give milliseconds of coherence in purified
  $^{28}$Si and are fast to drive; nuclear spins give seconds to minutes and
  serve as memory.
- **Isotopic purification is the key materials fact**: removing the $4.7\%$
  of spin-carrying $^{29}$Si takes electron coherence from microseconds to
  milliseconds.
- Two-qubit gates come from the **exchange interaction**
  $H = J\,\mathbf{S}_1\cdot\mathbf{S}_2$, with $J$ set electrostatically by the
  tunnel barrier.
- Verified by simulation: $\int J\,dt = \pi$ gives SWAP (deviation
  $10^{-16}$, global phase $e^{i\pi/4}$); $\int J\,dt = \pi/2$ gives
  $\sqrt{\text{SWAP}}$; the singlet–triplet splitting is exactly $J$; and the
  exchange oscillation has period $2\pi/J$.
- $\sqrt{\text{SWAP}}$ maximally entangles the antiparallel inputs but leaves
  $\left|\uparrow\uparrow\right\rangle$ and $\left|\downarrow\downarrow\right\rangle$
  unchanged up to a phase — entangling, but not a maximally entangling gate.
- **Gate error scales quadratically with $\delta J/J$** — verified: 1% gives
  $2.3\times10^{-5}$, 10% gives $2.3\times10^{-3}$. The exponential sensitivity
  of $J$ does not translate into exponential sensitivity of the gate, which is
  the platform's saving grace against charge noise.
- The scaling case is **size and manufacturability**: 50–100 nm dots, standard
  lithography, and $>99\%$ fidelity demonstrated on an industrial 300 mm wafer
  line.

## References

- Loss, D. & DiVincenzo, D. P., "Quantum computation with quantum dots"
  (PRA, 1998) — the original proposal, including the exchange gate.
- Kane, B. E., "A silicon-based nuclear spin quantum computer" (Nature, 1998) —
  donor spins in silicon.
- Petta, J. R. et al., "Coherent manipulation of coupled electron spins in
  semiconductor quantum dots" (Science, 2005) — the first exchange-based
  two-qubit gate and singlet–triplet oscillations.
- Koppens, F. H. L. et al., "Driven coherent oscillations of a single electron
  spin in a quantum dot" (Nature, 2006) — EDSR.
- Veldhorst, M. et al., "A two-qubit logic gate in silicon" (Nature, 2015) —
  the first two-qubit gate in silicon.
- Zwanenburg, F. A. et al., "Silicon quantum electronics" (Reviews of Modern
  Physics, 2013) — a comprehensive review of the physics and the challenges.
- Steinacker, P. et al. (Diraq/imec, Nature, September 2025) — $>99\%$
  two-qubit fidelity on an industrial 300 mm wafer line.
- Mobile spin qubits (Nature, 2025) — conveyor shuttling, $\sim99\%$ CZ, and
  teleportation between spins 320 nm apart.
- [Trapped Ions](57_trapped_ions.md),
  [Photonic Systems](58_photonic_systems.md),
  [Neutral Atoms](59_neutral_atoms.md) — the other platforms.
- [Calibrated Noise Models and Connectivity Topologies](61_platform_comparison.md)
  — the cross-platform comparison.
- [Error Mitigation](55_error_mitigation.md) — what to do before fault
  tolerance arrives.

---

**Next:** [Calibrated Noise Models and Connectivity Topologies](61_platform_comparison.md)
