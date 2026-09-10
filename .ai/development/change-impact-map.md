# Change-Impact Map — panchayat-complaint-tracker

rev 4 (2026-09-10), rework after test-architect's/architecture-reviewer's rev-3 findings (implementation-
plan.md/milestones.md F21-F25 and the M3/M4 milestone-wording fix); no content change to this file's own
rows was required by that pass — rev bump only, for consistency with the companion documents. Rev 3
(2026-09-10) reworked after architecture-reviewer's CHANGES_REQUIRED on rev 2 (F16, F19): the
`app/main.py` middleware-assembly row now cites **TC-SEC-039** by id (backend-architecture.md §2 rows
1-6 middleware-registration-order assertion) in place of the un-ID'd "middleware-order assertion" text;
both rows naming `TC-COMP-001..010` widened to `TC-COMP-001..014` (test-cases.md rev 3 has 14 component
cases, not 10). Extends
regression-plan.md §2 (test-architect's change-impact map) with the build-time artifacts (tasks,
reviewers, docs) that must also move when an area changes. Use this table before starting any change
after M1; do not run only the tests a diff "looks like" it touches.

| Changed area | Tests to run (beyond the always-run set) | Task(s) it lives in | Reviewer(s) |
|---|---|---|---|
| `core/validation`, `services/complaints/*`, `complaint`/`complaint_status_history`/`complaint_edit_history` tables or migrations | Full complaints integration set: TC-API-010..021, 030..034, 060..072, 100; TC-UNIT-001..006; TC-SEC-006/018 | T-009, T-018, T-019, T-020 | code-reviewer + security-reviewer (append-only guard) |
| `core/client_ip.py`, `app/worker.py`, rate-limit middleware, `rate_limit_counter` table/migration | TC-SEC-031 (SEC-T21, all 4 cases, nightly), TC-SEC-003/016/020/021/022, TC-API-020/021, TC-DB-004, TC-SEC-037 (PERF-T26) | T-025, T-026, T-040 | security-reviewer (mandatory — this is the highest-rework area in the whole architecture) |
| `app/main.py` middleware assembly (TrustedHost, security headers, CORS, body-size limit) | TC-SEC-027, TC-SEC-028, **TC-SEC-039** (middleware-registration-order, backend-architecture.md §2 rows 1-6) [A-F16] | T-006 (rows 4-6, provisional), T-010a (rows 1-3 + final order) | security-reviewer (mandatory — ordering is security-critical; a silent reorder is a bypass, not a crash) |
| `services/accounts.py`, `services/auth.py`, `session`/`clerk_account` tables | TC-API-001..004, 110..132; TC-SEC-001/007/011/011b/014/015/016/017/025/026/029/030 | T-006, T-007, T-008, **T-009** (TC-API-004 lives here [A-F14]), T-029, T-033, T-035, T-036 | security-reviewer |
| Any route's `response_model` or the per-route PII-classification table (api-contract.md Conventions / backend-architecture.md §5) | TC-API-046/051/072, TC-SEC-002/020/021/022, TC-SEC-033 (SEC-T29) | whichever router task owns the route + T-026 (limiter scope wiring), T-038 (account-route completion) | security-reviewer — a new route with no PII-table row must be treated as a finding, not merged |
| `error-catalog.md` codes or the exception handlers that raise them | TC-API-011..015, 031, 055/056, 112/113; every `TC-SEC-*` row whose expected result names a status/code | T-031 | code-reviewer |
| Any screen in screen-inventory.md | The E2E spec naming that screen (TC-E2E-001..006) + Vitest tests for that screen (**TC-COMP-001..014** [A-F19]) + the matching TC-A11Y case | T-012/013/014/022/023/029/034/036 (per screen) + T-047 (a11y) | ux-reviewer + accessibility-reviewer |
| CSP/security-headers middleware or `headers.config.json` | TC-SEC-012, the release-gate CSP assertions (run at `/release`, not in CI) | T-042 | security-reviewer |
| Alembic migrations (any) | `alembic upgrade head` + `alembic check` (CI step) + the full integration set for the changed table | T-003 + whichever task added the table/column | code-reviewer (migration read line-by-line, per coding-guidelines.md § Migrations) |
| `app/cli/*` (bootstrap-admin, unlock-account, reset-admin-password) | TC-API-130..132; manual CLI run per infrastructure.md §12 | T-007, T-035 | security-reviewer (these are the only non-HTTP entry points into the account model) |
| `web/src/lib/api.ts`, `src/lib/csrf.ts`, `src/lib/auth.ts` | **TC-COMP-001..014** [A-F19] (all — every screen calls this module), TC-E2E-001..006 | T-011 | ux-reviewer + security-reviewer (CSRF header attachment) |
| `.claude/project-config.md` / `.claude/project-testing.md` | Re-run the exact command each changed line references; if `start:` changes, re-run SEC-T21 (worker-class behaviour) | — (config, not code) | whichever role owns the phase currently running |
| A new dependency (either `pyproject.toml` or `package.json`) | `pip-audit`/`npm audit` + `npm audit signatures`, full CI | any task | **two-eyes mandatory** (dependency-strategy.md §6) — never approved by its own author, needs an FR/NFR/BR/AC citation |

## Requirement/contract-level impact (not file-level)

| If this changes | These are affected |
|---|---|
| A business rule (business-rules.md) | acceptance-criteria.md's covering AC, the service enforcing it (solution-architecture.md § "Where each business rule is enforced" table), the TC ids in test-cases.md's traceability row, and the task that built that service |
| The DB schema (schema.md) | A new Alembic migration (additive-only), the SQLAlchemy model, the repository, `alembic check` in CI, and — if a new PII-bearing column — the per-route PII classification table and its limiter scope |
| The API contract (api-contract.md) | The router + schema + generated `api-types.ts` (CI fails until regenerated) + every screen consuming that route + the E2E spec if the screen's E2E-tested flow uses it |
| A UX screen (screen-inventory.md) | The island/page component, its Vitest tests, its E2E spec (if named in test-cases.md), its a11y case, and `src/strings/en.ts` if wording changed |
| A dependency budget (dependency-strategy.md §3) | Requires an ADR before merge — this is not a `/build`-level decision |

## Notes

- This map is a superset add-on to regression-plan.md §2; where the two name different test-case IDs
  for the same area, regression-plan.md is authoritative (test-architect owns test scope) and this
  file's "task/reviewer" columns are the addition.
- Security-sensitive areas (rows 1-3, 8 above) always get a security-reviewer pass regardless of diff
  size — see coding-guidelines.md § Security-sensitive modules.
