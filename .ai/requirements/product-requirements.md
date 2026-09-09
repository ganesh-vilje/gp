# Panchayat Complaint Tracker

## Changelog
- rev 1 (2026-09-09) — initial draft from idea + intake answers. No prior findings to address (greenfield).
- rev 2 (2026-09-09) — rework pass 1/3, addressed reviewer findings:
  - P-F1: clarified that all clerks share full visibility of all complaints
    (MVP scope bullet, FR-007, Assumption A1 cross-reference); dropped
    "they've logged" wording.
  - P-F2: raised FR-007 priority to Must and stated its dependency
    relationship with FR-005.
  - P-F3: added FR-014 (edit-history for FR-012 changes) so citizen-detail
    edits are audited like status changes.
  - P-F4: added Q-013 (important) documenting the rate-limit threshold as an
    open question instead of an undefined "pending" reference.
  - P-F5: (see acceptance-criteria.md — AC-008 made deterministic).
  - P-F6: added Assumption A10 (password reset is a manual/admin action in
    MVP).
  - Q-F1: added BR-011 (concurrent status-update behavior) so the
    "auditable record" objective covers concurrent clerk edits.
  - Q-F2: (see acceptance-criteria.md — new AC-015, AC-016 for BR-003,
    BR-008).
  - Q-F3: added a Verification column to the NFR table; NFR-006/NFR-007 are
    explicitly marked as deferred to architecture/operational review rather
    than left without any verification path.
  - Q-F7: added BR-012 (phone number format/length validation). [Q2-F5: fixed
    this line in rev 3 — it previously misnamed the rule "BR-013".]
  - Q-F9: NFR-002 now cites the NFR-001 numeric target instead of
    "noticeable slowdown"; NFR-006 explicitly marked non-testable pre-
    architecture (see Verification column).
  - Q-002/Q-001/Q-003 (blocking) intentionally NOT answered — still open,
    per instruction not to resolve blocking human questions.
