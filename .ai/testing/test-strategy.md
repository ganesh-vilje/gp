# Test Strategy — panchayat-complaint-tracker

rev 3 (2026-09-10) — rework after rev 2 GATE_6 reviewer findings (arch F16/F17/F18, test-review
F1/F2): added **TC-SEC-039** for the previously-unmapped middleware-registration-order assertion
(backend-architecture.md §2 rows 1-6 / tech-stack.md assertion 16 — arch F16) and recounted every
total to **142** total / **128** always-run; §6 is restated as an exact per-level breakdown (not an
estimate) that correctly names **TC-SEC-012 as release-gate** (rev 2 miscounted it as always-run —
arch F17) and **TC-DB-004/TC-SEC-031 as nightly**; §3/§6 now separate the 5 clock-injection-driven
always-run reclassifications (TC-SEC-011b/014/015/037/038) from the 3 separately-fast deterministic
ones (TC-SEC-024, TC-API-019, TC-API-054 — test-review F2, rev 2 wrongly attributed all 8 to clock
injection); every wrong-meaning "OQ-9"/"OQ-10" reference is replaced with **ADR-014 Q4** (voluntary
password change) and **ADR-014 Q3** (name/phone search) — those OQ numbers name unrelated open
questions in architecture/open-questions.md (arch F18). rev 2's fixes (§1/§9 total and traceability
corrections, the injectable-clock update) stand unchanged except where superseded above.
Produced in `/plan` before GATE_6. Inputs: acceptance-criteria.md rev 6,
user-stories.md rev 4, business-rules.md rev 6, product-requirements.md rev 5,
api-contract.md rev 4, error-catalog.md rev 4, screen-inventory.md, user-flows.md,
tech-stack.md rev 5.1, review-advisories.md, threat-model.md rev 3, .claude/project-testing.md,
.claude/project-config.md. No application code exists; this document constrains what
implementation-plan.md may claim as "tested."

## 1. Pyramid and target counts

