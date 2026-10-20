# AGENTS.md — Minor_Project (Intubation_Project)

Multimodal difficult airway prediction (3-class: Easy/Moderate/Difficult).
30 tabular params + 5 image modalities (planned). Stack: PyTorch + FastAPI + MongoDB + Next.js + OpenAI-compatible LLM (OpenRouter default).

## Source of truth

- `docs/project_plan.md` — original design doc (historical; some paths predate the 2026-10 reorg)
- `docs/PRODUCTION_READINESS.md` — production gap analysis and status
- `CHANGELOG.md` — what changed and why
- `configs/train_config.yaml` — hyperparams for the multimodal `Trainer` only (NOT loaded by standalone tabular/xgb/rf scripts)
- `.env.example` — all env vars (`MONGO_URL`, `JWT_SECRET`, `LLM_API_URL`, `LLM_MODEL`, `MODEL_CHECKPOINT`, `MODEL_DEVICE`, `MODEL_REQUIRED`, `MODEL_SOFTMAX_TEMPERATURE`, `BEHIND_PROXY`, `ENFORCE_HTTPS`)

## Repo layout (2026-10 reorg)

```
├── backend/          FastAPI + ML (deploy/, models/, training/, data/)
├── frontend/         Next.js 14 dashboard (src/, public/, Dockerfile.frontend)
├── mobile/           Expo React Native app (Airway MD)
├── data/             dataset.xlsx (tracked, synthetic) + raw/ (gitignored PHI)
├── checkpoints/      tabular_best.pt + tabular_scaler.pkl + baselines (tracked)
├── configs/ scripts/ notebooks/ tests/ monitoring/ docs/
```

`data/raw/` holds real collected patient data (laryngoscopy spreadsheets + 343 clinical photos). It is PHI: **gitignored and dockerignored — never commit, never bake into images.**

## Entrypoints & commands

| What | Command | Output |
|------|---------|--------|
| TabTransformer (tabular-only) | `python backend/training/train_tabular.py` | `checkpoints/tabular_best.pt` |
| XGBoost baseline | `python backend/training/train_xgboost.py` | `checkpoints/xgboost_best.json` |
| Random Forest baseline | `python backend/training/train_randomforest.py` | `checkpoints/randomforest_best.pkl` |
| Regenerate synthetic data | `python scripts/generate_synthetic_data.py` | `data/dataset.xlsx` (2500 rows) |
| Run tests | `python -m pytest tests/ -q` | 51 tests |
| End-to-end smoke | `python scripts/smoke_test_prediction.py` | cardinality + 2-patient prediction check |
| Run API | `uvicorn backend.deploy.api:app --host 0.0.0.0 --port 8000` | FastAPI `:8000` (`/health`, `/live`, `/ready`) |
| Run Frontend (dev) | `cd frontend && npm install && npm run dev` | Next.js `:3000` |
| Docker Compose | `docker-compose up --build` | API + Frontend + MongoDB (secrets required) |
| Seed DB users | `docker exec -it <project>-api-1 python scripts/seed_db.py` | admin/doctor users |

No Makefile, no `pyproject.toml`, no pre-commit hooks.

## Architecture

```
   Next.js (frontend/, :3000)      Expo app (mobile/)
          │ HTTP + JWT                    │ HTTP + JWT
          ▼                               ▼
   FastAPI (backend/deploy/, :8000) — auth / patients / predictions / llm routers
          │                    │
          ▼                    ▼
   MongoDB (:27017)      OpenAI-compatible LLM API (OpenRouter default)
```

- **Frontend**: Next.js 14 App Router, Tailwind, Recharts, lucide-react — `frontend/src/`
- **Backend**: FastAPI + Motor (async Mongo) — `backend/deploy/`
- **ML**: TabTransformer (TabularModel, 7 numerical + 22 categorical) — `backend/models/tabular_model.py`
- **LLM**: prompt assembly in `backend/deploy/llm_assistant.py`, canned fallback on failure

## Backend layout (backend/deploy/)

- `api.py` — FastAPI app: lifespan (DB + indexes + model), CORS, security headers, HTTPS enforcement, request-ID middleware, `/health` `/live` `/ready`
- `config.py` — Pydantic settings (see `.env.example`); JWT secret backstop
- `database.py` — Motor connection, indexes, audit logging
- `auth.py` — JWT + bcrypt, role hierarchy (admin > doctor > viewer), `require_role(...)`, session `sid` claims + `session_error(...)`/`should_touch(...)` helpers
- `model_loader.py` — **fail-fast** checkpoint loading (strict state_dict), model version (sha256:8) on every prediction
- `logging_config.py` — JSON-per-line log formatter
- `llm_assistant.py` — LLM prompt engineering + fallback clinical text
- `routers/{auth,llm,patients,predictions}.py` — `/api/auth/login|logout|heartbeat|me`, etc.
- `schemas.py` — Pydantic input/output models with bounds + patient_id charset
- `export.py` — ONNX export (STALE — wrong dummy shapes, see gotchas)
- `Dockerfile.api` — API image (root build context)

