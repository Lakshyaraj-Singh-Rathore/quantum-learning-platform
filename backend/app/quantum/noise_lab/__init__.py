"""Quantum Noise Simulation Laboratory package."""

from app.quantum.noise_lab.catalogue import NOISE_CATALOGUE, PRESET_CONFIGS
from app.quantum.noise_lab.factory import build_noise_model
from app.quantum.noise_lab.metrics import calculate_metrics, total_variation_distance
from app.quantum.noise_lab.models import (
    CoherentParams,
    CorrelatedParams,
    DecoherenceParams,
    NoiseCategory,
    NoiseConfig,
    NoiseMetrics,
    NoiseSimulationResult,
    ReadoutParams,
    SimulationMethod,
    StochasticParams,
    ValidationReport,
)
from app.quantum.noise_lab.service import run_parameter_sweep, simulate_noise_experiment
from app.quantum.noise_lab.validator import validate_noise_config

__all__ = [
    "CoherentParams",
    "CorrelatedParams",
    "DecoherenceParams",
    "NoiseCategory",
    "NoiseConfig",
    "NoiseMetrics",
    "NoiseSimulationResult",
    "ReadoutParams",
    "SimulationMethod",
    "StochasticParams",
    "ValidationReport",
    "NOISE_CATALOGUE",
    "PRESET_CONFIGS",
    "build_noise_model",
    "calculate_metrics",
    "total_variation_distance",
    "validate_noise_config",
    "simulate_noise_experiment",
    "run_parameter_sweep",
]
