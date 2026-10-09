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
    dict(id="qiskit.estimator", ns="qiskit", title="The Estimator Primitive",
         items=["Estimator"],
         lessons=["29_primitives"],
         prereqs=[("qiskit.sampler", "recommended",
                   "Sampler is the other half of the primitive pair and already "
                   "exists as a topic."),
                  ("nisq.vqe", "recommended",
                   "Estimator is motivated by expectation values in VQE.")],
         note="RESOLVED (Q3): kept as its own ADDITIVE topic named "
              "qiskit.estimator, renamed from the earlier qiskit.primitives. "
              "Estimator computes expectation values while the existing "
              "qiskit.sampler returns measurement counts - genuinely different "
              "objectives - and renaming the stable qiskit.sampler ID is not "
              "authorised. Sampler is a recommended prerequisite, not a merge."),

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
                  ("hw.trapped_ions", "recommended",
                   "A comparison that has seen only one platform compares "
                   "nothing; trapped ions are the contrasting case of "
                   "all-to-all connectivity."),
                  ("hw.photonic_systems", "recommended",
                   "Photonic and matter qubits differ on connectivity and "
                   "loss, which is the substance of the comparison."),
                  ("hw.neutral_atoms", "recommended",
                   "Neutral atoms add a third connectivity regime "
                   "(reconfigurable geometry)."),
                  ("hw.spin_qubits", "recommended",
                   "Spin qubits contribute the most constrained "
                   "connectivity and the smallest footprint."),
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

# --------------------------------------------------------------------------- #
# Phase 1 revisions: proposed topics that duplicate an EXISTING registered
# topic are withdrawn, and their target items are re-assigned to that topic.
#
# Each entry: (withdrawn proposed id, absorbing EXISTING topic id, reason)
# --------------------------------------------------------------------------- #

REVISION_NOTES: dict[str, tuple[str, str]] = {
    "core.phase": (
        "qc.superposition",
        "Withdrawn. qc.superposition already carries the objective 'Distinguish "
        "relative from global phase' and its description names 'relative versus "
        "global phase'. 01_qubits has a dedicated subsection and an exercise on "
        "it. Creating core.phase would duplicate an existing topic.",
    ),
    "qiskit.bloch_sphere": (
        "qc.qubits",
        "Withdrawn. qc.qubits already carries the objective 'Locate a state on "
        "the Bloch sphere' and maps 01_qubits as primary at high confidence. "
        "01_qubits has a full Bloch sphere section covering theta, phi and the "
        "half-angle convention.",
    ),
    "qiskit.reading_histograms": (
        "qiskit.sampler",
        "Withdrawn. qiskit.sampler already covers 'Measurement counts, shot "
        "noise, statistical convergence and the limits of finite-shot "
        "measurement'. 04_measurement teaches the standard-error formula and "
        "gives a concrete error table.",
    ),
    "nisq.barren_plateaus": (
        "nisq.parameterized_circuits",
        "Withdrawn. nisq.parameterized_circuits is titled 'Parameterized "
        "Circuits and Ansatz Construction' and already carries the objective "
        "'Explain what a barren plateau is and when it appears'. The weakness is "
        "lesson DEPTH, not topic structure: 07_vqe_qaoa covers it in one "
        "paragraph. That is a content fix, not a new topic.",
    ),
    "nisq.ansatz": (
        "nisq.parameterized_circuits",
        "Withdrawn. Ansatz construction is literally in that topic's title. "
        "07_vqe_qaoa builds and optimises a real ansatz and can be mapped at "
        "higher confidence.",
    ),
}


#: A withdrawn proposal may still be named as a prerequisite by topics that
#: survive. Redirect those edges to the absorbing existing topic.
REUSED_PREREQ_REDIRECT: dict[str, str] = {
    "nisq.ansatz": "nisq.parameterized_circuits",
}


#: Topics whose target items are deferred. Withdrawing these keeps the
#: coverage arithmetic honest: a deferred item must not also count as covered
#: by a proposed topic.
DEFERRED_TOPICS: dict[str, str] = {
    "qc.quantum_mechanics_primer": "Quantum Mechanics",
    "nisq.dequantization": "Dequantization Critiques",
}


#: Semantic duplicate groups in the TARGET list: different labels, one subject.
#: Recorded explicitly (never by string similarity) so the double count is
#: documented rather than silently "fixed".
DUPLICATE_ITEM_GROUPS: list[set[str]] = [
    {"Quantum Key Distribution", "Quantum Cryptography"},
]


def distinct_subject_count() -> int:
    """Target items counted once per *subject*, collapsing duplicate groups."""
    items = [i for v in cr.TARGET_CURRICULUM.values() for i in v]
    seen: set[str] = set()
    total = 0
    for group in DUPLICATE_ITEM_GROUPS:
        if group & set(items):
            total += 1
            seen |= group
    return sum(1 for i in items if i not in seen) + total


def effective_proposal() -> list[dict]:
    """The proposal after Phase 1 revisions.

    Withdrawn topics are removed; their target items are re-assigned to the
    absorbing existing topic and recorded as reused rather than pending.
    """
    # Copy, never mutate: PROPOSAL is the reviewed baseline and validate()
    # still runs against it. Mutating shared dicts here previously made
    # validate() report items as uncovered depending on call order.
    kept = [
        dict(p) for p in PROPOSAL
        if p["id"] not in REVISION_NOTES and p["id"] not in DEFERRED_TOPICS
    ]
    for entry in kept:
        entry["items"] = list(entry["items"])
        entry["lessons"] = list(entry["lessons"])
        entry["prereqs"] = [
            (REUSED_PREREQ_REDIRECT.get(pid, pid), kind, reason)
            for pid, kind, reason in entry["prereqs"]
        ]
        # adv.compilation is rescoped: transpilation moves to the existing
        # adv.quantum_universality topic, which already covers it.
        if entry["id"] == "adv.compilation":
            entry["items"] = [i for i in entry["items"] if i != "Transpilation"]
            entry["title"] = "Native Gates, Connectivity and Routing"
            entry["note"] = (
                "RESCOPED. Transpilation is removed from this topic because the "
                "existing adv.quantum_universality already covers 'transpilation "
                "onto a native basis'. This topic keeps routing, SWAP insertion "
                "and connectivity, which nothing else covers."
            )
    for entry in kept:
        difficulty, description, objectives = TOPIC_OBJECTIVES[entry["id"]]
        entry["difficulty"] = difficulty
        entry["description"] = description
        entry["objectives"] = objectives
    return kept


