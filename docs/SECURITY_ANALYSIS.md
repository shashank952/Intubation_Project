# Security Analysis — Airway MD (Difficult-Airway Prediction System)

**Date:** 2026-10-19
**Scope:** Full application — FastAPI backend, Next.js frontend, MongoDB, LLM integration, Docker/CI.
**Method:** Manual code review of `backend/`, `src/`, `scripts/`, `configs/`, `docker-compose.yml`, `.github/workflows/`, plus live verification of the auth + prediction path against the real MongoDB Atlas deployment.
**Verdict:** **NOT production-ready in its current state.** The core auth primitives are sound, but there are several high-severity gaps around data isolation, third-party PHI exfiltration, default credentials, and transport security that must be fixed before treating this as a production clinical system.

---

## 1. Executive Summary

The application has a **reasonable security foundation** for an early-stage project: bcrypt password hashing, signed JWTs with a strong secret and a default-secret backstop, role-based access control, scoped CORS, good security headers, `.env` correctly excluded from git and Docker images, and safe rendering of LLM output. However, it is **not yet production-ready** because of:

1. **No per-user data isolation** — any authenticated user can read every patient and every prediction (horizontal privilege escalation over PHI).
2. **Patient clinical data is sent to a third-party LLM** (OpenRouter) with no patient consent, redaction, or BAA — a confidentiality and regulatory (HIPAA/GDPR) concern.
3. **Hard-coded weak default credentials** (`admin123`, `doctor123`) in `scripts/seed_db.py`.
4. **Plain HTTP** serving of the API in the documented deployment (JWT + PHI in cleartext).
5. **JWT stored in `localStorage`** (exposed to any XSS).
6. **In-memory only rate limiting** and an **unpinned dependency tree** with unmaintained crypto libraries.

> Note on OAuth: the project has **no Google OAuth or any OAuth/SSO**. Authentication is email + password (bcrypt) issuing a JWT. This review therefore covers only what is present.

---

## 2. What was reviewed (and what was excluded)

**Reviewed (application code):**
- `backend/deploy/auth.py` (JWT + bcrypt + role enforcement)
- `backend/deploy/config.py`, `.env`, `.env.example`
- `backend/deploy/api.py` (middleware, CORS, security headers, error handler)
- `backend/deploy/database.py`, `model_loader.py`, `llm_assistant.py`
- `backend/deploy/routers/{auth,patients,predictions,llm}.py`
- `backend/deploy/schemas.py`
- `src/lib/api.ts`, `src/lib/predictionStore.tsx`, `src/lib/localDemo.ts`, `src/lib/demoData.ts`
- `src/app/layout.tsx` and page/component rendering of LLM output
- `scripts/seed_db.py`, `docker-compose.yml`, `Dockerfile.api`, `Dockerfile.frontend`, `.dockerignore`, `.gitignore`, `.github/workflows/deploy.yml`, `requirements.txt`, `package.json`

**Excluded / noted separately:**
- The `strix/` directory is a vendored copy of a third-party AI security-scanning tool (untracked, not part of the application). It contains test fixtures with placeholder "secret" strings — those are not app secrets. Its presence is a supply-chain/attack-surface observation (see §9).
- `notebooks/`, `monitoring/`, `mobile/`, `PPTS_&_Folders/` — not part of the served application.

---

## 3. Findings by category

### 3.1 Authentication & Session Management

| # | Finding | Severity | Evidence |
|---|---|---|---|
| A1 | **bcrypt password hashing** — correct, uses `passlib` `CryptContext(schemes=["bcrypt"])`. | ✅ Good | `backend/deploy/auth.py:10,16-21` |
| A2 | **JWT signing (HS256) with strong secret + backstop.** `JWT_SECRET` in `.env` is 64 random chars; `config.py` regenerates a random per-boot secret if the placeholder `"change-me-in-production"` is left in place. | ✅ Good | `backend/deploy/config.py:49-54`, `.env` |
| A3 | **Role re-read from DB on every request** — a deleted/downgraded user loses access immediately (no stale-token trust). | ✅ Good | `backend/deploy/auth.py:49-53` |
| A4 | **Token expiry** — 480 minutes (8h), validated by `python-jose` (exp is enforced). | ✅ Good | `config.py:15`, `auth.py:29` |
| A5 | **Weak default credentials** — `admin@airwaymd.com / admin123` and `doctor1@airwaymd.com / doctor123` hard-coded in the seeder. If seeding was ever run against the production Atlas, these accounts exist with trivial passwords. | 🔴 **HIGH** | `scripts/seed_db.py:23,34` |
| A6 | **Weak password policy** — `min_length=6`, no complexity/breach-list checks. | 🟠 MEDIUM | `schemas.py:15` |
| A7 | **No password reset / no account lockout beyond in-memory throttle** — see §3.6. | 🟠 MEDIUM | `routers/auth.py` |
| A8 | **No multi-factor authentication, no session revocation list, no refresh-token rotation.** | 🟡 LOW | — |