## Key gotchas (verified from code)

- **Model must load or the app refuses to start**: `MODEL_REQUIRED=true` (default). A missing checkpoint raises at startup instead of silently serving random weights. `MODEL_REQUIRED=false` is dev-only.
- **Sessions are server-enforced**: every JWT carries a `sid` claim; the `sessions` collection holds `last_activity_at`. Idle longer than `SESSION_IDLE_TIMEOUT_MINUTES` (30) or older than `SESSION_ABSOLUTE_TIMEOUT_HOURS` (12) → 401 with `detail.code` = `session_expired` (or `session_revoked` after logout). Do **not** add background API polling — it would keep idle sessions alive and defeat automatic logoff. Legacy tokens without `sid` are rejected (`relogin_required`); users sign in once after deploy.
- **Never count idle ticks in the browser**: background tabs throttle `setInterval` to ~1/min. `frontend/src/lib/useIdleTimeout.ts` computes elapsed from a timestamp and recomputes on `visibilitychange` — do not rewrite it as a decrementing counter.
- **Softmax temperature 5.0 is calibration debt**: softens synthetic-training logits. Tune on real held-out data before clinical use (`MODEL_SOFTMAX_TEMPERATURE`).
- **In-memory rate limits** (login/register/predict): per-process only. Running multiple uvicorn workers or restarting resets them — move to Redis before scaling horizontally.
- **Multimodal trainer drops categoricals**: `backend/training/trainer.py:61,95` hardcode `categorical_indices = []`. Only the standalone `train_tabular.py` path is correct (22 cats + 7 nums, which is what `tabular_best.pt` used).
- **No `train_multimodal.py`**: `trainer.py` is a class only — dataset wiring (`backend/data/`) exists but nothing drives it end-to-end.
- **Image data is unlabeled**: `data/raw/Image Dataset/` has 343 clinical photos with no manifest linking them to patients or Easy/Moderate/Difficult labels. Image encoder + fusion code is unexercised.
- **ONNX export mismatch**: `export.py` uses `torch.randn(1, 20)` + empty cats — does not match TabularModel (7 num, 22 cat). Fix before exporting.
- **LLM silently falls back**: external LLM failures return canned text (marked `source: "fallback"` in reports). If LLM output "stopped working", check the provider + `LLM_API_KEY`.
- **GPU constraint**: 4GB VRAM (GTX 1650 Ti). `MODEL_DEVICE=cpu` is the default; `cuda` only for local training.
- **Docker build contexts are repo root**: `frontend/Dockerfile.frontend` and `backend/deploy/Dockerfile.api` both `COPY` from root context, filtered by the root `.dockerignore`. Keep that file updated when adding big dirs.
- **Compose container name for seeding**: `<project-prefix>-api-1` (e.g. `minor_project-api-1`).
- **Git signing is broken locally**: commit signing is enabled but no GPG secret key exists (`gpg: No secret key`), so commits land unsigned. Disable signing or import the key.

## CI (`.github/workflows/deploy.yml`)

Triggers on push/PR to `main`. Four jobs:

1. `lint` — `ruff check backend/ --ignore E402,F403,F401 --exit-zero`, `black --check backend/ --diff || true` (both non-fatal)
2. `test-backend` — installs requirements + pytest, runs `python -m pytest tests/ -q` (**required gate**), import smoke checks (spins up Mongo service)
3. `test-frontend` — in `frontend/`: `npm ci`, `npm run lint`, `npm run build`
4. `build-docker` — needs 1-3; pushes `api` and `frontend` images to `ghcr.io` on push to main

## Pre-trained checkpoints

| File | Accuracy | AUC-ROC |
|------|----------|---------|
| `checkpoints/tabular_best.pt` | 0.859 | 0.970 |
| `checkpoints/xgboost_best.json` | 0.845 | 0.962 |
| `checkpoints/randomforest_best.pkl` | 0.813 | 0.953 |

Trained on synthetic/augmented data (`data/dataset.xlsx`) — **not validated on real clinical data.** `tabular_scaler.pkl` must accompany `tabular_best.pt` (the API applies it at inference).

## Default users (after `seed_db.py`)

| Username | Password | Role |
|----------|----------|------|
| admin | admin123 | admin |
| doctor1 | doctor123 | doctor |

## Subagents (`.opencode/agent/`)

`@ml-engineer`, `@devops-engineer`, `@frontend-dev`, `@backend-db-engineer`, `@data-scientist` — see those files for domain scopes.
