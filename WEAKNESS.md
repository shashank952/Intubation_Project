# LLM Response Weaknesses — Checklist

Status legend: ✅ Implemented · 🔶 Partial · ⬜ Pending

| # | Weakness | Status | Counter-measure | Where |
|---|----------|--------|-----------------|-------|
| 1 | Silent failure masking (LLM failures invisible, fallback used silently) | ✅ | LLM connectivity check on login, response feasibility validation, structured logging, `source` flag (`llm`/`fallback`) saved per report, UI badge for AI status, UI notice when fallback is shown | `llm_assistant.py`, `routers/llm.py`, `routers/predictions.py`, dashboard, `AiClinicalAssessment` |
| 2 | No retries / no timeout (slow LLM hangs the request) | ✅ | Backend: 12s per-attempt timeout, SDK retries disabled, 1 retry with backoff, summary + recommendations in parallel under a 28s `LLM_REPORT_BUDGET_SECONDS` cap (overrun -> fallback report). Frontend: slow warning at 5s, 45s abort → "Time limit exceeded" error message shown in UI | `llm_assistant.py`, `config.py`, `api.ts`, dashboard |
| 3 | Incomplete context (LLM only saw 6 fields) | ✅ | Full patient profile — ALL categorical + numerical fields from the doctor's input are sent in the prompt | `llm_assistant.py` (`build_patient_profile`) |
| 4 | Synchronous generation adds latency | ✅ (Option B: bounded sync + UX states) | LLM call runs off the event loop (thread) so other requests stay responsive; UI shows loading → "taking longer than usual" → timeout error. Full async (Option A) noted as future work | `routers/predictions.py`, dashboard |
| 5 | Duplicate prompt templates (drift risk) | ✅ | Single shared prompt builder for both summary and recommendations | `llm_assistant.py` (`_build_report_prompt`) |

---

## 1. Silent failure masking
- [x] LLM connectivity is checked when the doctor logs in (`GET /api/llm/status`), shown as an AI badge in the header (Connected / Offline / Checking).
- [x] LLM responses are validated for feasibility (non-empty, minimum length) before being accepted.
- [x] Every LLM attempt/failure is logged with duration and error.
- [x] Each saved report stores `summary_source` and `recommendations_source` = `llm` | `fallback`.
- [x] UI shows a notice when a fallback (standard guidance) was used instead of a live AI answer.

## 2. No retries / no timeout
- [x] Backend: per-call timeout (`LLM_TIMEOUT` = 12s), 1 retry with backoff (`LLM_RETRIES` = 1).
- [x] Backend: OpenAI SDK retries disabled (`max_retries=0`); summary + recommendations run in parallel, bounded by `LLM_REPORT_BUDGET_SECONDS` = 28s, then fallback text.
- [x] Frontend: hard timeout at 45s, kept above the server budget so the server's fallback report wins the race.
- [x] Frontend: slow-warning message after 5s of waiting: "The LLM response is taking longer than usual. Please wait…"

## 3. Incomplete context
- [x] `build_patient_profile` now includes every categorical and numerical field the doctor provides (demographics, airway, physical, disease, symptoms, injury flags, derived categories).
- [x] Yes/No fields are presented as words ("Yes"/"No") so the LLM reads them naturally.

## 4. Synchronous latency
- [x] LLM calls run in a worker thread (`asyncio.to_thread`) so the event loop / other requests are not blocked.
- [x] Response is bounded by timeout + retry budget; UI communicates progress and failure clearly.
- 🔶 Future (Option A): fully async report generation with client-side polling — documented, not implemented.

## 5. Duplicate prompt templates
- [x] One shared `_build_report_prompt(kind, ...)` used by summary and recommendations; output rules defined once.

---

## Verification steps
- [x] `GET /api/llm/status` returns `{connected, model, latency_ms}` after login.
- [x] Prediction response includes `report_sources`.
- [x] Log shows LLM call duration / failure reasons.
- [x] Frontend build passes with the new LLM states.