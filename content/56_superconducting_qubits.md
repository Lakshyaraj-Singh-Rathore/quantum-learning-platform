# Superconducting Qubits

Superconducting qubits are the platform behind most of the machines you can
access in the cloud, and the platform behind the first credible demonstration of
a surface code logical qubit. They are also the most obviously *engineered* of
the quantum hardware families: a transmon is a lithographically printed circuit
that behaves as a single artificial atom.

This lesson covers how a transmon encodes a qubit, what numbers a real device
actually achieves, and where the errors come from.

## Learning objectives

By the end of this lesson you should be able to:

- **Describe** how a transmon encodes a qubit.
- **State** typical coherence times and gate fidelities.
- **Identify** the dominant error mechanisms for this platform.

## Prerequisites

[Quantum Noise and Decoherence](09_quantum_noise.md) (recommended).
$T_1$ and $T_2$ are the figures quoted per platform.

## From an oscillator to a qubit

An $LC$ circuit is a harmonic oscillator, and its energy levels are evenly
spaced:

$$E_m = \hbar\omega_r\left(m + \tfrac12\right)$$

Evenly spaced levels are useless as a qubit. A drive resonant with the
$0 \leftrightarrow 1$ transition is equally resonant with $1 \leftrightarrow 2$,
so you cannot address the first transition without immediately exciting the
second. A harmonic oscillator has no addressable two-level subspace.

The Josephson junction fixes this. It is a nonlinear, non-dissipative inductor,
and it makes the level spacing **uneven**. The circuit Hamiltonian is

$$H = 4E_C(\hat{n} - n_g)^2 - E_J\cos\hat{\phi}$$

where $E_C = e^2/2C$ is the charging energy, $E_J$ is the Josephson energy,
$\hat{n}$ is the number of Cooper pairs on the island, $\hat{\phi}$ is the
superconducting phase, and $n_g$ is a gate-offset charge. The $-E_J\cos\hat\phi$
term is the nonlinearity: it is what turns an evenly spaced ladder into an
anharmonic one.

The two energies define everything. $E_C$ sets how much a single extra Cooper
pair costs; $E_J$ sets how freely the phase can move. Their ratio $E_J/E_C$
determines which regime the device is in.

## The transmon

A bare Josephson junction operated at $E_J/E_C \sim 1$ is a **charge qubit**, and
it has a fatal problem: its transition frequency depends strongly on $n_g$, so
stray electric charge in the environment — which nobody can control — shifts the
qubit frequency and destroys the coherence.

The transmon's insight is to shunt the junction with a large capacitor. That
lowers $E_C$ and pushes the device into the regime

$$E_J/E_C \;\sim\; 50\text{–}100$$

In this regime the charge sensitivity does not merely decrease — it is
**exponentially suppressed**. That is the whole point of the design, and it can
be checked numerically.

## Verified: the transmon spectrum

The Hamiltonian above can be diagonalised directly in the charge basis, where
$\langle n|H|n\rangle = 4E_C(n - n_g)^2$ and $\langle n|\cos\hat\phi|n+1\rangle = \tfrac12$. Truncating at $|n| \le 25$ and fixing $E_C/h = 250$ MHz:

| $E_J/E_C$ | $\omega_{01}/2\pi$ | $\sqrt{8E_JE_C} - E_C$ | $\alpha/2\pi$ | $-E_C$ | Charge dispersion |
|---|---|---|---|---|---|
| 1 | 1.0252 | 0.4571 | $-0.9948$ | $-0.2500$ | $7.8\times10^{-1}$ |
| 5 | 1.4114 | 1.3311 | $-0.8812$ | $-0.2500$ | $2.7\times10^{-1}$ |
| 20 | 2.8887 | 2.9123 | $-0.3638$ | $-0.2500$ | $4.4\times10^{-3}$ |
| 50 | 4.7355 | 4.7500 | $-0.2873$ | $-0.2500$ | $9.9\times10^{-6}$ |
| 100 | 6.8113 | 6.8211 | $-0.2739$ | $-0.2500$ | $6.3\times10^{-9}$ |

