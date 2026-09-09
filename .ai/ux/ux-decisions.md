# UX Decisions

## Revision 3 changes (findings addressed)
| Finding | What changed | Where |
|---|---|---|
| A11Y-12 | Public lookup "Check status" button label/state-message container now explicitly `role="status"`/`aria-live="polite"` (same convention as Loading Indicator #11), so "Preparing…" → live → "Retry" → "Unavailable — reload the page" transitions are announced | screen-inventory.md Screen 1; user-flows.md Flow 5 step 1; component-spec.md #11 |
| A11Y-13 | Added a `role="status"`/`aria-live="polite"` region announcing the debounced search-result count or no-match message, and reused for "Loading more"/"All complaints shown" | interaction-patterns.md "Find, search, and pagination"; screen-inventory.md Screen 4; component-spec.md #11 |
| A11Y-14 | Text Input and Textarea "disabled (during submit)" state corrected to `aria-disabled` + `readonly` (never native `disabled`), consistent with Button #3 and Countdown #14 | component-spec.md #1, #2 |
| A11Y-15 | "Leave anyway?" route-change confirmation over the OTP dialog: Escape = "Stay" (default-focused); "Stay" returns focus to the OTP checkbox; only one dialog in the focus trap at a time | user-flows.md Flow 6 step 3a-iii; component-spec.md #9 |
| PROD (US-005 citation) | Corrected FR-005 citation — it requires only "by number or from a list"; name/phone search reclassified as a UX addition (UX-F1, NFR-010, FR-016), pending human confirmation | screen-inventory.md Screen 4; user-flows.md Flow 4; open-questions.md OQ-10 (new); ux-decisions.md traceability row US-005 |
| A11Y-06-followup | Session-expiry banner now stated as NOT dismissible in both places (was inconsistent) | user-flows.md Flow 1 step 7; component-spec.md #6 (unchanged, already correct) |
| A11Y-10-followup | "200% browser zoom" corrected to "320 px CSS width (400% zoom on a 1280 px viewport)" | interaction-patterns.md "Responsive behaviour" |
| A11Y-02-followup | Login screen given the same required-fields note as Change Password (native required/aria-required retained, visible suffix omitted, top-of-form "All fields are required" line) | screen-inventory.md Screen 2; Screen 3 (note text aligned) |
| A11Y-05-followup | "Load more" added to the Complaints focus order, after the last row | screen-inventory.md Screen 4 |

## Revision 2 changes (findings addressed)
| Finding | What changed | Where |
|---|---|---|
| UX-F1 | Added "Search by name or phone" + "Find by complaint number" controls and an explicit 25-row incremental "Load more" pagination pattern with its own loading/error/end-of-list states | screen-inventory.md Screen 4; user-flows.md Flow 4; interaction-patterns.md (new section); component-spec.md #1; information-architecture.md; traceability table below (US-005) |
| UX-F2 | OTP acknowledgment gate now blocks tab close (`beforeunload`), browser back/forward, and typed-URL navigation, not only Escape/Done, until the checkbox is checked | component-spec.md #9; user-flows.md Flow 6 step 3a; screen-inventory.md Screen 5 |
| UX-F3 | Defined the pre-CSRF-seed window explicitly: `aria-disabled` "Preparing…" button, live once seeded, "Retry" affordance if slow >4s, distinct failure messaging | user-flows.md Flow 5 step 1/1a-d; screen-inventory.md Screen 1 |
| A11Y-01 | New `--color-border-interactive` (#767676, 4.54:1) as the sole default-state boundary for interactive controls; `--color-border` restricted to decorative dividers | design-tokens.md; component-spec.md #1, #2, #5, #10 |
| A11Y-02 | Visible "(required)"/"(optional)" label convention + `required`/`aria-required`; per-form enumeration (status note is the only optional field) | component-spec.md #1, #2; interaction-patterns.md (new section); screen-inventory.md Screens 3, 4, 5 |
| A11Y-03 | Loading label container now `role="status"`/`aria-live="polite"` in addition to `aria-busy` | component-spec.md #11; interaction-patterns.md loading pattern |
| UX-F4 | 429 wording changed from "this device" to "this network" (public lookup + login-adjacent copy) | screen-inventory.md Screen 1; user-flows.md Flow 5 |
| A11Y-04 | Countdown/Retry Timer submit button now explicitly `aria-disabled`, cross-referenced to the Button rule | component-spec.md #14 |
| A11Y-05 | Per-screen focus-order notes added, including detail-panel-first-with-"Back to list" rule below 900px | screen-inventory.md Screens 1, 2, 4, 5 |
| A11Y-06 | Session-expiry banner on `/login` now moves focus on appearance, same rule as Form Error Summary | screen-inventory.md Screen 2 |
| A11Y-07 | `<html lang="en">` stated as an explicit build requirement, tied to OQ-1; per-fragment lang out of scope | accessibility-strategy.md |
| A11Y-08 | List Row now specifies `<ul>`/`<li>` (or `role="list"`) wrapping | component-spec.md #10 |
| PROD-F2 | Voluntary "Change password" menu action marked "pending human confirmation (OQ-9), not committed scope" | information-architecture.md; screen-inventory.md Screen 3; open-questions.md OQ-9 |
| UX-F5 | Rejected public message reworded to avoid using "closed" as a verb | interaction-patterns.md public status messages table |
| UX-F6 | Status icons explicitly considered and rejected (not silently omitted), with rationale | visual-direction.md |
| PROD-F3 | "subject/date" reworded to "description snippet/date" | screen-inventory.md Screen 4; component-spec.md #10 |
| A11Y-09 | Skip link added to clerk-app top nav | information-architecture.md; accessibility-strategy.md |
| A11Y-10 | "200% zoom" corrected — 320px CSS width stated directly, zoom-percentage framing dropped/corrected to 400% context | accessibility-strategy.md |
| A11Y-11 | OTP checkbox and status radios: clickable area explicitly includes label/padding, ≥24×24 CSS px | component-spec.md #5, #9 |

## How the product will feel to use, and why
The product should feel like a plain, trustworthy office register brought online. For the citizen, checking a status is a single obvious box and a fast, plain-language answer — forgiving of typos, usable on a cheap phone on a slow connection, never demanding technical understanding of what a "session" or "cookie" is unless absolutely necessary. For the clerk, it feels like a fast, low-friction logbook: one clear primary action per screen, choices restricted to what's actually valid (only legal next statuses, only an editable window that's still open) rather than accepting anything and scolding afterward, and visible confirmation and history everywhere so nothing ever feels like it silently vanished — which matters because the product's entire value proposition to the office is an *auditable* record. Nothing sparkles: no animation, no decorative imagery, no jargon. Plain type, strong contrast, and generous tap targets make the tool work equally well on a five-year-old Android phone in bright sunlight and on a modest office desktop, inside the ~120 KB / 3-second budget the technology stack sets.

## Screens per role
- **Citizen:** *Public Status Lookup* (`/`) — enter a complaint number, see its status, nothing else.
- **Clerk (regular):** *Login*; *Change Password*; *Complaints* (log new complaints, find/filter/update existing ones, view history, correct details within the edit window).
- **Admin clerk:** all of the above, plus *Accounts* (create clerk accounts, reset passwords).
- **Fallback (all):** a generic *404* for any unmatched path.

## The 3–5 UX decisions that most shape the product
1. **Restrict the status-update control to only the legally reachable next statuses (radio group of ≤3 options), instead of a free choice validated after submit.** Alternative rejected: a full 5-option dropdown with a server-side rejection message for illegal transitions. Driver: BR-002 (no skipping steps, no direct New→Rejected/Resolved/Closed) — preventing the mistake is cheaper for a busy clerk than explaining it after the fact.
2. **The public page shows only five fixed, pre-written status messages — never any part of the clerk's free-text note.** Alternative rejected: showing a sanitized/truncated version of the clerk's note. Driver: FR-009/BR-005 (human decision at GATE_2, "option (b), fixed status messages") and NFR-009 — a clerk's note may reference other people, addresses, or informal language never meant for public view.
3. **The one-time password screen requires an explicit "I have recorded this password" acknowledgment before it can be closed**, rather than a passive warning beside an "OK" button. Alternative rejected: a dismissible confirmation with warning text only. Driver: BR-016 — the password is genuinely unrecoverable after this screen closes, and the cost of an accidental dismiss is a locked-out colleague and a second reset cycle.
4. **A concurrent-edit conflict is shown as a non-blocking advisory banner ("someone else may have just updated this"), not a hard lock requiring a reload before any write is accepted.** Alternative rejected: a blocking optimistic-lock error (HTTP 409) that refuses the write until the clerk reloads. Driver: BR-011 explicitly allows last-write-wins on current status as long as both writers' history entries survive — a hard block would contradict that allowance and add friction for a small team working the same queue.
5. **The public lookup performs its own instant, no-network client-side check for blank/malformed complaint numbers**, showing "Enter a valid complaint number" with zero round trips, while the API remains the sole binding authority (FR-020/BR-015 unchanged). Alternative rejected: always submitting to the server and waiting for its response to show this message. Driver: NFR-001 (3-second/3G budget) — skipping a network round trip for an error class the client can already detect matters on a slow connection.

## Accessibility commitments
- Every interactive element is keyboard-operable in logical focus order with a visible, non-suppressed focus ring; form errors are linked to their fields (`aria-describedby`) and announced via `aria-live`, never conveyed by colour alone.
- Text and UI-component contrast meets WCAG 2.2 AA (body text ≥19.5:1, primary actions/links ≥6.4:1, all five status colours ≥4.5:1 — see design-tokens.md); every interactive control's default-state boundary uses `--color-border-interactive` (4.54:1), not the decorative divider token (rev 2, A11Y-01); touch targets are ≥44×44 CSS px on the public page and ≥24×24 CSS px elsewhere, with checkbox/radio click areas explicitly including label text (A11Y-11).
- Required/optional status is stated visibly on every field, never by colour alone (A11Y-02); loading states are announced via `role="status"`/`aria-live="polite"` in addition to `aria-busy` (A11Y-03); focus moves to session-expiry and form-error banners on appearance (A11Y-06).
- The interface reflows correctly at 320px CSS width and uses no animation beyond an optional 150ms fade that is skipped under `prefers-reduced-motion`; `<html lang="en">` is a stated build requirement (A11Y-07).

## Traceability — user story → screen(s)/flow(s)
| Story | Covered by |
|---|---|
| US-001 Clerk login | Login screen · Flow 1 |
| US-002 Log a new complaint | Complaints screen (new-complaint form) · Flow 2 |
| US-003 Receive a complaint number | Complaints screen (creation success state) · Flow 2 |
| US-004 Update complaint status | Complaints screen (status-update form) · Flow 3 |
| US-005 List and filter complaints | Complaints screen (list, status filter, "Find by number" — the FR-005 mechanism — plus "Search by name/phone," a UX addition pending confirmation, see OQ-10, and pagination) · Flow 4 |
| US-006 Citizen checks status | Public Status Lookup · Flow 5 |
| US-007 Not-found message | Public Status Lookup (not-found state) · Flow 5 |
| US-008 Correct a data-entry mistake | Complaints screen (edit-details form) · Flow 4 |
| US-009 View status history | Complaints screen (Activity timeline) · Flow 4 |
| US-010 Fast, low-bandwidth public lookup | Public Status Lookup (static shell, budgeted island) · Flow 5 |
| US-011 Protection against number-guessing | Public Status Lookup (429/503 states) · Flow 5 |
| US-012 Trust in concurrent edits | Complaints screen (concurrent-edit advisory banner) · Flow 3 |
| US-013 Confidence data is safe from unauthorized change/loss | Complaints screens generally — no delete affordance exists anywhere in the IA · Flows 2–4 |
| US-014 Admin creates a clerk account | Accounts screen (create-account form) · Flow 6 |
| US-015 Admin resets a clerk's password | Accounts screen (reset-password action) · Flow 6 |
| US-016 Confidence only the admin manages accounts | Accounts screen (403/"not authorized" state; nav-visibility rule) · Flow 6 |
| US-017 Bootstrap the first admin account | n/a — out-of-band operator console script (FR-015, tech-stack `bootstrap-admin`), no UI screen |
