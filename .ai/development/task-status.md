# Task Status — panchayat-complaint-tracker

Created 2026-09-10 by the /implement orchestrator from implementation-plan.md rev 4.
One row per task. `status` ∈ todo / in_progress / done / blocked. The orchestrator is the only writer.
Evidence = the orchestrator's own re-run summary line (not the developer's paste).

| id | milestone | status | branch | commit | evidence | reviewers |
|---|---|---|---|---|---|---|
| T-001 | M1 | done | build/M1 | 422bb48 | ruff/format/mypy clean; 11 unit tests pass; curl /healthz 200 (port 8001) | code-reviewer, security-reviewer (2 rounds) |
| T-002 | M1 | done | build/M1 | fce5c37 | npm ci/build/biome(8 files)/tsc clean; npm audit high=0; signatures verified | code-reviewer, security-reviewer (2 rounds) |
| T-003 | M1 | done | build/M1 | 0805ab2 | alembic up/down/up clean on PG16 both DBs; 7 tables, 2 enums, 12 indexes; ruff/mypy clean (alembic check → T-004) | code-reviewer, security-reviewer (2 rounds) |
| T-003a | M1 | done | build/M1 | 1db06ce | pytest -m integration 2 passed ×2 fresh processes; residual rows 0/0/0; unit 48 passed; ruff/format clean | code-reviewer |
| T-004 | M1 | done | build/M1 | b4e988e | integration 23 passed (TC-SEC-018, TC-SEC-006 ORM half), unit 54 passed, alembic check clean, ruff/format/mypy clean | code-reviewer, security-reviewer, performance-scalability-reviewer (3 rounds) |
| T-005 | M1 | done | build/M1 | 19862a9 | 48 unit tests pass (TC-UNIT-001..004, 007..010); ruff/format/mypy clean | code-reviewer, security-reviewer (2 rounds) |
| T-006 | M1 | done | build/M1 | 812252e | integration 32 passed, unit 116 passed, ruff/format/mypy clean, grep suite 6/6 | code-reviewer, security-reviewer (2 rounds) |
| T-007 | M1 | done | build/M1 | 2a4ed28 | integration 43 passed (TC-API-130/132), unit 117 passed, ruff/format/mypy clean, grep 6/6; manual bootstrap run + no-op | code-reviewer, security-reviewer (2 rounds) |
| T-006a | M1 | done | build/M1 | 8b8cbee | integration 48 passed ×2 (live_server, query_counter, seeded accounts), unit 119 passed, ruff/format/mypy clean, test DB empty | code-reviewer (2 rounds) |
| T-008 | M1 | done | build/M1 | 007b18a | integration 58 passed (TC-API-001..003, TC-SEC-001, ARCH-T33), unit 145 passed, ruff/format/mypy clean, grep 6/6 | code-reviewer, security-reviewer |
| T-009 | M1 | done | build/M1 | 23847c0 | unit 145 passed, integration 78 passed (3x rerun; 1 unrelated intermittent failure per run matches blocker B-001, not a T-009 regression), ruff/mypy clean | code-reviewer, security-reviewer (2 rounds) |
| T-010 | M1 | done | build/M1 | 69fbde7 | unit 145 passed, integration 98 passed (3x clean rerun), ruff/mypy clean | code-reviewer, security-reviewer (2 rounds) |
| T-010a | M1 | done | build/M1 | e0e644d | unit 168 passed, integration 98 passed (3x clean rerun), ruff/mypy clean | code-reviewer, security-reviewer (2 rounds) |
| T-011 | M1 | done | build/M1 | e7e68b2 | tsc --noEmit clean, biome ci clean, gen:api-types diff-free, npm ci clean (0 vulnerabilities) | code-reviewer, ux-reviewer (2 rounds), security-reviewer (2 rounds) |
| T-012 | M1 | done | build/M1 | 466a20e | vitest 4 passed, tsc --noEmit clean, biome ci clean | code-reviewer (2 rounds), ux-reviewer (2 rounds), accessibility-reviewer (2 rounds) |
| T-013 | M1 | done | build/M1 | c921c57 | vitest 18 passed, tsc --noEmit clean, biome ci clean | code-reviewer (2 rounds), ux-reviewer (2 rounds), accessibility-reviewer (3 rounds), security-reviewer (2 rounds) |
| T-014 | M1 | done | build/M1 | b37bf84 | vitest 21 passed, tsc --noEmit clean, biome ci clean, build 107kB First Load JS (no budget regression) | code-reviewer, ux-reviewer (2 rounds), accessibility-reviewer (2 rounds) |
| T-016 | M1 | done | build/M1 | 95fab1e | Green CI run on PR #1: https://github.com/ganesh-vilje/gp/actions/runs/35233692188 (api + web jobs both success). One earlier attempt hit blocker B-001's known intermittent auth race (1/98 integration tests, unrelated to this PR) — re-run came back clean. pip-audit 0 vulns, ruff/mypy/biome/tsc clean | code-reviewer, security-reviewer (2 rounds) |
| T-017 | M1 | done | build/M1 | c86be66 | `docker build -t api-test api/` exits 0 in CI with digest-pinned base image: https://github.com/ganesh-vilje/gp/actions/runs/35312544912 (api + web jobs both success). Base image digest resolved via a one-off CI lookup and hardcoded into api/Dockerfile per code review. Blocker B-001's intermittent auth race hit this PR's CI 5 separate times across T-016/T-017 (unrelated integration tests, always clears on rerun) — recommend fixing it before further work | code-reviewer, security-reviewer (2 rounds) |
| T-018 | M2 | done | build/M2 | 6dc6991 | unit 170 passed, ruff/mypy clean; integration flaky due to blocker B-001 (systemic, unrelated to this task's code — confirmed by 2 independent reviewers via sequential no-concurrency repro and DB-visibility check); this task's own tests correct and pass on a clean run | code-reviewer (2 rounds), security-reviewer (2 rounds) |
| T-019 | M2 | done | build/M2 | cbbe6bf | unit 174 passed, integration 111 passed (5x + 3x clean reruns), ruff/mypy clean | code-reviewer, security-reviewer (2 rounds) |
| T-020 | M2 | todo | | | | |
| T-021 | M2 | todo | | | | |
| T-022 | M2 | todo | | | | |
| T-023 | M2 | todo | | | | |
| T-024 | M2 | todo | | | | |
| T-025 | M3 | todo | | | | |
| T-026 | M3 | todo | | | | |
| T-027 | M3 | todo | | | | |
| T-028 | M3 | todo | | | | |
| T-029 | M3 | todo | | | | |
| T-030 | M3 | todo | | | | |
| T-031 | M3 | todo | | | | |
| T-032 | M3 | todo | | | | |
| T-033 | M4 | todo | | | | |
| T-034 | M4 | todo | | | | |
| T-035 | M4 | todo | | | | |
| T-036 | M4 | todo | | | | |
| T-037 | M4 | todo | | | | |
| T-038 | M4 | todo | | | | |
| T-039 | M5 | todo | | | | |
| T-040 | M5 | todo | | | | |
| T-041 | M5 | todo | | | | |
| T-042 | M5 | todo | | | | |
| T-043 | M5 | todo | | | | |
| T-044 | M5 | todo | | | | |
| T-045 | M5 | todo | | | | |
| T-046 | M5 | todo | | | | |
| T-047 | M5 | todo | | | | |
| T-048 | M5 | todo | | | | |
| T-049 | M5 | todo | | | | |

## Dependencies (from implementation-plan.md)

T-001 — · T-002 — · T-003 ← T-001 · T-003a ← T-001, T-003 · T-004 ← T-003, T-003a · T-005 ← T-001 ·
T-006 ← T-004, T-005 · T-007 ← T-006 · T-006a ← T-003a, T-004, T-006, T-007 · T-008 ← T-006, T-006a, T-007 ·
T-009 ← T-005, T-006, T-006a, T-008 · T-010 ← T-003, T-005, T-006, T-006a · T-010a ← T-001, T-006, T-009, T-010 ·
T-011 ← T-002, T-008, T-009, T-010, T-010a · T-012 ← T-011 · T-013 ← T-011, T-009 · T-014 ← T-011, T-010 ·
T-016 ← T-001, T-002, T-006a · T-017 ← T-001

## Notes

- T-004 note (from T-003a review): conftest.py is 331 lines because the three factories live in it; when T-004 rewrites them to ORM models, split them into `tests/factories.py`. `alembic check` becomes part of T-004's done-condition (models must match migration 0001).
- T-009/T-010 note (from T-006a review): the query_counter touched-table regex in tests/conftest.py scans raw statement text; strip string literals before the AC-018 zero-SQL assertions lean on it.
- T-010a follow-ups (from T-008 security review, APPROVED-with-notes): (1) unhandled-exception handler should log `type(exc).__name__` / traceback to stdout with the request id (never to the client), relying on the redaction filter; (2) add a logout test for the branch that mints a fresh `__Host-csrfseed` cookie and assert its HttpOnly/Secure/SameSite/Path; (3) assert no `Domain=` attribute on the session cookie.
- /implement invocation 2 (2026-09-11): T-004, T-006, T-007, T-006a, T-008 done. T-017 deferred until CI exists (T-016) — its only evidence is a Docker build in CI. Next: T-009.
- /implement invocation 1 (2026-09-10): T-001, T-002, T-003, T-003a, T-005 done. Next: T-004.

- No GitHub remote exists yet (GATE_6 Q2: human adds it before T-016). Until then tasks are committed
  directly on the milestone branch `build/M<n>`; per-task PRs start once the remote exists.
- Local DB: PostgreSQL 16 (project-config.md `db_start`); production/CI: 17.
