# Photonic Systems

Photons are the only qubits that do not decohere. A photon travelling through
optical fibre at room temperature has essentially no environment to leak phase
into — there is no $T_1$ and no $T_2$ in the sense used for
[trapped ions](57_trapped_ions.md) or
[superconducting circuits](56_superconducting_qubits.md). The price is that
photons do not interact with each other at all, and that they are lost.

This lesson covers how a qubit is encoded in light, why linear optics makes
two-qubit gates probabilistic while single-qubit gates are free, and why loss —
not decoherence — is the error channel that defines the platform.

## Learning objectives

By the end of this lesson you should be able to:

- **Describe** a photonic qubit encoding.
- **Explain** how linear optics implements gates probabilistically.
- **State** why loss is the dominant error channel.

## Prerequisites

[Quantum Noise and Decoherence](../qiskit/quantum_noise.md) (recommended). Same
per-platform metrics.

## Why photons

The attractions are substantial:

- **No decoherence.** Photons barely interact with anything. Coherence times are
  not measured in microseconds or seconds but in *distance travelled*.
- **Room-temperature operation.** No dilution refrigerator.
- **Natural for networking.** Photons are the only qubit that can carry quantum
  information between machines, which makes them the default choice for
  [quantum networks](67_quantum_networks.md).
- **Manufacturable.** Silicon photonics borrows an existing fabrication
  industry, which is the central argument for scaling.

The difficulties are equally substantial: photons do not interact with one
another, and they get lost. Almost everything distinctive about this platform
follows from those two facts.

## Photonic qubit encodings

A qubit needs two distinguishable states of *something*. For light, there are
several choices of "something", and the choice determines what the hardware
looks like.

### Dual-rail

The most common encoding in single-photon architectures. Two optical modes (two
waveguides, two polarisations, two time slots) hold exactly one photon:

$$|0\rangle_L = |1,0\rangle, \qquad |1\rangle_L = |0,1\rangle$$

A general qubit state is $\alpha|1,0\rangle + \beta|0,1\rangle$. This is the
encoding used by PsiQuantum and most linear-optical architectures. Its virtue is
that **any single-qubit unitary is a beam splitter plus a phase shifter** —
verified below.

### Polarisation

$$|0\rangle_L = |H\rangle, \qquad |1\rangle_L = |V\rangle$$

Easy to make and measure with waveplates and polarising beam splitters, and it
is the historical workhorse of quantum optics experiments. Less natural for
integrated photonics, since on-chip waveguides have a preferred polarisation.

### Time-bin

$$|0\rangle_L = \text{photon in the early time bin}, \qquad |1\rangle_L = \text{photon in the late bin}$$

Robust against polarisation drift in fibre, which makes it the encoding of
choice for long-distance [quantum communication](67_quantum_networks.md).

### Bosonic / continuous-variable encodings

