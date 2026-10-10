# Trapped Ions

Trapped ions are the other platform with a credible route to fault-tolerant
quantum computing, and they win on the metrics that matter most for error
correction: the highest two-qubit gate fidelities of any platform, the longest
coherence times, and a connectivity that removes the need for SWAP gates
entirely. They pay for all of it in speed.

This lesson covers how an ion encodes a qubit, how a chain of ions shares a
single mechanical bus that gives every qubit a direct line to every other, and
how that trade-off compares with the superconducting platform in
[the previous lesson](56_superconducting_qubits.md).

## Learning objectives

By the end of this lesson you should be able to:

- **Describe** how ion internal states encode a qubit.
- **Explain** how trapped ions achieve all-to-all connectivity.
- **Contrast** gate speed and coherence with superconducting devices.

## Prerequisites

[Quantum Noise and Decoherence](09_quantum_noise.md) (recommended). Same
per-platform metrics.

## The physical system

A trapped-ion qubit is a single atom, ionised and held in vacuum by
electromagnetic fields. Two features make this attractive, and both are
consequences of using atoms:

**Every qubit is identical by construction.** A $^{171}\mathrm{Yb}^+$ ion is the
same as every other $^{171}\mathrm{Yb}^+$ ion, anywhere, forever. There is no
fabrication spread, no two-level-system defect lottery, no per-device
calibration lottery. This is the structural reason ion fidelities are high, and
it contrasts sharply with superconducting devices, where lithographic variation
means every qubit must be characterised individually.

**Atoms are naturally long-lived.** Isolated from the environment in ultra-high
vacuum, an internal atomic state can hold coherence for seconds to minutes —
four to five orders of magnitude longer than a transmon.

### The trap

Ions cannot be held in a static electric field minimum — Earnshaw's theorem
forbids it. The standard solution is the **Paul trap** (precisely, the linear
Paul trap used in quantum computing):

- **Radio-frequency electrodes** create an oscillating quadrupole field that
  confines the ions radially. The ions sit at the node of the RF field, which
  is why they are so well isolated.
- **DC endcap electrodes** confine them axially, with a static harmonic well of
  frequency $\nu_z$, typically in the range of $0.1$ to $5$ MHz.

The result is a string of ions held in a line by the balance of the axial
confinement pushing them together and the Coulomb repulsion pushing them apart.

## How ion internal states encode a qubit

The qubit lives in two long-lived internal states of the ion. There are three
common choices, and the choice sets the character of the whole device.

| Encoding | States used | Splitting | Coherence | Addressed by |
|---|---|---|---|---|
| **Hyperfine** ("clock") | Two hyperfine levels of the ground electronic state, e.g. $^{171}\mathrm{Yb}^+$ $S_{1/2}\,|F=0,m_F=0\rangle \leftrightarrow |F=1,m_F=0\rangle$ | $\sim 12.6$ GHz (microwave) | Very long, seconds to minutes | Microwave, or Raman lasers |
| **Optical** | Ground to metastable excited state, e.g. $^{40}\mathrm{Ca}^+$ $S_{1/2} \leftrightarrow D_{5/2}$ | $\sim 400$ THz (optical, 729 nm) | Limited by excited-state lifetime, $\sim 1$ s | Narrow-linewidth laser |
| **Zeeman** | Two Zeeman sublevels of one hyperfine state | MHz (set by a magnetic field) | Long, but sensitive to field noise | RF or microwave |

The **hyperfine** encoding dominates in quantum computing because both states
are in the electronic ground manifold, so spontaneous emission is not a decay
channel at all and coherence is limited only by magnetic-field stability. The
$^{171}\mathrm{Yb}^+$ clock transition is a "first-order field-insensitive"
point: at the operating magnetic field the transition frequency is stationary
with respect to field fluctuations, which is why it reaches coherence times of
seconds.

The **optical** encoding offers easy individual addressing and straightforward
readout, at the cost of the excited state's finite lifetime.

### What makes it a qubit

In all cases, two properties make the encoding work as a qubit:

1. The two levels are **isolated** — transitions to other states are far off
   resonance, so the drive addresses only the intended pair.
2. The states are **long-lived** — the dominant decoherence is dephasing from
   magnetic-field noise, not spontaneous decay.

