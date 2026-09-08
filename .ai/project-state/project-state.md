# Project State
# Machine-read by the orchestrator and by hooks. Keep the `key: value` lines
# exactly in this shape — gate-guard.js parses `gates_passed:`.

project_name: panchayat-complaint-tracker
created: 2026-09-08
current_phase: requirements
gates_passed:
internal_approvals:
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
| requirements    | in_progress | .ai/requirements/        |       |
| tech-stack      | pending     | .ai/technology/          |       |
| ux              | pending     | .ai/ux/, .ai/design/     |       |
| architecture    | pending     | .ai/architecture/        |       |
| plan            | pending     | .ai/development/         |       |
| build           | pending     | (application code)       |       |
| qa              | pending     | .ai/testing/, .ai/qa/    |       |
| release         | pending     | .ai/release/             |       |

## Review log
<!-- one line per verdict: date | phase | rev | reviewer | verdict | crit/high/med/low -->

## Known risks (summary — details in risks.md)

## Technical debt (summary — details in risks.md)
