# Testing — index

Produced in `/plan`, before GATE_6, by the test-architect. No application code exists yet; these
documents constrain what the implementation plan may claim as "tested." (rev 3 rework after rev 2
GATE_6 reviewer findings: totals corrected to **142** rows — added **TC-SEC-039** for the previously
unmapped middleware-registration-order assertion (arch F16); the always-run/nightly/release-gate
breakdown is now an exact per-level count, **128/2/12** (arch F17); every wrong-meaning "OQ-9"/
"OQ-10" reference replaced with ADR-014 Q4/Q3 (arch F18); clock-injection-driven reclassifications
separated from other deterministic ones (test-review F2); regression-plan.md states a single
critical-workflow-subset figure, ~4-5 min (test-review F1). rev 2's rework — totals corrected to the
then-actual 141 rows, two fabricated traceability IDs repointed, 18 new IDs added (TC-COMP-011..014,
TC-SEC-025..038), and the always-run set updated for the injectable clock, `core/clock.py` — stands
unchanged except where superseded above.)

- **test-strategy.md** — pyramid and actual counts per level, level-selection rationale, tooling
  (reusing tech-stack.md; nothing new invented), test data strategy, environments, always-run
  regression suite and its exact per-level breakdown (128 of 142 cases, ~8 min), deferred items, and
  the full AC → test-case-ID traceability matrix (19/19 acceptance criteria covered, every ID
  grep-verified against test-cases.md).
- **test-cases.md** — 142 ID'd test cases (TC-UNIT-*, TC-API-*, TC-DB-*, TC-COMP-*, TC-E2E-*,
  TC-SEC-*, TC-A11Y-*, TC-PERF-*, TC-DESIGN-*), each with level, traces-to, preconditions, steps,
  expected result, and regression-set membership. Also includes the architecture-assertion → TC id
  mapping table (SEC-T21..T33/REL-T25/ARCH-T32/T33/PERF-T26/T27 plus the middleware-order assertion,
  backend-architecture.md §13/§2).
- **regression-plan.md** — the critical-workflow set that always runs, the change-impact map
  (diff area → test-case IDs to re-run), flaky-test handling, and what never runs outside `local`.
- **test-plan.md** — what runs when (every push, nightly, `/release`), environments (local/CI; no
  staging; prod is human-only), test data policy, and owners.

Reviewed against `.ai/requirements/acceptance-criteria.md`, `user-stories.md`, `business-rules.md`,
`product-requirements.md`; `.ai/api/api-contract.md`, `error-catalog.md`; `.ai/ux/screen-inventory.md`,
`user-flows.md`; `.ai/technology/tech-stack.md`; `.ai/architecture/review-advisories.md`;
`.ai/security/threat-model.md`; `.claude/project-config.md`, `.claude/project-testing.md`.
