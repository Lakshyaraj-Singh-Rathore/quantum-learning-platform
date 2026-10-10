# Calibrated Noise Models and Connectivity Topologies

Every platform lesson so far has quoted fidelity and coherence numbers. This
lesson is about what those numbers actually are: entries in a **calibration
file**, measured on a specific device, on a specific day. And it is about the
second thing that separates platforms — **which qubits can talk to which** —
which matters at least as much as the error rates and is far less often
quantified.

The goal is to be able to take a workload and say, defensibly, which platform
it belongs on.

## Learning objectives

By the end of this lesson you should be able to:

- **Read** a calibrated noise model for a device.
- **Compare** connectivity topologies across platforms.
- **Choose** a platform appropriate to a given workload.

## Prerequisites

[Superconducting Qubits](56_superconducting_qubits.md) (**required**) — needs at
least one concrete platform to calibrate against.
[Trapped Ions](57_trapped_ions.md) (recommended) — a comparison that has seen
only one platform compares nothing; trapped ions are the contrasting case of
all-to-all connectivity.

## What a calibration file contains

A superconducting device is characterised by a daily calibration run that
reports, per qubit and per gate, a set of numbers. Reading one means knowing
what each column means and what it does *not* tell you.

| Quantity | What it is | What it does not tell you |
|---|---|---|
| $T_1$ | Energy relaxation time | Anything about gate quality |
| $T_2$ | Coherence (dephasing) time | Whether the qubit is well controlled |
| Frequency | Qubit transition frequency | — but crowding causes crosstalk |
| Anharmonicity | Deviation from a perfect two-level system | — low values mean leakage risk |
| Readout error | Probability of a wrong measurement | Whether errors are biased |
| 1q gate error | Average single-qubit gate infidelity | Which gate, or whether it drifts |
| 2q gate error | Average entangling-gate infidelity | Whether errors are correlated |
| Gate duration | How long the gate takes | — but it sets the error floor |
| Coupling map | Which pairs have a native 2q gate | Whether those gates are all usable |

Two traps catch people reading these files.

**The mean hides the outliers.** A device with median readout error $1.17\%$ and
worst-case $35.75\%$ has a handful of genuinely bad qubits. Any average-fidelity
figure computed from the median is optimistic.

**Averages hide correlations.** Standard randomised benchmarking reports an
average error per gate. It does not tell you whether errors on neighbouring
qubits are correlated — and correlated errors are exactly what
[error correction](52_surface_codes.md) is least able to handle.

### Verified: a real calibration snapshot

Reading the calibration data shipped with a 127-qubit superconducting device
(snapshot dated 2024-05-27):

| Quantity | Median | Best | Worst |
|---|---|---|---|
| $T_1$ | $279.6$ μs | $458.8$ μs | $40.9$ μs |
| $T_2$ | $197.8$ μs | $423.3$ μs | $16.9$ μs |
| Readout error | $1.17\%$ | $0.33\%$ | $35.75\%$ |
| Two-qubit gate error | $0.80\%$ | $0.36\%$ | $7.40\%$ |
| Single-qubit gate error | $0.021\%$ | — | — |

| Quantity | Value |
|---|---|
| Two-qubit gate duration | $533$ ns |
| Single-qubit gate duration | $57$ ns |
| Native two-qubit gate | ECR (echoed cross-resonance), not CNOT |
| Qubit frequency (median) | $4.79$ GHz |

### What the file does not say on its face

Four things a practised reader extracts from this file beyond the headline
fidelity.

**The $T_2/T_1$ ratio is $0.752$, not 2.** For a qubit limited only by energy
relaxation, $T_2 = 2T_1$. A ratio below 2 means additional pure dephasing. At
$0.752$ the qubit is dephasing-limited by a wide margin — $T_2$ is *shorter than
$T_1$*, which is only possible when dephasing dominates. That points at noise the
calibration is not otherwise reporting.