Notation used below: $|g\rangle$ and $|e\rangle$ are the two qubit states,
$\omega_0$ is their splitting, and $\nu_z$ is the axial trap frequency.

## The phonon bus

Here is the mechanism that makes trapped ions different from everything else.

The ions are charged and repel each other, but they are held in a common
harmonic well. They cannot move independently. Small displacements of the chain
decompose into **collective normal modes** — quantised vibrational modes, or
*phonons* — and every ion participates in every mode.

That shared motion is a **bus**. Coupling the internal state of ion $i$ to the
motion, and the motion to the internal state of ion $j$, entangles $i$ with $j$
— regardless of how far apart they sit in the chain. This is the physical
origin of all-to-all connectivity.

### The model

In dimensionless units, with $l^3 = e^2/(4\pi\varepsilon_0 M\nu_z^2)$ for ion
mass $M$, the potential energy of a chain of $N$ ions at axial positions
$u_i = z_i/l$ is

$$f(u) = \sum_i u_i^2 + \sum_{i\neq j}\frac{1}{|u_i - u_j|}$$

The first term is the trap; the second is Coulomb repulsion. Equilibrium
positions $u_m$ satisfy

$$u_m - \sum_{j \neq m}\frac{u_m - u_j}{|u_m - u_j|^3} = 0$$

and the normal-mode frequencies follow from the Hessian of $f$:

$$\omega_p^2 = \frac{\nu_z^2}{2}\,\lambda_p, \qquad f_{mm} = 2 + 4\sum_{j\neq m}\frac{1}{|u_m-u_j|^3}, \qquad f_{mj} = -\frac{4}{|u_m-u_j|^3}$$

### Worked example: two ions

Put the ions at $-a$ and $+a$. The equilibrium condition for ion 1 is

$$-a - \frac{-2a}{(2a)^3} = 0 \;\Longrightarrow\; a = \frac{1}{4a^2} \;\Longrightarrow\; a^3 = \frac14 \;\Longrightarrow\; a = 2^{-2/3} \approx 0.62996$$

so the ion spacing is $2a = 2^{1/3} \approx 1.2599$ in units of $l$. With
$|u_1 - u_2| = 2a$ and $a^3 = 1/4$:

$$f_{11} = 2 + \frac{4}{(2a)^3} = 2 + \frac{4}{8a^3} = 2 + 2 = 4, \qquad f_{12} = -\frac{4}{(2a)^3} = -2$$

so the Hessian is $\begin{pmatrix}4 & -2 \\ -2 & 4\end{pmatrix}$, with
eigenvalues $2$ (antisymmetric, ions moving against each other) and $6$
(symmetric, ions moving together). Hence

$$\omega = \nu_z\sqrt{\tfrac{2}{2}} = \nu_z \quad\text{and}\quad \omega = \nu_z\sqrt{\tfrac{6}{2}} = \sqrt{3}\,\nu_z$$

The lower mode is the **centre of mass**: the whole chain oscillates rigidly in
the trap, which by definition happens at the bare trap frequency $\nu_z$. The
upper mode is the **stretch**, at $\sqrt{3}\,\nu_z \approx 1.732\,\nu_z$.

### Verified: mode spectra

Computing the equilibrium numerically and diagonalising the Hessian:

| $N$ | Spacing $/l$ | Mode frequencies $\omega_p/\nu_z$ |
|---|---|---|
| 2 | 1.25992 | 1.00000, 1.73205 |
| 3 | 1.07722 | 1.00000, 1.73205, 2.40832 |
| 4 | 0.95787 | 1.00000, 1.73205, 2.41038, 3.05096 |
| 5 | 0.87145 | 1.00000, 1.73205, 2.41199, 3.05486, 3.67081 |

Two exact checks confirm the computation:

- $N = 2$ gives $\sqrt{3}\,\nu_z = 1.732051\,\nu_z$ for the stretch mode, matching the hand calculation.
- $N = 3$ gives $\sqrt{29/5}\,\nu_z = 2.408319\,\nu_z$ for the breathing mode, against a computed $2.40832$ — agreement to $4.7\times10^{-9}$.

### Reading the spectra

Three features matter:

**The centre-of-mass mode is always exactly $\nu_z$**, for every $N$. A rigid
translation of the whole chain feels only the trap, never the Coulomb
interaction, so its frequency is independent of the number of ions.