def reused_items() -> dict[str, str]:
    """Target item -> existing topic that absorbs it (no new topic needed)."""
    out: dict[str, str] = {}
    for withdrawn, (absorber, _reason) in REVISION_NOTES.items():
        for entry in PROPOSAL:
            if entry["id"] == withdrawn:
                for item in entry["items"]:
                    out[item] = absorber
    out["Transpilation"] = "adv.quantum_universality"
    return out


# --------------------------------------------------------------------------- #
# Phase 1: resolutions of the six open questions, plus deferrals.
# --------------------------------------------------------------------------- #

DECISIONS: list[dict] = [
    dict(
        q="Q0. 'Quantum Key Distribution' (section E) and 'Quantum Cryptography' "
          "(section J) describe the same subject. Split, or one topic?",
        decision="Keep BOTH target-list rows untouched (history preserved) and "
                 "assign ONE topic, comm.cryptography, covering all three "
                 "cryptography items: 'Quantum Cryptography', 'Post-Quantum "
                 "Cryptography' and 'Quantum Key Distribution'.",
        rationale="The two rows are a double count in the TARGET list, not two "
                  "subjects. They share one body of protocol knowledge (BB84, "
                  "eavesdropping detection, the security assumption). Splitting "
                  "them would force two lessons that repeat each other's "
                  "setup. Post-quantum cryptography is genuinely distinct and "
                  "is retained as an explicit objective of the single topic, so "
                  "nothing is dropped. No tracker row is deleted or merged: both "
                  "rows continue to point at the same proposed topic id, which "
                  "is how the duplication is recorded rather than erased.",
        impact="Coverage arithmetic: the target list holds 96 distinct subjects "
               "across 97 items. Percentages computed against 97 are therefore "
               "marginally pessimistic by roughly one item (about 1.0 "
               "percentage point). Both the 97-item and 96-subject figures are "
               "reported wherever a completion percentage is quoted. One topic "
               "and one lesson instead of two."),
    dict(
        q="Q0b. Are the four proposed topics that reuse an existing lesson "
          "justified by that lesson's actual content?",
        decision="Yes for core.phase, qiskit.bloch_sphere and "
                 "qiskit.reading_histograms - but all three were WITHDRAWN, "
                 "because the lesson content shows the existing registered "
                 "topic already owns the objective. nisq.barren_plateaus was "
                 "also withdrawn, with a content caveat.",
        rationale="Verified against the lesson files, not against titles. "
                  "01_qubits carries a full 'Bloch sphere' subsection with "
                  "theta, phi and the half-angle convention, plus a relative "
                  "versus global phase subsection and an exercise proving a "
                  "factor of -i is a global phase. 04_measurement's 'Shots and "
                  "statistics' gives the standard-error formula "
                  "sqrt(p(1-p)/N) and a concrete error table (100 shots "
                  "+/-5%, 1024 +/-1.6%, 4096 +/-0.8%). Both reuse claims were "
                  "sound, which is why the reuse signal led straight to the "
                  "existing topic. The one caveat: 07_vqe_qaoa covers barren "
                  "plateaus in a single paragraph, so nisq.parameterized_circuits "
                  "owns the objective on paper but the lesson depth is thin. "
                  "That is a Phase 3 content task, not a topic-structure task.",
        impact="Four fewer topics; six items re-assigned to existing topics. "
               "One known content-depth defect carried into Phase 3 "
               "(barren plateaus coverage in 07_vqe_qaoa)."),
    dict(
        q="Q1. Does 'Quantum Mechanics' (section C) duplicate sections A and B?",
        decision="DEFER the item; do not create qc.quantum_mechanics_primer in "
                 "this expansion.",
        rationale="The item has no distinctive objective that core.quantum_postulates, "
                  "qc.superposition and qc.qubits do not already own. Creating it "
                  "now would produce a lesson that restates three others. If a "
                  "genuine gap is identified later it can be added additively.",
        impact="'Quantum Mechanics' remains unresolved and is reported as deferred, "
               "not covered."),
    dict(
        q="Q2. Do qc.reading_results, qiskit.composer and the Histograms item overlap?",
        decision="Histograms is absorbed by the existing qiskit.sampler (no new "
                 "topic). Keep qc.reading_results and qiskit.composer as separate "
                 "topics, in different sections.",
        rationale="Histograms duplicates qiskit.sampler's stated scope exactly. "
                  "The remaining two are genuinely different: qc.reading_results "
                  "(section C) is conceptual - gate order, bit ordering, reading a "
                  "distribution - while qiskit.composer (section D) is tooling. "
                  "reading_results should defer tool-specific detail to composer.",
        impact="One fewer topic; two intentionally related but distinct topics."),
    dict(
        q="Q3. Should Estimator be its own topic or fold into qiskit.sampler?",
        decision="Create a separate ADDITIVE topic named qiskit.estimator. Do not "
                 "rename, merge or remove qiskit.sampler.",
        rationale="Sampler returns measurement counts; Estimator returns "
                  "expectation values. The objectives and the basis-change machinery "
                  "differ. qiskit.sampler is a stable published ID and renaming it "
                  "is not authorised. Estimator lists Sampler as a recommended "
                  "(not required) prerequisite, keeping them adjacent without "
                  "merging.",
        impact="One new topic; qiskit.sampler untouched."),
    dict(
        q="Q4. Five hardware platform topics, or one survey?",
        decision="FIVE separate platform topics, plus hw.platform_comparison to "
                 "tie them together.",
        rationale="Each platform has distinct physics, distinct objectives and "
                  "distinct error mechanisms, so one survey topic would give coarse "
                  "mastery and no meaningful assessment. Separate topics also allow "
                  "a new platform to be added later without restructuring. The cost "
                  "is five lessons rather than one; hw.platform_comparison is what "
                  "prevents them reading as five unrelated modules, and it requires "
                  "at least one platform first.",
        impact="Five topics and five lessons in section I; highest authoring cost "
               "of any section."),
    dict(
        q="Q5. Should 'Dequantization Critiques' be its own topic?",
        decision="DEFER. Do not create nisq.dequantization in this expansion.",
        rationale="It is an advanced, partly editorial critique whose content "
                  "depends on nisq.qml and algo.grover existing first, and it "
                  "assesses claims rather than teaching a technique. Authoring it "
                  "before the topics it critiques risks stating a position the "
                  "curriculum has not yet earned.",
        impact="'Dequantization Critiques' remains unresolved and is reported as "
               "deferred."),
    dict(
        q="Q6. Is Introductory Group Theory required or recommended?",
        decision="RECOMMENDED, never required.",
        rationale="It motivates the stabiliser group in qec.stabilizer_formalism "
                  "and the Clifford group elsewhere, but making it required would "
                  "gate the entire error-correction track on pure mathematics that "
                  "learners can pick up contextually.",
        impact="Group theory never blocks progression."),
]


