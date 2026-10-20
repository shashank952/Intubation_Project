# Airway MD — Mobile Application Implementation Plan

> **Source of truth:** `mobile_application.md` (the specification document). This file is the **step-by-step implementation guide** derived from it.
>
> **Goal:** Build a React Native (Expo) mobile app in `D:\Minor_Project\mobile\` that is a 1:1 functional port of the Airway MD web dashboard, connecting to the **existing, unchanged FastAPI backend**.
>
> **Review note:** This document is for review BEFORE any code is written. After your approval, implementation follows these steps in order.

---

## Table of Contents

1. [Pre-requisites & Environment Setup](#1-pre-requisites--environment-setup)
2. [Phase 0 — Scaffold the Expo App](#2-phase-0--scaffold-the-expo-app)
3. [Phase 1 — Design System & Theme](#3-phase-1--design-system--theme)
4. [Phase 2 — Navigation Shell & Auth Gate](#4-phase-2--navigation-shell--auth-gate)
5. [Phase 3 — API Client & Data Layer](#5-phase-3--api-client--data-layer)
6. [Phase 4 — Login Screen](#6-phase-4--login-screen)
7. [Phase 5 — Dashboard (Home Tab)](#7-phase-5--dashboard-home-tab)
8. [Phase 6 — Assessment Wizard](#8-phase-6--assessment-wizard)
9. [Phase 7 — Prediction Result Screen](#9-phase-7--prediction-result-screen)
10. [Phase 8 — History Tab](#10-phase-8--history-tab)
11. [Phase 9 — Reports Tab](#11-phase-9--reports-tab)
12. [Phase 10 — Settings & About](#12-phase-10--settings--about)
13. [Phase 11 — Testing & QA](#13-phase-11--testing--qa)
14. [Phase 12 — Build & Release](#14-phase-12--build--release)
15. [Checklist Summary](#15-checklist-summary)

---

## 1. Pre-requisites & Environment Setup

### 1.1 Required Tools (install if missing)

| Tool | Purpose | Check |
|------|---------|-------|
| Node.js **18+ / 20 LTS** | Runs Expo & build tooling | `node --version` |
| npm | Package manager | `npm --version` |
| Git | Version control (already in repo) | `git --version` |
| **Expo CLI** | Scaffold/run the app | `npx expo --version` |
| Phone with **Expo Go** app | Test on real device (Android/iOS) | From Play Store / App Store |
| Android Studio **or** iOS Simulator (optional) | Native dev builds later | — |

### 1.2 Verify the Backend Runs (needed for live testing)

```bash
# From D:\Minor_Project — start the backend
uvicorn backend.deploy.api:app --host 0.0.0.0 --port 8000
```

- Confirm `http://localhost:8000/health` returns `{"status":"ok","version":"2.0.0"}`.
- Note your **PC's LAN IP** (e.g. `192.168.1.50`) — the phone will connect to `http://<LAN-IP>:8000`.
  ```powershell
  ipconfig   # look for "IPv4 Address" under your active adapter
  ```
- **Firewall:** allow inbound TCP port 8000 for the Python/uvicorn process (Windows Firewall prompt).

### 1.3 Create the Working Directory

- New folder: `D:\Minor_Project\mobile\`
- Add `mobile/` to `.gitignore` decision later (only `node_modules`, `.expo` — keep source tracked).

---

## 2. Phase 0 — Scaffold the Expo App

### Step 0.1 Create the app

```bash
cd D:\Minor_Project
npx create-expo-app@latest mobile --template blank-typescript
cd mobile
```

- Template: **blank-typescript** (we build our own navigation; do NOT use the default tabs template — it adds cruft we don't need).

### Step 0.2 Install core dependencies

```bash
npx expo install expo-secure-store expo-font expo-file-system expo-sharing \
  react-native-svg react-native-safe-area-context react-native-screens \
  @react-native-async-storage/async-storage expo-system-ui

npm install @react-navigation/native @react-navigation/bottom-tabs \
  @react-navigation/native-stack date-fns lucide-react-native

