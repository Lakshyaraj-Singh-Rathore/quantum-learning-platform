# NISQ Limitations

NISQ stands for **Noisy Intermediate-Scale Quantum** — a term Preskill coined in
2018 to name a regime rather than to describe a technology. The regime is
defined by what it *lacks*: no error correction, intermediate qubit counts, and
coherence that runs out.

This lesson turns that into a number. The entire NISQ constraint reduces to one
product, $N \cdot d \cdot \varepsilon$, and knowing it lets you look at a
proposed algorithm and say whether it can possibly run.

## Learning objectives

By the end of this lesson you should be able to:

- **State** the constraints defining the NISQ regime.
- **Explain** why circuit depth is limited by error rates.
- **Assess** whether a proposed algorithm fits current hardware.

## Prerequisites

[Quantum Noise and Decoherence](../qiskit/quantum_noise.md) (**required**) —
NISQ limits are decoherence and gate-error limits.
[Resource Estimation](../adv/resource_estimation.md) (recommended) — depth
budgets quantify what is feasible.

## What defines the NISQ regime

Four constraints, and they are all negative:

**1. No error correction.** Physical qubits are used directly. There are no
logical qubits, so the error rate of a computation is the error rate of the
hardware. This is the defining absence — the others follow from it.

**2. Intermediate scale.** Roughly 50 to a few hundred qubits. Enough that
classical simulation is hard or impossible; far too few for
[error correction](54_threshold_theorem.md) to pay for itself, since encoding
costs a factor of hundreds to thousands in physical qubits.

**3. Limited coherence.** Circuit duration is bounded by $T_1$ and $T_2$, so
depth is bounded by $T_2/t_g$ — the ratio computed for each platform in
[the comparison lesson](61_platform_comparison.md), running from roughly $10^3$
for superconducting devices to roughly $10^4$ for trapped ions.

**4. Imperfect connectivity.** Sparse coupling maps force SWAPs, which cost
depth — measured at about $3\times$ for a connectivity-hungry circuit.

Note what is *not* on the list: raw gate speed. NISQ is not limited by how fast
gates run in wall-clock terms; it is limited by how many of them you can stack
before the state is destroyed.

## The error budget

Consider a circuit on $N$ qubits with two-qubit depth $d$. Each layer
contributes of order $N$ entangling gates, so the circuit contains roughly
$N \cdot d$ two-qubit gates. If each has error probability $\varepsilon$ and the
errors are independent, the probability that *nothing* goes wrong is

$$P_{\text{success}} \;\approx\; (1-\varepsilon)^{Nd} \;\approx\; e^{-Nd\varepsilon}$$

**The entire error budget is the single product $N\,d\,\varepsilon$.** Every
NISQ trade-off is a consequence of keeping that product below about $1$.

Solve it for depth:

$$d_{\max} \;\approx\; \frac{\ln 2}{N\,\varepsilon} \qquad \text{(depth at which } P_{\text{success}} = \tfrac12)$$

At $\varepsilon = 0.01$:

| $N$ | $P$ at $d=1$ | $P$ at $d=10$ | $P$ at $d=50$ | $d$ for $P=\tfrac12$ |
|---|---|---|---|---|
| 4 | 0.9608 | 0.6703 | 0.1353 | 17.3 |
| 8 | 0.9231 | 0.4493 | 0.0183 | 8.7 |
| 16 | 0.8521 | 0.2019 | 0.0003 | 4.3 |
| 32 | 0.7261 | 0.0408 | $\sim 0$ | 2.2 |
| 64 | 0.5273 | 0.0017 | $\sim 0$ | 1.1 |
| 128 | 0.2780 | $\sim 0$ | $\sim 0$ | 0.5 |

Read the last column carefully. **At 128 qubits and 1% gate error, the usable
depth is less than one.** Not "small" — the circuit cannot complete a single
entangling layer with better than even odds. That is the NISQ wall, and it is
reached by scaling qubits *without* improving error rates.

The trade is exact and linear in both directions: halve the qubit count and you
double the usable depth; halve the error rate and you double it again. Depth is
not a free parameter. It is bought with error rate and paid for in qubit count.

### Verified: fidelity versus depth

The prediction above assumes independent errors. Checking it by simulating
random circuits of increasing depth with a depolarising channel of strength
$\varepsilon$ on every CX, and comparing against the exact noiseless state:

**$N = 4$, $\varepsilon = 0.002$:**

