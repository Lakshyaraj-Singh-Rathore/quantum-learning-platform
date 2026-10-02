# Quantum Education Platform — Future Curriculum & Feature Roadmap

> **STATUS: PLANNING ONLY. NOTHING HERE IS IMPLEMENTED.**
>
> This document is a list of things that *could* be added. No code, no UI
> changes, no curriculum changes, and no architecture changes have been made
> for anything described here. It exists so the ideas are not lost.
>
> It is deliberately separate from `UI_REDESIGN_PLAN.md`, which governs the
> current Streamlit → React migration. Nothing in this file should be started
> while the UI migration is unfinished, and nothing here blocks the cutover.

How to read each entry:

- **Concept** — prose/derivation material.
- **Visual** — something to look at (static or animated).
- **Interactive** — something to manipulate.
- **Sim** — something the engine actually runs.
- **Assess** — something that checks understanding.

---

## A. Introduction to Quantum Computing

### A1. Quantum Mechanics

- **Concept** — why classical physics fails at this scale; the postulates of QM stated as a working contract rather than as history.
- **Concept** — the measurement postulate specifically: the collapse is the part that breaks intuition, and it deserves its own treatment rather than a paragraph inside superposition.
- **Visual** — double-slit experiment, animated from single-particle impacts to an interference pattern building up.
- **Visual** — wave-particle duality side by side.
- **Interactive** — single-particle accumulation: fire one "particle" at a time and watch the pattern emerge from discrete hits.
- **Visual** — probability amplitude as a wave, and intensity as amplitude squared.
- **Assess** — "which of these is directly observable: amplitude or probability?" (a classic trap).
- **Misconceptions** — "the particle splits into two", "the wave is a physical wave in space".
- **Applications** — where QM shows up outside quantum computing: lasers, MRI, semiconductor band gaps, atomic clocks.

### A2. Qubits

- **Concept** — the qubit as a two-level system, and why "two-level" does not mean "two values".
- **Concept** — physical realisations compared: superconducting transmons, trapped ions, photons, spin qubits, neutral atoms. Hardware later, but a one-paragraph map here prevents the qubit becoming an abstraction with no referent.
- **Interactive** — a single qubit you can rotate by dragging, with the state vector and the measurement probabilities updating live.
- **Visual** — qubit vs bit, with the bit as a switch and the qubit as a point on a sphere.
- **Sim** — prepare a qubit, measure it N times, watch the histogram converge to the predicted probability as N grows. This is the single most useful demonstration in the whole platform: it makes "probabilistic" concrete.
- **Assess** — predict the histogram before revealing it.
- **Misconceptions** — "a qubit holds 0 and 1 simultaneously", "a qubit stores infinite information".
- **Prerequisite** — this is the entry point for almost everything else.

### A3. Dirac Notation

- **Concept** — ket as a column vector, bra as a row, bra-ket as an inner product. Taught as notation for things already drawn, not as new mathematics.
- **Concept** — why the notation exists at all: it makes the inner product and the outer product visually distinct.
- **Interactive** — build a ket by typing components; see the bra, the norm, and the inner product with another ket appear.
- **Visual** — bra-ket as a pairing operation, with the bracket literally closing.
- **Derivation** — the normalisation condition ⟨ψ|ψ⟩ = 1, step by step, with the arithmetic shown.
- **Assess** — normalise a set of unnormalised states; spot the one that cannot be normalised.
- **Misconceptions** — treating |0⟩ + |1⟩ as if the kets were numbers to be added to 1.

### A4. Tensor Product

- **Concept** — how one qubit becomes two, and why the state space grows as 2ⁿ rather than 2n.
- **Derivation** — |0⟩ ⊗ |0⟩ worked out entry by entry, so the 4-element result is constructed rather than asserted.
- **Interactive** — pick two single-qubit states, see their tensor product, and see the dimension of the result.
- **Visual** — the Kronecker product as a block expansion.
- **Visual** — exponential growth: 1 → 2 → 4 → 8 … → 2⁵⁰, plotted, to make the "why simulate on a GPU" argument concrete later.
- **Interactive** — separability tester: given a two-qubit state, try to factor it into a tensor product, and see that some states cannot be factored. This is the honest door into entanglement.
- **Assess** — decide whether a given state is separable or entangled.
- **Misconceptions** — "two qubits means two numbers".

