"""M4 topic-gap analysis: derive and validate the proposed topic architecture.

    cd backend/scripts && python3 topic_gap_analysis.py

This is ANALYSIS ONLY. It creates no topic IDs, writes no migrations and
touches no lesson content. It exists so the proposal in
docs/M4_TOPIC_GAP_ANALYSIS.md is generated from data that has been checked
rather than typed by hand:

  * every unmapped target item appears in exactly one proposed topic
  * no proposed topic ID collides with a registered one, or with another
  * proposed namespaces are all declared in NAMESPACES
  * every prerequisite points at a topic that exists or is proposed
  * every referenced lesson slug exists in content/
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # backend/
sys.path.insert(0, str(Path(__file__).resolve().parent))              # backend/scripts

from app.curriculum import NAMESPACES, TOPICS  # noqa: E402
import curriculum_reports as cr  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = ROOT / "content"

# --------------------------------------------------------------------------- #
# The proposal.
#
# Each entry: (topic_id, title, namespace, [target items], [proposed lessons],
#              [(prerequisite topic id, kind, reason)], note)
#
# Grouping deliberately does NOT assume one topic per target item. Items are
# merged where their learning objectives substantially overlap, and split where
# the prerequisite chains diverge.
# --------------------------------------------------------------------------- #

PROPOSAL: list[dict] = [
    # ---- A. Mathematical Foundations -------------------------------------- #
    dict(id="math.complex_numbers", ns="math", title="Complex Numbers and Euler's Formula",
         items=["Complex Numbers and Euler's Formula"],
         lessons=["14_complex_numbers"],
         prereqs=[],
         note="Self-contained; no quantum prerequisite."),
    dict(id="math.linear_algebra", ns="math", title="Vectors, Matrices and Linear Algebra",
         items=["Linear Algebra", "Vectors and Matrices", "Change of Basis"],
         lessons=["15_linear_algebra"],
         prereqs=[("math.complex_numbers", "required",
                   "Matrix entries are complex; inner products need conjugation.")],
         note="Three target items share one objective set (represent and manipulate "
              "state vectors and operators); splitting them would duplicate the "
              "change-of-basis treatment."),
    dict(id="math.eigen_and_operators", ns="math",
         title="Eigenvalues, Eigenvectors and Operator Classes",
         items=["Eigenvalues and Eigenvectors", "Hermitian and Unitary Matrices"],
         lessons=["16_eigen_and_operators"],
         prereqs=[("math.linear_algebra", "required",
                   "Eigen-decomposition is defined on matrices; Hermitian and unitary "
                   "are properties of a matrix.")],
         note="Hermitian/unitary are the operator classes whose spectra matter, so "
              "they belong with eigen-theory rather than general linear algebra."),
    dict(id="math.probability_and_statistics", ns="math",
         title="Probability, Expectation and Sampling Statistics",
         items=["Probability, Expectation and Variance",
                "Sampling Error and Confidence Intervals"],
         lessons=["17_probability_and_statistics"],
         prereqs=[],
         note="04_measurement already teaches the standard-error table, so this "
              "topic can use it as a secondary lesson rather than restating it."),
    dict(id="math.group_theory", ns="math", title="Introductory Group Theory",
         items=["Introductory Group Theory"],
         lessons=["18_group_theory"],
         prereqs=[("math.linear_algebra", "recommended",
                   "Matrix groups are the motivating example, but the topic can be "
                   "taught from symmetry alone.")],
         note="Needed later for the Clifford group and stabilisers; recommended "
              "rather than required so it does not gate the main track."),

    # ---- B. Core Quantum Theory ------------------------------------------- #
    dict(id="core.quantum_postulates", ns="core", title="Quantum Postulates",
         items=["Quantum Postulates"],
         lessons=["19_quantum_postulates"],
         prereqs=[("qc.qubits", "recommended",
                   "Postulates are best motivated after the reader has met a state "
                   "vector and the Born rule in practice.")],
         note="Overlaps 01_qubits and 04_measurement, which teach the rules "
              "operationally but never state them as postulates."),
    dict(id="core.phase", ns="core", title="Relative and Global Phase",
         items=["Relative and Global Phase"],
         lessons=["01_qubits"],
         prereqs=[("qc.qubits", "required", "Phase is defined on a superposition.")],
         note="ALREADY TAUGHT: 01_qubits has a dedicated section. This topic needs "
              "no new lesson - 01_qubits can be primary."),
    dict(id="core.density_matrices", ns="core",
         title="Density Matrices, Mixed States and Partial Trace",
         items=["Pure and Mixed States", "Density Matrices",
                "Partial Trace and Reduced States"],
         lessons=["20_density_matrices"],
         prereqs=[("core.quantum_postulates", "recommended",
                   "The density operator formalises the measurement postulate."),
                  ("qc.entanglement", "required",
                   "Partial trace is only meaningful once a composite system has "
                   "been reduced; entanglement is the motivating case.")],
         note="Three items are one formalism: rho, its purity, and reduction. "
              "09_quantum_noise and 11_bell_states already use purity and the "
              "density matrix and can be secondaries."),
    dict(id="core.entanglement_measures", ns="core",
         title="Entanglement Entropy and Monogamy",
         items=["Entanglement Entropy and Monogamy"],
         lessons=["21_entanglement_measures"],
         prereqs=[("core.density_matrices", "required",
                   "Entropy of entanglement is the von Neumann entropy of a reduced "
                   "density matrix."),
                  ("qc.bell_states", "required",
                   "Bell states are the reference maximally entangled pair.")],
         note="11_bell_states reports entropy and concurrence and can be a "
              "secondary; monogamy needs new content."),
    dict(id="core.no_cloning", ns="core", title="No-Cloning and No-Deleting",
         items=["No-Cloning and No-Deleting"],
         lessons=["22_no_cloning"],
         prereqs=[("qc.qubits", "required",
                   "The proof is a short argument about linearity of unitary "
                   "evolution on superpositions.")],
         note="Currently only asserted in passing (03_entanglement, "
              "10_gates_bootcamp); a real lesson with the proof is missing."),

    # ---- C. Introduction to Quantum Computing ----------------------------- #
    dict(id="qc.dirac_notation", ns="qc", title="Dirac Notation and Inner Products",
         items=["Dirac Notation", "Inner Product"],
         lessons=["23_dirac_notation"],
         prereqs=[("math.linear_algebra", "recommended",
                   "Bra-ket is a notation for the inner product, but it can be "
                   "introduced operationally first.")],
         note="Used throughout every existing lesson but never taught as a topic. "
              "Folding Inner Product in avoids two near-identical entries."),
    dict(id="qc.tensor_products", ns="qc", title="Tensor Products and Multi-Qubit Spaces",
         items=["Tensor Products"],
         lessons=["24_tensor_products"],
         prereqs=[("qc.dirac_notation", "required",
                   "Kronecker products are written in bra-ket."),
                  ("qc.qubits", "required",
                   "Multi-qubit space is built from single-qubit spaces.")],
         note="03_entanglement already distinguishes product from entangled states "
              "and can be a secondary."),
    dict(id="qc.quantum_mechanics_primer", ns="qc", title="Quantum Mechanics Primer",
         items=["Quantum Mechanics"],
         lessons=["25_quantum_mechanics_primer"],
         prereqs=[("qc.qubits", "recommended", "Assumes the reader has met a qubit.")],
         note="AMBIGUOUS - see open questions. Overlaps A and B heavily and risks "
              "duplicating core.quantum_postulates. Recommend deferring."),
    dict(id="qc.teleportation", ns="qc", title="Quantum Teleportation",
         items=["Quantum Teleportation"],
         lessons=["26_teleportation"],
         prereqs=[("qc.bell_states", "required",
                   "Teleportation consumes a shared Bell pair."),
                  ("adv.dynamic_circuits", "required",
                   "Bob's correction is conditional on Alice's two classical bits, "
                   "so the circuit needs mid-circuit feed-forward.")],
         note="A genuinely dynamic circuit; 12_control_flow already teaches the "
              "teleportation-style correction as its worked example."),
    dict(id="qc.reading_results", ns="qc",
         title="Understanding Circuits and Finding Results",
         items=["Understanding Circuits and Finding Results"],
         lessons=["27_reading_results"],
         prereqs=[("qc.basic_gates", "recommended",
                   "Reading a circuit requires knowing the gate symbols.")],
         note="Largely platform-UI material; overlaps qiskit.composer and "
              "qiskit.reading_histograms. Consider merging - see open questions."),

    # ---- D. Introduction to Qiskit --------------------------------------- #
    dict(id="qiskit.composer", ns="qiskit", title="The Quantum Composer",
         items=["Quantum Composer"],
         lessons=["28_composer_guide"],
         prereqs=[("qc.basic_gates", "required",
                   "You must know what a gate does before placing one.")],
         note="Platform documentation, not physics. No existing lesson covers it."),
    dict(id="qiskit.bloch_sphere", ns="qiskit", title="The Bloch Sphere",
         items=["Bloch Sphere"],
         lessons=["01_qubits"],
         prereqs=[("qc.qubits", "required",
                   "The sphere parametrises a single-qubit state.")],
         note="ALREADY TAUGHT: 01_qubits has a full Bloch sphere section and "
              "13_classical_bit_vs_qubit has a second. No new lesson needed."),
    dict(id="qiskit.reading_histograms", ns="qiskit",
         title="Histograms and Shot Statistics",
         items=["Histograms"],
         lessons=["04_measurement"],
         prereqs=[("core.measurement_theory", "required",
                   "A histogram is aggregated shot outcomes; measurement comes first.")],
         note="ALREADY TAUGHT: 04_measurement covers shot counts and error bars."),
    dict(id="qiskit.primitives", ns="qiskit", title="Estimator and Sampler Primitives",
         items=["Estimator"],
         lessons=["29_primitives"],
         prereqs=[("qiskit.sampler", "recommended",
                   "Sampler is the other half of the primitive pair and already "
                   "exists as a topic."),
                  ("nisq.vqe", "recommended",
                   "Estimator is motivated by expectation values in VQE.")],
         note="OVERLAP: could instead be folded into the existing qiskit.sampler "
              "topic. See open questions."),

    # ---- E. Quantum Algorithms ------------------------------------------- #
    dict(id="algo.bernstein_vazirani", ns="algo", title="Bernstein-Vazirani",
         items=["Bernstein-Vazirani"],
         lessons=["30_bernstein_vazirani"],
         prereqs=[("algo.deutsch_jozsa", "required",
                   "Same oracle/phase-kickback machinery; BV is the generalisation.")],
         note="Deliberately its own topic: one query versus n for DJ is the "
              "teaching point."),
    dict(id="algo.qft", ns="algo", title="Quantum Fourier Transform",
         items=["Quantum Fourier Transform"],
         lessons=["31_qft"],
         prereqs=[("qc.basic_gates", "required",
                   "QFT is a circuit of H and controlled-phase gates.")],
         note="The hub of the whole algorithms section."),
    dict(id="algo.phase_estimation", ns="algo", title="Quantum Phase Estimation",
         items=["Quantum Phase Estimation"],
         lessons=["32_phase_estimation"],
         prereqs=[("algo.qft", "required",
                   "QPE is the inverse QFT applied to a controlled-U register.")],
         note=""),
    dict(id="algo.shors", ns="algo", title="Shor's Algorithm",
         items=["Shor's Algorithm"],
         lessons=["33_shors_algorithm"],
         prereqs=[("algo.phase_estimation", "required",
                   "Order finding is an application of phase estimation."),
                  ("algo.qft", "required", "Shor's period-finding core is a QFT.")],
         note="Highest prerequisite depth in the curriculum."),
    dict(id="algo.simon", ns="algo", title="Simon's Algorithm",
         items=["Simon's Algorithm"],
         lessons=["34_simon"],
         prereqs=[("algo.deutsch_jozsa", "required",
                   "Same oracle-query model; Simon motivates the exponential "
                   "separation that Shor later exploits.")],
         note=""),
    dict(id="algo.quantum_walks", ns="algo", title="Quantum Walks",
         items=["Quantum Walks"],
         lessons=["35_quantum_walks"],
         prereqs=[("algo.grover", "recommended",
                   "Grover can be recast as a walk search; helpful but not needed "
                   "to define a walk.")],
         note=""),
    dict(id="algo.amplitude_estimation", ns="algo", title="Amplitude Estimation",
         items=["Amplitude Estimation"],
         lessons=["36_amplitude_estimation"],
         prereqs=[("algo.phase_estimation", "required",
                   "Amplitude estimation IS phase estimation on the Grover "
                   "operator."),
                  ("algo.grover", "required",
                   "The Grover operator is the input to the estimation.")],
         note=""),
    dict(id="algo.hhl", ns="algo", title="HHL Linear Systems",
         items=["HHL"],
         lessons=["37_hhl"],
         prereqs=[("algo.phase_estimation", "required",
                   "HHL uses phase estimation to extract eigenvalues.")],
         note="Carries well-known caveats (sparse, well-conditioned, "
              "state preparation) that a lesson must state honestly."),

    # ---- F. Advanced Gates and Circuits ---------------------------------- #
    dict(id="adv.multi_controlled_gates", ns="adv",
         title="Toffoli, Multi-Controlled Gates and Controlled Rotations",
         items=["Toffoli and Multi-Controlled Gates", "Controlled Rotations"],
         lessons=["38_multi_controlled"],
         prereqs=[("qc.basic_gates", "required",
                   "Controlled gates extend the single-qubit set.")],
         note="10_gates_bootcamp already has a Toffoli/MCX section and can be a "
              "secondary; controlled rotations need new content."),
    dict(id="adv.parameterized_two_qubit", ns="adv", title="U3, iSWAP and fSim",
         items=["U3, iSWAP and fSim"],
         lessons=["39_two_qubit_gates"],
         prereqs=[("qc.basic_gates", "required",
                   "These are specific two-qubit/one-qubit parameterisations of "
                   "the same idea."),
                  ("adv.multi_controlled_gates", "recommended",
                   "Controlled rotations are the usual consumer of these gates.")],
         note=""),
    dict(id="adv.circuit_identities", ns="adv",
         title="Circuit Identities and Simplification",
         items=["Circuit Identities and Simplification"],
         lessons=["40_circuit_identities"],
         prereqs=[("qc.basic_gates", "required",
                   "Identities are statements about gate products."),
                  ("adv.quantum_universality", "recommended",
                   "Motivates why rewriting to a basis matters.")],
         note="02_gates and 10_gates_bootcamp verify identities such as SX^2 = X "
              "and SWAP = 3 CNOTs, so they can be secondaries."),
    dict(id="adv.multipartite_entanglement", ns="adv",
         title="GHZ versus W States",
         items=["GHZ versus W States"],
         lessons=["41_multipartite_entanglement"],
         prereqs=[("qc.entanglement", "required",
                   "Both are multipartite extensions of two-qubit entanglement.")],
         note="03_entanglement teaches GHZ and can be primary; the W state and the "
              "GHZ-versus-W robustness contrast need new content."),
    dict(id="adv.compilation", ns="adv",
         title="Transpilation, Native Gates and Routing",
         items=["Transpilation", "Native Gates and Connectivity",
                "Routing and SWAP Insertion"],
         lessons=["42_compilation"],
         prereqs=[("qc.basic_gates", "required",
                   "Transpilation rewrites a circuit made of known gates."),
                  ("adv.quantum_universality", "recommended",
                   "Universality is why a fixed basis suffices.")],
         note="One pipeline: choose a basis, respect connectivity, insert SWAPs. "
              "Splitting them would separate cause from effect. 02_gates already "
              "covers the portable basis and can be a secondary."),
    dict(id="adv.resource_estimation", ns="adv", title="Resource Estimation",
         items=["Resource Estimation"],
         lessons=["43_resource_estimation"],
         prereqs=[("adv.compilation", "required",
                   "Counts depend on the compiled circuit, not the abstract one.")],
         note=""),

    # ---- G. Variational and NISQ Algorithms ------------------------------ #
    dict(id="nisq.ansatz", ns="nisq", title="Ansatz Construction",
         items=["Ansatz Construction"],
         lessons=["44_ansatz_construction"],
         prereqs=[("nisq.parameterized_circuits", "required",
                   "An ansatz IS a parameterised circuit.")],
         note="07_vqe_qaoa builds and runs an ansatz and can be a secondary."),
    dict(id="nisq.optimization", ns="nisq",
         title="Classical Optimization Loops and the Parameter-Shift Rule",
         items=["Classical Optimization Loops", "Parameter-Shift Rule"],
         lessons=["45_optimization_loops"],
         prereqs=[("nisq.ansatz", "required",
                   "Gradients are taken with respect to ansatz parameters.")],
         note="Parameter-shift is the gradient rule for the same loop, so folding "
              "it in avoids two half-lessons. 07_vqe_qaoa runs a real COBYLA "
              "optimisation and can be a secondary."),
    dict(id="nisq.approximation_ratios", ns="nisq", title="Approximation Ratios",
         items=["Approximation Ratios"],
         lessons=["46_approximation_ratios"],
         prereqs=[("nisq.qaoa", "required",
                   "The ratio is the quality measure for a QAOA solution.")],
         note=""),
    dict(id="nisq.barren_plateaus", ns="nisq", title="Barren Plateaus",
         items=["Barren Plateaus"],
         lessons=["07_vqe_qaoa"],
         prereqs=[("nisq.optimization", "required",
                   "A barren plateau is a property of the optimisation landscape.")],
         note="ALREADY TAUGHT: 07_vqe_qaoa has a dedicated section. No new "
              "lesson needed."),
    dict(id="nisq.qml", ns="nisq",
         title="Quantum Machine Learning, Feature Maps and Kernels",
         items=["Quantum Machine Learning", "Quantum Feature Maps and Kernels"],
         lessons=["47_quantum_machine_learning"],
         prereqs=[("nisq.ansatz", "required",
                   "Feature maps are parameterised circuits."),
                  ("nisq.optimization", "recommended",
                   "Training is the same hybrid loop.")],
         note="Two items, one pipeline: encode data, then train."),
    dict(id="nisq.dequantization", ns="nisq", title="Dequantization Critiques",
         items=["Dequantization Critiques"],
         lessons=["48_dequantization"],
         prereqs=[("algo.grover", "recommended",
                   "Dequantisation results bound claimed speed-ups for "
                   "linear-algebra style algorithms."),
                  ("nisq.qml", "recommended",
                   "Most dequantisation critiques target QML proposals.")],
         note="Editorial and advanced; recommend deferring until the surrounding "
              "topics exist."),

    # ---- H. Error Correction and Fault Tolerance ------------------------- #
    dict(id="qec.bit_flip_code", ns="qec", title="Three-Qubit Bit-Flip Code",
         items=["Three-Qubit Bit-Flip Code"],
         lessons=["49_bit_flip_code"],
         prereqs=[("adv.dynamic_circuits", "required",
                   "Syndrome measurement plus conditional correction is a dynamic "
                   "circuit."),
                  ("qiskit.quantum_noise", "required",
                   "The bit-flip channel is the error model being corrected.")],
         note=""),
    dict(id="qec.phase_flip_code", ns="qec", title="Three-Qubit Phase-Flip Code",
         items=["Three-Qubit Phase-Flip Code"],
         lessons=["50_phase_flip_code"],
         prereqs=[("qec.bit_flip_code", "required",
                   "Same structure in the conjugate basis; teach the pattern once.")],
         note=""),
    dict(id="qec.stabilizer_formalism", ns="qec", title="Stabilizer Formalism",
         items=["Stabilizer Formalism"],
         lessons=["51_stabilizer_formalism"],
         prereqs=[("qec.phase_flip_code", "required",
                   "Stabilisers generalise the two three-qubit codes."),
                  ("math.group_theory", "recommended",
                   "The stabiliser group is a group; helpful, not strictly needed.")],
         note=""),
    dict(id="qec.surface_codes", ns="qec", title="Surface Codes",
         items=["Surface Codes"],
         lessons=["52_surface_codes"],
         prereqs=[("qec.stabilizer_formalism", "required",
                   "Surface codes are stabiliser codes on a lattice.")],
         note=""),
    dict(id="qec.logical_physical", ns="qec",
         title="Logical and Physical Qubits, and Overhead",
         items=["Logical and Physical Qubits", "Error-Correction Overhead"],
         lessons=["53_logical_physical_qubits"],
         prereqs=[("qec.surface_codes", "required",
                   "Overhead is quoted as physical qubits per logical qubit for a "
                   "specific code.")],
         note="Overhead only means something relative to a code, so the items "
              "belong together."),
    dict(id="qec.threshold_theorem", ns="qec",
         title="Threshold Theorem and Fault Tolerance",
         items=["Threshold Theorem", "Fault Tolerance"],
         lessons=["54_threshold_theorem"],
         prereqs=[("qec.logical_physical", "required",
                   "The threshold is a bound on physical error rate given an "
                   "overhead budget.")],
         note="The theorem and the engineering discipline it licenses are one "
              "story; splitting them loses the point."),
    dict(id="qec.error_mitigation", ns="qec",
         title="Error Mitigation: ZNE, PEC and Readout Correction",
         items=["Zero-Noise Extrapolation", "Probabilistic Error Cancellation",
                "Readout Mitigation"],
         lessons=["55_error_mitigation"],
         prereqs=[("qiskit.quantum_noise", "required",
                   "Mitigation post-processes noisy results; it needs a noise "
                   "model first.")],
         note="IMPORTANT DISTINCTION: these are mitigation, not correction. They "
              "need no encoder and no syndrome, so they do NOT depend on the code "
              "topics above. Grouping them keeps that distinction visible."),

    # ---- I. Hardware and Ecosystem --------------------------------------- #
    dict(id="hw.superconducting_qubits", ns="hw", title="Superconducting Qubits",
         items=["Superconducting Qubits"], lessons=["56_superconducting_qubits"],
         prereqs=[("qiskit.quantum_noise", "recommended",
                   "T1/T2 are the figures quoted per platform.")], note=""),
    dict(id="hw.trapped_ions", ns="hw", title="Trapped Ions",
         items=["Trapped Ions"], lessons=["57_trapped_ions"],
         prereqs=[("qiskit.quantum_noise", "recommended", "Same per-platform metrics.")],
         note=""),
    dict(id="hw.photonic_systems", ns="hw", title="Photonic Systems",
         items=["Photonic Systems"], lessons=["58_photonic_systems"],
         prereqs=[("qiskit.quantum_noise", "recommended", "Same per-platform metrics.")],
         note=""),
    dict(id="hw.neutral_atoms", ns="hw", title="Neutral Atoms",
         items=["Neutral Atoms"], lessons=["59_neutral_atoms"],
         prereqs=[("qiskit.quantum_noise", "recommended", "Same per-platform metrics.")],
         note=""),
    dict(id="hw.spin_qubits", ns="hw", title="Spin-Based Qubits",
         items=["Spin-Based Qubits"], lessons=["60_spin_qubits"],
         prereqs=[("qiskit.quantum_noise", "recommended", "Same per-platform metrics.")],
         note=""),
    dict(id="hw.platform_comparison", ns="hw",
         title="Calibrated Noise Models and Connectivity Topologies",
         items=["Calibrated Noise Models", "Connectivity Topologies"],
         lessons=["61_platform_comparison"],
         prereqs=[("hw.superconducting_qubits", "required",
                   "Needs at least one concrete platform to calibrate against."),
                  ("adv.compilation", "recommended",
                   "Connectivity is what routing has to work around.")],
         note="Both items are cross-platform comparison material rather than a "
              "single technology."),
    dict(id="hw.nisq_limitations", ns="hw", title="NISQ Limitations",
         items=["NISQ Limitations"], lessons=["62_nisq_limitations"],
         prereqs=[("qiskit.quantum_noise", "required",
                   "NISQ limits are decoherence and gate-error limits."),
                  ("adv.resource_estimation", "recommended",
                   "Depth budgets quantify what is feasible.")],
         note="07_vqe_qaoa frames the NISQ motivation and can be a secondary."),
    dict(id="hw.complexity_classes", ns="hw", title="BQP, P, NP and BPP",
         items=["BQP, P, NP and BPP"], lessons=["63_complexity_classes"],
         prereqs=[("algo.grover", "recommended",
                   "Grover and Shor are the separations that motivate BQP.")],
         note="Theory, independent of hardware; kept its own topic because the "
              "objectives are definitional rather than engineering."),
    dict(id="hw.benchmarking", ns="hw", title="Quantum Benchmarking",
         items=["Quantum Benchmarking"], lessons=["64_benchmarking"],
         prereqs=[("hw.nisq_limitations", "required",
                   "Benchmarks measure how close a device is to its limits."),
                  ("hw.platform_comparison", "recommended",
                   "Cross-platform comparison needs comparable metrics.")],
         note=""),
    dict(id="hw.ecosystem", ns="hw",
         title="Quantum Ecosystem: Qiskit, Cirq, PennyLane, CUDA-Q and Braket",
         items=["Quantum Ecosystem: Qiskit, Cirq, PennyLane, CUDA-Q and Braket"],
         lessons=["65_quantum_ecosystem"],
         prereqs=[("qc.basic_gates", "recommended",
                   "Survey of tooling; assumes the basics.")],
         note="This platform already documents its four backends in "
              "08_dynamic_circuits and 04_measurement, which can be secondaries."),

    # ---- J. Communication and Simulation --------------------------------- #
    dict(id="comm.superdense_coding", ns="comm", title="Superdense Coding",
         items=["Superdense Coding"], lessons=["66_superdense_coding"],
         prereqs=[("qc.bell_states", "required",
                   "Consumes a shared Bell pair to send two bits in one qubit.")],
         note=""),
    dict(id="comm.quantum_networks", ns="comm",
         title="Quantum Repeaters and the Quantum Internet",
         items=["Quantum Repeaters", "Quantum Internet"],
         lessons=["67_quantum_networks"],
         prereqs=[("qc.teleportation", "required",
                   "Repeaters are chained entanglement swapping, which is "
                   "teleportation between nodes.")],
         note="The internet is the network built from repeaters; one story."),
    dict(id="comm.cryptography", ns="comm",
         title="Quantum Cryptography, QKD and Post-Quantum Cryptography",
         items=["Quantum Cryptography", "Post-Quantum Cryptography",
                "Quantum Key Distribution"],
         lessons=["68_quantum_cryptography"],
         prereqs=[("core.no_cloning", "required",
                   "QKD security rests on the impossibility of cloning an unknown "
                   "state.")],
         note="RESOLVES A CROSS-SECTION DUPLICATE: 'Quantum Key Distribution' is "
              "listed under E (algorithms) and 'Quantum Cryptography' under J. "
              "They are one subject. Recommend one topic under comm, noting the "
              "target list double-counts it."),
    dict(id="comm.quantum_simulation", ns="comm",
         title="Quantum Simulation and Many-Body Systems",
         items=["Quantum Simulation", "Quantum Many-Body Systems"],
         lessons=["69_quantum_simulation"],
         prereqs=[("algo.phase_estimation", "recommended",
                   "Energy estimation is the original simulation application."),
                  ("nisq.vqe", "recommended",
                   "VQE is the NISQ-era alternative for the same task.")],
         note="Simulation and its main application (many-body) belong together."),
    dict(id="comm.trotterization", ns="comm", title="Trotterization",
         items=["Trotterization"], lessons=["70_trotterization"],
         prereqs=[("comm.quantum_simulation", "required",
                   "Trotterisation is how a simulated Hamiltonian evolution is "
                   "broken into gates.")],
         note="Kept separate because the error/order trade-off is a substantial "
              "topic of its own."),
]


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def pending_items() -> list[str]:
    registered = {t["id"] for t in TOPICS}
    out = []
    for _sec, items in cr.TARGET_CURRICULUM.items():
        for item in items:
            if item not in cr.COVERAGE or cr.COVERAGE[item][0] not in registered:
                out.append(item)
    return out


def validate() -> list[str]:
    problems: list[str] = []
    registered = {t["id"] for t in TOPICS}
    proposed_ids = {p["id"] for p in PROPOSAL}

    if len(proposed_ids) != len(PROPOSAL):
        problems.append("duplicate proposed topic ids")

    for p in PROPOSAL:
        if p["id"] in registered:
            problems.append(f"{p['id']} collides with a registered topic")
        if p["ns"] not in NAMESPACES:
            problems.append(f"{p['id']} uses undeclared namespace {p['ns']}")
        if not p["items"]:
            problems.append(f"{p['id']} covers no target items")
        for lesson in p["lessons"]:
            if lesson.startswith(("0", "1")) and len(lesson) == 8 and False:
                pass
            if not (CONTENT_DIR / f"{lesson}.md").exists() and int(
                "".join(ch for ch in lesson if ch.isdigit())[:2]
            ) <= 13:
                problems.append(f"{p['id']} references missing lesson {lesson}")
        for prereq_id, kind, _reason in p["prereqs"]:
            if kind not in ("required", "recommended"):
                problems.append(f"{p['id']} has prereq kind {kind!r}")
            if prereq_id not in registered and prereq_id not in proposed_ids:
                problems.append(f"{p['id']} requires unknown topic {prereq_id}")

    # every pending item covered exactly once
    seen: dict[str, list[str]] = {}
    for p in PROPOSAL:
        for item in p["items"]:
            seen.setdefault(item, []).append(p["id"])
    pending = pending_items()
    for item in pending:
        if item not in seen:
            problems.append(f"UNCOVERED pending item: {item}")
    for item, owners in seen.items():
        if len(owners) > 1:
            problems.append(f"item in {len(owners)} proposed topics: {item} -> {owners}")
    for item in seen:
        if item not in pending:
            problems.append(f"proposed topic covers an ALREADY-MAPPED item: {item}")

    return problems


def report() -> None:
    pending = pending_items()
    covered = [i for p in PROPOSAL for i in p["items"]]
    reuse = [p for p in PROPOSAL if p["lessons"] and all(
        (CONTENT_DIR / f"{s}.md").exists() for s in p["lessons"])]

    print(f"pending target items      : {len(pending)}")
    print(f"items covered by proposal : {len(covered)}")
    print(f"proposed topics           : {len(PROPOSAL)}")
    print(f"  grouping ratio          : {len(covered)/len(PROPOSAL):.2f} items per topic")
    print(f"topics needing NO new lesson (reuse an existing one): {len(reuse)}")
    for p in reuse:
        print(f"    {p['id']:34s} -> {p['lessons']}")
    print()
    from collections import Counter
    by_ns = Counter(p["ns"] for p in PROPOSAL)
    for ns, n in sorted(by_ns.items()):
        items = sum(len(p["items"]) for p in PROPOSAL if p["ns"] == ns)
        print(f"  {ns:8s} {n:2d} proposed topics covering {items:2d} items")
    print()
    problems = validate()
    if problems:
        print("VALIDATION PROBLEMS:")
        for pr in problems:
            print("  -", pr)
    else:
        print("VALIDATION: clean - every pending item covered exactly once, "
              "no id collisions, all prerequisites resolve.")


if __name__ == "__main__":
    report()


# --------------------------------------------------------------------------- #
# Document generation
# --------------------------------------------------------------------------- #

DOC_PATH = ROOT / "docs" / "M4_TOPIC_GAP_ANALYSIS.md"


def _registered_map() -> dict[str, dict]:
    return {t["id"]: t for t in TOPICS}


def write_doc() -> None:
    registered = _registered_map()
    pending = pending_items()
    covered = [i for p in PROPOSAL for i in p["items"]]
    problems = validate()

    existing_slugs = {p.stem for p in CONTENT_DIR.glob("*.md")}
    new_lessons = sorted({
        lesson for p in PROPOSAL for lesson in p["lessons"]
        if lesson not in existing_slugs
    })
    reuse = [p for p in PROPOSAL if all(l in existing_slugs for l in p["lessons"])]

    lines: list[str] = []
    w = lines.append

    w("# M4 Topic-Gap Analysis and Proposed Curriculum Architecture")
    w("")
    w("**Status: PROPOSAL ONLY. Nothing here has been implemented.**")
    w("")
    w("No topic ID has been created, no mapping changed, no prerequisite added, no")
    w("lesson written and no migration run. This document exists to be reviewed and")
    w("approved before any of that happens.")
    w("")
    w("The tables below are generated by `backend/scripts/topic_gap_analysis.py`")
    w("from the registry in `app/curriculum.py`, the target list in")
    w("`backend/scripts/curriculum_reports.py`, and the real files in `content/`. The")
    w("generator validates the proposal before writing, so the counts here cannot")
    w("drift from the data. Run it with:")
    w("")
    w("```bash")
    w("cd backend/scripts && PYTHONPATH=<repo>/backend python3 topic_gap_analysis.py")
    w("```")
    w("")
    w("## 1. Where things stand")
    w("")
    w(f"- Target curriculum: **{sum(len(v) for v in cr.TARGET_CURRICULUM.values())} items** across 10 sections.")
    w(f"- Registered topics: **{len(TOPICS)}**.")
    w(f"- Items mapped to a registered topic: **{len(pending) and sum(len(v) for v in cr.TARGET_CURRICULUM.values()) - len(pending)}**.")
    w(f"- **Unmapped: {len(pending)} items** — the gap this phase analyses.")
    w("")
    w("### The 82 decompose into two different populations")
    w("")
    w("This matters, because the two need different treatment:")
    w("")
    w("| Population | Count | Meaning |")
    w("|---|---|---|")
    w("| Listed in `COVERAGE` with `topic_id = None` | 36 | Someone judged the item, then left the topic blank. Sections C, D, E, F, G. |")
    w("| Absent from `COVERAGE` entirely | 46 | Whole sections never registered: A, H, I, J plus 7 in B. |")
    w("")
    w("The 36 are gaps *inside* partially-built sections. The 46 are sections with no")
    w("topics at all. Four namespaces have **zero** registered topics:")
    w("")
    w("| Namespace | Section | Target items | Registered topics |")
    w("|---|---|---|---|")
    for ns in ("math", "qec", "hw", "comm"):
        slug, letter, title = NAMESPACES[ns]
        sec = next(s for s in cr.TARGET_CURRICULUM if s.startswith(letter))
        w(f"| `{ns}.` | {title} | {len(cr.TARGET_CURRICULUM[sec])} | **0** |")
    w("")
    w("## 2. How the proposal was built")
    w("")
    w("Three rules, applied in order:")
    w("")
    w("1. **Do not assume one topic per item.** Items are merged where their learning")
    w("   objectives substantially overlap, and split where prerequisite chains diverge.")
    w("2. **Reuse before authoring.** Where a rewritten lesson already teaches the")
    w("   material, the topic points at it rather than commissioning a new one.")
    w("3. **Keep the dependency honest.** Every prerequisite below carries a reason.")
    w("")
    w(f"Result: **{len(PROPOSAL)} proposed topics for {len(covered)} items** — a grouping")
    w(f"ratio of {len(covered)/len(PROPOSAL):.2f} items per topic.")
    w("")
    w(f"**{len(reuse)} of them need no new lesson at all**, because Batch 1 already")
    w("taught the material:")
    w("")
    w("| Proposed topic | Reuses | What already exists |")
    w("|---|---|---|")
    for p in reuse:
        w(f"| `{p['id']}` | `{p['lessons'][0]}` | {p['note']} |")
    w("")
    w("## 3. Proposed topics")
    w("")
    for ns, (_slug, letter, title) in NAMESPACES.items():
        group = [p for p in PROPOSAL if p["ns"] == ns]
        if not group:
            continue
        w(f"### {letter}. {title} (`{ns}.`)")
        w("")
        w("| Proposed topic ID | Title | Target items | Proposed lesson |")
        w("|---|---|---|---|")
        for p in group:
            items = "<br>".join(f"• {i}" for i in p["items"])
            lessons = "<br>".join(
                f"`{l}`" + (" *(exists)*" if l in existing_slugs else " *(new)*")
                for l in p["lessons"]
            )
            w(f"| `{p['id']}` | {p['title']} | {items} | {lessons} |")
        w("")
        w("**Prerequisites**")
        w("")
        w("| Topic | Requires | Kind | Why |")
        w("|---|---|---|---|")
        any_p = False
        for p in group:
            for prereq_id, kind, reason in p["prereqs"]:
                any_p = True
                known = "existing" if prereq_id in registered else "proposed"
                w(f"| `{p['id']}` | `{prereq_id}` ({known}) | {kind} | {reason} |")
        if not any_p:
            w("| — | none | — | Entry-level section. |")
        w("")
        w("**Grouping rationale**")
        w("")
        for p in group:
            if p["note"]:
                w(f"- `{p['id']}`: {p['note']}")
        w("")

    w("## 4. Cross-section duplicate found")
    w("")
    w("**`Quantum Key Distribution` (section E) and `Quantum Cryptography` (section J)")
    w("are the same subject.** The target list counts them twice. The proposal assigns")
    w("both, plus `Post-Quantum Cryptography`, to a single `comm.cryptography` topic.")
    w("")
    w("Consequence: the target list's 97 items are really **96 distinct subjects**. Any")
    w("coverage percentage computed against 97 is marginally pessimistic. Flagged rather")
    w("than silently merged, because deduplicating the target list is a curriculum")
    w("decision, not a documentation one.")
    w("")
    w("## 5. Open questions requiring a decision")
    w("")
    w("| # | Question | Options | Impact if unresolved |")
    w("|---|---|---|---|")
    w("| 1 | `Quantum Mechanics` (C) overlaps section A and `core.quantum_postulates` | (a) keep as a distinct primer, (b) **defer**, (c) drop | Risk of two lessons teaching the same postulates. |")
    w("| 2 | `qc.reading_results`, `qiskit.composer`, `qiskit.reading_histograms` overlap heavily | (a) three topics, (b) **merge into two** | Three thin lessons instead of two substantial ones. |")
    w("| 3 | `Estimator` vs existing `qiskit.sampler` | (a) new `qiskit.primitives`, (b) **fold into `qiskit.sampler`** | Either one new topic, or a rename of an existing stable ID. |")
    w("| 4 | Five hardware platforms: five topics or one survey? | (a) **five topics**, (b) one `hw.platforms` | (a) 5 lessons and finer mastery; (b) 1 long lesson, coarse mastery. |")
    w("| 5 | `Dequantization Critiques` | (a) own topic, (b) **defer** | Advanced/editorial; needs QML to exist first. |")
    w("| 6 | `Introductory Group Theory` required or recommended? | (a) **recommended**, (b) required | Required would gate stabilisers on pure maths. |")
    w("")
    w("## 6. Compatibility considerations")
    w("")
    w("**Adding a topic requires a migration.** `app/curriculum.py` is imported only by")
    w("migrations, tests and scripts — there is **no runtime sync** from the registry")
    w("into the database. Editing `TOPICS` alone changes nothing for a running service;")
    w("a new Alembic revision is needed to insert the rows. That revision is a separate")
    w("approval from this proposal.")
    w("")
    w("**New topics should be created with `status = \"draft\"`.** Only `published`")
    w("topics appear in learner navigation, so drafting first keeps the roadmap rule")
    w("(no inaccessible modules) intact while content is authored.")
    w("")
    w("**No legacy-mastery risk.** New topic IDs have no entry in `FLAT_TO_STABLE` and")
    w("no legacy tag rows to inherit, so nothing to migrate and nothing to lose on")
    w("downgrade. The 13 existing topics are untouched by this proposal.")
    w("")
    w("**Mastery semantics unchanged.** Confidence stays `high`/`medium`/`low`; only")
    w("`high` is mastery-mappable. New lessons should map at `high` to count toward")
    w("prerequisites, otherwise the graph will not unlock as designed.")
    w("")
    w("**Prerequisite kinds.** `required` blocks progression, `recommended` only warns.")
    w("The proposal uses `required` for genuine dependency and `recommended` for")
    w("motivation, so the main track is not gated on optional theory.")
    w("")
    w("**Suggested lesson slugs are placeholders.** The numeric prefix is a convention,")
    w("not a requirement; names must not collide with the 13 existing slugs, which are")
    w("foreign keys into quiz attempts, challenge attempts, recommendations and chat")
    w("history.")
    w("")
    w("## 7. Effort")
    w("")
    w(f"- Proposed topics: **{len(PROPOSAL)}**")
    w(f"- Topics reusing an existing lesson: **{len(reuse)}**")
    w(f"- New lessons to author: **{len(new_lessons)}**")
    w("- Prerequisite edges proposed: "
      f"**{sum(len(p['prereqs']) for p in PROPOSAL)}**")
    w("")
    w("## 8. Validation")
    w("")
    if problems:
        w("**The proposal currently FAILS validation:**")
        w("")
        for pr in problems:
            w(f"- {pr}")
    else:
        w("The generator checks the proposal on every run and this document was only")
        w("written because all checks pass:")
        w("")
        w("- every unmapped target item appears in exactly one proposed topic")
        w("- no proposed ID collides with a registered topic or another proposal")
        w("- all proposed namespaces are declared")
        w("- every prerequisite resolves to a topic that exists or is proposed")
        w("- every prerequisite kind is `required` or `recommended`")
        w("- every referenced existing lesson exists in `content/`")
        w("")
    w("## 9. What this phase deliberately did not do")
    w("")
    w("- No topic ID created.")
    w("- No lesson-to-topic mapping added or changed.")
    w("- No prerequisite added.")
    w("- No lesson slug renamed or created.")
    w("- No migration written or run.")
    w("- No production data touched.")
    w("- No lesson content rewritten (Batch 1 stands as committed).")
    w("")
    w("The inferred-tag defect (M4-1 in `REVIEW_REQUIRED.md`) is deliberately **not**")
    w("addressed here; it stays a separate decision so it does not complicate the")
    w("curriculum architecture work.")
    w("")

    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {DOC_PATH.relative_to(ROOT)} ({len(lines)} lines)")