**The native gate is ECR, not CNOT.** Any circuit compiled to this device is
decomposed into ECR plus single-qubit rotations. A CNOT costs at least one ECR,
so the "0.80% two-qubit error" is not the cost of a CNOT — it is the cost of the
native operation, and the logical CNOT you wrote costs more.

**Single-qubit gates are 250× better than two-qubit gates** ($0.021\%$ against
$0.80\%$) and **9× faster** ($57$ ns against $533$ ns). This asymmetry is the
single most important fact for compiling to this hardware: it is almost always
worth spending single-qubit gates to avoid two-qubit ones.

**The worst qubit is 10× worse than the median** on readout and $9\times$ on
two-qubit gates. Qubit selection — picking which physical qubits to use — is a
real optimisation with real gains, and it is why transpilers take the coupling
map *and* the error map as input.

### From a calibration file to a noise model

The file becomes usable when it is turned into a **noise model**: a set of
quantum channels attached to each gate and each qubit. Qiskit builds one
directly from a backend:

```python
import warnings
warnings.filterwarnings('ignore')   # qiskit 1.2 deprecates qiskit.providers.models,
                                    # which fake_provider still imports internally
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit_aer.noise import NoiseModel

backend = GenericBackendV2(num_qubits=16,
                           coupling_map=[(i, i + 1) for i in range(15)],
                           seed=7,
                           basis_gates=['cx', 'id', 'rz', 'sx', 'x'])
noise_model = NoiseModel.from_backend(backend)

print(noise_model.noise_instructions)   # which operations carry noise
print(len(noise_model.noise_qubits))    # how many qubits are noisy
```

The resulting model attaches thermal-relaxation channels (from $T_1$ and $T_2$),
depolarising channels (from the measured gate errors), and readout errors to the
corresponding operations. That is what a simulator needs in order to predict how
a circuit will actually behave.

What it does **not** include: crosstalk, correlated errors, drift between
calibration runs, and leakage. A simulation using a calibrated noise model is
consistently optimistic.

## Connectivity topologies

The second axis of comparison is which pairs of qubits have a native two-qubit
gate. Four topologies cover the platforms in this section:

| Topology | Structure | Typical platform |
|---|---|---|
| **All-to-all** | Every pair connected | [Trapped ions](57_trapped_ions.md) (within a chain) |
| **2D grid / lattice** | Nearest neighbours in a plane | [Neutral atoms](59_neutral_atoms.md), some superconducting |
| **Heavy-hex** | Degree ≤ 3, hexagon-tiled | IBM superconducting |
| **Line / ring** | Nearest neighbour along a chain | [Spin qubits](60_spin_qubits.md) |

Three quantitative metrics:

- **Degree** — how many direct neighbours each qubit has.
- **Diameter** — the longest shortest path between any two qubits.
- **Mean shortest path** — the average number of hops between two qubits.

On the 127-qubit device above:

| Metric | This device | All-to-all on 127 qubits |
|---|---|---|
| Edges | $144$ | $8001$ |
| Mean degree | $2.27$ | $126$ |
| Max degree | $3$ | $126$ |
| Diameter | $26$ | $1$ |
| Mean shortest path | $11.13$ | $1$ |

**This device has $1.80\%$ of the edges of an all-to-all machine.** Two qubits
chosen at random are, on average, eleven hops apart. That is the number to hold
in mind when comparing platforms: the difference is not a factor of two, it is
a factor of fifty.

The heavy-hex structure — max degree 3 — is a deliberate choice, not a
limitation of lithography. Lower degree means less crosstalk between
simultaneous gates and fewer frequency collisions, and for
[surface codes](52_surface_codes.md) it is sufficient: the code only ever needs
nearest-neighbour interactions. Connectivity is traded for gate quality on
purpose.

### Verified: what sparse connectivity costs

The honest way to measure this is to compile the same circuit onto each
topology and count. Using a QFT — a circuit that needs gates between nearly
every pair, so it is close to a worst case — with identical optimisation level
and seed:

