# Acceptance Criteria

## Changelog
- rev 1 (2026-09-09) — initial draft, no prior findings.
- rev 2 (2026-09-09) — rework pass 1/3:
  - P-F1: AC-005 rewritten — "all complaints the clerk is permitted to see"
    replaced with an explicit statement that all clerks see all complaints;
    order made deterministic (most-recently-created first).
  - Q-F1: added AC-014 verifying BR-011 concurrent-update behavior.
  - Q-F2: added AC-015 (BR-003 — unauthenticated create/edit/status-change
    rejected) and AC-016 (BR-008 — no delete affordance/endpoint exists).
  - Q-F3: added AC-012 (NFR-008 — no gov-ID field) and AC-013 (NFR-010 —
    retention, verified by design/config review since a 12-month window
    cannot be exercised end-to-end pre-release).
  - Q-F4: added a clerk-side not-found bullet to AC-005 (FR-005 search for a
    number that doesn't exist).
  - Q-F5: added a concurrent-creation bullet to AC-003 (FR-013 collision
    check under concurrent load, not just sequential).
  - Q-F6: AC-005 list order fixed to a single deterministic result
    (most-recently-created first); "or another documented order" removed.
  - P-F4: NFR-005/AC-011 threshold now explicitly tracked as Q-013 (added to
    open-questions.md) instead of an undefined "pending" reference.
  - P-F5: AC-008 second bullet resolved to one deterministic outcome (deny
    outright; no override role exists in MVP), still flagged pending
    Q-003/Q-007 since the underlying window/role model is unconfirmed.
  - Q-F7: added a phone-format validation bullet to AC-002 (BR-012).
  - Q-F8: AC-006 header now explicitly cites NFR-009.
  - P-F3: AC-009 extended to also cover FR-014 edit history.
- rev 3 (2026-09-09):
  - H1: added AC-017 (admin creates a clerk account; admin resets a clerk's
    password; non-admin clerk denied both) — verifies FR-017, FR-018,
    FR-019, BR-013; resolves Q-003.
  - H2: added AC-018 (blank/whitespace-only/malformed complaint number on
    the public lookup page shows "Enter a valid complaint number" and
    performs no lookup) — verifies FR-020, BR-015; resolves Q2-F1.
  - Q2-F2: added an in-flight/timeout bullet to AC-002 (log complaint),
    AC-004 (update status), and AC-006 (citizen lookup) — verifies NFR-011
    for all three core workflows.
  - Q2-F3: added a zero-complaints empty-state bullet to AC-005.
  - Q2-F4: AC-011 header and a new bullet now cite BR-010 explicitly — no
    longer an orphaned business rule.
  - Q2-F6: added max-length validation bullets to AC-002 — verifies BR-014.
  - P2-F3: added a bullet to AC-009 confirming the clerk detail view shows
    full citizen name and phone — verifies FR-016.
- rev 4 (2026-09-09) — rework pass 3/3 (final):
  - Q3-F1: added AC-019 (bootstrap of the first admin clerk account) —
    verifies FR-015; closes the high finding that FR-015 had no AC/US.
  - Q3-F2: added username-format, username-uniqueness, and password-length
    validation bullets to AC-017 — verifies new BR-016.
  - Q3-F3: added an in-flight/timeout bullet to AC-005 — verifies NFR-011
    for the list/filter workflow, matching AC-002/AC-004/AC-006.
- rev 4.1 (2026-09-09) — post-GATE_1 housekeeping: AC-004 and AC-006
  updated to record Q-002/Q-001 as resolved at GATE_1 (see
  open-questions.md § Resolved); no acceptance criterion's substance
  changed.
- rev 5 (2026-09-09) — post-GATE_2 amendment (technology stack approved):
  - AC-018: deleted the "with JS disabled" reasoning; strengthened the
    query-level assertion so it explicitly requires that no statement
    touching the complaint table executes for blank/whitespace/malformed
    input (BR-015, now stated as an API contract per H4).
  - AC-006: added an explicit assertion that the public response/DOM
    contains a message from the fixed, enumerated public-status-message
    set and never contains the clerk's free-text note, the citizen's name,
    or the citizen's phone number (resolves Q-016 per GATE_2 Q7).
  - AC-011: 20/min is now a confirmed human decision (GATE_2 Q4: "keep
    20/min."), no longer an analyst default; added a parallel-requests
    assertion so the limit must hold under concurrent load, not just
    sequential requests.

Every AC is written as Given/When/Then with a concrete, observable result.
Each AC states which FR/US/BR it verifies. Items marked **[pending Q-xxx]**
depend on an open question and may need revision once the human answers.

## AC-001 — Clerk login (verifies US-001, FR-001, NFR-003)
- Given a clerk with valid credentials on the login page, when they submit
  the login form, then they are granted access to the clerk area (complaint
  list / new-complaint form).
- Given a clerk submits invalid credentials, when the form is submitted,
  then access is denied and a generic error is shown (the message does not
  reveal whether the username or the password was wrong).
- Given no clerk is logged in, when a browser requests any clerk-only page
  or action directly (e.g., new-complaint form, status update), then the
  system redirects to login / denies the action.

## AC-002 — Log a new complaint (verifies US-002, FR-002, BR-006, BR-007, BR-012, BR-014, NFR-011)
- Given an authenticated clerk on the "new complaint" form, when they submit
  citizen name, citizen phone number, and complaint description all
  filled in, then a new complaint record is created with status "New" and a
  creation timestamp set to the current date/time.
- Given the same form submitted with the complaint description left blank,
  when submitted, then the system rejects the submission with a visible
  validation message and no record is created.
- Given the same form submitted with citizen name or phone left blank, when
  submitted, then the system rejects the submission with a visible
  validation message and no record is created.
- Given the same form submitted with a phone number that is not a plausible
  phone number per BR-012 (e.g., contains letters, or is 3 digits long),
  when submitted, then the system rejects the submission with a visible
  validation message and no record is created.
- Given a citizen name longer than 100 characters or a complaint
  description longer than 2,000 characters (BR-014), when the form is
  submitted, then the system rejects the submission with a visible
  validation message and no record is created.
- Given the form is submitted, when the save request is in flight, then
  the clerk sees a visible in-progress indicator (e.g., a disabled submit
  button or spinner), and if no response arrives within the bounded time
  defined by NFR-011, then the clerk sees a clear error/timeout message
  instead of an indefinitely spinning page.

## AC-003 — Complaint number generation (verifies US-003, FR-003, FR-004, FR-013, BR-001)
- Given a complaint is successfully created, when the record is saved, then
  the system assigns it a complaint number not shared by any other existing
  complaint.
- Given the complaint is saved, when the save completes, then the assigned
  complaint number is displayed to the clerk on screen before they navigate
  away.
- Given 100 complaints are created in sequence (test scenario), when all
  100 numbers are compared, then all 100 are distinct.
- Given two clerks submit "new complaint" requests at effectively the same
  time (concurrent-load test scenario, e.g., 20 simultaneous submissions),
  when all requests complete, then every complaint created receives a
  distinct complaint number with zero collisions — verified by a
  concurrent-load test, not just the sequential check above.

## AC-004 — Update complaint status (verifies US-004, FR-005, FR-006, BR-002, NFR-011)
- Given an authenticated clerk viewing an existing complaint with status
  "New", when they change status to "In Progress" and add the note "site
  visit scheduled", then the complaint's status becomes "In Progress", the
  note is stored, and the change is timestamped.
- Given a complaint currently in status "New", when a clerk attempts to set
  status directly to "Closed" (skipping Resolved/Rejected), then the system
  rejects the transition and shows an error. (resolved at GATE_1 — status/
  transition model confirmed per BR-002/Q-002)
- Given a status change is saved, when the clerk reopens the complaint
  detail view, then the new status and note are visible immediately.
- Given a clerk submits a status-change save, when the request is in
  flight, then a visible in-progress indicator is shown, and if no response
  arrives within the bounded time defined by NFR-011, then the clerk sees a
  clear error/timeout message rather than an indefinitely spinning page.

## AC-005 — List and filter complaints (verifies US-005, FR-005, FR-007, NFR-011)
- Given an authenticated clerk on the complaints list page with complaints
  in multiple statuses created by different clerks, when they apply a
  filter for status "In Progress", then only complaints currently in "In
  Progress" status are shown, regardless of which clerk created them (all
  clerks share full visibility — Assumption A1).
- Given no filter is applied, when the list page loads, then every
  complaint in the system is listed, most-recently-created first (single
  deterministic order — no other ordering is acceptable).
- Given an authenticated clerk searches the list for a complaint number
  that does not exist, when they submit the search, then the system shows
  a clerk-facing "no matching complaint found" message rather than an
  error, a blank screen, or an unfiltered list.
- Given no complaints have ever been logged in the system (zero rows), when
  a clerk opens the complaints list page, then the page shows an explicit
  empty-state message (e.g., "No complaints logged yet") rather than a
  blank table or an error.
- Given a clerk opens the complaints list page or applies a filter, when
  the request is in flight, then a visible in-progress indicator is shown,
  and if no response arrives within the bounded time defined by NFR-011,
  then the clerk sees a clear error/timeout message rather than an
  indefinitely spinning page.

## AC-006 — Citizen checks status (verifies US-006, FR-008, FR-009, BR-004, BR-005, NFR-009, NFR-011)
- Given the public status-lookup page, when a citizen enters a valid, exact
  complaint number and submits, then the result shows the complaint number,
  current status, date logged, and latest status note.
- Given the same lookup, when the result is displayed, then the citizen's
  name and phone number are not shown at all on the public view (see
  BR-005). (resolved at GATE_1 — masking rule confirmed per Q-001; wording
  standardized rev 3, P2-F2, to match FR-009, the MVP scope bullet, and
  BR-005.)
- Given the same lookup, when the result is displayed, then the status
  message shown is one of the fixed, enumerated public status messages
  (one per status, per FR-009/BR-005), and the response/DOM never contains
  the clerk's free-text note, the citizen's name, or the citizen's phone
  number, in any field, attribute, or embedded data (e.g., no leakage via
  a hidden field or API payload the page happens to fetch). (Resolves
  Q-016 per GATE_2 Q7: "option (b), fixed status messages." Added rev 5.)
- Given the citizen enters the complaint number with extra surrounding
  spaces or different letter case (if the format uses letters), when they
  submit, then the lookup still succeeds (basic normalization), unless the
  human specifies complaint numbers are case-sensitive.
- Given a citizen submits a valid-format complaint number, when the lookup
  request is in flight, then a visible in-progress indicator is shown, and
  if no response arrives within the bounded time defined by NFR-011, then
  the citizen sees a clear error/timeout message rather than an
  indefinitely spinning page.

## AC-007 — Not-found message (verifies US-007, FR-010)
- Given the public status-lookup page, when a citizen enters a complaint
  number that does not exist in the system, then the page displays a
  message telling them the number was not found and to check it or contact
  the panchayat office.
- Given an invalid/not-found lookup, when the result is displayed, then no
  information about any other complaint is shown or implied.

## AC-008 — Correct a data-entry mistake (verifies US-008, FR-012)
- Given a complaint was created less than 7 days ago **[pending Q-007 —
  edit-window length]**, when an authenticated clerk edits the citizen
  name, phone, or description and saves, then the updated values are
  stored and the original creation timestamp is unchanged.
- Given a complaint was created more than 7 days ago, when a clerk attempts
  to edit those same fields, then the system denies the edit outright with
  a visible message (no override path exists, since the MVP has no
  supervisor/admin role per Assumption A1). **[pending Q-007 for the
  7-day window length, and Q-003 in case a future role could override this
  — the "deny outright, no override in MVP" outcome itself is fixed as of
  rev 2, per P-F5]**

## AC-009 — View status and edit history (verifies US-009, FR-011, FR-014, FR-016)
- Given a complaint has had two status changes since creation, when an
  authenticated clerk opens the complaint detail view, then both status
  changes are listed in chronological order, each with its timestamp,
  resulting status, and note (if any).
- Given a complaint's citizen name, phone, or description was edited once
  under FR-012, when an authenticated clerk opens the complaint detail
  view, then the edit appears in the history with the previous value, new
  value, editing clerk, and timestamp, distinguishable from status-change
  entries.
- Given an authenticated clerk (admin or regular) opens a complaint's
  detail view, when the page renders, then the citizen's full name and full
  phone number are shown in full (per FR-016) — unlike the public view,
  which shows neither (FR-009/BR-005).

## AC-010 — Fast, low-bandwidth public lookup (verifies US-010, NFR-001, NFR-002)
- Given the public lookup page under normal pilot load (up to a few hundred
  lookups per day), when a citizen submits a valid complaint number over a
  reference 3G-equivalent connection, then the result renders within 3
  seconds.
- Given 5 clerks are simultaneously logged in and actively creating or
  updating complaints, when a citizen performs a lookup at the same time,
  then the lookup still completes within the same 3-second target.

## AC-011 — Protection against complaint-number guessing (verifies US-011, NFR-004, NFR-005, BR-010)
- Given the public lookup endpoint, when 25 lookup requests are submitted
  from the same source IP address within one minute, then requests beyond
  the 20th are throttled or rejected with a rate-limit message. (20/min is
  a confirmed human decision, GATE_2 Q4: "keep 20/min." — resolves Q-013;
  see open-questions.md § Resolved.)
- Given the same endpoint, when 25 lookup requests are submitted from the
  same source IP address as a burst of concurrent/parallel requests within
  one minute (not strictly sequential), then requests beyond the 20th are
  still throttled or rejected with a rate-limit message — the limit holds
  under parallel load, not only under sequential requests.
- Given the system as a whole, when any unauthenticated request is made,
  then there is no endpoint that returns a list of all complaint numbers or
  records (per BR-010 — no bulk public access; the only public capability is
  single-record lookup by an exact, individually supplied complaint number).

## AC-012 — No government ID field exists (verifies NFR-008, BR-009)
- Given the complaint-creation form and the complaint-edit form, when their
  full set of fields is inspected, then no field is present, labeled, or
  accepts input for any government-issued ID number (e.g., Aadhaar, voter
  ID, ration card number).
- Given a request is crafted to submit an extra/unexpected field containing
  what looks like a government ID number, when the request is submitted,
  then the system either ignores/strips the field or rejects the request —
  in no case is such a value persisted.

## AC-013 — Retention / no premature auto-deletion (verifies NFR-010)
- Given the system's configuration/scheduled jobs are inspected (design or
  code review, since a live 12-month wait is impractical pre-release), when
  reviewed, then no job or mechanism exists that deletes a complaint record
  before 12 months have elapsed since its creation.