**The spectrum gets denser as $N$ grows.** The highest mode rises while the
lowest stays pinned at $\nu_z$, so the modes crowd together. This is the central
scaling problem: more ions means more modes packed into a narrowing frequency
gap, and a gate that must avoid exciting the wrong ones has less room to
operate.

**The spacing shrinks** — from $1.26\,l$ at $N=2$ to $0.87\,l$ at $N=5$. Tighter
packing means stronger Coulomb coupling and a stiffer, harder-to-control chain.

### Computing the spectra

```python
import numpy as np
from scipy.optimize import minimize


def potential(u):
    """f(u) = sum u_i^2 + sum_{i != j} 1/|u_i - u_j|, dimensionless.

    The double sum over i != j counts each pair twice, which is why the
    Coulomb term carries no separate factor of 2.
    """
    d = np.abs(u[:, None] - u[None, :])
    iu = np.triu_indices(len(u), 1)
    return np.sum(u ** 2) + 2.0 * np.sum(1.0 / d[iu])


def hessian(u):
    n = len(u)
    H = np.zeros((n, n))
    for m in range(n):
        for j in range(n):
            if m == j:
                continue
            H[m, m] += 4.0 / abs(u[m] - u[j]) ** 3
            H[m, j] = -4.0 / abs(u[m] - u[j]) ** 3
    H[np.diag_indices(n)] += 2.0
    return H


def normal_modes(n):
    """Equilibrium positions and axial mode frequencies in units of nu_z."""
    u0 = np.linspace(-1, 1, n) * n ** (2 / 3) / 2.0
    res = minimize(potential, u0, method="BFGS", options={"gtol": 1e-12})
    u = res.x - np.mean(res.x)
    lam = np.linalg.eigvalsh(hessian(u))
    return u, np.sqrt(np.maximum(lam, 0.0) / 2.0)


for n in (2, 3, 4, 5):
    u, w = normal_modes(n)
    print(f"N={n}  spacing/l = {(u.max()-u.min())/(n-1):.5f}   "
          f"omega/nu_z = " + "  ".join(f"{x:.5f}" for x in w))

# the centre-of-mass mode is the shared bus: every ion moves by the same amount
u, w = normal_modes(5)
vals, vecs = np.linalg.eigh(hessian(u))
k = np.argmin(np.abs(np.sqrt(np.maximum(vals, 0) / 2) - 1.0))
v = vecs[:, k] / np.linalg.norm(vecs[:, k])
print(f"COM eigenvector, N=5: {np.round(np.abs(v), 6)}")
```

## Why that gives all-to-all connectivity

The centre-of-mass mode is special, and this can be checked directly. Its
eigenvector is **uniform**: every ion moves by exactly the same amount.

| $N$ | COM frequency $/\nu_z$ | Max deviation of COM eigenvector from uniform |
|---|---|---|
| 2 | 1.00000000 | $1.1\times10^{-16}$ |
| 3 | 1.00000000 | $1.1\times10^{-16}$ |
| 5 | 1.00000000 | $3.9\times10^{-16}$ |
| 10 | 1.00000000 | $6.1\times10^{-16}$ |
| 15 | 1.00000000 | $6.1\times10^{-16}$ |

For $N = 5$ the eigenvector is $(0.447214, 0.447214, 0.447214, 0.447214, 0.447214)$, and $1/\sqrt{5} = 0.4472136$. Every ion couples to the bus with
equal strength.

The consequence is the whole point. To entangle ions $i$ and $j$, you address
those two with laser beams that couple their internal states to the shared
motion. It does not matter whether they are neighbours or at opposite ends of
the chain — both couple to the same bus. **A two-qubit gate between any pair is
a single native operation.**

Compare with superconducting devices, where qubits are wired to their
immediate neighbours and entangling two distant qubits requires a chain of SWAP
gates, each one an additional two-qubit gate with its own error. For algorithms
whose communication pattern is not local, that overhead is substantial —
published estimates for the reduction in circuit depth from all-to-all
connectivity run from about $3\times$ to $10\times$ depending on the algorithm.

There is a caveat, and it is the reason the advantage is not unlimited: the
modes are shared, so gates that use the same mode cannot always run
simultaneously on disjoint pairs. Full parallelism is a scheduling problem, not
a free consequence.