npm install @expo-google-fonts/inter @expo-google-fonts/jetbrains-mono
```

### Step 0.3 Configure `app.json`

```jsonc
{
  "expo": {
    "name": "Airway MD",
    "slug": "airway-md-mobile",
    "version": "1.0.0",
    "orientation": "portrait",
    "userInterfaceStyle": "automatic",
    "splash": { "backgroundColor": "#111111" },
    "extra": {
      "apiBaseUrl": "http://192.168.1.50:8000"   // <- replace with your LAN IP
    },
    "plugins": ["expo-secure-store"]
  }
}
```

### Step 0.4 Set up path alias `@/`

- Edit `tsconfig.json`:
  ```jsonc
  { "extends": "expo/tsconfig.base", "compilerOptions": { "paths": { "@/*": ["./src/*"] } } }
  ```

### ✅ Verify (Step 0 done when...)
- `npx expo start` runs with **no red errors**.
- App renders a blank screen on the phone via Expo Go.
- The project folder structure exists: `mobile/src/`.

---

## 3. Phase 1 — Design System & Theme

> Ports `tailwind.config.js` (web) → token files (mobile). Everything visual uses these tokens — no hard-coded colors anywhere.

### Step 1.1 Create `src/theme/tokens.ts`

Port these values exactly (from `D:\Minor_Project\tailwind.config.js`):

```ts
export const colors = {
  page: { light: '#F5F1DC', dark: '#121212' },
  ink: '#111111',
  card: { light: '#FFFFFF', dark: '#18181B' },
  border: { light: '#E4E4E7', dark: '#3F3F46' },   // neutral.200 / neutral.700
  brand: { 500: '#FFD900', 100: '#FFF3C2', 700: '#C4A600', 800: '#9E8500' },
  success: { 50: '#E7FBFB', 500: '#16C2C8', 700: '#0D8388' },
  warning: { 50: '#fffbeb', 500: '#EAB308', 700: '#a16207' },
  danger:  { 50: '#FFECED', 500: '#FF5A5F', 700: '#BC3338' },
  neutral: { 50:'#FAFAFA',100:'#F4F4F5',200:'#E4E4E7',300:'#D4D4D8',400:'#A1A1AA',
             500:'#71717A',600:'#52525B',700:'#3F3F46',800:'#27272A',900:'#18181B',950:'#09090B' },
};

export const shadows = {
  soft:   { offset: {x:4,y:4}, color:'#111', radius:0 },
  card:   { offset: {x:5,y:5}, color:'#111', radius:0 },
  elevated:{ offset: {x:6,y:6}, color:'#111', radius:0 },
  pressed:{ offset: {x:2,y:2}, color:'#111', radius:0 },   // button pressed state
};

export const radii = { sm: 4, md: 6, lg: 8 };
export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, '2xl': 24 };
```

### Step 1.2 Create `src/theme/fonts.ts`

- Load **Inter** (600/700/800 weights) + **JetBrains Mono** via `expo-font`.
- Font names: `Inter_600SemiBold`, `Inter_700Bold`, `Inter_800ExtraBold`, `JetBrainsMono_400Regular`.

### Step 1.3 Create `src/theme/ThemeProvider.tsx`

- Context exposing `{ theme: 'light' | 'dark', toggleTheme, setTheme }`.
- Default: `Appearance.getColorScheme()` (system); persist override in AsyncStorage key `theme`.
- Provide a `useTheme()` hook + `useColors()` hook (returns merged color object for the active theme).

### Step 1.4 Create the core UI primitives in `src/components/ui/`

| File | Component | Mirrors web |
|------|-----------|-------------|
| `AppButton.tsx` | Primary/secondary/danger button — 2px black border, hard shadow, press → translate(2,2) + shadow shrink, disabled state | `clsx(...)` button classes in `PatientForm`/`login` |
| `Card.tsx` | White/dark900 rounded surface + border + `shadow-card` | `bg-white ... shadow-card` |
| `AppInput.tsx` | Bordered input, focus ring (brand), error state (red border + message), mono option | `inputClass()` from `PatientForm` |
| `Select.tsx` | Custom picker: bordered square trigger, opens bottom-sheet list of options | `<select>` styling |
| `Badge.tsx` | Colored pill (success/warning/danger/neutral) with optional dot | `badge()` helpers |
| `SegmentedTabs.tsx` | Pill container + active white/dark900 tab w/ shadow | section tabs + filter tabs |
| `Banner.tsx` | Tinted banner + 2px border + icon (error/warning/info) | error/slow-LLM banners |
| `Skeleton.tsx` | Shimmer block (animated opacity loop) | `skeleton` classes |
| `EmptyState.tsx` | Icon + title + subtitle centered | empty states in history/reports |
| `AppHeader.tsx` | Screen header: back button (optional), title, subtitle, right slot | web headers |

### ✅ Verify (Step 1 done when...)
- A sample screen renders: page bg `#F5F1DC`, a `Card` with `5px 5px 0 #111` shadow, an `AppButton` (yellow, black border) with working press animation, in **both light and dark mode**.
- Toggling dark mode via provider re-renders everything.

