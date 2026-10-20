# Airway MD — Mobile Application Specification

> **Purpose of this document:** Complete, implementation-ready specification for converting the **Airway MD** web application (Next.js dashboard + FastAPI backend) into a **native mobile application**. This document is the single source of truth for the mobile build. A work plan / implementation plan should be derived directly from the sections below.
>
> **Source web app:** Multimodal Difficult Airway Prediction (3-class: **Easy / Moderate / Difficult**) — clinical decision support for anesthesiologists.
> **Web stack today:** Next.js 14 + React 18 + TypeScript + Tailwind (frontend, repo root `src/`), FastAPI + Motor (async MongoDB) backend (`backend/deploy/`), PyTorch TabTransformer inference (`tabular_best.pt`), OpenRouter LLM (Qwen 2.5 72B) for clinical narratives.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Current Web App Inventory (What We Are Converting)](#2-current-web-app-inventory)
3. [Conversion Goals & Scope Decisions](#3-conversion-goals--scope-decisions)
4. [Technology Stack Recommendation](#4-technology-stack-recommendation)
5. [High-Level Mobile Architecture](#5-high-level-mobile-architecture)
6. [Navigation Structure](#6-navigation-structure)
7. [Screen-by-Screen Specification](#7-screen-by-screen-specification)
8. [Authentication & Secure Token Storage](#8-authentication--secure-token-storage)
9. [API Client Design](#9-api-client-design)
10. [Data Models (TypeScript Interfaces)](#10-data-models)
11. [State Management](#11-state-management)
12. [Design System & Theming](#12-design-system--theming)
13. [Offline & Connectivity Handling](#13-offline--connectivity-handling)
14. [Push Notifications (Optional)](#14-push-notifications-optional)
15. [Biometric Authentication (Optional)](#15-biometric-authentication-optional)
16. [Accessibility Requirements](#16-accessibility-requirements)
17. [Performance Requirements](#17-performance-requirements)
18. [Security & Clinical Compliance](#18-security--clinical-compliance)
19. [Proposed Project Structure](#19-proposed-project-structure)
20. [Dependencies List](#20-dependencies-list)
21. [Testing Strategy](#21-testing-strategy)
22. [Build, Release & Distribution](#22-build-release--distribution)
23. [Implementation Phases (Ordered)](#23-implementation-phases-ordered)
24. [Risks & Mitigations](#24-risks--mitigations)
25. [Decisions Needed Before Build Starts](#25-decisions-needed-before-build-starts)

---

## 1. Project Overview

### 1.1 What Airway MD Does

Airway MD predicts **intubation difficulty** for a patient *before* an airway procedure, using a combination of:

- **Tabular clinical parameters** (30 features: demographics, airway measurements, medical history, physical findings)
- **A trained ML model** (TabTransformer — `tabular_best.pt`, Accuracy 0.859 / AUC-ROC 0.970)
- **An LLM** (OpenRouter Qwen 2.5 72B) that converts the prediction into a **natural-language clinical summary + actionable recommendations** for the anesthesiologist.

Output is a **3-class prediction**: `Easy` / `Moderate` / `Difficult`, with confidence score, per-class probability distribution, a 0–100 risk gauge, and an AI-generated clinical narrative.

### 1.2 Core Users & Roles

| Role | Permissions (backend-enforced) |
|------|-------------------------------|
| **admin** (level 3) | Everything. Can delete patients, delete predictions, register users |
| **doctor** (level 2) | Create/update patients, run predictions, export CSV, view everything |
| **viewer** (level 1) | Read-only: view patients, predictions, reports |

Role hierarchy in backend (`backend/deploy/auth.py`): `ROLE_HIERARCHY = {"admin": 3, "doctor": 2, "viewer": 1}`.

Default seeded users: `admin/admin123`, `doctor1/doctor123`.

### 1.3 What the Mobile App Must Deliver

The mobile app must be a **1:1 functional port** of the web dashboard, optimized for phone/tablet use, with:

1. Login & role-aware access
2. Patient assessment (multi-section input form → prediction)
3. Rich prediction result display (risk gauge, confidence, probabilities)
4. AI clinical assessment (summary + recommendations + urgency banner)
5. Prediction/patient history with search, filter, delete, CSV export
6. Reports viewer (expandable LLM reports)
7. Settings (profile, dark mode, system status)
8. About (models, LLM info, architecture)

---

## 2. Current Web App Inventory

### 2.1 Screens / Routes (Web → Mobile Mapping)

| # | Web Route | Web File | Purpose | Mobile Equivalent |
|---|-----------|----------|---------|-------------------|
| 1 | `/` | `src/app/page.tsx` | Redirect to login or dashboard | Splash / auth-router (no visible screen) |
| 2 | `/login` | `src/app/login/page.tsx` | Username/password sign-in, stale-token check | **Login Screen** |
| 3 | `/dashboard` | `src/app/dashboard/page.tsx` | Main dashboard: patient form + prediction + AI report + stats + recent records | **Dashboard / Home Tab** (composed of sub-screens) |
| 4 | `/patients/new` | `src/app/patients/new/page.tsx` | Redirects to `#patient-entry` on dashboard | "New Assessment" button → scroll/route to Assessment |
| 5 | `/history` | `src/app/history/page.tsx` | Prediction history list (uses `PatientHistory` component) | **History Tab** |
| 6 | `/reports` | `src/app/reports/page.tsx` | Expandable LLM clinical reports | **Reports Tab** |
| 7 | `/settings` | `src/app/settings/page.tsx` | Profile, dark mode, system info | **Settings Tab** |
| 8 | `/about` | `src/app/about/page.tsx` | ML models, LLM info, architecture | **About Screen** (inside Settings stack) |

### 2.2 Web Components (Reusable Logic to Port)

| Component | File | Key Responsibilities | Port Notes |
|-----------|------|----------------------|------------|
| `Sidebar` | `src/components/Sidebar.tsx` | Nav (Dashboard, Patient Records, Reports, Settings, About), user chip, logout, dark-mode init, collapse/mobile drawer | → **Bottom Tab Bar** + optional drawer |
| `PatientForm` | `src/components/PatientForm.tsx` | 30-field multi-section form; validation ranges; test-data loaders (E/M/D/Random); compact mode; "More findings" toggle | → **Multi-step wizard** (largest port effort) |
| `RiskPredictionCard` | `src/components/RiskPredictionCard.tsx` | 270° radial gauge, confidence bar, stacked probability bar, Easy/Moderate/Difficult badge | → **Recharts-free SVG gauge** (react-native-svg) |
| `AiClinicalAssessment` | `src/components/AiClinicalAssessment.tsx` | Loading skeletons, "slow LLM" banner, urgency badge, summary bullets, recommendations, risk-factor banner, LLM fallback warning | → **Direct port**, text rendering only |
| `MiniHistory` | `src/components/MiniHistory.tsx` | Last 5 records on dashboard, selectable, "View all" link | → Dashboard sub-component |
| `PatientHistory` | `src/components/PatientHistory.tsx` | Full history: search, 4 filter tabs (All/Easy/Moderate/Difficult), CSV export, delete w/ confirm, table with view/delete actions | → **List screen** (table → cards/rows) |
| `StatsCard` | `src/components/StatsCard.tsx` | Overview counts (Easy/Moderate/Difficult, total) | → Dashboard summary row |
| — | `src/lib/api.ts` | Entire API client, JWT storage in `localStorage`, `apiFetch` wrapper, error normalization, CSV blob download | → **Rewrite for React Native** (fetch + SecureStore) |
| — | `src/types/index.ts` | All TypeScript interfaces | → **Port verbatim** (reuse file) |

### 2.3 Backend API Surface (Immutable Contract — Mobile Consumes This)

Base URL pattern: `<API_URL>` (e.g. `http://127.0.0.1:8000` locally, or hosted endpoint). All protected routes require header `Authorization: Bearer <token>`.

| Method | Path | Role | Request Body | Response | Notes |
|--------|------|------|--------------|----------|-------|
| POST | `/api/auth/login` | public | `{username, password}` | `{access_token, token_type:"bearer", user:{username, role}}` | 401 on bad creds |
| POST | `/api/auth/register` | public* | `{username, password, role?}` | `{message, username}` | *Web exposes it publicly; consider restricting for mobile |
| GET | `/api/auth/me` | any | — | `{username, role}` | Used to validate stored token |
| POST | `/api/patients` | doctor+ | `PatientCreate` | `PatientOut` (201) | 409 if `patient_id` exists |
| GET | `/api/patients` | any | `?skip=0&limit=50` | `PatientOut[]` | Sorted `created_at` desc |
| GET | `/api/patients/{patient_id}` | any | — | `PatientOut` | 404 if missing |
| PUT | `/api/patients/{patient_id}` | doctor+ | `PatientCreate` | `PatientOut` | 404 if missing |
| DELETE | `/api/patients/{patient_id}` | admin | — | 204 | Cascades: deletes patient's predictions too |
| POST | `/api/predictions` | doctor+ | `PredictionInput` | `{prediction, clinical_summary, recommendations, report_sources}` | **Slow**: runs ML + LLM. Web aborts at 35 s |
| GET | `/api/predictions` | any | `?patient_id=&skip=&limit=` | `PredictionOut[]` | Sorted `created_at` desc |
| GET | `/api/predictions/{prediction_id}/report` | any | — | `LLMReportOut` | `prediction_id` is Mongo ObjectId string |
| DELETE | `/api/predictions/{prediction_id}` | admin | — | 204 | Also deletes linked `llm_reports` |
| GET | `/api/predictions/export/csv` | doctor+ | — | CSV blob (`text/csv`) | All predictions, up to 10,000 rows |
| GET | `/api/llm/status` | any | — | `{connected, model, latency_ms}` | Health check for LLM connectivity |
| GET | `/health` | public | — | `{status:"ok", version}` | Backend liveness |

**Critical contract detail:** `POST /api/predictions` can take **5–40 seconds** because the LLM call is synchronous server-side (OpenRouter, timeout 15 s × 2 attempts + fallback). The mobile client **must** show a progress/loading state and use an AbortController with a 35–45 s timeout exactly like the web app (`src/app/dashboard/page.tsx:92-94`).

### 2.4 Form Validation Ranges (Must Be Reproduced Exactly)

From `src/components/PatientForm.tsx:62-81`:

| Field | Range / Rule | Error Text (web) |
|-------|--------------|------------------|
| `patient_id` | non-empty | "Required" |
| `age` | 0–120 | "0–120" |
| `gender` | required ("Male"/"Female") | "Required" |
| `bmi` | 10–60 | "10–60" |
| `mallampati_score` | 1–4 (integer) | "1–4 required" |
| `tmd` | 3–12 cm | "3–12 cm" |
| `neck_circumference` | 20–60 cm | "20–60 cm" |
| `mouth_opening` | 10–80 mm | "10–80 mm" |
| `smd` | 3–20 cm | "3–20 cm" |
| `neck_movement` | 30–180° | "30–180°" |

### 2.5 Prediction Request Payload — Full 30-Field Contract

```jsonc
// POST /api/predictions  (PredictionInput — ALL fields, defaults from schemas.py)
{
  "patient_id": "P-2024-0001",          // string, required
  "age": 54,                             // float, required
  "gender": "Female",                    // string, required  (Male | Female)
  "bmi": 23.7,                           // float, required
  "mallampati_score": 1,                 // float 1-4, required
  "tmd": 7.6,                            // float cm, required
  "neck_circumference": 36.4,            // float cm, required
  // --- Optional fields with server defaults ---
  "mouth_opening": 40.0,                 // mm
  "smd": 14.0,                           // cm
  "neck_movement": 85.0,                 // degrees
  "previous_airway_records": "No",       // "Yes" | "No"
  "disease_arthritis": "No",             // "Yes" | "No"
  "disease_diabetes": "No",              // "Yes" | "No"
  "disease_down_syndrome": "No",         // "Yes" | "No"
  "breathing_snoring": "No",             // "Yes" | "No"
  "breathing_sleep_apnea": "No",         // "Yes" | "No"
  "symptom_voice_changes": "No",         // "Yes" | "No"
  "symptom_difficulty_swallowing": "No", // "Yes" | "No"
  "symptom_cant_lie_flat": "No",         // "Yes" | "No"
  "injury_swelling": "No",               // "Yes" | "No"
  "injury_previous_neck_fracture": "No", // "Yes" | "No"
  "previous_emergencies_icu": "No",      // "Yes" | "No"
  "bmi_category": "Normal",              // derived category
  "beard": "No",                         // "Yes" | "No"
  "chest_size": "Medium",                // Small | Medium | Large
  "neck_structure": "Normal",            // Normal | Abnormal
  "tmd_category": "Normal",              // derived category
  "jaw_movement": "Normal",              // Normal | Reduced
  "neck_movement_category": "Normal",    // derived category
  "tissue_flexibility": "Normal"         // Normal | Reduced
}
```

> **Web behavior note:** `PatientForm` only collects the core 10 fields in the UI (patient_id, age, gender, bmi, mallampati, tmd, neck_circumference, mouth_opening, smd, neck_movement) plus the advanced Yes/No and category selects. The rest are sent with defaults. The mobile form should collect the **same 10 core + advanced section**, exactly mirroring the web form (do NOT build a 30-field form unless explicitly desired).

### 2.6 Prediction Response Contract

```jsonc
// POST /api/predictions response
{
  "prediction": {
    "prediction": "Moderate",           // "Easy" | "Moderate" | "Difficult"
    "confidence": 0.703,                // 0-1
    "risk_score": 0.5,                  // 0 (Easy) | 0.5 (Moderate) | 1.0 (Difficult)
    "probabilities": { "Easy": 0.152, "Moderate": 0.703, "Difficult": 0.145 }
  },
  "clinical_summary": "- Key risk factors...\n- ...",   // 5 bullet lines ("- " prefixed)
  "recommendations": "- Prepare ...\n- ...",            // 5-10 bullet lines
  "report_sources": { "summary": "llm" | "fallback", "recommendations": "llm" | "fallback" }
}
```

`GET /api/predictions` returns `PredictionOut[]` — same shape as `prediction` above plus `id` (Mongo ObjectId string) and `created_at` (ISO 8601).

### 2.7 Design Language to Preserve (Neo-Brutalist)

The web app has a distinctive visual identity that must carry into the mobile app:

- **Background:** cream paper `#F5F1DC` (light) / `#121212` (dark)
- **Ink:** near-black `#111111`
- **Brand accent:** yellow `#FFD900` (primary button/brand)
- **Semantic colors:** Easy = teal `#16C2C8` (`success`), Moderate = amber `#EAB308` (`warning`), Difficult = red `#FF5A5F` (`danger`)
- **Design tokens:** hard offset shadows (`4px 4px 0 #111`), thin **2px black borders**, small border radius (`4–8px`), bold typography, uppercase micro-labels with letter-spacing, mono font for numbers (`JetBrains Mono`)
- **Full palette + shadows + radii + animations:** see [Section 12](#12-design-system--theming)

---

## 3. Conversion Goals & Scope Decisions

### 3.1 Goals (Priority Order)

1. **Feature parity** — every web feature available on mobile (P0)
2. **Design parity** — preserve neo-brutalist identity (P0)
3. **Performance** — smooth 60fps navigation; prediction result should render within 200 ms of response (P1)
4. **Offline resilience** — graceful error states; never crash on network loss (P1)
5. **Security** — JWT stored in OS Keychain; no plaintext tokens (P0)

### 3.2 Explicitly OUT of Scope (v1)

- ❌ Image upload / multimodal image prediction (no backend support today — `data/raw/` empty)
- ❌ Offline model inference on-device (TabTransformer runs server-side)
- ❌ Patient image capture
- ❌ Real-time chat with LLM (predictions are one-shot)
- ❌ Web admin console for user management (register endpoint only)

### 3.3 Mobile-First UX Decisions (Deviations from Web, Deliberate)

| Web Pattern | Mobile Pattern | Reason |
|-------------|----------------|--------|
| Sidebar navigation | **Bottom tab bar** (5 tabs) | Thumb-reach, native convention |
| Full-page dashboard scroll | **Tabbed Home** + sub-screen stacks | Avoid massive scroll on small screens |
| 4-section form tabs | **Multi-step wizard** with progress indicator | Form is 30 fields — wizard reduces cognitive load |
| Expand/collapse report cards | **Detail screen** per report | Cleaner on mobile |
| Table for history | **Card list** with swipe actions or icon buttons | Tables don't fit phone width |
| `window.confirm` for delete | **Native Alert** dialog | Consistent destructive confirm |

---

## 4. Technology Stack Recommendation

### 4.1 Primary Recommendation: React Native + Expo (TypeScript)

**Why:** The web app is already **Next.js + React + TypeScript**. A React Native (Expo) codebase:
- Reuses the same language and mental model — fastest path for this codebase's maintainers
- Can port `src/types/index.ts` verbatim
- Shares validation logic patterns; identical API client logic
- Expo Managed Workflow handles native builds (EAS), push notifications (expo-notifications), secure storage (expo-secure-store), biometrics (expo-local-authentication) without Xcode/Android Studio for most work
- `react-native-svg` reproduces the radial gauge; `recharts` is NOT needed

| Layer | Choice | Justification |
|-------|--------|---------------|
| Framework | **Expo SDK 52+ (React Native, TypeScript)** | Managed workflow, OTA updates, dev builds |
| Navigation | **expo-router** (file-based) or **React Navigation v7** | File-based matches Next.js `src/app` mental model |
| Networking | **fetch** (built-in) with AbortController | Same pattern as web `api.ts`; no extra dep needed |
| Secure storage | **expo-secure-store** | JWT in Keychain/Keystore (replaces `localStorage`) |
| Charts/Gauge | **react-native-svg** | Radial gauge + progress bars drawn manually |
| State | **Zustand** (lightweight) + React Context for auth | Small app; Zustand avoids Redux boilerplate |
| Forms | **react-hook-form + zod** OR manual state (like web) | Web uses manual state — match it for parity; RHF optional |
| Date formatting | **date-fns** (already a dep) | Port `format(parseISO(...), 'MMM dd, yyyy HH:mm')` |
| Async storage (non-secret) | **@react-native-async-storage/async-storage** | Theme preference, cached lists |
| Icons | **lucide-react-native** | Same icon set as web (`lucide-react`) |
| Toasts | **react-native-toast-message** | Error/success feedback |
| Pull-to-refresh | **React Native RefreshControl** | Built-in |
| Fonts | **expo-font + Inter & JetBrains Mono** (same as web) | Design parity |

### 4.2 Alternative: Flutter

- Pros: single codebase, excellent performance, `fl_chart` for gauge
- Cons: complete rewrite in Dart; loses TS type-sharing; team must learn Dart
- **Decision:** Only choose Flutter if the team has stronger Dart skills. Default is React Native/Expo.

### 4.3 Alternative: Responsive PWA (Web App Wrapper)

- Pros: zero native work; web already responsive-ish
- Cons: no Keychain security, no biometrics, no push, weaker offline, no app-store presence; **not recommended for a clinical tool** due to security posture.

**Recommended: Expo (React Native) — proceed with that in the rest of this document.**

---

## 5. High-Level Mobile Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MOBILE APP (Expo/RN)                      │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Auth     │  │ Home     │  │ History  │  │ Reports  │    │
│  │ Stack    │  │ Tab      │  │ Tab      │  │ Tab      │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       └──────────────┴────────────┴─────────────┴──────────┘
│                              │
│                ┌─────────────┴──────────────┐
│                │  API Client (src/lib/api)   │
│                │  fetch + JWT + AbortControl │
│                │  SecureStore token vault    │
│                └─────────────┬──────────────┘
│                              │ HTTPS / HTTP
└──────────────────────────────┼─────────────────────────────┘
                               ▼
            ┌──────────────────────────────────────┐
            │   EXISTING FastAPI BACKEND (NO CHANGE) │
            │   /api/auth, /api/patients,            │
            │   /api/predictions, /api/llm           │
            │   + MongoDB + TabTransformer + LLM     │
            └──────────────────────────────────────┘
```

**Key principle — backend reuse:** The mobile app is a **pure API client**. The FastAPI backend requires **zero changes** for the mobile app (except optional CORS — see note below).

> ⚠️ **CORS note:** The web app is served from a browser origin; FastAPI currently has `allow_origins=["*"]` (`backend/deploy/api.py:26-30`), so CORS is already permissive and will NOT block native apps (native apps don't send Origin). **No backend change needed.**

### 5.1 API Base URL Configuration

- **Web:** `NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'`
- **Mobile:** Must be configurable at runtime (Settings screen or dev build env) because devices can't use `127.0.0.1` to reach a dev machine. Provide:
  - Default: `http://<LAN-IP>:8000` for dev (e.g., `http://192.168.1.50:8000`)
  - `app.config.ts` / `app.json` extra field: `extra.apiBaseUrl`
  - A **Settings → API URL** field (stored in AsyncStorage) for easy switching
  - Production: HTTPS URL of hosted backend

### 5.2 Network Security (Android HTTP)

- Android **blocks cleartext HTTP by default** (API 28+). For local dev against `http://LAN-IP:8000`:
  - Expo dev builds: `android:usesCleartextTraffic` must be enabled for dev (`app.json` → `expo.android.usesCleartextTraffic: true` for dev builds only) **or** use Expo Go which allows it.
  - **Production builds must use HTTPS only** and keep cleartext disabled.
- iOS: ATS blocks HTTP; add exception only in dev builds (Expo Go allows localhost). Production: HTTPS only.

---

## 6. Navigation Structure

### 6.1 Top-Level: Auth Gate + 4 Bottom Tabs

```
Root
├── AuthStack (when no valid token)
│   ├── Login
│   └── (Register — optional, admin-gated)
│
└── MainTabs (when token valid)   ← 4 bottom tabs
    ├── Tab 1: Home        (Dashboard stack)
    │   ├── Dashboard (list of: stats, quick assess button, recent records)
    │   ├── Assessment (multi-step form wizard)
    │   ├── PredictionResult (gauge + probabilities + AI report)
    │   └── ReportDetail
    ├── Tab 2: History     (History stack)
    │   ├── HistoryList   (search + filters + CSV export + delete)
    │   └── ReportDetail (from selected history row)
    ├── Tab 3: Reports     (Reports stack)
    │   ├── ReportsList   (expandable → pushes detail)
    │   └── ReportDetail
    └── Tab 4: Settings    (Settings stack)
        ├── Settings (profile, dark mode, API URL, system status)
        ├── About
        └── (optional) UserManagement (admin only, future)
```

### 6.2 Bottom Tab Bar Spec

- **5 items max is the native guideline; we use 4:** Home, History, Reports, Settings
- Each tab: icon (lucide-react-native) + label
- Active state: brand-yellow pill background with black border + hard shadow (matches web sidebar active state: `bg-brand-500 border-black shadow-[4px_4px_0_#000]`)
- Dark mode variants: `dark:border-neutral-600 dark:shadow-[4px_4px_0_#3F3F46]`
- Height: ~64px + safe-area inset
- Icons: `LayoutDashboard`, `History`, `FileText`, `Settings` (same as web Sidebar)

### 6.3 Stack Navigation Details

| Screen | Back behavior | Header |
|--------|---------------|--------|
| Login | — (no back) | Custom brand header (no native header) |
| Dashboard | — (root of tab) | Inline header with brand + user chip + theme toggle |
| Assessment | Back to Dashboard | "New Assessment" + step indicator |
| PredictionResult | Back to Dashboard | "Result" + patient id |
| ReportDetail | Back to list | Prediction id + date |
| HistoryList | — (root of tab) | "Patient Records" + role/user sub-line |
| Settings | — (root of tab) | "Settings" |
| About | Back to Settings | "About" |

---

## 7. Screen-by-Screen Specification

> Each screen lists: purpose, layout, data, interactions, states (loading/empty/error), and web-parity requirements. All screens follow the design system in Section 12.

### 7.1 Splash / Auth Router (web: `/`)

- **Purpose:** Decide AuthStack vs MainTabs; restore session.
- **Behavior:**
  1. On launch, read JWT from SecureStore.
  2. If token exists → call `GET /api/auth/me` to validate (web does this on login page, `login/page.tsx:19-36`).
  3. Valid → MainTabs. Invalid/expired → clear token, AuthStack.
  4. **No splash branding delay** beyond native splash screen (Expo splash, black bg, Stethoscope icon, "Airway MD").
- **States:** loading spinner while validating; error → Login with message.

### 7.2 Login Screen (web: `/login`)

- **Purpose:** Authenticate and store JWT.
- **Layout (port of `login/page.tsx`):**
  - Cream background (`#F5F1DC`), decorative brand blocks (yellow/magenta rounded squares at corners)
  - Centered brand header: black square logo (48×48, rounded, white Stethoscope icon) with hard shadow, title "Airway MD", subtitle "Clinical Assessment — Multimodal Airway Prediction"
  - White card (border + hard shadow) with:
    - "Welcome Back" heading + "Sign in to access the assessment dashboard"
    - Username field
    - Password field with show/hide toggle (Eye/EyeOff icons)
    - Inline error banner (red bg, AlertCircle icon)
    - Full-width "Sign In" button (brand-yellow, black border, hard shadow, pressed → translate + shrink shadow)
- **Behavior:**
  - Client-side validation: username required, password required
  - On submit: `POST /api/auth/login` → store `access_token` in **SecureStore**, `user` object in SecureStore/AsyncStorage → replace to MainTabs
  - Error: 401 → "Invalid credentials"; network fail → friendly message
  - Loading state: spinner + "Signing In..."
- **Security:** never store password; no autofill issues; enable `textContentType="username"` / `"password"` for OS password manager support.

### 7.3 Dashboard / Home Tab (web: `/dashboard`)

- **Purpose:** Overview + primary entry to assessment.
- **Layout (top → bottom):**
  1. **Header:** brand logo + "Airway Assessment" + `{role} · {username}` caption (capitalized role); right side: theme toggle (Sun/Moon), LLM status dot (connected/offline)
  2. **Stats row** (`StatsCard` port): Easy / Moderate / Difficult counts + "Total assessments" — horizontal compact cards
  3. **Primary CTA card:** "New Assessment" button → pushes Assessment wizard
  4. **Recent Records** (`MiniHistory` port): last 5 predictions, tap → ReportDetail, "View all" → History tab
- **Data:** `GET /api/predictions` on focus (pull-to-refresh).
- **LLM status:** `GET /api/llm/status` → show connected/offline indicator (same as web `llmStatus`).
- **States:** loading skeleton rows; empty state ("No records yet — Assess a patient to see results here"); error banner.

### 7.4 Assessment Wizard (web: `PatientForm`)

**This is the largest port.** Ports `PatientForm.tsx` (546 lines) into a 3–4 step wizard.

- **Steps:**
  1. **Demographics:** Patient ID (text), Age (number), Gender (Male/Female select)
  2. **Airway:** Mallampati Score (I–IV select), TMD (cm number), Mouth Opening (mm number)
  3. **Physical:** Neck Circumference (cm), SMD (cm), Neck Movement (°), "More findings" toggle → Beard, Chest Size, Neck Structure, Jaw Movement, Tissue Flexibility
  4. **History:** 12 Yes/No toggles (previous airway records, arthritis, diabetes, down syndrome, snoring, sleep apnea, voice changes, difficulty swallowing, can't lie flat, swelling, previous neck fracture, previous emergencies/ICU)
- **Step indicator:** segmented control / progress bar at top (web uses a 4-tab pill: `bg-neutral-100 border-2 border-black rounded-[5px]`, active tab `bg-white text-brand-700`).
- **Validation:** reproduce Section 2.4 ranges exactly. Inline field errors (small red text under field). On step advance, validate current step only. Final "Assess Patient" validates all.
- **Test-data helpers (web parity):** small buttons `E` (easy fixture), `M` (moderate), `D` (difficult), and `Random` (shuffle) that prefill the form — port `generateRandomData()` and the 3 fixture fillers verbatim (`PatientForm.tsx:144-188, 204-223`). Extremely useful for demo/testing.
- **Submit flow (web parity, `dashboard/page.tsx:85-117`):**
  1. Set `predicting=true`, show loading
  2. Fire `checkLlmStatus()` in parallel (non-blocking)
  3. **Create patient first:** `POST /api/patients` with patient_id, age, gender, bmi, mallampati (string!), tmd, neck_circumference
     - ⚠️ Note: web sends `mallampati: String(mallampati_score)` for the Patient create but `mallampati_score: number` for prediction — reproduce both exactly
     - If patient already exists (409), the web tolerates it? No — web does `await createPatient(...)` before prediction; if it throws 409 the whole flow errors. **Mobile improvement:** catch 409 and continue (documented deviation, safer UX) — flag for product decision.
  4. `POST /api/predictions` with full `PredictionInput` + `AbortController` (timeout 35 s)
  5. Show **"slow LLM" warning** if >5 s (`setTimeout` 5 s → `predictingSlow=true` — port `AiClinicalAssessment` slow banner)
  6. On success → navigate to **PredictionResult**
  7. On abort (>35 s) → error: "Time limit exceeded. There has been an error with the LLM response. Please wait for a while and try again."
- **Double-submit guard:** disable submit while loading.

### 7.5 PredictionResult Screen (web: `RiskPredictionCard` + `AiClinicalAssessment`)

- **Purpose:** Show the 3-class prediction, risk gauge, probabilities, and AI narrative.
- **Layout:**
  1. **RiskPredictionCard port:**
     - 270° **radial gauge** via `react-native-svg` (circle arc, track `neutral-100`, progress arc in semantic color; rotate 135°; sweep animation ~1 s with cubic-bezier; center readout: big number `score.toFixed(0)` + "% Risk")
     - Header: "Airway Risk Score" / "Predicted intubation difficulty" + `{score}/100` mono text
     - Prediction badge: bordered pill with "Easy Airway" / "Moderate Airway" / "Difficult Airway" in semantic colors
     - Confidence: label + mono % + horizontal progress bar
     - Probability distribution: segmented stacked bar (Easy teal / Moderate amber / Difficult red) + legend with per-class % in mono
  2. **AiClinicalAssessment port:**
     - Header: "AI Clinical Assessment" + urgency badge (Low/Moderate/High, colored)
     - Fallback warning banner (if `report_sources.* === 'fallback'`): "AI assistant unavailable — showing standard guidance."
     - **Assessment** section (brand-tinted card): bulleted summary (parse `- ` prefixed lines)
     - **Recommendations** section (green-tinted card): bulleted recommendations
     - **Risk Factors banner** (amber): text depends on prediction class (Difficult/Moderate/Easy canned strings)
     - Loading skeleton state (3–4 shimmer rows) while awaiting LLM
- **Colors:** Easy=success(teal), Moderate=warning(amber), Difficult=danger(red) throughout.
- **Data:** from `POST /api/predictions` response (kept in local state / context). Also refresh recent records after success.

### 7.6 History Tab (web: `/history` + `PatientHistory`)

- **Purpose:** Searchable, filterable prediction history with export + delete.
- **Layout:**
  - Header: "Patient Records" + count; **Export CSV** button (doctor+; disabled when empty; shows "Exporting..." spinner; success → share sheet via `expo-sharing` or download)
  - **Filter tabs** (segmented): All / Easy / Moderate / Difficult with counts (tabs disabled at 0 count unless "All")
  - **Search bar** (patient ID substring, case-insensitive)
  - **Record list** (cards instead of table):
    - Row: Patient ID (semibold), result badge (colored pill w/ dot), date (`MMM dd, yyyy HH:mm`), confidence `X.X%`
    - Actions: View (Eye icon → ReportDetail), Delete (Trash2 icon, admin-only → native Alert confirm "Delete record for {id}? This cannot be undone.")
  - Empty states: "No assessment history yet" / "No records match your search"
- **Data:** `GET /api/predictions`; client-side filter + search (matches web `PatientHistory.tsx:42-52`).
- **Delete:** `DELETE /api/predictions/{id}` then remove locally + refetch.
- **Export:** `GET /api/predictions/export/csv` → receive blob → save to device via `expo-file-system` + `expo-sharing` (or `react-native-blob-util`). Filename: `airway_predictions_YYYY-MM-DD.csv`.

### 7.7 Reports Tab (web: `/reports`)

- **Purpose:** Browse full LLM clinical reports.
- **Layout:**
  - Header: "Clinical Reports" + role/user caption
  - **List of reports** (prediction cards): colored icon (per class), patient ID, prediction badge, date, confidence
  - Tap → **ReportDetail** screen showing:
    - Probabilities: 3 stacked stat chips (Easy/Moderate/Difficult %)
    - "Clinical Summary" section (brand card, bulleted)
    - "Recommendations" section (green card, bulleted)
    - Source badges (`llm` vs `fallback`) shown as in web
- **Data:** `GET /api/predictions` then lazy `GET /api/predictions/{id}/report` on open (web fetches per-expansion, caches in `reports` map — replicate with a cache).
- **Empty state:** "No reports yet — Run an assessment to generate a clinical report".

### 7.8 Settings Tab (web: `/settings`)

- **Sections:**
  1. **Profile:** Username (read-only), Role (read-only, capitalized)
  2. **Appearance:** Dark Mode toggle (native Switch styled to match web toggle: black-bordered square knob)
  3. **API Connection (new for mobile):** API URL field (editable, stored AsyncStorage), **Test Connection** button (calls `/health` → shows Connected/Failed)
  4. **System:** MongoDB status, LLM Model (from `/api/llm/status`), ML Model (`TabTransformer (tabular_best.pt)` — hardcode like web or read from config)
- **Data:** `GET /api/llm/status` for LLM line.

### 7.9 About Screen (web: `/about`)

- **Sections (port verbatim):**
  1. **ML Models:** 3 cards (TabTransformer / XGBoost / Random Forest) with accuracy, AUC-ROC, features, file name — static data, no API
  2. **LLM Assistant:** provider, model, temperature, max tokens, purpose — static
  3. **System Architecture:** stacked layer rows (Frontend/Backend/ML Engine/LLM Service/Database) with icons — static
- **Note:** About text says "OpenRouter API + Qwen 2.5 72B" and "MongoDB Atlas (cloud)" — keep in sync with actual deployment config; if switching to Ollama locally, update text.

### 7.10 (Optional) User Management — admin only

- Backend has `POST /api/auth/register` (no auth decorator). For v1 mobile, either:
  - Hide it entirely (web doesn't surface it in UI), or
  - Add an admin-gated "Register User" screen in Settings (role: admin/doctor/viewer).
- **Recommendation:** v1 = hidden (matches web parity).

---

## 8. Authentication & Secure Token Storage

### 8.1 Token Lifecycle (port of `src/lib/api.ts`)

| Web (localStorage) | Mobile (SecureStore) |
|--------------------|----------------------|
| `getToken()` / `setToken()` / `clearToken()` | `getToken()` / `setToken()` using `expo-secure-store` |
| `getUser()` / `setUser()` (JSON in localStorage) | Same shape in SecureStore (or AsyncStorage — not sensitive) |
| `localStorage.setItem('theme', ...)` | AsyncStorage `theme` |

- **JWT expiry:** 480 minutes (8 h, backend `jwt_expire_minutes`). On any 401 from API:
  1. Clear token + user
  2. Navigate to Login
  3. Show "Session expired. Please sign in again."
- **`GET /api/auth/me`** used on app start to validate restored token.
- **No refresh-token flow exists** in the backend — do not design one; re-login is the mechanism.

### 8.2 Additional Security

- Biometric unlock (optional): see Section 15
- Auto-logout timer (optional, clinical app nicety): clear token after inactivity
- Do NOT store the JWT in AsyncStorage (plaintext, unencrypted) — SecureStore only
- Disable screenshots? (clinical app option; use `expo-screen-capture` if required by policy — **default off**, decision needed)

---

## 9. API Client Design

### 9.1 `src/lib/api.ts` Port — File-by-File

Create mobile `src/lib/api.ts` with identical exported functions:

```ts
export async function login(username, password): Promise<AuthResponse>
export function logout(): void
export async function getPatients(): Promise<Patient[]>
export async function createPatient(data: Partial<Patient>): Promise<Patient>
export async function getPatient(id): Promise<Patient>
export async function runPrediction(data: PredictionInput, signal?: AbortSignal): Promise<PredictionResponse>
export async function checkLlmStatus(): Promise<LlmStatus>
export async function getPredictions(patientId?): Promise<PredictionHistory[]>
export async function getPredictionReport(predictionId): Promise<LLMReport>
export async function deletePrediction(predictionId): Promise<void>
export async function exportCsv(): Promise<Blob>   // ← adapt: returns file path / base64
export { getToken, setToken, clearToken, getUser, setUser, BASE_URL }
```

### 9.2 `apiFetch` Port — Required Adaptations

Web (`api.ts:42-82`) does:
```ts
async function apiFetch<T>(endpoint, options) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const response = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers });
  if (!response.ok) { /* parse error.detail | error.message → throw Error */ }
  if (contentType includes json) return response.json();
  return response.text();
}
```

**Mobile adaptations:**
1. `getToken()` reads from SecureStore (async!) → `apiFetch` becomes `async` (already is) — fine
2. **401 handling:** add centralized interceptor → if `response.status === 401`, `clearToken()` + emit auth-expired event (React Context/listener) → router to Login
3. **Network error handling:** catch `TypeError: Network request failed` / offline → throw friendly `"Cannot reach server. Check your connection or API URL."`
4. **CSV export:** `exportCsv()` must return a **file path** (write blob via `expo-file-system` to cache dir) then share via `expo-sharing`
5. **Timeout:** pass `AbortController` from callers (runPrediction flow)
6. Base URL: resolve from AsyncStorage override → `EXPO_PUBLIC_API_URL` env → default

### 9.3 Base URL Resolution (ordered)

```ts
// 1) runtime override (Settings screen) → AsyncStorage 'apiBaseUrl'
// 2) EXPO_PUBLIC_API_URL env (build time)
// 3) default: http://<LAN-IP>:8000  (dev) — see app.json extra
```

---

## 10. Data Models

> **Port `src/types/index.ts` verbatim** to `mobile/src/types/index.ts`. Full contents (from repo):

```ts
export interface User { username: string; role: string; }
export interface AuthResponse { access_token: string; token_type: string; user: User; }
export interface Patient {
  patient_id: string; age: number; gender: string; bmi: number;
  mallampati: string; tmd: number; neck_circumference: number;
  comorbidities?: Record<string, string>; created_at: string;
}
export interface PredictionInput { /* all 30 fields — see Section 2.5 */ }
export interface PredictionResult {
  prediction: string; confidence: number; risk_score: number;
  probabilities: Record<string, number>;
}
export interface PredictionResponse {
  prediction: PredictionResult;
  clinical_summary: string;
  recommendations: string;
  report_sources?: { summary?: string; recommendations?: string };
}
export interface PredictionHistory {
  id: string; patient_id: string; prediction: string; confidence: number;
  risk_score: number; probabilities: Record<string, number>; created_at: string;
}
export interface LLMReport {
  prediction_id: string; summary: string; recommendations: string;
  summary_source?: string; recommendations_source?: string; created_at: string;
}
export interface LlmStatus { connected: boolean; model: string; latency_ms: number | null; }
```

**Additions specific to mobile:**
```ts
export interface PredictionStep { title: string; subtitle?: string; }  // wizard step meta
export type ThemePreference = 'light' | 'dark' | 'system';
```

---

## 11. State Management

| Concern | Approach |
|---------|----------|
| Auth (token, user) | **React Context + SecureStore**. Provider at root. Exposes `{user, token, signIn, signOut, isLoading}` |
| API base URL | Context or simple module-level getter + AsyncStorage (read on boot) |
| Theme (light/dark/system) | Context + AsyncStorage; applied via `expo-system-ui` / ThemeProvider wrapper |
| Dashboard data (stats, recent) | Local state in screen + pull-to-refresh; refetch on focus (e.g., `useFocusEffect` from React Navigation) |
| Reports cache (`{predId: LLMReport}`) | `useState` map in Reports screen (web parity) |
| Wizard form data | Local `useState` in Assessment screen; pass `initialData` for edit (web parity) |

**Zustand optional:** only introduce if cross-screen shared state grows (e.g., "last submitted patient"). Default: Context + local state — matches web app's actual approach.

---

## 12. Design System & Theming

### 12.1 Color Tokens (port of `tailwind.config.js` → theme file)

| Token | Light Value | Dark Value | Usage |
|-------|-------------|------------|-------|
| `bg.page` | `#F5F1DC` (paper) | `#121212` | App background |
| `ink` | `#111111` | `#111111` | Text primary / borders |
| `brand.500` | `#FFD900` | `#FFD900` | Primary button, active tab |
| `brand.100` | `#FFF3C2` | — | Brand tinted card bg |
| `success` | `#16C2C8` (teal) | same | Easy class |
| `warning` | `#EAB308` (amber) | same | Moderate class |
| `danger` | `#FF5A5F` (red) | same | Difficult class |
| `neutral` | zinc scale (50→950) | same | Text, borders, surfaces |
| Card bg | `#FFFFFF` | `neutral.900` `#18181B` | Cards, headers |
| Card border | `neutral.200` | `neutral.700` | Card outlines |

### 12.2 Shadow / Border Tokens (the signature look)

```
shadow-soft  : 4px 4px 0 #111
shadow-card  : 5px 5px 0 #111
shadow-elev  : 6px 6px 0 #111
press-state  : translate(2px,2px) + shadow 2px 2px 0  (pressed)
active-press : translate(4px,4px) + no shadow
border       : 2px solid #111   (light) / 2px solid neutral.600 (dark)
radius       : 4-8px (small, sharp edges)
```

### 12.3 Typography

| Style | Font | Spec |
|-------|------|------|
| Display / big numbers | Inter, 800 | gauge score `text-6xl` |
| Headings | Inter, 600–700 | `text-base/lg` |
| Body | Inter, 400–500 | `text-sm` |
| Mono (numbers, ids, system info) | **JetBrains Mono** | `tabular-nums` |
| Micro-labels | Inter, 600, uppercase | `text-[10px] tracking-[0.15em]` |

Load both fonts via `expo-font` + `@expo-google-fonts/inter`, `@expo-google-fonts/jetbrains-mono`.

### 12.4 Animations (port from tailwind keyframes)

| Animation | Keyframes | Use |
|-----------|-----------|-----|
| `fade-in` | opacity 0→1, 0.5 s | cards, results |
| `scale-in` | scale 0.95→1 + fade, 0.3 s | result card mount |
| `gauge-pulse` | scale 0.97→1.01→1 + opacity, 1.6 s | gauge mount |
| `slide-up` | translateY(10)→0 + fade, 0.5 s | bottom sheets, results |

### 12.5 Dark Mode

- Toggle in Settings (web: `settings/page.tsx`), also header quick-toggle on Dashboard (web does)
- Persist in AsyncStorage; default = **system** preference (web uses `matchMedia prefers-color-scheme`)
- Apply via React Native `Appearance` + `useColorScheme`-driven theme provider
- All components must support `dark` variants per token table above

### 12.6 Reusable Component Checklist (mobile equivalents)

| Web Component | Mobile Implementation |
|---------------|----------------------|
| Buttons (primary/secondary/danger) | `AppButton` — black border 2px, hard shadow, brand/neutral bg, press translate |
| Card | `Card` — white/dark900 bg, border, `shadow-card` |
| Select dropdown | RN `Picker` or custom bottom-sheet select (styled as bordered square) |
| Yes/No | Custom toggle segmented (No/Yes) or Switch — keep web's two-option select look |
| Text input | `AppInput` — bordered, hard shadow, focus ring brand, error state red border |
| Badge/Pill | `Badge` — colored bg + colored text, 2px border (success/warning/danger/neutral) |
| Segmented control | `SegmentedTabs` — neutral bg pill, active = white/dark900 w/ shadow |
| Skeleton | Shimmer block component (match `skeleton` classes) |
| Empty state | Icon + title + subtitle centered block |
| Banner (error/warning/info) | `Banner` — tinted bg + 2px border + icon |

---

## 13. Offline & Connectivity Handling

| Scenario | Behavior |
|----------|----------|
| No network at login | Show error: "Cannot reach server. Check your connection." + retry |
| No network mid-prediction | Abort controller fires → error banner; keep form data (draft) so user can retry |
| No network viewing history | Show cached list (AsyncStorage cache of last `GET /api/predictions`) + "Offline — showing cached data" banner; pull-to-refresh disabled |
| LLM offline (but API up) | `/api/llm/status` → false → show offline dot; prediction still works; report shows `fallback` source banner (server handles fallback) |
| Slow network | Use the 5 s "slow LLM" banner; show full-screen blocking spinner during prediction (web does) |

**Offline cache scope (v1):** predictions list + reports (read-only cache). **Not cached:** submitting predictions, mutations.

---

## 14. Push Notifications (Optional)

- **Not required for feature parity** — the web app has none. Listed for completeness / future:
  - `expo-notifications` for: prediction complete, daily summary, admin alerts
  - Requires push token registration endpoint (backend addition) — **out of scope v1**

---

## 15. Biometric Authentication (Optional)

- `expo-local-authentication` — device Face ID / fingerprint
- Flow: app lock screen on launch (if enabled in Settings) → biometric prompt → then session restore (existing JWT)
- Keep JWT in SecureStore; biometric is only a gate, not a token replacement
- **Default: OFF in v1** (decision needed; clinical apps often require it)

---

## 16. Accessibility Requirements

- Minimum tap target 44×44 pt (web uses 36–40px — bump for mobile)
- Color contrast ≥ 4.5:1 for text (check yellow `#FFD900` on black = OK for large/bold only; use `#9E8500`/`brand.800` for small text on light bg)
- Semantic labels on all icon buttons (`accessibilityLabel`, `accessibilityRole`)
- Dynamic type / font scaling support (React Native default) — verify layouts don't clip
- `reduce motion` support → disable gauge sweep & animations (`AccessibilityInfo.isReduceMotionEnabled`)
- Form fields: proper `label` association, error text linked via `accessibilityHint`
- Not just color for status: Easy/Moderate/Difficult badges have text, not color alone (already true)

---

## 17. Performance Requirements

| Metric | Target |
|--------|--------|
| Cold start → Login/Dashboard | < 3 s (dev build), < 2 s (release, no network wait) |
| Tab switch | < 100 ms perceived (render from cache, lazy-fetch) |
| Assessment → Result (server normal) | < 10 s typical (server-bound; LLM latency dominates) |
| History list scroll | 60 fps |
| Gauge animation | 60 fps (SVG arcs are cheap) |
| Memory | No unbounded caches; reports cache capped at ~100 entries |
| Network | Debounce search input (300 ms); paginate list fetches (skip/limit from API) |

---

## 18. Security & Clinical Compliance

- **JWT only in SecureStore** (Keychain/Keystore, encrypted)
- HTTPS required for production API (see Section 5.2)
- **No PHI in logs** — never log patient data or full prediction payloads
- App-level lock (optional biometrics, Section 15)
- Pin the API certificate in production builds (optional hardening)
- Clear sensitive data on logout (token, user, caches)
- Screenshot capture policy (decision, Section 25)
- Follow HIPAA/GDPR hygiene: this is clinical decision support — add **disclaimer screen/notice** ("not a substitute for clinical judgment") consistent with web's risk banner language
- Data retention: delete predictions cascades server-side already (admin)

---

## 19. Proposed Project Structure

```
D:\Minor_Project\
├── mobile/                        ← NEW React Native (Expo) app
│   ├── app.json                  # Expo config (splash, icons, plugins, extra.apiBaseUrl)
│   ├── package.json
│   ├── tsconfig.json             # path alias @/ → src/
│   ├── App.tsx                   # Root: ThemeProvider + AuthProvider + Navigation
│   ├── src/
│   │   ├── navigation/
│   │   │   ├── RootNavigator.tsx  # AuthGate → MainTabs
│   │   │   ├── MainTabs.tsx       # 4 bottom tabs
│   │   │   ├── HomeStack.tsx
│   │   │   ├── HistoryStack.tsx
│   │   │   ├── ReportsStack.tsx
│   │   │   └── SettingsStack.tsx
│   │   ├── screens/
│   │   │   ├── auth/LoginScreen.tsx
│   │   │   ├── home/DashboardScreen.tsx
│   │   │   ├── home/AssessmentScreen.tsx      # wizard
│   │   │   ├── home/PredictionResultScreen.tsx
│   │   │   ├── history/HistoryScreen.tsx
│   │   │   ├── reports/ReportsScreen.tsx
│   │   │   ├── reports/ReportDetailScreen.tsx
│   │   │   ├── settings/SettingsScreen.tsx
│   │   │   └── settings/AboutScreen.tsx
│   │   ├── components/           # AppButton, Card, Badge, AppInput, SegmentedTabs,
│   │   │   │                     # Banner, Skeleton, EmptyState, Gauge, ConfidenceBar,
│   │   │   │                     # ProbabilityBar, AiAssessmentCard, MiniHistoryList, ...
│   │   ├── lib/
│   │   │   ├── api.ts            # port of src/lib/api.ts (SecureStore, 401 handling)
│   │   │   ├── storage.ts        # SecureStore + AsyncStorage wrappers
│   │   │   └── constants.ts      # validation ranges, class colors, fixtures
│   │   ├── types/
│   │   │   └── index.ts          # verbatim port
│   │   ├── theme/
│   │   │   ├── tokens.ts         # colors, shadows, radii, spacing
│   │   │   ├── fonts.ts
│   │   │   └── ThemeProvider.tsx
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── usePredictions.ts
│   │   │   └── useTheme.ts
│   │   └── utils/
│   │       ├── formValidation.ts # Section 2.4 ranges
│   │       ├── randomData.ts     # port generateRandomData + E/M/D fixtures
│   │       └── parseBullets.ts   # "- " bullet parser (AiClinicalAssessment)
│   └── assets/                   # splash, icon, fonts
└── (backend/ unchanged)
```

---

## 20. Dependencies List

### Core (required)

```
expo (SDK 52+)
react-native
expo-router OR @react-navigation/native + @react-navigation/bottom-tabs + @react-navigation/native-stack
expo-secure-store
expo-font + @expo-google-fonts/inter + @expo-google-fonts/jetbrains-mono
@react-native-async-storage/async-storage
react-native-svg
lucide-react-native
date-fns
react-native-safe-area-context
react-native-screens
```

### Optional

```
zustand                       (if shared state grows)
react-native-toast-message    (toasts)
expo-sharing + expo-file-system  (CSV export share sheet)
expo-local-authentication     (biometric gate)
expo-notifications            (future push)
react-hook-form + zod         (alternative form handling — default: manual state like web)
expo-screen-capture           (if screenshot blocking required)
expo-network / @react-native-community/netinfo  (connectivity banner)
```

---

## 21. Testing Strategy

### 21.1 Unit Tests
- **Validation logic** (`formValidation.ts`) — boundary tests for every range (Section 2.4): 0/1/119/120 age, 9.9/10/60/60.1 BMI, 1/4 Mallampati, 2.9/3/12/12.1 TMD, etc.
- **`parseBullets`** — bullet parsing incl. edge cases (empty, no prefix)
- **`randomData` / fixtures** — produced payload is valid against ranges
- **API client** — mocked fetch: success, 401 (session expiry), 409 (duplicate patient), network error, abort
- **`risk_score` / class → color** mapping helpers
- **date formatting** (`date-fns` wrappers)

### 21.2 Integration / E2E
- **Jest + React Native Testing Library** for component tests (gauge renders, form validation UX)
- **Detox** (E2E) or **Maestro**: login → create assessment → prediction → history → delete happy path
- **Manual device matrix:** Android (Pixel/OnePlus, API 28–35), iOS (iPhone SE/14+, iOS 16–18), tablet

### 21.3 Backend Contract Tests
- Run real backend (uvicorn) + a scripted mobile-API client to verify all endpoints in Section 2.3 return expected shapes (guard against backend drift)
- Verify 35 s slow-LLM behavior & fallback sources

---

## 22. Build, Release & Distribution

| Item | Detail |
|------|--------|
| Dev loop | `npx expo start` + Expo Go OR `npx expo run:android` / `run:ios` (dev builds) |
| Internal testing | **EAS Build** (`eas build --profile preview`) → installable APK/IPA |
| Production | `eas build --profile production` → App Store (iOS) + Play Store (Android) |
| App identity | Name: **Airway MD**; icons/splash from existing brand (Stethoscope, black/yellow) |
| Versioning | Match backend `app_version: 2.0.0` semantics; store code `1.0.0` |
| Signing | EAS manages keystores; iOS needs Apple Developer account; Android needs Google Play account |
| CI | Add `mobile/` job to `.github/workflows/deploy.yml` (optional: EAS GitHub Action) |
| OTA updates | expo-updates for JS-only patches (optional) |
| Backend hosting | Reuse existing `render.yaml` / Docker deployment; **expose HTTPS** for production app |

**Tablet adaptation:** v1 = phone-first responsive (max content width ~700px, centered). Tablet-specific layout (multi-pane dashboard like web) = v2.

---

## 23. Implementation Phases (Ordered)

> Estimates assume one engineer, experienced with RN/Expo.

| Phase | Deliverables | Est. Effort |
|-------|--------------|-------------|
| **P0 — Scaffolding** | `mobile/` Expo app init, app.json, theme tokens, fonts, navigation shell (4 tabs + auth gate), SecureStore wrapper, base URL resolution | 0.5–1 day |
| **P1 — Auth** | Login screen (full port), token lifecycle, `/me` validation, session expiry handling | 1 day |
| **P2 — API client + types** | Port `types/index.ts`, `api.ts` (401 interceptor, error normalization, CSV file export), validation module + tests | 1–1.5 days |
| **P3 — Assessment wizard** | 4-step form, validation, test fixtures (E/M/D/Random), submit flow (create patient + predict + AbortController 35 s + slow banner) | 2–3 days |
| **P4 — Result screens** | RiskPredictionCard port (SVG gauge, confidence, probability bars), AiClinicalAssessment port (skeletons, bullets, urgency, fallback banner) | 2 days |
| **P5 — History tab** | List + search + filter tabs + delete confirm + CSV export/share + empty states | 1.5–2 days |
| **P6 — Reports tab** | List + lazy report fetch/cache + ReportDetail | 1 day |
| **P7 — Settings + About** | Profile, dark mode toggle + system theme, API URL editor + connection test, system status, About port | 1 day |
| **P8 — Dashboard polish** | Stats cards, recent records, LLM status dot, pull-to-refresh, empty/error states | 1 day |
| **P9 — QA hardening** | Accessibility pass, dark-mode audit, offline banners, performance pass, unit tests complete | 1.5–2 days |
| **P10 — Release** | EAS preview build → device testing → production build → store submission | 1–2 days |

**Total: ~13–17 engineer-days** for feature parity. Add buffer for review/fixes.

### Critical Path & Parallelization
- P0 → P1 → P2 are sequential (foundation).
- P3–P8 can be split into 2 parallel tracks after P2: (A) Assessment+Result, (B) History+Reports+Settings+About.
- P9–P10 sequential.

---

## 24. Risks & Mitigations

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| 1 | Slow LLM (5–40 s) makes prediction feel broken | UX | 5 s "slow" banner + 35 s abort + fallback-source banner + clear spinner; consider backend async job later |
| 2 | `POST /api/predictions` does NOT scale inputs (known backend gotcha — predictions router passes raw values; callers must normalize upstream) | Wrong predictions | **Out of mobile scope** (backend bug), but verify against web: web sends same raw values → mobile matches web behavior. Document; do not "fix" silently |
| 3 | API base URL confusion on devices | Connection failures | Settings → API URL editor + Test Connection + clear error guidance |
| 4 | Android cleartext HTTP blocked | Dev fails on device | Dev builds enable cleartext; production HTTPS only (Section 5.2) |
| 5 | JWT expiry mid-session (8 h) | Random logouts | 401 interceptor → graceful "Session expired" → login |
| 6 | Form parity drift (30 fields) | Wrong payloads | Single `PredictionInput` builder + contract test against real backend |
| 7 | Neo-brutalist look lost in native | Brand dilution | Token-driven components only (Section 12); visual QA against web screenshots |
| 8 | Duplicate patient on predict (web does createPatient then predict; 409 breaks flow) | Failed predictions | Catch 409 and continue to prediction (flag for decision) |
| 9 | SecureStore size limits (~2KB/item on Android, 2KB on iOS) | Can't store big values | JWT + user are small — fine. Never store lists in SecureStore (use AsyncStorage) |
| 10 | Multi-window / background kill loses form draft | Lost work | Persist wizard draft to AsyncStorage, restore on relaunch (nice-to-have) |

---

## 25. Decisions Needed Before Build Starts

Confirm these before writing the implementation plan:

1. **Framework:** React Native + Expo (recommended) vs Flutter? — *Default: Expo*
2. **Navigation lib:** expo-router vs React Navigation? — *Default: React Navigation v7 (more mature for custom tabs)*
3. **Duplicate-patient on predict:** catch 409 and continue (recommended) vs strict web parity? — *Default: continue*
4. **API URL config in-app:** allow runtime editing in Settings? — *Default: yes (dev convenience)*
5. **Biometric app lock:** include in v1? — *Default: no*
6. **Screenshot blocking:** required by clinical policy? — *Default: no*
7. **Platforms v1:** Android only, iOS only, or both? — *Default: both (Expo makes it cheap)*
8. **Register-user screen:** include (admin-gated) or match web (absent)? — *Default: absent in v1*
9. **Offline caching scope:** read-only cache of history/reports OK? — *Default: yes*
10. **Test fixtures (E/M/D/Random buttons):** keep in production build or dev-only? — *Default: keep (web has them in prod)*
11. **Tablet support:** phone-first v1, tablet v2? — *Default: yes*

## 26 Finishing 
Add this paragraph to the MD document, preferably near the end of **Section 3 (Conversion Goals & Scope Decisions)**:

 ** Development Scope:** This mobile application is currently being developed as a student/research project and is **not intended for production deployment or clinical use at this stage**. The implementation priority is functional parity with the existing web application and learning-focused mobile development rather than production-grade regulatory compliance or deployment hardening. React Native + Expo with React Navigation v7 will be used, the existing FastAPI backend and API contracts will remain unchanged, and duplicate-patient `409` responses will be handled by continuing with the prediction request. API URL editing may be available in development builds to simplify local testing. Biometrics, screenshot blocking, push notifications, certificate pinning, advanced offline synchronization, CI/CD, OTA updates, and production app-store configuration are out of scope for the current development phase. The `E/M/D/Random` test-data fixtures should be available in development/debug builds for testing but hidden from production builds. The prediction API contains a 30-field payload, but the mobile UI should **not** create 30 separate input fields; it should collect the same core and advanced fields as the existing web application while derived/default fields are generated as specified. The application will follow the implementation phases defined in this document, beginning with P0 scaffolding, followed by authentication, API integration, assessment, prediction results, history, reports, settings, dashboard refinement, QA, and finally optional release preparation.  



---

*End of specification. Derive the implementation plan from Sections 6–23; keep Section 2.3, 2.4, 2.5, and 2.6 as frozen API contracts.*