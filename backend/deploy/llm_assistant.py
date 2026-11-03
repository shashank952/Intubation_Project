import asyncio
import logging
import re
import time
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

from .config import settings

logger = logging.getLogger("airway.llm")

_client: Optional[OpenAI] = None

SYSTEM_PROMPT = (
    "Anesthesiologist decision-support for a difficult-airway prediction "
    "(Easy/Moderate/Difficult: standard intubation / alternatives + backup / "
    "advanced techniques + senior staff). Use ONLY provided patient data, "
    "never invent values. If confidence < 60%, note uncertainty. Frame as "
    "risk and preparation, never guaranteed outcomes. Concise, decisive, "
    "clinical tone; short bullet points only."
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.llm_api_key or "no-key",
            base_url=settings.llm_api_url,
            timeout=settings.llm_timeout,
            max_retries=0,
        )
    return _client


def report_deadline() -> float:
    return time.monotonic() + settings.llm_report_budget_seconds


_BULLET_PREFIX = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])\s+")


def _normalize_bullets(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = _BULLET_PREFIX.sub("", raw.strip()).replace("**", "").strip()
        if line:
            lines.append(f"- {line}")
    return "\n".join(lines)


def _model_chain() -> List[str]:
    chain = [settings.llm_model]
    for extra in settings.llm_fallback_models.split(","):
        name = extra.strip()
        if name and name not in chain:
            chain.append(name)
    return chain


def _extra_body() -> dict:
    # Reasoning models spend the whole token budget thinking and return empty
    # content, so ask OpenRouter to skip it. Other providers reject the field.
    if "openrouter" in settings.llm_api_url.lower():
        return {"reasoning": {"enabled": False}}
    return {}


def _is_feasible(text: str) -> bool:
    stripped = text.strip()
    return len(stripped) >= 15


def _call_llm(
    prompt: str, system: str = "", deadline: Optional[float] = None
) -> Optional[str]:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    chain = _model_chain()
    last_err: Optional[Exception] = None
    attempts_made = 0
    for attempt in range(settings.llm_retries + 1):
        attempts_made = attempt + 1
        remaining = None if deadline is None else deadline - time.monotonic()
        if remaining is not None and remaining <= 0.01:
            logger.warning(
                "LLM budget exhausted before attempt %d/%d",
                attempt + 1,
                settings.llm_retries + 1,
            )
            break
        attempt_timeout = (
            settings.llm_timeout
            if remaining is None
            else min(settings.llm_timeout, remaining)
        )
        model = chain[attempt % len(chain)]
        start = time.time()
        try:
            client = _get_client()
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
                timeout=attempt_timeout,
                extra_body=_extra_body(),
            )
            choices = getattr(resp, "choices", None)
            choice = choices[0] if choices else None
            raw = choice.message.content if choice else None
            text = _normalize_bullets(raw) if raw else ""
            if _is_feasible(text):
                logger.info(
                    "LLM ok in %.2fs (attempt %d/%d, model=%s)",
                    time.time() - start,
                    attempt + 1,
                    settings.llm_retries + 1,
                    model,
                )
                return text
            last_err = RuntimeError(
                f"empty or non-feasible LLM response "
                f"(finish_reason={getattr(choice, 'finish_reason', None)})"
                if choices
                else "LLM response contained no choices"
            )
            logger.warning("LLM attempt %d (%s): %s", attempt + 1, model, last_err)
        except Exception as e:
            last_err = e
            logger.warning(
                "LLM attempt %d/%d (%s) failed after %.1fs: %s",
                attempt + 1,
                settings.llm_retries + 1,
                model,
                time.time() - start,
                e,
            )
        if attempt < settings.llm_retries:
            backoff = 1.0 * (attempt + 1)
            if deadline is not None and time.monotonic() + backoff >= deadline:
                break
            time.sleep(backoff)

    logger.error("LLM failed after %d attempt(s): %s", attempts_made, last_err)
    return None


def check_llm_connection() -> Tuple[bool, Optional[float]]:
    try:
        client = _get_client()
        start = time.time()
        client.models.list(timeout=settings.llm_timeout)
        latency_ms = round((time.time() - start) * 1000, 1)
        logger.info("LLM connection check OK (%.1f ms)", latency_ms)
        return True, latency_ms
    except Exception as e:
        logger.warning("LLM connection check failed: %s", e)
        return False, None


