"""Translate the API's PredictionInput into the real-data model's 11 features.

The form was built for the synthetic TabTransformer (30 fields). The real model
was trained on 11 features, so a mapping is unavoidable and must be explicit.

Two conversions are assumptions, not measurements:

1. Mouth opening. The form collects millimetres; the model was trained on
   "fingers". ``scripts/generate_dataset45.py`` uses 15 mm per finger
   (3 fingers = 45 mm), so that same constant is reused here and the result is
   snapped to the nearest 0.5 finger.

2. Teeth and chest size. The form never asked for teeth, and asks for chest size
   as Small/Medium/Large rather than centimetres. When those values are absent
   they stay None, and the pipeline's median imputer fills them. Every imputed
   feature is returned so the caller can see what happened instead of guessing.
"""

from __future__ import annotations

from typing import Optional

from .schemas import PredictionInput

MM_PER_FINGER = 15.0

YES_VALUES = {"yes", "y", "true", "1", "abnormal", "missing", "dentures", "edentulous"}


def _fingers_from_mm(millimetres: Optional[float]) -> Optional[float]:
    if millimetres is None:
        return None
    fingers = millimetres / MM_PER_FINGER
    snapped = round(fingers * 2) / 2
    return max(1.0, min(5.0, snapped))


def _teeth_flag(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    text = value.strip().lower()
    if text in YES_VALUES:
        return 1
    if text in {"intact", "normal", "no", "none"}:
        return 0
    return None


def to_model_features(data: PredictionInput) -> tuple[dict, list[str]]:
    """Return (features, imputed_feature_names)."""
    imputed: list[str] = []

    def put(name: str, value):
        if value is None:
            imputed.append(name)
        return value

    features = {
        "Age": put("Age", float(data.age)),
        "Gender_Male": put(
            "Gender_Male", 1 if data.gender.strip().lower() == "male" else 0
        ),
        "Neck_Circumference_cm": put(
            "Neck_Circumference_cm", float(data.neck_circumference)
        ),
        "Chest_Size_cm": put(
            "Chest_Size_cm",
            float(data.chest_size_cm) if data.chest_size_cm is not None else None,
        ),
        "Mouth_Opening_Fingers": put(
            "Mouth_Opening_Fingers", _fingers_from_mm(data.mouth_opening)
        ),
        "Mallampati_Score": put(
            "Mallampati_Score",
            float(data.mallampati_score) if data.mallampati_score else None,
        ),
        "Mallampati_Unknown": put(
            "Mallampati_Unknown", 0 if data.mallampati_score else 1
        ),
        "TMD_cm": put("TMD_cm", float(data.tmd)),
        "SMD_cm": put("SMD_cm", float(data.smd) if data.smd is not None else None),
        "Jaw_Movement_Inadequate": put(
            "Jaw_Movement_Inadequate",
            1 if (data.jaw_movement or "").strip().lower() == "reduced" else 0,
        ),
        "Teeth_Abnormal": put("Teeth_Abnormal", _teeth_flag(data.teeth)),
    }
    return features, imputed
