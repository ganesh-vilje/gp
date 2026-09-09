# Architecture Decision Records

Every human gate and every major internal decision gets an ADR. Never delete an
ADR; supersede it with a new one and mark the old `Status: superseded by ADR-00n`.

## ADR-000 — Template
Date: YYYY-MM-DD | Gate: — | Status: accepted | superseded | rejected
Decision:
Alternatives considered:
Reasoning:
Risks & mitigations:
Human notes:

## ADR-001 — Requirements approved (GATE_1)
Date: 2026-09-09 | Gate: GATE_1 | Status: accepted
Decision: Approve requirements rev 4 (.ai/requirements/) as the product baseline
for the panchayat-complaint-tracker MVP: single-panchayat pilot, clerk-mediated
complaint intake, auto-generated unique complaint number, status updates with
notes and full audit history, public unauthenticated status lookup by exact
number, two clerk permission levels (regular / admin clerk), minimal PII (name,
phone, complaint text; no government IDs).
Alternatives considered: (a) show citizen name/phone on the public page —
rejected for privacy (Q-001); (b) allow direct New→Rejected for duplicates —
rejected, all complaints pass through In Progress (Q-002 sub-question); (c)
single clerk role with out-of-band account admin — superseded by human decision
H1 (admin clerk role); (d) photo upload, SMS/WhatsApp, multi-tenant,
self-service filing in MVP — deferred to Future scope.
Reasoning: Both internal reviewers (product-reviewer rev 3, requirements-qa-
reviewer rev 4) returned APPROVED after 3 rework loops; 20 FRs, 11 NFRs, 17
user stories, 19 ACs, 16 business rules, all traced. Remaining findings are
medium/low advisories carried forward to the analyst for the next revision.
Risks & mitigations: Q-001/Q-002 accepted as defaults rather than deliberated —
easy to revisit before GATE_3 (data model) if the panchayat disagrees. Admin
self-lockout (Q-015) mitigated by recommending a second admin account (BR-013).
Human notes: "yes, accept defaults" — human also decided H1 (one admin clerk
creates accounts and resets passwords) and H2 (blank/malformed public lookup
input shows "Enter a valid complaint number", no lookup) during rework.
