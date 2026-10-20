# Production Readiness — Gap Analysis & Status

_Last updated: 2026-10-20 (branch `dashboard-redesign`)._
This is the working checklist for taking the Intubation_Project to production.
Status legend: ✅ done · 🔶 partial · ⛔ blocked (needs labeled real data) · ❌ not started.

## 1. ML correctness & serving

| Item | Status | Notes |
|---|---|---|
| Fail-fast on missing/corrupt checkpoint | ✅ | `MODEL_REQUIRED=true` default; strict state_dict load |
| Model version on every prediction | ✅ | `model_version` = checkpoint sha256:8, stored per prediction |
| Scaler applied at inference | ✅ | `tabular_scaler.pkl` loaded + applied in predictions router |
| Non-blocking inference | ✅ | `asyncio.to_thread`; event loop no longer stalls |
| Softmax temperature configurable | ✅ | `MODEL_SOFTMAX_TEMPERATURE` (default 5.0 — calibration debt) |
| Model trained/validated on REAL labeled data | ⛔ | Current `tabular_best.pt` is synthetic-trained (0.859/0.970 on synthetic test). **Top production blocker.** Needs the labeled real dataset (collection in progress) |
| Calibration (Platt/temperature) on real held-out data | ⛔ | Blocked on real data |
| Labeled image manifest (image → patient → label) | ⛔ | 343 photos in `data/raw/Image Dataset/`, no labels yet (user collecting) |
| Multimodal model trained + wired | ⛔ | Encoder/fusion code unexercised; trainer drops categoricals (`trainer.py:61,95`) |
| Drift/monitoring of input & output distributions | ❌ | Future: log prediction distribution, alert on shift |
| ONNX export fixed | ❌ | `export.py` dummy shapes wrong (1×20 + empty cats) |

## 2. Security

| Item | Status | Notes |
|---|---|---|
| JWT auth + bcrypt + role hierarchy | ✅ | admin > doctor > viewer; role read fresh from DB |
| Login/register/prediction throttles | ✅ | **In-memory, per-process** — move to Redis before multi-worker/HA |
| Input validation (bounds, charset, NoSQL keys) | ✅ | Pydantic schemas; patient_id URL-safe charset |
| Security headers + optional HTTPS enforcement | ✅ | Set `ENFORCE_HTTPS=true` + `BEHIND_PROXY=true` in prod |
| CORS pinned (no wildcard) | ✅ | Explicit origins + Vercel preview regex |
| Compose secrets required (no defaults) | ✅ | `JWT_SECRET`/`MONGO_PASSWORD` must be set |
| PHI never committed / baked into images | ✅ | `data/raw/` gitignored + dockerignored; verified |
| Token storage hardening (httpOnly cookie / refresh rotation) | ❌ | JWT currently in localStorage (XSS-exposed). Short-lived + refresh is the fix |
| Invite-only registration (no open doctor signup) | ❌ | Currently anyone can register as doctor |
| Dependency/SCA scanning in CI | ❌ | Add `pip-audit` + Dependabot |
| Rate limiting on export/list endpoints | 🔶 | List clamped (max 200); export capped at 10k rows; no per-user throttle |
| Secrets management beyond env vars | ❌ | Render sync:false works; consider a secret manager |

## 3. Compliance (medical)

| Item | Status | Notes |
|---|---|---|
| PHI excluded from repo/images | ✅ | Real data stays local in `data/raw/` |
| Regulatory posture (SaMD/CDSCO/FDA/CE decision) | ❌ | Decision + disclaimers needed before clinical use |
| Consent management + retention/erasure policy | ❌ | Required for real-patient deployment |
| PII redaction before external LLM calls | ❌ | Patient profile sent to OpenRouter today. On-prem LLM or redaction needed |
| DPA with LLM provider | ❌ | Required if external LLM sees patient data |
| Encryption at rest (Mongo) | ❌ | Plan: MongoDB Atlas encryption or field-level |
| Clinical validation study + bias/fairness audit | ⛔ | Blocked on real labeled data |
| LLM output guardrails/validation | ❌ | Fallback marked; output not medically validated |

## 4. Observability & reliability

| Item | Status | Notes |
|---|---|---|
| JSON structured logging + request IDs | ✅ | `logging_config.py` + middleware; ready for Loki/ELK |
| `/live` vs `/ready` split | ✅ | `/ready` = DB ping + model status, 503 when degraded |
| Log aggregation / metrics (Prometheus) / alerting | ❌ | Next: prometheus-fastapi instrumentation + hosted aggregation |
| Error tracking (Sentry) | ❌ | |
| MongoDB backups / replica set / DR runbook | ❌ | Single container + volume today; move to Atlas |
| Graceful shutdown drain | 🔶 | Lifespan closes DB; no request draining config |

## 5. Testing & CI

| Item | Status | Notes |
|---|---|---|
| Backend pytest suite + CI required gate | ✅ | 51 tests incl. golden prediction regression lock |
| Frontend build gate in CI | ✅ | `npm run build` in `frontend/` |
| API integration tests (TestClient + Mongo) | ❌ | Current tests are unit-level; DB integration next |
| E2E tests (Playwright) | 🔶 | `scripts/e2e_test.py` exists; not wired into CI |
| Load tests | ❌ | After event-loop fix, verify with k6/Locust |
| Lint gates are non-fatal | 🔶 | ruff/black `|| true` — tighten gradually |

## 6. Infra & deployment

| Item | Status | Notes |
|---|---|---|
| Docker images build from root context with clean `.dockerignore` | ✅ | Updated for `frontend/` + `data/` layout |
| render.yaml deploy config | ✅ | Both services; frontend Dockerfile path updated |
| Local dev parity after reorg | ✅ | `cd frontend && npm run dev`; `uvicorn backend.deploy.api:app` |
| Staging environment + blue-green rollback | ❌ | Render previews exist; formalize promote flow |
| Managed MongoDB | ❌ | Move to Atlas (encryption + backups) before prod |
| Worker/replica config for uvicorn | ❌ | Single process today; requires Redis rate limits first |
| GPU inference latency benchmark | ❌ | CPU default; benchmark P95 after real-data model |

## Top priorities once labeled real data arrives

1. Train + validate on real labeled data (tabular first, then images via manifest).
2. Calibrate `MODEL_SOFTMAX_TEMPERATURE` on held-out real data.
3. Redis-backed rate limits → multi-worker uvicorn → load test.
4. Token hardening (httpOnly/refresh) + invite-only registration.
5. PII redaction or on-prem LLM + DPA.
6. Managed Mongo + backups + Sentry + Prometheus.

## Explicitly deferred (data-blocked)

- Image dataset work (labels pending — user collecting): manifest generator,
  dedup, orientation normalization, image encoder training.
- Multimodal fusion training pipeline.
- Real-data model validation + calibration.