| $n$ | All-to-all | Grid | Ring | Line |
|---|---|---|---|---|
| 9 | 72 | 123 | 171 | 165 |
| 16 | 240 | 462 | 645 | 588 |
| 25 | 600 | 1191 | 1494 | 1485 |

Two-qubit gate count, and the same circuits' depth:

| $n$ | All-to-all | Grid | Ring | Line |
|---|---|---|---|---|
| 9 | 61 | 165 | 163 | 162 |
| 16 | 117 | 417 | 428 | 358 |
| 25 | 189 | 694 | 601 | 591 |

### Expressed as a ratio

Expressed as a ratio against all-to-all:

| $n$ | Grid (gates) | Line (gates) | Grid (depth) | Line (depth) |
|---|---|---|---|---|
| 9 | 1.71× | 2.29× | 2.70× | 2.66× |
| 16 | 1.93× | 2.48× | 3.56× | 3.06× |
| 25 | 1.99× | 2.48× | 3.67× | 3.13× |

**Depth matters more than gate count**, because errors accumulate with circuit
depth. On depth, a line costs about **3× all-to-all** for this workload, and the
ratio grows with $n$: $2.66\times$ at $n=9$, $3.13\times$ at $n=25$.

Now the interesting part. A naive estimate would predict far worse. On a line,
the mean distance between two random qubits is $(n+1)/3$ — so $3.33$ hops at
$n=9$, $8.67$ at $n=25$ — and each hop is a SWAP, and each SWAP is three CNOTs.
That gives about $10$ CNOTs per logical gate at $n=9$ and $26$ at $n=25$, against
$1$ for all-to-all.

**The measured cost is 2.5×, not 26×.** The naive model is wrong by an order of
magnitude because real transpilers do not route one gate at a time: they reorder
operations, keep qubits near their partners, and amortise a single SWAP across
several gates.

That is a genuinely useful correction, and it cuts both ways. Connectivity
advantage is real — a factor of 3 on depth is a lot — but it is not the
order-of-magnitude effect that naive SWAP-counting suggests. Published estimates
of $3$–$10\times$ are in the right range and sit at the upper end of what
compilation actually recovers.

### Reproducing the table

```python
import warnings
warnings.filterwarnings('ignore')
import numpy as np
from qiskit import transpile
from qiskit.circuit.library import QFT
from qiskit.transpiler import CouplingMap


def line_cmap(n):
    return CouplingMap([(i, i + 1) for i in range(n - 1)])


def grid_cmap(n):
    s = int(np.sqrt(n))
    return CouplingMap([(r * s + c, r * s + c + 1)
                        for r in range(s) for c in range(s - 1)]
                       + [(r * s + c, (r + 1) * s + c)
                          for r in range(s - 1) for c in range(s)])


def ring_cmap(n):
    return CouplingMap([(i, (i + 1) % n) for i in range(n)])


def all_to_all_cmap(n):
    return CouplingMap([(i, j) for i in range(n) for j in range(i + 1, n)])


def two_qubit_count(qc):
    ops = qc.count_ops()
    return sum(ops.get(g, 0) for g in ("cx", "cz", "ecr", "swap"))


print(f"{'n':>4s}  {'topology':<12s}{'2q gates':>10s}{'depth':>8s}{'vs a2a':>10s}")
for n in (9, 16, 25):
    base = QFT(n, do_swaps=False).decompose()
    counts = {}
    for name, cm in (("all-to-all", all_to_all_cmap(n)), ("grid", grid_cmap(n)),
                     ("ring", ring_cmap(n)), ("line", line_cmap(n))):
        t = transpile(base, coupling_map=cm, optimization_level=1,
                      seed_transpiler=42, basis_gates=["u", "cx"])
        counts[name] = two_qubit_count(t)
        ratio = counts[name] / counts["all-to-all"]
        print(f"{n:>4d}  {name:<12s}{counts[name]:>10d}{t.depth():>8d}{ratio:>9.2f}x")
    print()
```

