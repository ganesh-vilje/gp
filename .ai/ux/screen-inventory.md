# Screen Inventory

Six screens (one public, five clerk-app) cover every route in information-architecture.md. "n/a" states are marked with why, per spec §42 — none are left undefined.

## 1. Public Status Lookup
- **Route:** `/` · **Roles:** citizen, unauthenticated · **Entry points:** direct URL, given verbally/on paper by a clerk.
- **Purpose:** let a citizen see a complaint's current status without an account.
- **Primary action:** submit a complaint number.
- **Data shown:** input field only, until a result returns: `{complaint_number, status, public status message, date logged}`. Never name, phone, or clerk note.
- **States:**
  - *Button/state-message live region (A11Y-12):* the "Check status" button's label and its adjacent state-message text share one `role="status"` / `aria-live="polite"` container — the same convention as the Loading Indicator (component-spec.md #11) — so every transition below ("Preparing…" → live → "Retry" → "Unavailable — reload the page" → "Checking…" → result) is announced automatically to screen-reader users without a forced focus move. See user-flows.md Flow 5 step 1.
  - *Empty (initial), CSRF seed pending:* field is enterable, but "Check status" is `aria-disabled="true"` with its label showing "Preparing…" until the background `GET /api/session` resolves (UX-F3) — the field itself is never disabled, so a fast typist isn't blocked from starting to type. See user-flows.md Flow 5 step 1a.
  - *Empty, ready:* single field + live button, no result area — the normal steady state once the seed resolves (typically well under 1s; no visible transition).
  - *Seed slow (>4s):* the "Preparing…" label gets a small retry affordance — "Taking longer than expected. Retry" (text button that re-fires the seed request) — so the citizen is never stuck indefinitely on a silent disabled button.
  - *Seed failed (network/5xx on the seed call itself):* button remains `aria-disabled`, label becomes "Unavailable — reload the page", same wording family as the Unavailable (503) state below.
  - *Invalid input (no request made):* "Enter a valid complaint number", field marked invalid, no loading state entered.
  - *Loading:* button disabled, "Checking…".
  - *Success:* result card-free block with number/status/message/date.
  - *Not found:* "We couldn't find a complaint with that number…".
  - *Rate-limited (429):* "Too many attempts from this network. Please wait a minute and try again." (UX-F4 — reworded from "this device"; the limit is per IP and carrier NAT commonly shares one IP across many devices).
  - *Unavailable (503):* "The service is temporarily unavailable. Please try again in a few minutes."
  - *Timeout/network error:* "The server is taking too long. Please try again."
  - *Cookies disabled:* "This page needs cookies enabled…" — this is also the message shown if the CSRF seed itself fails because cookies are blocked, rather than the generic "Unavailable" wording.
  - *No JavaScript:* `<noscript>` message, rendered without any script.
  - *Unauthorized:* n/a — no authentication concept on this page.
  - *404 (not-found route):* n/a — this is the only public route; any other path is a generic static 404 (see Screen 6).