Frequencies in GHz; $\alpha = \omega_{12} - \omega_{01}$ is the anharmonicity;
charge dispersion is the peak-to-peak variation of $\omega_{01}$ as the gate
offset $n_g$ sweeps from $0$ to $\tfrac12$.

### Reading the table

Three results, all of them the ones that matter:

**The anharmonicity converges to $-E_C$.** At $E_J/E_C = 100$ the computed
$\alpha/2\pi = -274$ MHz against $-E_C/h = -250$ MHz. This is the standard
transmon result, and it tells you something directly useful: the anharmonicity
is set by the charging energy alone, so choosing $E_C$ sets how strongly you can
address the $0\leftrightarrow1$ transition without leaking into $|2\rangle$.
Real transmons run at $\alpha/2\pi \approx -200$ to $-300$ MHz.

**The transition frequency follows $\omega_{01} \approx \sqrt{8E_JE_C} - E_C$.**
At $E_J/E_C = 50$ the numerical value is 4.7355 GHz against the analytic 4.7500
GHz. With $E_C/h = 250$ MHz and $E_J/E_C = 50$ the qubit lands at about
$4.7$ GHz — squarely in the $4\text{–}6$ GHz band where real devices operate.

**The charge dispersion collapses by eight orders of magnitude.** From $0.78$ GHz
at $E_J/E_C = 1$ to $6.3\times10^{-9}$ GHz at $E_J/E_C = 100$. That is the
transmon's entire reason for existing. At $E_J/E_C = 1$ the qubit frequency
swings by three quarters of a gigahertz as stray charge drifts, which is
unusable. At $E_J/E_C = 100$ the same stray charge moves the frequency by a few
hertz.

### Computing the spectrum

```python
import numpy as np


def transmon_spectrum(EJ, EC, ng, n_max=25):
    """Lowest eigenvalues of H = 4 E_C (n - n_g)^2 - E_J cos(phi).

    In the charge basis |n>, the diagonal is 4 E_C (n - n_g)^2 and the cosine
    couples neighbouring charge states with matrix element -E_J / 2.
    """
    ns = np.arange(-n_max, n_max + 1)
    H = np.diag(4 * EC * (ns - ng) ** 2).astype(float)
    for i in range(len(ns) - 1):
        H[i, i + 1] -= EJ / 2
        H[i + 1, i] -= EJ / 2
    return np.linalg.eigvalsh(H)


EC = 0.250                                  # E_C / h in GHz
for ratio in (1, 5, 20, 50, 100):
    EJ = ratio * EC
    E = transmon_spectrum(EJ, EC, 0.0)
    w01, w12 = E[1] - E[0], E[2] - E[1]
    # charge dispersion: spread of w01 as the offset charge sweeps 0 -> 1/2
    w01s = [transmon_spectrum(EJ, EC, g)[1] - transmon_spectrum(EJ, EC, g)[0]
            for g in np.linspace(0, 0.5, 21)]
    print(f"EJ/EC={ratio:4d}  w01={w01:.4f} GHz  "
          f"anharmonicity={w12 - w01:+.4f} GHz  "
          f"charge dispersion={max(w01s) - min(w01s):.2e} GHz")
```

## How the qubit is addressed

The computational states are the two lowest energy levels, $|0\rangle$ and
$|1\rangle$. Because the ladder is anharmonic, the $0\leftrightarrow1$
transition sits at a different frequency from $1\leftrightarrow2$, so a
microwave pulse tuned to $\omega_{01}$ drives only the intended transition. The
anharmonicity is the margin: with $\alpha/2\pi \approx -250$ MHz, the unwanted
transition is a quarter of a gigahertz away.

Single-qubit gates are shaped microwave pulses at $\omega_{01}$, typically
$10\text{–}50$ ns long. Readout disperses the qubit state onto a coupled
resonator whose frequency shifts depending on whether the qubit is in
$|0\rangle$ or $|1\rangle$; measuring the resonator's response reveals the state
without absorbing the qubit.

Two-qubit gates come in two main flavours:

- **Cross-resonance** (IBM). Drive one qubit at the frequency of its neighbour.
  The resulting conditional rotation entangles them, without any tunable
  element.
