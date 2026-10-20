"""Qiskit Aer NoiseModel factory with multi-mechanism error composition."""

from __future__ import annotations

import math
from typing import Any
import numpy as np

from app.quantum.noise_lab.models import NoiseConfig
from app.quantum.noise_lab.validator import validate_noise_config

PULSE_1Q = ("h", "x", "y", "rx", "ry", "sx", "id", "u", "u2", "u3")
PULSE_2Q = ("cx", "cz", "swap")
PULSE_3Q = ("ccx",)


def _tensor_error(error: Any, copies: int) -> Any:
    out = error
    for _ in range(copies - 1):
        nxt = error.copy() if hasattr(error, "copy") else error
        out = out.tensor(nxt) if hasattr(out, "tensor") else out.expand(nxt)
    return out


def _rx_matrix(theta: float) -> np.ndarray:
    half = theta / 2.0
    return np.array([
        [math.cos(half), -1j * math.sin(half)],
        [-1j * math.sin(half), math.cos(half)]
    ], dtype=complex)


def _rz_matrix(phi: float) -> np.ndarray:
    half = phi / 2.0
    return np.array([
        [np.exp(-1j * half), 0.0],
        [0.0, np.exp(1j * half)]
    ], dtype=complex)


def build_noise_model(config: NoiseConfig, n_qubits: int = 2) -> tuple[Any, list[str]]:
    """Build a Qiskit Aer NoiseModel from a comprehensive NoiseConfig."""
    try:
        from qiskit_aer.noise import (
            NoiseModel,
            ReadoutError,
            coherent_unitary_error,
            depolarizing_error,
            pauli_error,
            thermal_relaxation_error,
        )
    except ImportError as exc:
        raise RuntimeError("qiskit-aer is required for noise simulation") from exc

    report = validate_noise_config(config, circuit_qubits=n_qubits)
    if not report.valid:
        raise ValueError(f"Invalid noise configuration: {'; '.join(report.errors)}")

    model = NoiseModel()
    notes: list[str] = list(report.warnings)
    applied_mechanisms: list[str] = []

    # 1. Thermal Relaxation & Decoherence (T1, T2)
    d = config.decoherence
    if d.enabled and (d.t1_us > 0 or d.t2_us > 0):
        t1 = max(d.t1_us, 1e-6)
        t2 = max(d.t2_us, 1e-6)
        p1 = d.excited_state_pop

        if d.gate_time_1q_us > 0:
            err_1q = thermal_relaxation_error(t1, t2, d.gate_time_1q_us, p1)
            model.add_all_qubit_quantum_error(err_1q, list(PULSE_1Q))
            applied_mechanisms.append("T1/T2 thermal relaxation (1Q gates)")

        if d.gate_time_2q_us > 0:
            base_2q = thermal_relaxation_error(t1, t2, d.gate_time_2q_us, p1)
            model.add_all_qubit_quantum_error(_tensor_error(base_2q, 2), list(PULSE_2Q))
            applied_mechanisms.append("T1/T2 thermal relaxation (2Q gates)")

        if d.gate_time_3q_us > 0:
            base_3q = thermal_relaxation_error(t1, t2, d.gate_time_3q_us, p1)
            model.add_all_qubit_quantum_error(_tensor_error(base_3q, 3), list(PULSE_3Q))

    # 2. Stochastic Channels: Depolarizing
    s = config.stochastic
    if s.enabled:
        if s.depolarizing_1q > 0:
            err_depol_1q = depolarizing_error(s.depolarizing_1q, 1)
            model.add_all_qubit_quantum_error(err_depol_1q, list(PULSE_1Q))
            applied_mechanisms.append(f"1Q depolarizing (p={s.depolarizing_1q})")

        if s.depolarizing_2q > 0:
            err_depol_2q = depolarizing_error(s.depolarizing_2q, 2)
            model.add_all_qubit_quantum_error(err_depol_2q, list(PULSE_2Q))
            applied_mechanisms.append(f"2Q depolarizing (p={s.depolarizing_2q})")

        # Pauli Channels (Bit-flip, Phase-flip, Bit-phase-flip)
        px, py, pz = s.bit_flip, s.bit_phase_flip, s.phase_flip
        p_sum = px + py + pz
        if p_sum > 0:
            p_ident = max(0.0, 1.0 - p_sum)
            pauli_list = []
            if px > 0:
                pauli_list.append(("X", px))
            if py > 0:
                pauli_list.append(("Y", py))
            if pz > 0:
                pauli_list.append(("Z", pz))
            if p_ident > 0:
                pauli_list.append(("I", p_ident))
            
            p_err = pauli_error(pauli_list)
            model.add_all_qubit_quantum_error(p_err, list(PULSE_1Q))
            applied_mechanisms.append(f"Pauli noise (X:{px}, Y:{py}, Z:{pz})")

    # 3. Coherent Errors: Over/Under-rotations
    c = config.coherent
    if c.enabled:
        if abs(c.over_rotation_1q_rad) > 1e-9 or abs(c.phase_offset_rad) > 1e-9:
            u_rx = _rx_matrix(c.over_rotation_1q_rad)
            u_rz = _rz_matrix(c.phase_offset_rad)
            u_1q = u_rz @ u_rx
            err_coherent_1q = coherent_unitary_error(u_1q)
            model.add_all_qubit_quantum_error(err_coherent_1q, list(PULSE_1Q))
            applied_mechanisms.append(
                f"Coherent 1Q rotation offset (Δθ={c.over_rotation_1q_rad:.3f} rad, Δφ={c.phase_offset_rad:.3f} rad)"
            )

        if abs(c.over_rotation_2q_rad) > 1e-9:
            u_2q_single = _rx_matrix(c.over_rotation_2q_rad)
            u_2q = np.kron(u_2q_single, u_2q_single)
            err_coherent_2q = coherent_unitary_error(u_2q)
            model.add_all_qubit_quantum_error(err_coherent_2q, list(PULSE_2Q))
            applied_mechanisms.append(f"Coherent 2Q rotation offset (Δθ={c.over_rotation_2q_rad:.3f} rad)")

    # 4. Readout / SPAM Error
    r = config.readout
    if r.enabled and (r.prob_1_given_0 > 0 or r.prob_0_given_1 > 0):
        p10 = r.prob_1_given_0
        p01 = r.prob_0_given_1
        readout_matrix = [
            [1.0 - p10, p10],
            [p01, 1.0 - p01]
        ]
        ro_err = ReadoutError(readout_matrix)
        model.add_all_qubit_readout_error(ro_err)
        applied_mechanisms.append(f"Readout error (P(1|0)={p10}, P(0|1)={p01})")

    # 5. Correlated Crosstalk / ZZ Coupling
    corr = config.correlated
    if corr.enabled:
        if corr.zz_crosstalk_strength > 0:
            # ZZ crosstalk Hamiltonian exp(-i * zeta * Z⊗Z / 2)
            zeta = corr.zz_crosstalk_strength
            half_z = zeta / 2.0
            u_zz = np.diag([
                np.exp(-1j * half_z),
                np.exp(1j * half_z),
                np.exp(1j * half_z),
                np.exp(-1j * half_z)
            ])
            err_zz = coherent_unitary_error(u_zz)
            model.add_all_qubit_quantum_error(err_zz, list(PULSE_2Q))
            applied_mechanisms.append(f"Residual coherent ZZ coupling on 2Q gates (strength={zeta:.3f})")

        if corr.correlated_depolarizing_2q > 0:
            err_corr_depol = depolarizing_error(corr.correlated_depolarizing_2q, 2)
            model.add_all_qubit_quantum_error(err_corr_depol, list(PULSE_2Q))
            applied_mechanisms.append(f"Correlated 2Q depolarizing ({corr.correlated_depolarizing_2q})")

    notes.append(f"Active noise channels applied: {', '.join(applied_mechanisms) if applied_mechanisms else 'None (ideal)'}")
    return model, notes
