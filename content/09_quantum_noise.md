<!-- track: theory -->
# Quantum Noise and Decoherence

Every circuit you have run so far was **perfect**. Real quantum hardware is not.
This lesson explains what goes wrong, why, and how to see it in this platform.

## Learning objectives

By the end of this lesson you should be able to:

- **Explain** decoherence as information leaking into the environment.
- **Distinguish** T1 (energy relaxation) from T2 (dephasing) and predict how
  each one distorts a Bell state.
- **State** the bound $T_2 \le 2T_1$ and explain why this platform clamps it.
- **Compare** the standard noise channels and say which are physically realistic.
- **Interpret** the fidelity, purity, TV distance and shot-leakage meters.
- **Explain** why readout error changes your histogram but not your fidelity,
  and why virtual-Z gates accumulate no thermal error.

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

$T_1$ is the time constant. **This process is directional**: it pushes states toward $|0\rangle$, never toward $|1\rangle$. That asymmetry is visible in results — a noisy Bell state does not degrade into a uniform mush, it degrades preferentially toward $|00\rangle$.

### T2 — dephasing

$T_2$ describes how long the qubit keeps its **phase**. This is the subtler and usually the more damaging effect. Consider $|+\rangle = \tfrac{1}{\sqrt{2}}(|0\rangle + |1\rangle)$. The relative phase between the two terms is 0. If the qubit's energy levels fluctuate even slightly, that phase drifts randomly. Average over many shots and the phase is uniformly random, which means the interference that quantum algorithms depend on is destroyed. Crucially, **dephasing changes no measurement probabilities in the Z basis**. $|+\rangle$ and a fully dephased mixture both give 50/50 on a Z measurement. You only detect the damage when you interfere the state — for example by applying a second Hadamard, which should return exactly $|0\rangle$ and, after dephasing, does not.

### The relationship $T_2 \le 2T_1$

Energy relaxation also destroys phase, so $T_2$ can never exceed $2T_1$. This is a hard physical bound. Note the factor of 2: pure dephasing adds to the decoherence rate as

$$\frac{1}{T_2} = \frac{1}{2T_1} + \frac{1}{T_\phi}$$

so even with no dephasing at all ($T_\phi \to \infty$), the slowest possible
decoherence still leaves $T_2 = 2T_1$.

**The platform enforces this.** Set $T_2 > 2T_1$ and it is clamped, with a
warning. Verified: $T_1 = 5\,\mu$s with $T_2 = 100\,\mu$s produces
`T2 clamped to 2*T1 = 10 us (physical limit)`. The region $T_1 < T_2 < 2T_1$ is
legal and is left alone — Aer raises on a violation, so clamping keeps a run
alive with an explanation instead of an error.

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

**Verified on a Bell pair**, 2048 shots, seed 1234:

| Setting | Counts | Fidelity | Purity |
|---------|--------|----------|--------|
| Clean | `00`: 1022, `11`: 1026 | 1.000 | 1.000 |
| Readout 15%, T1/T2 huge | `00`: 791, `01`: 241, `10`: 255, `11`: 761 | **1.000** | 1.000 |
| T1 = 5, T2 = 4, no readout error | `00`: 1049, `01`: 56, `10`: 73, `11`: 870 | **0.864** | 0.759 |

The second row is the lesson: the forbidden states $|01\rangle$ and $|10\rangle$
now appear in large numbers, but fidelity stays at 1.000 — the state was fine,
the *reporting* was not. In the third row the state itself degraded, so both
fidelity and purity fell, and the distribution skewed toward $|00\rangle$ as T1
relaxation dragged population downward.

## Reading the meters

When noise is enabled, the results page shows several gauges.

- **Entanglement S** — single-qubit von Neumann entropy in bits. 0 means
  separable, 1 means maximally entangled. This is computed on the *ideal* state.
- **Fidelity** — $F(|\psi_{\text{ideal}}\rangle, \rho_{\text{noisy}})$. How much
  of the intended state survived. 1.000 is perfect.
