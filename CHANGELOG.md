# Changelog

Notable changes to the Intubation_Project. Format follows
[Keep a Changelog](https://keepachangelog.com/); entries grouped by date.

## 2026-10-20 — Production hardening + repo reorganization (dashboard-redesign)

### Repo organization
- **`frontend/`**: Next.js app moved from repo root into its own folder
  (`src/`, `public/`, `package.json`, configs, `Dockerfile.frontend`).
  All build configs updated: `docker-compose.yml`, `render.yaml`,
  `.github/workflows/deploy.yml` (test-frontend runs in `frontend/`).
  Docker build contexts remain the repo root (Render requirement); the
  frontend Dockerfile now COPYs from `frontend/` and uses `npm ci`.
- **`data/`**: `dataset.xlsx` moved to `data/dataset.xlsx`; the real patient
  data folder (`DATASET/` — laryngoscopy spreadsheets + 343 clinical photos,
  PHI) moved to `data/raw/` and hard-ignored in `.gitignore` + `.dockerignore`.
  All training/generation scripts updated to the new path.
- **`docs/resources/`**: reference PDFs/PPTs moved from `PPTS_&_Folders/`.
- Removed dead deployment artifacts: `backend/deploy/Dockerfile.ui`,
  `backend/deploy/frontend.py` (old Streamlit UI, superseded by Next.js).
- `.gitignore`/`.dockerignore` hardened: `DATASET/`, `data/raw/`, `strix/`
  (unrelated local project), `UI Design/`, `.playwright-mcp/`, `.codegraph/`,
  `.pytest_cache/`, `.expo/`. `.opencode/agent/` stays tracked (project config).

### Backend (ML serving correctness)
- **Fail-fast model loading** (`model_loader.py`): missing checkpoint raises at
  startup (`MODEL_REQUIRED=true` default) — no more silently serving random
  weights; state_dict loading is strict; dev fallback (`MODEL_REQUIRED=false`)
  is loudly flagged in logs + `/ready`.
- **Model version traceability**: every prediction stores `model_version`
  (checkpoint name + sha256:8); `/ready` reports it.
- **Non-blocking inference**: torch prediction moved to `asyncio.to_thread` —
  the event loop no longer stalls behind CPU-bound predictions.
- **Configurable softmax temperature** (`MODEL_SOFTMAX_TEMPERATURE`, default
  5.0, behavior unchanged) — flagged as calibration debt for real data.

### Backend (observability + hygiene)
- **`/live` + `/ready`** endpoints: `/ready` pings Mongo + checks model status,
  returns 503 when degraded; `/health` kept for Docker/Render health checks.
- **JSON logging** (`logging_config.py`): one JSON object per line
  (ts, level, logger, message, request_id, duration_ms).
- **Request-ID middleware**: `X-Request-ID` echoed on every response, tied to
  structured access logs.
- **Pagination clamps**: patients/predictions list endpoints cap `limit` at
  200; `patient_id` restricted to URL-safe charset in schemas.

### Testing
- **pytest suite added** (`tests/`, 51 tests): schema validation, auth/token/
  role checks, fail-fast loader + golden prediction regression lock, input
  preparation (scaler application, category mappings), LLM fallbacks, rate
  limits. Wired into CI as a **required gate** (was import-only smoke).

### Verification (all passing)
- `python -m pytest tests/ -q` → 51 passed
- `python scripts/smoke_test_prediction.py` → cardinality + end-to-end
  predictions OK against `data/dataset.xlsx` + checkpoints
- `cd frontend && npm run build` → 12 pages built, standalone output
