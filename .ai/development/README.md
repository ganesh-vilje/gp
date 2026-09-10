# development — index

Produced in `/plan` (rev 4, 2026-09-10, reworked after test-architect's CHANGES_REQUIRED and
architecture-reviewer's advisories on rev 3 — the M3/M4 milestone critical-workflow-set wording fix and
findings F21-F25; rev 3 fixed F14-F20), before GATE_6. Nothing under this folder is application code; it is the plan
`/build` executes. See `.ai/project-state/project-state.md` for phase/gate status.

| Document | What it contains |
|---|---|
| `implementation-plan.md` | Repository layout (`api/`, `web/`), dependency graph, the clock-injection decision, the ADR-014 scope note (T-036/T-037 correct rev 1's OQ-9/OQ-10 mislabeling — both were accepted at GATE_4, not open questions), the full task table (T-001…T-049 plus inserted `T-003a`/`T-006a`/`T-010a`) with files/modules, ACs/BRs/ADRs delivered, TC-id evidence, done-conditions, size/risk, git workflow, and self-audit |
| `milestones.md` | Five milestones (M1 walking skeleton → M5 deploy readiness), each with its task range, human demo criterion, exit tests, and what joins the always-run regression set from that point on |
| `coding-guidelines.md` | Layering rules (ADR-015), error-envelope discipline (ADR-018), never-log-list, validation/typing rules, naming, module-size/forbidden patterns, migration review rule, commit format, and what "evidence" a `/build` task must paste |
| `change-impact-map.md` | Which tests, tasks and reviewers must run/engage when a given module, screen, contract, or dependency changes — extends test-architect's regression-plan.md §2 with the build-time (task/reviewer) dimension |
| `technical-debt.md` | What `/plan` deliberately defers: the (resolved, not deferred) clock-injection decision, documentation-only advisories owned by other roles (now including the tech-stack.md/technology-comparison.md start-command wording cleanup), items blocked on a human answer (OQ-2, OQ-3, and the real OQ-10 log-retention confirmation), the real OQ-9 (detail-view audit, default "no") restated as a closed scope decision, and the two named architectural fallbacks (CSP `unsafe-inline`, byte-budget) taken only if their triggering spike/gate fails |

## Related, not owned by this phase

- `.ai/testing/test-strategy.md`, `test-cases.md` (**142 cases**, 128 always-run [2 nightly, 12
  release-gate] ≤8 min), `regression-plan.md` — test-architect's
  artifacts; this phase's task table cites their TC ids but does not restate or re-derive them.
- `.ai/architecture/*.md`, `.ai/security/threat-model.md`, `.ai/database/*.md`, `.ai/api/*.md` —
  binding inputs; `/plan` does not re-decide anything they already fixed.
- `.claude/project-config.md`, `.claude/project-testing.md` — filled in at this phase (source roots,
  the `start:` command per ADR-023, endpoint paths, fixture description); read by every later phase
  and by the global `app-qa` skill.