## The Mølmer–Sørensen gate

The standard entangling gate on this platform is the **Mølmer–Sørensen** gate.
Understanding it explains why ion gates are both slow and extraordinarily
accurate.

### The mechanism

Two laser beams, detuned from resonance by $\pm\delta$ around the qubit
frequency, illuminate both ions. In a frame rotating with the qubit, and after
the rotating-wave approximation, the interaction-picture Hamiltonian is

$$H(t) = g\,S_x\left(a^\dagger e^{i\delta t} + a\,e^{-i\delta t}\right), \qquad S_x = \sigma_1^x + \sigma_2^x$$

where $a, a^\dagger$ act on the motional mode, $g$ is the spin-motion coupling
(set by the laser intensity and the Lamb–Dicke parameter), and $\delta$ is the
detuning from the mode frequency.

Read the Hamiltonian carefully: it is a **force on the oscillator whose sign
depends on the spin state**. Ions in an eigenstate of $S_x$ push the motion one
way or the other. In the phase space of the motional mode, the state traces out
a circle.

The gate runs for one full period, $t = 2\pi/\delta$. At that moment the
trajectory closes: the motion returns exactly to where it started, so spin and
motion **disentangle**, and what remains is a pure spin operation. The phase
accumulated is proportional to the area enclosed, which is why this is a
*geometric* phase gate — and why it is robust: the phase depends on the area,
not on the details of the trajectory.

The result is

$$U = \exp\left(-i\theta\,S_x^2\right), \qquad \theta = 2\pi\left(\frac{g}{\delta}\right)^2$$

### Verified: the gate is insensitive to the motion

Since $S_x^2 = 2 + 2\sigma_1^x\sigma_2^x$, applying $U$ to $|gg\rangle$ gives

$$U|gg\rangle = e^{-2i\theta}\Big(\cos(2\theta)\,|gg\rangle - i\sin(2\theta)\,|ee\rangle\Big)$$

so the entanglement, measured by the concurrence, is $|\sin(4\theta)|$. This
prediction was checked by direct numerical integration of $H(t)$ over a
truncated Fock space:

| $g/\delta$ | Concurrence (numerical) | $|\sin\!\big(8\pi(g/\delta)^2\big)|$ | Difference | $F$ (motion returned) |
|---|---|---|---|---|
| 0.05 | 0.062791 | 0.062791 | $1.3\times10^{-8}$ | 1.000000 |
| 0.10 | 0.248690 | 0.248690 | $5.0\times10^{-8}$ | 1.000000 |
| 0.15 | 0.535827 | 0.535827 | $9.8\times10^{-8}$ | 1.000000 |
| 0.20 | 0.844328 | 0.844328 | $1.1\times10^{-7}$ | 1.000000 |
| 0.25 | 1.000000 | 1.000000 | $1.8\times10^{-13}$ | 1.000000 |

The analytic law holds to better than $10^{-7}$ across the range, confirming
both $\theta = 2\pi(g/\delta)^2$ and the closed-loop picture.

A maximally entangling gate needs $4\theta = \pi/2$, that is $\theta = \pi/8$,
which occurs at $g/\delta = 1/4$. At that setting, verified:

| Initial motional state $n$ | Concurrence | $F$ (motion returned) |
|---|---|---|
| 0 | 1.00000000 | 1.00000000 |
| 1 | 1.00000000 | 1.00000000 |
| 2 | 1.00000000 | 1.00000000 |
| 3 | 1.00000000 | 1.00000000 |
| 4 | 1.00000000 | 1.00000000 |

The output is the Bell state $(|gg\rangle - i|ee\rangle)/\sqrt{2}$ — populations
$(0.5, 0, 0, 0.5)$ and a coherence of $-0.5i$, a relative phase of exactly
$-90^\circ$.

### What the table shows

**The gate produces the same entangling unitary whether the ion chain started
in its motional ground state or in the $n = 4$ state.** This is the single most
important property of the Mølmer–Sørensen gate, and it is why trapped ions do
not need to be cooled to the motional ground state in order to compute. The
motion is a bus, not a memory: it only has to come back to where it started,
and the loop guarantees that.

### Why the gate is slow