---

## 4. Phase 2 — Navigation Shell & Auth Gate

### Step 2.1 Create `src/navigation/RootNavigator.tsx`

```
RootNavigator
├── if (authLoading)            → <LoadingScreen />        (spinner on #111 bg)
├── if (!token)                 → AuthStack  → Login
└── if (token)                  → MainTabs   (4 bottom tabs)
```

- On mount: read token from SecureStore → if present, call `GET /api/auth/me` to validate → valid: MainTabs; invalid: clear + Login. (Ports web `login/page.tsx:19-36`.)

### Step 2.2 Create `src/navigation/MainTabs.tsx`

- **Bottom Tab Navigator** with 4 tabs:

| Tab | Screen | Icon (lucide-react-native) | Label |
|-----|--------|---------------------------|-------|
| 1 | HomeStack | `LayoutDashboard` | Home |
| 2 | HistoryStack | `History` | Records |
| 3 | ReportsStack | `FileText` | Reports |
| 4 | SettingsStack | `Settings` | Settings |

- Styling: height ~64 + safe area; active tab = brand-yellow pill (`#FFD900`, 2px black border, `shadow-soft`), inactive = neutral text; dark-mode variants.

### Step 2.3 Create the 4 stacks

- `HomeStack.tsx`: `Dashboard` (initial) → `Assessment` → `PredictionResult` → `ReportDetail`
- `HistoryStack.tsx`: `History` (initial) → `ReportDetail`
- `ReportsStack.tsx`: `Reports` (initial) → `ReportDetail`
- `SettingsStack.tsx`: `Settings` (initial) → `About`

### Step 2.4 Auth context — `src/hooks/useAuth.ts` + `src/context/AuthContext.tsx`

- State: `{ token, user, isLoading }`
- Actions: `signIn(username, password)` (calls API, stores token+user in SecureStore), `signOut()` (clears SecureStore + caches, navigates to Login), `restoreSession()` (boot-time token validation).

### ✅ Verify (Step 2 done when...)
- No token → Login screen shows. Token in SecureStore → Dashboard tab shows.
- Sign out returns to Login; re-login returns to Dashboard.
- Tab bar visible with 4 tabs, correct active styling, dark mode works.

---

## 5. Phase 3 — API Client & Data Layer

> Direct port of web `src/lib/api.ts` + `src/types/index.ts` with mobile adaptations.

### Step 5.1 Port types — `src/types/index.ts`

- Copy the file from `D:\Minor_Project\src\types\index.ts` **verbatim** (all 10 interfaces). Do not rename fields.

### Step 5.2 Create `src/lib/storage.ts`

```ts
// SecureStore (encrypted) — token & user JSON
export async function getToken(): Promise<string | null>
export async function setToken(t: string): Promise<void>
export async function clearToken(): Promise<void>
export async function getUser(): Promise<User | null>
export async function setUser(u: User): Promise<void>

// AsyncStorage (non-sensitive)
export async function getApiBaseUrl(): Promise<string>   // Settings override
export async function setApiBaseUrl(url: string): Promise<void>
export async function getTheme(): Promise<string>
export async function setTheme(t: string): Promise<void>
```

### Step 5.3 Port API client — `src/lib/api.ts`

Same 12 exported functions as web (`login, logout, getPatients, createPatient, getPatient, runPrediction, checkLlmStatus, getPredictions, getPredictionReport, deletePrediction, exportCsv` + getters), with these **mobile adaptations**:

