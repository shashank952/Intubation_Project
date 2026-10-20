from backend.deploy.llm_assistant import (
    _fallback_recommendations,
    _fallback_summary,
    _is_feasible,
    build_patient_profile,
)


class TestBuildPatientProfile:
    def test_labels_and_yes_no_normalization(self):
        profile = build_patient_profile({
            "age": 44,
            "gender": "male",
            "mallampati_score": 3,
            "breathing_snoring": "1",
            "disease_diabetes": "yes",
            "previous_airway_records": "no",
        })
        assert "Age: 44" in profile
        assert "Mallampati Score: 3" in profile
        assert "Snoring: Yes" in profile
        assert "Disease: Diabetes: Yes" in profile
        assert "Previous Airway Records: No" in profile

    def test_skips_missing_values(self):
        profile = build_patient_profile({"age": None, "bmi": ""})
        assert "Age" not in profile
        assert "BMI" not in profile

    def test_empty_profile_fallback_text(self):
        assert build_patient_profile({}) == "No additional patient data provided."


class TestFallbacks:
    def test_summary_mentions_prediction_and_key_fields(self):
        text = _fallback_summary("Difficult", 0.82, {"mallampati_score": 4, "tmd": 5.5, "bmi": 33})
        assert "Difficult" in text
        assert "82.0%" in text
        assert "4" in text and "5.5" in text and "33" in text

    def test_recommendations_difficult_line(self):
        text = _fallback_recommendations("Difficult")
        assert "video laryngoscope" in text

    def test_recommendations_easy_line(self):
        text = _fallback_recommendations("Easy")
        assert "video laryngoscope" not in text


class TestFeasibility:
    def test_short_text_infeasible(self):
        assert not _is_feasible("too short")

    def test_long_text_feasible(self):
        assert _is_feasible("This is a sufficiently long clinical response.")