- **Tunable-coupler CZ** (Google and others). A coupler between the qubits is
  flux-tuned to bring specific levels briefly into resonance, accumulating a
  controlled phase. Fast, but requires a flux line per coupler.

Typical two-qubit gate durations run from about $25$ ns to several hundred
nanoseconds. The fastest reported is a $25$ ns controlled-Z at $99.8\%$
fidelity (Oxford Quantum Circuits, 2025); Google's Willow runs a surface-code
cycle — measurement, decode and reset — in about $1.1\ \mu$s.

## Typical device parameters

These are published figures for superconducting transmon devices as of 2025–2026.
They are **ranges across the fleet, not specifications** — individual qubits on
a single chip vary by factors of two or more, and the numbers move every year.

| Quantity | Typical range | Notes |
|---|---|---|
| Qubit frequency $\omega_{01}/2\pi$ | 4–6 GHz | consistent with the computed 4.74 GHz above |
| Anharmonicity $\alpha/2\pi$ | $-200$ to $-300$ MHz | equals $-E_C$ |
| $T_1$ (relaxation) | 100–300 μs typical; 400 μs+ in recent research devices | Aalto reported a 425 μs median, 666 μs maximum (2025) |
| $T_2$ (coherence) | 100–350 μs typical; $T_2^{\text{echo}}$ above 1 ms demonstrated | often shorter than $T_1$ |
| Single-qubit gate error | $10^{-4}$ to $10^{-3}$ | 99.9%–99.99% fidelity |
| Two-qubit gate error | $10^{-3}$ to $10^{-2}$ | 99%–99.9%; best around 99.85%–99.9% |
| Single-qubit gate time | 10–50 ns | |
| Two-qubit gate time | 25–300 ns | |
| Readout error | $5\times10^{-3}$ to $2\times10^{-2}$ | 98%–99.5%, slower than gates |

Two figures from the literature anchor the table. A 2025 review reports median
$T_1 = 288$ μs and $T_2 = 127$ μs for the IBM devices used in the utility-scale
experiments, with mean one-qubit error per gate of $6.75\times10^{-4}$ and
mean two-qubit error per gate of $1.15\times10^{-2}$ — a striking 17× gap
between the one-qubit and two-qubit numbers that is characteristic of the
platform. Toshiba and RIKEN reported $T_1 = 230$ μs and a two-qubit fidelity of
99.90% sustained over twelve hours (2024).

Note the pattern that dominates everything else: **two-qubit gates are roughly
an order of magnitude worse than single-qubit gates, and they are an order of
magnitude slower.** Any circuit's error budget is dominated by its entangling
gates.

## Verified: the coherence-limited floor

There is a hard floor on gate error that no amount of better control can beat: a
gate cannot be more faithful than the qubit's own coherence allows. For a gate
of duration $t_g$,

$$\epsilon_{\text{floor}} \;\approx\; \frac{t_g}{3T_1} + \frac{t_g}{3T_2}$$

Verified across four representative device parameter sets:

| $T_1$ (μs) | $T_2$ (μs) | 1q gate (ns) | 2q gate (ns) | 1q floor | 2q floor | Depth budget |
|---|---|---|---|---|---|---|
| 100 | 120 | 25 | 200 | $1.5\times10^{-4}$ | $1.2\times10^{-3}$ | 600 |
| 200 | 250 | 30 | 300 | $9.0\times10^{-5}$ | $9.0\times10^{-4}$ | 833 |
| 300 | 400 | 35 | 400 | $6.8\times10^{-5}$ | $7.8\times10^{-4}$ | 1000 |
| 500 | 600 | 40 | 500 | $4.9\times10^{-5}$ | $6.1\times10^{-4}$ | 1200 |

The last column is $T_2/t_g$ — the number of sequential two-qubit gates you can
apply before coherence is gone. It is the single most important number for
deciding what fits on the hardware, and it sits stubbornly in the range of a few
hundred to a little over a thousand.