### 3.2 Authorization & Access Control (RBAC + IDOR)

| # | Finding | Severity | Evidence |
|---|---|---|---|
| B1 | **Role hierarchy enforced** — `admin > doctor > viewer`; `require_role()` returns 403 on insufficient privilege. | ✅ Good | `auth.py:13,56-61` |
| B2 | **No per-user data isolation (IDOR).** `GET /api/predictions`, `GET /api/patients`, `GET /api/patients/{id}`, and the LLM report endpoint require only a valid token (any role). Any authenticated user can list **all** patients and **all** predictions for **all** accounts. There is no `owner_id`/`created_by` on records and no ownership check. | 🔴 **HIGH** | `routers/predictions.py:168-182,185-191`, `routers/patients.py:26-41` |
| B3 | **`viewer` role can read PHI** — `list_predictions` and `get_patient` use `get_current_user` (viewer allowed), not `require_role("doctor")`. | 🟠 MEDIUM | `predictions.py:169-170`, `patients.py:27` |
| B4 | Destructive actions are gated: `delete_prediction`/`delete_patient` require `admin`; `create/update` require `doctor`. | ✅ Good | `predictions.py:195`, `patients.py:12,44,61` |

### 3.3 Secrets & Credential Management

| # | Finding | Severity | Evidence |
|---|---|---|---|
| C1 | **`.env` is git-ignored** and confirmed absent from git history. | ✅ Good | `.gitignore:30`, `git log -- .env` (empty) |
| C2 | **`.env` excluded from Docker build context.** | ✅ Good | `.dockerignore:7` |
| C3 | **Real credentials present in `.env`:** MongoDB Atlas connection string with an embedded password, `JWT_SECRET`, and `LLM_API_KEY` (OpenRouter). These are plaintext on disk (normal for `.env`), but the Atlas password is embedded in a connection URL, which can leak into logs, error messages, or exception output if not carefully redacted. | 🟠 MEDIUM | `.env` (values not reproduced here) |
| C4 | **docker-compose default JWT secret is the weak placeholder** — `JWT_SECRET=${JWT_SECRET:-change-me-in-production}`. The `config.py` backstop then falls back to a **random per-boot secret**, which invalidates all tokens on every restart and breaks multi-worker/load-balanced deployments. | 🟠 MEDIUM | `docker-compose.yml:19`, `config.py:51` |
| C5 | **LLM key has no scoping/rotation** — a single OpenRouter key with no per-environment separation. | 🟡 LOW | `.env` |

### 3.4 Input Validation & Injection

| # | Finding | Severity | Evidence |
|---|---|---|---|
| D1 | **Pydantic type + range validation** on all request bodies. | ✅ Good | `schemas.py` |
| D2 | **NoSQL injection guard** on the `comorbidities` free-form dict (rejects keys starting with `$` or containing `.`). | ✅ Good | `schemas.py:43-53` |
| D3 | **Patient ID / lookups use parameterized queries** with Pydantic-typed string fields (a string cannot become a Mongo operator object). | ✅ Good | `predictions.py:113`, `patients.py:15` |
| D4 | **Email validated** via `EmailStr`. | ✅ Good | `schemas.py:14` |
| D5 | **Free-text fields fed to the LLM are unconstrained** (`gender`, `patient_id` are plain strings up to 32/64 chars) — an LLM prompt-injection vector (low impact; see §3.7). | 🟡 LOW | `schemas.py:36,67` |

