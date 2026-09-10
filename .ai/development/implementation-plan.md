# Implementation Plan — panchayat-complaint-tracker

rev 4 (2026-09-10), rework after test-architect's CHANGES_REQUIRED on rev 3 (one blocking finding, fixed
in milestones.md — M3's "full critical-workflow set is now live end to end" claim wrongly included
Admin account management, which lands at M4/T-033) and architecture-reviewer's advisories F21-F25 on
rev 3. Inputs: `.ai/testing/test-cases.md` rev 3 (**142 cases**, id **TC-SEC-039** —
middleware-registration-order assertion; totals still **128 always-run / 2 nightly / 12 release-gate**),
test-strategy.md rev 3, regression-plan.md rev 3. This
document does not change architecture, contracts, or test strategy — it sequences building them.
Findings fixed in this rev are tagged inline `[A-Fn]` (architecture-reviewer, F21-F25 this pass; F14-F20
from rev 3 stand unchanged) / `[T-Fn]` (test-architect). Numbering convention: **no task was renumbered**;
four tasks
inserted by rev 3's rework use a letter suffix (`T-003a`, `T-006a`, `T-010a`) so every pre-existing ID
(T-001…T-049) keeps its meaning across revisions — a stable ID is worth more than a tidy sequence.
**Rev 3's focus (F14-F20, unchanged by this rev):** repointed evidence on tasks that cited a TC id whose precondition or
target route lands on a later row (T-006, T-007, T-008, T-009 — see § Task table and § Self-audit);
made explicit which middleware rows are registered provisionally at T-006 vs. finalized/asserted at
T-010a (F15); cited **TC-SEC-039** by id everywhere the old un-ID'd "middleware-order assertion" text
stood (F16); recounted every total to 142/128/2/12 (F17); widened two change-impact-map.md TC-COMP
ranges to `..014` (F19); corrected the self-audit's false "no later-numbered dependency" claim and
added two missing task dependencies (F20).
**This rev's focus (F21-F25):** repointed T-021's search-evidence citation off the `q`-field case it
defers to T-037 (F21); annotated T-027's revoke-all evidence as service-level only, with the
route-level half re-run at T-029 (F22); split T-004's delete-capability evidence into an ORM-only half,
with the full case moved to T-009 (F23); completed T-038's 15-route deny-by-default evidence with the
two cases it was missing (F24); added a missing T-009 dependency and AC-019 credit to T-033 (F25).

## Repository layout

Monorepo, two independently deployable roots (solution-architecture.md § Runtimes and deployables;
backend-architecture.md §1; frontend-architecture.md §1). Paths below are exact — no `TBD` remains.

```
api/                            # Python project root (deployable #1: Fly Machine, bom)
  pyproject.toml                # uv project; runtime deps per dependency-strategy.md §1 (8 baseline)
  uv.lock                       # committed
  .python-version               # 3.13.x
  Dockerfile                    # python:3.13-slim@sha256:<digest>, non-root, CMD = start: (project-config.md)
  fly.toml                      # primary_region=bom, internal_port=8080, release_command, healthcheck (infrastructure.md §3)
  app/
    main.py                     # create_app(): settings → selfcheck → middleware (in order, [A-F1]) → routers
    worker.py                   # RawPeerWorker(UvicornWorker) — ADR-023
    settings.py                 # env-var settings, no defaults for secrets; ENVIRONMENT gate for /docs (BR-010)
    selfcheck.py                # production-config gate (backend-architecture.md §11)
    core/
      errors.py                 # domain error taxonomy + envelope (ADR-018)
      complaint_number.py       # generate/normalise/validate/checksum (ADR-016)
      validation.py             # phone/username/password policy (BR-012/BR-016)
      hashing.py                # argon2 wrapper, h(username)
      clock.py                  # now() — injectable (see § Clock injection decision below)
      client_ip.py              # peer-gated IP derivation (ADR-020) — sole reader of Fly-Client-IP/XFF
      logging.py                # structured JSON logger + redaction filter
      strings.py                # every server-side user-visible message, keyed (AD-12)
    db/
      engine.py                 # request engine (pool 4+2) + limiter AUTOCOMMIT engine (pool 4+0)
      session.py                # get_session() dependency
      guard.py                  # before_execute hook: raise on UPDATE/DELETE of append-only tables
      models/                   # SQLAlchemy 2.x Mapped[...] models, 1:1 with schema.md
      repositories/              # complaint.py, history.py, user.py, session.py, security_event.py
    services/
      auth.py                   # login, logout, session issue/rotate/revoke
      accounts.py                # create clerk, reset password, OTP issuance (BR-013/016)
      complaints/
        __init__.py             # create, update_status, edit_details
        transitions.py          # frozen BR-002 map
        search.py                # keyset pagination + PII-safe list DTO
      lookup.py                  # public lookup + status → public_update mapping
      limiter.py                  # atomic upsert, key derivation, deterministic cleanup
      security_events.py          # append-only event writer, bounded per R3-8/R4-5
    api/
      deps.py                    # current_user, require_admin_clerk, get_session
      routers/                   # session.py, auth.py, lookup.py, complaints.py, accounts.py, health.py
      schemas/                   # request/response DTOs, extra="forbid" on every response
    middleware/                  # security_headers.py, session_loader.py, csrf.py, authz.py, request_id.py
    cli/                         # bootstrap_admin.py, reset_admin_password.py, unlock_account.py
  migrations/
    versions/                    # Alembic, additive-only (schema.md § Migration strategy)
  tests/
    conftest.py                  # db/live_server/query-counter fixtures, factories, injectable clock
    unit/                        # pytest, no marker
    integration/                 # pytest -m integration
    e2e/                         # pytest -m e2e (Playwright for Python)
    cli/                         # bootstrap_admin/reset_admin_password/unlock_account tests [A-F13] —
                                 # aligns with project-testing.md's "tests live in api/tests/ (unit,
                                 # integration, e2e, cli)"; TC-API-130..132 live here

web/                             # Next.js project root (deployable #2: Render Static Site)
  package.json / package-lock.json
  next.config.mjs                 # output: "export", trailingSlash: true
  .nvmrc                          # 22
  tsconfig.json
  headers.config.json              # committed CSP/security headers (generated, §8)
  scripts/gen-csp.mjs               # post-build inline-script hashing
  src/
    app/                            # layout.tsx, page.tsx (/), login/, change-password/, complaints/,
                                     # accounts/, not-found.tsx — no dynamic segments (ADR-004)
    islands/                        # LookupIsland, LoginForm, ComplaintsApp, AccountsApp, ChangePasswordForm
    components/                     # presentational only, no fetching (component-spec.md)
    lib/                            # api.ts, csrf.ts, errors.ts, auth.ts, format.ts
    strings/en.ts                   # every user-visible string (AD-12)
    api-types.ts                    # generated by openapi-typescript, committed, CI fails if stale
    styles/app.css                  # hand-written CSS custom properties

.github/workflows/
  ci.yml                            # API job + frontend job (every push/PR)
  e2e.yml                            # PRs to master + pre-release
  monthly.yml                        # base-image rebuild + dependency re-audit

.ai/ , .claude/                     # unchanged by /build; read-only inputs to it
```