Instead of one photon in two modes, encode the qubit in a **single oscillator
mode** with a carefully structured state. The leading example is the
**Gottesman–Kitaev–Preskill (GKP)** code, where the qubit lives in a comb-like
superposition of squeezed states in phase space. This is
[continuous-variable](https://en.wikipedia.org/wiki/Continuous-variable_quantum_information)
rather than discrete, and it is Xanadu's approach.

GKP states have a remarkable property: **small displacements in phase space can
be detected and corrected**, so the encoding carries an intrinsic layer of error
correction before any code is layered on top. The catch is that producing them
requires substantial squeezing, and the quality achieved so far is far below
what fault tolerance demands — see the device table below.

## Verified: single-qubit gates are deterministic

This is the clean result on the platform, and it is worth understanding because
it explains why photonics is competitive at all.

A beam splitter with reflectivity $R$ mixes two modes. In the convention used
here, with $t = \sqrt{1-R}$ and $r = \sqrt{R}$:

$$U_{\text{BS}} = \begin{pmatrix} t & ir \\ ir & t \end{pmatrix}$$

which maps creation operators as $a_1^\dagger \to t\,a_1^\dagger + ir\,a_2^\dagger$
and $a_2^\dagger \to ir\,a_1^\dagger + t\,a_2^\dagger$.

Now apply it to a dual-rail qubit. The input has exactly one photon, and a beam
splitter **conserves photon number**, so the output also has exactly one photon.
The one-photon subspace is spanned by $\{|1,0\rangle, |0,1\rangle\}$ — which is
precisely the dual-rail qubit space. So the photon cannot leave the computational
subspace, and no post-selection is needed.

### Verified values

Verified by constructing the exact Fock-space operator:

| $R$ | Induced qubit unitary $U_{\text{qubit}}$ | Leakage from the one-photon subspace |
|---|---|---|
| 0.00 | $\begin{pmatrix}1 & 0 \\ 0 & 1\end{pmatrix}$ | $0$ (to $10^{-16}$) |
| 0.50 | $\begin{pmatrix}0.707 & 0.707i \\ 0.707i & 0.707\end{pmatrix}$ | $0$ (to $10^{-16}$) |
| 1.00 | $\begin{pmatrix}0 & i \\ i & 0\end{pmatrix}$ | $0$ (to $10^{-16}$) |

The leakage is zero to numerical precision at every reflectivity, and the
induced matrix is unitary at every reflectivity. Note that $R = 1$ gives
$i\sigma_x$: a bit flip, produced by a single optical element.

**Single-qubit gates in photonics are deterministic, exact, and cheap.** Add a
phase shifter and you have arbitrary single-qubit control. This is worth
contrasting with every other platform, where single-qubit gates are the easy
case but still cost fidelity.

Two-qubit gates are the hard case, and that is where the probability comes in.

### Computing the unitary

```python
import numpy as np
from scipy.linalg import expm, logm


def fock_ops(nmodes, nmax):
    """Annihilation operators on the truncated Fock space."""
    dims = [nmax + 1] * nmodes
    D = int(np.prod(dims))
    a = []
    for m in range(nmodes):
        op = np.zeros((D, D), dtype=complex)
        for idx in np.ndindex(*dims):
            if idx[m] == 0:
                continue
            src = list(idx); src[m] -= 1
            op[np.ravel_multi_index(tuple(src), dims),
               np.ravel_multi_index(idx, dims)] = np.sqrt(idx[m])
        a.append(op)
    return a, dims


def linear_optical_unitary(U, a):
    """Fock-space operator for a mode-mixing unitary U.

    For bosons, U_Fock = exp(sum_ij (log U)_ij a_i^dag a_j).
    """
    L = logm(np.asarray(U, dtype=complex))
    H = sum(L[i, j] * a[i].conj().T @ a[j]
            for i in range(L.shape[0]) for j in range(L.shape[1]))
    return expm(H)


def state(dims, occ):
    v = np.zeros(int(np.prod(dims)), dtype=complex)
    v[np.ravel_multi_index(tuple(occ), dims)] = 1.0
    return v


```

With those three helpers, both effects are four lines. The first loop shows a
beam splitter acting on one photon — a deterministic qubit gate — and the second
### Running it

```python
a, dims = fock_ops(2, 4)
ket0, ket1 = state(dims, (1, 0)), state(dims, (0, 1))
k11, k20, k02 = state(dims, (1, 1)), state(dims, (2, 0)), state(dims, (0, 2))

for R in (0.0, 0.5, 1.0):
    t, r = np.sqrt(1 - R), np.sqrt(R)
    UF = linear_optical_unitary([[t, 1j * r], [1j * r, t]], a)

    # (i) one photon in: a deterministic single-qubit gate, no leakage
    M = np.array([[ket0.conj() @ UF @ ket0, ket0.conj() @ UF @ ket1],
                  [ket1.conj() @ UF @ ket0, ket1.conj() @ UF @ ket1]])
    leak = 1 - abs(ket0.conj() @ UF @ ket0) ** 2 - abs(ket1.conj() @ UF @ ket0) ** 2
    print(f"R={R:.2f}  leakage={abs(leak):.1e}  U_qubit={np.round(M, 4).tolist()}")

    # (ii) one photon in each port: Hong-Ou-Mandel interference
    psi = UF @ k11
    print(f"        |1,1> -> {k20.conj() @ psi:+.4f}|2,0> "
          f"{k11.conj() @ psi:+.4f}|1,1> {k02.conj() @ psi:+.4f}|0,2>")
```

## The problem: photons do not interact

A two-qubit gate needs one photon to affect another. In vacuum, they do not.
Maxwell's equations are linear, so two light beams pass through each other
unchanged. Every component available — beam splitters, phase shifters,
waveguides — is a **linear** optical element, and no combination of linear
elements can make two photons interact deterministically.

So how is a gate possible at all? The answer is interference plus
**post-selection**, and the canonical demonstration is the Hong–Ou–Mandel
effect.

### Verified: Hong–Ou–Mandel interference

Put one photon into each input port of a beam splitter. Verified amplitudes in
the output Fock basis:

| $R$ | $\text{amp}(|2,0\rangle)$ | $\text{amp}(|1,1\rangle)$ | $\text{amp}(|0,2\rangle)$ | $P(|1,1\rangle)$ | $(1-2R)^2$ |
|---|---|---|---|---|---|
| 0.00 | 0 | 1.000 | 0 | 1.000000 | 1.000000 |
| 0.25 | $0.612i$ | 0.500 | $0.612i$ | 0.250000 | 0.250000 |
| 0.50 | $0.707i$ | **0** | $0.707i$ | **0.000000** | 0.000000 |
| 0.75 | $0.612i$ | $-0.500$ | $0.612i$ | 0.250000 | 0.250000 |
| 1.00 | 0 | $-1.000$ | 0 | 1.000000 | 1.000000 |

The $|1,1\rangle$ output amplitude is $t^2 - r^2 = 1 - 2R$, confirmed against
the closed form $(1-2R)^2$ in every row.

**At $R = 1/2$ the $|1,1\rangle$ amplitude is exactly zero.** The photons always
leave together, bunched into $|2,0\rangle$ or $|0,2\rangle$, even though nothing
made them interact. This is purely a consequence of bosonic statistics: the
amplitude for "both transmitted" and the amplitude for "both reflected"
interfere destructively.

(Equivalently, and depending on the beam-splitter phase convention, the output
is written as $(|2,0\rangle - |0,2\rangle)/\sqrt{2}$. The vanishing $|1,1\rangle$
component — the physical content — is convention-independent.)

### Why that gives a probabilistic gate

The bunching is an *effective* interaction: the two-photon amplitude depends on
the joint input, which is what an interaction would do. But notice what happened
— the useful outcome is only one of several possible outcomes. To get a gate,
you measure the output and **keep the run only if you got the outcome you
wanted**. The rest of the time the gate failed, and that failure is heralded:
you know it happened.

That is the deal at the heart of linear-optical quantum computing:

- **Single-qubit gates**: deterministic, because photon number is conserved and
  the qubit is the one-photon subspace.
- **Two-qubit gates**: probabilistic, because the interaction is supplied by
  post-selected interference rather than by a real coupling.

### Verified: boosting the success probability

A gate that fails most of the time is not directly usable — a circuit of $N$
such gates succeeds with probability $p^N$, which collapses. The resolution is
the **Knill–Laflamme–Milburn (KLM)** scheme: use ancilla photons and
teleportation to make the effective success probability arbitrarily close to 1.

The published KLM result is that an NS (nonlinear sign) gate built with $2n$
ancilla photons succeeds with probability

$$p = \frac{n^2}{(n+1)^2}$$

| $n$ | Ancilla photons | $p = n^2/(n+1)^2$ | Failure $1-p$ |
|---|---|---|---|
| 1 | 2 | 0.250000 | 0.750000 |
| 2 | 4 | 0.444444 | 0.555556 |
| 3 | 6 | 0.562500 | 0.437500 |
| 5 | 10 | 0.694444 | 0.305556 |
| 10 | 20 | 0.826446 | 0.173554 |
| 50 | 100 | 0.961169 | 0.038831 |
| 100 | 200 | 0.980296 | 0.019704 |

The $n = 1$ row reproduces the original KLM figure of exactly $1/4$. As $n$
grows the success probability approaches 1 — but the cost is ancilla photons,
which grow without bound. The scaling is polynomial in $1/(1-p)$, so scalable
computation is possible in principle, at a large constant overhead.

This is the trade that defines the platform's gate story: **probabilistic gates
made near-deterministic by spending more photons.**

The modern evolution of this idea is **fusion-based quantum computation**, used
by PsiQuantum. Rather than building up large entangled states and then gating
them, small entangled resource states are generated and then stitched together
by **fusion measurements** — partial Bell measurements that join two states.
Fusions are themselves probabilistic, but failures are heralded, so the
architecture routes around them.

## Measurement

Measurement in photonics is photon detection, and it is unusually good:

- **Destructive but near-perfect.** Detecting a photon absorbs it, but the
  efficiency of superconducting nanowire single-photon detectors is very high.
- **Photon-number-resolving (PNR) detection** is possible and is essential for
  GKP architectures, where the measurement outcome is a continuous quadrature
  value rather than a bit.
- **Homodyne detection** measures quadratures $\hat{q}$ and $\hat{p}$ — the
  continuous-variable counterpart, used by Xanadu.

Measurement is one of the platform's strengths, and it is why
[error correction](52_surface_codes.md) architectures here lean heavily on
measurement-based rather than circuit-based constructions.

## Why loss is the dominant error channel

Photons have no $T_1$ and no $T_2$. What they have is **loss**: the photon is
absorbed, scattered, or couples out of the waveguide, and the qubit simply
ceases to exist.

### Verified: loss is exponential

If a photon must pass through $N$ components, each transmitting with
probability $\eta$, the survival probability is $\eta^N$:

| $N$ | $\eta^N$ at $\eta = 0.99$ |
|---|---|
| 1 | 0.990000 |
| 10 | 0.904382 |
| 100 | 0.366032 |
| 1000 | 0.000043 |
| 10000 | $\sim 10^{-44}$ |

A per-component efficiency of 99% sounds excellent and is catastrophic at
scale. Over a kilometre of optical fibre at the standard $0.2$ dB/km:

| Distance | Transmission | Loss probability |
|---|---|---|
| 1 m | 0.999954 | $4.6\times10^{-5}$ |
| 100 m | 0.995405 | $4.6\times10^{-3}$ |
| 1 km | 0.954993 | $4.5\times10^{-2}$ |
| 10 km | 0.630957 | $3.7\times10^{-1}$ |
| 50 km | 0.100000 | $9.0\times10^{-1}$ |
| 100 km | 0.010000 | $9.9\times10^{-1}$ |

The transmission is $10^{-0.02L}$ for $L$ in kilometres, which is exponential
in distance. That is why long-distance quantum communication needs
[quantum repeaters](67_quantum_networks.md) rather than better fibre.

### Why this is worse than an equivalent gate error

Three reasons, and they are what make loss the *defining* challenge rather than
merely the largest number:

**1. It compounds across the whole circuit.** A gate error of $10^{-3}$ per
operation gives a total error of roughly $10^{-3}N$ for $N$ gates — linear, and
handled by [fault tolerance](54_threshold_theorem.md). Loss gives $\eta^N$ —
exponential, and not handled the same way.

**2. It is leakage, not a Pauli error.** A qubit that has lost its photon is no
longer in the computational subspace. Stabiliser codes detect and correct Pauli
errors; a missing photon is a different kind of event. Codes for photonics must
explicitly handle loss, typically by treating a detected loss as an erasure —
which is more forgiving than an unknown error, *provided the loss is detected*.
That is the crucial qualifier: **heralded** loss (you know the photon is gone)
is far easier to correct than **unheralded** loss (the photon vanished silently
and you compute on as if nothing happened).

**3. The qubit is destroyed, not merely perturbed.** For matter qubits, a
$T_1$ event leaves a qubit you can reset and reuse. A lost photon is gone.

The consequence for architecture: photonic quantum computing is largely the
problem of getting loss below threshold. Published thresholds vary enormously
with the scheme — under $1\%$ for the simplest fusion networks, up to around
$18.8\%$ per photon for the most advanced adaptive designs — and the whole
engineering programme is about closing the gap between the two.

## Device parameters

These are **vendor-reported results for specific systems**, not platform
constants. The gap between what is achieved and what is required is the story
here, so both numbers are given.

| System | Encoding | Reported figures |
|---|---|---|
| PsiQuantum Omega (Nature, Feb 2025) | Single-photon, dual-rail | SPAM fidelity $99.98\% \pm 0.01\%$; two-photon interference visibility $99.50\% \pm 0.25\%$; two-qubit fusion fidelity $99.22\% \pm 0.12\%$; BTO electro-optic switches and superconducting nanowire detectors integrated on a silicon photonic chip |
| Xanadu Borealis (2022) | Squeezed-state CV, GBS | 216 squeezed modes; mean squeezing $r \approx 1.1$ ($\sim 9.6$ dB) |
| Xanadu on-chip GKP (Nature, 2025) | GKP bosonic | $\geq 4$ resolvable peaks, $3\times3$ negative Wigner grid; symmetric effective squeezing $0.62 \pm 0.02$ dB, against a fault-tolerance threshold of $9.75$ dB |

Two things to read off that table.

The PsiQuantum figures are genuinely impressive fidelities — comparable to or
better than the best superconducting two-qubit gates. The challenge there is not
gate quality but **scale and loss**: the architecture targets a
loss-per-photon threshold around $2.7\%$ for its baseline design, with more
advanced adaptive schemes modelled up to about $18.8\%$.

The Xanadu figures show the opposite problem. The GKP states are real and
on-chip, but the achieved effective squeezing of $0.62$ dB sits about $9$ dB
below the $9.75$ dB threshold. Reported loss figures likewise run from tens of
percent on the path towards below $1\%$ required. That is a large but
concretely specified gap, not a vague one.

## Limitations

- **Loss dominates everything.** Per-component efficiency must be pushed very
  high because the cost is exponential in the number of components.
- **Probabilistic gates need overhead.** Even with KLM-style boosting, the
  ancilla cost is large, and multiplexing — trying many times in parallel and
  switching in a success — adds switching loss of its own.
- **No memory.** Photons travel at the speed of light and cannot be parked. Delay
  lines and fibre loops are the only storage, and they lose photons.
- **Sources are probabilistic.** Spontaneous parametric down-conversion produces
  photon pairs at random times; multiplexing many sources is needed to
  approximate an on-demand source.
- **GKP is demanding.** Useful GKP states need roughly $10$–$12$ dB of squeezing,
  which is at or beyond current hardware limits.
- **Detectors must be excellent and numerous.** Photon-number resolution, high
  efficiency, and low dark counts, at scale.

## Common misconceptions

- **"Photons don't interact, so photonic quantum computing is impossible."**
  Linear optics plus post-selection plus ancillas gives effective interactions.
  They are probabilistic, not impossible.
- **"Photonic qubits have no decoherence, so they have no errors."** They have
  no decoherence *in the $T_1/T_2$ sense*. They have loss, which is worse
  because it is exponential in circuit size.
- **"A probabilistic gate is useless."** A *heralded* failure — one you know
  about — can be routed around, retried, or treated as an erasure. An
  unheralded failure is the dangerous kind.
- **"Loss is just another error rate to plug into the threshold theorem."**
  Loss is leakage out of the computational subspace. Standard stabiliser
  formalism handles Pauli errors; photonic codes need explicit loss handling.
- **"Single-photon and GKP machines are just two implementations of the same
  idea."** They are different architectures with different error models,
  different dominant noise, and very different gaps to fault tolerance.
- **"99% component efficiency is good enough."** Ten components in series give
  $0.90$; a hundred give $0.37$; a thousand give $4\times10^{-5}$.

## Exercises

1. Explain why a beam splitter implements a deterministic single-qubit gate on
   a dual-rail qubit but not a two-qubit gate.

2. Compute the $|1,1\rangle$ output amplitude of a beam splitter with
   reflectivity $R = 0.3$, and the probability of that outcome.

3. A photonic circuit requires a photon to pass through 200 components, each
   with transmission $0.995$. What is the survival probability? What per-component
   efficiency would you need for the survival probability to exceed $0.9$?

4. Why is a *heralded* photon loss much easier to handle than an unheralded
   one?

5. Using $p = n^2/(n+1)^2$, how many ancilla photons are needed for a success
   probability of at least $0.9$?

6. Name two reasons loss is a harder error channel than the $T_1$ decay of a
   superconducting qubit.

### Answers to 1–3

**1.** A dual-rail qubit is the one-photon subspace of two modes, and a beam
splitter conserves photon number, so a one-photon input can only produce a
one-photon output — it cannot leave the computational subspace, and no
post-selection is needed. Verified: the leakage is zero to numerical precision
at every reflectivity. A two-qubit gate needs the photons to become entangled,
which requires an effective photon–photon interaction; linear optics supplies
that only through interference and post-selection, and the wanted outcome is
only one of several possibilities.

**2.** The amplitude is $t^2 - r^2 = (1-R) - R = 1 - 2R = 1 - 0.6 = 0.4$. The
probability of the $|1,1\rangle$ outcome is $(1-2R)^2 = 0.16$, confirmed by the
verified table at neighbouring reflectivities.

**3.** Survival is $\eta^N = 0.995^{200}$:

$$0.995^{200} = e^{200\ln 0.995} = e^{200(-0.005013)} = e^{-1.0025} \approx 0.367$$

so about $37\%$. For survival above $0.9$ over 200 components you need
$\eta^{200} > 0.9$, so $\eta > 0.9^{1/200} = e^{\ln(0.9)/200} = e^{-0.000527} \approx 0.999473$ — better than $99.95\%$ per component.

### Answers to 4–6

**4.** A heralded loss tells you *where and when* the qubit disappeared. That
converts an unknown error into an **erasure**: you know exactly which qubit is
missing, and erasure-correcting codes are substantially more efficient than
codes that must locate and identify an unknown error. An unheralded loss leaves
you computing on a state that silently lacks a photon, and the resulting error
propagates without any signal.

**5.** Solve $n^2/(n+1)^2 \geq 0.9$, i.e. $n/(n+1) \geq \sqrt{0.9} = 0.9487$, so
$n \geq 0.9487n + 0.9487$, giving $0.0513n \geq 0.9487$ and $n \geq 18.5$. So
$n = 19$, which from the verified table sits between $n = 10$ ($p = 0.826$) and
$n = 20$ ($p = 0.907$). That means **38 ancilla photons** for a single gate
success probability above $90\%$.

**6.** Any two of: loss is exponential in the number of components ($\eta^N$)
whereas $T_1$ decay contributes roughly linearly to the total error budget over
a fixed circuit; loss removes the qubit from the computational subspace
entirely, so a Pauli-error stabiliser code cannot detect it without explicit
loss handling; a lost photon cannot be reset and reused, whereas a relaxed
superconducting qubit is still a working qubit; and loss compounds with
*distance*, so delay lines and fibre storage actively degrade the qubit.

## Summary

- Photons do not decohere — there is no $T_1$ or $T_2$. The error channel is
  **loss**, and it is exponential in the number of components.
- Encodings include **dual-rail** ($|0\rangle_L = |1,0\rangle$,
  $|1\rangle_L = |0,1\rangle$), **polarisation**, **time-bin**, and
  **bosonic/GKP** continuous-variable states.
- **Single-qubit gates are deterministic**: verified by exact Fock-space
  simulation, a beam splitter has zero leakage from the one-photon subspace and
  induces a unitary on the dual-rail qubit at every reflectivity.
- **Two-qubit gates are probabilistic**, because photons do not interact. The
  Hong–Ou–Mandel effect supplies an effective interaction by interference —
  verified: the $|1,1\rangle$ amplitude is $1-2R$, vanishing exactly at
  $R = 1/2$ — and the gate is obtained by post-selection.
- KLM boosts the success probability to $p = n^2/(n+1)^2$ using $2n$ ancilla
  photons: $1/4$ at $n=1$, $0.98$ at $n=100$. Near-deterministic gates cost
  photons.
- **Loss is worse than an equivalent gate error** because it is exponential
  ($\eta^N$), it is leakage rather than a Pauli error, and it destroys the
  qubit. Heralded loss is an erasure and is far easier to correct than
  unheralded loss.
- Vendor figures are snapshots: PsiQuantum reports $99.22\%$ fusion fidelity
  with a loss threshold around $2.7\%$ per photon; Xanadu's on-chip GKP states
  reach $0.62$ dB of effective squeezing against a $9.75$ dB threshold. Both
  gaps are large but concretely specified.

## References

- Knill, E., Laflamme, R. & Milburn, G. J., "A scheme for efficient quantum
  computation with linear optics" (Nature, 2001) — the KLM scheme and the
  $p = n^2/(n+1)^2$ scaling.
- Hong, C. K., Ou, Z. Y. & Mandel, L., "Measurement of subpicosecond time
  intervals between two photons by interference" — the HOM effect.
- Kok, P. et al., "Linear optical quantum computing with photonic qubits"
  (Reviews of Modern Physics) — a full review of encodings and gates.
- Gottesman, D., Kitaev, A. & Preskill, J., "Encoding a qubit in an oscillator"
  — the GKP code.
- Bartlett, S. D., Sanders, B. C., Braunstein, S. L. & Nemoto, K. — efficient
  classical simulation of linear optics under a Gaussian-error model.
- Browne, D. E. & Rudolph, T., "Resource-efficient linear optical quantum
  computation" — fusion-based approaches.
- Bourassa, J. E. et al. (PsiQuantum), "Blueprint for a scalable photonic
  fault-tolerant quantum computer" — fusion-based QC and loss thresholds.
- PsiQuantum, "Omega chipset" (Nature, February 2025) — integrated silicon
  photonics figures quoted above.
- Xanadu, Borealis (Nature, 2022) and on-chip GKP qubits (Nature, 2025) — the
  continuous-variable results quoted above.
- [Trapped Ions](57_trapped_ions.md) — the preceding platform.
- [Neutral Atoms](59_neutral_atoms.md) — the next platform.
- [Quantum Networks](67_quantum_networks.md) — where photonics is the only
  option.
- [Surface Codes](52_surface_codes.md) — the error-correction context, and why
  loss needs handling beyond the Pauli formalism.

---

**Next:** [Neutral Atoms](59_neutral_atoms.md)