Look at the gate time: $t = 2\pi/\delta$. To avoid exciting the motional mode
resonantly, the detuning $\delta$ must be small compared with the mode
frequency — and the mode frequencies are megahertz at best, with the gaps
between modes narrowing as the chain grows. A small $\delta$ means a long gate.

That is the fundamental speed limit. You cannot simply drive harder: pushing
$g$ up means displacing the motion further, and beyond the Lamb–Dicke regime
the tidy closed-loop picture breaks down. In the verification above, at
$g/\delta = 0.56$ the concurrence from $n = 5$ fell to $0.60$ — well outside the
regime where the gate is motion-insensitive. Ion gates are slow because the bus
they use is slow, and that is physics, not engineering.

## State preparation, single-qubit gates and measurement

**State preparation** is optical pumping. A laser drives transitions that
eventually funnel population into one particular state — typically $|g\rangle$
— from which the pump light cannot excite it. It is self-correcting: repeated
cycling drives the population to the target with very high probability.

**Single-qubit gates** are resonant Rabi drives. A microwave field (for
hyperfine qubits) or a pair of Raman laser beams (for optical addressing)
drives coherent oscillations between $|g\rangle$ and $|e\rangle$; pulse area and
phase set the rotation. Individual addressing means focusing a laser on one ion
in the chain, which requires the ions to be far enough apart to resolve —
another reason the shrinking spacing at high $N$ is a problem.

**Measurement** is the platform's other great advantage: **fluorescence
detection**. A laser resonant with a cycling transition from $|g\rangle$ scatters
many photons; the same laser does not excite $|e\rangle$, which stays dark.
Collecting the fluorescence for a few hundred microseconds distinguishes bright
from dark with very high confidence. Because $|g\rangle$ and $|e\rangle$ are
separated by an optical transition, the two outcomes are spectacularly
distinguishable — this is why ion readout fidelities are among the best in the
field, and why measurement is not the dominant error source it is on
superconducting hardware.

## Gate speed and coherence: the contrast

This is the trade that defines the platform's relationship with superconducting
devices.

| Quantity | Trapped ions | Superconducting | Ratio |
|---|---|---|---|
| Two-qubit gate time | $\sim 100$ μs (range $10$ μs – $1$ ms) | $\sim 100$–$300$ ns | ions $\sim 10^3\times$ slower |
| Coherence $T_2$ | seconds to minutes | $100$–$350$ μs | ions $\sim 10^4\times$ longer |
| Two-qubit fidelity | $99.9\%+$ routine; best $99.99\%$ | $99$–$99.9\%$ | ions better |
| Connectivity | all-to-all | nearest-neighbour | ions better |
| Physical qubits | tens to $\sim 100$ | hundreds to $>1000$ | superconducting far ahead |
| Operating environment | room-temperature vacuum chamber, lasers | $\sim 10$ mK dilution refrigerator | — |

The first two rows pull in opposite directions, and the ratio that actually
matters is the last column's quotient.

### The ratio that matters

The number of sequential two-qubit gates
you can apply before coherence is gone is $T_2/t_g$:

| Platform | $T_2$ | Two-qubit gate $t_g$ | Depth budget $T_2/t_g$ |
|---|---|---|---|
| Trapped ions (typical) | $1$ s | $100$ μs | $10\,000$ |
| Trapped ions (fast gate) | $1$ s | $10$ μs | $100\,000$ |
| Superconducting (typical) | $200$ μs | $200$ ns | $1\,000$ |
| Superconducting (fastest) | $200$ μs | $25$ ns | $8\,000$ |

**Ions are about a thousand times slower per gate but roughly ten thousand times
longer-lived, and they net roughly an order of magnitude more sequential
gates.** That is the honest version of the comparison: superconducting devices
win decisively on wall-clock time, ions win on how much you can do before the
quantum state dies.

The practical consequence follows directly. If your runtime budget is measured
in seconds, superconducting hardware wins. If your constraint is circuit depth
and total error, ions win. And for error correction the second is what counts:
high fidelity plus long coherence plus all-to-all connectivity is exactly the
combination that minimises physical qubits per logical qubit.

## Device parameters

The figures below are **vendor-reported results for specific machines**, not
universal properties of the platform. They move quickly; treat them as snapshots
of where the field stood in 2025–2026 rather than as specifications.

