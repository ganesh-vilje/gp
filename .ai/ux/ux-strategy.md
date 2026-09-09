# UX Strategy — Panchayat Complaint Tracker

## Design drivers
Every decision in this and the sibling documents cites one of these.

| ID | Driver | Evidence |
|----|--------|----------|
| U1 | Citizens use low-end Android phones, possibly on slow (3G-equivalent) networks, with varying literacy and possibly English as a second language. | Personas; NFR-001; A5 |
| U2 | Clerks (1–5) work from a modest shared/office desktop or laptop, are comfortable with basic web forms, and log a handful of complaints per day — not high-volume data entry. | Personas; A6 |
| U3 | Error cost is real but not catastrophic; the true cost is *lost trust* (a citizen given wrong status, a clerk unsure if a note was saved) and *lost audit trail* — not financial loss. Every write must be traceable, nothing is ever silently lost or deleted. | Business objective ("auditable record"); BR-008, BR-011, FR-011, FR-014 |
| U4 | The public page must be usable with zero training, no login, and an exact-match single field (BR-004) — plain language is mandatory, not a nicety. | FR-008–FR-010, BR-004 |
| U5 | Frontend performance budget: ≤120 KB gzipped first-load JS on the public route, static export, no CSS framework, no component library, no icon package, no web fonts. | tech-stack.md Frontend section, NFR-001 |
| U6 | Security-sensitive moments (one-time password shown once, cookies required, session expiry) must be explained in plain language, not technical jargon, because clerks are not IT staff. | BR-016; tech-stack CSRF/session sections |
| U7 | Very small user population (≤6 accounts, two roles). No need for enterprise patterns: no dashboards, no bulk actions, no complex permission matrices. | A12; Personas |
| U8 | The public page requires JavaScript (human decision H4/Q8) and a first-party cookie (CSRF seed); both failure modes need a friendly, actionable message rather than a blank page. | tech-stack Frontend/CSRF sections |
| U9 | Single-language MVP, English default (A5, open — Q-004). Plain language matters more given literacy/first-language variance (U1). | A5 |
| U10 | No delete of any record, ever (BR-008) — the UI must never imply an undo/delete affordance for complaints. | BR-008, BR-003 |

## Principles
1. **Plain language over jargon**, everywhere, including error and security messages (U1, U4, U6).
2. **One clear primary action per screen** — the citizen has one field and one button; the clerk's screens each foreground a single next step (U2, U7).
3. **Prevent, don't just detect** — restrict choices to what is valid (e.g., only legal next statuses selectable) rather than accepting anything and rejecting after submit (U3, BR-002).
4. **Nothing disappears silently** — every save is visibly confirmed, every history is visible, no delete affordance exists anywhere (U3, U10, BR-008/BR-011).
5. **Visible state, always** — every request shows loading, then success or a specific, actionable error (NFR-011), never a blank or frozen screen.
6. **Design within the budget** — plain HTML controls, system fonts, hand-written CSS, no dependency the performance budget can't afford (U5).
7. **Small system, small surface** — resist dashboard/admin-panel conventions that don't fit 1–5 users and a few hundred daily lookups (U7).

## Per-role goals
- **Citizen:** confirm a complaint's status in under a few seconds, on any device/connection, without needing to understand what went wrong if something does.
- **Clerk (regular):** log a complaint and hand over its number fast; find and update any complaint without ambiguity about what's allowed; trust that history is preserved even under concurrent edits.
- **Admin clerk:** create accounts and reset passwords confidently and rarely, hand over the one-time password without fear of losing it, and be nudged away from the one failure mode unique to their role (self-lockout with no second admin).

## Out of scope for UX (per requirements)
No self-service citizen filing, no SMS/WhatsApp, no photo upload, no multi-language UI, no dashboards/analytics, no bulk export — these are Future scope and are not designed here.
