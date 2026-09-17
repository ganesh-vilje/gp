# Project State
# Machine-read by the orchestrator and by hooks. Keep the `key: value` lines
# exactly in this shape — gate-guard.js parses `gates_passed:`.

project_name: panchayat-complaint-tracker
created: 2026-09-08
current_phase: build
gates_passed: GATE_1 GATE_2 GATE_4 GATE_3 GATE_5 GATE_6
internal_approvals: requirements: rev 4, product-reviewer, requirements-qa-reviewer; tech-stack: rev 5 (FastAPI + Next.js per H3/H4), architecture-reviewer, security-reviewer, cost-reviewer; ux: rev 3, ux-reviewer, accessibility-reviewer, product-reviewer; architecture: rev 4 (cost-reviewer rev 1, performance-scalability-reviewer rev 2, reliability-reviewer rev 2, security-reviewer rev 4, architecture-reviewer rev 4); plan: rev 4 (architecture-reviewer rev 3, test-architect rev 4)
rework_count: 0

## Idea (verbatim from human)
I want to build a small tool where a panchayat clerk logs citizen complaints and citizens check status by complaint number

## Intake answers
- **Scale:** One panchayat pilot, 1-5 clerks, a few hundred citizens checking status.
- **Constraints:** None stated. Make reasonable assumptions: low-cost hosting, no stack preference, no fixed deadline.
- **Citizen channel:** Public web page on phone/desktop where the citizen types the complaint number. No SMS/WhatsApp in MVP.
- **Compliance / PII:** Keep it minimal, no special regime. Store only name, phone, and complaint text; no Aadhaar or government ID numbers.
- **Type:** Greenfield MVP (empty folder).
- **Core workflow (inferred from idea):** Clerk logs a complaint -> system issues a complaint number -> citizen looks up status by that number.

## Phase status
| Phase           | Status      | Artifact root            | Notes |
|-----------------|-------------|--------------------------|-------|
| requirements    | approved    | .ai/requirements/        | GATE_1 2026-09-09, rev 4 |
| tech-stack      | approved    | .ai/technology/          | GATE_2 2026-09-09, rev 5 (FastAPI JSON API + Next.js static export, Fly.io Mumbai per Q1) |
| ux              | approved    | .ai/ux/, .ai/design/     | GATE_4 2026-09-09, rev 3 |
| architecture    | approved    | .ai/architecture/, .ai/security/, .ai/database/, .ai/api/ | GATE_3+GATE_5 2026-09-10, rev 4 (3 rework loops) |
| plan            | approved    | .ai/development/, .ai/testing/ | GATE_6 2026-09-10, rev 4 (3 rework loops) |
| build           | in_progress | (application code)       | branch per milestone build/M1..M5, human merges to master |
| qa              | pending     | .ai/testing/, .ai/qa/    |       |
| release         | pending     | .ai/release/             |       |