| Device | Species | Reported result |
|---|---|---|
| Quantinuum Helios (Nov 2025) | $^{137}\mathrm{Ba}^+$ | 98 physical ions, 48 logical qubits, all-pairs two-qubit fidelity $99.921\%$, single-qubit $99.9975\%$ |
| IonQ prototype (Oct 2025) | $^{171}\mathrm{Yb}^+$ | $99.99\%$ two-qubit fidelity using electronic qubit control |
| Oxford Ionics (2024) | $^{43}\mathrm{Ca}^+$ | $99.97\%$ two-qubit fidelity, laser-free electronic control |

Commonly used species are $^{171}\mathrm{Yb}^+$, $^{43}\mathrm{Ca}^+$,
$^{137}\mathrm{Ba}^+$ and $^{88}\mathrm{Sr}^+$, each chosen for a convenient
combination of transition wavelengths, mass and coherence.

Two architectural approaches are being pursued:

- **QCCD** (quantum charge-coupled device, Quantinuum's approach). The trap has
  separate loading, storage, gate and readout zones, and ions are **shuttled**
  between them by moving the confining potential. This keeps gate zones small
  and well-controlled while allowing many ions, at the cost of time spent
  shuttling and the error that comes with it.
- **Electronic qubit control** (Oxford Ionics, now part of IonQ). Replace laser
  beams with microwave electrodes fabricated into the trap chip itself, removing
  the optical complexity that dominates a laser-based system's engineering.

## Dominant error mechanisms

- **Motional heating.** Electric-field noise at the trap surface drives the
  motional mode to higher energy. Because the Mølmer–Sørensen gate is mediated
  by that motion, heating directly degrades gate fidelity. The rate scales
  steeply with trap size — smaller traps heat worse — which is a real tension
  with the drive to miniaturise.
- **Laser phase and intensity noise.** The gate phase depends on the laser
  amplitude, so intensity noise becomes gate error.
- **Spontaneous emission.** Small for hyperfine qubits driven off-resonantly,
  but not zero, and it grows with the drive strength needed for faster gates.
- **Mode crosstalk.** With many modes packed close together, a gate intended to
  use one mode off-resonantly excites others. This is the scaling limiter.
- **Shuttling error** in QCCD architectures — heating and dephasing incurred
  while moving ions.
- **Magnetic-field drift**, the main dephasing channel for hyperfine qubits.

## Limitations

- **Gates are slow, and intrinsically so.** The bus is a megahertz mechanical
  oscillator, and the detuning must stay below it. Wall-clock runtimes are
  orders of magnitude worse than superconducting hardware, which matters
  enormously for error correction, where a syndrome-extraction round that takes
  a microsecond on a transmon takes about a millisecond on an ion.
- **Scaling the chain is hard.** More ions means a denser mode spectrum, tighter
  spacing that makes individual addressing harder, and more crosstalk. The
  practical limit for a single chain is tens of ions.
- **Many ions need many lasers.** Individual addressing means individual beam
  paths, and the optical complexity grows with the qubit count. This is the
  central engineering argument for electronic control.
- **Vacuum and vibration.** Ions need ultra-high vacuum and are sensitive to
  mechanical vibration of the trap.
- **Qubit count lags.** Demonstrated systems are in the tens to low hundreds,
  against over a thousand for the largest superconducting chips.

## Common misconceptions

- **"All-to-all connectivity means every pair can be gated simultaneously."**
  No. Pairs that share a motional mode compete for it. Full parallelism is a
  scheduling problem.
- **"Trapped ions are just better than superconducting qubits."** They are
  better at fidelity, coherence and connectivity, and much worse at speed and
  scale. The ratio $T_2/t_g$ favours ions by only about an order of magnitude,
  not by the four orders of magnitude the raw coherence numbers suggest.
- **"The ions must be cooled to the motional ground state to compute."** They
  must not. The verified table above shows the Mølmer–Sørensen gate produces an
  identical unitary from $n = 0$ through $n = 4$. Cooling is still needed for
  high fidelity, but not as a precondition for the gate to work.
- **"A trapped-ion qubit is a natural atom, so it has no engineering in it."**
  The qubit is natural; everything around it — trap, vacuum, lasers, control
  electronics — is not.
- **"Faster gates just need stronger lasers."** Beyond the Lamb–Dicke regime the
  gate stops being motion-insensitive. The verification shows concurrence
  dropping to $0.60$ at $g/\delta = 0.56$ with $n = 5$.
- **"All-to-all connectivity removes all compilation overhead."** It removes
  SWAP insertion. Routing, scheduling around shared modes, and shuttling in
  QCCD architectures remain.

## Exercises

1. Explain in one or two sentences why the centre-of-mass mode frequency is
   independent of the number of ions in the chain.

2. Using the worked example, verify that the $N=2$ stretch mode is at
   $\sqrt{3}\,\nu_z$. Show the Hessian and its eigenvalues.

3. What is the concurrence produced by a Mølmer–Sørensen gate run at
   $g/\delta = 0.15$? Is it maximally entangling? What value of $g/\delta$
   would be?

4. Why is a trapped-ion two-qubit gate necessarily slower than a superconducting
   one? Give the physical reason, not an engineering one.

5. A trapped-ion device has $T_2 = 10$ s and a two-qubit gate time of
   $200$ μs. A superconducting device has $T_2 = 200$ μs and a two-qubit gate
   time of $200$ ns. Compute the depth budget $T_2/t_g$ for each and the ratio.

6. Name two reasons the mode spectrum gets harder to work with as the number of
   ions grows.

### Answers to 1–3

**1.** In the centre-of-mass mode the whole chain translates rigidly, so no
inter-ion separation changes and the Coulomb energy is untouched. Only the trap
potential is felt, and that gives the bare trap frequency $\nu_z$ regardless of
$N$. Verified numerically: the COM frequency is $1.00000000\,\nu_z$ for every
$N$ from 2 to 15, and its eigenvector is uniform to $10^{-16}$.

**2.** With the ions at $\pm a$ and $a^3 = 1/4$, the spacing is $2a$, and

$$f_{11} = 2 + \frac{4}{(2a)^3} = 2 + \frac{4}{8 \cdot \frac14} = 4, \qquad f_{12} = -\frac{4}{(2a)^3} = -2$$

so the Hessian is $\begin{pmatrix}4 & -2 \\ -2 & 4\end{pmatrix}$. Its
eigenvalues are $4 - 2 = 2$ for the antisymmetric vector $(1,-1)$ and
$4 + 2 = 6$ for the symmetric one $(1,1)$. Using
$\omega_p^2 = \nu_z^2\lambda_p/2$: $\omega = \nu_z\sqrt{2/2} = \nu_z$ for the
centre of mass, and $\omega = \nu_z\sqrt{6/2} = \sqrt3\,\nu_z \approx 1.732\,\nu_z$ for the stretch.

**3.** With $\theta = 2\pi(g/\delta)^2 = 2\pi(0.15)^2 = 0.1414$, the concurrence
is $|\sin(4\theta)| = |\sin(0.5655)| = 0.5358$, matching the verified table. It
is not maximally entangling. A maximally entangling gate needs
$4\theta = \pi/2$, so $\theta = \pi/8$ and
$g/\delta = \sqrt{\theta/2\pi} = \sqrt{1/16} = 1/4$.

### Answers to 4–6

**4.** The gate is mediated by a collective motional mode whose frequency is
megahertz at most, and the detuning $\delta$ must stay well below that
frequency to avoid resonantly exciting the mode. Since the gate takes
$t = 2\pi/\delta$, a megahertz-scale bus forces a microsecond-scale gate. That
is a property of the mechanism, not of the lasers: using motion as the bus is
what buys all-to-all connectivity, and the bus's own frequency sets the speed.

**5.** Ions: $T_2/t_g = 10\,\text{s} / 200\,\mu\text{s} = 50\,000$.
Superconducting: $200\,\mu\text{s} / 200\,\text{ns} = 1\,000$. The ratio is
$50$, so the ion device supports about fifty times as many sequential two-qubit
gates — while being a thousand times slower per gate, since
$200\,\mu\text{s} / 200\,\text{ns} = 1000$.

**6.** Any two of: the spectrum crowds, because the lowest mode stays pinned at
$\nu_z$ while the highest keeps rising, so the gaps between neighbouring modes
narrow and a gate has less room to avoid off-resonant excitation; the ion
spacing shrinks (from $1.26\,l$ at $N=2$ to $0.87\,l$ at $N=5$), making
individual laser addressing harder; and with more modes present, crosstalk onto
unintended modes becomes more likely.

## Summary

- A trapped-ion qubit is two internal states of a single trapped atom — usually
  a **hyperfine** pair in the electronic ground state, split by about
  $12.6$ GHz for $^{171}\mathrm{Yb}^+$ and addressed by microwaves or Raman
  lasers. Atoms are identical by construction and hold coherence for seconds to
  minutes.
- The ions share **collective motional modes** — a phonon bus. Verified by
  diagonalising the Coulomb-plus-trap Hessian: the centre of mass is always
  exactly $\nu_z$, the $N=2$ stretch is $\sqrt3\,\nu_z$, and the $N=3$ breathing
  mode is $\sqrt{29/5}\,\nu_z$ to within $4.7\times10^{-9}$.
- **All-to-all connectivity follows from the bus.** The centre-of-mass
  eigenvector is uniform — verified to $10^{-16}$ for $N$ from 2 to 15, with
  every entry equal to $1/\sqrt{N}$. Any pair couples through the same mode, so
  any two ions can be gated in one native operation, with no SWAPs.
- The **Mølmer–Sørensen gate** drives a closed loop in the mode's phase space
  over $t = 2\pi/\delta$, giving $U = \exp(-i\theta S_x^2)$ with
  $\theta = 2\pi(g/\delta)^2$. Verified to better than $10^{-7}$, and maximally
  entangling at $g/\delta = 1/4$.
### The trade-off, in one table

- Verified: at that setting the gate gives **concurrence $1.00000000$ and
  returns the motion to its initial state, identically for $n = 0$ through
  $4$**. The gate does not care what the motion was doing — which is why ions
  need not be in the motional ground state to compute.
- Ions are about $10^3\times$ slower per gate and about $10^4\times$ longer-lived
  than superconducting qubits, netting roughly $10\times$ more sequential gates
  ($T_2/t_g \sim 10^4$ against $\sim 10^3$). Superconducting wins on wall-clock
  time and qubit count; ions win on fidelity, coherence and connectivity.
- Vendor-reported figures (98 ions and 48 logical qubits on Quantinuum Helios;
  $99.99\%$ two-qubit fidelity on an IonQ prototype) are snapshots of specific
  machines, not platform constants.

## References

- Cirac, J. I. & Zoller, P., "Quantum computations with cold trapped ions" — the
  original proposal.
- James, D. F. V., "Quantum dynamics of cold trapped ions with application to
  quantum computation" — the normal-mode analysis used above, including the
  $\sqrt{29/5}$ result.
- Mølmer, K. & Sørensen, A., "Multiparticle entanglement of hot trapped ions" —
  the geometric-phase gate that does not require ground-state cooling.
- Sørensen, A. & Mølmer, K., "Quantum computation with ions in thermal motion".
- Wineland, D. J. et al. — the experimental foundations of ion-trap quantum
  control; fluorescence readout.
- Blatt, R. & Roos, C. F., "Quantum simulations with trapped ions".
- Leibfried, D., Blatt, R., Monroe, C. & Wineland, D., "Quantum dynamics of
  single trapped ions" (Reviews of Modern Physics).
- Quantinuum (2025) — Helios: 98 $^{137}\mathrm{Ba}^+$ ions, 48 logical qubits,
  $99.921\%$ all-pairs two-qubit fidelity.
- IonQ / Oxford Ionics (2024–2025) — electronic qubit control, $99.97\%$ then
  $99.99\%$ two-qubit fidelity.
- [Superconducting Qubits](56_superconducting_qubits.md) — the platform
  contrasted throughout.
- [Photonic Systems](58_photonic_systems.md) — the next platform.
- [Calibrated Noise Models and Connectivity Topologies](61_platform_comparison.md)
  — the cross-platform comparison.
- [Surface Codes](52_surface_codes.md) — why fidelity and connectivity together
  determine the physical-to-logical ratio.
- [Threshold Theorem and Fault Tolerance](54_threshold_theorem.md) — what the
  fidelity figures are ultimately for.

---

**Next:** [Photonic Systems](58_photonic_systems.md)
