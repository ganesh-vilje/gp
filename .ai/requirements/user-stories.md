# User Stories

## Changelog
- rev 1 (2026-09-09) — initial draft, no prior findings.
- rev 2 (2026-09-09) — rework pass 1/3:
  - P-F1: US-005 reworded — clerk sees ALL complaints in the office, not just
    ones they personally logged (matches product-requirements.md rev 2).
  - P-F3: US-008 now also references FR-014 (edits are audited).
  - Q-F1: added US-012 (concurrent-edit audit trust), implementing BR-011.
  - Q-F2: added US-013 (confidence that only clerks can write, and nothing
    is ever deleted), implementing BR-003 and BR-008.
- rev 3 (2026-09-09):
  - H1 (resolves Q-003): added US-014 (admin creates a clerk account),
    US-015 (admin resets a clerk's password), and US-016 (assurance that
    only the admin clerk can manage accounts) — implementing FR-017,
    FR-018, FR-019, BR-013.
  - H2 (resolves Q2-F1): US-006 now also implements FR-020 and is verified
    additionally by AC-018 (blank/malformed complaint-number input).
- rev 4 (2026-09-09) — rework pass 3/3 (final):
  - Q3-F1: added US-017 (bootstrap the first admin clerk account),
    implementing FR-015, verified by new AC-019 — closes the high finding
    that FR-015 had no US.
  - Q3-F4: US-009 now also implements FR-016 (clerk detail view shows
    citizen name/phone), verified additionally by AC-009's existing FR-016
    bullet.

Each story references the FR(s)/BR(s) it implements. Acceptance criteria for
each story live in `acceptance-criteria.md` under matching IDs.

## US-001 — Clerk login
As a panchayat clerk, I want to log in with my own account so that only
authorized staff can record and manage complaints.
- Implements: FR-001, NFR-003
- Verified by: AC-001

## US-002 — Log a new complaint
As a panchayat clerk, I want to enter a citizen's name, phone number, and
complaint description so that the complaint is recorded in the system.
- Implements: FR-002, BR-006, BR-007
- Verified by: AC-002

## US-003 — Receive a complaint number
As a panchayat clerk, I want the system to generate a unique complaint
number as soon as I save a new complaint so that I can give it to the
citizen for future reference.
- Implements: FR-003, FR-004, FR-013, BR-001
- Verified by: AC-003

## US-004 — Update complaint status
As a panchayat clerk, I want to change a complaint's status and add a note
so that progress is tracked and the citizen sees an up-to-date status when
they check.
- Implements: FR-005, FR-006, BR-002
- Verified by: AC-004

## US-005 — List and filter complaints
As a panchayat clerk, I want to see a list of all complaints logged in the
office — not just the ones I personally entered — filterable by status, so
that any of the 1–5 clerks can follow up on ones still pending, regardless
of who originally logged them.
- Implements: FR-005, FR-007
- Verified by: AC-005

## US-006 — Citizen checks status
As a citizen, I want to enter my complaint number on a public page so that
I can see its current status without needing to create an account or visit
the office.
- Implements: FR-008, FR-009, FR-020, BR-004, BR-005, BR-015, NFR-004,
  NFR-009
- Verified by: AC-006, AC-018

## US-007 — Not-found message
As a citizen, I want a clear message if my complaint number isn't
recognized so that I know to double-check it or contact the panchayat
office instead of assuming something is broken.
- Implements: FR-010
- Verified by: AC-007

## US-008 — Correct a data-entry mistake
As a panchayat clerk, I want to correct the citizen's name, phone, or
description shortly after logging a complaint so that the record stays
accurate if I made a typo. I also want that correction to be recorded, not
silently overwritten, so the office keeps an auditable trail of any change.
- Implements: FR-012, FR-014
- Verified by: AC-008, AC-009

## US-009 — View status history
As a panchayat clerk, I want to see the history of status changes on a
complaint so that I understand what has already been done before I take
the next action.
- Implements: FR-011, FR-016
- Verified by: AC-009

## US-010 — Fast, low-bandwidth public lookup
As a citizen on a slow mobile connection, I want the status page to load
quickly so that checking status doesn't cost me a lot of time or data.
- Implements: NFR-001, NFR-002
- Verified by: AC-010

## US-011 — Protection against complaint-number guessing
As the panchayat office, I want the public lookup to resist automated
guessing of complaint numbers so that citizens' complaint details (even
the limited public fields) aren't scraped in bulk.
- Implements: NFR-004, NFR-005
- Verified by: AC-011

## US-012 — Trust in concurrent edits
As a panchayat clerk, I want to know that my status update is never
silently lost or overwritten without a trace if another clerk updates the
same complaint at nearly the same time, so that the office's record stays
trustworthy even with multiple clerks working at once.
- Implements: BR-011
- Verified by: AC-014

## US-013 — Confidence that data is safe from unauthorized change or loss
As the panchayat office, I want assurance that only logged-in clerks can
ever create or change a complaint, and that no complaint can ever be
deleted (by a clerk, a citizen, or an outside request), so that the
complaint record remains a reliable, tamper-resistant history of what was
reported and done.
- Implements: BR-003, BR-008
- Verified by: AC-015, AC-016

## US-014 — Admin creates a clerk account
As an admin clerk, I want to create a new clerk account so that a new
staff member can log in and start recording complaints, without needing to
ask the deploying operator to run an out-of-band script every time.
- Implements: FR-017, BR-013
- Verified by: AC-017

## US-015 — Admin resets a clerk's password
As an admin clerk, I want to reset another clerk's password so that a
locked-out colleague can get back into the system without waiting for the
deploying operator.
- Implements: FR-018, BR-013
- Verified by: AC-017

## US-016 — Confidence that only the admin clerk manages accounts
As the panchayat office, I want assurance that only the designated admin
clerk can create new clerk accounts or reset passwords — not any of the
other clerks — so that account management stays controlled and auditable
even though every clerk shares the same complaint-handling permissions.
- Implements: FR-019, BR-013
- Verified by: AC-017

## US-017 — Bootstrap the first admin clerk account
As the deploying operator, I want a one-time way to create the very first
admin clerk account so that someone can log in and start using FR-017/
FR-018 to provision every other clerk account, without needing an admin
account to already exist.
- Implements: FR-015
- Verified by: AC-019
