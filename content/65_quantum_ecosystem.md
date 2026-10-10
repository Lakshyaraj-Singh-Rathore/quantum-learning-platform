# Quantum Ecosystem: Qiskit, Cirq, PennyLane, CUDA-Q and Braket

There are too many quantum SDKs, and the differences between them are mostly not
about syntax — they are about what each one is *for*. Picking the wrong one means
fighting the framework for the whole project.

This lesson surveys the major frameworks, explains what a hardware provider
service does that an SDK does not, and gives you a way to choose. Because this
platform runs several of them side by side, we can be concrete: the capabilities
described below are the ones this application actually dispatches to.

## Learning objectives

By the end of this lesson you should be able to:

- **Name** the major SDKs and what each is best at.
- **Explain** the role of a hardware provider service.
- **Choose** tooling appropriate to a task.

## Prerequisites

[Quantum Gates](../qc/basic_gates.md) (recommended) — survey of tooling; assumes
the basics.

## Why so many frameworks

The ecosystem fragmented for a real reason: the frameworks were built by
different organisations solving different problems, and none of them set out to
be a general-purpose tool.

- **IBM** built Qiskit to drive its own superconducting hardware end to end.
- **Google** built Cirq for the precise, low-level control that NISQ
  experiments need.
- **Xanadu** built PennyLane around differentiable programming, because its
  interest was quantum machine learning.
- **NVIDIA** built CUDA-Q to plug quantum simulation into GPU and HPC
  workflows.
- **Amazon** built Braket as a *service* giving access to other people's
  hardware.

Different goals produced different abstractions, and the abstractions are not
interchangeable. That is the thing to understand — not the syntax.

## The major SDKs

| Framework | Origin | Best at | Notable limitation |
|---|---|---|---|
| **Qiskit** | IBM | The complete stack: circuit construction, transpilation, simulation, noise models, hardware access | Hardware access is tied to IBM |
| **Cirq** | Google | Precise low-level control of NISQ devices, moment-based scheduling | No native runtime control flow |
| **PennyLane** | Xanadu | Differentiable quantum programming, quantum machine learning, hardware-agnostic devices | Optimised for the variational/gradients use case |
| **CUDA-Q** | NVIDIA | GPU-accelerated simulation and HPC integration | Requires GPU infrastructure to matter |
| **Braket** | AWS | Access to many vendors' hardware through one service | A provider service, not a development SDK |

### Qiskit — the full stack

Qiskit is the most complete framework and the default choice for most work.
Its distinguishing feature is that it covers the **whole pipeline**: build a
circuit, transpile it for a specific device's coupling map and basis gates,
simulate it with or without noise, and submit it to real hardware.

The component that matters most and is least appreciated is the
**transpiler**. As [the comparison lesson](61_platform_comparison.md) showed,
compiling the same circuit onto different topologies changes the two-qubit gate
count by a factor of 2.5 and the depth by 3. Qiskit's transpiler, with its
coupling map and optimisation levels, is the maturest tool for that job.

`qiskit-aer` provides high-performance simulation including noise models built
from device calibration data. Qiskit also has the best-developed support for
**dynamic circuits** — mid-circuit measurement and classical feedback — which
matters for [error correction](52_surface_codes.md) and
[teleportation](../qc/teleportation.md).

### Cirq — precise control

Cirq is built around the needs of someone running experiments on near-term
hardware. Its central abstraction is the **moment**: a layer of operations
happening simultaneously. This makes timing and scheduling explicit in a way
Qiskit's gate-list model does not.

That precision is the point. If you care exactly when operations happen — for
calibration, for benchmarking, for characterising a device — Cirq's model is a
better fit.

The limitation is real and specific: **Cirq has no native runtime control flow.**
A dynamic circuit — one where a measurement result determines what happens next —
cannot be expressed as a single Cirq circuit. It has to be driven from Python,
running one segment at a time and feeding results back. This platform does
exactly that: its Cirq code generator emits a circuit plus a Python driver for
dynamic circuits, precisely because the framework cannot express them natively.

### PennyLane — differentiable programming

