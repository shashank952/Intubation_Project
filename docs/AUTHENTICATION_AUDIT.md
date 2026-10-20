# Authentication Audit

> Scope: backend (`backend/deploy/`) + web frontend (`src/`) + mobile (`mobile/src/`).
> Date: 2026-08-27
> Status: **for review — not yet implemented**

---

## Summary

Authentication is **partially correct but has two critical security holes and one
UI-breaking bug**. Password hashing and role *checking* are correct; the problem is
that **role *assignment* is client-controlled** and the **JWT secret has a weak
hardcoded default**. The web dashboard also **crashes after login** due to a
`username` vs `email` type mismatch.

**Priority order for implementation:**

1. 🔴 `#1` — registration role escalation (critical)
2. 🔴 `#2` — hardcoded default JWT secret (critical)
3. 🟠 `#3` — web `username` vs `email` crash (breaks the app)
4. 🟡 `#4`–`#6` — hardening (rate-limit, role re-validation, email normalization)
5. 🟢 `#7`–`#9` — polish (Swagger tokenUrl, seed creds, localStorage)

---

## 🔴 Critical

### 1. Anonymous self-registration grants `admin` role

- **Files:** `backend/deploy/routers/auth.py:9-19`, `backend/deploy/schemas.py:13-16`
- **Problem:** The `register` endpoint is unauthenticated. `UserCreate` contains a
  `role` field (default `doctor`), and `register()` does `doc = user.model_dump()`
  and inserts it — so the client controls the role.

  ```http
  POST /api/auth/register
  {"email":"evil@x.com","password":"123456","role":"admin"}
  ```

  → creates a full admin account. Anonymous attacker → admin in one request.

- **Fix (minimal):** never trust the client for role on registration.

  ```python
  doc = user.model_dump(exclude={"role", "password"})
  doc["role"] = "doctor"          # registration never grants admin
  doc["hashed_password"] = hash_password(user.password)
  ```

---

### 2. Hardcoded default JWT secret

- **File:** `backend/deploy/config.py:13`
- **Problem:** `jwt_secret: str = "change-me-in-production"`. If `JWT_SECRET` is not
  set in the environment, every deployment signs tokens with a public, known string.
  Anyone can forge `{"sub":"admin@airwaymd.com","role":"admin","exp":...}` and
  bypass all auth. `require_role` trusts the token's `role` claim entirely and never
  re-checks it against the DB.
- **Fix (minimal):** fail fast instead of silently using the placeholder.

  ```python
  # in Settings, after loading (or in app lifespan)
  if settings.jwt_secret in ("", "change-me-in-production"):
      raise RuntimeError("JWT_SECRET must be set to a strong random value")
  ```

---

## 🟠 High

### 3. Web dashboard crashes after login — `username` vs `email` mismatch

- **Files:** `src/lib/api.ts:27-40`, `src/types/index.ts:1-10`,
  `src/components/Sidebar.tsx:118,121`, `src/app/dashboard/page.tsx:201,238`
- **Problem:** The backend returns the user as `{ email, role }` (`UserOut`), and
  `login()` stores it via `setUser(data.user)`. But `getUser()`/`setUser()` are typed
  `{ username: string; role: string }`. There is **no `username` key** on the stored
  object.

  - `Sidebar.tsx:118` → `user.username.charAt(0)` → `TypeError: Cannot read
    properties of undefined (reading 'charAt')` → sidebar crashes.
  - `dashboard/page.tsx:238` → same crash in the header avatar.
  - `Sidebar.tsx:121` and `dashboard/page.tsx:201` render an empty username.

- **Fix (minimal):** align everything on `email` (matches backend `UserOut`).

  ```ts
  // src/lib/api.ts
  function getUser(): { email: string; role: string } | null { ... }
  function setUser(user: { email: string; role: string }): void { ... }

  // Sidebar.tsx + dashboard/page.tsx
  user.email      // instead of user.username
  user.email.charAt(0).toUpperCase()
  ```

---

## 🟡 Medium

### 4. No rate limiting / lockout on `/login`

- **File:** `backend/deploy/routers/auth.py:22-29`
- **Problem:** Unlimited login attempts → brute-force/credential-stuffing. Returns the
  same "Invalid credentials" (good, no user-enumeration leak) but no throttle.
- **Fix:** simple per-email (or per-IP) attempt counter / delay after N failures.

### 5. Token role never re-validated against DB

- **Files:** `backend/deploy/auth.py:39-47`
- **Problem:** `get_current_user` returns the token claims as-is. If a user is
  deleted or downgraded, their old token still grants the old role until expiry
  (`jwt_expire_minutes=480`, i.e. 8 hours).