Compare the floor with reality. The best two-qubit errors are around
$10^{-3}$, against a coherence floor of $0.6\text{–}1.2\times10^{-3}$ in the
table. **State-of-the-art two-qubit gates are within a factor of two or three of
what coherence permits.** There is not an order of magnitude of headroom left in
gate control; further improvement has to come from longer coherence or from
error correction.

## Dominant error mechanisms

### Relaxation ($T_1$)

The qubit loses energy to its environment. The identified contributors:

- **Two-level systems (TLS).** Defects at the metal–air, metal–substrate and
  junction interfaces that absorb energy at frequencies near the qubit. This is
  widely considered the dominant relaxation mechanism, and it is a materials
  problem, not a circuit-design one.
- **Quasiparticles.** Broken Cooper pairs that tunnelling across the junction
  causes, generated by stray infrared light, cosmic rays or thermal leaks.
- **Purcell decay.** The qubit decays into its own readout resonator. Managed by
  filtering, but the readout path is always a loss channel.
- **Dielectric and surface loss.** Lossy amorphous oxides at surfaces and
  interfaces.

### Dephasing ($T_2$)

The relative phase of $|0\rangle$ and $|1\rangle$ randomises.

- **Flux noise.** Especially for frequency-tunable qubits, where the qubit
  frequency depends on a magnetic flux that drifts. A major reason fixed-
  frequency transmons are attractive.
- **Charge noise.** The mechanism the transmon was designed to suppress, and
  largely successful — but not entirely eliminated.
- **Photon shot noise.** Stray photons in the readout resonator shift the qubit
  frequency via the AC Stark effect, dephasing it.
- **Thermal noise and control electronics.** Phase noise in the microwave
  source transfers directly into the qubit.

Note that $1/T_2 = 1/(2T_1) + 1/T_\phi$, so $T_2 \le 2T_1$ always, and
relaxation alone sets a ceiling on coherence.

### Gate errors

- **Control errors.** Miscalibrated pulse amplitude, phase or duration; pulse
  distortion.
- **Leakage.** The drive populates $|2\rangle$ despite the anharmonicity.
  Leakage is qualitatively different from a bit flip: the state leaves the
  computational subspace and Pauli stabilisers cannot detect it, so it needs
  dedicated leakage-reduction operations.
- **Residual $ZZ$ coupling.** Neighbouring qubits interact even when idle, which
  is an always-on correlated error.

### Correlated errors

- **Crosstalk.** Operating on one qubit perturbs its neighbours.
- **Cosmic rays and correlated bursts.** High-energy events generate quasiparticles
  across an entire chip at once, producing simultaneous errors on many qubits.
  This violates the independence assumption behind
  [the threshold theorem](54_threshold_theorem.md), and it is one reason a real
  machine's logical error rate can exceed the prediction.

### Readout errors

Readout is slow — hundreds of nanoseconds to microseconds — and typically the
least accurate operation. State preparation and measurement errors are
separable from gate errors by
[readout correction](55_error_mitigation.md), which is why that technique is so
widely used on this platform.

## Limitations

- **Coherence is the binding constraint.** A depth budget of a few hundred to a
  thousand two-qubit gates is what the numbers permit, and no control
  improvement changes it.
- **Nearest-neighbour connectivity.** Most superconducting chips couple only
  adjacent qubits, so non-adjacent operations cost SWAPs, which cost depth.
- **Every qubit needs wiring.** Drive lines, flux lines and readout resonators
  all have to reach the chip through a dilution refrigerator. Routing and
  thermal load are serious engineering limits on scale.
- **Dilution refrigeration.** Operation at around 10 mK is required, which sets
  the size, cost and power envelope of any installation.
- **Fabrication variability.** Qubit parameters come from lithography and vary
  across a wafer, so each device needs individual calibration, and TLS defects
  are essentially random.
- **Errors are not independent.** Crosstalk and correlated bursts break the
  assumption that error-correction analysis rests on.

## Common misconceptions

- **"A transmon is a harmonic oscillator."** The entire point is that it is
  not. The Josephson junction supplies the anharmonicity, without which there
  is no addressable two-level subspace.
