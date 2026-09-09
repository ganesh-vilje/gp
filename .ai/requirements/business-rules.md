# Business Rules

## Changelog
- rev 1 (2026-09-09) — initial draft, no prior findings.
- rev 2 (2026-09-09) — rework pass 1/3:
  - Q-F1: added BR-011 (concurrent status-update behavior — last-write-wins
    on current status/note, but no silent audit-trail loss).
  - Q-F7: added BR-012 (phone number format/length validation rule).
  - P-F3: BR note added under BR-008 cross-referencing FR-014 (edits are now
    audited, not just status changes).
  - Verified by: AC-012 (BR-009/NFR-008), AC-014 (BR-011), AC-015 (BR-003),
    AC-016 (BR-008) — see acceptance-criteria.md rev 2.
- rev 3 (2026-09-09):
  - H1 (resolves Q-003): added BR-013 (admin clerk account-management
    rules) — verified by new AC-017.
  - H2 (resolves Q2-F1): added BR-015 (public lookup validates input before
    any lookup is performed) — verified by new AC-018.
  - Q2-F4: BR-010 was previously an orphan (cited by no AC/FR/US). It is now
    cited in AC-011's verifies-list (see acceptance-criteria.md).
  - Q2-F6: added BR-014 (explicit max-length limits on citizen name and
    complaint description — a deliberate MVP decision, not an oversight) —
    verified by an added bullet in AC-002.
  - P2-F2: reworded BR-005 to use the identical sentence already used in
    product-requirements.md's MVP scope bullet and FR-009, so all three (plus
    AC-006) now state the public-masking rule identically.
- rev 4 (2026-09-09) — rework pass 3/3 (final):
  - Q3-F2: added BR-016 (username uniqueness/format, password minimum
    requirements, and how a new/reset password reaches the clerk) —
    verified by new bullets in AC-017.
  - P3-F3: added a mitigation line to BR-013 recommending a second admin
    clerk account as mitigation for admin self-lockout, pending Q-015.
- rev 4.1 (2026-09-09) — post-GATE_1 housekeeping: BR-002 and BR-005 updated
  to record Q-002/Q-001 as resolved at GATE_1 (see
  open-questions.md § Resolved); no rule's substance changed.
- rev 5 (2026-09-09) — post-GATE_2 amendment (technology stack approved):
  - BR-015: removed the "or at the very first server check" phrasing that
    was written to permit a no-JS implementation (superseded by H4/Q8 —
    the frontend may require JavaScript). The validation-before-lookup rule
    itself is unchanged and is enforced by the API (FastAPI backend, per
    H4).
  - BR-005: reworded to state that the public page shows the enumerated
    public status message (per Q-016, resolved GATE_2 Q7: "option (b),
    fixed status messages"), never the clerk's free-text note.
  - BR-010: no change to BR-010's own text (it does not itself state a
    number); noted here for traceability because AC-011 verifies BR-010
    alongside NFR-005, and NFR-005's 20-requests-per-IP-per-minute figure
    is now a confirmed human decision (GATE_2 Q4: "keep 20/min."), not an
    analyst default — see product-requirements.md NFR-005 and
    open-questions.md § Resolved (Q-013).
- rev 6 (2026-09-09) — reconciliation with ADR-007 (GATE_2) — password
  minimum 12 (C5); surfaced by product-reviewer in /ux rev 1:
  - BR-016: password minimum length changed from 8 to 12 characters to match
    the human-approved GATE_2 technology decision ADR-007 (C5). No other part
    of BR-016 changed. Verified by updated AC-017 (acceptance-criteria.md).

## BR-001 — Complaint number uniqueness and immutability
Every complaint is assigned exactly one complaint number by the system at
creation time. The number is unique across all complaints (past and
present) and, once assigned, never changes and is never reused, even if the
complaint is later marked invalid/duplicate.

## BR-002 — Complaint status model (resolved at GATE_1, Q-002)
Default statuses: **New** (set automatically at creation) → **In
Progress** → **Resolved** or **Rejected** → **Closed** (optional final
state). A complaint cannot move directly from **New** to **Closed**,
**Resolved**, or **Rejected**; it must pass through **In Progress** first.
This model was the analyst's default and was confirmed by the human at
GATE_1 (Q-002, resolved at GATE_1) — see open-questions.md § Resolved.

## BR-003 — Who may create or change a complaint
Only an authenticated clerk may create a complaint, change its status, add
a note, or edit its citizen-detail fields. Citizens cannot create, edit, or
delete any complaint record through the public interface.

## BR-004 — Public lookup requires an exact match
The public status-lookup page accepts only an exact complaint number.
Partial matches, wildcard search, or "did you mean" suggestions are not
permitted, to avoid leaking information about other complaints.

## BR-005 — Public view masks citizen PII (resolved at GATE_1, Q-001; public-message rule resolved at GATE_2, Q-016)
The citizen's name and phone number are not shown at all on the public
view (status + number + date + public status message are sufficient for
the citizen to recognize their own complaint, since they already hold the
number). This default was confirmed by the human at GATE_1 (Q-001,
resolved at GATE_1) — see open-questions.md § Resolved. (Wording
standardized rev 3, P2-F2, to match FR-009 and the MVP scope bullet in
product-requirements.md, and AC-006 in acceptance-criteria.md.)
The public view shows a public status message drawn from a fixed,
enumerated set (one per status, wording defined in /ux); the clerk's
free-text note is never shown on the public view — it is visible to
clerks only. This resolves Q-016 (human decision at GATE_2 Q7, verbatim:
"option (b), fixed status messages") — see open-questions.md § Resolved.
(Reworded rev 5.)

