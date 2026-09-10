# Milestones — panchayat-complaint-tracker

rev 4 (2026-09-10), rework after test-architect's CHANGES_REQUIRED on rev 3 (one blocking finding: M3
wrongly claimed regression-plan.md §1's full critical-workflow set was live end to end, when Admin
account management doesn't land until M4/T-033 — fixed below, M4 is now the first milestone to make
that claim) and architecture-reviewer's advisories F21/F25 (M2's TC-API-046 citation corrected;
implementation-plan.md's T-009 dependency/AC-019 fixes are reflected here where cited). Companion to
implementation-plan.md (task detail, rev 4) and test-strategy.md/regression-plan.md rev 3
(evidence sources). Five milestones; each ends with something a human can run and see, per CLAUDE.md.
TC ids updated to test-cases.md rev 3 (**142 cases**; 128 always-run / 2 nightly / 12 release-gate; new
id **TC-SEC-039** — middleware-registration-order assertion, backend-architecture.md §2 rows 1-6). M1's
wording corrected to reflect that the middleware chain is assembled in two steps, not fully wired at
once (F15, see below).

## M1 — Walking skeleton

**Goal:** prove the core idea end-to-end — a clerk can log a complaint and a citizen can look up its
status — on the real stack (FastAPI + Postgres + Next.js static export), locally, with every row of
the ADR-007 middleware chain (TrustedHost/headers/CORS/body-limit + session-loader/CSRF/authz) **live
from day one**: rows 4-6 (session-loader/CSRF/authz) are registered by T-006 in a provisional order,
rows 1-3 (TrustedHost, headers, CORS/body-limit) are inserted by T-010a, which also asserts the final
exact 6-row sequence (TC-SEC-039) — no route in M1 is ever reachable without the full chain enforcing
it, but the *exact order* is only pinned down once T-010a lands [A-F15, corrects rev 2's "assembled
from day one" wording, which read as if all six rows were wired in one step].

**Tasks:** T-001, T-002, T-003, T-003a, T-004, T-005, T-006, T-007, T-006a, T-008, T-009, T-010,
T-010a, T-011 … T-017 (implementation-plan.md).

**Human demo criterion:**
1. `uv run bootstrap-admin` (interactive) creates the first admin clerk.
2. `uv run uvicorn app.main:app --reload --port 8000 --no-proxy-headers` + `npm run dev` (both from
   project-config.md).
3. Open `http://localhost:3000/login`, sign in.
4. Open `/complaints`, fill the new-complaint form (name, phone, description), submit — a complaint
   number is shown on screen before navigating away.
5. Open `http://localhost:3000/` in a private/incognito window (no session), enter that number,
   submit — status, date logged and a public status message appear; no name or phone anywhere in the
   page or in the network tab's response body.

**Exit tests:** `run_test_unit` + `run_test_integration` green, specifically TC-API-001..021,
TC-API-050..056, TC-DB-001..003, TC-UNIT-001..010, TC-COMP-001..005/011, TC-SEC-006/024/027/028,
**TC-SEC-039** [A-F16] (middleware-registration-order, T-010a); `run_test_web` green. (TC-SEC-030 moved
to M3/T-029 — see implementation-plan.md's task table [A-F14].) E2E ids named against the relevant M1
screens (TC-E2E-001/002/004/006) are
proven by the human-demo steps above, not by an automated harness yet — the Playwright harness itself
is built at T-045 (M5); every early UI task's `e2e:` evidence cell says "deferred to T-045."

**Always-run regression from here on:** log-a-complaint (TC-API-010..018), public lookup
(TC-API-050..056, TC-DB-001/002), append-only guard + no-delete-capability (TC-SEC-018, TC-SEC-006),
deny-by-default on the routes that exist so far (subset of TC-SEC-004/005), the middleware-order
assertion (**TC-SEC-039**) + CORS/body-limit (TC-SEC-027/028) — the full critical-workflow set (regression-plan.md §1)
is only complete once M2/M3 land, but these stay green from M1 onward and are never allowed to
regress.

## M2 — Complaint lifecycle & search

**Goal:** the Complaints screen is feature-complete for a clerk's daily work: status transitions with
history, 7-day edit window, merged activity timeline, list/filter/search with pagination.

**Tasks:** T-018 … T-024.

**Human demo criterion:**
1. Open a logged complaint, change its status New → In Progress with a note — the note and the
   change appear in the Activity tab with a timestamp.
2. Attempt New → Closed directly (e.g. by temporarily editing the DOM/using the API docs in dev) —
   rejected with an explicit error; status unchanged.
3. Edit the citizen's phone number (within 7 days) — the old and new values both appear in Activity.
4. On the list, filter by status, and jump directly to a complaint by its exact number.
5. With >25 complaints seeded, "Load more" fetches the next page without re-fetching or reordering
   already-shown rows.

**Exit tests:** TC-UNIT-005/006, TC-API-030..034, TC-API-060..063/070..072, **TC-API-090** [A-F14, moved
from T-009], TC-API-040..045 [A-F21 — TC-API-046 needs the `q` field, deferred to T-037/M4], TC-API-100, TC-COMP-006/007/012. TC-E2E-003 (status-rejection spec) is
proven by hand per the demo steps above;
automated in T-045.

**Always-run regression from here on (adds to M1's set):** status-update (TC-API-030..034,
TC-UNIT-005/006), append-only audit trail (TC-SEC-006/018 — guard already built in M1, now exercised
by real writes), list/search (TC-API-040..045 [A-F21]). Regression-plan.md §1's "Log a complaint", "Status
update" and "Append-only audit trail" rows are now fully live.

## M3 — Security & session hardening

**Goal:** every mechanism the architecture treats as load-bearing for a government-adjacent, PII-
holding system is real, not a stub: correct client-IP derivation under the real worker class, the
full rate limiter (all seven scopes), session idle/absolute/rotation/revoke-scope, CSRF on every
unsafe method, OTP single-use by credential destruction, deny-by-default over the M3 route table.

**Tasks:** T-025 … T-032.

**Human demo criterion:**
1. From a script, send 25 lookups in one minute from one source — the 21st onward is `429` with
   `Retry-After`, and forged `X-Forwarded-For`/`Fly-Client-IP` headers from an untrusted peer do not
   change which bucket the requests land in (TC-SEC-031, SEC-T21 case 1 — run nightly, re-run on
   demand before this demo since it needs the real gunicorn CMD, not `live_server`).
2. Log in with a freshly issued one-time password, then attempt to log in with the *same* OTP again —
   the second attempt fails with the generic "incorrect username or password," not a distinguishing
   message (TC-SEC-025).
3. Call any authenticated route with no cookie — `401`; call an admin-only route as a regular clerk —
   `403`; both via a direct HTTP request, not just via the hidden UI.
4. Advance the injected clock past the idle window in a test run (not real elapsed time) — the
   session is rejected and revoked on the next request (TC-SEC-014, TC-SEC-038).
5. Log in again from a second device for the same user, then separately change the password — the
   first login's session survives the second login (only the presented session was revoked) but both
   are gone after the password change (TC-SEC-026).

**Exit tests:** TC-SEC-031 (nightly), TC-SEC-003/008/009/011/011b/014/015/016/017/020/021/022/023/025/
026/029/030/032/033/034/035, TC-SEC-004/005, TC-API-116.

**Always-run regression from here on (adds to M1/M2's set):** rate limiting under parallel load
(TC-SEC-003, TC-API-020/021), CSRF (TC-SEC-008/009), deny-by-default over the M3 route table
(TC-SEC-004/005), session revoke-scope and OTP destruction (TC-SEC-025/026) — regression-plan.md §1's
critical-workflow set is live at M3 for every row **except** "Admin account management"
(TC-API-110..119, TC-SEC-007), which doesn't land until M4/T-033 [T-F-blocking]. The ~4-5 minutes
wall-clock figure regression-plan.md §1 states is for the *complete* set (all rows); it applies once
M4 lands (see M4 below), not to this M3 subset alone. TC-SEC-031 and TC-DB-004 remain nightly-only
(cost, not clock — see implementation-plan.md § Clock injection decision).

## M4 — Admin accounts + ADR-014 additions

**Goal:** the only path to onboard or recover a clerk account works, both directions of the
admin/regular permission split are proven over the complete 15-route table, and the two ADR-014
UX additions accepted at GATE_4 — voluntary password change (Q4) and name/phone search (Q3) — ship
as ordinary tasks, not conditional ones.

**Tasks:** T-033 … T-038.

**Human demo criterion:**
1. As the admin clerk, create a new regular-clerk account — a one-time password is shown once, with
   a mandatory "I have recorded this password" acknowledgment before the dialog can be dismissed.
2. Log in as that new clerk with the OTP — forced to `/change-password` immediately, no nav available
   except logout.
3. As the regular clerk, attempt to open `/accounts` by typed URL — an explicit "you don't have
   permission" message, not a silent redirect; a direct API call to the same effect is `403`.
4. As an already-authenticated clerk, use the nav's "Change password" to change password voluntarily,
   including a wrong-current-password error that leaves the session usable (TC-SEC-029).
5. Search the complaints list by a citizen's name or phone number.

**Exit tests:** TC-API-110..119, **TC-API-131** [A-F14, moved from T-007], TC-SEC-010/029, TC-COMP-010/013, TC-API-046, TC-COMP-008,
TC-SEC-034 (SEC-T30 account-route cases, completed here per T-038).

**Always-run regression from here on:** admin account management (TC-API-110..119, TC-SEC-007) and
the two ADR-014 additions (TC-API-046, TC-COMP-008/013, TC-SEC-029) join the permanent
critical-workflow set (regression-plan.md §1). With "Admin account management" now live, **M4 is the
first milestone at which regression-plan.md §1's full critical-workflow set is live end to end**, at
the ~4-5 minutes wall-clock figure regression-plan.md §1 states for that complete set [fixes M3's
premature claim, test-architect blocking finding]. The full 15-route deny-by-default sweep (TC-SEC-004/
005) is now complete, not partial.

## M5 — Observability, resilience & deploy readiness

**Goal:** the system is deployable and operable as designed — CSP without `unsafe-inline` (or a
recorded, deliberate fallback), bounded sweeps, the full CI pipeline including E2E, the exact
production start command (bound to the literal port 8080, not an unset `$PORT` — infrastructure.md:101)
and `selfcheck` gate, and the accessibility/performance budgets the architecture set are measured, not
assumed.

**Tasks:** T-039 … T-049.

**Human demo criterion:**
1. `docker build` + `docker run` the API image with production-shaped env vars **in the CI job** (no Docker on the build machine — GATE_6 Q1), published on
   `8080`; `selfcheck` passes; deliberately unset one required variable — `selfcheck` refuses to
   start; `/docs`, `/redoc`, `/openapi.json` all 404 (TC-SEC-012).
2. A full CI run (API job + frontend job + E2E job) is green on a real PR, including the ≤120KB
   gzipped byte-budget gate on `/` and the generated CSP with no `unsafe-inline` (or the recorded
   fallback, stated as such, not silently taken).
3. The full regression suite (**142** total cases: 128 always-run + 2 nightly + 12 release-gate) runs
   its 128-case always-run subset in ≤8 minutes wall-clock (test-cases.md Coverage summary,
   test-strategy.md §6).
4. An accessibility pass confirms focus order, live-region announcements and touch targets across all
   six screens at 320px and 900px.
5. No log line, across a full login/OTP/validation-error request set, contains a password, OTP,
   session token, CSRF token, or citizen name/phone (TC-SEC-036).

**Exit tests:** the entire always-run set (test-strategy.md §6, 128 cases) plus TC-E2E-001..006,
TC-PERF-001/002, TC-A11Y-001..006, TC-DESIGN-001, TC-API-092, TC-SEC-036/037/038, TC-SEC-012.

**Always-run regression from here on:** everything (test-strategy.md §6's full always-run set, 128
cases, ≤8 min ceiling); E2E (6 specs) and CSP/header assertions become release-gate checks
(regression-plan.md §4), run before `/release`, not on every commit. TC-SEC-031 and TC-DB-004 stay
nightly, re-run on demand per regression-plan.md §2.

## Milestone → GATE_6 relationship

GATE_6 is the human checkpoint before any application code is written (CLAUDE.md). This plan is what
is presented at GATE_6; once approved, M1's first task (T-001) is the first `/build` action. No
milestone here is itself a human gate — the human gates that follow are `/release`'s own checklist
(domain attachment, backup destination, restore test, second-admin provisioning), which this plan
prepares for in T-049 but does not perform. **Neither ADR-014 addition (T-036/T-037) is a Gate-6
question** — both were already decided at GATE_4 (decisions.md ADR-014); see implementation-plan.md
§ "ADR-014 scope note" for the correction of rev 1's mislabeling. The Gate-6 question list itself
(open questions genuinely still open) is presented separately by the requirements/architecture roles,
not fabricated here.