- **"More capacitance is always better."** The shunt suppresses charge noise
  but also reduces $E_C$, and $E_C$ sets the anharmonicity. Transmon designs
  trade charge insensitivity against anharmonicity; you cannot maximise both.
- **"$T_1$ and $T_2$ are the same sort of thing."** $T_1$ is energy relaxation;
  $T_2$ is phase coherence and includes relaxation. $T_2 \le 2T_1$ always.
- **"Gate fidelity is limited by control precision."** For the best two-qubit
  gates, no — the coherence floor computed above is within a factor of two or
  three. Coherence, not control, is the limit.
- **"Superconducting qubits have the best coherence."** They have among the
  shortest. Trapped ions and neutral atoms hold coherence for seconds. The
  superconducting advantage is **speed**: gates 1000× faster, which partly
  compensates.
- **"Leakage is just another error."** It takes the state out of the
  computational subspace entirely, where Pauli stabilisers cannot see it.

## Exercises

1. Why is an evenly spaced ladder unsuitable for a qubit? What specifically goes
   wrong when you drive it?

2. Using the verified table, what happens to the charge dispersion as
   $E_J/E_C$ goes from 1 to 100, and what does that mean for the device?

3. A transmon has $E_C/h = 250$ MHz and $E_J/E_C = 60$. Estimate $\omega_{01}/2\pi$
   and the anharmonicity.

4. A qubit has $T_1 = 200$ μs and $T_2 = 150$ μs. Two-qubit gates take $300$ ns.
   Compute the coherence-limited error floor and the depth budget. A proposed
   circuit needs 5000 two-qubit gates — does it fit?

5. Why does leakage to $|2\rangle$ require treatment different from a bit flip?

6. Name two error mechanisms on this platform that violate the independence
   assumption of the threshold theorem, and say briefly why each is correlated.

### Answers to 1–3

**1.** In an evenly spaced ladder the $0\leftrightarrow1$ and $1\leftrightarrow2$
transitions are at the same frequency. A drive resonant with one is resonant
with the other, so you cannot excite $|1\rangle$ without also exciting
$|2\rangle$, $|3\rangle$ and so on. There is no two-level subspace you can
address, which is exactly what a qubit needs.

**2.** The charge dispersion falls from $7.8\times10^{-1}$ GHz to
$6.3\times10^{-9}$ GHz — about eight orders of magnitude. At $E_J/E_C = 1$ the
qubit frequency swings by most of a gigahertz as uncontrolled offset charge
drifts, which destroys coherence. At $E_J/E_C = 100$ the same drift moves it by
a few hertz, which is negligible. That suppression is what makes the transmon
usable at all.

**3.** $\omega_{01} \approx \sqrt{8E_JE_C} - E_C$ with $E_J = 60 \times 250\ \text{MHz} = 15$ GHz:

$$\omega_{01}/2\pi \approx \sqrt{8 \times 15 \times 0.25} - 0.25 = \sqrt{30} - 0.25 \approx 5.48 - 0.25 = 5.23\ \text{GHz}$$

The anharmonicity is $-E_C$, so $\alpha/2\pi \approx -250$ MHz. Both are in the
normal operating range.

### Answers to 4–6

**4.** The floor is

$$\epsilon \approx \frac{t_g}{3T_1} + \frac{t_g}{3T_2} = \frac{0.3}{600} + \frac{0.3}{450} = 5.0\times10^{-4} + 6.7\times10^{-4} = 1.17\times10^{-3}$$

(times in μs). So no two-qubit gate can beat about $1.2\times10^{-3}$ error on
this qubit. The depth budget is $T_2/t_g = 150\,\mu\text{s}/0.3\,\mu\text{s} = 500$ two-qubit gates. A circuit needing 5000 is ten times over budget: **it does
not fit**, and no improvement in control changes that — only longer coherence or
error correction would.

**5.** A bit flip stays inside the computational subspace and is detectable by
Pauli stabiliser measurements. Leakage takes the state to $|2\rangle$, outside
the subspace, where those stabilisers are blind to it. A leaked qubit silently
stops participating correctly and the error is invisible to the decoder, so it
needs dedicated leakage-reduction operations rather than ordinary correction.

