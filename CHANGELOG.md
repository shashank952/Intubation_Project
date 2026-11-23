# Changelog

Notable changes to the Intubation_Project. Format follows
[Keep a Changelog](https://keepachangelog.com/); entries grouped by date.

## 2026-11-23 — Image NDMS panel (4-view morphometric score)

### Backend
- `POST /api/images/ndms`: accepts up to four view-tagged photos (`frontal`, `teeth`, `tongue`, `jawline`), reuses the existing in-memory redaction/quality pipeline, and returns per-view quality/geometry plus an NDMS score.
- `backend/deploy/image_analysis.py`: new view proxies (teeth/tongue colour statistics, jawline aspect + submental brightness) and pure `compute_ndms()` / `blend_risk()` helpers, unit-tested in `tests/test_ndms.py`.
- NDMS is 0–1 (0 favourable, 1 unfavourable), requires at least two usable components, and contributes a capped **+0 to +5** points to the tabular risk. It never lowers the risk and is labelled non-validated — photo features did not validate against the difficulty label on this dataset.

### Frontend
- Dashboard "Photo" tab renamed **Image**; new `ImageAnalysisPanel` with four fixed drag-and-drop slots (Frontal, Teeth & Lip-bite, Tongue out, Side & Jawline), redacted previews, an NDMS gauge, component bars, confidence, and the image risk contribution / combined risk.

## 2026-11-20 — Fix bimodal risk scores (label smoothing + calibrated temperature)

### Backend / ML
- `backend/training/train_tabular.py`: train with label smoothing (`LABEL_SMOOTHING=0.1`) so the TabTransformer no longer produces overconfident logits. Fixes the "risk score only ever ~13% (Easy) or ~88% (Difficult), Moderate never appears" issue — the model now predicts all three classes (Moderate recall 0.83 vs ~0 before).
- `tabular_scaler.pkl` is now written by the same training run (replaces the separate `scripts/save_scaler.py` step), so the checkpoint and scaler can never drift.
- `MODEL_SOFTMAX_TEMPERATURE` default changed 5.0 → 1.0. Label smoothing already calibrates the logits, so the old 5.0 temperature was over-flattening (it compressed the risk score into a ~40–60 band).
- Retrained `checkpoints/tabular_best.pt`: 0.792 accuracy / 0.931 AUC (down from 0.859/0.970 — the expected cost of honest, non-overconfident probabilities), with balanced per-class recall (Easy 0.82 / Moderate 0.83 / Difficult 0.73) and a continuous risk-score span.

## 2026-11-11 — Real-patient model, photo analysis endpoint, dashboard Photo tab

### Data pipeline
- Rebuilt the redacted image set from the corrected source folder
  (`data/raw/Image Dataset/AI Intubation`): 337 photos, 333 auto-redacted,
  4 reviewed manually; all 337 sit in `data/raw/redacted_images/`.
- `scripts/build_image_mapping.py`: filename -> patient mapping
  (`data/temp/image_mapping.csv`), a review workbook, and a thumbnail contact
  sheet. 79 of 80 labelled patients have photos; P-0023 has none and the
  P-0081/82 photos are left unmapped.
- `scripts/merge_laryngoscopy_datasets.py` + `scripts/onehot_laryngoscopy.py`:
  combined and one-hot workbooks with 80 unique patients
  (19 Easy / 53 Moderate / 8 Difficult).
- New analysis scripts: `train_tabular_baseline.py`, `feature_ablation.py`,
  `fusion_baseline.py`, `extract_image_features.py`, `teeth_visibility_check.py`,
  `train_final_tabular.py`.

### Model
- `checkpoints/tabular_real_v1.joblib` + `.json`: logistic regression on the 80
  real patients (11 features), 5-fold x 10 CV - 0.854 accuracy, 0.885 balanced,
  0.96 Difficult recall. Target is the doctor's recorded decision, not an
  intubation outcome.
- Measured: teeth adds +0.095 accuracy, beard adds nothing, and photo features
  do not improve the model (fusion 0.818 vs 0.854 tabular-only), so images are
  used for capture quality only.

### Backend
- `POST /api/images/analyze`: decodes the upload, redacts the eyes with the YOLO
  face model, returns quality/geometry plus a redacted preview; never stores the
  image and never returns a preview when no face is found.
- `PREDICTION_MODEL` (`real` | `synthetic`, default `real`). `/api/predictions`
  now serves the real model and returns `model_used` + `imputed_features`.
- `real_model_input.py`: explicit form -> feature mapping (15 mm per finger for
  mouth opening; teeth and chest are optional and median-imputed when absent).
- `PredictionInput` gains optional `teeth` and `chest_size_cm`.
- `requirements.txt`: `ultralytics>=8.4.0`, because image analysis is now on the
  served path.

### Frontend
- Dashboard tabs: **Assessment** / **Photo**. The upload card moved into the
  Photo tab with an optional patient ID field and a panel describing what the
  check does and does not do. Tabs are hidden with CSS rather than unmounted, so
  a half-filled assessment survives a tab switch.
- Patient form: teeth select and chest (cm) input in the advanced section.
- New `/images` page with a sidebar **Images** entry next to Patient Records: a
  large drag-and-drop area that accepts multiple JPEG/PNG files, checks them one
  at a time and shows a per-photo result card (redacted preview, usability,
  issues). Optional patient ID is applied to the batch's audit log.

### Tests
- `tests/test_image_analysis.py` (11) and `tests/test_real_model_input.py` (10);
  backend suite now 94 tests.

### Deployment notes
- `yolo26n-face.pt` is not in the repo or the image. Set `FACE_MODEL_PATH` and
  provision the weights, otherwise `/api/images/analyze` returns 503.
- `render.yaml` gains `PREDICTION_MODEL`, `REAL_MODEL_PATH` and `FACE_MODEL_PATH`.

## 2026-10-20 — Neo-brutalist loading system

- New `frontend/src/components/NeoLoader.tsx` with `inline` / `block` / `page`
  variants: brand-colored pulse blocks that step mechanically (`steps(1, end)`,
  hard 2px borders + collapsing offset shadows) and a photocopier-style scan
  bar. Works across all 7 themes via `--brand-*` CSS variables, light + dark,
  `prefers-reduced-motion` fallback (static fill), `role="status"` +
  screen-reader text.
- New `frontend/src/app/loading.tsx`: branded full-page loader for route
  transitions.
- Replaced the ad-hoc spinners in login, signup, patient form, reports
  (page + per-report row), dashboard background-assessment banner, AI
  assessment card (slow-response notice) and background-task toast.
  The 28px delete-icon spinner stays as a micro icon.

## 2026-10-20 — Removed local demo mode

- Deleted `frontend/src/lib/localDemo.ts` and `frontend/src/lib/demoData.ts`.
  The app no longer auto-creates a fake session or serves demo
  history/reports on localhost, private-IP hosts, or via `?demo=1`.
  Every environment now requires a real login against the real backend.
- Removed the demo branches from the dashboard (fake user, demo history,
  demo result, "demo mode" banner/error), login page, root redirect,
  `SessionProvider`, and `api.ts` (`ensureLocalSession`, demo return values).
- Idle-logout enforcement no longer needs a demo exemption — it applies
  everywhere.

## 2026-10-20 — Session idle logout (automatic sign-out)

### Backend
- **Server-enforced sliding sessions**: every JWT carries a `sid` claim; the
  new `sessions` collection tracks `created_at` / `last_activity_at` /
  `revoked_at`. `get_current_user` rejects missing, revoked, idle-expired
  (`SESSION_IDLE_TIMEOUT_MINUTES`, default 30) and absolute-expired
  (`SESSION_ABSOLUTE_TIMEOUT_HOURS`, default 12) sessions with typed 401
  details — `session_expired` / `session_revoked` / `relogin_required`.
- Activity-touch writes are throttled (`SESSION_TOUCH_INTERVAL_SECONDS`,
  default 60) so an active request stream does not write on every call.
- New `POST /api/auth/logout` (idempotent revoke — logout now actually
  invalidates the token server-side, not just local storage) and
  `POST /api/auth/heartbeat` (explicit "stay signed in" touch). Login now
  returns `expires_at`, `idle_timeout_seconds`, `warning_seconds`.
- JWT lifetime is capped by the absolute session timeout.
- Legacy tokens without `sid` are rejected — existing users sign in once
  after deploy.
- 13 new tests (`tests/test_sessions.py`): session state machine (idle /
  absolute / revoked / missing / naive-UTC), touch throttle, `sid`+`iat`
  claims, expiry capping.

### Frontend
- `useIdleTimeout` hook + `SessionWarningModal`: idle elapsed is computed from
  a timestamp (background tabs throttle `setInterval` to ~1/min, so ticks must
  never be counted), 2-minute warning with countdown and explicit
  "Stay signed in" (heartbeat) / "Log out" buttons, immediate recompute on
  `visibilitychange`, cross-tab logout via `storage` events, and centralized
  401 `session_expired` / `session_revoked` handling in `apiFetch`.
- Login page shows "signed out after a period of inactivity" on `?reason=idle`.
- Local demo mode (localhost) is exempt from idle enforcement.

### Note
This satisfies the HIPAA-style automatic-logoff expectation
(§164.312(a)(2)(iii)). Token storage is still `localStorage` — httpOnly
cookies / refresh-token rotation remain separate production work.

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
