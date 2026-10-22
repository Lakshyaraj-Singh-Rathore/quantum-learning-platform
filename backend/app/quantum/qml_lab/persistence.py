"""Model artifacts on disk: JSON for structure, ``.npz`` for weights.

Three hard rules, each with a test:

* **Never pickle.** Weights load with ``allow_pickle=False``, so a tampered
  artifact cannot execute code on load. ``numpy.save``'s pickle path is the
  obvious shortcut for object arrays and it is not taken here.
* **Never join a user-supplied string into a path.** The experiment id must
  parse as a non-negative integer or a UUID; anything else is rejected before
  it touches the filesystem. The resolved directory is then re-checked to be
  inside the root, so neither ``../`` nor an absolute path nor a symlink can
  escape.
* **Writes are atomic.** Files are written to a temporary name in the same
  directory and renamed into place, so an interrupted save cannot leave a
  half-written artifact that later loads as corrupt data.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.quantum.qml_lab.errors import QmlPersistenceError
from app.quantum.qml_lab.models import QmlExperimentConfig
from app.quantum.qml_lab.vqc import Parameters

#: Bump when the on-disk layout changes incompatibly. Stored in every
#: artifact so a future loader can refuse or migrate rather than
#: misinterpreting an old file.
ARTIFACT_VERSION = 1

_CONFIG_FILE = "config.json"
_WEIGHTS_FILE = "weights.npz"
_METRICS_FILE = "metrics.json"


@dataclass(frozen=True)
class LoadedModel:
    """What :func:`load_model` hands back."""

    version: int
    config: QmlExperimentConfig
    params: Parameters
    metrics: dict[str, Any]


def canonical_experiment_id(experiment_id: Any) -> str:
    """Validate an experiment id and return its canonical directory name.

    Accepts a non-negative ``int`` or a ``uuid.UUID`` (or a string that parses
    cleanly as either). Everything else raises. This is the only place an id
    becomes a path component.
    """
    if isinstance(experiment_id, bool):  # bool is an int subclass; reject it explicitly
        raise QmlPersistenceError(f"invalid experiment id: {experiment_id!r}")

    if isinstance(experiment_id, int):
        if experiment_id < 0:
            raise QmlPersistenceError(f"experiment id must be non-negative, got {experiment_id}")
        return str(experiment_id)

    if isinstance(experiment_id, uuid.UUID):
        return str(experiment_id)

    if isinstance(experiment_id, str):
        text = experiment_id.strip()
        if text.isdigit():
            return str(int(text))
        try:
            return str(uuid.UUID(text))
        except (ValueError, AttributeError, TypeError) as exc:
            raise QmlPersistenceError(
                f"experiment id must be a non-negative integer or a UUID, got {experiment_id!r}"
            ) from exc

    raise QmlPersistenceError(f"experiment id must be an int or UUID, got {type(experiment_id).__name__}")


def experiment_dir(root: Path | str, experiment_id: Any) -> Path:
    """Resolve the directory for one experiment, guaranteed inside ``root``."""
    root_path = Path(root).resolve()
    candidate = (root_path / canonical_experiment_id(experiment_id)).resolve()

    # Defence in depth: the id is already constrained to digits or a UUID, but
    # re-checking containment means a future change to the id rules cannot
    # silently become a traversal.
    if candidate != root_path and root_path not in candidate.parents:
        raise QmlPersistenceError(f"resolved path {candidate} escapes the artifact root {root_path}")
    return candidate


def save_model(
    root: Path | str,
    experiment_id: Any,
    config: QmlExperimentConfig,
    params: Parameters,
    metrics: dict[str, Any] | None = None,
) -> Path:
    """Write config, weights and metrics; return the directory written to."""
    target = experiment_dir(root, experiment_id)
    target.mkdir(parents=True, exist_ok=True)

    try:
        _atomic_json(
            target / _CONFIG_FILE,
            {
                "version": ARTIFACT_VERSION,
                "experiment_id": canonical_experiment_id(experiment_id),
                "config": config.model_dump(mode="json"),
                "parameter_shape": {"n_qubits": params.n_qubits, "n_layers": params.n_layers},
            },
        )
        _atomic_npz(target / _WEIGHTS_FILE, theta=np.asarray(params.theta, dtype=float))
        _atomic_json(target / _METRICS_FILE, {"version": ARTIFACT_VERSION, "metrics": metrics or {}})
    except OSError as exc:
        raise QmlPersistenceError(f"could not write artifacts to {target}: {exc}") from exc

    return target


def load_model(root: Path | str, experiment_id: Any) -> LoadedModel:
    """Read an artifact back. Raises if anything is missing or inconsistent."""
    target = experiment_dir(root, experiment_id)
    config_path = target / _CONFIG_FILE
    weights_path = target / _WEIGHTS_FILE

    if not config_path.is_file() or not weights_path.is_file():
        raise QmlPersistenceError(f"no complete artifact at {target}")

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QmlPersistenceError(f"unreadable config at {config_path}: {exc}") from exc

    version = int(payload.get("version", -1))
    if version != ARTIFACT_VERSION:
        raise QmlPersistenceError(f"artifact version {version} is not supported (expected {ARTIFACT_VERSION})")

    config = QmlExperimentConfig.model_validate(payload["config"])
    shape = payload["parameter_shape"]

    # allow_pickle=False is the point of using npz at all.
    try:
        with np.load(weights_path, allow_pickle=False) as archive:
            theta = np.asarray(archive["theta"], dtype=float)
    except (OSError, ValueError, KeyError) as exc:
        raise QmlPersistenceError(f"unreadable weights at {weights_path}: {exc}") from exc

    expected = shape["n_layers"] * shape["n_qubits"] * 2 + 1
    if theta.size != expected:
        raise QmlPersistenceError(f"weight vector has {theta.size} entries, expected {expected}")

    metrics: dict[str, Any] = {}
    metrics_path = target / _METRICS_FILE
    if metrics_path.is_file():
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8")).get("metrics", {})
        except (OSError, json.JSONDecodeError):
            metrics = {}

    return LoadedModel(
        version=version,
        config=config,
        params=Parameters(theta=theta, n_qubits=int(shape["n_qubits"]), n_layers=int(shape["n_layers"])),
        metrics=metrics,
    )


def delete_experiment(root: Path | str, experiment_id: Any) -> bool:
    """Remove an experiment's directory. Returns whether anything was removed.

    Used to clean up after a cancelled run so a partial artifact is never left
    behind for a later load to trip over.
    """
    target = experiment_dir(root, experiment_id)
    if not target.exists():
        return False
    shutil.rmtree(target)
    return True


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _atomic_npz(path: Path, **arrays: np.ndarray) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.savez(handle, **arrays)
    os.replace(temporary, path)