- Given a complaint created today (test scenario, e.g., with a
  reduced/simulated retention window for testing purposes), when the
  simulated retention window has not yet elapsed, then the complaint record
  is still retrievable by its complaint number.

## AC-014 — Concurrent status updates preserve audit trail (verifies BR-011)
- Given two clerks open the same complaint at nearly the same time, when
  Clerk A saves a status change to "In Progress" with note "site visit
  scheduled" and, before reloading, Clerk B saves a status change to
  "Resolved" with note "fixed same day", then the complaint's final status
  reflects the last save that completed (per last-write-wins), and both
  Clerk A's and Clerk B's changes appear, in order, in the status-change
  history with their respective clerk identity, note, and timestamp — i.e.,
  no update silently disappears from the history even though only one is
  "current."

## AC-015 — Unauthenticated write attempts are rejected (verifies BR-003)
- Given no clerk is authenticated, when a request is made directly to
  create a complaint (bypassing the UI, e.g., a direct API/form-post
  attempt), then the system rejects the request and no complaint record is
  created.
- Given no clerk is authenticated, when a request is made directly to
  change an existing complaint's status or edit its citizen-detail fields,
  then the system rejects the request and the complaint record is
  unchanged.

## AC-016 — No delete capability exists (verifies BR-008)
- Given the clerk-facing UI for an existing complaint, when the available
  actions are inspected, then no button, link, or menu item offers to
  delete the complaint.