## Choosing a platform

Now the point of the lesson. Given a workload, which platform?

### The four platforms side by side

The four platforms covered in this section, on the axes that matter:

| | Superconducting | Trapped ions | Neutral atoms | Spin qubits |
|---|---|---|---|---|
| Two-qubit gate | $\sim 100$–$300$ ns | $\sim 100$ μs | $\sim 0.5$ μs | $\sim 10$–$100$ ns |
| Coherence | $100$–$350$ μs | Seconds to minutes | Seconds | ms (electron), s (nuclear) |
| Best 2q fidelity | $\sim 99.9\%$ | $99.99\%$ | $99.5\%$ | $99.99\%$ |
| Connectivity | Nearest-neighbour, degree $\le 3$ | All-to-all | Local, reconfigurable | Nearest-neighbour |
| Scale demonstrated | $>1000$ | $\sim 100$ | Thousands | Tens |
| Fabrication | Lithography | None — atoms | None — atoms | Lithography |
| Distinctive error | Crosstalk, drift | Slow gates | Atom loss (heralded) | Charge noise |

Read that table as a set of trade-offs, not a ranking. There is no best
platform; there are workloads.

### Choose by asking what binds

**Choose by asking which resource binds.**

*Circuit depth is binding* — you need many sequential gates before the state
decays. Compare $T_2/t_g$: roughly $10^3$ for superconducting, roughly $10^4$ for
trapped ions. Ions win by about an order of magnitude. But if your algorithm is
[error corrected](54_threshold_theorem.md), the syndrome-extraction round takes
about a microsecond on a transmon and about a millisecond on an ion — and
suddenly wall-clock time binds instead, and superconducting wins by $1000\times$.

*Connectivity is binding* — your circuit needs gates between distant qubits.
All-to-all gives about $3\times$ on depth for a connectivity-hungry circuit like
QFT. But if your circuit is local — a
[surface code](52_surface_codes.md), or a nearest-neighbour simulation — the
advantage largely disappears, and you are paying for connectivity you never use.

*Qubit count is binding* — you need more qubits than any one platform has.
Neutral atoms have demonstrated the largest arrays; superconducting has the most
integrated qubits. Neither is yet large enough for the cryptographic workloads,
which is the subject of [resource estimation](43_resource_estimation.md).

*Fidelity is binding* — you are near the error-correction threshold and every
$0.1\%$ counts. Trapped ions and spin qubits have the best reported numbers, and
since the physical-to-logical ratio depends steeply on physical error rate, this
is where fidelity matters most.

*Integration is binding* — you need the thing to be manufactured. Spin qubits
and superconducting qubits are lithographic; atoms are not. The 2025 result of
$>99\%$ two-qubit fidelity on devices from an industrial 300 mm wafer line is the
strongest evidence available that a quantum processor can be *made* rather than
assembled.

### A worked decision

Suppose the workload is a variational algorithm — see
[VQE and QAOA](07_vqe_qaoa.md) — with a dense ansatz on 40 qubits, run for
$10^4$ circuit evaluations.

- **Depth**: variational circuits are shallow but repeated often, so wall-clock
  time per evaluation matters. Superconducting gates are $1000\times$ faster, so
  $10^4$ shots take minutes rather than hours.
- **Connectivity**: a dense ansatz wants all-to-all. On a heavy-hex device the
  SWAP overhead adds roughly $3\times$ depth, which at $0.8\%$ per gate is
  punishing.
- **Verdict**: this is genuinely close. Superconducting wins on throughput;
  trapped ions win on effective circuit depth. The deciding question is whether
  the ansatz can be rewritten to match the hardware connectivity — a
  hardware-efficient ansatz on superconducting hardware often beats a dense
  ansatz on all-to-all hardware, because it trades expressibility for a factor
  of three in depth.

