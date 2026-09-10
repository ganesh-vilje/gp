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
| T-004 | M1 | todo | | | | |
| T-005 | M1 | done | build/M1 | 19862a9 | 48 unit tests pass (TC-UNIT-001..004, 007..010); ruff/format/mypy clean | code-reviewer, security-reviewer (2 rounds) |
| T-006 | M1 | todo | | | | |
| T-007 | M1 | todo | | | | |
| T-006a | M1 | todo | | | | |
| T-008 | M1 | todo | | | | |
| T-009 | M1 | todo | | | | |
| T-010 | M1 | todo | | | | |
| T-010a | M1 | todo | | | | |
| T-011 | M1 | todo | | | | |
| T-012 | M1 | todo | | | | |
| T-013 | M1 | todo | | | | |
| T-014 | M1 | todo | | | | |
| T-016 | M1 | todo | | | | |
| T-017 | M1 | todo | | | | |
| T-018 | M2 | todo | | | | |
| T-019 | M2 | todo | | | | |
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
- /implement invocation 1 (2026-09-10): T-001, T-002, T-003, T-003a, T-005 done. Next: T-004.

- No GitHub remote exists yet (GATE_6 Q2: human adds it before T-016). Until then tasks are committed
  directly on the milestone branch `build/M<n>`; per-task PRs start once the remote exists.
- Local DB: PostgreSQL 16 (project-config.md `db_start`); production/CI: 17.
