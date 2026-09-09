# panchayat-complaint-tracker — testing brief

Generated at GATE_2 (2026-09-09) from .claude/project-config.md and .ai/technology/tech-stack.md rev 5.
Paths marked TBD are set in /plan. Anything present here overrides discovery.

## Stack
- Frontend:    Next.js 15 + React 19 + TypeScript 5, fully static export (output: "export"), Node 22 LTS build-only
- Backend:     FastAPI on Python 3.13 (JSON API only, sync handlers), gunicorn + uvicorn-worker
- Database:    PostgreSQL 17 (managed); SQLAlchemy 2.x + Alembic
- Router:      Next.js App Router (static routes only — no dynamic segments; /complaints/* rewrites to the /complaints shell)
- Auth:        httponly-session-cookie   # __Host-session, SameSite=Lax, set by the API; CSRF via X-CSRF-Token header

## Runtime
- Start command:    uv run uvicorn app.main:app --reload --port 8000   (API)  ·  npm run dev   (web, port 3000)
- Base URL:         http://localhost:3000
- Backend URL:      http://localhost:8000
- Environment:      local
- Source root:      TBD (set in /plan) — expected two roots: the API package (Python) and the web app (src/)

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
- clerk complaint and account endpoints — paths TBD (set in /plan); every route declares an explicit response_model
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
- History is append-only: no update or delete path on status/edit history (FR-011 / FR-014)
- Regular clerk is denied account-management endpoints by the API, not just hidden in the UI (AC-015, both directions)
- POST without a valid CSRF token → 403 on both an authenticated write and the public lookup
- Password minimum length 12; one-time password expires in 72 h and is single-use

## Test data strategy
- Synthetic data only; production data is never copied to dev, CI or any AI tool
- Local Postgres is reset by re-running Alembic migrations; fixtures TBD (set in /plan)
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