Two lockfiles, two CI jobs, two deployables, one registrable domain (OQ-3) — matches
solution-architecture.md's "three patching streams, no more" (AD-6).

## Dependency graph (why the milestones are ordered this way)

```
schema (migrations, all 7 tables in one initial revision — already fully specified, rev 4 final)
  → test fixtures (base: rollback+markers; extended: live_server+query-counter+seeded accounts) [A-F2]
    → repositories (complaint, history, user, session, security_event, rate_limit_counter)
      → core (errors, clock, hashing, complaint_number, validation, strings)
        → services (auth, accounts, complaints, lookup, limiter, security_events)
          → middleware assembly (TrustedHost/headers/CORS/body-limit [A-F1] + session loader/CSRF/authz)
            → routers (15 endpoints, additive)
              → frontend data layer (api.ts, api-types.ts generated from the running API)
                → screens (public lookup, login, complaints, change-password, accounts)
                  → E2E (drives the real static export + real API)
```

Every task below respects this: a task is never scheduled before the module it imports from. Re-verified
acyclic after this rework's insertions (`T-003a`, `T-006a`, `T-010a`) — see § Self-audit.

## Clock injection decision (gap a — test-architect's three flagged gaps, #1)

**Decision: an injectable clock, not a freezing library.** `core/clock.py` exposes `now()`; in
production it returns `datetime.now(UTC)`, and every module that needs "now" (session expiry, OTP
expiry, rate-limiter window truncation) calls `core.clock.now()` rather than the stdlib directly — a
grep assertion enforces this (coding-guidelines.md). In tests, `conftest.py` provides a fixture that
monkeypatches `core.clock.now` to a controllable value (`advance(delta)` helper), so a test can jump
45 minutes, 9 hours, or 72 hours instantly. No third-party freezing library is added (dependency
budget, dependency-strategy.md §1 criterion 2 — the standard-library-first rule already covers this
with ~15 lines). This is implemented in task **T-005** (core module) and adopted by **T-027**
(session lifecycle) and **T-026/T-040** (limiter windows) and **T-029** (OTP expiry).