- **Purity** — $\mathrm{Tr}(\rho^2)$. 1.0 means the state is still pure (a
  definite quantum state). Lower means it has become a statistical *mixture* —
  the signature of decoherence.
- **TV distance** — total variation between the ideal and noisy distributions,
  i.e. the largest probability error you could observe.
- **Shot leakage** — the fraction of shots landing on outcomes that should have
  had essentially zero probability.

Fidelity and purity answer different questions. A state can be pure but wrong
(a coherent error), or partly mixed but still mostly overlapping the target.

### Purity does not always fall

This surprises people, so it is worth stating precisely. Purity bottoms out at
0.5 for a single qubit that has been **fully dephased** — the maximally mixed
state $\rho = I/2$ has $\mathrm{Tr}(\rho^2) = \tfrac12$.

But T1 relaxation alone does the opposite: it drives the qubit into $|0\rangle$,
which is a **pure** state. Verified on $|+\rangle$:

| Regime | Purity | Fidelity |
|--------|--------|----------|
| T1 = 0.1 $\mu$s, T2 = 0.1 $\mu$s | 0.767 | 0.684 |
| T1 = 0.01 $\mu$s, T2 = 0.01 $\mu$s | **1.000** | 0.500 |
| T1 huge, T2 = 0.1 $\mu$s (pure dephasing) | 0.568 | 0.684 |
| T1 huge, T2 = 0.01 $\mu$s (full dephasing) | **0.500** | 0.500 |

So "purity falls below 1" is a signature of **mixing**, and mixing is what
dephasing does. Strong relaxation instead produces a pure-but-wrong state:
purity returns to 1.0 while fidelity drops to 0.5. Always read the two meters
together; neither alone tells you what happened.

## Why virtual-Z gates are free

You will notice that $Z$, $S$, $T$ and $RZ$ pick up **no** thermal error in the
simulation. That is not a simplification — it reflects real hardware.

A $Z$-type rotation does not require a physical pulse. The control system simply
redefines the phase reference for all subsequent pulses on that qubit. This is
called a **virtual Z gate**, it takes zero time, and it is essentially
error-free. $X$ and $Y$ rotations need actual microwave pulses and so do
accumulate decoherence.

Verified in the source: the noise model treats `z`, `s`, `sdg`, `t`, `tdg`, `rz`
and `p` as zero-duration, while `h`, `x`, `y`, `rx`, `ry`, `sx` and all
multi-qubit gates accumulate T1/T2 error.

This is why hardware-efficient circuits are decomposed to push as much work as
possible into virtual-Z gates.

## Practical example

```python
from app.quantum.ir import CircuitIR, Op
from app.quantum.noise import NoiseParams
from app.quantum.backends import qiskit_aer

def bell():
    ir = CircuitIR(name="bell", n_qubits=2, n_clbits=2)
    ir.place(Op(kind="gate", gate="h", qubits=[0]), 0)
    ir.place(Op(kind="gate", gate="cx", qubits=[0, 1]), 1)
    ir.place(Op(kind="measure", qubits=[0], clbits=[0]), 2)
    ir.place(Op(kind="measure", qubits=[1], clbits=[1]), 2)
    return ir

def run(noise, shots=2048):
    result = qiskit_aer.run(bell(), shots=shots, noise=noise, seed=1234)
    m = result["metadata"]["metrics"]
    return (dict(sorted(result["counts"].items())),
            round(m["fidelity"], 4), round(m["purity"], 4))

# T2 above 2*T1 is clamped, not rejected
params, notes = NoiseParams(enabled=True, t1_us=5.0, t2_us=100.0).clamped()
print(notes)                      # ['T2 clamped to 2*T1 = 10 us (physical limit).']
print("clamped t2:", params.t2_us)  # 10.0

# Readout error corrupts the histogram but not the state
print(run(NoiseParams(enabled=True, t1_us=1e6, t2_us=1e6, readout_error=0.15)))
# ({'00': 791, '01': 241, '10': 255, '11': 761}, 1.0, 1.0)

# T1/T2 corrupt the state itself
print(run(NoiseParams(enabled=True, t1_us=5.0, t2_us=4.0, readout_error=0.0)))
# ({'00': 1049, '01': 56, '10': 73, '11': 870}, 0.8645, 0.7586)
```