| Depth | CX gates | $F$ measured | $(1-\varepsilon)^{\text{gates}}$ | Difference |
|---|---|---|---|---|
| 1 | 3 | 0.995172 | 0.994012 | 0.001160 |
| 2 | 6 | 0.989932 | 0.988060 | 0.001872 |
| 4 | 12 | 0.979308 | 0.976262 | 0.003046 |
| 8 | 24 | 0.959363 | 0.953088 | 0.006275 |
| 12 | 36 | 0.939347 | 0.930464 | 0.008883 |
| 16 | 48 | 0.919872 | 0.908377 | 0.011495 |
| 24 | 72 | 0.881859 | 0.865763 | 0.016096 |
| 32 | 96 | 0.845716 | 0.825148 | 0.020568 |

### A second error rate

**$N = 6$, $\varepsilon = 0.005$:**

| Depth | CX gates | $F$ measured | $(1-\varepsilon)^{\text{gates}}$ | Difference |
|---|---|---|---|---|
| 1 | 5 | 0.979345 | 0.975249 | 0.004096 |
| 4 | 20 | 0.914464 | 0.904610 | 0.009854 |
| 8 | 40 | 0.833948 | 0.818320 | 0.015628 |
| 16 | 80 | 0.693452 | 0.669648 | 0.023804 |

The measured fidelity decays multiplicatively with gate count and tracks the
independent-error prediction closely, running very slightly *above* it — as
expected, since a depolarising channel leaves the state untouched with
probability $1-\varepsilon$ rather than rotating it slightly.

**This is the mechanism by which NISQ circuits fail.** Not through one dramatic
error, but through the steady accumulation of small independent ones. It also
explains why [error mitigation](55_error_mitigation.md) works at all: if the
decay is smooth and predictable, it can be extrapolated away.

### Running it

```python
import warnings
warnings.filterwarnings('ignore')
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, DensityMatrix, state_fidelity
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error


def random_circuit(n, depth, seed=0):
    """Random rotation layers alternating with a nearest-neighbour CX layer."""
    rng = np.random.default_rng(seed)
    qc = QuantumCircuit(n)
    for _ in range(depth):
        for q in range(n):
            qc.rz(2 * np.pi * rng.random(), q)
            qc.rx(2 * np.pi * rng.random(), q)
        for q in range(n - 1):
            qc.cx(q, q + 1)
    return qc


def fidelity_vs_depth(n, eps, depths):
    noise = NoiseModel()
    noise.add_all_qubit_quantum_error(depolarizing_error(eps, 2), ["cx"])
    sim = AerSimulator(method="density_matrix", noise_model=noise)
    sim.set_options(seed_simulator=12345)
    rows = []
    for d in depths:
        qc = random_circuit(n, d, seed=7)
        ideal = Statevector(qc)
        noisy = qc.copy()
        noisy.save_density_matrix()
        rho = sim.run(noisy, shots=1).result().data()["density_matrix"]
        gates = d * (n - 1)
        rows.append((d, state_fidelity(ideal, DensityMatrix(rho)),
                     gates, (1 - eps) ** gates))
    return rows


for d, F, gates, predicted in fidelity_vs_depth(4, 0.002, [1, 8, 16, 32]):
    print(f"depth {d:3d}  CX {gates:3d}  F = {F:.6f}   predicted {predicted:.6f}")
```

### What the budget buys

Inverting the relation: at $P_{\text{success}} = 1/2$ the total number of
two-qubit gates available is $\ln 2/\varepsilon$.

| $\varepsilon$ | Total CX gates available | Depth on 50 qubits |
|---|---|---|
| $10^{-2}$ | 69 | 1.4 |
| $5\times10^{-3}$ | 139 | 2.8 |
| $10^{-3}$ | 693 | 13.9 |
| $5\times10^{-4}$ | 1386 | 27.7 |
| $10^{-4}$ | 6931 | 138.6 |
| $10^{-5}$ | 69315 | 1386.3 |

At $1\%$ error the entire budget is about 69 two-qubit gates — a depth of
roughly 1.4 on 50 qubits. At $10^{-4}$ it is about 6900 gates, a depth of 139.

**Error rate enters linearly and the payoff is dramatic.** A hundredfold
improvement in $\varepsilon$ buys a hundredfold increase in circuit volume. That
is why the whole field is aimed at improving $\varepsilon$, and why
[fault tolerance](54_threshold_theorem.md) — the only known way to move it by
orders of magnitude — is the central goal rather than a refinement.

## Assessing whether an algorithm fits

This is the practical skill. Given a proposed algorithm, work through five
checks.

**1. Count the gates, not the qubits.** Obtain the two-qubit gate count and the
depth after compilation — compilation, not the logical description, because
[connectivity overhead](61_platform_comparison.md) can add a factor of 3.

**2. Compute $N \cdot d \cdot \varepsilon$** using the target device's measured
$\varepsilon$. If the product exceeds about $1$, the output is noise.

**3. Check the qubit count** against what the device actually has, remembering
that a sparse coupling map may need extra qubits for routing.