That is the general shape of these decisions: the answer usually depends on
whether the algorithm can be restructured to suit the hardware, not on which
platform has the better spec sheet.

## Common misconceptions

- **"Fidelity is the metric that matters."** Fidelity, connectivity, gate speed
  and qubit count all matter, and which one binds depends on the workload. A
  $99.99\%$ gate on a machine too small for your circuit is useless.
- **"All-to-all connectivity gives order-of-magnitude savings."** Verified: about
  $3\times$ on depth for a QFT. Real, valuable, and roughly an order of magnitude
  less than naive SWAP-counting predicts.
- **"The native gate is CNOT."** On the device above it is ECR. Your CNOT is
  compiled into it, and the cost is not the number in the calibration file.
- **"A calibrated noise model is a complete description."** It omits crosstalk,
  correlated errors, drift and leakage. Simulations are optimistic.
- **"$T_2 \le 2T_1$ always."** True, and a measured $T_2/T_1 = 0.75$ means
  dephasing dominates relaxation — information the median fidelity does not
  carry.
- **"More connectivity is always better."** Degree 3 is a deliberate choice:
  it reduces crosstalk and frequency collisions, and it is sufficient for
  surface codes.

## Exercises

1. A device reports $T_2/T_1 = 0.75$. Is it relaxation-limited or
   dephasing-limited, and why?

2. From the verified table, a 25-qubit QFT needs 600 two-qubit gates on
   all-to-all and 1485 on a line. If every gate has error $0.8\%$, estimate the
   probability that a circuit runs without error in each case.

3. Using the naive SWAP estimate, what does one distant gate cost on a
   127-qubit line? Why is the measured cost so much lower?

4. Your circuit is a nearest-neighbour simulation on a 2D lattice. Which
   platform connectivity do you actually need, and is all-to-all worth paying
   for?

5. A calibration file lists median readout error $1.17\%$ and worst $35.75\%$.
   What is the consequence for how you should use the device?

6. Give one workload where superconducting clearly beats trapped ions, and one
   where the reverse holds. Justify each with a number from this lesson.

### Answers to 1–3

**1.** Dephasing-limited, and strongly so. Relaxation alone gives
$1/T_2 = 1/(2T_1)$, so $T_2 = 2T_1$. A measured ratio of $0.75$ means $T_2$ is
*shorter than $T_1$*, which can only happen if there is substantial pure
dephasing on top of relaxation. In practice it points at low-frequency noise —
flux noise, or drift — that the gate-error figures do not capture.

**2.** Treating errors as independent, the probability of no error is
$(1-0.008)^{N}$:

$$(0.992)^{600} = e^{600\ln 0.992} = e^{-4.819} \approx 0.0081$$

$$(0.992)^{1485} = e^{1485\ln 0.992} = e^{-11.93} \approx 6.6\times10^{-6}$$

So about $0.8\%$ against about $7$ in a million. The $2.48\times$ gate-count
penalty becomes a factor of roughly $1200$ in success probability — which is why
connectivity matters far more than the raw gate-count ratio suggests, and why
[error mitigation](55_error_mitigation.md) or
[error correction](52_surface_codes.md) is mandatory at this scale.

**3.** The mean distance between two random qubits on a line of $n$ is
$(n+1)/3$, so at $n = 127$ that is $42.67$ hops. At three CNOTs per SWAP, about
$128$ CNOTs. The measured cost is nowhere near this because a transpiler does
not route gates one at a time: it reorders operations, keeps interacting qubits
adjacent, and amortises a single SWAP over many gates. Naive SWAP-counting is
an upper bound, not an estimate.

### Answers to 4–6

**4.** You need nearest-neighbour connectivity in two dimensions — which a
**grid** gives you directly. All-to-all would cost you nothing in routing, but
you would be paying for connectivity you never use, and if that connectivity is
bought with lower fidelity or fewer qubits you are worse off. Neutral atoms
(native 2D arrays) or a heavy-hex superconducting device (which embeds a 2D
lattice with modest overhead) are the natural fits. This is the general point:
match the topology to the algorithm's communication graph.

