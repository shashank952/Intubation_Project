import torch

from backend.data.preprocessing import CATEGORICAL_COLS
from backend.deploy.routers.predictions import _prepare_input
from backend.deploy.schemas import PredictionInput


def _make_input(**overrides) -> PredictionInput:
    base = dict(
        patient_id="P-TEST1", age=44, gender="male", bmi=24,
        mallampati_score=1, tmd=7, neck_circumference=41,
    )
    base.update(overrides)
    return PredictionInput(**base)


def _category_value(categorical, col_name):
    idx = CATEGORICAL_COLS.index(col_name)
    return int(categorical[idx].item())


class TestNumericalPreparation:
    def test_numerical_is_scaled_not_raw(self):
        numerical, _ = _prepare_input(_make_input(age=44, bmi=24))
        values = numerical[0].tolist()
        assert 44.0 not in values
        assert 24.0 not in values

    def test_numerical_shape(self):
        numerical, _ = _prepare_input(_make_input())
        assert numerical.shape == (1, 7)


class TestCategoricalPreparation:
    def test_all_22_categoricals_present(self):
        _, categorical = _prepare_input(_make_input())
        assert len(categorical) == len(CATEGORICAL_COLS) == 22
        assert all(t.shape == (1,) for t in categorical)

    def test_mallampati_mapped_ordinal(self):
        _, categorical = _prepare_input(_make_input(mallampati_score=4))
        assert _category_value(categorical, "Mallampati_Score") == 3

    def test_gender_binary(self):
        _, categorical = _prepare_input(_make_input(gender="male"))
        assert _category_value(categorical, "Gender") == 1

    def test_yes_no_field_mapping(self):
        _, categorical = _prepare_input(
            _make_input(breathing_snoring="Yes", previous_airway_records="no")
        )
        assert _category_value(categorical, "Breathing_Snoring") == 1
        assert _category_value(categorical, "Previous_Airway_Records") == 0

    def test_bmi_category_thresholds(self):
        assert _category_value(_prepare_input(_make_input(bmi=24))[1], "BMI_Category") == 0
        assert _category_value(_prepare_input(_make_input(bmi=27))[1], "BMI_Category") == 1
        assert _category_value(_prepare_input(_make_input(bmi=31))[1], "BMI_Category") == 2

    def test_tmd_category_thresholds(self):
        assert _category_value(_prepare_input(_make_input(tmd=5.5))[1], "TMD_Category") == 2
        assert _category_value(_prepare_input(_make_input(tmd=6.2))[1], "TMD_Category") == 1
        assert _category_value(_prepare_input(_make_input(tmd=7.0))[1], "TMD_Category") == 0

    def test_neck_movement_category_thresholds(self):
        assert _category_value(_prepare_input(_make_input(neck_movement=60))[1], "Neck_Movement_Category") == 2
        assert _category_value(_prepare_input(_make_input(neck_movement=75))[1], "Neck_Movement_Category") == 1
        assert _category_value(_prepare_input(_make_input(neck_movement=85))[1], "Neck_Movement_Category") == 0
