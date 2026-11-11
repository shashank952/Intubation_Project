"""Loader for the real-patient tabular model (checkpoints/tabular_real_v1.joblib).

This is separate from ``model_loader.py``, which loads the synthetic-trained
TabTransformer used by the current ``/api/predictions`` path. Keeping them
apart means the existing API keeps working while the real-data model is wired
in deliberately.

Target definition
-----------------
The model predicts the doctor's recorded decision (Easy / Moderate / Difficult),
not a post-hoc intubation outcome. Do not present its output as clinical
accuracy.

Missing inputs
--------------
The uploaded form may leave a field empty (Mallampati was 'NA' for 2 of 80
patients). Missing values are passed to the pipeline's median imputer, which
was fitted on the real training data. Nothing is invented here.

Usage
-----
    from backend.deploy.real_model import predict
    result = predict({"Age": 44, "Neck_Circumference_cm": 41, ...})
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger("airway.real_model")

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "checkpoints" / "tabular_real_v1.joblib"
CLASS_NAMES = ["Easy", "Moderate", "Difficult"]

_artifact: Optional[dict] = None
_meta: Optional[dict] = None
_version: Optional[str] = None


def _model_path() -> Path:
    override = os.getenv("REAL_MODEL_PATH")
    return Path(override) if override else DEFAULT_PATH


def load() -> dict:
    """Load the artifact once. Raises if it is missing - no silent fallback."""
    global _artifact, _meta, _version
    if _artifact is not None:
        return _artifact

    import joblib

    path = _model_path()
    if not path.exists():
        raise RuntimeError(
            f"Real-data model not found: {path}. "
            "Run `py -3.12 scripts/train_final_tabular.py` first."
        )

    _artifact = joblib.load(path)
    for key in ("pipeline", "features", "classes"):
        if key not in _artifact:
            raise RuntimeError(f"Model artifact is missing '{key}': {path}")

    meta_path = path.with_suffix(".json")
    _meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    _version = f"{path.name}:{hashlib.sha256(path.read_bytes()).hexdigest()[:8]}"
    logger.info("Real model loaded: %s (%d features)", _version, len(_artifact["features"]))
    return _artifact


def model_info() -> dict:
    artifact = load()
    return {
        "loaded": True,
        "version": _version,
        "path": str(_model_path()),
        "features": list(artifact["features"]),
        "classes": list(artifact["classes"]),
        "n_patients": _meta.get("n_patients"),
        "target_definition": _meta.get("target_definition"),
        "metrics": _meta.get("cv"),
    }


def predict(features: dict) -> dict:
    """Predict from a feature dict. Unknown keys are ignored, missing ones imputed."""
    artifact = load()
    pipeline = artifact["pipeline"]
    names = list(artifact["features"])

    values = []
    missing = []
    for name in names:
        raw = features.get(name)
        if raw is None or raw == "":
            values.append(np.nan)
            missing.append(name)
        else:
            values.append(float(raw))

    vector = np.array([values], dtype=float)
    probabilities = pipeline.predict_proba(vector)[0]
    index = int(np.argmax(probabilities))

    return {
        "prediction": CLASS_NAMES[index],
        "confidence": round(float(probabilities[index]), 3),
        "probabilities": {
            name: round(float(p), 3) for name, p in zip(CLASS_NAMES, probabilities)
        },
        "missing_features": missing,
        "unknown_features": sorted(set(features) - set(names)),
        "model_version": _version,
    }
