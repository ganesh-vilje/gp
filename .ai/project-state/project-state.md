# Project State
# Machine-read by the orchestrator and by hooks. Keep the `key: value` lines
# exactly in this shape — gate-guard.js parses `gates_passed:`.

project_name: panchayat-complaint-tracker
created: 2026-09-08
current_phase: ux
gates_passed: GATE_1 GATE_2
internal_approvals: requirements: rev 4, product-reviewer, requirements-qa-reviewer; tech-stack: rev 5 (FastAPI + Next.js per H3/H4), architecture-reviewer, security-reviewer, cost-reviewer
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
| ux              | in_progress | .ai/ux/, .ai/design/     |       |
| architecture    | pending     | .ai/architecture/        |       |
| plan            | pending     | .ai/development/         |       |
| build           | pending     | (application code)       |       |
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

## Known risks (summary — details in risks.md)

## Technical debt (summary — details in risks.md)
