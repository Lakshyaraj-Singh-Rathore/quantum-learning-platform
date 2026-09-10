"""Qiskit Aer static simulation backend."""

from __future__ import annotations

from typing import Optional

import numpy as np

from qiskit import transpile
from qiskit.quantum_info import Statevector

from app.quantum.backends.base import BackendError, Timer, make_result, statevector_to_json
from app.quantum.ir import CircuitIR
from app.quantum.noise import (
    NoiseParams,
    build_noise_model,
    entanglement_entropy,
    total_variation,
)
from app.quantum.normalize import strip_measurements, to_qiskit

NAME = "qiskit_aer"


def run(
    ir: CircuitIR,
    shots: int = 1024,
    *,
    seed: Optional[int] = None,
    noise: Optional[NoiseParams] = None,
) -> dict:
    try:
        from qiskit_aer import AerSimulator
    except ImportError as exc:  # pragma: no cover
        raise BackendError("qiskit-aer is not installed") from exc

    circ = to_qiskit(ir, include_measurements=True)
    warnings: list[str] = []

    if not ir.has_measurements():
        circ.measure_all(add_bits=False) if circ.num_clbits >= circ.num_qubits else None
        for q in range(min(circ.num_qubits, circ.num_clbits)):
            circ.measure(q, q)
        warnings.append("No measurements in circuit; measured all qubits automatically.")

    noise_model = None
    noise_meta: dict = {"enabled": False}
    if noise is not None and noise.enabled:
        noise_model, noise_notes = build_noise_model(noise)
        warnings.extend(noise_notes)
        clean, _ = noise.clamped()
        noise_meta = {
            "enabled": True,
            "t1_us": clean.t1_us,
            "t2_us": clean.t2_us,
            "readout_error": clean.readout_error,
        }
        warnings.append(
            "Noise model is a teaching approximation with parameters you chose, "
            "not calibration from any real device."
        )

    sim = AerSimulator(noise_model=noise_model) if noise_model else AerSimulator()
    with Timer() as timer:
        compiled = transpile(circ, sim)
        job = sim.run(compiled, shots=shots, seed_simulator=seed)
        counts = job.result().get_counts()

    # Aer returns only as many bits as there are classical registers, so a
    # partially-measured 2-qubit circuit yields keys like "0"/"1". Those are
    # ambiguous in the UI (they read as a 1-qubit result) and Plotly parses
    # them as numbers. Left-pad to the register width.
    counts = {
        k.replace(" ", "").zfill(circ.num_clbits): int(v) for k, v in counts.items()
    }

    statevector = None
    try:
        pure = strip_measurements(to_qiskit(ir, include_measurements=False))
        statevector = statevector_to_json(Statevector.from_instruction(pure).data)
    except Exception:  # noqa: BLE001 - reset/mid-measure make this undefined
        warnings.append("Statevector unavailable (circuit is not purely unitary).")

    if noise_meta["enabled"] and statevector is not None:
        warnings.append(
            "Statevector shown is the IDEAL state; only the counts carry noise."
        )

    metrics: dict = {}
    ideal_counts: dict[str, int] | None = None

    if statevector is not None:
        import numpy as np

        amplitudes = np.array([complex(re, im) for re, im in statevector])
        entropy, concurrence = entanglement_entropy(amplitudes, ir.n_qubits)
        metrics["entanglement_entropy"] = entropy
        metrics["concurrence"] = concurrence
        metrics["entangled"] = entropy > 0.05

    if noise_meta["enabled"]:
        # Run the SAME circuit without noise so the UI can put ideal and noisy
        # side by side, and compute how far the noise pushed the distribution.
        ideal_job = AerSimulator().run(
            transpile(circ, AerSimulator()), shots=shots, seed_simulator=seed
        )
        ideal_counts = {
            k.replace(" ", "").zfill(circ.num_clbits): int(v)
            for k, v in ideal_job.result().get_counts().items()
        }
        total_ideal = sum(ideal_counts.values()) or 1
        total_noisy = sum(counts.values()) or 1
        ideal_probs = {k: v / total_ideal for k, v in ideal_counts.items()}
        noisy_probs = {k: v / total_noisy for k, v in counts.items()}
        metrics["total_variation"] = total_variation(ideal_probs, noisy_probs)
        support = {k for k, v in ideal_probs.items() if v >= 0.02}
        metrics["shot_leakage"] = sum(
            v for k, v in noisy_probs.items() if k not in support
        )

        try:
            fidelity, purity = _density_metrics(ir, noise)
            metrics["fidelity"] = fidelity
            metrics["purity"] = purity
        except Exception as exc:  # noqa: BLE001 - non-unitary circuits
            warnings.append(f"Fidelity/purity unavailable: {exc}")
    else:
        metrics["fidelity"] = 1.0
        metrics["purity"] = 1.0
        metrics["total_variation"] = 0.0
        metrics["shot_leakage"] = 0.0

    return make_result(
        backend=NAME,
        counts=counts,
        shots=shots,
        n_qubits=ir.n_qubits,
        runtime=timer.seconds,
        statevector=statevector,
        warnings=warnings,
        metadata={
            "mode": "static",
            "noise": noise_meta,
            "metrics": metrics,
            "ideal_counts": ideal_counts,
        },
    )


def _density_metrics(ir: CircuitIR, noise: NoiseParams) -> tuple[float, float]:
    """State fidelity against the ideal state, and purity of the noisy state.

    Uses the density-matrix simulator with readout error excluded: readout is a
    measurement fault, not a channel acting on the state, so including it would
    wrongly depress the reported state fidelity.
    """
    from qiskit.quantum_info import DensityMatrix, Statevector, state_fidelity
    from qiskit_aer import AerSimulator

    pure = strip_measurements(to_qiskit(ir, include_measurements=False))
    model, _ = build_noise_model(noise, include_readout=False)

    saved = pure.copy()
    saved.save_density_matrix(label="rho")
    sim = AerSimulator(method="density_matrix", noise_model=model)
    data = sim.run(transpile(saved, sim), shots=1).result().data(0)
    rho = DensityMatrix(data["rho"])

    fidelity = float(np.real(state_fidelity(Statevector.from_instruction(pure), rho)))
    purity = float(np.real(rho.purity()))
    return min(1.0, max(0.0, fidelity)), min(1.0, max(0.0, purity))


__all__ = ["run", "NAME"]
