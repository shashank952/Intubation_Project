"""Tests for the PredictionInput -> real-model feature mapping."""

from __future__ import annotations

import pytest

from backend.deploy.real_model_input import MM_PER_FINGER, to_model_features
from backend.deploy.schemas import PredictionInput

BASE = {
    "patient_id": "P-0001",
    "age": 44,
    "gender": "Male",
    "bmi": 24,
    "mallampati_score": 1,
    "tmd": 7,
    "neck_circumference": 41,
}


def make(**overrides) -> PredictionInput:
    return PredictionInput(**{**BASE, **overrides})


def test_gender_maps_to_binary():
    male, _ = to_model_features(make(gender="Male"))
    female, _ = to_model_features(make(gender="Female"))
    assert male["Gender_Male"] == 1
    assert female["Gender_Male"] == 0


def test_mouth_opening_millimetres_to_fingers():
    features, _ = to_model_features(make(mouth_opening=MM_PER_FINGER * 3))
    assert features["Mouth_Opening_Fingers"] == 3.0


def test_mouth_opening_snaps_to_half_finger():
    features, _ = to_model_features(make(mouth_opening=40.0))
    assert features["Mouth_Opening_Fingers"] == 2.5


def test_jaw_movement_reduced_becomes_one():
    reduced, _ = to_model_features(make(jaw_movement="Reduced"))
    normal, _ = to_model_features(make(jaw_movement="Normal"))
    assert reduced["Jaw_Movement_Inadequate"] == 1
    assert normal["Jaw_Movement_Inadequate"] == 0


@pytest.mark.parametrize(
    "raw,expected",
    [("Intact", 0), ("Normal", 0), ("Abnormal", 1), ("Missing", 1), (None, None), ("", None)],
)
def test_teeth_mapping(raw, expected):
    features, imputed = to_model_features(make(teeth=raw))
    assert features["Teeth_Abnormal"] == expected
    assert ("Teeth_Abnormal" in imputed) is (expected is None)


def test_missing_chest_size_is_reported_as_imputed():
    features, imputed = to_model_features(make())
    assert features["Chest_Size_cm"] is None
    assert "Chest_Size_cm" in imputed


def test_complete_record_imputes_nothing():
    features, imputed = to_model_features(
        make(
            chest_size_cm=96,
            teeth="Intact",
            mouth_opening=45,
            smd=22,
            jaw_movement="Adequate",
            mallampati_score=2,
        )
    )
    assert imputed == []
    assert features["Chest_Size_cm"] == 96.0
    assert features["Mallampati_Unknown"] == 0
    assert features["Teeth_Abnormal"] == 0


def test_mallampati_is_required_and_bounded():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        make(mallampati_score=0)
    features, _ = to_model_features(make(mallampati_score=3))
    assert features["Mallampati_Unknown"] == 0


def test_feature_names_match_the_frozen_model():
    import json
    from pathlib import Path

    meta_path = Path(__file__).resolve().parents[1] / "checkpoints" / "tabular_real_v1.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    features, _ = to_model_features(make())
    assert list(features.keys()) == meta["features"]
