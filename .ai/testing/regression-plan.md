# Regression Plan — panchayat-complaint-tracker

rev 3 (2026-09-10) — rework after rev 2 GATE_6 reviewer findings: totals realigned to **142** rows
(TC-SEC-039, the new middleware-registration-order case, added to §2's CORS/route-method
change-impact row — arch F16); the critical-workflow subset estimate is restated at a single figure,
**~4-5 minutes** (test-review F1 — this document previously said ~3-4 min while milestones.md said
~4-5 min; ~4-5 min is now the one figure this plan states, for the planner to align milestones.md
against). rev 2's changes (totals/estimates realigned with test-cases.md's then-actual 141 rows and
test-strategy.md's ~8-minute always-run estimate; the clock-dependent flaky-test note updated now
that `core/clock.py` — implementation-plan.md T-005 — is decided; TC-SEC-025..038 added to the
relevant change-impact rows) stand unchanged except where superseded above. Companion to
test-strategy.md §6 and test-cases.md. This document is the
change-impact map shared with the implementation-planner: given a diff touching area X, which
test-case IDs must be run beyond the standard always-run set, and what the critical-workflow set is
that never gets skipped.

## 1. Critical-workflow set (always run, every commit/PR)

This is the "always-run regression suite" referenced by test-strategy.md §6. It is the minimum
proof that the four workflows named in `.claude/project-testing.md` § Critical workflows still
work, plus every security/authz assertion that has no cheaper substitute.

