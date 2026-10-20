import hashlib
import logging
import time

import torch
import torch.nn as nn
from pathlib import Path
from typing import Optional

from .config import settings

logger = logging.getLogger("airway.model")

_model: Optional[nn.Module] = None
_device: str = settings.model_device
_model_info: dict = {}


def _build_model() -> nn.Module:
    from backend.models.tabular_model import TabularModel
    num_numerical = 7
    cat_cardinalities = [2, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 2, 2, 3, 4, 3, 3, 3, 2]
    model = TabularModel(
        num_numerical=num_numerical,
        cat_cardinalities=cat_cardinalities,
        num_classes=3,
        embed_dim=64,
        tab_output_dim=128,
        dropout=0.3,
    )
    return model


def _checkpoint_version(ckpt: Path) -> str:
    """Short content hash so every prediction can be traced to the exact weights."""
    sha = hashlib.sha256(ckpt.read_bytes()).hexdigest()[:8]
    return f"{ckpt.name}:{sha}"


def load_model() -> None:
    """Load the tabular model from settings.model_checkpoint.

    Fails fast (RuntimeError) when the checkpoint is missing or does not match
    the model architecture — silently serving random weights is unacceptable
    for a clinical API. Set MODEL_REQUIRED=false only for local development.
    """
    global _model, _model_info
    ckpt = Path(settings.model_checkpoint)
    _model = _build_model()

    if not ckpt.exists():
        if settings.model_required:
            raise RuntimeError(
                f"Model checkpoint not found: {ckpt.resolve()}. "
                "Fix MODEL_CHECKPOINT. Set MODEL_REQUIRED=false only for "
                "local development (random weights, never in production)."
            )
        logger.critical(
            "Model checkpoint missing (%s) — serving RANDOM weights (dev mode, "
            "MODEL_REQUIRED=false). Never enable this in production.",
            ckpt,
        )
        _model.to(_device)
        _model.eval()
        _model_info = {
            "loaded": False,
            "checkpoint": None,
            "version": None,
            "device": _device,
            "dev_random_weights": True,
        }
        return

    load_start = time.perf_counter()
    state = torch.load(ckpt, map_location=_device, weights_only=True)
    # strict=True: a shape/key mismatch means wrong architecture or corrupted
    # file — refuse to serve instead of half-loading weights.
    _model.load_state_dict(state, strict=True)
    _model.to(_device)
    _model.eval()
    _model_info = {
        "loaded": True,
        "checkpoint": str(ckpt),
        "version": _checkpoint_version(ckpt),
        "device": _device,
        "load_seconds": round(time.perf_counter() - load_start, 2),
    }
    logger.info(
        "Model loaded: %s on %s in %.2fs",
        _model_info["version"], _device, _model_info["load_seconds"],
    )


def get_model() -> nn.Module:
    if _model is None:
        load_model()
    return _model


def get_model_info() -> dict:
    """Snapshot of model load state — surfaced by /ready and stored per prediction."""
    return dict(_model_info)


def model_status() -> str:
    return "ok" if _model_info.get("loaded") else "not_loaded"


def predict_tabular(numerical: torch.Tensor, categorical: list) -> dict:
    model = get_model()
    # Temperature softens extreme logits from synthetic-data training.
    # NOTE: calibration debt — replace with a calibrated temperature
    # (Platt/temperature scaling on held-out REAL data) before clinical use.
    temperature = settings.model_softmax_temperature
    with torch.no_grad():
        logits = model(numerical.to(_device), [c.to(_device) for c in categorical])
        probs = torch.softmax(logits / temperature, dim=-1)
        pred_class = probs.argmax(dim=-1).item()
        confidence = probs[0, pred_class].item()
    class_names = ["Easy", "Moderate", "Difficult"]
    risk_scores = {"Easy": 0.0, "Moderate": 0.5, "Difficult": 1.0}
    return {
        "prediction": class_names[pred_class],
        "confidence": round(confidence, 3),
        "risk_score": risk_scores[class_names[pred_class]],
        "model_version": _model_info.get("version"),
        "probabilities": {
            name: round(float(probs[0, i].item()), 3) for i, name in enumerate(class_names)
        },
    }
