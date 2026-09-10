# Test Plan — panchayat-complaint-tracker

rev 3 (2026-09-10) — rework after rev 2 GATE_6 reviewer findings: this document now states the
total/always-run/nightly/release-gate figures explicitly (§1a below — test-cases.md previously
claimed this document restated them when it did not, arch F17); §1's always-run row separates the
5 clock-injection-driven boundary cases from the 3 separately-fast deterministic reclassifications
(test-review F2). rev 2's changes (nightly row narrowed to the two cost-based cases, TC-DB-004/
TC-SEC-031, now that the injectable clock moved every clock-dependent case into always-run;
always-run target time restated at ~8 minutes) stand unchanged. Operational companion to
test-strategy.md (what/why) and test-cases.md (the cases themselves) and regression-plan.md (what
re-runs on a change). This document is "what runs when, in which environment, on whose data, and
who owns it."

## 1a. Totals (restated identically from test-strategy.md §1/§6 and test-cases.md's Coverage summary)

**142 total test cases: 128 always-run, 2 nightly (TC-DB-004, TC-SEC-031), 12 release-gate**
(TC-E2E-001..006, TC-SEC-012, TC-A11Y-005/006, TC-PERF-001/002, TC-DESIGN-001) — by level: unit 10/10
always-run; integration-API 59/59; integration-DB 3/4 (1 nightly); integration-security 38/40
(1 nightly, 1 release-gate); component 14/14; E2E 0/6 (all release-gate); a11y 4/6 (2 release-gate);
perf 0/2 (release-gate); design review 0/1 (release-gate). See test-strategy.md §6 for the full
per-level table.

## 1. What runs when

| Trigger | Commands (from project-config.md, unchanged) | Scope | Target time |
|---|---|---|---|
| Every local save (developer-optional) | `uv run pytest -m "not e2e and not integration" -k <touched module>` | Unit tests near the edit | seconds |
| Every push / PR (CI, required check) | `run_test_unit` → `run_test_integration` → `run_test_web` → `lint`/`lint_web` → `typecheck`/`typecheck_web` → `db_check_drift` → `security_audit`/`security_audit_web` → `deploy_check` | Always-run regression set (test-strategy.md §6, 128 of 142 cases, ~8 min; includes both the clock-injection-driven boundary cases — TC-SEC-011b/014/015/037/038, always-run because `core/clock.py` removed their real-wait cost — and the separately-fast deterministic reclassifications TC-SEC-024/TC-API-019/TC-API-054, which needed no clock change to be always-run) | ≤ 15 min total including lint/typecheck/audit |
| PR targeting `main`, and before `/release` | `run_test_e2e` (additional CI job) | 6 Playwright specs (TC-E2E-001..006) | ~2-4 min |
| Nightly scheduled CI run | Cost-based nightly set (not clock-based — see test-cases.md rows for the stated reason on each): TC-DB-004 (500-request burst volume), TC-SEC-031 (real-gunicorn IP-derivation subprocess boot), plus a full `security_audit`/`security_audit_web` re-run against current advisory databases | Cost-isolation and dependency-freshness checks | best-effort, no hard ceiling |
| `/release`, human-run | `app-qa` `/smoke-test` or `/full-test`; the deployed-artifact checks (CSP hash set, security headers on the live preview, IP-derivation/HTTPS-redirect verification per tech-stack.md § Rate limiting); the one human-run Playwright production smoke spec (login → log a complaint → public lookup) | Deployed-artifact and production-adjacent evidence | manual, part of the release checklist |
| On demand | `app-qa` `/regression-test` | Smoke set + whatever the current change-impact map (regression-plan.md §2) names | varies |

`test_all` (`uv run pytest && npm run test`) is the single local command a developer runs before
opening a PR; it does not include `-m e2e` (that needs the exported build + a running API, per
project-config.md's own note on `run_test_e2e`'s preconditions).

## 2. Environments

| Environment | Purpose | Data | Who touches it |
|---|---|---|---|
| `local` | Development, all four test levels, destructive operations permitted | Synthetic fixtures + factory-generated data; Postgres reset via Alembic re-run | developer |
| `test` (CI service containers) | Unit + integration + component tests, one fresh Postgres container per workflow run | Synthetic only, created fresh per run, discarded after | CI (GitHub Actions) |
| `staging` | **Does not exist** (project-config.md: "No staging environment at launch") | n/a | n/a — frontend PR previews exist but are outside the API's CORS allow-list and are not a test target |
| `prod` | Live pilot | Real citizen/clerk data | human-only; the only test activity is the `/release` smoke spec and IP/HTTPS verification, run by a human, never by CI |

No test suite at any level ever points at `prod`. No production data is ever copied into `local`,
`test`, or any fixture (tech-stack.md § Database; project-testing.md § Test data strategy) —
restated here as a plan-level constraint, not just a strategy-level one.

## 3. Test data policy

- **Synthetic only.** Every complaint, clerk account, and session in every environment below `prod`
  is generated by a fixture factory (`make_clerk`, `make_complaint`, `make_session` — named in
  test-strategy.md §3) or created through the real bootstrap/account-creation code path. No test
  ever hand-writes a plausible-looking real name, real phone number range, or real village name.
- **Seeded accounts (local + CI only):** one admin clerk and one regular clerk, created via
  `bootstrap-admin`/the fixture equivalent — never a raw SQL INSERT — so their passwords/OTPs go
  through the same Argon2/validation code path a real account would.
- **Postgres reset:** local — re-run Alembic migrations (project-testing.md); CI — a fresh service
  container per workflow run, migrated from empty (`alembic upgrade head`), then `alembic check`
  for drift.
- **No secrets in fixtures or test files.** Credentials used by tests are either generated at test
  time (bootstrap/OTP flow) or read from `.env.test.local` (gitignored) per project-testing.md §
  Auth strategy — never committed.

## 4. Owners

| Responsibility | Owner |
|---|---|
| Test strategy, test-case authorship, this test plan | test-architect (this document's author) |
| Implementing the fixtures/tests described here | whichever engineer implements the task that names the test-case ID in its acceptance evidence (assigned in implementation-plan.md, not here) |
| CI pipeline configuration (the commands in §1) | already fixed at GATE_2 in `.claude/project-config.md`; changes to the commands themselves are a technology-stack change, not a test-plan change |
| Injectable clock (`core/clock.py`) and its fixture surface (`advance(delta)`) | decided at `/build` (implementation-plan.md T-005); already adopted — the nightly clock-dependent suite from rev 1 has been retired (test-strategy.md §3/§6) |
| `app-qa` skill invocations (`/smoke-test`, `/full-test`, `/regression-test`) | whoever runs `/test-app` or `/release` — human or orchestrating agent, per the global org's command set |
| Release-gate evidence (CSP headers, IP derivation, production smoke spec) | human, per `.claude/project-config.md` `production_deploy: human-only` |

## 5. Traceability

See test-strategy.md §9 for the full AC → test-case-ID matrix (19/19 ACs covered) and
regression-plan.md §2 for the change-impact map. This plan does not duplicate either; it states
only the scheduling, environment, data, and ownership facts layered on top of them.