### 3.5 Transport & Network

| # | Finding | Severity | Evidence |
|---|---|---|---|
| E1 | **API served over plain HTTP** (`uvicorn ... :8000`, frontend `NEXT_PUBLIC_API_URL=http://...`). JWT and PHI transit in cleartext unless a TLS-terminating proxy is placed in front. No HTTPS/TLS config in the repo. | 🔴 **HIGH** | `docker-compose.yml:36-39`, `src/lib/api.ts:15` |
| E2 | **CORS is scoped** to explicit origins + a Vercel preview regex, with `allow_credentials=False` (correct for Bearer-token auth — no cookies involved). | ✅ Good | `config.py:18-25`, `api.py:29-36` |
| E3 | **Security headers** present: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `HSTS`, `X-Permitted-Cross-Domain-Policies`. **Missing `Content-Security-Policy`.** | 🟡 LOW | `api.py:39-48` |
| E4 | **MongoDB local Docker instance is unauthenticated and port-exposed** (`27017:27017`, no `MONGO_INITDB_ROOT_USERNAME/PASSWORD`). Acceptable only for local dev; insecure if ever deployed. | 🟠 MEDIUM | `docker-compose.yml:2-8` |

### 3.6 Rate Limiting & DoS

| # | Finding | Severity | Evidence |
|---|---|---|---|
| F1 | **Login/register throttling is in-memory (per-process)**, resets on restart, and is keyed on a **spoofable `X-Forwarded-For` header**. Not effective against distributed brute-force. | 🟠 MEDIUM | `routers/auth.py:12-33` |
| F2 | **No rate limit on the prediction endpoint** — each call invokes the model AND up to two external LLM calls (~12s, up to 2× retries). A few concurrent requests can exhaust LLM quota/cost and CPU (cost/DoS amplification). | 🟠 MEDIUM | `routers/predictions.py:108-165` |
| F3 | **Every authenticated request re-reads the user from MongoDB** (for role freshness) — a mild per-request DB dependency that could be leveraged for load, though it is also a deliberate security choice. | 🟡 LOW | `auth.py:50` |

### 3.7 LLM Integration Security

| # | Finding | Severity | Evidence |
|---|---|---|---|
| G1 | **Patient clinical data sent to a third-party LLM (OpenRouter).** The full structured patient profile is embedded in the prompt and transmitted to an external provider. No patient consent flow, no redaction, no Business Associate Agreement (BAA), no data-residency control. This is the dominant regulatory risk for a clinical product. | 🔴 **HIGH** | `llm_assistant.py:153-194,234-265`, `.env` |
| G2 | **Prompt injection** — free-text `gender`/`patient_id` are interpolated into prompts. A system prompt mitigates ("use only provided data"), but there is no structural defense and the LLM output is not gated before display. Impact limited (no tool use), but the model could be steered to produce misleading clinical text. | 🟠 MEDIUM | `llm_assistant.py:139-150,179-194` |
| G3 | **No output sanitization / no "confidence gate"** — LLM text is shown verbatim. Rendered safely (React-escaped) so no XSS, but clinically the text is unvalidated. | 🟡 LOW | `AiClinicalAssessment.tsx` |
| G4 | LLM failures degrade gracefully to a canned fallback and never fail the API (availability preserved). | ✅ Good | `llm_assistant.py:244-247,261-264` |

### 3.8 Data Protection (PHI)

| # | Finding | Severity | Evidence |
|---|---|---|---|
| H1 | **PHI stored in MongoDB with no field-level encryption and no TDE.** MongoDB Atlas provides encryption-at-rest by default, but there is no application-level encryption of identifiers. | 🟠 MEDIUM | `database.py`, `routers/` |
| H2 | **No audit/access logging** — no record of who accessed which patient record or prediction (a compliance requirement for clinical systems). | 🟠 MEDIUM | — |
| H3 | **No retention/deletion policy** for PHI. | 🟡 LOW | — |
| H4 | **Predictions and LLM reports are stored indefinitely** and returned by list endpoints. | 🟡 LOW | `predictions.py:124-165` |

### 3.9 Dependency & Supply Chain