### A5. Inner Product

- **Concept** — the inner product as "how much of this state is in that state", which is the only interpretation that survives contact with measurement.
- **Concept** — orthogonality as perfect distinguishability; orthogonal states can be told apart with certainty, non-orthogonal ones cannot.
- **Visual** — projection of one vector onto another, in 2D where it can actually be seen.
- **Interactive** — drag two states; watch the inner product and the resulting measurement probability move together.
- **Derivation** — the Born rule written as |⟨φ|ψ⟩|² and connected to the inner product just taught.
- **Assess** — given two non-orthogonal states, explain why no measurement can distinguish them perfectly.
- **Prerequisite** — required before measurement theory and before any algorithm that relies on interference.

### A6. Superposition

- **Concept** — superposition as a linear combination with complex coefficients, not as "being in two states at once".
- **Concept** — the difference between a superposition and a mixture. This is the distinction most learners never get taught and it is the source of most later confusion. A density matrix view, even briefly, settles it.
- **Interactive** — amplitude sliders for α and β with the normalisation constraint enforced and the sphere following.
- **Interactive** — phase slider: hold |α| and |β| fixed and rotate the relative phase; measurement probabilities do not change. Then put that qubit through a circuit where the phase *does* matter. The contrast is the lesson.
- **Visual** — equal superposition vs unequal vs a phase difference, three panels side by side.
- **Sim** — prepare superpositions, measure many times, compare the histogram to |α|² and |β|².
- **Assess** — "two states with the same measurement probabilities — are they the same state?" (no, and the follow-up is interference).
- **Misconceptions** — superposition as parallelism, superposition as uncertainty about which value the qubit "really" has.

### A7. Bell States

- **Concept** — the four Bell states, and entanglement as non-separability rather than as "spooky action".
- **Derivation** — build |Φ⁺⟩ from H then CNOT, gate by gate, showing the state after each.
- **Visual** — the Bell state as a state that cannot be written as a product.
- **Sim** — measure one qubit of a Bell pair and show the other's outcome is now determined, across many shots.
- **Interactive** — measure in different bases (Z, X, and a rotated basis) and see the correlations change.
- **Concept** — Bell inequalities and why local hidden variables fail. Optional, but it is the payoff for teaching entanglement properly.
- **Interactive** — a CHSH game: play it, and watch the quantum strategy beat the best classical strategy on average.
- **Assess** — predict the correlation for a given measurement basis.
- **Misconceptions** — "entanglement allows faster-than-light communication" — explicitly refuted, with the no-communication argument.
- **Applications** — the resource behind teleportation, superdense coding, and QKD.

### A8. Basic Quantum Gates

- **Concept** — gates as unitary matrices; unitarity as "reversible and norm-preserving", which is the actual constraint.
- **Visual** — matrix form next to circuit symbol next to Bloch-sphere action, for every gate.
- **Interactive** — apply any single-qubit gate to any state and watch the Bloch vector rotate.
- **Interactive** — build a gate sequence and see the product matrix, so "circuit = matrix multiplication" becomes visible.
- **Concept** — the Clifford vs non-Clifford distinction. The composer already colours gates this way; the lesson should explain why.
- **Concept** — controlled gates as "apply this gate, conditional on that wire".
- **Interactive** — reverse a circuit: given an output state, find the input. Makes reversibility concrete.
- **Assess** — "which of these matrices is not unitary, and what would break if you used it?"
- **Misconceptions** — "measurement is a gate", "gates copy information" (and the no-cloning theorem as the reason they cannot).
- **Reference** — a gate glossary: symbol, matrix, action, common uses.

### A9. Understanding a Circuit and Finding Its Results

