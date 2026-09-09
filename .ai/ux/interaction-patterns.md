# Interaction Patterns

## Forms and validation timing
- **On blur** for field-level checks (required, format, length) — feedback the moment a clerk/citizen leaves a field, before they've moved on mentally.
- **On submit**, re-validate everything and, if any field fails, show a **top-of-form error summary** ("There are 2 problems with this form") whose items are links that move focus to the offending field — required for screen-reader users who don't see inline errors below the fold (WCAG 2.2 SC 3.3.1/3.3.3).
- **Never validate on every keystroke** — it is noisy and unnecessary at this data-entry volume (driver U2), except a live character counter near the max-length limits (BR-014) which updates as the clerk types, so they see the limit coming rather than hitting a wall.
- **Server response is the final authority** on every field (defence in depth) — a 422 always maps back to a field-level error even though the client already checked it.

## Required-field indication (A11Y-02)
Every required field's `<label>` carries a visible, non-colour suffix — **"(required)"** — in addition to `required` and `aria-required="true"` on the control itself (never colour or an asterisk alone, since an asterisk needs a legend and colour alone fails non-colour-dependent users). Fields that are genuinely optional are labelled the opposite way — **"(optional)"** — so the convention reads unambiguously either way, rather than leaving unmarked fields ambiguous. Per form: new-complaint and edit-details forms have **no optional fields** (name, phone, description all required); the status-update form has exactly **one** optional field, the free-text note ("Note (optional)") — every other field in the product (login, change-password, create-account) is entirely required. See component-spec.md #1 (Text Input) and #2 (Textarea) and screen-inventory.md per-screen notes.

## Find, search, and pagination on the Complaints list (UX-F1, FR-005, NFR-010)
The record set has no delete and no MVP date filter, so it only grows over the life of the office's use of the tool:
- **Two independent find controls above the list:** "Find by complaint number" (exact match, jumps straight to the row) and **"Search by name or phone"** (partial match against the citizen name/phone clerks already see per FR-016, debounced ~300ms — never fires on every keystroke). Both combine with the existing status filter (AND); clearing all three shows the full list again.
- **Result announcement (A11Y-13):** once the ~300ms debounce settles and the filtered result returns, a `role="status"`/`aria-live="polite"` region near the search box announces the outcome in plain language — "12 complaints shown" or the no-match message ("No complaints match \"{term}\".") — so a screen-reader user isn't left re-reading the list to discover what changed. The same region announces "Loading more" while a pagination request is in flight and "All complaints shown" at the end of the list (see below), rather than adding a second, competing live region.
- **Incremental load, not numbered pages:** 25 rows per load, a **"Load more"** button beneath the rendered rows rather than page-number controls — clerks scan recent activity top-down rather than jumping to an arbitrary page number, and incremental load is simpler to keep accessible (no page-count arithmetic to announce). Loading more appends rows without moving scroll position or collapsing any open detail panel.
- **Distinct states**, none reusing the first-load spinner: loading-more (button → "Loading…", disabled; existing rows remain interactive), load-more error (button reverts to its normal label; a dedicated inline message — "Couldn't load more complaints. Retry." — appears above it without disturbing already-loaded rows), end-of-list ("Load more" is replaced by static text "All complaints shown," never left as a dead disabled control).
- Changing the status filter or the search term resets to page one of the new filtered/searched set.

## Restricting invalid choices (a recurring pattern, not just Flow 3)
Wherever the business rules define a legal subset of options, the UI presents only that subset instead of a free choice plus a rejection message:
- Status-update control offers only the statuses reachable from the current one (BR-002).
- "Edit details" is hidden/disabled once the edit window has passed (A8), not merely rejected on submit.
- The status-update form for a citizen never exists — public users have no write capability at all (BR-003).

## Feedback: inline banners, not toasts
All success/error/warning feedback is an **inline, persistent element** near the action (top of a form, top of a panel) rather than a transient global toast. Rationale: transient toasts are missed on a shared office screen with someone glancing over, are not reliably announced to screen readers, and add a dependency-free but nontrivial amount of JS/CSS for no material benefit at this scale (driver U5, U7). Exception: the "logged out" / "session expired" message, which must survive a full navigation to `/login` and is rendered as a banner on the destination page, not a toast that could disappear before the page loads.