| Level | Tool (from project-config.md) | Actual count (test-cases.md) | What it proves |
|---|---|---|---|
| Unit (Python) | `pytest -m "not e2e and not integration"` | 10 | Pure validation/business-rule logic that needs no DB: phone/name/description format and length (BR-012/BR-014), username/password policy (BR-016), complaint-number checksum/format, status-transition map (BR-002), error-envelope shape |
| Integration (Python + real Postgres) | `pytest -m integration` | 103 (59 API + 4 DB + 40 security) | Anything that needs a real transaction, a real unique constraint, real concurrency, or a real row: complaint-number uniqueness under concurrency (AC-003), rate limiting under parallel load (AC-011), audit-trail append-only behaviour (BR-008/BR-011/FR-011/FR-014), authz/authn on every route (AC-015/AC-017), CSRF, session lifecycle, query-counter "no SQL touched `complaint`" assertions (AC-018), OTP consumption/expiry (including hash-destruction, SEC-T22), admin account management (AC-017/AC-019), the middleware-registration-order assertion (tech-stack.md assertion 16, TC-SEC-039), and the architecture-named assertions SEC-T21..T33/REL-T25/ARCH-T32/T33/PERF-T26/T27 (see test-cases.md's mapping table) |
| Frontend component (Vitest + Testing Library) | `npm run test` | 14 | Client-side rendering/validation logic that doesn't need a live backend: lookup island's format check and error/timeout states, login form states, complaints-list rendering against a mocked API, required-field markup (TC-COMP-011), complaint-detail edit-window/stale-load form state (TC-COMP-012), voluntary change-password form (TC-COMP-013), retry/duplicate-submit state on complaint creation (TC-COMP-014), a11y roles on the live regions |
| E2E (Playwright for Python via `pytest -m e2e`) | `pytest -m e2e` | 6 (per tech-stack.md's stated 4-6 band, ceiling used) | The handful of full-stack workflows a human actually does: clerk login (AC-001), log a complaint incl. in-flight/timeout (AC-002/NFR-011), status-transition rejection (AC-004), public lookup success+not-found (AC-006/AC-007), blank/malformed lookup message (AC-018 client side), admin reset-password → forced change (AC-017) |
| Accessibility / Performance / Design-review | component+E2E cross-check / Playwright-throttled / code-review | 6 + 2 + 1 | See test-cases.md §Accessibility/§Performance/§Design — not part of the pyramid proper but counted in the grand total below |
| Browser QA (manual/agent-driven, `app-qa` skill) | `/smoke-test`, `/full-test`, `/regression-test` | not counted here — see §7 | Exploratory/visual/responsive confirmation of the same workflows against a running deployment, using `.claude/project-testing.md` as its brief |

Total test cases in test-cases.md: **142** (10 unit + 103 integration [59 API + 4 DB + 40 security] +
14 component + 6 E2E + 6 a11y + 2 perf + 1 design review). Of these, **128 are always-run**, **2 are
nightly** (TC-DB-004, TC-SEC-031) and **12 are release-gate** (see §6 for the exact per-level
breakdown). This figure is recounted directly from test-cases.md's rows and is restated identically
in test-cases.md's own Coverage summary, regression-plan.md, test-plan.md, and README.md — no
document states a different number. This mix is
deliberately integration-heavy, not unit-heavy — see §2 for why this project inverts the textbook
pyramid.

## 2. Level chosen per requirement class, and why

- **Business rules that are pure functions of input (BR-012 phone shape, BR-014 max lengths, BR-016
  username/password shape, BR-002 the frozen transition map as a data structure)** → **unit**. No DB
  needed to prove "given this string, is it valid"; tech-stack.md's own query-counter/live-server
  fixtures are integration-tier tools, so pure validation stays out of that tier for speed.
- **Business rules that depend on a real database property (uniqueness, atomicity, concurrency,
  append-only, transaction rollback)** → **integration, against real Postgres, never SQLite**
  (tech-stack.md § Tooling, D6/D7/D8: "the `UNIQUE` constraint, transactions and the `ON CONFLICT`
  counter behave as in production"). This covers BR-001/FR-013 (complaint-number uniqueness under
  concurrent creation, AC-003), BR-011 (concurrent status updates, AC-014), BR-008 (no
  UPDATE/DELETE on the three append-only tables, security-assertion 13), and the rate limiter
  (BR-010/NFR-005, AC-011) — a fixed-window counter over a real table cannot be proven correct
  against a fake DB, per tech-stack.md's own rejection of SQLite/in-process counters.
- **API contracts (request/response shape, status codes, error codes, PII exclusion)** → **integration**,
  using `httpx`/`TestClient` against the real API and real Postgres — this is where every
  AC-002/004/005/006/007/009/011/015/016/017/018/019 assertion that names a specific status code,
  field, or "never contains X" lives, because api-contract.md and error-catalog.md are API-level
  documents.
  - AC-018's asserted DB effect ("no statement touching the `complaint` table") is a Python
    integration test using the `before_cursor_execute` query-counter fixture named in tech-stack.md
    §Tooling, asserting by table name, not by count.
  - The 429-under-parallel-load requirement (AC-003, AC-011) uses `concurrent.futures` +
    `httpx.Client` against the `live_server` fixture, exactly as tech-stack.md §Tooling prescribes;
    a sequential loop is explicitly rejected as evidence there and in this strategy.
- **Workflows that only exist end-to-end in a real browser against a real static export + real API**
  (in-flight/timeout UI states, focus order, `<noscript>`, forced-password-change redirect, CSP
  headers on the deployed shape) → **E2E**, kept to the 4-6 specs tech-stack.md names, because each
  Playwright spec is materially more expensive to write and maintain than an integration test that
  proves the same server-side contract.
- **Pure rendering/validation logic that has no server dependency at all** (the lookup island's
  client-side format check, disabled-button/label states, required-field markup) → **Vitest
  component tests**, mocking the API — proving the same business rule twice (once server-side,
  once client-side) is intentional here only where BR-015/FR-020 explicitly documents client-side
  validation as "defence in depth, not the contract" (business-rules.md BR-015).
- **NFR-006 (hosting choice) and NFR-007 (uptime)** are **not** given product test cases — per
  product-requirements.md's own Verification column, NFR-006 is assessed at architecture/deployment
  review and NFR-007 is deferred to post-launch uptime monitoring (the `/healthz` pinger,
  tech-stack.md § Observability). No test-case ID is invented for either; this is stated as a
  deliberate deferral, not a gap (see §6).
- **AC-013 (12-month retention)** is verified once by design/code review (no scheduled-deletion job
  exists — grep/code-review evidence) plus one integration test using a simulated/reduced retention
  window, exactly as acceptance-criteria.md AC-013 itself specifies; a live 12-month wait is never
  attempted.

## 3. Tooling detail (reusing tech-stack.md; nothing new invented)

- **Markers:** `pyproject.toml` registers `integration` and `e2e` (per project-config.md); unit tests
  carry neither marker so the default `pytest -m "not e2e and not integration"` selects them.
- **Fixtures:**
  - `db_url` / transaction-per-test rollback fixture (~40 lines, in-repo `conftest.py`, replaces
    `pytest-django`) — each integration test runs inside a transaction that is rolled back at
    teardown, so tests never depend on execution order and the schema is migrated once per test
    session (`alembic upgrade head` against the CI Postgres service container), not once per test.
    Rate-limiter and concurrency tests are the deliberate exception: the limiter's counter table
    write is on a dedicated `AUTOCOMMIT` connection (tech-stack.md § Rate limiting) and is therefore
    **not** rolled back by the per-test transaction — these tests clean up explicitly (`DELETE FROM
    rate_limit_counter WHERE scope = :scope` in teardown) rather than relying on rollback.
  - `live_server` fixture (~25 lines, uvicorn in a background thread, OS-assigned port) — used only
    by the tests that need real concurrent connections (AC-003, AC-011, the anonymous-flood
    assertion) or a real Playwright target.
  - Query-counter fixture (`before_cursor_execute` SQLAlchemy listener) — used by every AC-018 test
    and by the "which tables were touched" assertions in the append-only tests.
  - **Injectable clock (`api/app/core/clock.py`), decided at /build (implementation-plan.md T-005):**
    every time-dependent code path (OTP expiry, session idle/absolute expiry, rate-limiter window
    truncation, the limiter/session sweep boundaries) calls `core.clock.now()` rather than the
    stdlib directly; tests monkeypatch it to a controllable value with an `advance(delta)` helper.
    This is specifically why **five** rows cost milliseconds, not real elapsed time, and are
    always-run (§6) rather than nightly: TC-SEC-011b (OTP 72h expiry), TC-SEC-014 (session idle
    window), TC-SEC-015 (session absolute expiry), and the two sweep-boundary cases TC-SEC-037/038 —
    superseding rev 1's "if a clock-injection library is adopted" framing, it now has.
  - **Separately, three other rows are always-run for a non-clock reason** and must not be
    attributed to clock injection (test-review F2, rev 2 wrongly grouped all eight together):
    **TC-SEC-024** has no clock or volume cost at all — it asserts that a limiter-counter increment
    on a dedicated AUTOCOMMIT connection survives the surrounding request's rollback, a property with
    no time dimension; **TC-API-019** has no time dimension either — it forces five complaint-number
    collisions via a monkeypatched generator, not a wait; **TC-API-054** simulates a stalled backend
    response via mocking, not a real elapsed wait. All three were already fast and deterministic and
    needed no clock-injection change to become always-run.
  - Fixture-factory pattern for test data: `make_clerk(username=None, is_admin=False,
    must_change_password=False)`, `make_complaint(status="new", ...)`, `make_session(user, ...)` —
    each returns a fully-valid row with sensible synthetic defaults so a test only overrides the
    field it cares about (no hand-rolled INSERTs in test bodies).
  - Seeded accounts for integration/E2E: one admin clerk (`admin_test`) and one regular clerk
    (`clerk_test`), created via the same `bootstrap-admin --from-env`/fixture path documented in
    project-testing.md, never via a raw SQL insert, so the tests exercise the real account-creation
    code path.
- **Test DB strategy:** per-test transaction rollback is the default (fast, isolated, no fixture
  teardown ordering bugs). Fresh-schema-per-run is used once per CI job (`alembic upgrade head` from
  empty, then `alembic check`), not per test — matching tech-stack.md's CI pipeline
  (`pytest` → `alembic upgrade head` → `alembic check`).
- **429-under-parallel-load mechanism:** `concurrent.futures.ThreadPoolExecutor` firing >20 (AC-011)
  or 20 (AC-003) requests at effectively the same time against the `live_server` fixture and a real
  Postgres connection pool; the assertion counts exact successes/rejections across the whole burst,
  never a sequential loop (tech-stack.md explicitly rejects sequential loops as evidence for either
  AC).
- **"No SQL executed" assertions:** the `before_cursor_execute` listener fixture collects every
  statement's target table for the duration of one request; AC-018 tests assert `"complaint" not in
  touched_tables`; the `GET /api/session` anonymous-variant test asserts `touched_tables == []`
  (zero statements, not merely zero `complaint` statements — api-contract.md's stronger claim for
  that one route).
- **Frontend:** Vitest + Testing Library against `jsdom`, mocking `fetch`/the API client — no real
  network calls in component tests.
- **E2E:** Playwright for Python (not Playwright-for-Node/Cypress — tech-stack.md's boringness
  argument), driving the real `next build` static export served with the same host rewrite rule
  used in production, against the real FastAPI app. Runs on PRs to `main` and before `/release`, not
  on every commit (see §5).

## 4. Test data strategy

- **Synthetic only, always.** No production data ever reaches dev, CI, or a fixture — restated
  from tech-stack.md § Database and .claude/project-testing.md § Test data strategy; this is
  non-negotiable and has no exception for testing convenience.
- Fixture factories (above) generate plausible-but-fake citizen names/phone numbers per test; no
  fixture ever reuses a real village name or a real Indian phone-number range that could be
  mistaken for genuine PII.
- Seeded accounts: `admin_test` (admin clerk) and `clerk_test` (regular clerk), created through the
  bootstrap/account-creation code path (never a raw INSERT), so their passwords go through the same
  Argon2/OTP logic as production accounts.
- CI Postgres is a fresh service container per workflow run; local dev Postgres is reset by
  re-running Alembic migrations, per project-testing.md.

## 5. Environments

- **Local:** developer machine, `uv run uvicorn ... --reload` + `npm run dev`, local Postgres —
  unit + integration + component tests run here on demand; E2E requires `playwright install
  chromium` once plus the exported frontend served locally with the host rewrite rule.
- **CI (GitHub Actions):** two jobs (API, frontend) run on every push/PR — unit, integration,
  component, lint, typecheck, `pip-audit`/`npm audit`, `alembic check`, `selfcheck`. A third,
  **E2E job** runs only on PRs to `main` and before a release (tech-stack.md § CI), not on every
  commit, because Playwright + a full stack boot is materially slower than the other two jobs.
- **No staging environment exists** (project-config.md `base_url_staging: not applicable`) — frontend
  PR previews are not in the API's CORS allow-list per project-testing.md § Known limitations, so
  no test suite targets a preview deploy; the E2E job runs against a locally-composed
  frontend+API+Postgres stack, not a hosted environment.
- **Production:** human-only deploy; the only test-shaped activity against production is the
  `/release` post-deploy smoke check (one Playwright spec: login → log a complaint → public lookup)
  run by a human, per tech-stack.md § Hosting, and the `/release` IP-derivation/HTTPS-redirect
  verification steps — neither is part of the CI suite and neither is repeated here as a test-case
  ID; they are release-gate activities, out of test-cases.md's scope.

## 6. Always-run regression suite and its wall-clock budget

**Definition — runs on every commit/PR. This is an exact, grep-counted per-level breakdown against
test-cases.md's "Reg" column (142 total rows after TC-SEC-039), not an estimate:**

| Level | Total rows | Always-run (Y) | Nightly (N) | Release-gate (R) |
|---|---|---|---|---|
| Unit | 10 | 10 | 0 | 0 |
| Integration — API | 59 | 59 | 0 | 0 |
| Integration — DB | 4 | 3 | 1 (TC-DB-004) | 0 |
| Integration — Security | 40 | 38 | 1 (TC-SEC-031) | 1 (**TC-SEC-012**) |
| Component | 14 | 14 | 0 | 0 |
| E2E | 6 | 0 | 0 | 6 |
| A11y | 6 | 4 | 0 | 2 (TC-A11Y-005/006) |
| Perf | 2 | 0 | 0 | 2 |
| Design review | 1 | 0 | 0 | 1 |
| **Total** | **142** | **128** | **2** | **12** |

**TC-SEC-012 is release-gate, not always-run** (its own row has always carried `Reg: R` — it asserts
`/docs`/`/redoc`/`/openapi.json` return 404 under "production-shaped config", which only exists at
release time). Rev 2's enumeration summed to 124 because it (a) omitted the 4 always-run a11y cases
from the always-run list entirely and (b) implicitly counted TC-SEC-012 as if the "100 of 102"
figure already excluded it, when in fact it only excluded the 2 nightly cases — this is corrected
here (arch F17).

- Target ≤ 30 s for the 10 unit cases, ≤ 7 min for the 100 always-run integration cases (59 API +
  3 DB + 38 security) against the CI Postgres service container, ≤ 30 s for the 14 component cases,
  negligible added time for the 4 always-run a11y cases (component-level checks, not a separate
  browser boot). **Estimated total wall-clock for the 128-case always-run set: ~8 minutes**,
  comfortably inside the ≤ 15 minute ceiling this role's brief requires.
- Of the 128 always-run cases, 5 are always-run **specifically because of clock injection**
  (`api/app/core/clock.py`): TC-SEC-011b/014/015 and the two sweep-boundary cases TC-SEC-037/038.
  A separate 3 are always-run for **non-clock** deterministic reasons (see §3): TC-SEC-024,
  TC-API-019, TC-API-054. The remaining 12 brand-new security-assertion rows added in rev 2
  (TC-SEC-025..030, 032..036) and the 1 added in rev 3 (TC-SEC-039) were fast and deterministic from
  the start — none needed a clock or cost reclassification to be always-run.
  (E2E is intentionally excluded from "every commit" — see below — which is what keeps this under
  budget.)

**Runs nightly (not every commit) — exactly 2 cases, each kept nightly for a stated non-clock cost
reason, not a real-time-wait reason:**
- **TC-DB-004** — a ~500-request unauthenticated burst; the cost is sheer request volume (5-25x every
  other concurrency case in the suite), not elapsed clock time, so clock injection does not reduce it.
- **TC-SEC-031** — the four real-gunicorn IP-derivation cases (SEC-T21); each boots the actual
  production gunicorn CMD as a subprocess (worker fork + socket bind, ~1-3 s/case), materially
  slower than the in-thread `live_server` fixture every other integration test uses.
- Both re-run on-demand whenever their change-impact trigger fires (regression-plan.md §2), and both
  run before `/release` regardless of the nightly schedule.

**Runs before `/release` — exactly 12 cases (E2E + deployed-artifact + config-review checks):**
- All 6 Playwright E2E specs (TC-E2E-001..006, ~2-4 min locally against a composed stack).
- **TC-SEC-012** (`/docs`/`/redoc`/`/openapi.json` 404 under production-shaped config).
- TC-A11Y-005/006 (JS-disabled `<noscript>`, 320px viewport — need the real exported build).
- TC-PERF-001/002 (3G-throttled Playwright timing).
- TC-DESIGN-001 (retention-job code/config review).
- The CSP-hash/security-header assertions against a deployed preview (assertion 18/19 in
  tech-stack.md) — these need a real deployed artifact and cannot run in the PR pipeline at all
  (no staging environment); they are a `/release`-time check, not a CI-pipeline test-case ID and are
  not counted in the 142 (see §8).

**Change-impact mapping (shared with the planner):** a change touching —
- `core/validation`, `services/complaints`, or the `complaint`/`*_history` tables → run the full
  integration set plus the complaints-module unit tests.
- `core/client_ip.py`, the rate-limit middleware, or `rate_limit_counter` → run the AC-003/AC-011
  concurrency tests plus the anonymous-flood assertion (17), even if the diff looks unrelated —
  these are the tests most likely to pass by construction and fail only under real concurrency.
- `services/accounts`, `core/auth`, or the `session`/`clerk_account` tables → run every AC-001/
  AC-017/AC-019 test plus the session-lifecycle and CSRF assertions.
- Any route's `response_model` or the PII-classification table in api-contract.md → run the full
  "no name/phone in list response" and "detail scope covers this route" assertions (security
  assertion 20 and the `detail`/`search`/`write` limiter-scope tests).
- Any screen in screen-inventory.md → run the E2E spec that names that screen, plus the Vitest
  component tests for that screen.

## 7. Browser QA plan (references the `app-qa` skill; does not duplicate it)

The global `app-qa` skill (`/smoke-test`, `/full-test`, `/regression-test`) reads
`.claude/project-testing.md` as its brief and covers, against a running deployment or local stack:
- **Smoke:** the four "Critical workflows" listed in project-testing.md (log a complaint, public
  lookup, status update, admin reset) — a fast, shallow pass.
- **Full test:** every screen in screen-inventory.md and every state named there (loading, empty,
  error, unauthorized, 404, responsive at 320px/900px breakpoints, a11y focus order) — this is
  where the visual/responsive/a11y confirmation that a Playwright script would be expensive to
  assert pixel-by-pixel actually happens, driven by an agent operating a real browser.
- **Regression:** re-runs the smoke set plus any workflow named in a recent change's change-impact
  mapping (§6 above).

This test strategy does not re-specify what `app-qa` does; test-cases.md's E2E section is the
**automated, CI-integrated** subset (6 Playwright specs) that must pass on every PR to `main`, while
`app-qa` is the **human/agent-in-the-loop** exploratory layer run on demand or before a release. The
two are complementary, not duplicative: Playwright proves the contract holds; `app-qa` catches what
no assertion was written for.

## 8. Deferred, and why

- **NFR-006 (hosting cost-appropriateness)** — assessed at architecture/deployment review per its
  own Verification column; no product test case exists or should exist for "is this cheap enough."
- **NFR-007 (99% uptime)** — deferred to post-launch `/healthz` pinger monitoring; not a pre-release
  AC, per product-requirements.md's own Verification column.
- **AC-013 (12-month retention)** — verified by design/code review (no deletion job exists) plus one
  simulated-window integration test, never a live 12-month wait, exactly as the AC itself specifies.
- **Load/performance testing beyond AC-010's 3-second target and AC-011's concurrency check** — no
  k6/Locust suite exists; tech-stack.md explicitly rejects a load-testing platform for this
  question's scale ("`concurrent.futures` suffices"). AC-010's 3-second target is asserted once in
  the E2E suite against a locally-throttled network profile (Playwright's built-in network
  throttling to a 3G-equivalent profile), not against a dedicated load-testing tool.
- **Threat-model items marked `accepted` or `n-a`** (threat-model.md rev 3 §Counts: 18 accepted, 10
  n-a) are not given test cases — an `accepted` risk is a recorded business decision, not a
  contract to prove; an `n-a` item has no attack surface to test. Only `mitigated` threats that map
  to a testable control get a TC-SEC-* case (see test-cases.md §Security).
- **CSP hash-set / deployed-header assertions (tech-stack.md assertions 3, 18, 19)** — deferred to
  `/release`, because they require a deployed static-site artifact; no staging environment exists
  to run them against pre-release.
- **Browser/device matrix beyond the two responsive breakpoints named in screen-inventory.md
  (320px, 900px)** — no cross-browser grid is specified anywhere in the inputs; deferred to the
  `app-qa` full-test pass, which can be pointed at additional viewports on request, not hardcoded
  into the CI Playwright suite.

## 9. Traceability matrix — AC → test-case IDs

**Total ACs in acceptance-criteria.md: 19 (AC-001 through AC-019). Covered: 19/19 (100%).**
Full per-case detail is in test-cases.md; this table names, per AC, at least one covering case ID
and the level(s) used.

| AC | Covering TC IDs (see test-cases.md) | Level(s) |
|---|---|---|
| AC-001 | TC-API-001, TC-API-002, TC-API-003, TC-SEC-001, TC-E2E-001 | integration, security, E2E |
| AC-002 | TC-UNIT-001..004, TC-API-010..016, TC-E2E-002 | unit, integration, E2E |
| AC-003 | TC-API-020, TC-API-021 | integration (concurrency) |
| AC-004 | TC-UNIT-005, TC-API-030..034, TC-E2E-003 | unit, integration, E2E |
| AC-005 | TC-API-040..046 | integration |
| AC-006 | TC-API-050..055, TC-SEC-002, TC-E2E-004 | integration, security, E2E |
| AC-007 | TC-API-056, TC-E2E-004 | integration, E2E |
| AC-008 | TC-API-060..063 | integration |
| AC-009 | TC-API-070..072 | integration |
| AC-010 | TC-PERF-001, TC-PERF-002 | E2E/perf |
| AC-011 | TC-SEC-003 | security (concurrency — >20 parallel lookups from one IP, real `live_server`) |
| AC-012 | TC-API-090, TC-API-091 | integration |
| AC-013 | TC-DESIGN-001, TC-API-092 | design review, integration |
| AC-014 | TC-API-100 | integration |
| AC-015 | TC-SEC-004, TC-SEC-005 | security (integration) |
| AC-016 | TC-SEC-006, TC-A11Y-001 (UI absence) | security, a11y/UI |
| AC-017 | TC-API-110..119, TC-SEC-007, TC-E2E-005 | integration, security, E2E |
| AC-018 | TC-DB-001, TC-DB-002, TC-COMP-001, TC-E2E-006 | integration (query-counter), component, E2E |
| AC-019 | TC-API-130..132 | integration |

## 10. Self-audit

- Every AC (19/19) has ≥1 covering test case at a named level with an observable expected result —
  confirmed in test-cases.md.
- Every business rule named in project-testing.md § "Business rules worth checking" has a covering
  case: BR-015/FR-020 → TC-DB-001/002; BR-002 → TC-API-030/031; BR-005/NFR-009 → TC-API-050/TC-SEC-002;
  NFR-005/AC-011 parallel → TC-SEC-003; FR-011/FR-014 append-only → TC-SEC-*/TC-API-100; AC-015
  both directions → TC-SEC-004/005; CSRF 403 → TC-SEC-008/009; password length 12 / OTP 72h single-use
  → TC-API-113/114, TC-SEC-010/011.
- The always-run regression set (§6) is **128 of 142 cases**, an exact per-level count (not an
  estimate), at ~8 minutes wall-clock, under the 15-minute ceiling.
- Every ID in §9's traceability matrix has been grep-verified to exist as a row in test-cases.md
  (previous rev's TC-API-080/081/120 were fabricated and have been repointed to real rows: AC-011 →
  TC-SEC-003; AC-018 → TC-DB-001/002, TC-COMP-001, TC-E2E-006).
- Every architecture-named assertion (SEC-T21..T33, REL-T25, ARCH-T32/T33, PERF-T26/T27,
  backend-architecture.md §13) maps to an existing or new TC row — see test-cases.md's
  "Architecture assertion → TC id(s)" table — **plus the middleware-registration-order assertion**
  (tech-stack.md assertion 16 / backend-architecture.md §2 rows 1-6), previously unmapped, now
  **TC-SEC-039**.
- Voluntary password change (**ADR-014 Q4**) and name/phone search (**ADR-014 Q3**) were accepted at
  GATE_4; no test in this document or test-cases.md carries a "pending human confirmation" caveat for
  either. (These ADR-014 questions are unrelated to architecture/open-questions.md's own OQ-9/OQ-10,
  which cover detail-view auditing and log retention respectively — neither of those OQ numbers is
  used in this document.)
- a11y and security cases exist for every public route (`/`) and every auth path (`/login`,
  `/change-password`, `/accounts`) — see test-cases.md §A11Y and §Security.
- No test case exists solely to prove "a button was clicked" — every case in test-cases.md states
  the business outcome (an AC/BR/threat-model id) it proves.