- **Fix:** look the user up in MongoDB inside `get_current_user` (or shorten expiry /
  add token versioning).

### 6. No email normalization

- **File:** `backend/deploy/routers/auth.py:12,25`
- **Problem:** `Admin@x.com` and `admin@x.com` are treated as different accounts;
  enables duplicate/ambiguous accounts.
- **Fix:** `email = user.email.strip().lower()` before find/insert.

---

## 🟢 Low

### 7. Swagger "Authorize" is broken

- **File:** `backend/deploy/auth.py:10`
- **Problem:** `OAuth2PasswordBearer(tokenUrl="/api/auth/login")` expects OAuth2 form
  fields (`username`/`password`), but the login endpoint reads JSON
  (`email`/`password`). The docs' Authorize flow won't work.
- **Fix:** either add a form-compatible login or change the security scheme.

### 8. Weak seed credentials + weak password policy

- **Files:** `scripts/seed_db.py:23,34`, `backend/deploy/schemas.py:15`
- **Problem:** `admin123` / `doctor123` default passwords; minimum password length 6
  with no strength requirement.
- **Fix:** rotate seed passwords; enforce a stronger policy for production.

### 9. Web token in `localStorage`

- **File:** `src/lib/api.ts:19,23`
- **Problem:** JWT in `localStorage` is readable by any injected script (XSS).
  Mobile is fine — it uses `expo-secure-store`.
- **Fix:** prefer `httpOnly` cookies, or at minimum tighten CSP / XSS hygiene.

---

## ✅ What is correct (do not touch)

- Password hashing — bcrypt via passlib, `hash_password` / `verify_password` correct.
- `require_role` — missing/unknown role defaults to `viewer` (least privilege).
- Expired/invalid tokens → 401 (via `ExpiredSignatureError ⊂ JWTError`).
- **Mobile auth** is the healthiest surface: encrypted `SecureStore` token storage,
  central 401 → auto-logout handler (`mobile/src/context/AuthContext.tsx:24-29`),
  and `signUp` sends only `email`/`password` (no role from the client).

---

## Fix approach note (ponytail)

Implement with the `ponytail` skill — laziest correct solution, no refactors, no new
dependencies:

- `#1`: one `model_dump(exclude=...)` line + hardcode role.
- `#2`: one fail-fast guard on the secret.
- `#3`: rename `username` → `email` in 2 helper functions + 2 usages.
- `#4`–`#6`: smallest possible additions, no auth library.

---

## ✅ What I implemented (plain English)

All changes below are done and in the code.

### Backend security fixes

1. **Registration can no longer make someone an admin.** Before, anyone could sign
   up and send `role: admin` to become a full admin. Now the server ignores whatever
   role the client sends and always creates new accounts as `doctor`.
   *(`backend/deploy/routers/auth.py`)*

2. **JWT secret is no longer the public placeholder.** Before, the token-signing
   secret defaulted to `change-me-in-production`, so anyone could forge admin tokens.
   Now there's a strong random secret in `.env`, plus a safety net in `config.py`
   that generates a random secret at startup if the placeholder is ever still there.
   *(`backend/deploy/config.py`, `.env`)*

3. **Deleted or downgraded users lose access immediately.** Before, the role was read
   from the token and trusted for up to 8 hours. Now every request re-checks the user
   in the database, so removing a user or changing their role takes effect right away.
   *(`backend/deploy/auth.py`)*

4. **Login now throttles brute-force attempts.** After 5 failed logins for the same
   email within 15 minutes, that email is temporarily locked out (returns 429).
   *(in-memory; fine for a single-process dev server)*

5. **Emails are normalized.** `Admin@x.com` and `admin@x.com` are now treated as the
   same account (lowercased + trimmed) on both register and login.

6. **Swagger "Authorize" is fixed.** Swapped the security scheme from OAuth2 form to a
   plain Bearer scheme, matching how the web/mobile clients actually send the token.

### Frontend + mobile bug fix

7. **The web dashboard no longer crashes after login.** The UI was looking for a
   `username` field, but the backend only sends `email` — so it crashed with a
   TypeError. Fixed everywhere (web + mobile) to use `email`.

### What I deliberately did NOT change (development-stage call)

- **Seed passwords** (`admin123` / `doctor123`) — left as-is because they're
  documented dev credentials; changing them would break your current logins.
- **localStorage token storage → httpOnly cookies** — left as-is. That's a production
  hardening change with real complexity, not worth doing while still in development.