- **Focus order:** label → input → "Check status" button → result block (when present); the result block, when it appears, is not auto-focused (it's adjacent to the button the citizen just activated, so a screen reader continues linearly into it without a forced focus jump).
- **Responsive:** single column, mobile-first (320 px baseline), full-width field and button ≥44×44 px touch target; identical layout at all widths, just wider margins above 600 px.

## 2. Login
- **Route:** `/login` · **Roles:** unauthenticated visitor (clerk or admin clerk) · **Entry points:** direct URL, redirect from any protected route, redirect after logout/session expiry.
- **Purpose:** authenticate a clerk.
- **Primary action:** submit username + password.
- **Data shown:** username, password fields only.
- **States:**
  - *Empty:* blank form.
  - *Loading:* button disabled, "Signing in…".
  - *Error — invalid credentials (401):* generic message, password cleared.
  - **Required fields (A11Y-02-followup):** both fields (username, password) are required. Native `required` and `aria-required="true"` attributes are retained on each field, but since every field on this screen shares the same status, the per-field visible "(required)" suffix is omitted and replaced by a single top-of-form line, "All fields are required" — same convention as Change Password below.
  - *Error — rate-limited (429):* countdown + disabled submit.
  - *Error — network/timeout:* "The server is taking too long. Please try again."
  - *Success:* redirect to `/change-password` (if forced) or `/complaints`.
  - *Already authenticated:* visiting `/login` with a valid session redirects straight to `/complaints` — no form flash.
  - *Empty-data state:* n/a — a login form has no "no data" condition.
  - *Session-expiry banner (arrived via redirect):* "Your session has expired. Please log in again." — on appearance, focus moves to the banner itself (same rule as the Form Error Summary, component-spec.md #8/#6) rather than leaving focus on `<body>`, so a screen-reader user lands on the explanation immediately instead of a blank-feeling form (A11Y-06).
  - *Unauthorized:* n/a — this screen is the entry point for authorization, not a protected one.
  - *404:* n/a — fixed route.
- **Focus order:** (session-expiry banner, if present) → username → password → show/hide toggle → submit.
- **Responsive:** centered single-column form, works down to 320 px; no layout change at wider widths beyond max-width centering.

## 3. Change Password
- **Route:** `/change-password` · **Roles:** any authenticated clerk (forced when `must_change_password=true`; the voluntary trigger below is **pending human confirmation, OQ-9 — not committed scope** until answered at Gate 4) · **Entry points:** forced redirect after first login/reset; "Change password" in user menu (voluntary entry point — pending confirmation, see below).
- **Purpose:** set a new password.
- **Primary action:** submit new password (+ current password, for the voluntary path only).
- **Scope note (PROD-F2):** the forced path (redirect after first login/admin reset) is committed MVP scope and has a backing requirement chain (tech-stack session-rotation design). The **voluntary** "Change password" menu action — letting a clerk change their password anytime, not just when forced — has no backing FR and is marked **pending human confirmation (OQ-9), not committed scope**; if the human declines it at Gate 4, remove the menu item and the "current password" field/voluntary states below, leaving only the forced flow.
- **Data shown:** password fields only; a live length counter (≥12 chars) and policy hints.
- **States:**
  - *Empty:* blank form, policy hints visible (not only revealed on error).
  - *Loading:* "Updating…".
  - *Error — policy violation (length/similarity/common-password):* inline, field-specific.
  - *Error — mismatch (confirm ≠ new):* inline.
  - *Error — wrong current password (voluntary path only):* generic, matches Login's wording.
  - *Error — network/timeout:* standard message.
  - *Success:* confirmation, then redirect to `/complaints`; all other sessions for the account are revoked (server-side), reflected by a note: "You've been signed out of any other devices."
  - *Forced-mode lockout of navigation:* while `must_change_password=true`, the nav bar and all other links are hidden/disabled — this screen is the only reachable one besides logout.
  - *Empty-data / Unauthorized / 404:* n/a — a form-only screen behind auth; unauthenticated visits redirect to `/login`.
- **Required fields (A11Y-02):** every field on this screen is required — current password (voluntary path only), new password, confirm new password. Native `required` and `aria-required="true"` attributes are retained on each field, but since every field shares the same status, the per-field visible "(required)" suffix is omitted here and replaced by a single top-of-form line, "All fields are required" (contrast with the new-complaint and status-update forms below, which mix required and optional fields and so need per-field suffixes).
- **Focus order:** (current password, voluntary path only) → new password → show/hide toggle → confirm new password → submit.

## 4. Complaints (list + inline detail — no separate detail route, see information-architecture.md)
- **Route:** `/complaints` · **Roles:** clerk, admin clerk (identical data access, BR-013) · **Entry points:** default post-login landing page, nav link.
- **Purpose:** log new complaints; find, review, and update existing ones.
- **Primary action:** "+ New complaint" (list level) / "Update status" (detail level).
- **Data shown:** list — complaint number, status, description snippet/date (no phone/name per response-minimisation in tech-stack; PROD-F3 — "description snippet," not "subject," since there is no separate subject field); detail — full citizen name/phone (FR-016), description, status, combined status+edit history (FR-011/FR-014).
- **Find/search controls (UX-F1):** two controls above the list, not one: (1) "Find by complaint number" (exact-match quick jump, unchanged from rev 1 — this is the control FR-005 requires, "find an existing complaint by number or from a list"), and (2) a new **"Search by name or phone"** text input (partial-match, debounced ~300ms, searches the citizen name and phone fields clerks already see per FR-016). Name/phone search has **no backing FR** — it is a UX addition motivated by UX-F1 (the list only grows, NFR-010, and a clerk fielding a phone call without the complaint number in hand), built on data clerks already see on this authenticated route (FR-016), never exposed publicly. **Pending human confirmation at Gate 4 — see open-questions.md OQ-10**; if declined, this search box is removed and only "Find by complaint number" plus pagination remain. Both controls are additive filters alongside the existing status filter; clearing all three returns to the full list. Search and status-filter combine with AND.
- **Search-result announcement (A11Y-13):** a `role="status"` / `aria-live="polite"` region beside the search box announces the settled result once the ~300ms debounce fires — e.g. "12 complaints shown" — or the no-match message ("No complaints match \"{term}\"."); the same region is reused to announce "Loading more" and "All complaints shown" during pagination (see states below), so a screen-reader user is told the outcome without needing to re-scan the list.
- **Pagination / scale (UX-F1, NFR-010 — the record set only grows, no delete):** the list loads in **pages of 25, most-recent-first**, with a **"Load more" button** at the bottom of the rendered rows (incremental load, not numbered pages — matches the low-density, glance-then-scroll usage pattern of driver U2 better than page-number navigation). Loading more never replaces already-rendered rows, so scroll position is preserved. A status/search filter change resets to the first page of the new filtered set.
- **States (list):**
  - *Loading (first page):* skeleton/spinner.
  - *Empty, no data:* "No complaints logged yet. Create the first one."
  - *Empty, filtered/searched:* "No complaints match this filter." (search box additionally echoes the term: "No complaints match \"{term}\".", announced via the search-result live region, A11Y-13, above)
  - *Success:* rows, most-recent-first, status filter and/or search applied.
  - *Loading more (pagination):* the "Load more" button shows a "Loading…" label and is disabled; already-rendered rows stay visible and interactive (this is a distinct, additive loading state, not a full-list reload).
  - *Load-more error:* the button reverts to its normal label plus an inline message directly above it, "Couldn't load more complaints. Retry." — already-loaded rows are unaffected.
  - *End of list reached:* the "Load more" button is replaced by static text, "All complaints shown" — never left as a dead disabled button.
  - *Error (first page):* "Couldn't load complaints. Retry."
  - *Unauthorized:* n/a at this route for any authenticated clerk (both roles have equal access); an expired/absent session instead redirects to `/login` (handled globally, not a distinct list state).
- **States (detail panel):**
  - *Loading:* spinner inside the panel.
  - *Success:* full detail + Activity timeline.
  - *Error:* "Couldn't load this complaint. Retry."
- **States (new-complaint form):** empty, validating (inline + summary), submitting, server-error, success (complaint-number confirmation), timeout — see user-flows.md Flow 2. **Required fields (A11Y-02):** citizen name, phone, and description are all required — none optional on this form; each label carries a visible "(required)" suffix plus `required`/`aria-required="true"` (component-spec.md #1/#2).
- **States (status-update form):** empty (only legal next statuses shown), submitting, concurrent-edit advisory banner, success, error/timeout — see Flow 3. **Required/optional fields (A11Y-02):** the status choice is required; the free-text note is the one genuinely **optional** field in the product and is labelled "Note (optional)" rather than carrying a "(required)" suffix — the only field in the whole product without one.
- **States (edit-details form):** available (within window) / disabled-with-tooltip (window passed, A8 default 7 days); empty, validating, submitting, success, error/timeout — see Flow 4. **Required fields:** same three fields/rules as the new-complaint form above.
- **404:** n/a — any stray `/complaints/*` path is host-rewritten to this same shell (tech-stack decision), so a 404 state is architecturally impossible here.
- **Responsive:** ≥900 px shows list and detail side by side (list ~40%, detail ~60%); below 900 px the detail becomes a full-width panel that replaces the list view with a "Back to list" control.
- **Focus order (A11Y-05):** ≥900 px — status filter → search box → find-by-number box → "+ New complaint" → list rows (top to bottom) → "Load more" (if present) → (if a row is expanded) into the detail panel's heading. Below 900 px, when the detail panel is showing, the DOM order is **"Back to list" control first, then the panel heading and content** — matching the visual top-to-bottom order in the collapsed single-column layout, so keyboard/screen-reader users meet the way back before the detail content, not after it.

## 5. Accounts
- **Route:** `/accounts` · **Roles:** admin clerk only · **Entry points:** nav link (admin only), direct URL by anyone.
- **Purpose:** create clerk accounts and reset passwords.
- **Primary action:** "+ New clerk account" / "Reset password" per row.
- **Data shown:** username, role, created date per account; one-time password shown once per create/reset action.
- **States:**
  - *Loading:* spinner.
  - *Empty (only self):* "No other clerk accounts yet."
  - *Success:* account list, self-lockout advisory banner shown when only one admin exists.
  - *Error:* "Couldn't load accounts. Retry."
  - *Create form — empty/validating/submitting/error (username taken/invalid)/success:* success shows the one-time password once with a mandatory "I have recorded this password" acknowledgment before dismissal (ux-decisions.md decision 3). **Both fields (username, role) are required** — no optional fields on this form.
  - *Reset — confirmation dialog / submitting / success (same OTP-display pattern) / error.*
  - *OTP-display screen open (UX-F2):* until the "I have recorded this password" checkbox is checked, the screen is guarded against every exit path, not only Escape/Done — see component-spec.md #9 and user-flows.md Flow 6 step 3a for the full list (tab close, browser back, typed-URL navigation).
  - *Unauthorized (403):* regular clerk reaching this route by URL sees "You don't have permission to view this page. Contact your admin clerk for account changes." with a link back to Complaints — rendered explicitly, not a silent redirect (FR-019).
  - *404:* n/a — fixed route, no dynamic segments.
- **Responsive:** single-column list at all widths (small dataset, ≤6 rows expected); forms/dialogs are full-width below 600 px, centered modal above it.
- **Focus order:** advisory banner (if shown) → "+ New clerk account" → account rows (username → role → created date → "Reset password") top to bottom.

## 6. Generic 404 (fallback, both apps)
- **Route:** any path not matched by the above (e.g. a mistyped domain path outside the public/clerk shells) · **Roles:** anyone.
- **Purpose:** avoid a platform default error page.
- **Primary action:** link back to `/` (public site) or `/complaints` (clerk app), depending on which build served it.
- **Data shown:** none.
- **States:** *success (i.e., the 404 itself is the only state)* — "Page not found."; all other states (loading/empty/error/unauthorized) are **n/a — a static page with no data or auth dependency.**
- **Responsive:** single centered block, all widths.