1. `BASE_URL` resolution (priority order):
   ```
   AsyncStorage override ('apiBaseUrl')  →  Constants.expoConfig.extra.apiBaseUrl  →  'http://<LAN-IP>:8000'
   ```
2. `apiFetch` becomes async token-aware (SecureStore read):
   ```ts
   const token = await getToken();
   if (token) headers.Authorization = `Bearer ${token}`;
   const response = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers, signal });
   ```
3. **401 interceptor:** if `response.status === 401` → `clearToken()` + notify auth context (→ navigate to Login, show "Session expired").
4. **Network error:** catch fetch `TypeError` → throw `new Error('Cannot reach server. Check your connection or API URL.')`.
5. Error normalization identical to web (`errorBody.detail` → `errorBody.message` → statusText).
6. `exportCsv()` — **changed for mobile**: fetch blob → write to `FileSystem.cacheDirectory/airway_predictions_YYYY-MM-DD.csv` → return file path (screen handles sharing).
7. `runPrediction(data, signal)` keeps the `AbortSignal` parameter.

### Step 5.4 Create `src/utils/formValidation.ts`

Port the ranges from `PatientForm.tsx:62-81` exactly:

```ts
export function validateField(field: keyof PredictionInput, value: any): string | null
// patient_id: required
// age: 0–120 | bmi: 10–60 | mallampati_score: 1–4
// tmd: 3–12 | neck_circumference: 20–60 | mouth_opening: 10–80 | smd: 3–20 | neck_movement: 30–180
export function validateAll(data: PredictionInput): Record<string, string>
```

### Step 5.5 Create `src/utils/randomData.ts`

Port `generateRandomData()` (PatientForm.tsx:144-188) + the 3 fixtures (E/M/D, lines 204-223) verbatim → return valid `PredictionInput` objects.

### Step 5.6 Create `src/utils/parseBullets.ts`

Port `AiClinicalAssessment.parseBullets()` (split by `\n`, trim, filter empty, strip leading `- `).

### ✅ Verify (Step 3 done when...)
- `npm run typecheck` passes (add `tsc --noEmit` script).
- A tiny debug screen can: log in, list patients, list predictions, get a report, check LLM status — all against the real backend.
- Wrong password → friendly error; backend down → friendly network error.

---

## 6. Phase 4 — Login Screen

### Step 6.1 Create `src/screens/auth/LoginScreen.tsx`

Port `src/app/login/page.tsx` 1:1:

- **Layout:**
  - Page bg `#F5F1DC` (dark `#121212`), decorative brand blocks (yellow + magenta rounded squares, absolutely positioned corners)
  - Brand header: 48×48 black rounded square + white `Stethoscope` icon + hard shadow; "Airway MD"; subtitle "Clinical Assessment — Multimodal Airway Prediction"
  - White card: "Welcome Back" + "Sign in to access the assessment dashboard"
  - Username `AppInput` (autoComplete `username`)
  - Password `AppInput` with Eye/EyeOff toggle (autoComplete `current-password`)
  - Error `Banner` (danger) with `AlertCircle`
  - `AppButton` "Sign In" (brand bg, loading spinner + "Signing In...")
- **Behavior:**
  - Validate: username required, password required (inline errors)
  - `signIn()` → success: `router.replace` to MainTabs; fail: show error (401 → "Invalid credentials")
  - Keyboard avoiding: wrap in `KeyboardAvoidingView`; scroll view for small screens
- **Extra (mobile-only):** "Cannot reach server" guidance if the API URL is wrong.

### ✅ Verify (Step 4 done when...)
- Login with `admin/admin123` → Dashboard. Wrong password → red banner. Backend off → network error message. Dark mode looks correct.

---

## 7. Phase 5 — Dashboard (Home Tab)

### Step 7.1 Create `src/screens/home/DashboardScreen.tsx`

