# Component Specification

Plain HTML elements styled with the tokens in design-tokens.md — no component library (per tech-stack.md). ARIA is added only where semantic HTML is insufficient.

## 1. Text Input
**Purpose:** single-line data entry (username, password, phone, complaint number, citizen name, and — UX-F1 — the Complaints list's "Search by name or phone" and "Find by complaint number" boxes, using `type="search"` semantics where appropriate).
**Anatomy:** `<label>` + `<input>` + optional help text (`--text-xs`) + optional inline error.
**Variants:** text, password (with a visible show/hide toggle — a real button, not an icon-only control, labelled "Show password"/"Hide password"), tel-like text (complaint number/phone use `inputmode="numeric"`/appropriate pattern but remain plain text inputs, not `type="number"`, to avoid spinner controls and locale-based formatting surprises).
**States:** default (border `--color-border-interactive`, 4.54:1 on white — A11Y-01, rev 2; not `--color-border`, which at 1.40:1 is too faint to serve as the sole boundary of an interactive control per WCAG 1.4.11), focus (`:focus-visible` ring, `--color-focus`), filled, disabled-during-submit (**A11Y-14:** `aria-disabled="true"` + `readonly` — never the native `disabled` attribute — so a field that currently has focus when the form is submitted (e.g. via Enter) is not abruptly blurred or dropped from the tab order mid-submit; consistent with Button #3 and Countdown/Retry Timer #14), invalid (`aria-invalid="true"`, red border `--color-error`, error text below), valid (no special styling — absence of error is sufficient, per "don't overdecorate success").
**Required/optional (A11Y-02):** every label states its field's status explicitly and visibly — "(required)" or "(optional)" as a plain-text suffix, never colour/asterisk alone. Required fields additionally carry `required` and `aria-required="true"`. See interaction-patterns.md "Required-field indication" for the per-form enumeration (e.g. the status-update note is the one optional field on that form; name/phone/description are required on the complaint forms).
**Keyboard:** standard text-input behaviour; Tab in/out; no custom key handling.
**ARIA:** `<label for>` association; `aria-describedby` pointing to help/error text; `aria-invalid` when in error state.
**Note on `<select>`:** this design uses no `<select>` element anywhere — the one place a dropdown might be expected (status choice) uses the Status-Choice radio group (#5) instead, since it never has more than 3 options; role/status filtering on the Complaints list uses a segmented control, not a `<select>`. So the A11Y-01 border-token fix applies to Text Input and Textarea only; there is no Select component in this system to update.

## 2. Textarea
**Purpose:** complaint description, status-update note.
**Anatomy:** `<label>` + `<textarea>` + character counter (appears when within ~10% of the max length) + optional error.
**States:** default (border `--color-border-interactive`, 4.54:1 — A11Y-01, same rationale as Text Input), focus, disabled-during-submit (**A11Y-14:** `aria-disabled` + `readonly`, never native `disabled` — same rule and rationale as Text Input #1), invalid (exceeds max length or empty on required field), near-limit (counter switches to `--color-error` text inside the last 10%, still shown as text, not colour alone: "1,950 / 2,000").
**Required/optional (A11Y-02):** same "(required)"/"(optional)" label convention and `required`/`aria-required` as Text Input — the status-update note is this product's only "(optional)" textarea.
**Keyboard:** native; resizable vertically only (no horizontal resize, to protect layout).
**ARIA:** same label/describedby/invalid pattern as Text Input; counter region is `aria-live="polite"` only when it crosses into the near-limit state, not on every keystroke (avoids over-announcing).

## 3. Button
**Purpose:** all triggered actions.
**Variants:** **primary** (filled `--color-primary`, white text — one per screen/section, the single most important action), **secondary** (outlined, `--color-primary` text/border on white — e.g. "Cancel", "Back to list"), **caution** (outlined, `--color-error` text/border — used only for "Reset password", which ends sessions; never for anything destructive-to-data, since no such action exists), **text/link-style** (no border/fill, underlined on hover/focus — e.g. "Copy" affordance, in-page navigation).
**States:** default, `:hover` (subtle background shift, desktop only — irrelevant on touch), `:focus-visible` (ring), `:active`, `disabled` (during submit — reduced opacity + `aria-disabled`, never removed from the tab order silently), `loading` (label replaced with a present-tense verb + inline spinner, e.g. "Saving…").
**Keyboard:** native `<button>`; Enter/Space activates.
**ARIA:** `aria-busy="true"` while loading; if icon-only anywhere (none currently planned), would require `aria-label` — avoided by preferring text labels throughout (driver: no icon package, plain language).

## 4. Status Badge
**Purpose:** display a complaint's status, consistently, wherever it appears (list row, detail header, activity entries).
**Anatomy:** small pill (`--radius-pill`) containing the status **word** in `--font-weight-medium`, coloured per design-tokens.md status colours, with a subtle matching-hue border — never colour alone, the text is the primary signal.
**Variants:** New, In Progress, Resolved, Rejected, Closed — five fixed variants, no custom/free-text status is ever renderable through this component.
**States:** static display only — no interactive state (it is not a button).
**ARIA:** plain text content is sufficient; no `role` override needed.

## 5. Status-Choice Control (status-update form)
**Purpose:** let a clerk pick the next status, restricted to legal transitions (BR-002).
**Anatomy:** a radio group (not a `<select>`, so all 1–3 legal options are visible at once with no extra click — appropriate given there are never more than three choices) with a `<fieldset>`/`<legend>` of "Change status to."
**States:** default (visible outline in `--color-border-interactive`, 4.54:1 — A11Y-01), one option checked, disabled (if no legal transition exists, e.g. already Closed — the whole control is replaced by a static note "This complaint is closed and cannot be moved to another status").
**Click/tap area (A11Y-11):** the clickable area for each radio option is the full label text plus surrounding padding — at least 24×24 CSS px — not just the small native radio dot; clicking anywhere on the label row selects that option.
**Keyboard:** native radio-group behaviour (arrow keys move selection, Tab enters/exits the group).
**ARIA:** native `<fieldset>/<legend>/<input type=radio>` semantics are sufficient; no custom ARIA widget needed (explicitly preferred over a custom-styled `<select>` or listbox, which would need far more ARIA to do correctly).

## 6. Alert / Banner
**Purpose:** page- or section-level success, error, warning, or informational message (session expiry, rate-limit, self-lockout advisory, concurrent-edit advisory, service unavailable).
**Anatomy:** a full-width or section-width block with a coloured left border (not full-colour fill, to keep text contrast simple — text stays `--color-text` on `--color-bg-subtle`) and a short, plain-language message; dismissible banners include a "Dismiss" text button (never an "×" icon alone).
**Variants:** info (border `--color-text-muted`), success (border `--color-primary`), warning (border `--color-status-in-progress`), error (border `--color-error`).
**States:** visible, dismissed (where dismissible — session-expiry and error banners are not dismissible, since the user must act).
**ARIA:** `role="status"`/`aria-live="polite"` for info/success/advisory banners; `role="alert"`/`aria-live="assertive"` for errors and the session-expiry notice (per accessibility-strategy.md).

## 7. Inline Field Error
**Purpose:** attach a specific error to a specific field.
**Anatomy:** short text (`--text-xs`, `--color-error`) directly below the field, referenced by the field's `aria-describedby`.
**States:** present/absent only.
**ARIA:** see Text Input/Textarea — the error element itself needs no additional role beyond being the `aria-describedby` target.

## 8. Form Error Summary
**Purpose:** on failed submit, list every problem at the top of the form with links to each field.
**Anatomy:** a heading ("There are N problems with this form") + an unordered list of `<a href="#field-id">` links, one per invalid field, each restating the specific error.
**States:** hidden until a submit attempt fails; reappears (and is re-announced) on every subsequent failed submit.
**Keyboard:** each list item is a real link; activating it moves focus to the field (native anchor behaviour plus a script-set `.focus()` on the target, since anchors alone don't always move focus reliably across browsers).
**ARIA:** `role="alert"`/`aria-live="assertive"`, and focus is moved to the summary heading on first appearance so screen-reader users hear it immediately.

## 9. Modal / Dialog
**Purpose:** the reset-password confirmation and the one-time-password display.
**Anatomy:** `<dialog>` (or an equivalent focus-trapped `div` if `<dialog>`'s browser support is a concern at /architecture's discretion) with a heading, body text, and 1–2 actions.
**States:** open, submitting (action buttons disabled/loading), closed. The OTP-display variant has an additional required state — **unacknowledged-guarded** — active from the moment the dialog opens until the "I have recorded this password" checkbox is checked: the primary "Done" action stays disabled, and (UX-F2, rev 2) **every exit path is guarded, not only Escape/Done**: (1) `Escape` is intercepted and does nothing; (2) a `beforeunload` listener triggers the browser's native "leave site?" confirmation on tab close or typed-URL/bookmark navigation; (3) an in-app route-change guard intercepts nav-link clicks and browser back/forward and shows an in-app confirmation — "You haven't confirmed you've recorded this password. Leave anyway? You will not be able to see it again." (Stay / Leave without recording). **(A11Y-15)** This confirmation dialog opens on top of the OTP dialog; only one dialog is ever in the active focus trap at a time — the OTP dialog's trap is suspended while the confirmation is open, and its trap resumes when the confirmation closes. Unlike the OTP dialog, this confirmation does not suppress Escape: `Escape` here is equivalent to activating its default-focused "Stay" action. On "Stay," focus returns to the "I have recorded this password" checkbox inside the OTP dialog. All three guards are removed the instant the checkbox is checked. See user-flows.md Flow 6 step 3a.
**Click/tap area (A11Y-11):** the "I have recorded this password" checkbox's clickable area includes its label text and surrounding padding, ≥24×24 CSS px, matching the Status-Choice Control convention.
**Keyboard:** focus moves to the dialog's heading on open; Tab is trapped within the dialog; Escape closes it (except the OTP-display variant's unacknowledged-guarded state above, where dismissing without acknowledging is the one mistake this product actively prevents).
**ARIA:** `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to the heading; focus returns to the triggering button on close (or, for the OTP-display variant, to the list/screen that triggered it once genuinely dismissed).

## 10. List Row (complaints, accounts)
**Purpose:** one row per complaint or account.
**Anatomy:** a plain bordered row (bottom divider `--color-border` — decorative use, fine at 1.40:1; the row is not itself the interactive control's boundary, see A11Y-01 — no card/shadow) containing the key fields (complaint number, status badge, description snippet/date — PROD-F3, reworded from "subject/date": there is no separate subject field, only a truncated description — or username, role, created date) and a primary click target for the whole row (complaints) or explicit per-row action buttons (accounts: "Reset password").
**List semantics (A11Y-08):** the Complaints list and the Accounts list are each wrapped in a `<ul>` (or a container with `role="list"` if a reset CSS strips native list semantics), with each row as an `<li>` — so screen-reader users get an announced item count and list navigation, rather than a flat sequence of unrelated buttons/links.
**States:** default, `:hover`/`:focus-visible` (subtle background shift), selected/expanded (complaints list only — the row whose detail panel is open is visually marked, e.g. a left border in `--color-primary`).
**Keyboard:** the whole row is a single `<button>`/link where it opens the detail panel (not a `<div onClick>`), so it is natively focusable and activatable.
**ARIA:** `aria-expanded`/`aria-controls` on the row when it toggles the detail panel, pointing to the panel's id.

## 11. Loading Indicator
**Purpose:** communicate an in-flight request (NFR-011, uniform pattern).
**Anatomy:** a small inline spinner (pure CSS, no image/GIF/animation library) paired with present-tense text ("Checking…", "Saving…") — text is never omitted, since the spinner alone conveys nothing to a screen reader and little to a low-vision user.
**States:** visible only while in flight; replaced entirely by the result (success block or error banner) on completion — never left showing indefinitely (bounded by the 10 s abort).
**ARIA (A11Y-03, rev 2):** the containing control carries `aria-busy="true"` as before; additionally, **the label's containing element carries `role="status"` and `aria-live="polite"`**, so "Checking…"/"Saving…" and the text that replaces it on completion are both announced automatically to screen-reader users without focus moving — `aria-busy` alone communicated a state but not the text change itself. The spinner graphic remains `aria-hidden="true"` (the text is the accessible content).
**Reused elsewhere (A11Y-12, A11Y-13):** this same `role="status"`/`aria-live="polite"` container convention is reused for two non-in-flight cases that are not literally "loading" but still need announced text transitions: (1) the Public Status Lookup's "Check status" button label/state-message, which cycles through "Preparing…" → live → "Retry" → "Unavailable — reload the page" before any request is even sent (screen-inventory.md Screen 1; user-flows.md Flow 5 step 1); and (2) the Complaints list's search-result and pagination-status announcements — settled result count, no-match message, "Loading more," "All complaints shown" (screen-inventory.md Screen 4; interaction-patterns.md "Find, search, and pagination").

## 12. Top Navigation Bar
**Purpose:** role-based wayfinding and the always-visible logout control (clerk app only — the public page has none).
**Anatomy:** app name (plain text), primary links ("Complaints"; "Accounts" only if `is_admin_clerk`), user menu (username + "Change password" + "Log out").
**States:** default; current-page link is visually and programmatically marked (`aria-current="page"`); `must_change_password=true` state hides/disables every link except "Log out."
**Keyboard:** all links/buttons in natural tab order; the user menu, if implemented as a disclosure rather than always-expanded links, uses `aria-expanded` and closes on Escape/outside click.
**ARIA:** `<nav aria-label="Main">`; `aria-current="page"` on the active link.

## 13. Copy-to-Clipboard Control
**Purpose:** copy a complaint number or one-time password without manual text selection.
**Anatomy:** a text button labelled "Copy" beside the monospaced value; on success the label temporarily changes to "Copied" (reverting after ~2s) — text change, not an icon swap.
**States:** default, copied (transient), failed (rare — clipboard API unavailable/denied: falls back to "Select the text above to copy it manually" rather than failing silently).
**Keyboard:** native button, Enter/Space activates.
**ARIA:** the transient "Copied" state is announced via `aria-live="polite"` on the label's containing element.

## 14. Countdown / Retry Timer
**Purpose:** show a rate-limit or backoff wait time (429 responses).
**Anatomy:** plain text ("Try again in 42s") next to the disabled submit button, decrementing once per second.
**States:** counting down, expired (control re-enables automatically, text disappears).
**Disabled-state rule (A11Y-04):** the associated submit button uses `aria-disabled="true"` during the countdown, **not the native `disabled` attribute** — same rule as Button (#3): it stays in the tab order and is announced as disabled rather than silently skipped, and re-enabling at zero is a single attribute flip rather than re-inserting a removed element.
**ARIA:** the countdown text updates visually every second but is **not** wrapped in `aria-live` (which would announce every second and be unusable) — instead, the initial wait message is announced once (`aria-live="polite"` on first render only), and the re-enabled state is announced once more when it happens.