- Given a request is crafted to delete a complaint directly (bypassing the
  UI, e.g., a direct API delete-style attempt), when the request is
  submitted, then the system rejects the request and the complaint record
  still exists afterward, unchanged.

## AC-017 — Admin clerk account management (verifies US-014, US-015, US-016, FR-017, FR-018, FR-019, BR-013, BR-016)
- Given an authenticated admin clerk on an account-creation screen, when
  they submit a new clerk's username/initial credentials (marking the
  account as regular or admin), then a new clerk account is created and
  can subsequently be used to log in (FR-001).
- Given an authenticated admin clerk on a password-reset screen for an
  existing clerk account, when they submit a password reset for that
  account, then the target clerk's password is changed and the old
  password no longer authenticates that account.
- Given an authenticated clerk who is NOT an admin clerk, when they attempt
  to reach the account-creation or password-reset screen directly (e.g., by
  URL), then the system denies the action (e.g., redirects away or shows an
  access-denied message) and no account is created and no password is
  changed.
- Given no clerk is authenticated at all, when a request is made directly
  to create an account or reset a password, then the system rejects the
  request.
- Given an admin clerk submits a new-account form with a username that
  already exists, or that is shorter than 3 or longer than 30 characters,
  or that contains characters other than letters/digits/underscores (per
  BR-016), when submitted, then the system rejects the submission with a
  visible validation message and no account is created.