Port `src/app/dashboard/page.tsx` (the parts that aren't the form/result):

- **Header:** brand logo + "Airway Assessment" + `{role} · {username}` (capitalized role) + right side: theme toggle (Sun/Moon), LLM status dot (connected=teal / offline=gray / checking=spinner).
- **Stats row** — port `StatsCard.tsx`: Easy / Moderate / Difficult counts + "Total assessments". Compact horizontal cards.
- **Primary CTA card:** "New Assessment" `AppButton` → `navigation.navigate('Assessment')`.
- **Recent Records** — port `MiniHistory.tsx`: last 5 predictions (patient id, class badge, `MMM dd` date, chevron) → tap = navigate `ReportDetail`; "View all" → switch to Records tab.
- **Data:** `getPredictions()` on focus (`useFocusEffect`) + `RefreshControl` pull-to-refresh.
- **LLM status:** `checkLlmStatus()` on mount (non-blocking; update dot).
- **States:** skeleton rows while loading; empty state "No records yet"; error banner with retry.

### Step 7.2 Create `src/hooks/usePredictions.ts`

- Wraps `getPredictions()` + refresh + loading/error state, reused by Dashboard, History, Reports.

### ✅ Verify (Step 5 done when...)
- After a login, dashboard shows user role, stats, CTA, recent records (or empty state), LLM status dot, dark-mode toggle works, pull-to-refresh reloads.

---

## 8. Phase 6 — Assessment Wizard

> **The biggest phase.** Port `PatientForm.tsx` (546 lines) into a 4-step wizard + the submit flow from `dashboard/page.tsx:85-117`.

### Step 8.1 Create `src/screens/home/AssessmentScreen.tsx`

- **State:** `formData: PredictionInput` (init from `defaultFormData` — port `PatientForm.tsx:19-47`), `step: 1|2|3|4`, `errors`, `showAdvanced`, `predicting`, `predictingSlow`, `llmStatus`.
- **Step indicator:** `SegmentedTabs` with 4 items (Basic / Airway / Physical / History) — port section tabs (icons: `User`, `Stethoscope`, `ClipboardList`, `History`).
- **Step 1 — Basic:** Patient ID (text), Age (number), Gender (Male/Female `Select`).
- **Step 2 — Airway:** Mallampati (I–IV `Select`), TMD cm (number), Mouth Opening mm (number).
- **Step 3 — Physical:** Neck Circumference cm, SMD cm, Neck Movement °, plus "More findings" toggle → Beard, Chest Size, Neck Structure, Jaw Movement, Tissue Flexibility.
- **Step 4 — History:** 12 Yes/No toggles (two-option segmented: No/Yes) — port `yesNoSelect()`.
- **Validation:** per-step on "Next"; full `validateAll()` on final submit. Inline field errors (danger text under field) + summary error banner.
- **Test fixtures (web parity):** small labeled buttons **E / M / D / Random** (FunnelFlask/Shuffle icons) that prefill the form — port the 3 fixtures + `generateRandomData()`.
- **Draft persistence (nice-to-have):** save formData to AsyncStorage on change; restore on mount; clear on success.

### Step 8.2 Submit flow (`handleSubmit`) — port exactly

```text
1. setPredicting(true); setPredictingSlow(false)
2. fire checkLlmStatus() in parallel (non-blocking)
3. start slow-timer: 5s → setPredictingSlow(true)
4. start abort-timer: 35s → controller.abort()
5. createPatient({
     patient_id, age, gender, bmi,
     mallampati: String(mallampati_score),   // NOTE: string here (web parity)
     tmd, neck_circumference
   })
   → 409 (duplicate): DECISION — continue to prediction (recommended)
6. result = await runPrediction(formData, controller.signal)
7. on success: navigate('PredictionResult', { result, input: formData })
              + refresh recent records
8. on abort:  error "Time limit exceeded. There has been an error with the
              LLM response. Please wait for a while and try again."
9. on other error: show err.message
10. finally: clear timers, setPredicting(false)
```

- **UI during prediction:** full-screen blocking overlay (web shows spinner state on the button + skeletons) — show card skeleton + spinner + (after 5 s) the "LLM is taking longer than usual" warning banner (`AiClinicalAssessment` slow state).

### ✅ Verify (Step 6 done when...)
- Full wizard: fill E fixture → Next through all 4 steps → "Assess Patient" → reaches result screen in <10 s with real prediction.
- Validation blocks invalid values with correct messages.
- Killing the backend mid-prediction → 35 s abort message.

---

## 9. Phase 7 — Prediction Result Screen

### Step 9.1 Create `src/screens/home/PredictionResultScreen.tsx`

Composes two ported components:

**A. `src/components/result/RiskPredictionCard.tsx`** (port `RiskPredictionCard.tsx`):
- **Gauge** via `react-native-svg`:
  - `Circle` track: `R=52`, `strokeWidth=11`, `strokeDasharray = [0.75*C, C]` where `C = 2πR`, `transform="rotate(135 60 60)"`
  - Progress arc: same, `strokeDasharray = [progress, C]`, animated from 0 → progress over ~1 s (cubic-bezier), color = semantic class color
  - Center readout: `{score.toFixed(0)}` big (Inter 800) + "% Risk" micro-label
  - `score = clamp(riskScore*100, 0, 100)`
- Header: "Airway Risk Score" / "Predicted intubation difficulty" + `{score}/100` (mono)
- Class badge: "Easy Airway" (teal) / "Moderate Airway" (amber) / "Difficult Airway" (red)
- Confidence: label + mono `%` + horizontal progress bar (animated width)
- Probability distribution: stacked segmented bar (Easy/Moderate/Difficult widths) + legend with mono percentages
- Color mapping object per class (port `colorClasses` from web)

**B. `src/components/result/AiClinicalAssessment.tsx`** (port `AiClinicalAssessment.tsx`):
- Header: "AI Clinical Assessment" + urgency badge (Low/Moderate/High)
- Fallback warning `Banner` if `report_sources.* === 'fallback'`: "AI assistant unavailable — showing standard guidance."
- **Assessment** section (brand-tinted card): `parseBullets(summary)` → bullet rows (brand dot)
- **Recommendations** section (green-tinted card): bullet rows (green dot)
- **Risk banner** (amber): canned text by class:
  - Difficult: "Difficult airway anticipated — ensure difficult airway cart and experienced clinician available."
  - Moderate: "Moderate risk — prepare alternative airway devices and have backup plan ready."
  - Low: "Low risk — standard intubation protocol is likely sufficient."
- **Loading state:** skeleton (3–4 shimmer rows) while `predicting`; slow banner if `predictingSlow`.

### Step 9.2 Screen layout

```
AppHeader "Result" (back → Dashboard)
[RiskPredictionCard]
[AiClinicalAssessment]
"New Assessment" AppButton (clears state, goes back to wizard)
```

### ✅ Verify (Step 7 done when...)
- Real prediction displays: gauge sweeps, correct class colors, confidence, probabilities sum to 100%.
- AI summary + recommendations render as bullets; urgency badge correct.
- With LLM offline: fallback banner shows, canned text displays.
- With LLM slow: "taking longer" banner appears at 5 s.

---

## 10. Phase 8 — History Tab

### Step 10.1 Create `src/screens/history/HistoryScreen.tsx`

Port `history/page.tsx` + `PatientHistory.tsx`:

- **Header:** "Patient Records" + `{n} records` + Export CSV button (doctor+; disabled when empty; "Exporting..." spinner).
- **Filter tabs** (`SegmentedTabs`): All / Easy / Moderate / Difficult with counts (disable 0-count tabs except All).
- **Search bar:** `AppInput` with Search icon, debounced 300 ms, matches patient_id (case-insensitive substring).
- **Record list** (cards, not table):
  - Patient ID (semibold) + class `Badge` (dot) + date `MMM dd, yyyy HH:mm` (date-fns `format(parseISO(...))`) + confidence `X.X%` (mono)
  - Actions: View (Eye) → `ReportDetail`; Delete (Trash2, admin-only via `user.role === 'admin'`) → native `Alert.alert` confirm "Delete record for {id}? This cannot be undone." → `deletePrediction(id)` → refetch
- **Client-side filtering** identical to web (`PatientHistory.tsx:42-52`).
- **Empty states:** "No assessment history yet" / "No records match your search".
- **Pull-to-refresh** + loading skeletons.

### Step 10.2 CSV export

```ts
const path = await exportCsv();          // writes file, returns path
await Sharing.shareAsync(path, { mimeType: 'text/csv' });  // native share sheet
```

### ✅ Verify (Step 8 done when...)
- List loads, filters work, search works, delete confirms + removes (as admin), CSV exports via share sheet, dark mode correct.

---

## 11. Phase 9 — Reports Tab

### Step 11.1 Create `src/screens/reports/ReportsScreen.tsx`

Port `reports/page.tsx`:

- **Header:** "Clinical Reports" + `{role} · {username}`.
- **List:** prediction cards — class-colored icon tile (Easy teal / Moderate amber / Difficult red), patient ID, class badge, date, confidence. Tap → `ReportDetail`.
- **Lazy report fetch + cache:** on open, if not cached, `getPredictionReport(pred.id)` → store in local map `{ [id]: LLMReport }` (port web `reports` state). Show spinner row while loading.

### Step 11.2 Create `src/screens/reports/ReportDetailScreen.tsx`

- **Probabilities:** 3 stacked chips (Easy/Moderate/Difficult with % in mono).
- **Clinical Summary:** brand-tinted card, bullets via `parseBullets`.
- **Recommendations:** green-tinted card, bullets.
- **Source badges:** show `summary_source` / `recommendations_source` (`llm` vs `fallback`) subtly (web shows fallback banner instead — use the `AiClinicalAssessment` fallback banner logic if sources include fallback).
- **Empty state (Reports list):** "No reports yet — Run an assessment to generate a clinical report".

### ✅ Verify (Step 9 done when...)
- Reports list shows after predictions exist; tapping loads report; detail renders summary/recommendations; fallback source shows banner; back navigation works.

---

## 12. Phase 10 — Settings & About

### Step 12.1 Create `src/screens/settings/SettingsScreen.tsx`

Port `settings/page.tsx` + mobile additions:

1. **Profile** card: Username (read-only), Role (read-only, capitalized)
2. **Appearance** card: Dark Mode toggle (Switch styled like web: black-bordered square knob, `translate-x` animation)
3. **API Connection** card (new): `AppInput` for API URL (stored via `setApiBaseUrl`), **Test Connection** button → `GET /health` → success: "Connected" (green) / failure: "Failed" (red). Persist override.
4. **System** card: MongoDB (show from `/api/llm/status` + `/health` — if health OK show "Connected"), LLM Model (`checkLlmStatus().model`), ML Model (static "TabTransformer (tabular_best.pt)").

### Step 12.2 Create `src/screens/settings/AboutScreen.tsx`

Port `about/page.tsx` verbatim (all static):

- ML Models: 3 cards (TabTransformer / XGBoost / Random Forest) — accuracy, AUC-ROC, features, filename
- LLM Assistant: provider (OpenRouter API), model (Qwen 2.5 72B Instruct), temperature 0.3, max tokens 512, purpose
- System Architecture: 5 layer rows (Frontend / Backend / ML Engine / LLM Service / Database) with icons

### ✅ Verify (Step 10 done when...)
- Settings shows profile, dark toggle persists across restarts, API URL can be changed + tested, system info correct.
- About renders 3 sections correctly.

---

## 13. Phase 11 — Testing & QA

### Step 13.1 Unit tests (Jest + Jest-Expo + React Native Testing Library)

```bash
npm install --save-dev jest jest-expo @testing-library/react-native @types/jest
```

Test files:
- `src/utils/__tests__/formValidation.test.ts` — boundary tests: age 0/1/119/120, BMI 9.9/10/60/60.1, Mallampati 1/4, TMD 2.9/3/12/12.1, neck 19.9/20/60/60.1, mouth 9/10/80/81, SMD 2.9/3/20/20.1, movement 29/30/180/181, missing patient_id/gender
- `src/utils/__tests__/parseBullets.test.ts` — empty, plain lines, `- ` stripped, whitespace trimmed
- `src/utils/__tests__/randomData.test.ts` — fixtures + random always produce valid ranges
- `src/lib/__tests__/api.test.ts` — mocked fetch: success, 401 (clears token + auth event), 409, network error message, abort signal propagation
- `src/components/__tests__/RiskPredictionCard.test.tsx` — renders score, class label, colors; probabilities sum
- `src/screens/__tests__/LoginScreen.test.tsx` — empty-field validation, submit calls API, error shown

Add `"test": "jest"` script.

### Step 13.2 Manual QA checklist (both Android + iOS, light + dark)

- [ ] Login (correct / wrong / no server)
- [ ] Session expiry (set JWT expiry, relaunch → login)
- [ ] Wizard: all 4 steps, E/M/D/Random fixtures, validation errors
- [ ] Prediction: happy path, LLM slow (>5 s banner), LLM down (fallback banner), 35 s abort
- [ ] History: load, search, filter, delete (admin), CSV export + share
- [ ] Reports: list, detail, lazy load
- [ ] Settings: theme persist, API URL change + test
- [ ] Pull-to-refresh everywhere
- [ ] Offline: airplane mode → friendly errors, no crashes
- [ ] Back navigation correctness on Android hardware back
- [ ] Keyboard: inputs not hidden by keyboard
- [ ] Small phone (SE) & large phone — no clipping

### Step 13.3 Contract test (optional but recommended)

Small script `mobile/scripts/contractTest.ts` (or a jest suite) hitting the real backend: login → create patient → predict → list → report → delete → export. Guards against backend drift.

### ✅ Verify (Step 11 done when...)
- All unit tests pass; manual checklist signed off on both platforms.

---

## 14. Phase 12 — Build & Release

### Step 14.1 Dev build (optional, for native modules on device)

```bash
npx expo run:android    # requires Android Studio
npx expo run:ios        # requires macOS + Xcode
```

### Step 14.2 Preview build (EAS)

```bash
npm install -g eas-cli
eas login
eas build --profile preview --platform android   # APK for sideloading
```

Add to `app.json`:
```jsonc
"eas": {
  "build": {
    "preview":  { "distribution": "internal", "android": { "buildType": "apk" } },
    "production": { "autoIncrement": true }
  }
}
```

### Step 14.3 Production build

```bash
eas build --profile production --platform all
```

- iOS: requires **Apple Developer** account ($99/yr) + `eas credentials`.
- Android: requires **Google Play** account ($25 one-time) — APK/AAB via EAS.

### Step 14.4 Store metadata

- App name: **Airway MD**
- Icon/splash: black bg + Stethoscope + yellow brand (create from existing assets)
- Category: Medical
- Description: clinical decision support for difficult airway prediction
- Screenshots: capture after QA (login, wizard, result, history)

### Step 14.5 (Optional) CI — add mobile job to `.github/workflows/deploy.yml`

- `npm ci`, `npm run typecheck`, `npm test`, `eas build` on push to main (needs `EXPO_TOKEN` secret).

### ✅ Verify (Step 12 done when...)
- APK installs on Android device and works against the **production HTTPS backend**.
- (If iOS) TestFlight build installs and works.

---

## 15. Checklist Summary

### Sequential foundation (must be in order)
- [ ] **P0** Scaffold Expo app (Step 2)
- [ ] **P1** Design system + UI primitives (Step 3)
- [ ] **P2** Navigation shell + auth gate (Step 4)
- [ ] **P3** API client + types + validation (Step 5)

### Parallel feature tracks (after P3)
- [ ] **Track A:** Login (Step 6) → Dashboard (Step 7) → Assessment (Step 8) → Result (Step 9)
- [ ] **Track B:** History (Step 10) → Reports (Step 11)
- [ ] **Merge:** Settings + About (Step 12)

### Final
- [ ] **P11** Testing & QA (Step 13)
- [ ] **P12** Build & Release (Step 14)

### Total estimate
- **13–17 working days** for one developer (from `mobile_application.md` Section 23).

---

## Decisions Re-confirmed in This Plan (for your review)

| # | Decision | Recommended | Your call? |
|---|----------|-------------|------------|
| 1 | Framework | React Native + Expo | ✅ |
| 2 | Navigation | React Navigation v7 (custom tabs) | ✅ |
| 3 | Duplicate patient on predict (409) | Continue to prediction instead of error | ❓ |
| 4 | API URL editable in Settings | Yes | ❓ |
| 5 | Biometric lock in v1 | No | ❓ |
| 6 | Screenshot blocking | No | ❓ |
| 7 | Platforms v1 | Android + iOS | ❓ |
| 8 | Register-user screen | Absent in v1 (web parity) | ❓ |
| 9 | Offline cache (history/reports read-only) | Yes | ❓ |
| 10 | E/M/D/Random test fixtures in production build | Keep (web parity) | ❓ |
| 11 | Tablet support | Phone-first v1 | ✅ |

---

*Review this document. Once you approve (and answer the ❓ decisions), implementation begins at Phase 0 and proceeds in order.*