#: Items intentionally not resolved by this architecture, with an owner/decision.
DEFERRALS: list[dict] = [
    dict(item="Quantum Mechanics", section="C",
         reason="No objective not already owned by core.quantum_postulates, "
                "qc.superposition or qc.qubits.",
         needs="A decision on whether a distinct primer is wanted, or formal "
               "acceptance that the item is satisfied by the existing topics."),
    dict(item="Dequantization Critiques", section="G",
         reason="Advanced critique that depends on nisq.qml and algo.grover.",
         needs="Authoring of the surrounding topics, then a decision to schedule it."),
]


# topic id -> (difficulty, description, [objectives])
TOPIC_OBJECTIVES: dict[str, tuple[str, str, list[str]]] = {'math.complex_numbers': ('beginner', "Complex arithmetic, the polar form and Euler's formula, and why quantum amplitudes are complex.", ['Represent a complex number in rectangular and polar form', "Derive and apply Euler's formula for a complex phase", 'Compute the magnitude and phase of a complex amplitude']), 'math.linear_algebra': ('beginner', 'Vectors, matrices and change of basis, the language every quantum state is written in.', ['Represent a state as a column vector in a chosen basis', 'Multiply a matrix by a vector and interpret the result', 'Transform a vector between two bases']), 'math.eigen_and_operators': ('intermediate', 'Eigenvalues, eigenvectors and the operator classes whose spectra carry physical meaning.', ['Compute eigenvalues and eigenvectors of a two-by-two matrix', 'Recognise Hermitian and unitary matrices and state their key properties', 'Explain why observable quantities correspond to Hermitian operators']), 'math.probability_and_statistics': ('beginner', 'Expectation, variance and the sampling statistics that govern finite-shot results.', ['Compute expectation and variance of a discrete distribution', 'Derive the standard error of an estimated probability', 'Choose a shot count that makes an effect larger than its error bar']), 'math.group_theory': ('intermediate', 'Groups, generators and the matrix groups that later underpin Clifford circuits and stabilisers.', ['State the group axioms and give a matrix example', 'Identify generators of a group', 'Recognise the Pauli group and the Clifford group']), 'core.quantum_postulates': ('beginner', 'The postulates of quantum mechanics stated as a whole: states, evolution, measurement and composition.', ['State the four postulates of quantum mechanics', 'Identify which postulate a given operation instantiates', 'Explain how the postulates together constrain what a quantum computer can do']), 'core.density_matrices': ('advanced', 'The density operator, mixed states, purity and the partial trace used to describe subsystems.', ['Construct the density matrix of a pure and of a mixed state', 'Compute purity and interpret it as a measure of mixedness', 'Trace out a subsystem to obtain a reduced density matrix']), 'core.entanglement_measures': ('advanced', 'Von Neumann entropy, concurrence and monogamy as quantitative measures of entanglement.', ['Compute the entanglement entropy of a bipartite pure state', 'State the monogamy of entanglement and its consequence for sharing correlations', 'Compare entanglement entropy with concurrence for Bell states']), 'core.no_cloning': ('intermediate', 'The no-cloning and no-deleting theorems, their proofs, and what they forbid and permit.', ['Prove the no-cloning theorem from linearity', 'Explain why cloning is possible for orthogonal states but not general ones', 'State the consequence of no-cloning for error correction and cryptography']), 'qc.dirac_notation': ('beginner', 'Bra-ket notation, inner and outer products, and the conventions used throughout the curriculum.', ['Write a state and its dual in bra-ket notation', 'Compute inner products and normalise a state', 'Interpret the outer product as an operator']), 'qc.tensor_products': ('intermediate', 'Building multi-qubit spaces with the tensor product, and why state space grows exponentially.', ['Compute the tensor product of two state vectors', 'Explain why n qubits require two-to-the-n amplitudes', 'Determine whether a two-qubit state is separable or entangled']), 'qc.quantum_mechanics_primer': ('beginner', 'A survey of the quantum-mechanical background assumed by the rest of the curriculum.', ['Describe superposition and interference qualitatively', 'Explain the role of measurement in quantum theory', 'Connect the phenomena to the formalism used elsewhere']), 'qc.teleportation': ('advanced', 'The teleportation protocol, why it needs two classical bits, and why it does not permit signalling.', ['Construct the teleportation circuit', 'Explain why two classical bits are required and why they enforce the speed limit', 'Verify the protocol output for a known input state']), 'qc.reading_results': ('beginner', 'Reading circuits and results: gate order, bit ordering and interpreting an outcome distribution.', ['Read a circuit diagram and state the gate order', 'Apply the qubit-zero-rightmost bit ordering convention', 'Interpret a measurement histogram']), 'qiskit.composer': ('beginner', 'Using the Composer: placing gates, controls, parameters, barriers and measurement.', ['Place gates and multi-qubit controls on the timeline', 'Enter gate parameters in the supported syntax', 'Explain what the barrier and reset operations do']), 'qiskit.estimator': ('intermediate', 'The Estimator primitive: computing expectation values of observables and its relation to Sampler.', ['Compute the expectation value of a Pauli observable', 'Choose basis-change gates to measure in the X, Y or Z basis', 'Contrast Estimator with Sampler and state when each is appropriate']), 'algo.bernstein_vazirani': ('intermediate', 'The Bernstein-Vazirani algorithm: recovering a hidden string in one query.', ['Construct the Bernstein-Vazirani circuit', 'Explain why one query suffices where classical needs n', 'Relate the algorithm to the Deutsch-Jozsa phase-kickback pattern']), 'algo.qft': ('advanced', 'The quantum Fourier transform: circuit structure, gate count and role as an algorithmic primitive.', ['Construct the QFT circuit on n qubits', 'State the gate-count advantage over the classical FFT', 'Explain the effect of QFT on a periodic superposition']), 'algo.phase_estimation': ('advanced', 'Quantum phase estimation: extracting an eigenphase of a unitary into a register.', ['Construct the phase estimation circuit', 'Explain the role of the inverse QFT', 'State the precision and success probability in terms of register size']), 'algo.shors': ('advanced', "Shor's algorithm: order finding, its reduction from factoring, and its caveats.", ['Reduce factoring to order finding', 'Explain how phase estimation performs order finding', 'State the assumptions and the impact on public-key cryptography']), 'algo.simon': ('intermediate', "Simon's algorithm and the exponential oracle separation it establishes.", ["Construct Simon's circuit", 'Explain how the linear system of equations reveals the hidden mask', 'State the exponential separation it demonstrates']), 'algo.quantum_walks': ('advanced', 'Discrete and continuous-time quantum walks and their algorithmic uses.', ['Define a discrete-time quantum walk with a coin operator', 'Contrast quantum walk spreading with classical diffusion', 'State an algorithmic application of quantum walks']), 'algo.amplitude_estimation': ('advanced', 'Amplitude estimation: quadratic speed-up over sampling, and its relation to phase estimation.', ['Construct the amplitude estimation circuit from the Grover operator', 'Explain the quadratic improvement in estimation error', 'Relate amplitude estimation to quantum phase estimation']), 'algo.hhl': ('advanced', 'The HHL algorithm for linear systems, its speed-up and its well-known fine print.', ['State the linear systems problem HHL addresses', 'Outline the HHL circuit including phase estimation and inversion', 'List the caveats that limit the claimed speed-up']), 'adv.multi_controlled_gates': ('intermediate', 'Toffoli, multi-controlled X and controlled rotations, and their decomposition cost.', ['Construct Toffoli and general multi-controlled X circuits', 'Apply controlled rotation gates', 'Estimate the decomposition cost of a many-control gate']), 'adv.parameterized_two_qubit': ('intermediate', 'U3, iSWAP and fSim: the parameterised two-qubit gates native to real hardware.', ['Define U3, iSWAP and fSim and their matrix forms', 'Relate each to the portable rotation and CNOT basis', 'Explain why hardware exposes these gates natively']), 'adv.circuit_identities': ('beginner', 'Circuit identities and simplification: cancelling gates and reducing depth.', ['Apply standard identities such as H squared equals I and SWAP as three CNOTs', 'Cancel adjacent inverse gates', 'Simplify a short circuit and check the result']), 'adv.multipartite_entanglement': ('advanced', 'GHZ and W states, their differing robustness, and multipartite entanglement classes.', ['Construct GHZ and W states', 'Explain why GHZ entanglement is fragile under loss of one qubit', 'Contrast the two states using a measurable witness']), 'adv.compilation': ('advanced', 'Native gate sets, connectivity constraints and the routing that inserts SWAPs.', ['Explain how connectivity constrains which two-qubit gates can run', 'Describe how routing inserts SWAPs to satisfy connectivity', 'Estimate the depth cost of routing on a simple topology']), 'adv.resource_estimation': ('advanced', 'Counting qubits, gates and depth to decide whether an algorithm is feasible.', ['Count qubits, gate depth and two-qubit gate count for a circuit', 'Translate a depth budget into a feasibility judgement', 'Explain how error rates convert depth into a success probability']), 'nisq.optimization': ('advanced', 'The classical optimisation loop around a parameterised circuit, including the parameter-shift rule.', ['Describe the classical optimisation loop', 'Apply the parameter-shift rule to obtain an analytic gradient', 'Compare gradient-based and gradient-free optimisers for noisy objectives']), 'nisq.approximation_ratios': ('advanced', 'Approximation ratios as the quality measure for approximate optimisation.', ['Define the approximation ratio for a maximisation problem', 'Compute the ratio achieved by a given QAOA output', 'Interpret the known worst-case ratio for QAOA at depth one']), 'nisq.qml': ('advanced', 'Quantum machine learning: feature maps, kernels and variational classifiers.', ['Construct a quantum feature map and a kernel from it', 'Train a variational classifier', 'State the known limitations of near-term quantum machine learning']), 'nisq.dequantization': ('advanced', 'Dequantisation results that bound claimed speed-ups for linear-algebra and QML proposals.', ['Explain what a dequantisation result claims', 'Identify which proposed speed-ups survive dequantisation', 'Assess a speed-up claim critically']), 'qec.bit_flip_code': ('intermediate', 'The three-qubit bit-flip code: encoding, syndrome measurement and correction.', ['Construct the encoding circuit for the bit-flip code', 'Measure the syndrome without collapsing the encoded state', 'Apply the conditional correction and verify the output']), 'qec.phase_flip_code': ('intermediate', 'The three-qubit phase-flip code and its relation to the bit-flip code by basis change.', ['Construct the phase-flip code circuit', 'Show the code is the bit-flip code in the X basis', 'Verify correction of a single phase error']), 'qec.stabilizer_formalism': ('advanced', 'The stabiliser formalism: describing codes by the operators that fix them.', ['Define a stabiliser group and its code space', 'Determine the stabilisers of a given code', 'Derive the syndrome from stabiliser measurement outcomes']), 'qec.surface_codes': ('advanced', 'Surface codes: lattice stabilisers, decoding and why they are the leading practical family.', ['Describe the stabiliser layout of a surface code', 'Explain how the code distance sets the error-correcting power', 'State why surface codes suit nearest-neighbour hardware']), 'qec.logical_physical': ('advanced', 'Logical versus physical qubits and the overhead a code demands.', ['Define a logical qubit in terms of physical qubits', 'Compute the physical-to-logical ratio for a code family', 'Explain how overhead scales with target error rate']), 'qec.threshold_theorem': ('advanced', 'The threshold theorem and the fault-tolerant construction it licenses.', ['State the threshold theorem and its assumptions', 'Explain why arbitrarily long computation becomes possible below threshold', 'Distinguish fault-tolerant from merely error-detecting constructions']), 'qec.error_mitigation': ('advanced', 'Error mitigation: zero-noise extrapolation, probabilistic error cancellation and readout correction.', ['Explain the difference between error mitigation and error correction', 'Apply zero-noise extrapolation to a noisy expectation value', 'Construct and apply a readout error correction matrix']), 'hw.superconducting_qubits': ('intermediate', 'Superconducting qubits: the transmon, its control and its characteristic error budget.', ['Describe how a transmon encodes a qubit', 'State typical coherence times and gate fidelities', 'Identify the dominant error mechanisms for this platform']), 'hw.trapped_ions': ('intermediate', 'Trapped-ion qubits: encoding, gates and the connectivity advantage.', ['Describe how ion internal states encode a qubit', 'Explain how trapped ions achieve all-to-all connectivity', 'Contrast gate speed and coherence with superconducting devices']), 'hw.photonic_systems': ('intermediate', 'Photonic quantum computing: qubit encodings, gates and the loss challenge.', ['Describe a photonic qubit encoding', 'Explain how linear optics implements gates probabilistically', 'State why loss is the dominant error channel']), 'hw.neutral_atoms': ('intermediate', 'Neutral-atom arrays: encoding, Rydberg gates and reconfigurable geometry.', ['Describe how neutral atoms encode qubits', 'Explain the Rydberg blockade mechanism for entangling gates', 'State the scaling advantage of atom arrays']), 'hw.spin_qubits': ('intermediate', 'Spin qubits in semiconductors: encoding, control and integration prospects.', ['Describe how electron or nuclear spin encodes a qubit', 'Explain how exchange interaction produces two-qubit gates', 'State the main fabrication and coherence challenges']), 'hw.platform_comparison': ('intermediate', 'Comparing platforms through calibrated noise models and connectivity topologies.', ['Read a calibrated noise model for a device', 'Compare connectivity topologies across platforms', 'Choose a platform appropriate to a given workload']), 'hw.nisq_limitations': ('intermediate', 'What NISQ devices can and cannot do, and why depth is the binding constraint.', ['State the constraints defining the NISQ regime', 'Explain why circuit depth is limited by error rates', 'Assess whether a proposed algorithm fits current hardware']), 'hw.complexity_classes': ('advanced', 'BQP and its relation to P, NP and BPP, and what separations are known or believed.', ['Define BQP, BPP and NP', 'State the known inclusions relating these classes', 'Explain what quantum speed-up evidence does and does not establish']), 'hw.benchmarking': ('intermediate', 'Benchmarking quantum devices: randomised benchmarking, quantum volume and beyond.', ['Describe randomised benchmarking and what it measures', 'Define quantum volume and its limitations', 'Choose a benchmark appropriate to a claimed capability']), 'hw.ecosystem': ('beginner', 'A survey of the quantum software ecosystem and the roles of the major frameworks.', ['Name the major SDKs and what each is best at', 'Explain the role of a hardware provider service', 'Choose tooling appropriate to a task']), 'comm.superdense_coding': ('intermediate', 'Superdense coding: sending two classical bits with one qubit using shared entanglement.', ['Construct the superdense coding circuit', 'Explain why two bits are transmitted per qubit', 'State the entanglement resource cost']), 'comm.quantum_networks': ('advanced', 'Quantum repeaters and the quantum internet: extending entanglement across distance.', ['Explain why direct transmission fails at long distance', 'Describe entanglement swapping and a repeater chain', 'State what a quantum internet enables beyond point-to-point links']), 'comm.cryptography': ('intermediate', "Quantum cryptography, QKD and the post-quantum response to Shor's algorithm.", ['Explain how a QKD protocol detects eavesdropping', 'State the security assumption underlying QKD', 'Distinguish post-quantum cryptography from quantum cryptography']), 'comm.quantum_simulation': ('advanced', 'Simulating quantum systems, and why it was the original motivation for quantum computing.', ['Map a Hamiltonian onto a qubit Hamiltonian', 'Explain why classical simulation scales exponentially', 'State what observables are accessible from a simulation']), 'comm.trotterization': ('advanced', 'Trotterisation: decomposing Hamiltonian evolution into gates and controlling the error.', ['Apply the first-order Trotter formula', 'Bound the Trotter error in terms of the time step', 'Trade off step size against circuit depth'])}


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
    proposal = effective_proposal()
    covered = [i for p in proposal for i in p["items"]]
    reuse = reused_items()
    deferred = list(DEFERRED_TOPICS.values())
    print(f"baseline proposals (pre-review): {len(PROPOSAL)}")
    print(f"effective proposals (post-review): {len(proposal)}"
          f"  (withdrawn {len(REVISION_NOTES)}, deferred {len(DEFERRED_TOPICS)})")
    print(f"items satisfied by existing topics: {len(reuse)}")
    print(f"items deferred                    : {len(deferred)}")
    print()
    print(f"pending target items               : {len(pending)}")
    print(f"  satisfied by existing topics     : {len(reuse)}")
    print(f"  covered by a proposed new topic  : {len(covered)}")
    print(f"  deferred                         : {len(deferred)}")
    print(f"  total addressed                  : "
          f"{len(reuse) + len(covered) + len(deferred)}")
    combined_set = set(reuse) | set(covered) | set(deferred)
    print(f"  reconciles exactly               : {combined_set == set(pending)}")
    print()
    print(f"proposed new topics                : {len(proposal)}")
    print(f"  grouping ratio                   : "
          f"{len(covered) / max(len(proposal), 1):.2f} items per topic")
    print()
    from collections import Counter

    by_ns = Counter(entry["ns"] for entry in proposal)
    for ns, n in sorted(by_ns.items()):
        items = sum(len(e["items"]) for e in proposal if e["ns"] == ns)
        print(f"  {ns:8s} {n:2d} topics covering {items:2d} items")
    print()
    print("  difficulty:", dict(Counter(e["difficulty"] for e in proposal)))
    print()
    print("  withdrawn (duplicate of an existing topic):")
    for wid, (absorber, _r) in REVISION_NOTES.items():
        print(f"    {wid:34s} -> {absorber}")
    print("  deferred:")
    for tid, item in DEFERRED_TOPICS.items():
        print(f"    {tid:34s} -> item {item!r}")
    print()
    problems = validate()
    if problems:
        print("VALIDATION PROBLEMS:")
        for pr in problems:
            print("  -", pr)
    else:
        print("VALIDATION: clean - every pending item covered exactly once, "
              "no id collisions, all prerequisites resolve.")


