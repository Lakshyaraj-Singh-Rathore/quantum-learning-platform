"""Negative-path limit sweeps verifying hard boundary enforcement across the platform.

Verifies:
1. QML limits: MAX_QUBITS=8, MAX_LAYERS=4, MAX_SAMPLES=1000 (and density matrix limits).
2. CUDA-Q Noise simulation limit: NOISE_MAX_QUBITS=11 boundary.
3. Qudit Lab dimension limits: d in {2, 3, 4, 5}, wire limits, and operand dimension safety.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.quantum.backends import cudaq_sim
from app.quantum.backends.base import BackendError
from app.quantum.backends.cudaq_sim import NOISE_MAX_QUBITS
from app.quantum.ir import CircuitIR, Op
from app.quantum.noise import NoiseParams
from app.quantum.qml_lab import limits
from app.quantum.qml_lab.models import CircuitConfig, DatasetConfig
from app.quantum.qudit_lab.models import (
    QuditCircuit,
    QuditOp,
    QuditWire,
)
from app.quantum.qudit_lab.validator import (
    DIMENSION_MAX_QUDITS,
    validate_qudit_circuit,
)


# ==============================================================================
# 1. QML Limits Sweep (MAX_QUBITS 8, MAX_LAYERS 4, MAX_SAMPLES 1000)
# ==============================================================================

class TestQmlNegativePathLimits:
    """Rigorous negative-path bounds checking for QML configurations."""

    @pytest.mark.parametrize("invalid_qubits", [9, 10, 16, 0, -1])
    def test_max_qubits_negative_sweep(self, invalid_qubits: int):
        assert limits.MAX_QUBITS == 8
        with pytest.raises(ValidationError) as exc:
            CircuitConfig(n_qubits=invalid_qubits)
        errors = exc.value.errors()
        assert any(e["loc"] == ("n_qubits",) for e in errors)

    @pytest.mark.parametrize("valid_qubits", [1, 2, 4, 6, 8])
    def test_max_qubits_positive_bounds(self, valid_qubits: int):
        cfg = CircuitConfig(n_qubits=valid_qubits)
        assert cfg.n_qubits == valid_qubits

    @pytest.mark.parametrize("invalid_layers", [5, 6, 10, 0, -1])
    def test_max_layers_negative_sweep(self, invalid_layers: int):
        assert limits.MAX_LAYERS == 4
        with pytest.raises(ValidationError) as exc:
            CircuitConfig(n_layers=invalid_layers)
        errors = exc.value.errors()
        assert any(e["loc"] == ("n_layers",) for e in errors)

    @pytest.mark.parametrize("valid_layers", [1, 2, 3, 4])
    def test_max_layers_positive_bounds(self, valid_layers: int):
        cfg = CircuitConfig(n_layers=valid_layers)
        assert cfg.n_layers == valid_layers

    @pytest.mark.parametrize("invalid_samples", [1001, 1002, 5000, 19, 0, -10])
    def test_max_samples_negative_sweep(self, invalid_samples: int):
        assert limits.MAX_SAMPLES == 1000
        with pytest.raises(ValidationError) as exc:
            DatasetConfig(n_samples=invalid_samples)
        errors = exc.value.errors()
        assert any(e["loc"] == ("n_samples",) for e in errors)

    @pytest.mark.parametrize("valid_samples", [20, 100, 200, 500, 1000])
    def test_max_samples_positive_bounds(self, valid_samples: int):
        cfg = DatasetConfig(n_samples=valid_samples)
        assert cfg.n_samples == valid_samples


# ==============================================================================
# 2. CUDA-Q Noise Simulation Limit (NOISE_MAX_QUBITS = 11)
# ==============================================================================

class TestCudaqNoiseNegativeLimits:
    """Verifies that density-matrix noise simulation enforces NOISE_MAX_QUBITS=11."""

    def test_noise_max_qubits_constant(self):
        assert NOISE_MAX_QUBITS == 11

    def test_noise_exceeding_11_qubits_is_rejected(self):
        # Build 12-qubit circuit
        ir_12 = CircuitIR(
            n_qubits=12,
            n_clbits=12,
            ops=[Op(kind="gate", gate="h", qubits=[i], layer=0) for i in range(12)],
        )
        noise = NoiseParams(enabled=True, t1_us=50.0, t2_us=30.0)

        with pytest.raises(BackendError) as exc:
            cudaq_sim.run(ir_12, noise=noise)
        assert "beyond 11 qubits that stops being a laptop-scale" in str(exc.value)

    def test_noise_at_11_qubits_passes_limit_guard(self):
        # 11-qubit circuit: exactly at NOISE_MAX_QUBITS boundary
        ir_11 = CircuitIR(
            n_qubits=11,
            n_clbits=11,
            ops=[Op(kind="gate", gate="h", qubits=[i], layer=0) for i in range(11)],
        )
        noise = NoiseParams(enabled=True, t1_us=50.0, t2_us=30.0)

        # Check that the 11-qubit limit guard does not raise BackendError with NOISE_MAX_QUBITS
        try:
            cudaq_sim.run(ir_11, shots=10, noise=noise)
        except BackendError as exc:
            assert "beyond 11 qubits" not in str(exc)
        except Exception:
            pass  # Simulation or hardware execution can take its course; boundary guard passed!


# ==============================================================================
# 3. Qudit Lab Dimension Sweeps (d in {2, 3, 4, 5})
# ==============================================================================

class TestQuditLabNegativeLimits:
    """Verifies dimension restrictions, state bounds, wire limits, and gate matching."""

    @pytest.mark.parametrize("invalid_d", [1, 6, 7, 10, 0, -1])
    def test_invalid_dimension_rejected(self, invalid_d: int):
        # QuditWire validates dimension ge=2, le=5
        with pytest.raises(ValidationError):
            QuditWire(id="w0", index=0, dimension=invalid_d, initial_state=0)

    @pytest.mark.parametrize("valid_d", [2, 3, 4, 5])
    def test_valid_dimensions_accepted(self, valid_d: int):
        circuit = QuditCircuit(
            dimension=valid_d,
            wires=[QuditWire(id="w0", index=0, dimension=valid_d, initial_state=0)],
            ops=[],
        )
        val = validate_qudit_circuit(circuit)
        assert val.valid, f"Dimension {valid_d} should be valid, got errors: {val.errors}"

    @pytest.mark.parametrize("dim,invalid_state", [
        (2, 2), (2, 3),
        (3, 3), (3, 5),
        (4, 4), (4, 9),
        (5, 5), (5, 6),
    ])
    def test_initial_state_out_of_bounds_rejected(self, dim: int, invalid_state: int):
        circuit = QuditCircuit(
            dimension=dim,
            wires=[QuditWire(id="w0", index=0, dimension=dim, initial_state=invalid_state)],
            ops=[],
        )
        val = validate_qudit_circuit(circuit)
        assert not val.valid
        assert any(f"exceeds dimension {dim}" in err for err in val.errors)

    def test_wire_count_exceeding_dimension_limit_rejected(self):
        # For d=5, DIMENSION_MAX_QUDITS[5] == 3. 4 qudits must be rejected.
        max_d5 = DIMENSION_MAX_QUDITS[5]
        wires = [
            QuditWire(id=f"w{i}", index=i, dimension=5, initial_state=0)
            for i in range(max_d5 + 1)
        ]
        circuit = QuditCircuit(dimension=5, wires=wires, ops=[])
        val = validate_qudit_circuit(circuit)
        assert not val.valid
        assert any("qudits at dimension d=5" in err for err in val.errors)

    def test_gate_dimension_mismatch_rejected(self):
        # Wire is d=2, gate is d=3
        circuit = QuditCircuit(
            dimension=2,
            wires=[QuditWire(id="w0", index=0, dimension=2, initial_state=0)],
            ops=[
                QuditOp(
                    id="op1",
                    gate="x",
                    targets=[0],
                    dimension=3,
                )
            ],
        )
        val = validate_qudit_circuit(circuit)
        assert not val.valid
        assert any("dimension 3 does not match target wire dimension 2" in err for err in val.errors)

    def test_two_qudit_heterogeneous_dimensions_rejected(self):
        # 2-qudit gate between wire of d=2 and wire of d=3
        circuit = QuditCircuit(
            dimension=2,
            wires=[
                QuditWire(id="w0", index=0, dimension=2, initial_state=0),
                QuditWire(id="w1", index=1, dimension=3, initial_state=0),
            ],
            ops=[
                QuditOp(
                    id="op1",
                    gate="csum",
                    targets=[1],
                    controls=[0],
                    dimension=2,
                )
            ],
        )
        val = validate_qudit_circuit(circuit)
        assert not val.valid
        assert any("requires matching dimensions" in err or "does not match" in err for err in val.errors)