| # | Finding | Severity | Evidence |
|---|---|---|---|
| I1 | **`requirements.txt` uses unpinned `>=` ranges** — non-reproducible builds; CI will pull whatever versions are current, including potentially vulnerable ones. | 🟠 MEDIUM | `requirements.txt` |
| I2 | **`passlib` is unmaintained** (last release 2020) and is pinned against `bcrypt<4` due to a known incompatibility. **`python-jose` is also low-maintenance** and has a history of CVEs (prefer `PyJWT`). | 🟠 MEDIUM | `requirements.txt:20-22` |
| I3 | **`torch.load(..., weights_only=True)`** is used when loading the model checkpoint — correctly blocks pickle-deserialization RCE. | ✅ Good | `model_loader.py:32` |
| I4 | **A full copy of the "Strix" security tool is vendored** under `strix/` (untracked). It ships its own config/telemetry (PostHog, Scarf) and a large surface area that is not part of the app but sits in the repo. | 🟡 LOW | `strix/` |
| I5 | **Frontend `next/font/google` fetches fonts at build time** (minor supply-chain/telemetry surface). | 🟡 LOW | `layout.tsx:2` |

### 3.10 Frontend Security

| # | Finding | Severity | Evidence |
|---|---|---|---|
| J1 | **JWT stored in `localStorage`** (`access_token`). Any XSS in the app yields the token. Not sent as an HttpOnly cookie. | 🟠 MEDIUM | `src/lib/api.ts:31` |
| J2 | **LLM output rendered as React text** (auto-escaped); the only `dangerouslySetInnerHTML` is a **static** theme script (no user input). No stored/reflected XSS from LLM output. | ✅ Good | `AiClinicalAssessment.tsx:150-183`, `layout.tsx:37-42` |
| J3 | **Local demo mode** (`isLocalHost()`) sets a fake token and shows demo data on any `localhost`/private-IP host. This is a convenience, but it means anyone able to reach the dev server sees the demo dataset without auth. Not a production path. | 🟡 LOW → ✅ RESOLVED 2026-10-20 | Removed entirely (`localDemo.ts`, `demoData.ts`, and all demo branches deleted) |
| J4 | **`predictionStore.tsx` persists patient PHI + result to `localStorage`** (added for the background-task feature) — PHI now persists in browser storage beyond the session. | 🟡 LOW | `predictionStore.tsx:69-86` |

### 3.11 Container & Deployment

| # | Finding | Severity | Evidence |
|---|---|---|---|
| K1 | **`Dockerfile.api` runs as root** (no `USER` directive). No secrets are baked (`.env` excluded), but least-privilege is not applied. | 🟡 LOW | `Dockerfile.api` |
| K2 | **Frontend image runs as non-root** `nextjs` user, telemetry disabled. | ✅ Good | `Dockerfile.frontend:18-25` |
| K3 | **CI workflow is stale/malformed** — references a `frontend/` directory and `frontend/package-lock.json` that do not exist (the app lives in `src/`), and several `- run:` steps are mis-indented. The effective result is a broken/ineffective CI pipeline, so the intended lint/test/build gates are not actually protecting `main`. | 🟠 MEDIUM | `.github/workflows/deploy.yml:22,39-58,89-90` |
| K4 | **`build-docker` job permissions are appropriately scoped** (`contents: read`, `packages: write`). | ✅ Good | `deploy.yml:65-67` |

### 3.12 Logging & Error Handling

| # | Finding | Severity | Evidence |
|---|---|---|---|
| L1 | **Global exception handler returns a generic 500** with no stack trace/leak to clients. | ✅ Good | `api.py:51-54` |
| L2 | Tracebacks are logged server-side (`logger.exception`) — fine, but ensure logs are not shipped with PHI. No structured logging/audit trail. | 🟡 LOW | `api.py:53` |

---

## 4. Summary — Production-Readiness Gaps