- **Concept** — reading order (left to right, gates compose right to left as matrices), and why that mismatch trips people up.
- **Interactive** — step through a circuit one column at a time, showing the full state vector after each.
- **Interactive** — a prediction exercise: hide the answer, ask for the outcome, then reveal.
- **Visual** — the state vector as a bar chart of amplitudes at each step, not just at the end.
- **Sim** — run the circuit for real and compare the learner's hand calculation to the engine's answer.
- **Derivation** — a worked example end to end: Bell pair, written out in full, every intermediate state shown.
- **Assess** — a graded set of "compute this circuit by hand" problems, from 1 qubit up to 3.
- **Assess** — spot-the-error: a circuit with a deliberately wrong answer and a chance to find the mistake.
- **Prerequisite** — the hinge topic. Everything after this assumes it.

### A10. Quantum Teleportation

- **Concept** — teleportation moves a state, not matter; two classical bits plus one entangled pair.
- **Derivation** — full state evolution through the protocol, step by step. This is the first protocol where the algebra is genuinely worth following.
- **Interactive** — step through the protocol with the state shown at each stage.
- **Interactive** — pick the unknown state to teleport and see it arrive.
- **Sim** — run it for real, with the deferred-measurement corrections applied.
- **Interactive** — break it: drop the classical channel, or apply the wrong correction, and watch the protocol fail.
- **Assess** — "why can this not transmit information faster than light?" — the classical channel is the answer.
- **Misconceptions** — teleportation as cloning (it destroys the source — show this explicitly), teleportation as faster-than-light.

---

## B. Introduction to Qiskit

### B1. Qiskit Composer

- **Interactive** — guided tours that build a specific circuit, with the goal stated and the steps checked.
- **Exercise** — reproduce a given circuit from a picture.
- **Exercise** — build a named state (Bell, GHZ, W) from scratch.
- **Visual** — circuit-to-QASM, live and side by side, so the drag-and-drop and the code are never separate mental models.
- **Visual** — QASM-to-circuit, the reverse direction.
- **Assess** — "here is a circuit, here is what the author intended, here is what it does — find the bug".
- **Reference** — a composer cheat sheet.

### B2. Sampler

- **Concept** — what a Sampler primitive is and what it returns (bitstring counts, not amplitudes).
- **Code** — minimal working example, annotated line by line.
- **Exercise** — vary the shot count and watch the estimate of a probability tighten.
- **Visual** — convergence: estimated probability vs shots, with the exact value as a reference line and the √N error envelope drawn.
- **Experiment** — sampling error as a first-class idea: the difference between two runs is noise, not a bug.
- **Assess** — "how many shots do you need to distinguish p = 0.50 from p = 0.51?" The honest answer (a lot) is a genuinely useful lesson.
- **Exercise** — estimate several probabilities from one set of samples.

### B3. Estimator

- **Concept** — expectation values of observables, and what the Estimator is for (it is not a Sampler with extra steps).
- **Code** — annotated example: build an operator, estimate ⟨Z⟩.
- **Visual** — expectation value as a weighted average over the measurement distribution.
- **Experiment** — estimate ⟨Z⟩, ⟨X⟩, ⟨Y⟩ for a state and reconstruct the Bloch vector from them. This closes the loop with the Bloch sphere.
- **Exercise** — Hamiltonian expectation values, as the door into variational algorithms.
- **Assess** — relate shot count to the precision of an estimate; compare the cost of estimating an expectation vs a probability.

### B4. Bloch Sphere

- **Interactive** — drag the state vector on the sphere and read off θ and φ.
- **Interactive** — apply a gate and watch the vector rotate, with the rotation axis drawn.
- **Visual** — great-circle rotation traces, so a gate sequence draws a path rather than teleporting.
- **Interactive** — mixed states as interior points, with purity shown as distance from the surface. This is where decoherence becomes visible.
- **Visual** — the antipodal mapping: orthogonal states are opposite points.
- **Exercise** — given a Bloch vector, write the state; given a state, place it on the sphere.
- **Assess** — predict where a sequence of rotations lands.
- **Limitation to state honestly** — the Bloch sphere visualises one qubit only. Say this explicitly; learners otherwise assume it generalises.

### B5. Histograms