## Review log
<!-- one line per verdict: date | phase | rev | reviewer | verdict | crit/high/med/low -->
2026-09-09 | requirements | rev 1 | product-reviewer | CHANGES_REQUIRED | 0/1/2/3
2026-09-09 | requirements | rev 1 | requirements-qa-reviewer | CHANGES_REQUIRED | 0/2/4/3
2026-09-09 | requirements | rev 2 | product-reviewer | CHANGES_REQUIRED | 0/1/0/2
2026-09-09 | requirements | rev 2 | requirements-qa-reviewer | CHANGES_REQUIRED | 0/1/3/3
2026-09-09 | requirements | rev 3 | product-reviewer | APPROVED | 0/0/2/1
2026-09-09 | requirements | rev 3 | requirements-qa-reviewer | CHANGES_REQUIRED | 0/1/2/1
2026-09-09 | requirements | rev 4 | requirements-qa-reviewer | APPROVED | 0/0/2/3
2026-09-09 | tech-stack | rev 1 | cost-reviewer | APPROVED | 0/0/2/2
2026-09-09 | tech-stack | rev 1 | architecture-reviewer | CHANGES_REQUIRED | 0/5/6/3
2026-09-09 | tech-stack | rev 1 | security-reviewer | CHANGES_REQUIRED | 0/9/4/1
2026-09-09 | tech-stack | rev 2 | cost-reviewer | APPROVED | 0/0/0/1
2026-09-09 | tech-stack | rev 2 | security-reviewer | CHANGES_REQUIRED | 0/1/4/2
2026-09-09 | tech-stack | rev 2 | architecture-reviewer | CHANGES_REQUIRED | 0/2/4/2
2026-09-09 | tech-stack | rev 3 | architecture-reviewer | APPROVED | 0/0/4/2
2026-09-09 | tech-stack | rev 3 | security-reviewer | APPROVED | 0/0/4/3
2026-09-09 | tech-stack | rev 3 | HUMAN (GATE_2) | CHANGES: "use FastAPI for the backend" | rev 4 rework
2026-09-09 | tech-stack | rev 3 | HUMAN (GATE_2) | CHANGES: "Use FastAPI as a JSON API with a separate Next.js frontend." | folded into rev 4
2026-09-09 | tech-stack | rev 4 | cost-reviewer | APPROVED | 0/0/1/1
2026-09-09 | tech-stack | rev 4 | architecture-reviewer | CHANGES_REQUIRED | 0/1/8/1
2026-09-09 | tech-stack | rev 4 | security-reviewer | CHANGES_REQUIRED | 0/3/4/2
2026-09-09 | tech-stack | rev 5 | cost-reviewer | APPROVED | 0/0/0/0
2026-09-09 | tech-stack | rev 5 | architecture-reviewer | APPROVED | 0/0/3/4
2026-09-09 | tech-stack | rev 5 | security-reviewer | APPROVED | 0/0/4/1
2026-09-09 | tech-stack | rev 5 | HUMAN (GATE_2) | APPROVED — "yes" + answers to Q1–Q9 (see ADR-002) | phase → ux
2026-09-09 | ux | rev 1 | product-reviewer | CHANGES_REQUIRED | 0/1/1/1
2026-09-09 | ux | rev 1 | ux-reviewer | CHANGES_REQUIRED | 0/3/1/2
2026-09-09 | ux | rev 1 | accessibility-reviewer | CHANGES_REQUIRED | 0/3/5/3
2026-09-09 | ux | rev 2 | ux-reviewer | APPROVED | 0/0/0/1
2026-09-09 | ux | rev 2 | product-reviewer | APPROVED | 0/0/1/0
2026-09-09 | ux | rev 2 | accessibility-reviewer | CHANGES_REQUIRED | 0/2/2/4
2026-09-09 | ux | rev 3 | accessibility-reviewer | APPROVED | 0/0/0/2
2026-09-09 | ux | rev 3 | HUMAN (GATE_4) | APPROVED — "yes" + answers Q1–Q5 (see ADR-014) | phase → architecture
2026-09-09 | architecture | rev 1 | cost-reviewer | APPROVED | 0/0/2/2
2026-09-09 | architecture | rev 1 | performance-scalability-reviewer | CHANGES_REQUIRED | 0/0/3/1
2026-09-09 | architecture | rev 1 | reliability-reviewer | CHANGES_REQUIRED | 0/2/4/1
2026-09-09 | architecture | rev 1 | security-reviewer | CHANGES_REQUIRED | 0/4/6/5
2026-09-09 | architecture | rev 1 | architecture-reviewer | CHANGES_REQUIRED | 0/4/6/3
2026-09-09 | architecture | rev 2 | performance-scalability-reviewer | APPROVED | 0/0/0/1
2026-09-09 | architecture | rev 2 | reliability-reviewer | APPROVED | 0/0/0/2
2026-09-09 | architecture | rev 2 | architecture-reviewer | CHANGES_REQUIRED | 0/3/3/2
2026-09-09 | architecture | rev 2 | security-reviewer | CHANGES_REQUIRED | 0/2/4/5
2026-09-09 | architecture | rev 3 | architecture-reviewer | CHANGES_REQUIRED | 0/1/3/1
2026-09-09 | architecture | rev 3 | security-reviewer | CHANGES_REQUIRED | 0/3/2/3
2026-09-10 | architecture | rev 4 | security-reviewer | APPROVED | 0/0/3/6
2026-09-10 | architecture | rev 4 | architecture-reviewer | APPROVED | 0/0/1/1
2026-09-10 | architecture | rev 4 | HUMAN (GATE_3+GATE_5) | APPROVED — "yes" + answers Q1–Q5 (see ADR-024) | phase → plan
2026-09-10 | plan | rev 1 | test-architect (review) | CHANGES_REQUIRED | 0/3/2/2
2026-09-10 | plan | rev 1 | architecture-reviewer | CHANGES_REQUIRED | 0/7/5/1
2026-09-10 | plan | rev 2 | test-architect (review) | APPROVED | 0/0/0/2
2026-09-10 | plan | rev 2 | architecture-reviewer | CHANGES_REQUIRED | 0/1/4/2
2026-09-10 | plan | rev 3 | architecture-reviewer | APPROVED | 0/0/2/3
2026-09-10 | plan | rev 3 | test-architect (review) | CHANGES_REQUIRED | 0/0/1/1
2026-09-10 | plan | rev 4 | test-architect (review) | APPROVED | 0/0/0/0
2026-09-10 | plan | rev 4 | HUMAN (GATE_6) | APPROVED — "yes" + answers Q1–Q4 (see ADR-025) | phase → build
2026-09-17 | build (T-009) | rev 1 | code-reviewer | APPROVED | 0/0/0/0
2026-09-17 | build (T-009) | rev 1 | security-reviewer | CHANGES_REQUIRED | 0/0/3/3
2026-09-17 | build (T-009) | rev 2 | security-reviewer | APPROVED (F7 new finding, fixed in rev 3) | 0/0/1/2
2026-09-17 | build (T-010) | rev 1 | code-reviewer | APPROVED | 0/0/0/0
2026-09-17 | build (T-010) | rev 1 | security-reviewer | CHANGES_REQUIRED | 0/0/2/3
2026-09-17 | build (T-010) | rev 2 | security-reviewer | APPROVED | 0/0/0/2
2026-09-17 | build (T-010a) | rev 1 | code-reviewer | APPROVED | 0/0/0/0
2026-09-17 | build (T-010a) | rev 1 | security-reviewer | CHANGES_REQUIRED | 0/2/6/4
2026-09-17 | build (T-010a) | rev 2 | security-reviewer | APPROVED | 0/0/0/4
2026-09-17 | build (T-011) | rev 1 | code-reviewer | APPROVED | 0/0/0/0
2026-09-17 | build (T-011) | rev 1 | ux-reviewer | CHANGES_REQUIRED (revised after clarification) | 0/0/1/0
2026-09-17 | build (T-011) | rev 1 | security-reviewer | CHANGES_REQUIRED | 0/0/2/3
2026-09-17 | build (T-011) | rev 2 | security-reviewer | APPROVED | 0/0/0/2
2026-09-17 | build (T-011) | rev 2 | ux-reviewer | APPROVED (doc-comment fix applied) | 0/0/0/0
2026-09-17 | build (T-012) | rev 1 | code-reviewer | CHANGES_REQUIRED | 0/2/0/0
2026-09-17 | build (T-012) | rev 1 | ux-reviewer | CHANGES_REQUIRED | 0/1/1/1
2026-09-17 | build (T-012) | rev 1 | accessibility-reviewer | CHANGES_REQUIRED | 0/1/2/2
2026-09-17 | build (T-012) | rev 2 | accessibility-reviewer | APPROVED | 0/0/0/1
2026-09-17 | build (T-012) | rev 2 | ux-reviewer | APPROVED | 0/0/0/1
2026-09-17 | build (T-012) | rev 2 | code-reviewer | APPROVED | 0/0/0/0
2026-09-17 | build (T-013) | rev 1 | code-reviewer | APPROVED | 0/0/1/0
2026-09-17 | build (T-013) | rev 1 | ux-reviewer | CHANGES_REQUIRED | 0/2/2/0
2026-09-17 | build (T-013) | rev 1 | accessibility-reviewer | CHANGES_REQUIRED | 0/1/0/1
2026-09-17 | build (T-013) | rev 1 | security-reviewer | APPROVED | 0/0/1/2
2026-09-17 | build (T-013) | rev 2 | code-reviewer | APPROVED | 0/0/0/0
2026-09-17 | build (T-013) | rev 2 | ux-reviewer | APPROVED | 0/0/0/0
2026-09-17 | build (T-013) | rev 2 | security-reviewer | APPROVED | 0/0/0/3
2026-09-17 | build (T-013) | rev 2 | accessibility-reviewer | CHANGES_REQUIRED | 0/1/1/1
2026-09-17 | build (T-013) | rev 3 | accessibility-reviewer | APPROVED | 0/0/0/0
2026-09-17 | build (T-014) | rev 1 | code-reviewer | APPROVED | 0/0/0/0
2026-09-17 | build (T-014) | rev 1 | ux-reviewer | CHANGES_REQUIRED | 0/3/3/1
2026-09-17 | build (T-014) | rev 1 | accessibility-reviewer | CHANGES_REQUIRED | 0/2/2/1
2026-09-17 | build (T-014) | rev 2 | accessibility-reviewer | APPROVED | 0/0/0/0
2026-09-17 | build (T-014) | rev 2 | ux-reviewer | APPROVED | 0/0/0/2

## Known risks (summary — details in risks.md)

## Technical debt (summary — details in risks.md)