PennyLane's organising idea is that a quantum circuit should be a
**differentiable function** you can place inside a larger machine-learning model.
Gradients of expectation values with respect to circuit parameters are
first-class, and it integrates with PyTorch, JAX and NumPy the way you would
expect a neural-network layer to.

This makes it the natural choice for
[variational algorithms](07_vqe_qaoa.md) and
[quantum machine learning](47_quantum_machine_learning.md), and the obvious
choice if the quantum part is one component of a bigger differentiable model.

It is also deliberately **hardware-agnostic**: the "device" abstraction means the
same program runs on a simulator or on hardware from several vendors with a
one-line change. The trade is that PennyLane does less low-level control than
Cirq and has a less mature transpiler than Qiskit.

### CUDA-Q — GPU and HPC

CUDA-Q is built for scale and for integration with classical high-performance
computing. Its distinguishing feature is GPU-accelerated statevector simulation,
which pushes the practical simulation limit well past what a CPU can do.

It matters when simulating larger circuits, and it matters for hybrid workflows
where the quantum simulator is one part of an HPC job. On a laptop with no GPU,
it buys you nothing — the framework's whole value proposition is the hardware.

### Braket — the provider service

Amazon Braket is the odd one out, and understanding why is the point of the next
section. Braket is not primarily a development SDK. It is a **service** that
gives you one API and one bill across hardware from several vendors — ion traps,
superconducting devices, and neutral atoms — plus its own simulators.

## The role of a hardware provider service

Objective 2, and a distinction that trips people up constantly.

**An SDK builds and runs circuits. A provider service sells access to hardware.**

They are different layers, and you generally use both:

```
 your code
     |
  SDK  (Qiskit, Cirq, PennyLane ...)     <- builds circuits, transpiles, simulates
     |
  provider service (IBM Quantum, Braket, Azure Quantum, IonQ Cloud ...)
     |
  hardware (superconducting, ion trap, neutral atom ...)
```

A provider service does five things an SDK does not:

1. **Queues and schedules jobs.** Real hardware is oversubscribed. The service
   manages the queue.
2. **Handles calibration windows.** Device calibrations drift; the service
   reports the current one and decides when recalibration invalidates queued
   work — see [calibrated noise models](61_platform_comparison.md).
3. **Bills.** Hardware time costs money, priced per task or per shot.
4. **Abstracts vendor differences.** IonQ, Rigetti, QuEra and Oxford Quantum
   Circuits have different native gates, different connectivity and different
   submission formats. A multi-vendor service lets you compare them without
   learning four APIs.
5. **Returns results with provenance.** Which device, which calibration, which
   queue time, how many shots.

The trade for all of that is **latency and loss of control**. A cloud submission
involves queueing minutes to hours — unusable inside a tight variational loop,
which is why [NISQ-era](62_nisq_limitations.md) algorithm development mostly
happens on local simulation and only finishes on hardware.

### Verified: what this platform actually supports

Because this application dispatches to several frameworks, the capabilities are
concrete rather than theoretical. Its static-circuit runners are:

| Backend | Framework | Noise models | Runtime control flow |
|---|---|---|---|
| `qiskit_aer` | Qiskit + Aer | Yes | No |
| `cirq` | Cirq | No | No — routed to Qiskit |
| `pennylane` | PennyLane | No | No — routed to Qiskit |
| `qbraid` | Qbraid (Braket-style access) | No | No — routed to Qiskit |
| `cudaq` | CUDA-Q | Yes | No |
| `qiskit_dynamic` | Qiskit | — | **Yes** |

Three facts worth extracting, because they are the kind of thing that only shows
up when you actually wire several frameworks together:

**Only one engine handles runtime control flow.** A dynamic circuit requested on
Cirq, PennyLane or Qbraid is silently **routed to the Qiskit dynamic engine**,
with a note attached to the result. The abstraction leaks: the capability is not
uniform across frameworks, and something has to decide what to do about it.