- **Concept** — reading a counts histogram: what the bars are, what the axis order means, and the bit-ordering convention (Qiskit's little-endian ordering is a genuine, frequent stumbling block).
- **Visual** — bit-ordering as an explicit toggle, so the learner can see the same counts labelled both ways.
- **Exercise** — read a probability off a histogram and check it against theory.
- **Exercise** — given two histograms, decide whether the circuits were the same.
- **Visual** — uncertainty bars on each bar, so a histogram stops looking exact.
- **Assess** — "these two circuits produced these histograms — are they the same circuit run twice, or different circuits?" This is a real skill.

### B6. Quantum Noise

- **Concept** — decoherence, depolarising, amplitude damping, phase damping, readout error. Each as "here is what it does to the state" rather than only as a channel definition.
- **Interactive** — a noise strength slider with the ideal and noisy results shown together.
- **Visual** — the Bloch sphere shrinking toward the centre as noise rises. Decoherence made literal.
- **Sim** — run a circuit ideal vs noisy and diff the histograms.
- **Experiment** — fidelity vs circuit depth at fixed noise: the point where depth makes things worse rather than better.
- **Concept** — where noise comes from physically (T1, T2, gate error, readout error) and how it is characterised.
- **Experiment** — error mitigation: read the result, correct for a known readout error, and see how much of the gap closes.
- **Assess** — "is this deviation noise or a bug in the circuit?" — the question every practitioner actually faces.

---

## C. Quantum Algorithms — Theory + Implementation

### C1. Deutsch–Jozsa

- **Concept** — the problem: is f constant or balanced, with the promise that it is one or the other.
- **Concept** — why classical needs 2ⁿ⁻¹ + 1 queries in the worst case, and why one quantum query suffices. The gap is the whole point and should be stated numerically for several n.
- **Derivation** — the full circuit: phase kickback worked through, the interference at the end, and why the final measurement is deterministic rather than probabilistic.
- **Interactive** — step through the algorithm for a chosen oracle, showing the state after each stage.
- **Sim** — run it against several oracles, including constant ones.
- **Visual** — phase kickback as the mechanism, isolated and animated — it recurs in Grover and Shor, so it is worth teaching properly once.
- **Code** — Qiskit implementation, annotated; the oracle as a function the learner writes.
- **Exercise** — write the oracle for a given f; get it wrong and see the algorithm return the wrong answer.
- **Compare** — classical vs quantum query counts as a table across n.
- **Assess** — "what does the algorithm return if the promise is violated?" (undefined — a good conceptual checkpoint).
- **Honest caveat** — the speedup is real but the problem is contrived. Say so; learners find out anyway, and pretending otherwise costs credibility.

### C2. Grover's Algorithm

*The platform already has a Grover lab (P6c). These are additions on top.*

- **Concept** — amplitude amplification as the general principle, with Grover as the special case for unstructured search.
- **Derivation** — the geometric picture: a rotation in the two-dimensional subspace spanned by the target and the uniform state. This is the derivation that makes the iteration count obvious.
- **Concept** — why the optimum is ⌊π/4·√N⌋ and not √N, and why overshooting makes the probability *fall*. Already demonstrated in the lab; the lesson should explain the geometry behind it.
- **Interactive** — the oracle as a function the learner supplies, not just a fixed target index.
- **Interactive** — iterate past the optimum and watch the probability come back down. Already possible; worth making it a guided exercise.
- **Sim** — scale up and show the query count vs classical, as a table and as a plot.
- **Code** — Qiskit implementation with a general oracle.
- **Exercise** — search for multiple marked items, and discover that the optimal iteration count changes.
- **Compare** — classical O(N) vs quantum O(√N) with concrete N values.
- **Applications** — where amplitude amplification actually helps: unstructured search, and as a subroutine inside other algorithms.
- **Honest caveat** — the "Grover breaks passwords" framing is wrong, and the platform already says so. Keep saying it.

### C3. Shor's Algorithm

- **Concept** — the problem: integer factorisation, and why it is believed hard classically.
- **Concept** — the reduction: factoring to order-finding. This is the conceptual heart and should be taught before any circuit.
- **Concept** — quantum period-finding via the QFT, with modular exponentiation as the expensive classical part.
- **Derivation** — the order-finding circuit step by step, with the QFT as a component that can be treated as a black box first and opened later.
- **Interactive** — pick n, run period-finding, see the period, then complete the classical post-processing to get a factor.
- **Sim** — factor small numbers for real (15 = 3 × 5 is the classic and it actually fits).
- **Prerequisite** — the Quantum Fourier Transform, which needs its own treatment first (see Part 3).
- **Code** — Qiskit implementation of the order-finding core.
- **Compare** — classical sub-exponential vs quantum polynomial, and what that means concretely for RSA key sizes.
- **Assess** — "why can you not just read the period off the measurement directly?" (you get a multiple; the post-processing is where the work is).
- **Honest caveat** — factoring RSA-2048 needs orders of magnitude more qubits than exist. The threat is real and long-term, not imminent, and saying otherwise is the fastest way to lose credibility.

### C4. Quantum Key Distribution (QKD)

- **Concept** — the problem: agreeing a secret key over a channel an eavesdropper can read.
- **Concept** — BB84: conjugate bases, and why measuring in the wrong basis randomises the result.
- **Interactive** — play Alice, Bob, and optionally Eve. Sending and measuring is the fastest way to make the protocol click.
- **Interactive** — introduce Eve and watch the error rate rise; then do basis reconciliation and see the key shrink.
- **Derivation** — the intercept-resend attack, and why it introduces a 25% error rate. That number is derivable and worth deriving.
- **Sim** — run full BB84 with eavesdropping and privacy amplification.
- **Concept** — E91, the entanglement-based version, which ties back to Bell states and the CHSH game.
- **Concept** — security proofs, stated at the level of "here is the assumption, here is what is proven" rather than in full.
- **Compare** — QKD vs post-quantum cryptography. They solve different problems and are often confused. QKD needs a quantum channel; PQC does not.
- **Assess** — "what exactly does QKD protect against, and what does it not?" (it does not authenticate; it needs an authenticated classical channel).
- **Applications** — where it is actually deployed today.

---

## Part 3 — Missing Topics

Topics absent from the three sessions above that a comprehensive platform would want.

### Mathematical foundations
- **Linear algebra** — vectors, matrices, eigenvalues/eigenvectors, Hermitian and unitary matrices, change of basis. The single highest-leverage prerequisite; most confusion in quantum computing is linear-algebra confusion wearing a costume.
- **Complex numbers** — arithmetic, the complex plane, Euler's formula, magnitude and phase. Needed before phase means anything.
- **Probability** — distributions, expectation, variance, sampling error, confidence intervals. Needed before a histogram can be read honestly.
- **Group theory (light)** — enough to make "why are gates unitary" feel motivated rather than arbitrary.

### Core quantum theory
- **Measurement theory** — general measurements (POVMs), projective measurements, and why the distinction matters. Currently only the projective case is implied.
- **Quantum states** — pure vs mixed, density matrices, partial trace, reduced states. Essential for noise and for entanglement of subsystems.
- **Unitary operations** — as a topic in its own right, including the connection to reversible classical computation.
- **Quantum interference** — deserves standalone treatment rather than being a side effect of the double slit. It is the mechanism behind every speedup.
- **Quantum entanglement** — as a topic separate from Bell states: entanglement entropy, monogamy, entanglement as a resource.
- **Quantum phase** — global vs relative phase, and why only the relative phase is observable. Small topic, disproportionate payoff.
- **No-cloning and no-deleting theorems** — short, and they explain several otherwise-arbitrary constraints.
- **Quantum channels** — the general formalism for noise, of which depolarising and amplitude damping are examples.

### Gates and circuits
- **Gates beyond the basics** — Toffoli and multi-controlled gates, controlled rotations, arbitrary single-qubit rotations (U3), iSWAP, fSim.
- **Universality** — which gate sets are universal, and why. Ties directly to the Clifford/non-Clifford split the composer already colours.
- **Circuit identities and optimisation** — gate cancellation, commutation rules, rewriting. Practical and immediately useful.
- **Multi-qubit systems** — GHZ vs W states, and why W is more robust to loss.
- **Quantum circuit compilation / transpilation** — logical circuit to hardware-native gates, qubit routing and SWAP insertion, and why the compiled circuit differs from the one drawn. This is where theory meets real hardware and it is almost never taught.
- **Resource estimation** — qubit count, gate count, circuit depth, and T-count. Needed before anyone can judge whether an algorithm is feasible.

### Algorithms beyond the four
- **Quantum Fourier Transform** — as a first-class topic. It is a prerequisite for Shor and for phase estimation, and it is beautiful on its own.
- **Phase estimation** — the subroutine behind Shor, and the cleanest demonstration of the QFT doing work.
- **Simon's algorithm** — historically the precursor to Shor; simpler, and the oracle separation it gives is worth knowing.
- **Bernstein–Vazirani** — a one-query algorithm that is almost trivial to follow and makes phase kickback unmistakable. An excellent teaching algorithm.
- **Quantum walks** — a different algorithmic paradigm, and the basis of several speedups.
- **Amplitude estimation** — the generalisation of amplitude amplification to estimating probabilities, with a quadratic speedup over classical sampling.
- **HHL / linear systems** — worth mentioning for completeness, with the heavy caveats about its assumptions stated plainly.

### Variational and NISQ-era algorithms
- **Variational Quantum Eigensolver (VQE)** — the canonical NISQ algorithm: ansatz, parameterised circuit, classical optimiser loop.
- **QAOA** — combinatorial optimisation, with the approximation ratio as the thing to plot.
- **Parameterised circuits and gradients** — the parameter-shift rule, barren plateaus. Barren plateaus in particular explain why variational methods are harder than they first look.
- **Quantum machine learning** — data encoding strategies, kernel methods, and an honest account of the current state of the field, including the dequantisation critiques.

### Error correction and fault tolerance
- **Quantum error correction** — the three-qubit bit-flip and phase-flip codes as the entry point, then the surface code conceptually. Why continuous error and the no-cloning theorem make this harder than classical error correction.
- **Stabiliser formalism** — the language error correction is actually written in.
- **Fault-tolerant quantum computing** — logical vs physical qubits, the threshold theorem, and the overhead it implies. This is what makes resource estimates honest.
- **Quantum error mitigation** — as distinct from correction: zero-noise extrapolation, probabilistic error cancellation, readout mitigation. Practical today, unlike full correction.

### Hardware and the ecosystem
- **Quantum hardware** — superconducting, trapped ion, photonic, neutral atom, spin: how each works, and what its strengths and limits are.
- **NISQ computing** — what the current era is, what it can and cannot do, and why the name matters.
- **Hardware noise models** — calibrated device noise, not just idealised channels. Connecting simulated noise to a real backend's reported error rates.
- **Quantum architectures** — connectivity topologies, and why layout constrains compilation.
- **Quantum complexity** — BQP, its relation to P, NP, and BPP, and what is and is not known. Stated carefully; this is where popular accounts go wrong most often.
- **Classical vs quantum complexity** — the honest comparison, including the cases where quantum gives no useful advantage.
- **The current ecosystem** — Qiskit, Cirq, PennyLane, CUDA-Q, Braket, and the major hardware providers. A map, not a tutorial. Useful because learners otherwise assume Qiskit is the whole field.
- **Benchmarking** — how algorithms and hardware are compared: quantum volume, CLOPS, and the limits of each metric.

### Communication and simulation
- **Quantum communication** — beyond QKD: superdense coding, quantum repeaters, the quantum internet as a programme.
- **Quantum cryptography** — beyond QKD: post-quantum cryptography, and the distinction from quantum cryptography proper.
- **Quantum simulation** — simulating physical systems, Feynman's original motivation, Trotterisation. Arguably the most likely source of practical advantage.

---

## Part 4 — Platform-Level Educational Features

Capabilities that would make this an all-in-one environment rather than a good set of lessons.

### Structure and progression
- **Structured learning paths** — curated sequences, not just a flat topic list. "I want to understand Shor" should produce an ordered route with the prerequisites filled in.
- **Beginner → advanced progression** — explicit levels per topic, so the same topic can be revisited at depth.
- **Prerequisite mapping** — a dependency graph between topics, shown to the learner, with "you are missing this" warnings and a way to fill gaps.
- **Topic mastery** — per-topic competence inferred from assessment performance, with the confidence shown rather than hidden behind a single bar.
- **Placement / diagnostic** — a short initial test that skips what the learner already knows.

### Learning modes
- **Interactive lessons** — the default mode: explanation interleaved with things to do, not a wall of text followed by an exercise.
- **Practice mode** — unlimited attempts, hints available, no record.
- **Challenge mode** — the existing Challenges page, extended.
- **Exam mode** — timed, no hints, single attempt. Genuinely different from practice, and worth separating.
- **Project-based learning** — longer tasks with several stages: implement Deutsch–Jozsa, extend it, break it, fix it.
- **Virtual labs** — guided experiments with a hypothesis, a procedure, and a conclusion, rather than free play.

### Playgrounds
- **Circuit playground** — the existing Playground, expanded.
- **Qiskit playground** — a code environment with a circuit preview and a results panel, so code and visualisation are never separated.
- **Algorithm playground** — algorithm templates with tunable parameters (oracle, iteration count, problem size) and a classical baseline running alongside.
- **Sandbox execution** — running learner Qiskit code server-side and returning real results. Substantial engineering; needs a sandbox with a strict time and memory budget, and probably a queue.

### Assessment and feedback
- **Quizzes** — per topic, with explanations shown after answering rather than just a score.
- **Assessments** — longer, multi-part, per module.
- **Automated feedback** — on wrong answers, explain the specific error, not just "incorrect".
- **Error explanations** — a catalogue of common mistakes per topic, matched to the answer given.
- **Concept checkpoints** — short gates between sections; you cannot proceed until the idea is demonstrated.
- **Spaced repetition** — revisiting earlier topics on a schedule.

### Tracking and analytics
- **Progress tracking** — per topic, per path, over time.
- **Learning analytics** — where learners get stuck, which is also the most valuable input for improving the material.
- **Experiment history** — every circuit run, kept, with its parameters and results, so a learner can return to something they did last week.
- **Saved circuits and saved experiments** — named, tagged, shareable.
- **Certificates / badges** — completion credentials. Only meaningful if the assessment behind them is real.

### Reference
- **Reference library** — the material organised for lookup rather than for study. Different navigation for a different task.
- **Formula sheet** — every identity and formula in one place, with each one linked to the lesson that derives it.
- **Quantum glossary** — every term, with a one-line definition and a link to the full treatment.
- **Interactive documentation** — the platform's own API and circuit model, documented against live examples.

### Visualisation and comparison tools
- **Visualisation toolkit** — Bloch sphere, state vector, density matrix, phase disk, Q-sphere, histogram, probability curve. Several of these already exist in the results suite and could be reused as teaching objects rather than only as run output.
- **Algorithm comparison tools** — run two algorithms on the same problem and compare query counts, gate counts, depth, and results side by side.
- **Classical-vs-quantum demonstrations** — one interface, two implementations, honest numbers on both sides. This is the most persuasive thing the platform can build, and it is also the easiest to do dishonestly.

---

## Suggested sequencing (if this is ever picked up)

Not a commitment — a dependency-aware order for whoever reads this later.

1. **Mathematical foundations** (linear algebra, complex numbers, probability). Nearly everything else is easier afterwards.
2. **Measurement theory, density matrices, interference, phase** — the conceptual gaps that cause the most trouble later.
3. **QFT and phase estimation** — prerequisites for Shor, and useful independently.
4. **Bernstein–Vazirani** — the cheapest possible way to make phase kickback obvious, ahead of Deutsch–Jozsa.
5. **Noise and error mitigation** — practical, and it makes every later result more honest.
6. **Variational algorithms** — after noise, because the motivation depends on it.
7. **Error correction and fault tolerance** — last of the theory; it assumes most of the rest.
8. **Platform features** — analytics and reference material can land at any point; structured paths are most useful once there is enough content to path through.

Two things worth protecting as this grows:

- **Every number shown should come from the engine.** The platform's standing rule is that nothing in the run path is faked. That rule should extend to teaching material: a hand-tuned "expected" histogram that disagrees with the simulator would be worse than no histogram.
- **Honest caveats on every algorithm.** Deutsch–Jozsa solves a contrived problem; Grover does not crack passwords; Shor is not an imminent threat to RSA-2048. Learners discover these things, and the platform is more credible if it says them first.