- Given an admin clerk submits a new-account or password-reset form with a
  password shorter than 8 characters (per BR-016), when submitted, then the
  system rejects the submission with a visible validation message and no
  account is created/no password is changed.
- Given an admin clerk successfully creates an account or resets a
  password, when the action completes, then the new/reset password is
  displayed once on-screen to the admin clerk (per BR-016), and the
  affected clerk is required to change that password at their next login.

## AC-018 — Blank/malformed public lookup input (verifies US-006, FR-020, BR-015)
- Given the public status-lookup API endpoint, when a request is submitted
  with the complaint-number field left blank, then the API returns the
  message "Enter a valid complaint number" and no lookup request is made
  against the complaint store.
- Given the public status-lookup API endpoint, when a request is submitted
  with only whitespace in the complaint-number field, then the API returns
  the message "Enter a valid complaint number" and no lookup request is
  made.
- Given the public status-lookup API endpoint, when a request is submitted
  with a value that does not match the expected complaint-number format
  (e.g., contains disallowed characters, or is clearly the wrong
  shape/length), then the API returns the message "Enter a valid complaint
  number" and no lookup request is made — this is distinct from AC-007's
  "not found" message, which only applies to a well-formed number that
  simply has no matching record.
- Given blank, whitespace-only, or malformed-format input submitted
  directly to the API (bypassing the Next.js frontend entirely, e.g., a
  direct HTTP request), when database/query activity is inspected for that
  request, then no statement touching the complaint table executes at all
  — validation happens before any query is issued, and this holds
  regardless of whether the request originated from the frontend or a
  direct API call.

## AC-019 — Bootstrap of the first admin clerk account (verifies US-017, FR-015)
- Given a fresh deployment with no admin clerk account yet in existence,
  when the operator's bootstrap mechanism (e.g., seed script or initial
  config value, per Assumption A11) runs, then exactly one admin clerk
  account exists afterward, with credentials the operator can retrieve or
  that were supplied as bootstrap input.
- Given that bootstrapped admin clerk account, when the operator (or
  whoever receives the credentials) logs in with it, then login succeeds
  (FR-001) and the account can perform FR-017 (create a clerk account) and
  FR-018 (reset a clerk's password).
- Given the bootstrap mechanism is run a second time on a deployment that
  already has an admin clerk account, when it runs, then it does not
  silently create a duplicate/conflicting admin account (exact behavior —
  no-op vs. error — is left to the architect, but data integrity must be
  preserved).
