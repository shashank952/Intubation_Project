import asyncio
import time

from backend.deploy import llm_assistant
from backend.deploy.llm_assistant import (
    _call_llm,
    _fallback_recommendations,
    _fallback_summary,
    _is_feasible,
    build_patient_profile,
    fallback_reports,
    report_deadline,
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


class TestBudget:
    def test_report_deadline_is_in_the_future(self):
        assert report_deadline() > time.monotonic()

    def test_call_llm_skips_http_when_budget_already_spent(self, monkeypatch):
        monkeypatch.setattr(llm_assistant.settings, "llm_external_enabled", True)
        assert _call_llm("prompt", deadline=time.monotonic() - 1) is None

    def test_generate_summary_falls_back_when_budget_already_spent(self, monkeypatch):
        monkeypatch.setattr(llm_assistant.settings, "llm_external_enabled", True)
        text, source = llm_assistant.generate_clinical_summary(
            "Moderate", 0.7, {"Easy": 0.2, "Moderate": 0.7, "Difficult": 0.1},
            {"age": 50}, deadline=time.monotonic() - 1,
        )
        assert source == "fallback"
        assert "Moderate" in text

    def test_fallback_reports_returns_both_sources_as_fallback(self):
        summary, summary_source, recommendations, recommendations_source = (
            fallback_reports("Difficult", 0.9, {"mallampati_score": 4})
        )
        assert "Difficult" in summary
        assert "video laryngoscope" in recommendations
        assert summary_source == "fallback"
        assert recommendations_source == "fallback"


def _fast_summary(*_args, **_kwargs):
    return "- Fast summary line for the patient.", "llm"


def _slow_recommendations(*_args, **_kwargs):
    import time as _time

    _time.sleep(1.0)
    return "- Slow recommendations line.", "llm"


class TestGenerateReports:
    def test_parallel_calls_keep_successful_report_when_other_hits_budget(
        self, monkeypatch
    ):
        monkeypatch.setattr(llm_assistant.settings, "llm_report_budget_seconds", 0.2)
        monkeypatch.setattr(llm_assistant, "generate_clinical_summary", _fast_summary)
        monkeypatch.setattr(
            llm_assistant, "generate_recommendations", _slow_recommendations
        )

        summary, summary_source, recommendations, recommendations_source = (
            asyncio.run(
                llm_assistant.generate_reports(
                    "Moderate", 0.7, {"Moderate": 0.7}, {"age": 50}
                )
            )
        )

        assert summary_source == "llm"
        assert summary == "- Fast summary line for the patient."
        assert recommendations_source == "fallback"
        assert "airway equipment" in recommendations
