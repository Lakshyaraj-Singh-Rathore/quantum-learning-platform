"""Interactive Model Tester for Quantum ML Lab.

Loads the saved Hybrid QNN artifact (or any trained model) and predicts
on arbitrary coordinates [x1, x2].
"""

from __future__ import annotations

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np

from app.quantum.qml_lab import algorithms
from app.quantum.qml_lab.persistence import load_model


def test_custom_coordinates(x1: float, x2: float, model_id: int = 101):
    artifact_root = pathlib.Path("artifacts/qml_live_models")
    loaded = load_model(artifact_root, model_id)
    config = loaded.config

    # Rebuild scaler using training seed
    rng = np.random.default_rng(config.seed)
    dataset = algorithms.build_dataset_for_config(config, rng)
    model = algorithms.build_model(config, dataset.n_features)

    raw_point = np.array([[x1, x2]])
    scaled_point = dataset.scaler.transform(raw_point)

    pred_class = int(model.predict(scaled_point, loaded.params)[0])
    prob = float(model.predict_proba(scaled_point, loaded.params)[0])

    print("\n" + "=" * 60)
    print(f"QUANTUM HYBRID QNN INFERENCE RESULT")
    print("=" * 60)
    print(f"  Input Coordinates:      x1 = {x1:+.4f}, x2 = {x2:+.4f}")
    print(f"  Scaled Coordinates:     x1' = {scaled_point[0,0]:+.4f}, x2' = {scaled_point[0,1]:+.4f}")
    print(f"  Predicted Class:        CLASS {pred_class}")
    print(f"  Probability P(y=1):     {prob:.4f} ({prob*100:.2f}%)")
    print(f"  Decision Confidence:    {max(prob, 1.0 - prob)*100:.2f}%")
    print("=" * 60 + "\n")
    return pred_class, prob


if __name__ == "__main__":
    if len(sys.argv) == 3:
        x1 = float(sys.argv[1])
        x2 = float(sys.argv[2])
    else:
        # Default test point
        x1, x2 = 0.5, -0.2
        print(f"No coordinates provided. Running default test point ({x1}, {x2}).")
        print("Usage: python scripts/test_model_interactive.py <x1> <x2>")

    test_custom_coordinates(x1, x2)