| Workflow | Covering test-case IDs | Why it can never be skipped |
|---|---|---|
| Log a complaint | TC-API-010..018, TC-UNIT-001..004, TC-COMP-001 | Core deliverable (US-002/US-003); a regression here blocks every clerk |
| Public lookup | TC-API-050..056, TC-DB-001/002, TC-SEC-002, TC-COMP-001 | The only citizen-facing feature (US-006/US-007); a PII leak here is the single worst possible regression (BR-005/NFR-009) |
| Status update | TC-API-030..034, TC-UNIT-005/006 | Core deliverable (US-004); illegal-transition regressions corrupt the audit trail's meaning |
| Admin account management | TC-API-110..119, TC-SEC-007 | The only path to onboard/recover a clerk (US-014/015/016); both-direction authz is the highest-value security check per dollar spent |
| Deny-by-default authz | TC-SEC-004, TC-SEC-005 | Parametrised over the whole route table (threat #41/#44) — the cheapest test to add for a brand-new route, and the one most likely to be silently broken by a route added without thinking about auth |
| CSRF | TC-SEC-008, TC-SEC-009 | Applies to every write and to the public lookup; threat #8/#9 |
| Rate limiting under parallel load | TC-SEC-003, TC-API-020/021 | The only proof AC-003/AC-011 hold that a sequential loop cannot provide — explicitly the highest-value concurrency test in the suite |
| Append-only audit trail | TC-SEC-006, TC-SEC-018, TC-API-100 | Protects the system's core deliverable, "an auditable record" (business objective) |
| Session/password lifecycle correctness (arch-named assertions) | TC-SEC-025, TC-SEC-026, TC-SEC-029, TC-SEC-030 | OTP hash-destruction, session-revoke scope, wrong-current-password handling, and logout/rotation are all gateway-to-every-asset controls (threat-model A3) with no cheaper substitute now that clock injection makes them always-run cost-free |

**Estimated wall-clock for this critical-workflow subset alone: ~4-5 minutes** (a proper subset of
the ~8-minute always-run total in test-strategy.md §6 — the remaining always-run cases add breadth,
not a different workflow). This is the one figure this document states for the subset; report it to
the implementation-planner so milestones.md's own ~4-5 minute mention (previously misaligned with
this document's stale ~3-4 minute figure) stays consistent with it.

## 2. Change-impact map

| Changed area (file/module) | Must additionally run | Reason |
|---|---|---|
| `core/validation`, `services/complaints`, `complaint`/`complaint_status_history`/`complaint_edit_history` tables or their migrations | Full integration set for complaints: TC-API-010..021, TC-API-030..034, TC-API-060..072, TC-API-100, TC-UNIT-001..006, TC-SEC-006/018 | Every business rule that constrains this data lives in these tests; a schema or service change here risks BR-001/002/006/007/008/011/012/014 simultaneously |
| `core/client_ip.py`, rate-limit middleware, `rate_limit_counter` table/migration | TC-SEC-003, TC-SEC-020/021/022, TC-API-020/021, TC-DB-004, TC-SEC-024, TC-SEC-031 (real-gunicorn IP derivation), TC-SEC-032/034 (throttle-event dedup, write/search scopes), TC-SEC-037 (counter-sweep boundary) | These are the tests most likely to pass by construction (unit-level) and fail only under real concurrency or real header spoofing (threat #60) — the highest-regret area to under-test |
| `services/accounts`, `core/auth`, `session`/`clerk_account` tables | TC-API-001..004, TC-API-110..132, TC-SEC-001/007/011/011b/014/015/016/017, TC-SEC-025/026/029/030 (OTP hash destruction, session-revoke scope, wrong-current-password, logout/rotation), TC-SEC-038 (session-sweep boundary) | Session, password, and OTP logic is the gateway to every other asset (threat-model A3) |
| `core/clock.py` (the injectable clock itself) | Every clock-dependent case: TC-SEC-011b/014/015/037/038, TC-API-019/054 | A clock regression here silently breaks every boundary test that now relies on `advance()` instead of a real wait — re-run the full clock-dependent set, not a sample |
| Any route's `response_model` or the per-route PII-classification table in api-contract.md | TC-API-046/051/072, TC-SEC-002/020/021/022 | A new or changed route that skips this table fails SEC-T29-equivalent coverage silently (rev 4 finding pattern: `/activity` and `/search` were missed exactly this way) |
| `error-catalog.md` codes or the exception handlers that raise them | TC-API-011..015, TC-API-031, TC-API-055/056, TC-API-112/113, all `TC-SEC-*` rows whose expected result names an HTTP status/code | The envelope shape and code set is the frontend's only integration point; a silent code change breaks client-side `switch` logic that unit/component tests won't catch |
| Any screen in screen-inventory.md | The E2E spec naming that screen (TC-E2E-001..006) + the Vitest component tests for that screen (TC-COMP-001..010) + the matching A11Y case | UI-level regressions are invisible to API-level tests |
| CSP/security-headers middleware or the static-site header config | TC-SEC-012, plus the release-gate CSP assertions (tech-stack.md assertions 3/18/19 — run at `/release`, not in this suite) | Header regressions are silent to every functional test |
| Alembic migrations (any) | `alembic upgrade head` + `alembic check` (CI pipeline step, not a TC-ID) + the full integration set for whatever table changed | Migration drift is invisible to tests that only run against an already-migrated DB |
| Bootstrap/CLI scripts (`bootstrap-admin`, `unlock-account`, `reset-admin-password`) | TC-API-130..132 | These are the only non-HTTP entry points into the account model |
| CORS config, route-method table, `main.py`'s `create_app()` middleware registration, or the request-body-size middleware | TC-SEC-027 (GET/POST-only + CORS), TC-SEC-028 (413 body limit), **TC-SEC-039** (middleware registration order, backend-architecture.md §2 rows 1-6) | A route or CORS-config change that widens allowed methods/origins/body size, or a middleware reordered in `create_app()`, is otherwise invisible to every functional test — a CSRF check that silently starts running before the session loader, or an authz check before CSRF, would pass every other test in the suite |
| Structured logging config/formatters | TC-SEC-036 | The only test that inspects raw log output rather than the `security_event` table (TC-SEC-023) for PII/secret leakage |

## 3. Flaky-test handling

- **Formerly clock-dependent tests** (TC-SEC-011b, TC-SEC-014, TC-SEC-015, TC-SEC-024, TC-SEC-037,
  TC-SEC-038, TC-API-019, TC-API-054) now run against the injectable clock (`api/app/core/clock.py`,
  implementation-plan.md T-005) — `advance(delta)` moves the clock in milliseconds, no real elapsed
  time, so they are always-run, not nightly (superseding rev 1's framing). A failure here is never
  muted or re-run — it is treated as a real bug (an exact boundary — 72h, 30-60min, 9h, or a
  sweep-rollover point — either holds or it doesn't; there is no timing fuzziness left to blame).
- **Concurrency tests** (TC-API-020/021, TC-SEC-003, TC-DB-004, TC-SEC-031/032/034) run against a real
  `live_server` (or, for TC-SEC-031, a real gunicorn subprocess) + real Postgres by design
  (test-strategy.md §1) specifically so they are deterministic under load, not flaky approximations.
  A failure here is never re-run silently — it is escalated as a possible real race condition,
  because these are exactly the tests the architecture review flagged as needing real concurrency
  evidence (ARCH-F1/F2, AC-003/AC-011). TC-DB-004 and TC-SEC-031 remain nightly for cost, not
  flakiness, reasons (see test-cases.md rows for the concrete cost stated on each).
- **E2E tests** (Playwright) are the one category permitted a single automatic retry in CI (network/
  browser-launch flake), consistent with standard Playwright practice; a test that needs a second
  retry to pass is filed as a real defect, not re-muted.
- **No test is ever skipped/xfailed to make CI green** without a linked, dated tracking note in the
  test file naming the reason and an owner — this is a process rule for `/build`, not a technical
  control, and is stated here so the implementation-planner can hold it as a task-acceptance gate.

## 4. What never runs outside `local`

Per `.claude/project-testing.md` § Destructive-operation policy: any bulk-delete, migration reset,
or `unlock-account`/`bootstrap-admin --from-env` exercise runs only against the `local` Postgres
instance. No test suite touches `staging` (none exists) or `prod`; the only prod-adjacent activity
is the human-run `/release` smoke spec (TC-E2E-001-equivalent, login → log a complaint → public
lookup) and the IP-derivation/HTTPS-redirect verification steps named in tech-stack.md § Rate
limiting — both release-gate activities, not part of this regression plan's CI-triggered set.