PATIENT_PROFILE_LABELS = {
    "age": "Age",
    "gender": "Gender",
    "bmi": "BMI",
    "bmi_category": "BMI Category",
    "mallampati_score": "Mallampati Score",
    "mallampati": "Mallampati Score",
    "tmd": "Thyromental Distance (cm)",
    "tmd_category": "TMD Category",
    "neck_circumference": "Neck Circumference (cm)",
    "neck_circ": "Neck Circumference (cm)",
    "mouth_opening": "Mouth Opening (mm)",
    "smd": "Sternomental Distance (cm)",
    "neck_movement": "Neck Movement (degrees)",
    "neck_movement_category": "Neck Movement Category",
    "beard": "Beard",
    "chest_size": "Chest Size",
    "neck_structure": "Neck Structure",
    "jaw_movement": "Jaw Movement",
    "tissue_flexibility": "Tissue Flexibility",
    "previous_airway_records": "Previous Airway Records",
    "disease_arthritis": "Disease: Arthritis",
    "disease_diabetes": "Disease: Diabetes",
    "disease_down_syndrome": "Disease: Down Syndrome",
    "breathing_snoring": "Snoring",
    "breathing_sleep_apnea": "Sleep Apnea",
    "symptom_voice_changes": "Symptom: Voice Changes",
    "symptom_difficulty_swallowing": "Symptom: Difficulty Swallowing",
    "symptom_cant_lie_flat": "Symptom: Can't Lie Flat",
    "injury_swelling": "Injury: Swelling",
    "injury_previous_neck_fracture": "Injury: Previous Neck Fracture",
    "previous_emergencies_icu": "Previous Emergencies/ICU",
}

YES_NO_FIELDS = {
    "beard", "previous_airway_records", "disease_arthritis", "disease_diabetes",
    "disease_down_syndrome", "breathing_snoring", "breathing_sleep_apnea",
    "symptom_voice_changes", "symptom_difficulty_swallowing", "symptom_cant_lie_flat",
    "injury_swelling", "injury_previous_neck_fracture", "previous_emergencies_icu",
}


def build_patient_profile(data: dict) -> str:
    parts = []
    for key, label in PATIENT_PROFILE_LABELS.items():
        val = data.get(key)
        if val is None or str(val).strip() == "":
            continue
        if key in YES_NO_FIELDS:
            is_yes = str(val).lower() in ("1", "yes", "y", "true")
            parts.append(f"{label}: {'Yes' if is_yes else 'No'}")
        else:
            parts.append(f"{label}: {val}")
    return "\n".join(parts) or "No additional patient data provided."


def _build_report_prompt(
    kind: str,
    prediction: str,
    confidence: float,
    probabilities: Dict[str, float],
    profile: str,
) -> str:
    probs_str = ", ".join(f"{k}: {v:.1%}" for k, v in probabilities.items())
    if kind == "summary":
        content_rule = (
            "Explicitly name the key risk factors you identified from the "
            "profile, including any positive categorical findings (e.g., "
            "snoring, sleep apnea, diabetes, difficulty swallowing, reduced "
            "jaw or neck mobility, can't lie flat). Then state the predicted "
            "class, confidence, and airway implication."
        )
    else:
        content_rule = (
            "Tailor airway plan, equipment, staffing, monitoring and "
            "documentation to the predicted class."
        )
    bullet_rule = (
        "Return ONLY 5 concise bullet points."
        if kind == "summary"
        else "Return between 5 and 10 concise bullet points."
    )
    return f"""Patient Profile:
{profile}

Model probabilities: {probs_str}

Identify the key risk factors from the patient profile above, then write a {kind} for an anesthesiologist. Base every claim ONLY on facts present in the profile - never invent values.

{bullet_rule}
Rules:
- Each line must start with "- ".
- No introduction, no headings, no paragraph.
- Keep every bullet under 18 words.
- Be direct, clinical, and actionable.
- {content_rule}

The model's predicted class is {prediction} ({confidence:.1%} confidence). Use it as a guide, but ground every claim in the profile above."""


