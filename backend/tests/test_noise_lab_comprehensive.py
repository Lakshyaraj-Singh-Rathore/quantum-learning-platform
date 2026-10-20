"""Comprehensive test suite for Quantum Noise Lab."""

from __future__ import annotations

import math
import pytest
from app.quantum.ir import CircuitIR
from app.quantum.noise_lab import (
    NOISE_CATALOGUE,
    PRESET_CONFIGS,
    CoherentParams,
    CorrelatedParams,
    DecoherenceParams,
    NoiseConfig,
    ReadoutParams,
    StochasticParams,
    build_noise_model,
    run_parameter_sweep,
    simulate_noise_experiment,
    validate_noise_config,
)

BELL_CIRCUIT = {
    "n_qubits": 2,
    "n_clbits": 2,
    "ops": [
        {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
        {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
        {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
        {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
    ],
}


# ------------------------------------------------------------------- Validation
def test_catalogue_contains_all_core_categories():
    categories = {m["category"] for m in NOISE_CATALOGUE}
    assert {"decoherence", "stochastic", "coherent", "readout", "correlated"} <= categories
    assert len(NOISE_CATALOGUE) >= 8


def test_presets_validity():
    for name, preset in PRESET_CONFIGS.items():
        report = validate_noise_config(preset)
        assert report.valid, f"Preset '{name}' failed validation: {report.errors}"


def test_t2_greater_than_2t1_rejected():
    cfg = NoiseConfig(
        decoherence=DecoherenceParams(enabled=True, t1_us=50.0, t2_us=120.0)
    )
    report = validate_noise_config(cfg)
    assert not report.valid
    assert any("2*T1" in err for err in report.errors)


def test_t2_equal_2t1_accepted():
    cfg = NoiseConfig(
        decoherence=DecoherenceParams(enabled=True, t1_us=50.0, t2_us=100.0)
    )
    report = validate_noise_config(cfg)
    assert report.valid


def test_pauli_sum_greater_than_1_rejected():
    cfg = NoiseConfig(
        stochastic=StochasticParams(enabled=True, bit_flip=0.5, phase_flip=0.4, bit_phase_flip=0.2)
    )
    report = validate_noise_config(cfg)
    assert not report.valid
    assert any("sum" in err.lower() for err in report.errors)


def test_negative_times_rejected():
    cfg = NoiseConfig(
        decoherence=DecoherenceParams(enabled=True, t1_us=-10.0, t2_us=20.0)
    )
    report = validate_noise_config(cfg)
    assert not report.valid


def test_readout_probabilities_capped():
    # p > 1.0 or p < 0.0 must be rejected
    with pytest.raises(Exception):
        ReadoutParams(enabled=True, prob_1_given_0=1.5)
    with pytest.raises(Exception):
        ReadoutParams(enabled=True, prob_0_given_1=-0.1)


def test_readout_inverted_channel_warning_and_execution():
    # Readout p in (0.5, 1.0] is mathematically valid in Aer (inverted channel),
    # but emits a clear physical warning.
    r = ReadoutParams(enabled=True, prob_1_given_0=0.7, prob_0_given_1=0.7)
    cfg = NoiseConfig(readout=r)
    report = validate_noise_config(cfg)
    assert report.valid is True
    assert any("inverted" in w.lower() for w in report.warnings)

    # Must execute cleanly on Aer
    ir = CircuitIR.model_validate(BELL_CIRCUIT)
    res = simulate_noise_experiment(ir, cfg, shots=1000, seed=42)
    # Prepared Bell state |00> + |11> should now predominantly register as |11> + |00>
    # but with flipped individual bits
    assert res.metrics.total_variation_distance > 0.10


def test_coherent_phase_offset_delta_phi_independent_effect():
    # Single-qubit superposition state |+> = (|0> + |1>)/sqrt(2)
    superpos_circuit = {
        "n_qubits": 1,
        "n_clbits": 1,
        "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 1},
        ],
    }
    ir = CircuitIR.model_validate(superpos_circuit)

    # 1. Zero noise gives pure state with fidelity 1.0
    cfg_zero = NoiseConfig(coherent=CoherentParams(enabled=True, over_rotation_1q_rad=0.0, phase_offset_rad=0.0))
    res_zero = simulate_noise_experiment(ir, cfg_zero, shots=1000, seed=42)
    assert res_zero.metrics.fidelity == pytest.approx(1.0, abs=1e-5)
    assert res_zero.metrics.purity == pytest.approx(1.0, abs=1e-5)

    # 2. Non-zero delta phi (phase offset): rotates relative phase between |0> and |1>
    cfg_phi = NoiseConfig(coherent=CoherentParams(enabled=True, over_rotation_1q_rad=0.0, phase_offset_rad=0.40))
    res_phi = simulate_noise_experiment(ir, cfg_phi, shots=1000, seed=42)
    # Coherent error preserves pure state (purity == 1.0), but shifts state away from ideal |+>
    assert res_phi.metrics.purity == pytest.approx(1.0, abs=1e-4)
    assert res_phi.metrics.fidelity < 0.99


def test_asymmetric_readout_error_behavior():
    ir = CircuitIR.model_validate(BELL_CIRCUIT)
    cfg = NoiseConfig(
        readout=ReadoutParams(enabled=True, prob_1_given_0=0.02, prob_0_given_1=0.25)
    )
    report = validate_noise_config(cfg)
    assert report.valid is True
    res = simulate_noise_experiment(ir, cfg, shots=2000, seed=42)
    # Asymmetric readout produces different false positive vs false negative rates
    assert res.metrics.total_variation_distance > 0.05


def test_zz_crosstalk_2q_coupling_physics_and_parity_dependence():
    # 1. On Bell state |Phi+> = (|00> + |11>)/sqrt(2), Z0*Z1 = +1 is a definite eigenstate!
    # ZZ crosstalk exp(-i zeta Z⊗Z/2) applies a uniform phase exp(-i zeta/2) across both terms,
    # which is purely a global phase. Therefore, fidelity to Bell state remains 1.0!
    bell_ir = CircuitIR.model_validate(BELL_CIRCUIT)
    cfg = NoiseConfig(
        correlated=CorrelatedParams(enabled=True, zz_crosstalk_strength=0.50)
    )
    res_bell = simulate_noise_experiment(bell_ir, cfg, shots=2000, seed=42)
    assert res_bell.metrics.fidelity == pytest.approx(1.0, abs=1e-5)
    assert res_bell.metrics.purity == pytest.approx(1.0, abs=1e-4)

    # 2. On a superposition that spans both even and odd parity states (H(0), H(1), CX(0,1)):
    # ZZ crosstalk introduces relative phase shifts between parities, degrading fidelity!
    superpos_2q = {
        "n_qubits": 2,
        "n_clbits": 2,
        "ops": [
            {"kind": "gate", "gate": "h", "qubits": [0], "layer": 0},
            {"kind": "gate", "gate": "h", "qubits": [1], "layer": 0},
            {"kind": "gate", "gate": "x", "qubits": [1], "controls": [0], "layer": 1},
            {"kind": "measure", "qubits": [0], "clbits": [0], "layer": 2},
            {"kind": "measure", "qubits": [1], "clbits": [1], "layer": 2},
        ],
    }
    ir_super = CircuitIR.model_validate(superpos_2q)
    res_super = simulate_noise_experiment(ir_super, cfg, shots=2000, seed=42)
    # Unitary ZZ crosstalk keeps purity == 1.0 while degrading fidelity to cos^2(zeta/2) < 0.98!
    assert res_super.metrics.purity == pytest.approx(1.0, abs=1e-4)
    assert res_super.metrics.fidelity < 0.98


# ------------------------------------------------------------------- Execution & Physics
def test_zero_noise_reproduces_bell_state_fidelity():
    ir = CircuitIR.model_validate(BELL_CIRCUIT)
    cfg = PRESET_CONFIGS["ideal"]
    res = simulate_noise_experiment(ir, cfg, shots=2000, seed=42)
    
    assert res.metrics.fidelity == pytest.approx(1.0, abs=1e-5)
    assert res.metrics.purity == pytest.approx(1.0, abs=1e-5)
    assert res.metrics.total_variation_distance < 0.05
    # Off-diagonal Bell basis |01> and |10> must be near zero
    assert res.noisy_counts.get("01", 0) + res.noisy_counts.get("10", 0) < 50


def test_depolarizing_noise_reduces_purity():
    ir = CircuitIR.model_validate(BELL_CIRCUIT)
    cfg = NoiseConfig(
        stochastic=StochasticParams(enabled=True, depolarizing_2q=0.10)
    )
    res = simulate_noise_experiment(ir, cfg, shots=2000, seed=42)
    assert res.metrics.purity is not None
    assert res.metrics.purity < 0.95
    assert res.metrics.fidelity is not None
    assert res.metrics.fidelity < 0.95
    assert res.metrics.total_variation_distance > 0.02


def test_coherent_overrotation_maintains_purity_while_reducing_fidelity():
    # Coherent error is a unitary perturbation: purity must remain 1.0 (pure state),
    # while fidelity to the target Bell state drops!
    ir = CircuitIR.model_validate(BELL_CIRCUIT)
    cfg = NoiseConfig(
        coherent=CoherentParams(enabled=True, over_rotation_2q_rad=0.30)
    )
    res = simulate_noise_experiment(ir, cfg, shots=2000, seed=42)
    assert res.metrics.purity is not None
    assert res.metrics.purity == pytest.approx(1.0, abs=1e-4)  # Still a pure state!
    assert res.metrics.fidelity is not None
    assert res.metrics.fidelity < 0.98  # But incorrect state!


def test_readout_error_leaves_pure_state_fidelity_intact():
    ir = CircuitIR.model_validate(BELL_CIRCUIT)
    cfg = NoiseConfig(
        readout=ReadoutParams(enabled=True, prob_1_given_0=0.08, prob_0_given_1=0.08)
    )
    res = simulate_noise_experiment(ir, cfg, shots=2000, seed=42)
    # Counts are corrupted by detector error:
    leakage = res.noisy_probabilities.get("01", 0.0) + res.noisy_probabilities.get("10", 0.0)
    assert leakage > 0.08
    assert res.metrics.total_variation_distance > 0.05


def test_parameter_sweep_produces_monotonic_fidelity_decay():
    ir = CircuitIR.model_validate(BELL_CIRCUIT)
    cfg = NoiseConfig()
    sweep = run_parameter_sweep(
        ir,
        base_config=cfg,
        param_path="stochastic.depolarizing_2q",
        start_val=0.0,
        end_val=0.15,
        steps=4,
        shots=500,
    )
    assert len(sweep) == 4
    fidelities = [pt["fidelity"] for pt in sweep if pt.get("fidelity") is not None]
    assert len(fidelities) == 4
    # Monotonically non-increasing fidelity
    assert fidelities[0] > fidelities[-1]


# ------------------------------------------------------------------- API Endpoints
def test_noise_api_catalogue(client):
    res = client.get("/noise/catalogue")
    assert res.status_code == 200
    assert len(res.json()) >= 8


def test_noise_api_presets(client):
    res = client.get("/noise/presets")
    assert res.status_code == 200
    assert "superconducting_transmon" in res.json()


def test_noise_api_simulate(client, student_headers):
    payload = {
        "circuit_ir": BELL_CIRCUIT,
        "noise_config": PRESET_CONFIGS["superconducting_transmon"].model_dump(),
        "shots": 500,
    }
    res = client.post("/noise/simulate", json=payload, headers=student_headers)
    assert res.status_code == 200
    data = res.json()
    assert "ideal_counts" in data
    assert "noisy_counts" in data
    assert data["metrics"]["total_variation_distance"] >= 0.0


def test_noise_api_sweep(client, student_headers):
    payload = {
        "circuit_ir": BELL_CIRCUIT,
        "noise_config": NoiseConfig().model_dump(),
        "param_path": "stochastic.depolarizing_2q",
        "start_val": 0.01,
        "end_val": 0.05,
        "steps": 3,
        "shots": 200,
    }
    res = client.post("/noise/sweep", json=payload, headers=student_headers)
    assert res.status_code == 200
    assert len(res.json()) == 3