**Noise is supported on two of five engines.** Requesting a noise model on the
Cirq, PennyLane or Qbraid backends is rejected, because those paths have no
noise implementation. If your work involves
[noise or error mitigation](55_error_mitigation.md), that constrains your choice
of framework more than any stylistic preference.

**Qbraid plays the provider-service role here.** It is the route to hardware and
to other vendors' devices, sitting alongside the development SDKs rather than
competing with them.

## Choosing tooling

Objective 3. Work down this list; the first match is usually right.

| Your task | Choose | Why |
|---|---|---|
| Learning, general algorithm development | **Qiskit** | Complete stack, best documentation, largest community |
| Transpiling for real hardware topology | **Qiskit** | Maturest transpiler and coupling-map handling |
| Noisy simulation | **Qiskit** (Aer) or **CUDA-Q** | These are the engines here with noise support |
| Dynamic circuits, mid-circuit measurement | **Qiskit** | Only engine here with runtime control flow |
| Precise timing and scheduling, calibration work | **Cirq** | Moment-based model makes timing explicit |
| Variational algorithms, QML, gradients | **PennyLane** | Differentiability is the organising principle |
| Large simulation, GPU available | **CUDA-Q** | GPU-accelerated statevector |
| Comparing hardware vendors | **Braket** or **Qbraid** | One API across devices |
| Running on real hardware | SDK **+** provider service | You need both layers |

Two heuristics that save time:

**Start with Qiskit unless you have a specific reason not to.** It is the most
complete and the best documented. The specific reasons are: differentiability
(PennyLane), timing precision (Cirq), and GPU scale (CUDA-Q).

**Do not pick a framework for its hardware.** Pick the SDK for what you are
building, and the provider service for where you want to run it. The two choices
are independent, and conflating them is the most common mistake.

## Interoperability

The frameworks do interoperate, and it is worth knowing how.

**OpenQASM** is the lowest common denominator — a circuit description language
that Qiskit, Cirq and others can emit or consume. Exchanging OpenQASM loses
high-level structure: a PennyLane QNode with trainable parameters becomes a flat
list of gates with concrete angles.

**Direct conversion libraries** exist, but they handle the common subset well and
the edges badly. Anything framework-specific — PennyLane's differentiation,
Cirq's moments, Qiskit's control flow — will not survive the trip.

The practical advice: **convert at the circuit boundary, early, and once.**
Pick a framework, build the circuit in it, and only translate at the point where
you must. Do not plan on round-tripping between frameworks mid-development.

## Common misconceptions

- **"Pick the framework whose hardware you want to run on."** SDK and provider
  are different layers. You nearly always use both.
- **"All frameworks can do everything."** Verified above: runtime control flow
  works in one engine here, noise in two. Capabilities genuinely differ.
- **"Braket is a Qiskit competitor."** Braket is a provider service; Qiskit is a
  development SDK. You can use Qiskit *through* a provider.
- **"I can write it once and run it anywhere."** Hardware differs in native
  gates, connectivity and error rates. A circuit tuned for one device is often
  poor on another — which is what [transpilation](42_compilation.md) is for, and
  why it is not free.
- **"GPU acceleration always helps."** Only for simulation, and only at sizes
  where GPU memory is the binding constraint rather than overhead.
- **"OpenQASM preserves my program."** It preserves the circuit. Higher-level
  structure — parameters, gradients, control flow — does not survive.

## Exercises

1. What is the difference between a quantum SDK and a hardware provider
   service? Name one of each.

2. You are building a variational classifier with PyTorch. Which framework and
   why?

3. Your circuit needs a mid-circuit measurement whose result selects the next
   operation. Which of this platform's backends can run it, and what happens if
   you request Cirq?

4. You need a noisy simulation. Which backends are available, and what happens
   if you ask for noise on PennyLane?

5. Give two reasons a cloud provider service is a poor fit for a variational
   loop.

6. Why does translating a PennyLane QNode to OpenQASM lose information?

### Answers to 1–3

**1.** An SDK builds, transpiles and simulates circuits — Qiskit, Cirq,
PennyLane, CUDA-Q. A provider service sells access to hardware, handling
queueing, calibration windows, billing and vendor abstraction — IBM Quantum,
Amazon Braket, Azure Quantum, IonQ Cloud, Qbraid. You use an SDK *through* a
provider.

