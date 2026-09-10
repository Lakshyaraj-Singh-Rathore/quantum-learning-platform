<!-- track: theory -->
# Quantum Noise and Decoherence

Every circuit you have run so far was **perfect**. Real quantum hardware is not.
This lesson explains what goes wrong, why, and how to see it in this platform.

## Why noise is the central problem

A classical bit sitting in a memory cell will hold its value for years. A qubit
holding a superposition loses it in **microseconds**. That is the entire
difficulty of building a quantum computer: the thing that makes qubits powerful
(superposition and entanglement) is also extraordinarily fragile.

The qubit is not isolated. It is coupled to its surroundings: stray photons,
vibrating atoms, magnetic fields, the control wiring itself. Every one of those
couplings leaks information about the qubit into the environment. Once the
environment "knows" whether the qubit is 0 or 1, the superposition is gone.

That leaking process is called **decoherence**.

## The two timescales: T1 and T2

Hardware vendors quote two numbers for every qubit.

### T1 — energy relaxation (amplitude damping)

A qubit in the excited state $|1\rangle$ has more energy than $|0\rangle$. Left
alone, it eventually dumps that energy into its environment and falls to
$|0\rangle$ — exactly like an excited atom emitting a photon.

The probability of *still* being excited after time $t$ decays exponentially:

$$P_1(t) = e^{-t/T_1}$$

$T_1$ is the time constant. **This process is directional**: it pushes states
toward $|0\rangle$, never toward $|1\rangle$. That asymmetry is visible in
results — a noisy Bell state does not degrade into a uniform mush, it
degrades preferentially toward $|00\rangle$.

### T2 — dephasing

$T_2$ describes how long the qubit keeps its **phase**. This is the subtler and
usually the more damaging effect.

Consider $|+\rangle = \tfrac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$. The relative
phase between the two terms is 0. If the qubit's energy levels fluctuate even
slightly, that phase drifts randomly. Average over many shots and the phase is
uniformly random, which means the interference that quantum algorithms depend on
is destroyed.

Crucially, **dephasing changes no measurement probabilities in the Z basis**.
$|+\rangle$ and a fully dephased mixture both give 50/50 on a Z measurement. You
only detect the damage when you interfere the state — for example by applying a
second Hadamard, which should return exactly $|0\rangle$ and, after dephasing,
does not.

### The relationship $T_2 \le 2T_1$

Energy relaxation also destroys phase, so $T_2$ can never exceed $2T_1$. This is
a hard physical bound. **The platform enforces it**: set $T_2 > 2T_1$ in the
Composer and it is clamped, with a warning.

## The standard noise channels

Beyond T1/T2, noise is often described with idealised channels.

| Channel | What it does | Typical cause |
|---|---|---|
| **Bit flip** | applies $X$ with probability $p$ | control error, stray excitation |
| **Phase flip** | applies $Z$ with probability $p$ | frequency drift |
| **Depolarizing** | with probability $p$, replaces the state with a random one | catch-all model |
| **Amplitude damping** | $|1\rangle \to |0\rangle$ with probability $\gamma$ | this is T1 |
| **Phase damping** | randomises phase, leaves populations alone | this is T2 |

Amplitude and phase damping are the physically realistic pair; depolarizing is a
convenient worst-case approximation used in error-correction proofs.

## Readout error is different

The three effects above corrupt the **quantum state**. Readout error does not.

Measurement hardware distinguishes $|0\rangle$ from $|1\rangle$ by a noisy
analogue signal, and sometimes gets it wrong. The state was correct; the
*reported bit* is wrong.

This distinction matters for interpreting results:

- Readout error changes your **histogram** but not the state fidelity.
- T1/T2 change the **actual state**, so both fidelity and histogram move.

In this platform you can verify that yourself: set T1 and T2 enormously high and
readout error to 20%. Fidelity stays at ~1.000 while counts leak badly.

## Reading the meters

When noise is enabled, the results page shows three dials.

- **Entanglement S** — single-qubit von Neumann entropy in bits. 0 means
  separable, 1 means maximally entangled. This is computed on the *ideal* state.
- **Fidelity** — $F(|\psi_{\text{ideal}}\rangle, \rho_{\text{noisy}})$. How much
  of the intended state survived. 1.000 is perfect.
- **Purity** — $\mathrm{Tr}(\rho^2)$. 1.0 means the state is still pure (a
  definite quantum state). Lower means it has become a statistical *mixture* —
  the signature of decoherence. For one fully decohered qubit, purity bottoms
  out at 0.5.

Fidelity and purity answer different questions. A state can be pure but wrong
(a coherent error), or partly mixed but still mostly overlapping the target.

Two further numbers appear below:

- **TV distance** — total variation between the ideal and noisy distributions,
  i.e. the largest probability error you could observe.
- **Shot leakage** — the fraction of shots landing on outcomes that should have
  had essentially zero probability.

## Why virtual-Z gates are free

You will notice that $Z$, $S$, $T$ and $RZ$ pick up **no** thermal error in the
simulation. That is not a simplification — it reflects real hardware.

A $Z$-type rotation does not require a physical pulse. The control system simply
redefines the phase reference for all subsequent pulses on that qubit. This is
called a **virtual Z gate**, it takes zero time, and it is essentially
error-free. $X$ and $Y$ rotations need actual microwave pulses and so do
accumulate decoherence.

This is why hardware-efficient circuits are decomposed to push as much work as
possible into virtual-Z gates.

## Try it

Open the **Composer**, build a Bell pair (H on q0, then CNOT q0 to q1), and open
the **Noise model** panel.

1. **Baseline.** Run with noise off. Fidelity 1.000, purity 1.000, only
   $|00\rangle$ and $|11\rangle$ appear.
2. **Readout only.** Enable noise, set T1 and T2 to 200 microseconds, readout to
   15%. The forbidden states $|01\rangle$ and $|10\rangle$ now appear, but
   fidelity stays near 1.000 — the state was fine, the reporting was not.
3. **Decoherence.** Set T1 = 5, T2 = 4, readout back to 0%. Watch purity fall
   below 1 and the distribution skew toward $|00\rangle$ as T1 relaxation drags
   population downward.
4. Open the **Ideal vs noisy** tab to see both histograms side by side, and the
   difference plot underneath.

## A caution about these numbers

The noise model here is a **teaching approximation with parameters you choose**.
It is not calibration data from any particular quantum computer. Real devices
have per-qubit T1 and T2 that vary across the chip and drift hour to hour,
crosstalk between neighbouring qubits, and correlated errors that this
independent-error model does not capture.

The physics of the trends is right. The specific numbers are yours.
