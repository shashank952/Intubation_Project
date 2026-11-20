import torch
import torch.nn as nn
from pathlib import Path
from typing import Optional
from .config import settings


_model: Optional[nn.Module] = None
_device: str = settings.model_device


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


def load_model():
    global _model
    _model = _build_model()
    ckpt = Path(settings.model_checkpoint)
    if ckpt.exists():
        state = torch.load(ckpt, map_location=_device, weights_only=True)
        _model.load_state_dict(state, strict=False)
    _model.to(_device)
    _model.eval()


def get_model() -> nn.Module:
    if _model is None:
        load_model()
    return _model


def predict_tabular(numerical: torch.Tensor, categorical: list) -> dict:
    model = get_model()
    temperature = 1.0  # label smoothing keeps logits calibrated; no extra scaling needed
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
        "probabilities": {
            name: round(float(probs[0, i].item()), 3) for i, name in enumerate(class_names)
        },
    }