**6.** Any two of:

- *Crosstalk.* Driving one qubit perturbs its neighbours through residual
  coupling, so errors on nearby qubits happen together rather than
  independently.
- *Cosmic-ray and quasiparticle bursts.* A single high-energy event generates
  quasiparticles across a whole chip at once, producing many simultaneous
  errors — the textbook example of a correlated fault.
- *Residual $ZZ$ coupling.* Neighbouring qubits interact while idle, so their
  errors are not independent even when nothing is being driven.
- *Drifting calibration.* A parameter that drifts over the course of an
  experiment produces errors correlated in time, violating the Markovian
  assumption as well as the independence one.

## Summary

- A Josephson junction makes the circuit **anharmonic**, and that anharmonicity
  is what makes an addressable qubit possible.
- The transmon shunts the junction with a capacitor to reach
  $E_J/E_C \sim 50\text{–}100$. Verified by direct diagonalisation: the
  anharmonicity converges to $-E_C$, the frequency follows
  $\sqrt{8E_JE_C} - E_C$, and the charge dispersion collapses by **eight orders
  of magnitude** from $E_J/E_C = 1$ to $100$.
- The qubit is the two lowest levels, addressed by microwave pulses at
  $\omega_{01}$; the anharmonicity is the margin that keeps $|2\rangle$ out of
  it.
- Typical figures: $\omega_{01}/2\pi$ of 4–6 GHz, anharmonicity $-200$ to
  $-300$ MHz, $T_1$ of 100–300 μs, $T_2$ of 100–350 μs, one-qubit error
  $10^{-4}$–$10^{-3}$, two-qubit error $10^{-3}$–$10^{-2}$, two-qubit gates
  $25$–$300$ ns.
- **Two-qubit gates are the bottleneck** — roughly ten times worse and ten times
  slower than one-qubit gates.
- Verified: the coherence-limited error floor $t_g/3T_1 + t_g/3T_2$ gives a
  depth budget $T_2/t_g$ of only 600–1200 two-qubit gates, and the best
  two-qubit gates are already within a factor of two or three of that floor.
- Dominant errors: TLS defects and quasiparticles (relaxation), flux and photon
  shot noise (dephasing), control error and leakage (gates), crosstalk and
  cosmic rays (correlated), plus slow readout.
- The platform trades short coherence for **speed** — gates a thousand times
  faster than ions or atoms — which is why it is the leading candidate for
  surface-code error correction despite having the shortest coherence times.

## References

- Koch, J. et al., "Charge-insensitive qubit design derived from the Cooper pair
  box" — the original transmon paper; the $E_J/E_C$ analysis above.
- Blais, A., Grimsmo, A. L., Girvin, S. M. & Wallraff, A., "Circuit quantum
  electrodynamics" — the full cQED framework.
- Kjaergaard, M. et al., "Superconducting qubits: current state of play" — a
  survey of parameters and error mechanisms.
- Krantz, P. et al., "A quantum engineer's guide to superconducting qubits" —
  practical device physics.
- Google Quantum AI, "Quantum error correction below the surface code threshold"
  (Nature, 2024) — Willow parameters, the 1.1 μs cycle time.
- Tuokkola et al. (Aalto, Nature Communications, 2025) — $T_1$ median 425 μs,
  maximum 666 μs, $T_2^{\text{echo}}$ to 1.06 ms.
- Toshiba & RIKEN (2024) — $T_1 = 230$ μs, two-qubit fidelity 99.90% sustained
  over twelve hours.
- EPJ Quantum Technology 12, 2025, "Superconducting quantum computers: who is
  leading the future?" — fleet-wide IBM medians quoted in the table.
- [Trapped Ions](57_trapped_ions.md) — the contrasting platform: long coherence,
  slow gates, all-to-all connectivity.
- [Calibrated Noise Models and Connectivity Topologies](61_platform_comparison.md)
  — the cross-platform comparison.
- [Surface Codes](52_surface_codes.md) — why this platform's speed and planar
  layout suit the surface code.

---

**Next:** [Trapped Ions](57_trapped_ions.md)
