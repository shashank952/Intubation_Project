import pytest
import torch

import backend.deploy.model_loader as ml
from backend.deploy.config import settings
from backend.deploy.routers.predictions import _prepare_input
from backend.deploy.schemas import PredictionInput


@pytest.fixture(autouse=True)
def reset_model_state():
    yield
    ml._model = None
    ml._model_info = {}


def _make_input(**overrides) -> PredictionInput:
    base = dict(
        patient_id="P-TEST1", age=44, gender="male", bmi=24,
        mallampati_score=1, tmd=7, neck_circumference=41,
    )
    base.update(overrides)
    return PredictionInput(**base)


class TestFailFastLoading:
    def test_missing_checkpoint_raises_when_required(self, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "model_checkpoint", str(tmp_path / "nope.pt"))
        monkeypatch.setattr(settings, "model_required", True)
        with pytest.raises(RuntimeError, match="checkpoint not found"):
            ml.load_model()

    def test_missing_checkpoint_dev_mode_flags_random_weights(self, monkeypatch, tmp_path):
        monkeypatch.setattr(settings, "model_checkpoint", str(tmp_path / "nope.pt"))
        monkeypatch.setattr(settings, "model_required", False)
        ml.load_model()
        assert ml.model_status() == "not_loaded"
        info = ml.get_model_info()
        assert info["dev_random_weights"] is True


class TestRealCheckpoint:
    def test_strict_load_and_version(self):
        ml.load_model()
        assert ml.model_status() == "ok"
        info = ml.get_model_info()
        assert info["loaded"] is True
        assert info["version"].startswith("tabular_best.pt:")
        assert info["device"] == settings.model_device

    def test_golden_prediction(self):
        numerical, categorical = _prepare_input(_make_input())
        result = ml.predict_tabular(numerical, categorical)
        assert result["prediction"] in ("Easy", "Moderate", "Difficult")
        assert abs(sum(result["probabilities"].values()) - 1.0) < 0.01
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["model_version"] == ml.get_model_info()["version"]

    def test_prediction_deterministic_for_same_input(self):
        numerical, categorical = _prepare_input(_make_input())
        first = ml.predict_tabular(numerical, categorical)
        second = ml.predict_tabular(numerical, categorical)
        assert first == second