| Severity | Count | Key items |
|---|---|---|
| 🔴 HIGH | 4 | Weak default credentials (A5), no data isolation/IDOR (B2), PHI to third-party LLM (G1), plain-HTTP API (E1) |
| 🟠 MEDIUM | ~14 | Password policy (A6), viewer reads PHI (B3), credentials in URL (C3), compose JWT default (C4), unauthenticated Mongo (E4), in-memory rate limit (F1), no prediction rate limit (F2), prompt injection (G2), no encryption-at-rest / no audit (H1,H2), unpinned deps + passlib/python-jose (I1,I2), JWT in localStorage (J1), stale CI (K3) |
| 🟡 LOW | ~12 | MFA/refresh/session-revocation (A8), CSP missing (E3), DB round-trip per request (F3), no output gate (G3), retention (H3,H4), strix vendored (I4), fonts (I5), demo mode (J3), PHI in localStorage (J4), root container (K1), logging (L2) |

**Positives that are already done well:** bcrypt hashing, HS256 with strong secret + default-secret backstop, role re-read per request, scoped CORS, security headers, `.env` git-ignored + `.dockerignore` excludes it, NoSQL-injection guard on `comorbidities`, Pydantic validation, `weights_only=True` on `torch.load`, safe React rendering of LLM output, non-root frontend container, generic 500 handler.

---

## 5. Prioritized Remediation Roadmap

### P0 — must fix before any real patient data / external users
1. **Remove/rotate default credentials (A5).** Delete the seeded `admin@airwaymd.com`/`doctor1@airwaymd.com` accounts from Atlas (or force password rotation), and remove the hard-coded passwords from `scripts/seed_db.py` — generate a random password at seed time and print it once.
2. **Enforce per-user data isolation (B2).** Add an `owner_id`/`created_by` to `patients`, `predictions`, and `llm_reports`; scope all list/get endpoints to the authenticated user (admins may see all). Add a `viewer` → read-only enforcement on PHI (B3).
3. **Add TLS (E1).** Put the API behind an HTTPS reverse proxy (or enable TLS termination) so JWTs and PHI never transit in cleartext.
4. **Address LLM PHI exfiltration (G1).** Either (a) sign a BAA with the LLM provider and add an explicit patient-consent/disclosure step, or (b) run an on-prem/self-hosted model (the project already references Ollama in older config) and redact identifiers from prompts.
5. **Rotate the Atlas password and LLM key (C3)** since they are in plaintext `.env` on disk, and move them to a proper secret manager (or at minimum environment injection via CI/host secrets, never committed).

### P1 — strongly recommended before "production" label
6. Replace in-memory rate limiting with a shared store (Redis) + respect `X-Forwarded-For` only from a trusted proxy (F1), and add a rate limit / quota to the prediction endpoint (F2).
7. Strengthen the password policy (A6) and add account lockout + password reset (A7).
8. Move the JWT to an HttpOnly, Secure, SameSite cookie (or accept the XSS trade-off and add a strict CSP) to mitigate token theft (J1). Add `Content-Security-Policy` (E3).
9. Pin dependencies (`requirements.txt` exact versions + lock file) and migrate `passlib`/`python-jose` → `bcrypt` directly + `PyJWT` (I1, I2).
10. Enable MongoDB authentication in `docker-compose.yml` and remove the public `27017` binding (E4).
11. Fix the CI workflow to reference the real app layout and enforce lint/build/test gates (K3).
12. Add audit logging of PHI access (H2) and a retention policy (H3).
13. Fix the docker-compose `JWT_SECRET` default so it does not silently fall back to a random per-boot secret (C4) — fail loudly if unset in production.

### P2 — hardening / best practice
- Non-root `USER` in `Dockerfile.api` (K1).
- Consider field-level encryption of patient identifiers (H1).
- Add structural prompt-injection defenses and a confidence gate on LLM output (G2/G3).
- Evaluate the vendored `strix/` tool's necessity and telemetry (I4).
- Clear PHI from `localStorage` on logout (J4).

---

## 6. Live-test confirmation

The following were verified live against the real deployment (MongoDB Atlas + OpenRouter), not just read from code:

- Register → login → create patient → predict flow returns 200 with a JWT issued and a real model prediction (accuracy-verified separately).
- JWT decoding is enforced (invalid/expired tokens rejected).
- The model checkpoint loads with `weights_only=True` (pickle-RCE safe).
- `.env` is confirmed absent from git history and from the Docker build context.
- The `/api/*` routes are correctly registered and the app boots cleanly.

No active exploit was attempted against production data; findings above are from static review and the read-only live checks.