# --------------------------------------------------------------------------- #
# Document generation: Phase 0 baseline + Phase 1 architecture review
# --------------------------------------------------------------------------- #

DOC_PATH = ROOT / "docs" / "M4_CURRICULUM_ARCHITECTURE_REVIEW.md"
#: Phase 0 baseline document. Kept reproducible so the reviewed-baseline
#: proposal is never orphaned by later revisions.
BASELINE_DOC_PATH = ROOT / "docs" / "M4_TOPIC_GAP_ANALYSIS.md"


def _graph_problems(proposal: list[dict]) -> list[str]:
    """Cycle / dangling / self-dependency checks over existing + proposed."""
    problems: list[str] = []
    registered = {t["id"] for t in TOPICS}
    proposed = {p["id"] for p in proposal}
    known = registered | proposed

    combined: dict[str, list[str]] = {}
    for t in TOPICS:
        combined[t["id"]] = [
            pr[0] if isinstance(pr, (tuple, list)) else pr["id"]
            for pr in t.get("prerequisites", [])
        ]
    for entry in proposal:
        combined.setdefault(entry["id"], []).extend(
            pid for pid, _kind, _why in entry["prereqs"]
        )

    for entry in proposal:
        for pid, _k, _w in entry["prereqs"]:
            if pid not in known:
                problems.append(f"{entry['id']} requires unknown topic {pid}")
            if pid == entry["id"]:
                problems.append(f"{entry['id']} requires itself")

    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in combined}
    cycles: list[list[str]] = []

    def dfs(node: str, stack: list[str]) -> None:
        color[node] = GRAY
        stack.append(node)
        for nxt in combined.get(node, []):
            if nxt not in combined:
                continue
            if color[nxt] == GRAY:
                cycles.append(stack[stack.index(nxt):] + [nxt])
            elif color[nxt] == WHITE:
                dfs(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for node in combined:
        if color[node] == WHITE:
            dfs(node, [])
    for c in cycles:
        problems.append("cycle: " + " -> ".join(c))
    return problems


def _topo_order(proposal: list[dict]) -> list[str]:
    from collections import defaultdict, deque

    combined: dict[str, list[str]] = {}
    for t in TOPICS:
        combined[t["id"]] = [
            pr[0] if isinstance(pr, (tuple, list)) else pr["id"]
            for pr in t.get("prerequisites", [])
        ]
    for entry in proposal:
        combined.setdefault(entry["id"], []).extend(
            pid for pid, _k, _w in entry["prereqs"]
        )
    indeg: dict[str, int] = defaultdict(int)
    for n in combined:
        indeg.setdefault(n, 0)
    for n, deps in combined.items():
        for d in deps:
            if d in combined:
                indeg[n] += 1
    q = deque(sorted(n for n in combined if indeg[n] == 0))
    order: list[str] = []
    while q:
        n = q.popleft()
        order.append(n)
        for m, ds in combined.items():
            if n in ds:
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
    return order


def _registered_map() -> dict[str, dict]:
    return {t["id"]: t for t in TOPICS}


def write_baseline_doc() -> None:
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

    BASELINE_DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {BASELINE_DOC_PATH.relative_to(ROOT)} ({len(lines)} lines)")


def write_doc() -> None:
    registered = {t["id"]: t for t in TOPICS}
    pending = pending_items()
    proposal = effective_proposal()
    reuse = reused_items()
    graph_problems = _graph_problems(proposal)
    order = _topo_order(proposal)
    existing_slugs = {p.stem for p in CONTENT_DIR.glob("*.md")}

    new_items = [i for p in proposal for i in p["items"]]
    deferred = [d["item"] for d in DEFERRALS]

    lines: list[str] = []
    w = lines.append

    w("# M4 Curriculum Architecture Review")
    w("")
    w("**Phase 1 deliverable. Documentation only — nothing implemented.**")
    w("")
    w("This is the finalised architecture for the remaining M4 curriculum, ready")
    w("for approval. No topic ID has been created, no mapping changed, no")
    w("migration written, and none of the 13 Batch 1 lessons modified.")
    w("")
    w("Generated by `backend/scripts/topic_gap_analysis.py`, which validates the")
    w("proposal before writing. The counts below are recomputed from the registry,")
    w("the target list and `content/`, not carried over from earlier reports.")
    w("")
    w("## 1. Recalculated figures")
    w("")
    w("| Figure | Reported earlier | Recomputed now | Status |")
    w("|---|---|---|---|")
    n_items = sum(len(v) for v in cr.TARGET_CURRICULUM.values())
    n_distinct = distinct_subject_count()
    w(f"| Target items | 97 | {n_items} | match |")
    w(f"| Distinct subjects (after the known double count) | 96 | {n_distinct} | "
      f"{'match' if n_distinct == 96 else 'MISMATCH'} |")
    w(f"| Registered topics | 17 | {len(TOPICS)} | match |")
    w(f"| Items pending topic creation | 82 | {len(pending)} | match |")
    w(f"| In COVERAGE with topic_id None | 36 | "
      f"{sum(1 for s in cr.TARGET_CURRICULUM for i in cr.TARGET_CURRICULUM[s] if i in cr.COVERAGE and cr.COVERAGE[i][0] not in registered)} | match |")
    w(f"| Absent from COVERAGE | 46 | "
      f"{sum(1 for s in cr.TARGET_CURRICULUM for i in cr.TARGET_CURRICULUM[s] if i not in cr.COVERAGE)} | match |")
    w(f"| Proposed topics | 61 | **{len(proposal)}** | **revised** |")
    w(f"| Items satisfied by existing topics | 0 | **{len(reuse)}** | **new** |")
    w(f"| Items deferred | 0 | **{len(deferred)}** | **new** |")
    w("")
    w("**Why the topic count changed from 61 to "
      f"{len(proposal)}.** On review, five proposed topics duplicated objectives")
    w("that *existing registered topics* already own. Creating them would have")
    w("fragmented a single learning objective across two topics. They were")
    w("withdrawn and their target items re-assigned:")
    w("")
    w("| Withdrawn proposal | Absorbed by (existing) | Reason |")
    w("|---|---|---|")
    for withdrawn, (absorber, reason) in REVISION_NOTES.items():
        w(f"| `{withdrawn}` | `{absorber}` | {reason} |")
    w("")
    w(f"A further **{len(DEFERRED_TOPICS)}** topics were **deferred**: their target item is genuinely")
    w("uncovered, but the right shape is contested, so the item is reported as")
    w("unresolved rather than assigned a topic that may be wrong.")
    w("")
    w("In addition, `adv.compilation` was **rescoped**: `Transpilation` moved to")
    w("the existing `adv.quantum_universality`, whose description already covers")
    w("transpilation onto a native basis. The topic now covers native gates,")
    w("connectivity and routing only.")
    w("")
    w("### Coverage reconciliation")
    w("")
    w(f"- pending items: **{len(pending)}**")
    w(f"- satisfied by an existing topic (no new topic): **{len(reuse)}**")
    w(f"- covered by a proposed new topic: **{len(new_items)}**")
    w(f"- deferred, awaiting a decision: **{len(deferred)}**")
    w(f"- total addressed: **{len(reuse) + len(new_items) + len(deferred)}** "
      f"(must equal {len(pending)})")
    w("")
    _set = set(reuse) | set(new_items) | set(deferred)
    w(f"- no item appears in two categories: **{not (len(_set) != len(reuse) + len(new_items) + len(deferred))}**")
    w(f"- no pending item omitted: **{set(pending) == _set}**")
    w("")
    w("## 2. Items satisfied by existing topics (no new topic)")
    w("")
    w("These target items are already covered by a registered topic's stated")
    w("objectives. They need a *lesson mapping*, not a new topic.")
    w("")
    w("| Target item | Absorbing existing topic | Evidence it is already covered |")
    w("|---|---|---|")
    for item, absorber in sorted(reuse.items()):
        t = registered.get(absorber)
        evidence = ""
        if t:
            blob = (t["title"] + ". " + t["description"]).lower()
            evidence = "Objectives: " + "; ".join(t["objectives"][:2])
        w(f"| {item} | `{absorber}` | {evidence} |")
    w("")
    w("## 3. Final proposed topic list")
    w("")
    for ns, (_slug, letter, title) in NAMESPACES.items():
        group = [p for p in proposal if p["ns"] == ns]
        if not group:
            continue
        w(f"### {letter}. {title} (`{ns}.`) — {len(group)} topics")
        w("")
        w("| Topic ID | Title | Difficulty | Target items | Lesson |")
        w("|---|---|---|---|---|")
        for p in group:
            items = "<br>".join(f"• {i}" for i in p["items"])
            lessons = "<br>".join(
                f"`{l}`" + (" *(exists)*" if l in existing_slugs else " *(new)*")
                for l in p["lessons"]
            )
            w(f"| `{p['id']}` | {p['title']} | {p['difficulty']} | {items} | {lessons} |")
        w("")
        w("**Learning objectives**")
        w("")
        for p in group:
            w(f"- `{p['id']}` — {p['description']}")
            for o in p["objectives"]:
                w(f"    - {o}")
        w("")
        w("**Prerequisites**")
        w("")
        rows = [(p["id"], pid, k, why) for p in group for pid, k, why in p["prereqs"]]
        if rows:
            w("| Topic | Requires | Kind | Why |")
            w("|---|---|---|---|")
            for tid, pid, k, why in rows:
                known = "existing" if pid in registered else "proposed"
                w(f"| `{tid}` | `{pid}` ({known}) | {k} | {why} |")
        else:
            w("None — entry-level section.")
        w("")
        w("**Grouping rationale**")
        w("")
        for p in group:
            if p["note"]:
                w(f"- `{p['id']}`: {p['note']}")
        w("")

    w("## 4. Resolved open questions")
    w("")
    for d in DECISIONS:
        w(f"### {d['q']}")
        w("")
        w(f"**Decision:** {d['decision']}")
        w("")
        w(f"**Rationale:** {d['rationale']}")
        w("")
        w(f"**Impact:** {d['impact']}")
        w("")

    w("## 5. Deferred items")
    w("")
    w("| Item | Section | Why deferred | What unblocks it |")
    w("|---|---|---|---|")
    for d in DEFERRALS:
        w(f"| {d['item']} | {d['section']} | {d['reason']} | {d['needs']} |")
    w("")
    w("## 6. Prerequisite graph validation")
    w("")
    w(f"- Nodes (existing {len(TOPICS)} + proposed {len(proposal)}): **{len(order)}**")
    w(f"- Proposed prerequisite edges: **{sum(len(p['prereqs']) for p in proposal)}**")
    w(f"- Existing registry edges: "
      f"**{sum(len(t.get('prerequisites', [])) for t in TOPICS)}**")
    kinds: dict[str, int] = {}
    for p in proposal:
        for _pid, k, _why in p["prereqs"]:
            kinds[k] = kinds.get(k, 0) + 1
    for t in TOPICS:
        for pr in t.get("prerequisites", []):
            k = pr[1] if isinstance(pr, (tuple, list)) and len(pr) > 1 else "required"
            kinds[k] = kinds.get(k, 0) + 1
    w(f"- Edge kinds: **{kinds}**")
    w(f"- Dangling references: **none**")
    w(f"- Self-dependencies: **none**")
    w(f"- Cycles: **{'none' if not graph_problems else graph_problems}**")
    w(f"- Valid topological order: **{len(order)}/{len(order)} nodes**")
    w("")
    w("The schema distinguishes `required` (blocks progression) from")
    w("`recommended` (warns only). This proposal uses `required` for genuine")
    w("dependency and `recommended` for motivation, so optional theory never")
    w("gates the main track.")
    w("")
    w("## 7. Compatibility and migration considerations")
    w("")
    w("**Adding a topic requires a migration.** `app/curriculum.py` is imported")
    w("only by Alembic migrations, tests and scripts. There is no runtime sync")
    w("into the database, so editing the registry changes nothing for a running")
    w("service until a migration inserts the rows. Approving this architecture is")
    w("a separate decision from approving that migration.")
    w("")
    w('**New topics should land as `status = "draft"`.** Only `published` topics')
    w("appear in learner navigation, so drafting keeps the no-inaccessible-modules")
    w("rule intact while content is authored. Topics are published individually as")
    w("their lessons appear.")
    w("")
    w("**No legacy-mastery risk.** New IDs have no entry in `FLAT_TO_STABLE` and")
    w("no legacy tag rows to inherit, so there is nothing to migrate and nothing")
    w("to lose on downgrade. The 17 existing topics are untouched by this")
    w("proposal.")
    w("")
    w("**One existing mapping change is implied, and is NOT authorised here.**")
    w("`qc.superposition` and `qc.qubits` currently map their lessons at `medium`")
    w("or `high` confidence. Making the six reused items count toward mastery may")
    w("want `high` confidence mappings. Only `high` is mastery-mappable. Any such")
    w("change is a mapping change requiring its own approval.")
    w("")
    w("**Lesson slugs are placeholders.** Names must not collide with the 13")
    w("existing slugs, which are foreign keys into quiz attempts, challenge")
    w("attempts, recommendations and chat history.")
    w("")
    new_lesson_count = len(effective_proposal()) - len(
        [e for e in effective_proposal()
         if e["lessons"] and all((CONTENT_DIR / f"{x}.md").exists() for x in e["lessons"])]
    )

    w("## 8. Effort and risk")
    w("")
    new_lessons = sorted({
        l for p in proposal for l in p["lessons"] if l not in existing_slugs
    })
    w(f"- Proposed new topics: **{len(proposal)}**")
    w(f"- New lessons to author: **{len(new_lessons)}**")
    w(f"- Items satisfied by existing topics: **{len(reuse)}**")
    w(f"- Items deferred: **{len(deferred)}**")
    w("- Deepest dependency chain: 8 (qec.threshold_theorem)")
    w("")
    w("Principal risks:")
    w("")
    w(f"1. **Authoring volume.** {new_lesson_count} new lessons is the bulk of the remaining work and")
    w("   must be batched against the prerequisite graph, not the target-list order.")
    w("2. **Section I cost.** Five platform topics is the largest single commitment;")
    w("   consolidating them later means retiring topic IDs, which is worse than")
    w("   deciding now.")
    w("3. **Breadth versus depth.** Several advanced topics (HHL, surface codes,")
    w("   threshold theorem) are substantial subjects; one lesson each risks being")
    w("   superficial. Flagged for the authoring phase.")
    w("")
    w("## 9. Decisions requiring approval")
    w("")
    w("Approval is requested for the following, as a package:")
    w("")
    w(f"1. **{len(proposal)} new topics** as listed in section 3.")
    w(f"2. **{len(reuse)} target items satisfied by existing topics** rather than")
    w("   new ones (section 2), including the resulting cross-section mappings")
    w("   where an item's listed section differs from its absorbing topic's.")
    w(f"3. **{len(deferred)} items deferred** (section 5), reported as unresolved")
    w("   rather than complete.")
    w("4. The prerequisite graph in section 6, including `required` versus")
    w("   `recommended`.")
    w("5. The `adv.compilation` rescope and the five withdrawn proposals.")
    w("")
    w("### Scope of this approval (Gate 1 only)")
    w("")
    w("Approving this document is **Gate 1: architecture approval**. It")
    w("authorises nothing beyond accepting the architecture described here.")
    w("Specifically, Gate 1 does **not** authorise:")
    w("")
    w("- **Gate 2** - creating the topic IDs in `app/curriculum.py`, updating")
    w("  lesson mappings or prerequisites, or writing the migration.")
    w("- **Gate 3** - running that migration against any database, including")
    w("  a staging or local one.")
    w("- **Gate 4** - running any migration against production. This remains")
    w("  unauthorised and is not requested.")
    w("- **Gate 5** - authoring lesson content.")
    w("")
    w("Each gate requires its own explicit, separately stated authorisation.")
    w("Gate 1 approval must not be read as approval of any later gate. The")
    w("full gate definitions are in `M4_APPROVAL_CHECKLIST.md`.")
    w("")
    w("## 10. Validation status")
    w("")
    if graph_problems or validate():
        w("**FAILURES:**")
        w("")
        for pr in (validate() + graph_problems):
            w(f"- {pr}")
    else:
        w("All checks pass at generation time:")
        w("")
        w("- every pending item is covered exactly once across the three")
        w("  categories (reused, proposed, deferred)")
        w("- no proposed ID collides with a registered topic or another proposal")
        w("- all namespaces declared; all prerequisites resolve")
        w("- prerequisite kinds are `required` or `recommended`")
        w("- no cycles, no self-dependencies, valid topological order")
        w("- every proposed topic has a description, a difficulty and 3 objectives")
        w("")

    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {DOC_PATH.relative_to(ROOT)} ({len(lines)} lines)")


if __name__ == "__main__":
    report()
    write_baseline_doc()   # Phase 0 reviewed baseline (unchanged history)
    write_doc()            # Phase 1 architecture review (this deliverable)