**4. Check the coherence limit** separately: circuit duration against $T_2$. A
circuit can satisfy the error budget and still overrun coherence — the two
constraints are independent and both bind.

**5. Ask whether the algorithm tolerates noise.** This is the check people skip.
Two families do:

- **Variational algorithms** ([VQE and QAOA](07_vqe_qaoa.md)) push the hard part
  into a classical optimiser. The quantum processor evaluates a shallow
  parameterised circuit; the optimiser absorbs some noise, because a
  consistently wrong energy surface can still have its minimum in roughly the
  right place.
- **Algorithms with error mitigation** ([ZNE, PEC, readout
  correction](55_error_mitigation.md)) trade more circuit executions for a
  less-biased answer, buying back perhaps an order of magnitude in effective
  error at the cost of sampling overhead.

Algorithms that do **not** tolerate noise are those requiring exact
interference over long sequences: [Shor's](33_shors_algorithm.md),
[HHL](37_hhl.md), and long [Grover](06_grover.md) searches.

### Worked assessments

**VQE on 20 qubits, hardware-efficient ansatz, depth 12.**
$N d \varepsilon = 20 \times 12 \times 0.008 \approx 1.9$. Over budget — but the
observable is an energy, and the optimiser tolerates bias. **Verdict: feasible
with mitigation.** This is the canonical NISQ workload, and it is the reason the
regime has a name.

**Grover search over $2^{50}$ items.** Needs about $2^{25} \approx 3\times10^7$
iterations, each involving an oracle. Even at $\varepsilon = 10^{-6}$ the budget
allows $7\times10^5$ gates. **Verdict: infeasible by many orders of magnitude.**
Grover's quadratic speedup is real and is utterly consumed by error accumulation
at this scale.

**Shor's algorithm on RSA-2048.** [Resource estimates](43_resource_estimation.md)
put this at millions of physical qubits and gate counts in the billions.
**Verdict: infeasible, and not marginally so.** The gap is not something
incremental hardware improvement closes; it needs fault tolerance.

**QAOA on 100 qubits, $p = 1$ (depth 1).** $N d \varepsilon = 100 \times 1 \times 0.008 = 0.8$. Right at the edge. **Verdict: feasible, barely
— and only because depth 1 keeps the product under control.** Increase to
$p = 10$ and the product is 8, which is not.

Notice the pattern: every feasible case is **shallow**. Depth is the variable
that kills NISQ algorithms, and shallow is the only reliable way to survive.

## The shape of NISQ algorithm design

Everything that works in this regime shares a design philosophy forced by the
budget:

- Keep depth minimal, even at the cost of more qubits or more shots.
- Match the ansatz or circuit to the hardware connectivity rather than the
  reverse.
- Sample many short circuits rather than running one long one.
- Push as much work as possible to the classical co-processor.
- Accept a biased answer if the bias is correctable or tolerable.

That is a genuinely different discipline from fault-tolerant algorithm design,
where depth is cheap and the goal is minimising logical gate count.

## Common misconceptions

- **"More qubits is the main thing we need."** Verified: at 128 qubits and 1%
  error the usable depth is below 1. Scaling qubits without improving
  $\varepsilon$ walks straight into the wall.
- **"A 99% gate is nearly perfect."** At $N=50$, $d=10$, a 99% gate gives
  $P_{\text{success}} = e^{-5} \approx 0.7\%$.
- **"NISQ machines are just smaller versions of future ones."** The design
  principles are different: shallow-and-sample rather than deep-and-exact.
- **"Error mitigation fixes this."** It buys perhaps an order of magnitude in
  effective error at sampling cost, and it amplifies variance. See
  [error mitigation](55_error_mitigation.md), where the variance overhead is
  quantified.
- **"If it fits the qubit count it fits."** Three separate constraints bind:
  qubit count, the error budget $Nd\varepsilon$, and coherence $T_2$.
- **"Depth and gate count are the same constraint."** They are related but
  distinct; a wide shallow circuit and a narrow deep one with equal gate counts
  have different coherence and connectivity costs.

## Exercises

1. Using $d_{\max} \approx \ln 2/(N\varepsilon)$, compute the usable depth at
   $N = 40$ and $\varepsilon = 0.005$.

2. A circuit has $N = 30$, $d = 20$, $\varepsilon = 0.004$. Estimate
   $P_{\text{success}}$ and say whether the result is usable.

3. From the verified simulation table at $N=4$, $\varepsilon = 0.002$: by what
   factor does the fidelity drop going from depth 8 to depth 32? Compare with
   the prediction.

4. You halve the error rate and double the qubit count. What happens to the
   usable depth?

5. Why do variational algorithms tolerate noise better than Shor's algorithm?

6. Name the three independent constraints that determine whether an algorithm
   fits a NISQ device.

### Answers to 1–3

**1.** $d_{\max} = \ln 2/(40 \times 0.005) = 0.693/0.2 = 3.47$. So a depth of
about 3 — three entangling layers before the success probability falls to
even.

**2.** $Nd\varepsilon = 30 \times 20 \times 0.004 = 2.4$, so
$P_{\text{success}} \approx e^{-2.4} = 0.091$. About 9%: the circuit runs
cleanly roughly one time in eleven. Unless the algorithm tolerates bias
(variational) or the answer can be mitigated, this is not usable. Running more
shots does not fix a bias — it only reduces the uncertainty on a wrong number.

**3.** Measured: $0.845716/0.959363 = 0.882$. Predicted:
$0.825148/0.953088 = 0.866$. The measured decay is slightly gentler, because
depolarising noise leaves the state completely untouched with probability
$1-\varepsilon$ rather than perturbing it slightly. Both are close to the ratio
of $\exp(-96\varepsilon)$ to $\exp(-24\varepsilon) = e^{-0.144} = 0.866$.

### Answers to 4–6

**4.** Usable depth is $\ln 2/(N\varepsilon)$. Halving $\varepsilon$ doubles it;
doubling $N$ halves it. Together they cancel exactly — the usable depth is
unchanged. This is the trap: improving fidelity and scaling qubits at the same
rate buys nothing.

**5.** A variational algorithm's output is fed to a classical optimiser that
searches for a minimum. A consistently biased but smooth energy surface still
has its minimum near the right place, so systematic noise partly cancels.
Shor's algorithm depends on exact constructive and destructive interference
across a very long sequence — [phase estimation](32_phase_estimation.md) must
resolve a phase to a precision that a single mid-circuit error destroys. There
is no optimiser downstream to absorb the error.

**6.** (i) The **error budget** $N d \varepsilon \lesssim 1$ — whether the
circuit completes without an error. (ii) **Coherence** — whether the circuit
duration fits inside $T_2$, which is a separate constraint from the error
budget. (iii) **Qubit count and connectivity** — whether the device has enough
physical qubits, including any needed for routing on a sparse coupling map. All
three must hold.

## Summary

- **NISQ** is defined by four absences: no error correction, intermediate qubit
  count, limited coherence, imperfect connectivity.
- **The whole constraint is one product**: $N\,d\,\varepsilon$. The probability
  of running cleanly is $P \approx e^{-Nd\varepsilon}$.
- **Usable depth is $d_{\max} \approx \ln 2/(N\varepsilon)$.** At 128 qubits and
  1% error it is below 1 — the circuit cannot complete a single entangling layer
  with even odds.
- Verified by simulation: fidelity decays **multiplicatively** with gate count
  and tracks the independent-error prediction, running slightly above it because
  depolarising noise leaves the state untouched with probability
  $1-\varepsilon$. NISQ circuits fail by accumulation, not catastrophe — which
  is also why error mitigation is possible.
- **Depth is bought with error rate and paid for in qubit count.** Improving
  fidelity while scaling qubits at the same rate buys exactly nothing.
- **To assess an algorithm**, check three independent constraints: the error
  budget, coherence, and qubit count with connectivity. Then ask whether the
  algorithm tolerates bias — variational and mitigated algorithms do;
  Shor, HHL and long Grover searches do not.
- Everything that works in this regime is **shallow**.

## References

- Preskill, J., "Quantum Computing in the NISQ era and beyond" (Quantum, 2018) —
  the paper that named the regime.
- Bharti, K. et al., "Noisy intermediate-scale quantum algorithms"
  (Reviews of Modern Physics, 2022) — a comprehensive survey of what runs in
  this regime.
- Cerezo, M. et al., "Variational quantum algorithms" (Nature Reviews Physics,
  2021) — including the barren-plateau problem.
- [Quantum Noise and Decoherence](../qiskit/quantum_noise.md) — where the error
  rates come from.
- [Error Mitigation: ZNE, PEC and Readout Correction](55_error_mitigation.md) —
  buying back effective error rate, and what it costs in variance.
- [Threshold Theorem and Fault Tolerance](54_threshold_theorem.md) — the only
  known way to move $\varepsilon$ by orders of magnitude.
- [Calibrated Noise Models and Connectivity Topologies](61_platform_comparison.md)
  — the per-platform numbers to plug into the budget.
- [Resource Estimation](../adv/resource_estimation.md) — turning an algorithm
  into gate counts and depths.
- [Quantum Benchmarking](64_benchmarking.md) — how the $\varepsilon$ values are
  actually measured.

---

**Next:** [Quantum Benchmarking](64_benchmarking.md)