- rev 3 (2026-09-09) — rework pass 2/3:
  - P2-F1: named the provisioning actor in Personas; added FR-015 (clerk
    account provisioning/password reset via out-of-band operator action)
    and Q-014 (important — is a CLI/script acceptable for the pilot).
  - Q2-F1: (see acceptance-criteria.md — new AC-018 for blank/malformed
    public lookup input).
  - Q2-F2: added NFR-011 (in-flight/timeout behavior for all three core
    workflows); ACs updated accordingly (AC-002, AC-004, AC-006).
  - Q2-F3: (see acceptance-criteria.md — AC-005 empty-state bullet added).
  - Q2-F4: BR-010 no longer an orphan — cited in AC-011's verifies-list.
  - Q2-F5: fixed changelog typo referencing "BR-013" instead of BR-012 (see
    rev 2 entry above).
  - Q2-F6: added BR-014 (no enforced max length on name/description in MVP
    — deliberate, not an oversight).
  - Q2-F7: added a line to Q-002 in open-questions.md asking whether
    immediate New→Rejected transitions should be allowed for
    duplicate/invalid complaints, given BR-008's guidance.
  - P2-F2: standardized the public name/phone masking wording identically
    across the MVP scope bullet, FR-009, BR-005, and AC-006 (all now read:
    "the citizen's name and phone number are not shown at all on the public
    view; the exact masking rule is pending Q-001").
  - P2-F3: added FR-016 (clerk detail view shows full citizen name/phone,
    unlike the public view).
  - Q-001/Q-002/Q-003 (blocking) intentionally NOT answered.
- rev 3 continued (2026-09-09) — human decisions H1/H2 received; also closed
  the gap between what this changelog previously claimed and what was
  actually written in the other requirements files:
  - H1 (resolves Q-003, supersedes part of P2-F1's original fix): the human
    decided the pilot needs a second role, "admin clerk" — a clerk with the
    added ability to create clerk accounts and reset passwords. Updated
    Personas (admin clerk named explicitly; Operator narrowed to a one-time
    bootstrap actor only), rewrote FR-015 (bootstrap of the first admin
    account only, out-of-band), added FR-017 (admin creates a clerk
    account), FR-018 (admin resets a clerk's password), FR-019 (non-admin
    clerk denied access to both). Converted Assumptions A1, A2, A10 from
    open assumptions into recorded decisions; added A11 (bootstrap
    mechanism assumption — the one part of this still not specified by the
    human) and A12 (exactly one admin clerk expected in practice, not
    hard-enforced). Q-003 moved to Resolved in open-questions.md. New
    nice-to-know question added (Q-015) for admin-clerk self-lockout, since
    H1 does not say how an admin clerk resets their own forgotten password.
  - H2 (resolves Q2-F1, which rev-3-continued a gap in): blank, whitespace-
    only, or malformed-format complaint-number input on the public lookup
    page shows the exact message "Enter a valid complaint number" and
    performs no lookup at all (no request against the complaint store).
    Added FR-020 and BR-015; verified by new AC-018 in
    acceptance-criteria.md.
  - Synchronization fix: the AC/BR amendments this file's previous rev-3
    entry described for Q2-F2 (loading/timeout states), Q2-F3 (empty-state
    list), Q2-F4 (BR-010 citation), Q2-F6 (max-length rule), and P2-F3
    (clerk sees name/phone in detail view) had not actually been applied to
    acceptance-criteria.md/business-rules.md yet. They are applied now — see
    those files' own rev-3 changelogs for the concrete bullets added
    (AC-002, AC-004, AC-005, AC-006, AC-009, AC-011; BR-014).
  - P2-F2: re-verified wording; BR-005 and AC-006 previously used
    differently-worded statements of the same public-masking rule.
    Reworded both to the identical sentence already used in the MVP scope
    bullet and FR-009: "the citizen's name and phone number are not shown
    at all on the public view; the exact masking rule is pending Q-001."
  - Q-001/Q-002 (blocking) intentionally NOT answered; Q-003 resolved via
    H1 above.
- rev 4 (2026-09-09) — rework pass 3/3 (final), requirements-qa-reviewer
  high finding + advisories, plus product-reviewer advisories:
  - P3-F1: MVP scope bullet promised filtering "by status and/or date" but
    FR-007/AC-005 only ever specified status. Removed "and/or date" from
    the MVP bullet; added date filtering to Future scope instead.
  - P3-F2: raised FR-011 and FR-014 (audit history) from Should to Must —
    the business objective names an "auditable record" as a core
    deliverable, not an optional one.
  - Q3-F1/Q3-F2/Q3-F3/Q3-F4/P3-F3: see business-rules.md,
    acceptance-criteria.md, and user-stories.md rev-4 changelogs for the
    concrete additions (BR-016, AC-019, AC-005/AC-017 bullets, US-017,
    US-009's Implements list, BR-013 mitigation line). No product-
    requirements.md body change was needed for these beyond this note.
  - Q-001/Q-002 (blocking) intentionally NOT touched per instruction.

## Problem
A panchayat (village-level local government office) currently has no structured
way to record citizen complaints (e.g., broken streetlight, water supply issue,
road damage) or to let citizens check what happened to a complaint they
reported. Complaints are likely tracked informally (paper registers, memory),
making it hard for the clerk to follow up and impossible for a citizen to get
a status update without visiting or calling the office. The tool should let a
clerk log a complaint once and give the citizen a reference number they can
use to self-check status later, reducing repeat visits/calls to the office.

## Target users & personas
- **Panchayat clerk** — panchayat staff member (1–5 people in the pilot) who
  receives complaints (in person, by phone) and enters them into the system.
  Comfortable with basic web forms; works from a panchayat-office computer
  (assumption, see Assumptions).
- **Citizen** — resident of the panchayat area who filed a complaint through
  the clerk and wants to check its status later using a phone or shared
  computer. Not assumed to have a smartphone or reliable data connection;
  may be visiting a low-cost/shared device or on a slow mobile network.

- **Admin clerk** — one of the clerks (decision H1, resolves Q-003), who has
  every regular-clerk permission plus two additional abilities: creating a
  new clerk account, and resetting an existing clerk's password (FR-017,
  FR-018). This is a login-based persona, not a separate ongoing "admin
  web app" role — the admin clerk uses the same clerk UI as everyone else,
  with two extra screens/actions available only to them. The pilot is
  expected to have exactly one admin clerk in practice (Assumption A12).
- **Operator** (minimal, one-time-only actor, narrowed in rev 3 by H1) — the
  deploying/support party who performs a single out-of-band bootstrap step
  at deployment time to create the very first admin clerk account (FR-015,
  Assumption A11), before any admin clerk exists to use FR-017. Not an
  ongoing role: once the first admin clerk account exists, all further
  account creation and password resets happen in-app via the admin clerk
  (FR-017, FR-018), not via the Operator.

Personas explicitly out of scope for this MVP (see Scope challenges /
Future scope): a panchayat supervisor/officer role, department staff who
resolve complaints, and a full-time system-administrator persona with a
separate admin web application — the minimal account-management need is
covered by the admin clerk persona above (a clerk with two extra
permissions), not a separate ongoing role or application.

## Business objective
Reduce the effort citizens spend chasing status updates in person, and give
the panchayat office a simple, auditable record of complaints received and
their resolution status, for a single-panchayat pilot with 1–5 clerks and a
few hundred citizens checking status.

## Core workflows
1. **Log a complaint (clerk):** Clerk receives a complaint (in person or by
   phone) and enters citizen name, phone number, and complaint description
   into the system. System generates a unique complaint number and shows it
   to the clerk, who relays it to the citizen (verbally or on paper).
2. **Update status (clerk):** Clerk finds an existing complaint (by number or
   from a list) and updates its status as work progresses, optionally adding
   a note.
3. **Check status (citizen):** Citizen visits a public web page, types in
   their complaint number, and sees the current status without logging in.

## MVP scope
- Clerk authentication with two permission levels: regular clerk and admin
  clerk (decision H1, resolves Q-003; no self-registration for either). The
  first admin clerk account is created out-of-band by the Operator as a
  one-time bootstrap step (FR-015, Assumption A11). From then on, the admin
  clerk creates further clerk accounts and resets any clerk's password
  in-app (FR-017, FR-018); a regular (non-admin) clerk cannot do either
  (FR-019).
- Clerk creates a complaint: citizen name, phone, description, auto-set
  creation date/time. The complaint detail view shows the clerk the full
  citizen name and phone number (FR-016) — this is not masked for clerks,
  only for the public view (see below).
- System auto-generates a unique complaint number per complaint.
- Clerk updates complaint status and can add a free-text note per update.
- Clerk can list/search all complaints logged in the office, regardless of
  which clerk created them (basic filter by status; date filtering is
  Future scope — see below, P3-F1). All 1–5 clerks share full visibility of
  every complaint — there is no per-clerk "my complaints" restriction in
  the MVP (see Assumption A1 — complaint-visibility permissions are shared
  between regular and admin clerks).
- Clerk can view status-change history for a complaint.
- Clerk can correct citizen name/phone/description shortly after logging
  (data-entry correction window — see Open Questions).
- Public, unauthenticated web page where a citizen enters an exact complaint
  number and sees: complaint number, status, date logged, latest note. The
  citizen's name and phone number are not shown at all on the public view;
  the exact masking rule is pending Q-001 (see BR-005).
- Clear "not found" message for an unmatched complaint number.
- Single panchayat, single language (assumption — see Open Questions),
  low-cost hosting suitable for pilot scale.

## Future scope
- SMS/WhatsApp notifications to citizens on status change (explicitly
  excluded from MVP per intake).
- Citizen self-service complaint filing (online form) instead of
  clerk-mediated intake.
- Photo/attachment upload on complaints.
- Multi-panchayat / multi-tenant support.
- Supervisor/admin role with cross-clerk reporting dashboards and analytics.
- Complaint categorization and routing to departments; SLA/escalation
  tracking.
- Multi-language UI.
- Bulk export / audit-log export for compliance or reporting.
- Filtering the complaint list by date (in addition to status) — MVP only
  requires status filtering (FR-007, AC-005); moved here from the MVP scope
  bullet, P3-F1, rev 4.

## Functional requirements

| ID | Requirement | Priority | Source |
|----|-------------|----------|--------|
| FR-001 | An authenticated clerk shall log in before creating or editing complaints. | Must | Intake (clerk logs complaints) |
| FR-002 | An authenticated clerk shall be able to create a complaint with citizen name, citizen phone number, and complaint description; creation date/time is set automatically. | Must | Idea |
| FR-003 | On creation, the system shall generate a complaint number that is unique across all existing complaints. | Must | Idea |
| FR-004 | The system shall display the generated complaint number to the clerk immediately after the complaint is saved. | Must | Idea |
| FR-005 | An authenticated clerk shall be able to find an existing complaint (by number or from a list) and change its status. | Must | Idea |
| FR-006 | An authenticated clerk shall be able to add a free-text note each time they change a complaint's status. | Should | Inferred (useful for follow-up) |
| FR-007 | An authenticated clerk shall be able to list/search all complaints in the system (not restricted to complaints they personally created), filterable at least by status, ordered most-recently-created first. | Must (raised from Should — FR-005's "find ... from a list" depends on this) | Inferred (1-5 clerks, single shared role, share full visibility — Assumption A1) |
| FR-008 | Any citizen shall be able to look up a complaint's status on a public web page by entering the exact complaint number, without authentication. | Must | Idea |
| FR-009 | The public lookup result shall show complaint number, current status, date logged, and latest status note; the citizen's name and phone number are not shown at all on the public view (exact masking rule pending Q-001). | Must | Inferred (privacy) — see BR-005 |
| FR-010 | The system shall show a clear "not found" message when an entered complaint number does not match any record. | Must | Idea |
| FR-011 | The system shall keep a status-change history (previous status, new status, note, timestamp, editing clerk) per complaint, visible to clerks. | Must (raised from Should, P3-F2 — the business objective names an "auditable record" as core) | Inferred |
| FR-012 | An authenticated clerk shall be able to correct citizen name/phone/description within a defined edit window after creation. | Should | Inferred (data-entry errors happen) |
| FR-013 | The system shall prevent two complaints from ever sharing the same complaint number, including when two complaints are created concurrently. | Must | Idea (implied by "complaint number") |
| FR-014 | The system shall retain a history of edits made under FR-012 to citizen name/phone/description (previous value, new value, editing clerk, timestamp), visible to clerks. | Must (raised from Should, P3-F2) | Inferred — objective is an "auditable record" (see Business objective); added to close audit gap between FR-011 (status) and FR-012 (data edits) |
| FR-015 | The Operator actor shall create the very first admin clerk account through a one-time, out-of-band bootstrap mechanism (e.g., a seed script or initial config value) at deployment time, before any in-app account-management action is possible. | Must | H1 (rev 3) — supersedes the original FR-015 wording; FR-001 (Must) depends on an account existing; gap identified in P2-F1 |
| FR-016 | An authenticated clerk viewing a complaint's detail page shall see the complaint's full citizen name and phone number (unlike the public view, which shows neither per FR-009/BR-005). | Should | Inferred from BR-007; gap identified in P2-F3 |
| FR-017 | An authenticated admin clerk shall be able to create a new clerk account (regular or admin) via the application, without needing the Operator's out-of-band mechanism. | Must | H1 (rev 3), resolves Q-003 |
| FR-018 | An authenticated admin clerk shall be able to reset the password of any clerk account (regular or admin) via the application. | Must | H1 (rev 3), resolves Q-003 |
| FR-019 | A non-admin (regular) clerk shall have no access to account-creation or password-reset functionality; a direct attempt to reach either (e.g., by URL) shall be denied. | Must | H1 (rev 3), resolves Q-003 |
| FR-020 | The public lookup page shall validate the complaint-number input before performing any lookup; blank, whitespace-only, or malformed-format input shall show the message "Enter a valid complaint number" and no lookup request shall be made against the complaint store. | Must | H2 (rev 3), resolves Q2-F1 |

## Non-functional requirements

| ID | Requirement | Priority | Source | Verification |
|----|-------------|----------|--------|---------------|
| NFR-001 | The public status-lookup page shall render a result within 3 seconds on a typical mobile connection (reference: 3G-equivalent bandwidth). | Must | Intake (phone-based citizens) | AC-010 |
| NFR-002 | The system shall support at least 5 concurrent clerk sessions and a few hundred citizen lookups per day while keeping public lookup responses within the 3-second target defined in NFR-001 (no separate, undefined "slowdown" threshold). | Must | Intake (pilot scale) | AC-010 |
| NFR-003 | Clerk accounts shall require authentication (at minimum, username + password); citizen lookup shall require none. | Must | Idea + inferred | AC-001, AC-015 |
| NFR-004 | The public lookup feature shall not expose any endpoint that lists or enumerates all complaints; only single-record lookup by exact number is public. | Must | Inferred (privacy/security) | AC-011 |
| NFR-005 | The public lookup endpoint shall be rate-limited (assumption: no more than 20 attempts per IP per minute) to reduce automated guessing of complaint numbers. | Should | Inferred (security) — threshold tracked as Q-013 (important) | AC-011 |
| NFR-006 | The system shall be deployable on low-cost hosting appropriate for a single-panchayat pilot; no specific technology is mandated at this stage. | Must | Intake | Not independently testable pre-architecture — this constrains the architect's hosting choice rather than defining a runtime behavior; compliance is assessed at architecture/deployment review, not via a product AC. |
| NFR-007 | The system shall target at least 99% uptime during panchayat office hours; it is not required to be a 24/7 mission-critical system. | Should | Assumption (pilot scale) | Deferred to post-launch uptime monitoring — cannot be verified as a pre-release AC; architect/ops should define the monitoring mechanism. |
| NFR-008 | Only citizen name, phone number, and complaint text/status/notes shall be stored as personal data; no government ID numbers (e.g., Aadhaar) shall be collected or stored. | Must | Intake (compliance/PII) | AC-012 |
| NFR-009 | Stored citizen phone numbers and full names shall never be exposed through any public-facing page or API. | Must | Inferred (privacy) | AC-006 |
| NFR-010 | The system shall retain complaint records for at least 12 months by default, with no automatic deletion in the MVP. | Should | Assumption — see Open Questions (Q-006) | AC-013 |
| NFR-011 | For all three core workflows (log complaint, update status, citizen lookup), the UI shall show a visible in-progress indicator while a request is pending, and a clear error/timeout message if no response arrives within a bounded time (default suggested: 10 seconds; exact bound left to architecture). | Should | Inferred — gap identified in Q2-F2 | AC-002, AC-004, AC-006 |

## Integrations & data
- No external integrations identified for the MVP (no SMS gateway, no
  government ID verification, no payment, no GIS/mapping).
- Data captured per complaint: citizen name, citizen phone number, complaint
  description (free text), auto-generated complaint number, status, status
  history (status + note + timestamp per change), creation timestamp.
- No integration with any existing panchayat records system is assumed to
  exist; this is a standalone tool for the pilot.

## Constraints (stated by human)
- No specific technology stack, database, or hosting provider is chosen at
  this stage — that is a later (architecture) phase.
- No fixed deadline stated.
- No special compliance regime; minimal PII only (name, phone, complaint
  text) — explicitly no Aadhaar or other government ID numbers.
- Citizen channel for MVP is a public web page only (no SMS/WhatsApp).
- Scale: one panchayat, 1–5 clerks, a few hundred citizens checking status.

## Scope challenges
- **Photo/attachment upload on complaints** — very common for panchayat
  complaint types (broken road, garbage, streetlight) but not mentioned in
  the idea or intake. Pushed back: adding file upload increases storage
  cost, moderation concerns, and mobile bandwidth needs for a pilot that is
  supposed to be low-cost and simple. Recommend deferring to a later phase.
  Kept in Future scope so the human can pull it forward if needed.
- **Public display of citizen name/phone on the status page** — the idea did
  not specify what a citizen sees on lookup. Displaying a citizen's full name
  and phone number to anyone who can guess or overhear a complaint number is
  a privacy risk with no stated business need. Proposed default: mask/omit
  name and phone from the public view (FR-009, BR-005), pending human
  confirmation (Q-001, blocking).
- **Multi-panchayat / multi-tenant design** — the idea's title and framing
  could imply reuse across panchayats later, but intake explicitly scopes
  this pilot to a single panchayat. Pushed back on building any
  multi-tenant data model or admin-of-admins concept now; recorded as
  Future scope only.
- **Citizen self-service complaint filing** — the idea's phrasing ("clerk
  logs citizen complaints... citizens check status") already limits intake
  to the clerk, but this is a natural next ask. Confirmed as Future scope,
  not MVP, so the architect does not build an authenticated/self-service
  citizen intake flow now.
- **Rate limiting / anti-enumeration on public lookup** — not requested
  explicitly, but sequential or simple complaint numbers are guessable.
  Proposed a modest rate limit (NFR-005) as a low-cost mitigation rather
  than a heavier control (e.g., CAPTCHA), pending human confirmation.

## Assumptions
- A1 (DECISION per H1, rev 3 — Q-003 resolved, no longer an assumption):
  All clerks share one permission set except for two admin-only abilities
  (creating clerk accounts, resetting passwords — FR-017, FR-018). There is
  no separate supervisor/officer role and no cross-clerk reporting
  role in the MVP; the only role split is regular clerk vs. admin clerk.
- A2 (DECISION per H1, rev 3 — no longer an assumption): Ongoing clerk
  account creation and password resets happen in-app, performed by the
  admin clerk (FR-017, FR-018) — not by an external Operator/CLI. The
  Operator actor's involvement is narrowed to a single one-time bootstrap
  of the first admin clerk account (FR-015; see A11 below for how that
  bootstrap step itself is assumed to work). There is no citizen or clerk
  self-registration flow.
- A3: Default complaint statuses are: New → In Progress → Resolved /
  Rejected, with an optional final "Closed" state (see Q-002, blocking).
- A4: Complaint number format is left to the architect, but must be short
  enough for a clerk to read aloud or write on paper, and must not be
  guessable in bulk (no purely public listing).
- A5: The system is single-language (assume English, pending Q-004,
  important) for the MVP.
- A6: Clerks access the system primarily from a shared/office computer, not
  necessarily a personal phone (pending Q-010, nice-to-know).
- A7: Complaint records are not deleted once created; a clerk can only move
  a complaint through statuses, not remove it (BR-008), to preserve a basic
  audit trail.
- A8: Edit window for correcting citizen name/phone/description after
  creation is assumed to be 7 days (pending Q-007, important).
- A9: Retention period for complaint records is assumed to be at least 12
  months with no automatic purge in the MVP (pending Q-006, important).
- A10 (DECISION per H1, rev 3 — no longer an assumption): Clerk password
  reset is an in-app administrative action performed by the admin clerk
  (FR-018), not an out-of-band/manual action outside the application. There
  is still no self-service "forgot password" flow for a regular clerk — only
  the admin clerk can trigger a reset, and only for another clerk's account.
  How an admin clerk recovers if they themselves are locked out is not
  specified by the human and is tracked as Q-015 (nice-to-know). (Originally
  added rev 2, P-F6; superseded/updated rev 3, H1.)
- A11 (new, rev 3, H1): The bootstrap mechanism for the very first admin
  clerk account (FR-015) is assumed to be a one-time seed script or initial
  configuration value run by the deploying operator; no other bootstrap
  mechanism is specified by the human, and this is not designed further
  here — it is an architecture-level implementation detail.
- A12 (new, rev 3, H1): The pilot is expected to have exactly one admin
  clerk account in practice, matching the human's phrasing ("one admin
  clerk"). The system is not required to hard-enforce a maximum of one
  admin account (FR-017 does not prevent an admin from creating a second
  admin), since the human did not state this as a hard constraint.

## Uncertain / needs human
See `.ai/requirements/open-questions.md` for the full, ranked list. As of
rev 3, two questions remain blocking design: public-page PII display
(Q-001) and complaint status/transition model (Q-002, which now also asks
whether immediate New→Rejected transitions should be allowed — Q2-F7).
Q-003 (single-vs-multi role model) is now **resolved** via human decision
H1 — see the Resolved section of open-questions.md and Assumptions A1/A2/
A10 above. A new nice-to-know question was added in rev 3: what happens if
an admin clerk is themselves locked out (Q-015).