## Loading / in-flight pattern (uniform across all three core workflows, per NFR-011)
Every request that writes or looks up data:
1. Disables the triggering control immediately.
2. Shows a short present-tense label ("Checking…", "Saving…", "Signing in…") next to or inside the control — not a full-page spinner that hides context.
3. Aborts and shows **"The server is taking too long. Please try again."** if no response arrives within 10 s (tech-stack's client abort bound).
4. Re-enables the control and preserves all entered data on any failure.
5. **(A11Y-03)** The label container itself — not just the control — carries `role="status"` and `aria-live="polite"`, so "Checking…"/"Saving…" and the subsequent result text are announced to screen-reader users automatically, without focus moving away from where the user was. `aria-busy="true"` on the control is retained in addition to this, not instead of it — the two serve different assistive-tech needs (busy state vs. announced text change). This applies uniformly to every use of the Loading Indicator (component-spec.md #11), including the Complaints list's "Loading more" state above.

## Empty states
Every list/collection screen distinguishes **"nothing exists yet"** from **"nothing matches your filter"** with different copy (see screen-inventory.md) — conflating them makes a clerk think the office has no complaints when they've just filtered too narrowly.

## Confirmation and "destructive-adjacent" actions
There is **no delete action anywhere** in this product (BR-008) — so no delete-confirmation pattern is needed. The only disruptive (not destructive-to-data) actions are:
- **Reset a clerk's password** — ends that clerk's sessions. Confirmed via a modal dialog stating the consequence in plain language before proceeding (Flow 6, step 4).
- **Logout** — not confirmed (reversible in one click, not disruptive to anyone else).
- **One-time password display** — not a confirmation but an *acknowledgment gate*: the admin must check "I have recorded this password" before leaving the screen, because the value is genuinely unrecoverable afterward (BR-016). This is the single most important "make it hard to make this mistake" moment in the product.

## Complaint number display
Wherever a complaint number is shown to a clerk or citizen (creation confirmation, public lookup result), it is set in a monospaced, letter-spaced, large type size with a **Copy** button — it is read aloud, written on paper, and re-typed by people, so legibility and copy-ability matter more than visual consistency with body text.

## Public status messages (fixed, enumerated set — FR-009/BR-005, Q-016 resolved)
| Status | Public message |
|---|---|
| New | "Your complaint has been received and is awaiting review." |
| In Progress | "Your complaint is being worked on." |
| Resolved | "Your complaint has been marked as resolved." |
| Rejected | "Your complaint was reviewed and will not be taken further. Contact the panchayat office if you have questions." (UX-F5 — reworded from "...reviewed and closed without further action," which used "closed" as a verb even though "Closed" is a distinct, separate status; this avoids implying the complaint's status is now literally "Closed.") |
| Closed | "This complaint has been closed." |
These five strings are the **entire** public-facing status vocabulary; the clerk's free-text note is never interpolated into them.

## Rate-limit / backoff countdown
Any 429 response with a `Retry-After` header drives a plain countdown ("Try again in 42s") that decrements once per second and re-enables the control at zero — no page reload required, no CAPTCHA, matching the human's explicit "keep it soft" rate-limit decision.

## Concurrent-edit awareness (BR-011)
A non-blocking advisory banner, not a hard lock (see user-flows.md Flow 3) — informs without preventing the write, because BR-011 explicitly allows last-write-wins as long as both edits remain in history.

## Responsive behaviour
- **Public page:** single column at every width; the only responsive change is margin, from edge-to-edge padding at 320 px to a centered ~480 px column above ~600 px.
- **Clerk app:** single column below 900 px (list OR detail, with a "Back to list" control); list-beside-detail at ≥900 px. Forms/modals are full-width sheets below 600 px and centered dialogs above it.
- Breakpoints and exact values are defined in design-tokens.md; all layout uses relative units so the page reflows correctly at 320 px CSS width (400% zoom on a 1280 px viewport) rather than clipping (see accessibility-strategy.md).