## BR-006 — Complaint description is required
A complaint cannot be created with a blank description field. The
description is the substance of the complaint and is required for the
clerk and any future reader to understand what was reported.

## BR-007 — Citizen name and phone are required at creation
Citizen name and phone number are required fields when a clerk creates a
complaint, even though they are not shown on the public view. They exist so
the clerk/office can contact the citizen if needed.

## BR-008 — No hard delete of complaints
Once created, a complaint record cannot be deleted by a clerk. If a
complaint was logged in error or is a duplicate, it must be moved to a
status that reflects that (e.g., "Rejected" with a note explaining why)
rather than removed, to preserve a basic audit trail. (Assumption — the
exact status vocabulary for "invalid/duplicate" is part of Q-002.) This
no-delete rule now applies symmetrically to the edit history introduced by
FR-014: past values of citizen name/phone/description are retained, not
overwritten in place, mirroring how status history is never deleted.
(Cross-reference added rev 2, P-F3.)

## BR-009 — No government ID numbers collected
No field in the system may capture a government-issued ID number (e.g.,
Aadhaar, voter ID, ration card number). Only name, phone number, and
complaint text/status/notes are stored, per the intake compliance
constraint.

## BR-010 — No bulk public access
There is no public-facing feature, page, or endpoint that returns a list of
complaints or complaint numbers. The only public capability is single-record
lookup by an exact, individually supplied complaint number.

## BR-011 — Concurrent status updates do not silently lose data
If two clerks update the same complaint's status/note at effectively the
same time, the system applies last-write-wins for the complaint's *current*
status and note (the mechanism — e.g., optimistic locking vs. simple
overwrite — is an architecture decision, not specified here). Regardless of
which write "wins," both updates must be preserved in the status-change
history (FR-011) with each editing clerk's identity and timestamp, so no
update is silently lost from the audit trail even if it is superseded as
the current status. (Added rev 2, Q-F1. UX preference for warning a clerk
of a concurrent edit is tracked as Q-012, nice-to-know — not blocking.)

## BR-012 — Citizen phone number format
Citizen phone number must be a plausible phone number at entry: digits
only, optionally with a leading "+" and country code, length between 7 and
15 characters (loosely E.164-shaped). The clerk sees a validation error and
the record is not saved if the phone number fails this check. (Added rev 2,
Q-F7. Exact validation regex/format is left to the architect.)

## BR-013 — Admin clerk account-management rules (decision H1, resolves Q-003)
There are two clerk permission levels: regular clerk and admin clerk. Only
an authenticated admin clerk may (a) create a new clerk account (regular or
admin), or (b) reset the password of any clerk account. A regular
(non-admin) clerk has no access to either action, including via direct
URL/API access — both must be denied for a non-admin clerk. All other
permissions (creating/updating complaints, viewing all complaints, adding
notes) are identical between regular and admin clerks; the admin clerk has
no other elevated visibility into complaint data. The very first admin
clerk account is created out-of-band by the deploying operator as a one-
time bootstrap step (see FR-015, Assumption A11), not through this rule.
(Added rev 3, H1.) As mitigation for admin self-lockout (Q-015, still
open), the office is recommended to provision a second admin clerk account
in practice, even though only one is strictly expected (Assumption A12);
this is a recommendation, not an enforced rule. (Added rev 4, P3-F3.)

## BR-014 — Maximum input length for citizen name and complaint description
Citizen name is limited to 100 characters; complaint description is limited
to 2,000 characters. These are deliberate MVP limits — generous enough for
normal use, chosen to bound storage/display cost and give the architect a
concrete constraint — not an oversight of "no limit." A clerk who exceeds
either limit sees a validation error and the record is not saved until the
field is shortened. (Added rev 3, Q2-F6.)

## BR-015 — Public lookup validates input before any lookup is performed
The API validates the entered complaint number before making any request
against the complaint store. Blank input, whitespace-only input, and input
that does not match the expected complaint-number format are all rejected
by the API, before any data lookup, with the message "Enter a valid
complaint number." This is an API-level (server-side) contract, independent
of any additional client-side validation the Next.js frontend also
performs (H4: FastAPI JSON API with a separate Next.js frontend). No
lookup, and no distinction between "not found" and "invalid," is ever
performed or implied for this class of input — see BR-004 (exact match
only) and BR-010 (no bulk access), which this rule complements by ensuring
malformed input never reaches the lookup mechanism at all. (Added rev 3,
H2; reworded rev 5 to remove the no-JS allowance per H4/Q8.)

## BR-016 — Account creation and password rules (decision H1, resolves Q3-F2)
A new clerk's username must be unique across all clerk accounts and match
a simple format (letters, digits, and underscores only, 3–30 characters);
an admin clerk sees a validation error and no account is created if the
username fails either check. A password (whether set at account creation
or set by a password reset) must be at least 12 characters (per ADR-007,
GATE_2, C5); a shorter password is rejected with a validation error and no
account is created/password is not changed. A new or reset password is shown once,
on-screen, to the admin clerk performing the action (not emailed or
texted, since no such channel exists in the MVP); the admin clerk is
expected to hand it to the affected clerk in person or by phone, and the
affected clerk must change that password at their first subsequent login.
(Added rev 4, Q3-F2. Exact username/password character-class regex is left
to the architect; the username length is the analyst's default. Password
minimum length is 12, per ADR-007/GATE_2/C5, not an analyst default;
amended rev 6.)