**Consequence for test-strategy.md §6 / regression-plan.md §3 [A-F10]:** once T-027/T-029/T-040 land,
the clock-dependent cases test-cases.md rev 2 now names explicitly — **TC-SEC-011b, TC-SEC-014,
TC-SEC-015, TC-SEC-037** (PERF-T26, rate-limiter sweep boundary), **TC-SEC-038** (PERF-T27,
session-sweep boundary) — are always-run (`Reg=Y`), because "advance the injected clock" costs
milliseconds, not real elapsed time. Two cases stay **nightly**, for a different, non-clock reason,
and are **not** moved by this decision: **TC-DB-004** (500-request burst — sheer request volume,
5-25x every other concurrency case in this suite) and **TC-SEC-031** (SEC-T21 — boots a real gunicorn
subprocess, not the lightweight `live_server` thread); both are re-run on-demand per
regression-plan.md §2 whenever their changed area (rate-limit middleware / `core/client_ip.py`) is
touched. This plan does not edit test-strategy.md/regression-plan.md/test-cases.md (test-architect's
artifacts); it records the decision here. Task **T-046**'s done-condition re-verifies the exact
figures test-cases.md's Coverage summary now states: **142 total cases, 128 always-run, ≤8 minutes
wall-clock** (the remaining 14 are **2 nightly** — TC-DB-004, TC-SEC-031 — **plus 12 release-gate**,
per test-cases.md's Coverage summary table [A-F17]).

## ADR-014 scope note — T-036/T-037 corrected (gap b — was mislabeled OQ-9/OQ-10) [A-F3]

Rev 1 wrongly called these two tasks `GATE_6 QUESTION — OQ-9/OQ-10`. They are **not** open questions:
the human already accepted both as MVP scope at **GATE_4** — decisions.md ADR-014 (~lines 319-323):
*"Q3: accept name/phone search on the clerk list. Q4: accept voluntary password change."* Separately,
`architecture/open-questions.md` defines a **different** OQ-9 (:80 — should complaint *detail views*
be audited; default **no**, reconfirmed rev 2 after SEC-F4 — unchanged by this plan, nothing to build)
and a different OQ-10 (:93 — platform log retention window; default "assume `security_event` is the
durable record," confirmed at signup — addressed in **T-049**'s runbook prep below, not a `/build`
task). api-contract.md rev 4 (approved at GATE_5) already specifies `POST /api/password/change`
(voluntary, normal-session variant) and `POST /api/complaints/search`'s `q` field, so **T-036**
(ADR-014 Q4, voluntary change-password entry point) and **T-037** (ADR-014 Q3, name/phone `q` search)
are ordinary in-scope tasks below, placed late (Milestone 4) only because they sit beside the
admin-accounts slice — not because they are conditional. Neither is a dependency of any later
milestone. **Outstanding, not a `/build` blocker:** requirements-analyst still owes the matching FRs
at the next `/requirements` revision (decisions.md:322); T-036/T-037 build directly to
api-contract.md/ADR-014 in the meantime, so there is no behavioural ambiguity for the builder. See
technical-debt.md TD-003/TD-005 for where the *real* OQ-9/OQ-10 are tracked.

## Milestones (summary — full detail in milestones.md)

| # | Milestone | Thin-slice demo |
|---|-----------|------------------|
| M1 | Walking skeleton | clerk logs in, logs a complaint, gets a number; citizen looks it up publicly and sees status |
| M2 | Complaint lifecycle & search | status transitions, edit window, activity history, list/search/pagination, full Complaints screen |
| M3 | Security & session hardening | real client-IP derivation, full rate limiter, session lifecycle, forced password change, CSRF, deny-by-default over every route |
| M4 | Admin accounts + ADR-014 additions | admin creates/resets clerk accounts; voluntary password change and name/phone search (ADR-014 Q3/Q4) ship as ordinary tasks |
| M5 | Observability, resilience, deploy readiness | CSP, healthz caching, sweeps, full CI incl. E2E, Dockerfile/fly.toml final, a11y pass, go-live prep |

## Task table

Legend for the **Evidence** column (exact commands are in `.claude/project-config.md`):
`unit` → `run_test_unit` · `int` → `run_test_integration` · `comp` → `run_test_web` · `e2e` → `run_test_e2e` ·
`sec`/`db` rows are `pytest -m integration` unless noted · TC ids are from `.ai/testing/test-cases.md`
rev 3 (**142 cases**; **128 always-run** [2 nightly, 12 release-gate], ≤8 min wall-clock [T-F6, A-F17]).
"Done" = the cited command exits
0 and the named TC ids pass; for infra tasks, done is a literal manual command result (stated per row).
Early UI tasks (M1/M2) that cite an `e2e:` id are marked **deferred to T-045** [T-F4] — the Playwright
harness itself is not built until M5; the cited id documents *which* spec will exercise the screen once
the harness exists, and the M1/M2 demo criteria (milestones.md) are proven by hand in the interim.

### Milestone 1 — Walking skeleton

| ID | Slice (files/modules) | Delivers | Evidence (Done-condition) | Depends | Size/Risk |
|---|---|---|---|---|---|
| T-001 | `api/pyproject.toml`, `uv.lock`, `.python-version`, ruff/mypy config, `app/main.py` (`/healthz` only), `app/settings.py` (incl. `ENVIRONMENT` flag gating `/docs`,`/redoc`,`/openapi.json` — BR-010) | ADR-003, ADR-010, AD-6, BR-010 | `uv sync --frozen` (uv 0.10.8 — GATE_6 Q3; `.python-version` 3.13 is installed by uv, the system Python is 3.11.9); `uv run ruff check .`; `uv run mypy app`; `curl :8000/healthz` → `{"status":"ok"}`; **local DB = installed PostgreSQL 16 service, not Docker** (GATE_6 Q1 — project-config.md `db_start`; role `panchayat` and DBs `panchayat`/`panchayat_test` pre-exist — no setup step): `"C:\Program Files\PostgreSQL\16\bin\psql" -U panchayat -d panchayat -c "select version()"` shows 16.x (production/CI remain on 17) | — | S / low |
| T-002 | `web/package.json`, `package-lock.json`, `next.config.mjs` (output export), `.nvmrc`, `tsconfig.json`, biome config, `src/app/layout.tsx`+`page.tsx` stub | ADR-004 | `npm ci --ignore-scripts`; `npm run build`; `npx biome ci .`; `npx tsc --noEmit` | — | S / low |
| T-003 | `api/migrations/versions/0001_initial.py` — all 7 tables, 2 enums, 12 indexes verbatim from `schema.md` compact DDL | schema.md (full), ADR-005/006/016/022 | `uv run alembic upgrade head` against local Postgres; `uv run alembic check` clean | T-001 | M / med — get the full DDL/CHECKs right first pass |
| T-003a | **[new — A-F2]** `api/tests/conftest.py` **base**: per-test transaction-rollback fixture for the request DB session, pytest markers (`unit`/`integration`/`e2e`) registered in `pyproject.toml`, fixture-factory skeletons (`make_clerk`/`make_complaint`/`make_session`) | test-strategy.md §3 | `uv run pytest -m integration` runs a scaffold test twice; the rollback fixture leaves zero residual rows between runs (a deliberately-inserted row in run 1 is confirmed absent in run 2) | T-001, T-003 | S / high — foundational; a leaky rollback fixture silently corrupts every later integration test |
| T-004 | `app/db/models/*` (7 tables), `app/db/engine.py` (request pool 4+2, limiter AUTOCOMMIT 4+0), `app/db/session.py`, `app/db/guard.py` | ADR-005, BR-008, AC-016 [T-F1], backend §9/§10 | int: TC-SEC-018 (UPDATE/DELETE on 3 append-only tables raises), TC-SEC-006 **[A-F23 — ORM-half only: the guard raises at the data-access layer; the delete-style-HTTP-request half re-runs in full at T-009 once a router exists]** | T-003, T-003a | M / med |
| T-005 | `app/core/{errors,strings,clock,hashing,complaint_number,validation}.py` + the layering/import-graph unit test [A-F8] | BR-012/014/016(shape), ADR-016, ADR-018, AD-12, clock decision above, coding-guidelines.md § Layering | unit: TC-UNIT-001..004, TC-UNIT-007..010 | T-001 | M / low |
| T-006 | `app/db/repositories/{user,session}.py`, `app/services/auth.py` (login **and logout** — session issue/revoke, no OTP/expiry edge cases yet), `app/middleware/{session_loader,csrf,authz}.py` **and their registration in `create_app()` — rows 4-6 of the ADR-007 middleware chain, in provisional order (T-010a later inserts rows 1-3 and asserts the final exact sequence) [A-F15]**, `app/api/deps.py`, CI grep-suite scaffolding (6 forbidden-pattern checks, coding-guidelines.md) [A-F8] | ADR-007 (core), D-A, BR-003 | unit: layering/import-graph test (coding-guidelines.md § Layering — no `services` import from `api`, no `core` import from `services`); int: session issue/revoke service-level tests calling `services/auth.py` directly (login success, login failure, logout revokes the session row) using the `make_clerk`/`make_session` factory skeletons from T-003a — no HTTP route is hit here, so this is provable before T-008 exists; CI grep-suite scaffolding present (6 forbidden-pattern checks stubbed, wired live at T-016) **[repoints rev-2's `TC-API-001..004` citation, which required routes/fixtures not yet built at this row — A-F14]** | T-004, T-005, T-003a | M / med — session/CSRF core is security-sensitive |
| T-007 | `app/cli/bootstrap_admin.py`, `[project.scripts]` entry point | FR-015, AC-019 | int: TC-API-130/132 (in `tests/cli/` — fresh-deployment bootstrap and second-run no-op, both self-contained); manual `uv run bootstrap-admin` creates one admin, second run no-op. **TC-API-131 moved to T-033 [A-F14]** — its steps ("log in, then create a clerk account and reset a password") need `POST /api/login` (T-008) and the admin-accounts API (T-033), neither of which exists at this row | T-006 | S / low |
| T-006a | **[new — A-F2]** `api/tests/conftest.py` **extended**: `live_server` fixture (uvicorn in a background thread), query-counter fixture (`before_cursor_execute` listener), seeded `admin_test`/`clerk_test` via the bootstrap path (not raw INSERTs) | test-strategy.md §3 | `uv run pytest -m integration` runs a scaffold test using `live_server` + the query-counter fixture; `admin_test`/`clerk_test` are present and usable | T-003a, T-004, T-006, T-007 | S / high — foundational; must exist before T-009/T-010's concurrency and zero-SQL evidence |
| T-008 | `app/api/routers/auth.py`, `app/api/schemas/auth.py`, wire `POST /api/login` **and `POST /api/logout`** (logout returns an anonymous-HMAC token — ARCH-T33 [A-F6/A-F7]) | AC-001, FR-001, ARCH-T33 | int: **TC-API-001..003** [A-F14 — moved wholly here from T-006, now provable: both routes and the seeded `clerk_test`/`live_server` fixtures (T-006a) exist], TC-SEC-001. **TC-SEC-030 moved to T-029 [A-F14]** — it is one case covering *both* logout-token-verifies-anonymous *and* password-change-rotates-cookie; the second half needs `POST /api/password/change`, which doesn't exist until T-029, so the case cannot be evidenced in full here | T-006, T-006a, T-007 | S / low |
| T-009 | `app/services/complaints/__init__.py` (create, retry-on-collision), `app/db/repositories/complaint.py`, `POST /api/complaints` route+schemas — idempotency key (`client_request_id`) from day one | AC-002/003/012/015/016 [A-F23], BR-001/006/007/009/012/014, ADR-016, ADR-022, R2-6, REL-T25 | int: TC-UNIT-001..004, TC-API-010..021, **TC-API-004** [A-F14 — moved here from T-008/T-006: its step targets `POST /api/complaints`, which is built by this row], **TC-API-091** (new-complaint schema half, self-contained); TC-API-017 (REL-T25 — idempotent replay, same id/number, no second row) [A-F7]; **TC-SEC-006 in full** [A-F23, ORM-half already proven at T-004 — this row's router now exists, so the delete-style-HTTP-request half is provable]. **TC-API-090 moved to T-019 [A-F14]** — it inspects *both* the new-complaint *and* the edit-details schema, and edit-details doesn't exist until T-019 | T-005, T-006, T-006a, T-008 [A-F25] | M / med — idempotent-insert + retry logic |
| T-010 | `app/services/lookup.py`, `app/services/limiter.py` (lookup scope only), `POST /api/lookup`, `GET /api/session` (both variants) | AC-006/007/011(lookup)/018, BR-004/005/010/015, ADR-008(lookup) | int: TC-API-050..056, TC-DB-001..003, TC-SEC-002/013, TC-SEC-024 [T-F5] (limiter counter persists through a rolled-back request via the dedicated AUTOCOMMIT engine) | T-003, T-005, T-006, T-006a | M / med — BR-015 query-counter correctness is the anti-enumeration control |
| T-010a | **[new — A-F1]** `app/main.py`: **inserts rows 1-3** of the ADR-007 middleware chain — `TrustedHostMiddleware`, request-ID + security-headers middleware, CORS (`allow_methods == {GET,POST}` exactly) — plus the `MAX_REQUEST_BODY_BYTES=65536` / 413 body-size rejection ahead of body parsing (threat #37, SEC-S8); **asserts the final exact registered sequence** of all 6 rows (rows 4-6 — session-loader/CSRF/authz — were registered provisionally by T-006; this row is where the order becomes load-bearing and permanent) [A-F15] | ADR-007, backend-architecture.md §2 (rows 1-3 + body-size control, and rows 1-6 as an ordered set) | int: **TC-SEC-039** (backend-architecture.md §2 rows 1-6 — walks the registered middleware stack and asserts the exact sequence) [A-F16, replaces rev-2's un-ID'd "middleware-order assertion" text], TC-SEC-027, TC-SEC-028 | T-001, T-006, T-009, T-010 | M / high — ordering is the highest-rework area in the architecture; a silent reorder is a bypass, not a crash |
| T-011 | `web/src/lib/{api,csrf}.ts`, `src/strings/en.ts` (skeleton), `gen:api-types` wiring, committed `src/api-types.ts` | frontend-architecture §4/§5 | `npm run gen:api-types` produces a diff-free `api-types.ts` against the dumped OpenAPI schema (`openapi_dump` command, project-config.md [A-F13]); `npx tsc --noEmit` | T-002, T-008, T-009, T-010, T-010a | S / low |
| T-012 | `web/src/app/login/page.tsx`, `src/islands/LoginForm.tsx` | AC-001, screen-inventory #2 | comp: TC-COMP-004/005; e2e: TC-E2E-001 (**deferred to T-045** [T-F4]) | T-011 | M / low |
| T-013 | `web/src/app/complaints/page.tsx` (new-complaint form only), `src/islands/ComplaintsApp.tsx` (partial), `src/lib/auth.ts` (`AuthProvider`), client_request_id generation | AC-002, screen-inventory #4 (new-complaint states), NFR-011, ADR-022 (client) | comp: TC-COMP-011 [A-F9] (required-field markup / error-summary); e2e: TC-E2E-002 (**deferred to T-045**, partial) | T-011, T-009 | M / med — REL-F1 retry/duplicate UX (full duplicate/retry coverage at T-041) |
| T-014 | `web/src/app/page.tsx`, `src/islands/LookupIsland.tsx` — full state set from screen-inventory #1 | AC-006/007/018, NFR-001(partial)/011 | comp: TC-COMP-001..003; e2e: TC-E2E-004, TC-E2E-006 (**deferred to T-045**) | T-011, T-010 | M / med — many states |
| T-016 | `.github/workflows/ci.yml` — API job (ruff, ruff format, mypy, pytest unit+integration on a Postgres service container, alembic upgrade+check, pip-audit, **layering import-graph test** [T-005/T-006 — hand-written AST/import-walk check; `import-linter` deliberately not adopted, it is not in dependency-strategy.md's dev-dependency list §153], **CI grep suite** — 6 named forbidden-pattern steps per coding-guidelines.md) + frontend job (biome, tsc, vitest, next build w/ byte-budget stub, npm audit) [A-F8] | infrastructure.md §5, ADR-010 | green CI run on a real PR, log attached as evidence | T-001, T-002, T-006a | M / med — first CI is often the flakiest task |
| T-017 | `api/Dockerfile` (digest-pinned `python:3.13-slim`, non-root, `uv sync --frozen --no-dev`), `app/worker.py` skeleton (behavior completed in T-025) | infrastructure.md §3 | `docker build -t api-test api/` (**in CI only** — no Docker on the build machine, GATE_6 Q1) exits 0 | T-001 | S / low |

*(T-015 from rev 1 no longer exists as a single row — its scope is split into T-003a and T-006a per
[A-F2]; every downstream reference to "T-015" has been repointed to T-006a above.)*

**M1 demo:** `uv run bootstrap-admin` → log in at `/login` → new-complaint form → complaint number
shown → open `/` in another tab/profile → enter the number → status "We've received your complaint."

### Milestone 2 — Complaint lifecycle & search

| ID | Slice | Delivers | Evidence | Depends | Size/Risk |
|---|---|---|---|---|---|
| T-018 | `app/services/complaints/transitions.py` (frozen map), `update_status` (row lock + history insert), `POST /api/complaints/{id}/status`, `GET /api/complaints/{id}`, `app/db/repositories/history.py` | AC-004/014/009(part), BR-002/011, ADR-017 | unit: TC-UNIT-005/006; int: TC-API-030..034, TC-API-100, TC-API-072 | T-004, T-006, T-009 | M / med — row-lock concurrency correctness |
| T-019 | `edit_details` service (7-day window), `POST /api/complaints/{id}/details`, `complaint_edit_history` repo | AC-008, FR-012/014, BR-014 | int: TC-API-060..063, **TC-API-090** [A-F14, moved from T-009 — now both the new-complaint and edit-details schemas exist, so the "no government-ID field on either" inspection is fully provable] | T-018, T-009 | M / low |
| T-020 | `GET /api/complaints/{id}/activity` (merged status+edit timeline) | AC-009, FR-011/014 | int: TC-API-070/071 | T-018, T-019 | S / low |
| T-021 | `services/complaints/search.py` (keyset pagination; `status` + exact-match `complaint_number` fields only — `q` deferred to **T-037**, ADR-014 Q3, accepted MVP scope [A-F3]), `POST /api/complaints/search` | AC-005, FR-005/007, NFR-010 | int: TC-API-040..045 **[A-F21 — TC-API-046 is name/phone search-matching, which needs the `q` field this row defers; cited in full at T-037 only]** | T-004, T-009 | M / med — pagination/cursor correctness |
| T-022 | `web/src/app/complaints/page.tsx` (list), status filter, find-by-number, "Load more" pagination, empty states | screen-inventory #4 (list), AC-005 | comp: TC-COMP-006/007; a11y: TC-A11Y-004(part) | T-011, T-021 | M / med |
| T-023 | Detail panel + Activity tab + status-update form + edit-details form (UI) | screen-inventory #4 (detail/status/edit), AC-004/008/009 | e2e: TC-E2E-003 (**deferred to T-045**); comp: TC-COMP-012 [A-F9] (detail form state — 7-day-window enabled/disabled, stale-load advisory) | T-022, T-018, T-019, T-020 | L / med — largest single UI task; if it exceeds ~8 files, split status-form and edit-form into a follow-up sub-task before starting the build iteration |
| T-024 | E2E: status-transition rejection spec; manual concurrent-edit advisory check (BR-011) | AC-004/014 | e2e: TC-E2E-003 (**deferred to T-045**) | T-023 | S / low |

**M2 demo:** clerk moves a complaint New→In Progress→Resolved→Closed (illegal skip rejected), edits a
citizen's phone number within 7 days, sees both in the Activity tab; list is paginated and filterable.

### Milestone 3 — Security & session hardening

| ID | Slice | Delivers | Evidence | Depends | Size/Risk |
|---|---|---|---|---|---|
| T-025 | `app/core/client_ip.py` (peer-gated derivation), `app/worker.py` full `RawPeerWorker`, `app/selfcheck.py` (behavioral proxy-header assertions per review-advisories SEC-F1: 2 of 3 checks live in `worker.py`, refuse-to-serve; 1 in `selfcheck`); confirms `run_dev`'s `--no-proxy-headers` parity with the production worker (project-config.md, ADR-023) [A-F12] | ADR-020/023, security-architecture §5, SEC-T21 | int: **TC-SEC-031** (SEC-T21, 4 cases, backend-architecture §5) run against a real gunicorn process (`live_server` replaced by the actual container CMD for this task only) — **nightly** per test-cases.md's cost note, not part of the ≤8-min always-run budget [A-F7] | T-001, T-005 | M / high — SEC-F1 was reworked 4 times at /architecture; the failure mode is silent, not a crash |
| T-026 | Rate limiter full: `login_ip`/`login_userip`/`login_user` tiers with progressive backoff; `detail`/`write`/`search` scopes wired across every route per the per-route PII table (api-contract.md Conventions); throttle-event once-per-window write rule | ADR-008(full), R2-7/R3-2/R3-3/R4-2/R4-3/R4-5, SEC-T28/T29/T30 | int: TC-SEC-003/016/020/021/022; **TC-SEC-032** (SEC-T28 — one `throttle_*` row per burst); **TC-SEC-033** (SEC-T29 — PII-classification table walk); **TC-SEC-034** (SEC-T30 — write/search 429 scopes; **complaints-route cases only here** — account-route cases (`POST /api/accounts`, `.../reset-password`) complete at **T-038** since those routes don't exist until T-033 [A-F7]); TC-API-020/021 revalidated; nightly: TC-DB-004 | T-010, T-018, T-019, T-021, T-025 | L / high — most rev-4 architecture findings were exactly here; a new route with no PII-table row must fail its own test |
| T-027 | Session lifecycle: idle 45min/absolute 9h, login-triggered `ctid`-bounded sweeps, revoke-all on password change/reset, rotation-on-login (ADR-021); **adopts the injectable clock (T-005)** | ADR-019/021, SEC-T23, PERF-T27 | int: TC-SEC-014/015 (now always-run per clock decision); **TC-SEC-026** (SEC-T23 — revoke-scope: presented-only on new login, both-on-password-change) **[A-F22 — service-level revoke-all only; no `POST /api/password/change` route exists yet, so the password-change half is re-run at route level once T-029 builds it]**; **TC-SEC-038** (PERF-T27 — session-sweep boundary) [A-F7] | T-006, T-005 | M / med |
| T-028 | CSRF full: anonymous stateless-HMAC path + session-bound path, `Origin` allow-list, applied to every unsafe method incl. the public lookup | ADR-007 §4, security-architecture §4 | int: TC-SEC-008/009, TC-DB-003 | T-006, T-010 | M / med |
| T-029 | Password lifecycle: OTP issuance/consumption-by-hash-destruction (R4-1), `must_change_password` gate middleware, `POST /api/password/change` (must-change variant only — no `current_password`), forced Change-Password screen (`web/src/app/change-password/`, `ChangePasswordForm`) | BR-016, ADR-007 §3, R2-5/R4-1, screen-inventory #3 (forced path), SEC-T22 | int: TC-SEC-011/011b/017, TC-API-116; **TC-SEC-025** (SEC-T22 — hash destroyed on OTP consumption, second attempt with same OTP fails) [A-F7]; **TC-SEC-030** (ARCH-T33 — full case, both halves: logout token verifies anonymous *and* password-change rotates the `__Host-session` cookie) [A-F14, moved from T-008 — this is the first row where `POST /api/password/change` exists, so both halves of the case are provable together]; **TC-SEC-026 route-level half** [A-F22 — password-change-revokes-both-sessions, re-run here now that this row builds the route; service-level half already proven at T-027]; comp: TC-COMP-009; e2e: TC-E2E-005 (**deferred to T-045**, part) | T-006, T-007, T-005, T-008 | L / high — 3 architecture rework loops landed here; second-login-with-same-OTP must fail, not merely deny |
| T-030 | `app/services/security_events.py`: login/throttle/reset events, bounded per `(scope,key,window)` (R3-8) and per `(actor_username_hash, derived_ip, 15-min window)` (R4-5); **also bounds `login_success`** the same way (review-advisories SEC-F2) | ADR-011, R3-7/R3-8/R4-5/R4-6, SEC-F2, SEC-T33 | int: TC-SEC-023; **TC-SEC-035** (SEC-T33 — at most one `login_failure` row per 15-min window) [A-F7 — SEC-T28 lives solely at T-026, not duplicated here] | T-026, T-008 | M / med |
| T-031 | Deny-by-default authz sweep over **every route that exists at M3** (T-038 completes the full 15-route pass once M4's accounts routes land [A-F7 reword]); error-envelope completeness (every code in error-catalog.md raised somewhere and asserted); `core/logging.py` redaction filter + never-log-list unit tests | ADR-018, security-architecture §8, AC-015 [T-F1] | int: TC-SEC-004/005; unit: TC-UNIT-010 | T-008..T-029 (every M3 route must exist) | M / med |
| T-032 | Security regression pass: run full `TC-SEC-*` suite, close any gap found, paste evidence | — | int: full `TC-SEC-*` set green (includes TC-SEC-025..030/032..036 landed in this milestone; TC-SEC-031/TC-DB-004 run once as nightly evidence for this pass) | T-025..T-031 | S / low |

**M3 demo:** forged `X-Forwarded-For` does not move the rate-limit key (TC-SEC-031, SEC-T21 case 1);
21st lookup in a minute is 429; an OTP works once and only once; a non-admin clerk's direct API call
to `/api/accounts` is 403; a stale session is rejected and revoked.

### Milestone 4 — Admin accounts + ADR-014 additions

| ID | Slice | Delivers | Evidence | Depends | Size/Risk |
|---|---|---|---|---|---|
| T-033 | `app/services/accounts.py` (create, reset — reuses T-029's OTP mechanism), `GET/POST /api/accounts`, `POST /api/accounts/{id}/reset-password`, `require_admin_clerk` | AC-017, AC-019 [A-F25 — TC-API-131, which proves AC-019, was already moved here from T-007; AC-019 is credited to both tasks], BR-013/016, FR-017/018/019 | int: TC-API-110..119, **TC-SEC-010** [T-F5] (password minimum 12 enforced at create/reset, cross-ref TC-UNIT-008/TC-API-114); **TC-API-131** [A-F14, moved from T-007 — needs the login route (T-008, already built) plus the admin create/reset-password routes this row builds] | T-029, T-007 | M / med |
| T-034 | `web/src/app/accounts/page.tsx`, `AccountsApp` island (list, create form, reset action, OTP-display dialog with acknowledgment guard) | screen-inventory #5, UX-F2 | comp: TC-COMP-010; e2e: TC-E2E-005 (**deferred to T-045**) | T-033, T-011 | M / med |
| T-035 | `app/cli/reset_admin_password.py`, `app/cli/unlock_account.py` | backend §12, REL-F2 (review-advisories) | manual: CLI run prints an OTP once + writes one `security_event` row (infrastructure.md §12.1 runbook steps) | T-033, T-030 | S / low |
| T-036 | Voluntary "Change password" nav entry + normal-session variant wiring (`current_password` field/error state) on the already-built Change Password screen — **ADR-014 Q4** (accepted MVP scope at GATE_4, not a Gate-6 question [A-F3]) | ADR-014 (Q4), screen-inventory #3 (voluntary path), ARCH-T32 | int: **TC-SEC-029** [A-F9] (ARCH-T32 — wrong current password → 422 `invalid_current_password`, session still usable afterward); `POST /api/password/change` normal-session variant tests; comp: **TC-COMP-013** [A-F9] (voluntary-form test) | T-029 | S / low |
| T-037 | `q` free-text field on `POST /api/complaints/search` (`ILIKE` over name/phone) + "Search by name or phone" UI control — **ADR-014 Q3** (accepted MVP scope at GATE_4 [A-F3]) | ADR-014 (Q3), screen-inventory #4 (UX-F1) | int: TC-API-046 (name/phone still excluded from the list DTO); comp: TC-COMP-008 | T-021, T-026 | S / low |
| T-038 | Regression pass over M4: **completes** the full 15-route deny-by-default sweep begun at T-031, including the two new routes/fields and the account-route `write`-scope cases T-026 deferred here [A-F7] | AC-015/017 | int: TC-SEC-004/005/007/019, **TC-SEC-027** (SEC-T24 — GET/POST-only + CORS `allow_methods` re-walked over the now-complete 15-route table), **TC-SEC-033** (SEC-T29 — PII-classification table walk re-run over the complete route table), **TC-SEC-034** (SEC-T30 — account-route write-scope cases, now that T-033's routes exist) **[A-F24 — the three together are the 15-route completion pass]** | T-033..T-037 | S / low |

**M4 demo:** admin creates a clerk account, OTP shown once with acknowledgment gate; new clerk logs in
with the OTP, forced to change password; a regular clerk's direct API call to any admin route is 403;
an already-authenticated clerk uses "Change password" from the nav; a clerk searches the list by name.

### Milestone 5 — Observability, resilience, deploy readiness

| ID | Slice | Delivers | Evidence | Depends | Size/Risk |
|---|---|---|---|---|---|
| T-039 | `/healthz` 10s in-process cache; structured JSON log fields finalized; never-log-list suite completeness | observability-reliability.md §1/§3 | int: **TC-SEC-036** [A-F9/T-F5] (log-capture assertion across login/OTP/validation-error traffic — password, OTP, session-cookie value, CSRF token, citizen name/phone never appear in any log line) | T-005, T-016 | S / low |
| T-040 | Rate-limit-counter sweep on window rollover (deterministic `ctid`-bounded delete); session sweep from T-027 re-verified under the clock fixture | PERF-F2/F5, R3-9/R3-10, PERF-T26 | int: **TC-SEC-037** (PERF-T26 — limiter-counter sweep, always-run); **TC-SEC-038** (PERF-T27 — session sweep, re-verified here under the clock fixture) [A-F7] | T-026, T-027 | M / med |
| T-041 | Resilience UI: "may already be saved" duplicate-creation state (T-013 hardened), chunk-load-failure reload prompt, per-screen error boundaries | REL-F1 (client), frontend-architecture §6 | comp: **TC-COMP-014** [A-F9] (double-submit and retry-after-failure both resolve to exactly one `client_request_id`, cross-checked against TC-API-017) | T-013, T-022, T-023 | M / low |
| T-042 | CSP spike + `scripts/gen-csp.mjs` + `headers.config.json`; security-headers middleware finalized; byte-budget CI gate (≤120KB gz on `/`) | ADR-010 H-C, frontend-architecture §8/§9 | `npm run build && npm run gen:csp`; CI byte-budget check log attached | T-002, T-014 | M / med — spike may force the named `unsafe-inline` fallback; if so, record it as a fallback here, not silently |
| T-043 | `api/Dockerfile` final (digest pin, non-root, CMD = project-config.md `start:`, literal `--bind 0.0.0.0:8080` — Fly sets no `$PORT`, infrastructure.md:101/tech-stack.md:804 [A-F4]), `fly.toml`, `selfcheck` wired as a startup hook + release command | infrastructure.md §3, ADR-023, BR-010 | `docker run -p 8080:8080 ... && curl :8080/healthz` locally; `selfcheck` fails on a deliberately-wrong env var (proves the gate works); **TC-SEC-012** [T-F5] (`GET /docs`,`/redoc`,`/openapi.json` all 404 under this prod-shaped config) | T-017, T-025 | M / med |
| T-044 | CI complete: E2E job (PRs to `master` + pre-release), monthly scheduled job (base-image rebuild + `pip-audit`/`npm audit` re-run); branch-protection settings documented as a human GitHub-UI step | infrastructure.md §5 | green E2E job run attached; monthly job dry-run | T-016, T-043, T-024 | M / med |
| T-045 | Full E2E suite (6 Playwright specs) wired to the host rewrite rule (`/complaints/*` → shell) + CI static server — the harness every earlier-milestone task's "deferred to T-045" e2e cell resolves against | AC-010, TC-E2E-001..006 traceability | `run_test_e2e` green, 6/6; **TC-PERF-001/002** green (network-throttled, AC-010) | T-012, T-013, T-014, T-018, T-023, **T-029** [A-F20 — TC-E2E-005 exercises the forced-change-password screen T-029 builds], T-033, **T-034** [A-F13] | M / med |
| T-046 | Full regression run; confirm always-run wall-clock ≤8 min across the **128**-case always-run set (test-strategy.md §6, test-cases.md Coverage summary [T-F6, A-F17]); fix flakiness per regression-plan.md §3 rules | — | full suite green (**142** total cases: 128 always-run + 2 nightly + 12 release-gate), 128 always-run timed at ≤8 min, recorded | all prior | M / med |
| T-047 | Accessibility pass: focus order, live regions, contrast/target-size per screen-inventory, across all screens | TC-A11Y-001..006 | comp+e2e a11y set green | T-012, T-013, T-014, T-022, T-023, T-034, **T-029, T-036** [A-F20 — a11y coverage includes the `/change-password` screen (forced path built at T-029, voluntary path/nav entry at T-036)] | M / med |
| T-048 | AC-013 retention integration test (simulated window) + design-review evidence note (no deletion job exists); AC-012 review note; licence inventory (`uv tree` + `npm ls --all` report) | AC-012/013, dependency-strategy.md §5 | int: TC-API-092; design review: TC-DESIGN-001 | T-009 | S / low |
| T-049 | Go-live prep: second-admin provisioning step documented as a runbook action (OQ-5), domain/CORS config left as named env vars (OQ-3, human fills at /release), confirm the platform's actual log-retention window at signup and record it in the runbook (**real OQ-10**, open-questions.md:93-96 [A-F3]), `selfcheck` dry run against a prod-shaped local env | ADR-024 human note (Q5), infrastructure.md §13 | manual: `selfcheck` passes with prod-shaped env vars, fails with one deliberately wrong | T-043 | S / low |

**M5 demo:** `docker build && docker run` the API image locally with prod-shaped env vars, `selfcheck`
passes; full CI (both jobs + E2E) green on a PR; a11y and byte-budget gates enforced in CI.

## Git workflow for the build phase

- **Branch per task:** `build/T-0NN-short-slug` (letter-suffixed IDs use the same pattern, e.g.
  `build/T-003a-conftest-base`), off the milestone branch `build/M1`…`build/M5`, which is cut from `master`. One task = one PR into the milestone branch; **the human merges each milestone branch into `master`** (GATE_6 Q4 — the repository's default branch is `master`, not `main`; the GitHub remote is added by the human before T-016, GATE_6 Q2). One task = one PR. Never bundle two task IDs in one PR
  (breaks the evidence trail and the change-impact map).
- **Commit format:** `T-0NN: <imperative summary>` as the subject; body cites the AC/BR/ADR ids
  delivered and the TC ids proven, e.g. `T-018: status transitions + row-locked update\n\nDelivers
  AC-004, AC-014, BR-002, BR-011 (ADR-017). Evidence: TC-UNIT-005/006, TC-API-030..034, TC-API-100.`
- **Checkpoint after each task's evidence:** before opening the PR, the implementing agent pastes the
  exact command and its output (or the relevant tail) for every Evidence cell in the task's row —
  per coding-guidelines.md § What "evidence" means. A PR with no pasted command output is not done.
- **Review:** producer never approves own work (CLAUDE.md); the reviewing agent re-runs the cited
  command, does not just read the paste.
- **Migrations:** `db_makemigrations` output is committed only after a human (or, pre-GATE_6-human,
  the reviewing agent acting as the required second pair of eyes) reads the generated SQL — never
  autogenerate-and-commit blind (coding-guidelines.md § Migrations).
- **No force-push, no history rewrite, no destructive SQL, no production deploy** from any agent
  (CLAUDE.md, unchanged here).

## Test-first mapping

Covered inline in each task's Evidence column and exhaustively in test-strategy.md §9 (AC → TC ids,
19/19 — cross-checked by grep, see § Self-audit) and test-cases.md rev 3 (**142 cases**, **128**
always-run [2 nightly, 12 release-gate], ≤8 min). This plan adds no new test level and invents no new
TC ids; where a task
implements a named architecture assertion (SEC-T21..T33, ARCH-T32/33, PERF-T26/27, REL-T25), the
Evidence column cites the **TC id** test-cases.md's own assertion-mapping table (§ "Architecture
assertion → TC id(s)") assigns to it, with the assertion name kept in parentheses for traceability —
not the assertion name alone [A-F7].

## Deferred (technical debt)

See `technical-debt.md` for the full list with ids, reasons and revisit triggers. Summary: 4 items are
documentation-only advisories owned by other roles (not a `/build` task — includes the tech-stack.md/
technology-comparison.md start-command wording cleanup owned by technology-evaluator [A-F11]), 3 items
are blocked on a human answer already tracked as an open question (OQ-2 dump destination, OQ-3 domain,
OQ-10 real log-retention confirmation), 1 item is a named architectural fallback (CSP `unsafe-inline`)
taken only if T-042's spike fails. The real OQ-9 (detail-view audit, default "no") is restated in
TD-005 as a closed scope decision, not debt.

## Self-audit

- Every task has a done-condition (an exit-0 command or a stated manual result) and an evidence
  citation (TC ids and/or a literal command) — no task lacks both.
- Every AC-001..AC-019 appears in at least one task's Delivers/Evidence — re-grepped after this
  rework: AC-001 T-008/T-012; AC-002 T-009/T-013; AC-003 T-009; AC-004 T-018/T-023/T-024; AC-005
  T-021/T-022; AC-006 T-010/T-014; AC-007 T-010/T-014; AC-008 T-019/T-023; AC-009 T-018/T-020/T-023;
  AC-010 T-045; AC-011 T-010; AC-012 T-009/T-048; AC-013 T-048; AC-014 T-018/T-024; AC-015 T-009/T-031/
  T-038; **AC-016 T-004/T-009** (fixed — was uncited, T-F1; T-009 added [A-F23]); AC-017 T-029/T-033/T-034/T-036/T-038; AC-018
  T-010/T-014; AC-019 T-007/T-033 [A-F25]. All 19 present.
- Milestone 1 is a genuine end-to-end slice: a human can log a complaint and look it up publicly
  after M1 alone, without M2-M5.
- **No task depends on a task listed later in the build order** — letter-suffixed ids are ordered by
  row position, not by number, so e.g. `T-006a` (row after T-007) legitimately depends on `T-007` (the
  row before it) even though `6 < 7`; this is not a numbering violation [A-F20, corrects rev 2's false
  "no later-*numbered*" claim, which broke on exactly this case]. Confirmed by walking every row's
  Depends cell top-to-bottom: `T-003a`→{T-001,T-003}; `T-006`→{T-003a,T-004,T-005}; `T-006a`→
  {T-003a,T-004,T-006,T-007}; `T-008`→{T-006,T-006a,T-007}; `T-009`→{T-005,T-006,T-006a,T-008} [A-F25]; `T-010a`→
  {T-001,T-006,T-009,T-010}; `T-019`→{T-009,T-018}; `T-029`→{T-005,T-006,T-007,T-008}; `T-045`→{…,T-029,
  T-033,T-034}; `T-047`→{…,T-029,T-036} — every dependency named is an earlier row than the task
  citing it, so the graph remains acyclic by construction (schema → fixtures → repositories → services
  → middleware → routers → frontend → screens).
- `.claude/project-config.md` and `.claude/project-testing.md` have no remaining `TBD`/`<…>` except
  `base_url_prod`/`base_url_api_prod`, which are explicitly allowed to stay TBD (no domain registered
  yet, OQ-3) and are stated as such rather than guessed.
- Every carried advisory in `.ai/architecture/review-advisories.md` is either a task above (SEC-F1 →
  T-025, SEC-F2 → T-030, REL low "reset-admin-password" → T-035) or listed in technical-debt.md with
  an owner and a reason (the doc-only advisories owned by solution-architect/data-api-architect/
  ux-designer/requirements-analyst/technology-evaluator — including the start-command wording item
  added to TD-002 in this rework [A-F11] — none of which is a `/build` deliverable).

## Conflicts

None found that block `/build`. One thing worth the architects' attention, not blocking: T-023
(Complaints detail panel + status form + edit form + activity tab) is sized L against the ≤8-files/
≤400-lines guidance in this role's brief; it is kept as one task because the four sub-views share one
`AuthProvider`-driven data hook (`useComplaints`) and splitting it risks an inconsistent detail-panel
state mid-build. If the build agent finds it exceeds the guidance in practice, split along the
component-spec.md boundary (detail read-only vs. the two write forms) as a same-milestone follow-up
task, not a scope cut.