**5.** Choose which physical qubits to use. A single bad qubit with $36\%$
readout error will dominate the results of any circuit routed through it.
Transpilers accept an error map alongside the coupling map precisely so bad
qubits can be avoided, and the $10\times$ spread between median and worst means
qubit selection is worth doing. It also means you should not trust a
device-wide average fidelity as a prediction for your circuit.

**6.** *Superconducting wins:* any workload where wall-clock throughput binds —
for example a variational loop with $10^4$ circuit evaluations. Gates are about
$1000\times$ faster ($200$ ns against $100$ μs), so the same experiment takes
minutes rather than days. *Trapped ions win:* a deep circuit that needs many
sequential gates before decoherence. The depth budget $T_2/t_g$ is roughly
$10^4$ for ions against roughly $10^3$ for superconducting devices, so ions
support about ten times as many sequential operations. They also win on
connectivity, worth about $3\times$ on depth for a dense circuit.

## Summary

- A calibration file reports per-qubit $T_1$, $T_2$, frequency, anharmonicity,
  readout error, and per-gate errors and durations. Verified on a real
  127-qubit snapshot: median $T_1 = 279.6$ μs, $T_2 = 197.8$ μs, readout error
  $1.17\%$, two-qubit error $0.80\%$.
- **The mean hides the outliers** — the worst qubit was $10\times$ worse than the
  median. **Averages hide correlations** — randomised benchmarking does not
  report them, and correlated errors are the hardest to correct.
- **$T_2/T_1 = 0.75$ means dephasing dominates**, not relaxation. The native gate
  is **ECR**, so a logical CNOT costs more than the quoted two-qubit error. And
  single-qubit gates are $250\times$ better and $9\times$ faster, which should
  drive compilation choices.
- **Connectivity is quantified by degree, diameter and mean shortest path.** The
  127-qubit device has **$1.80\%$ of the edges of an all-to-all machine**,
  diameter 26, and mean shortest path $11.13$.
- Verified by compilation: sparse connectivity costs about **$2.5\times$ on gate
  count and $3.1\times$ on depth** for a QFT. Depth is the metric that matters.
  The naive SWAP estimate predicts ~26× and is wrong by an order of magnitude,
  because transpilers reorder and amortise.
- **Choose by asking which resource binds** — depth, connectivity, qubit count,
  fidelity, or manufacturability. Usually the deciding question is whether the
  algorithm can be restructured to suit the hardware.
- A calibrated noise model is necessary but **not sufficient**: it omits
  crosstalk, correlated errors, drift and leakage.

## References

- Qiskit documentation, `NoiseModel.from_backend` — building a noise model from
  a backend's calibration data.
- Magesan, E. et al., "Scalable and robust randomised benchmarking of quantum
  processes" — what average gate fidelity does and does not capture.
- IBM Quantum, "The heavy-hex lattice" — why degree 3 is a deliberate design
  choice for surface codes.
- Nation, P. D. et al., "Benchmarking of quantum processors" — survey of what
  calibration data means.
- Wallman, J. J. & Emerson, J., "Noise tailoring for scalable quantum
  computation via randomised compiling" — turning general noise into Pauli
  noise.
- [Superconducting Qubits](56_superconducting_qubits.md),
  [Trapped Ions](57_trapped_ions.md),
  [Photonic Systems](58_photonic_systems.md),
  [Neutral Atoms](59_neutral_atoms.md),
  [Spin Qubits](60_spin_qubits.md) — the platforms compared.
- [NISQ Limitations](62_nisq_limitations.md) — what these limits mean for what
  is computable.
- [Quantum Benchmarking](64_benchmarking.md) — how the fidelity figures are
  actually measured.
- [Resource Estimation](43_resource_estimation.md) — turning platform parameters
  into qubit counts.

---

**Next:** [NISQ Limitations](62_nisq_limitations.md)