**Try it.** Open the **Composer**, build a Bell pair (H on q0, then CNOT q0 to
q1), and open the **Noise model** panel.

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

## Common misconceptions

- **"Noise just adds random jitter to the answer."** T1 is directional, not
  random: it pushes population toward $|00\rangle$. Verified above.
- **"Low purity always means heavy noise."** Strong relaxation produces a
  pure-but-wrong state. Purity tracks *mixing*, not *error*.
- **"Fidelity 1.0 means my circuit is fine."** With readout error at 15% your
  fidelity is 1.000 and your histogram is badly wrong. Check both.
- **"T2 is always less than T1."** The physical bound is $T_2 \le 2T_1$. Values
  in $T_1 < T_2 < 2T_1$ are legal.

## Exercises

**1.** A qubit starts in $|1\rangle$. What is the probability it is still in
$|1\rangle$ after $t = T_1$? After $t = 3T_1$?

**2.** You set $T_1 = 10\,\mu$s and $T_2 = 30\,\mu$s. What does the platform do,
and what value is used?

**3.** Why does a Z-basis measurement fail to reveal dephasing?

**4.** A run reports fidelity 0.95 and purity 1.000. Is the state mixed? What
kind of error does this suggest?

**5.** Why does `rz(pi/4)` accumulate no thermal error while `rx(pi/4)` does?

### Answers

**1.** $P_1(T_1) = e^{-1} \approx 0.368$. After $3T_1$: $e^{-3} \approx 0.0498$.

**2.** The bound is $T_2 \le 2T_1 = 20\,\mu$s, and $30 > 20$, so $T_2$ is
**clamped to 20 $\mu$s** with the note `T2 clamped to 2*T1 = 20 us (physical
limit)`. The run continues rather than erroring.

**3.** Dephasing randomises the relative phase between $|0\rangle$ and
$|1\rangle$, and Z-basis probabilities depend only on $|\alpha|^2$ and
$|\beta|^2$, not on phase. You must interfere the branches (for example with a
second Hadamard) to convert the phase damage into a population difference.

**4.** Purity 1.000 means the state is **not** mixed — it is still a definite
quantum state, just not the one you intended. That is the signature of a
**coherent** error, such as a slightly miscalibrated rotation angle.

**5.** `rz` is a **virtual-Z** gate: hardware implements it by redefining the
phase reference rather than applying a microwave pulse, so it takes zero time
and picks up no thermal error. `rx` requires a real pulse, during which T1 and T2
decay act.

## Summary

- Decoherence is information leaking from the qubit into its environment.
- T1 is energy relaxation ($|1\rangle \to |0\rangle$, directional); T2 is
  dephasing (randomises phase, leaves populations alone).
- The bound is $T_2 \le 2T_1$; this platform clamps violations with a warning.
- Readout error corrupts the reported bit, not the state — fidelity stays at
  1.000 while the histogram degrades.
- Purity 0.5 is the floor for a *fully dephased* qubit; strong relaxation
  instead gives a pure-but-wrong state with purity back at 1.0.
- Virtual-Z gates (`z`, `s`, `t`, `rz`, `p`) take zero time and accumulate no
  thermal error.

Next, **[Dynamic Circuits](08_dynamic_circuits.md)** shows the measurement-based
feedback that error correction is built on.

## References

- Nielsen, M. A. & Chuang, I. L. *Quantum Computation and Quantum Information*,
  10th Anniversary Edition, Cambridge University Press (2010), §8.3–8.4.
- Krantz, P. et al. "A quantum engineer's guide to superconducting qubits",
  *Applied Physics Reviews* 6 (2019) 021318.
- Qiskit documentation, "Noise models and AerSimulator":
  https://docs.quantum.ibm.com/
- Qiskit 1.2.4 release notes: https://docs.quantum.ibm.com/api/qiskit/release-notes
