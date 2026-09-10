# panchayat-complaint-tracker — testing brief

Generated at GATE_2 (2026-09-09) from .claude/project-config.md and .ai/technology/tech-stack.md rev 5.
Paths marked TBD are set in /plan. Anything present here overrides discovery.
rev 2 (2026-09-10) /plan rework: Start command now matches project-config.md's `run_dev`
(`--no-proxy-headers`, A-F12); `tests/cli/` (A-F13) is a real directory in implementation-plan.md's
repo layout, not just a category name here.

## Stack
- Frontend:    Next.js 15 + React 19 + TypeScript 5, fully static export (output: "export"), Node 22 LTS build-only
- Backend:     FastAPI on Python 3.13 (JSON API only, sync handlers), gunicorn + uvicorn-worker
- Database:    PostgreSQL 17 (managed); SQLAlchemy 2.x + Alembic
- Router:      Next.js App Router (static routes only — no dynamic segments; /complaints/* rewrites to the /complaints shell)
- Auth:        httponly-session-cookie   # __Host-session, SameSite=Lax, set by the API; CSRF via X-CSRF-Token header

## Runtime
- Start command:    uv run uvicorn app.main:app --reload --port 8000 --no-proxy-headers   (API)  ·  npm run dev   (web, port 3000)
- Base URL:         http://localhost:3000
- Backend URL:      http://localhost:8000
- Environment:      local
- Source root:      api/app/ (Python package, FastAPI service — see implementation-plan.md § Repository layout) and web/src/ (Next.js app); tests live in api/tests/ (unit, integration, e2e, cli) and web/src/**/*.test.tsx (Vitest, colocated)

## Modules (top-level surfaces to test)
- public-lookup: citizen enters a complaint number, sees status + date + fixed public status message; no name/phone ever  (routes: /)
- clerk-auth: username/password login, forced password change, idle/absolute session expiry, logout  (routes: /login)
- complaints: clerk logs a complaint, lists/filters, views detail (client state, no id in URL), updates status with a note, edits within the edit window  (routes: /complaints, /complaints/*)
- accounts: admin clerk creates clerk accounts and resets passwords; one-time password shown once  (routes: /accounts)

## Critical routes
- / — public complaint-status lookup (static shell + client island)
- /login — clerk login
- /complaints — clerk complaint list and detail (detail is client state; deep links land on the list)
- /accounts — admin-clerk account management (regular clerk must be denied by the API)

## Critical API endpoints (if backend exists)
- GET /healthz — process + DB health (public)
- GET /api/session — CSRF token bootstrap (public; must execute no SQL when no session cookie is presented)
- POST /api/lookup — public status lookup; response contains only complaint_number, status, date_logged, public_update
- POST /api/login — clerk login; rate-limited per username+IP; returns rotated CSRF token
- clerk complaint and account endpoints (api-contract.md, 11 routes behind a session, 3 of them admin-only):
  `POST /api/complaints`, `POST /api/complaints/search`, `GET /api/complaints/{id}`,
  `GET /api/complaints/{id}/activity`, `POST /api/complaints/{id}/status`,
  `POST /api/complaints/{id}/details`, `POST /api/logout`, `POST /api/password/change`,
  `GET /api/accounts` (admin), `POST /api/accounts` (admin),
  `POST /api/accounts/{id}/reset-password` (admin) — every route declares an explicit response_model
- GET /docs, /redoc, /openapi.json — must return 404 in production-shaped config

## Critical workflows
- Log a complaint: login → new complaint (name, phone, description) → complaint number issued → appears in list
- Public lookup: open / → enter the number → status, date logged and public status message shown; no name/phone anywhere in the response or DOM
- Status update: login → open complaint → change status (New → In Progress → Resolved/Rejected → Closed, no skipping) with a note → history appended
- Admin reset: admin login → /accounts → reset a clerk's password → one-time password shown once → clerk must change it at next login

## Business rules worth checking
- Blank/whitespace/malformed complaint number → "Enter a valid complaint number", and no query touches the complaint table (FR-020 / AC-018, server-side)
- Status transitions cannot skip steps; New → Rejected directly is refused (BR-002)
- Public response never contains citizen name or phone (BR-005 / NFR-009); public_update is from a fixed set (GATE_2 Q7)
- 20 lookups per IP per minute → 429 with Retry-After; the limit must hold under parallel requests (AC-011)
- Login protection is **anti-lockout backoff, not account lockout** (threat-model.md #36): repeated
  wrong passwords produce `429 + Retry-After` (≤5s at the per-account tier), never a locked/disabled
  account and never a thread sleep; `unlock-account` clears counters, it does not mean an account was
  "locked." Do not test for, or describe findings in terms of, an account-lockout state — it does not
  exist by design.
- History is append-only: no update or delete path on status/edit history (FR-011 / FR-014)
- Regular clerk is denied account-management endpoints by the API, not just hidden in the UI (AC-015, both directions)
- POST without a valid CSRF token → 403 on both an authenticated write and the public lookup
- Password minimum length 12; one-time password expires in 72 h and is single-use

## Test data strategy
- Synthetic data only; production data is never copied to dev, CI or any AI tool
- Local Postgres is reset by re-running Alembic migrations. Fixtures (api/tests/conftest.py, per
  test-strategy.md §3): a per-test transaction-rollback fixture for the request DB session; a
  `live_server` fixture (uvicorn in a background thread) for concurrency/E2E-adjacent tests; a
  query-counter fixture (`before_cursor_execute` listener) for "no SQL touched `complaint`"
  assertions; fixture factories `make_clerk()`, `make_complaint()`, `make_session()` with
  synthetic defaults; an injectable clock (`core/clock.py`) so session/OTP/rate-limiter window
  tests can advance time deterministically instead of waiting or freezing wall-clock (see
  implementation-plan.md § Clock injection decision)
- Test accounts: one admin clerk and one regular clerk created by the bootstrap-admin command / fixtures in local only

## Auth strategy
- Persistent profile (Layer 1) — log in once via the /login form; the httpOnly __Host-session cookie is not JS-readable, so do not attempt token capture via browser_evaluate
- Credentials source: .env.test.local keys (gitignored) or manual entry once, persisted by profile — never written into any file this skill produces

## Known limitations
- Static frontend: client-side route guards are UX only; every authorisation assertion must target the API
- No staging environment; frontend PR previews are not in the API's CORS allow-list and talk to no real data
- Public lookup requires a first-party cookie (__Host-csrfseed) and JavaScript; cookie-blocking browsers see an "enable cookies" message
- No error tracker; server errors are visible only in platform logs

## Destructive-operation policy
- Local dev only — deletions and migration resets are safe against the local Postgres
- Any environment other than local: never run bulk-delete, reset or migration tests; production is human-only
