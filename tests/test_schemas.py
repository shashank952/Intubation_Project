import pytest
from pydantic import ValidationError

from backend.deploy.schemas import (
    PatientCreate,
    PredictionInput,
    PredictionOut,
    UserCreate,
)


class TestUserCreate:
    def test_valid_user(self):
        u = UserCreate(email="doc@example.com", password="secret123")
        assert u.role == "doctor"

    def test_password_needs_letter_and_digit(self):
        with pytest.raises(ValidationError):
            UserCreate(email="doc@example.com", password="abcdefgh")

    def test_password_needs_min_length(self):
        with pytest.raises(ValidationError):
            UserCreate(email="doc@example.com", password="ab1")

    def test_invalid_email_rejected(self):
        with pytest.raises(ValidationError):
            UserCreate(email="not-an-email", password="secret123")


class TestPatientCreate:
    def test_valid_patient(self):
        p = PatientCreate(
            patient_id="P-0001", age=44, gender="male", bmi=24,
            mallampati="2", tmd=7, neck_circumference=41,
        )
        assert p.patient_id == "P-0001"

    @pytest.mark.parametrize("bad_id", ["P 0001", "P/0001", "P\\0001", "P<0001>", ""])
    def test_patient_id_charset_rejected(self, bad_id):
        with pytest.raises(ValidationError):
            PatientCreate(
                patient_id=bad_id, age=44, gender="male", bmi=24,
                mallampati="2", tmd=7, neck_circumference=41,
            )

    def test_bmi_out_of_bounds_rejected(self):
        with pytest.raises(ValidationError):
            PatientCreate(
                patient_id="P-0001", age=44, gender="male", bmi=99,
                mallampati="2", tmd=7, neck_circumference=41,
            )

    def test_gender_validated(self):
        with pytest.raises(ValidationError):
            PatientCreate(
                patient_id="P-0001", age=44, gender="attackhelicopter", bmi=24,
                mallampati="2", tmd=7, neck_circumference=41,
            )

    def test_comorbidities_nosql_keys_rejected(self):
        with pytest.raises(ValidationError):
            PatientCreate(
                patient_id="P-0001", age=44, gender="male", bmi=24,
                mallampati="2", tmd=7, neck_circumference=41,
                comorbidities={"$where": "1"},
            )


class TestPredictionInput:
    def test_defaults_applied(self):
        d = PredictionInput(
            patient_id="P-0001", age=44, gender="male", bmi=24,
            mallampati_score=1, tmd=7, neck_circumference=41,
        )
        assert d.mouth_opening == 40.0
        assert d.previous_airway_records == "No"

    def test_mallampati_bounds(self):
        with pytest.raises(ValidationError):
            PredictionInput(
                patient_id="P-0001", age=44, gender="male", bmi=24,
                mallampati_score=9, tmd=7, neck_circumference=41,
            )

    def test_patient_id_charset_rejected(self):
        with pytest.raises(ValidationError):
            PredictionInput(
                patient_id="P 0001", age=44, gender="male", bmi=24,
                mallampati_score=1, tmd=7, neck_circumference=41,
            )


class TestPredictionOut:
    def test_model_version_optional(self):
        out = PredictionOut(
            patient_id="P-0001", prediction="Easy", confidence=0.9,
            probabilities={"Easy": 0.9}, risk_score=0.0,
            created_at="2026-01-01T00:00:00Z",
        )
        assert out.model_version is None