FALLBACK_SUMMARY = (
    "- Prediction: {prediction} ({confidence:.1%} confidence).\n"
    "- Key risk factors: Mallampati {mallampati}, TMD {tmd} cm, BMI {bmi}.\n"
    "- Clinical correlation recommended to confirm findings.\n"
    "- Consider patient history and additional imaging if available.\n"
    "- Document airway assessment findings in patient record."
)

FALLBACK_RECOMMENDATIONS = (
    "- Prepare appropriate airway equipment based on risk category.\n"
    "- {difficult_line}\n"
    "- Monitor patient closely during induction of anesthesia.\n"
    "- Ensure emergency airway equipment is readily available.\n"
    "- Document airway management plan in patient record.\n"
    "- Consider early involvement of senior anesthesiologist if concerns persist."
)


def _fallback_summary(prediction: str, confidence: float, patient_data: dict) -> str:
    return FALLBACK_SUMMARY.format(
        prediction=prediction,
        confidence=confidence,
        mallampati=patient_data.get("mallampati_score", patient_data.get("mallampati", "N/A")),
        tmd=patient_data.get("tmd", "N/A"),
        bmi=patient_data.get("bmi", "N/A"),
    )


def _fallback_recommendations(prediction: str) -> str:
    difficult_line = (
        "Consider video laryngoscope or awake fiberoptic intubation."
        if prediction == "Difficult"
        else "Standard intubation protocol is likely sufficient."
    )
    return FALLBACK_RECOMMENDATIONS.format(difficult_line=difficult_line)


def generate_clinical_summary(
    prediction: str,
    confidence: float,
    probabilities: Dict[str, float],
    patient_data: dict,
    deadline: Optional[float] = None,
) -> Tuple[str, str]:
    profile = build_patient_profile(patient_data)
    prompt = _build_report_prompt(
        "summary", prediction, confidence, probabilities, profile
    )
    text = _call_llm(prompt, SYSTEM_PROMPT, deadline)
    if text is None:
        logger.warning("Summary generation failed -> using fallback")
        return _fallback_summary(prediction, confidence, patient_data), "fallback"
    return text, "llm"


def generate_recommendations(
    prediction: str,
    confidence: float,
    probabilities: Dict[str, float],
    patient_data: dict,
    deadline: Optional[float] = None,
) -> Tuple[str, str]:
    profile = build_patient_profile(patient_data)
    prompt = _build_report_prompt(
        "recommendations", prediction, confidence, probabilities, profile
    )
    text = _call_llm(prompt, SYSTEM_PROMPT, deadline)
    if text is None:
        logger.warning("Recommendations generation failed -> using fallback")
        return _fallback_recommendations(prediction), "fallback"
    return text, "llm"


def fallback_reports(
    prediction: str, confidence: float, patient_data: dict
) -> Tuple[str, str, str, str]:
    return (
        _fallback_summary(prediction, confidence, patient_data),
        "fallback",
        _fallback_recommendations(prediction),
        "fallback",
    )


async def generate_reports(
    prediction: str,
    confidence: float,
    probabilities: Dict[str, float],
    patient_data: dict,
) -> Tuple[str, str, str, str]:
    deadline = report_deadline()
    summary_task = asyncio.create_task(
        asyncio.to_thread(
            generate_clinical_summary,
            prediction, confidence, probabilities, patient_data, deadline,
        )
    )
    recommendations_task = asyncio.create_task(
        asyncio.to_thread(
            generate_recommendations,
            prediction, confidence, probabilities, patient_data, deadline,
        )
    )
    done, pending = await asyncio.wait(
        {summary_task, recommendations_task},
        timeout=settings.llm_report_budget_seconds,
    )
    for task in pending:
        task.cancel()
    if pending:
        logger.warning(
            "LLM report budget of %.1fs exceeded for %d/2 report(s) -> fallback",
            settings.llm_report_budget_seconds,
            len(pending),
        )

    fallback_summary_text, fallback_source, fallback_recs_text, fallback_recs_source = (
        fallback_reports(prediction, confidence, patient_data)
    )

    def settled(task, default):
        if task in done and not task.cancelled() and task.exception() is None:
            return task.result()
        return default

    summary, summary_source = settled(
        summary_task, (fallback_summary_text, fallback_source)
    )
    recommendations, recommendations_source = settled(
        recommendations_task, (fallback_recs_text, fallback_recs_source)
    )
    return summary, summary_source, recommendations, recommendations_source