**2.** **PennyLane.** Its organising principle is that a quantum circuit is a
differentiable function, and it integrates with PyTorch, JAX and NumPy directly,
so the quantum circuit becomes a layer in a larger model whose parameters train
end to end. Gradients of expectation values are first-class rather than
something you bolt on.

**3.** Only `qiskit_dynamic` — the Qiskit dynamic engine. Verified in the
dispatch logic: if you request `cirq`, `pennylane` or `qbraid` for a dynamic
circuit, the request is **routed to the Qiskit dynamic engine** and a note is
attached to the result saying the requested backend cannot execute runtime
control flow. The programme runs, but not on the framework you asked for.

### Answers to 4–6

**4.** `qiskit_aer` and `cudaq`. Requesting noise on the Cirq, PennyLane or
Qbraid backends is rejected, because those engine paths have no noise
implementation — a hard constraint on framework choice if your work involves
[noise](55_error_mitigation.md), not a preference.

**5.** Any two of: hardware is queued, so each iteration waits minutes to hours
while a variational loop may need thousands; calibration drifts between
submissions, so parameters optimised against one calibration are stale by the
next; each submission costs money, and the cost scales with the number of
iterations; and results come back asynchronously, breaking the tight
evaluate-and-update cycle. Variational development therefore mostly happens on
local simulation, with hardware used for a final validation.

**6.** OpenQASM describes a circuit: a sequence of gates with concrete
parameters. A PennyLane QNode carries structure that is not in the circuit —
which parameters are trainable, how they differentiate, and the classical
processing around the expectation values. Serialising to OpenQASM keeps the gates
and drops the rest, so the result is no longer differentiable or trainable.

## Summary

- Frameworks fragmented because they were built for **different goals**: Qiskit
  for the full pipeline to IBM hardware, Cirq for precise NISQ control,
  PennyLane for differentiable programming, CUDA-Q for GPU and HPC, Braket as a
  provider service.
- **Qiskit** is the default: complete stack, maturest transpiler, best noise
  simulation, and the only engine here with runtime control flow.
- **Cirq** for timing precision; **PennyLane** for gradients and QML;
  **CUDA-Q** for GPU-accelerated simulation; **Braket** for multi-vendor
  hardware access.
- **An SDK builds circuits; a provider service sells hardware access** —
  queueing, calibration windows, billing, vendor abstraction, provenance. You
  need both, and they are independent choices.
- Verified from this platform's dispatch table: **only `qiskit_dynamic` runs
  runtime control flow** (other backends are silently routed to it), and **noise
  is supported on `qiskit_aer` and `cudaq` only**. Capabilities genuinely differ
  between frameworks.
- **Choose the SDK for what you are building and the provider for where you run
  it.** Start with Qiskit absent a specific reason. Convert between frameworks
  early and once, at the circuit boundary, and expect higher-level structure not
  to survive.

## References

- Qiskit documentation — circuit construction, the transpiler, and Aer noise
  models.
- Cirq documentation — moments, scheduling, and device-specific control.
- PennyLane documentation — `qml.grad`, interfaces to PyTorch/JAX, and the
  device abstraction.
- NVIDIA CUDA-Q documentation — GPU-accelerated simulation and HPC integration.
- Amazon Braket documentation — the provider-service model and multi-vendor
  device access.
- OpenQASM 3 specification — the interchange format, and its limits.
- [Compilation and Transpilation](42_compilation.md) — why transpiling for a
  target device is not free.
- [Calibrated Noise Models and Connectivity Topologies](61_platform_comparison.md)
  — what the provider reports about a device.
- [NISQ Limitations](62_nisq_limitations.md) — why most development happens in
  simulation.
- [VQE and QAOA](07_vqe_qaoa.md),
  [Quantum Machine Learning](47_quantum_machine_learning.md) — the workloads
  PennyLane is built for.

---

**Next:** [Superdense Coding](66_superdense_coding.md)
