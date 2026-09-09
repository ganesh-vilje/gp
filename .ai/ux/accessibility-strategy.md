# Accessibility Strategy — WCAG 2.2 AA

Designed in from the flows and screens above, not retrofitted. Applies to both the public page and the clerk app.

## Keyboard
- **Skip link (A11Y-09):** the clerk app's first focusable element on every page is a visually-hidden-until-focused "Skip to main content" link, jumping past the top nav bar to `<main>` — see information-architecture.md navigation model for the rationale (full page loads with no client-side route persistence mean this repeats on every navigation).
- Every interactive element (fields, buttons, the status-choice control, the copy button, the OTP acknowledgment checkbox, filter controls, nav links) is reachable and operable with Tab/Shift+Tab/Enter/Space alone — no mouse-only affordance anywhere, and no custom widget that traps focus.
- **Focus order** follows visual/reading order (top-to-bottom, left-to-right in LTR English): header → primary content → primary action → secondary links. In the Complaints screen, expanding a detail panel moves focus into the panel's heading; closing it returns focus to the row that opened it (no orphaned or lost focus).
- **Focus ring:** always visible, never suppressed with `outline: none` without a replacement — 3px solid `--color-focus` (`#146C43`) with 2px offset (≥3:1 contrast against both white and the darkest adjacent surface — see design-tokens.md for the computed ratio).
- Modals/dialogs (reset-password confirmation, OTP display) trap focus **within the dialog only** while open, return focus to the triggering control on close, and close on Escape.

## Labels and semantic structure
- Every form control has a visible, programmatically-associated `<label>` (not placeholder-as-label — placeholders disappear on input and fail for users who need to re-read the label while typing).
- Headings are structural (`h1` per page, `h2` for major sections such as "Activity", `h3` for sub-groups), not chosen for size — so a screen-reader user can navigate by heading.
- Status is always conveyed as **text**, never colour alone (each status badge carries its label; each error is a text string, not a red border by itself).
- Landmarks: one `<main>` per page, `<nav>` for the top bar, `<form>` for each distinct form.

## Contrast (WCAG 2.2 AA — ratios computed in design-tokens.md)
- Body text `#1A1A1A` on white: ~19.5:1 (far exceeds the 4.5:1 minimum).
- Primary action colour `#146C43` on white (buttons/links): 6.46:1 — passes 4.5:1 for text and 3:1 for UI components/large text.
- All five status-badge text colours: 5.3:1–6.5:1 on white (full table in design-tokens.md) — every status is legible without relying on the colour swatch alone (also carries a text label, per above).
- Placeholder/help text `#5B6570` on white: 5.93:1 — deliberately chosen above the 4.5:1 floor even for secondary text, since some readers are not fluent in the UI language (driver U1/U9).

## Touch targets
- Public page (phone-primary, driver U1): all interactive elements ≥44×44 CSS px, per the spec's "ideally 44" guidance — this is the page most likely to be used one-handed on a cheap touchscreen.
- Clerk app (desktop-primary, driver U2): ≥24×24 CSS px minimum with ≥8px spacing between adjacent targets (row action buttons, filter chips), meeting the WCAG 2.2 SC 2.5.8 floor; primary buttons are still sized to ≥40px height for comfort.

## Form error announcement
- Each invalid field: `aria-invalid="true"` and `aria-describedby` pointing to its inline error message.
- The top-of-form error summary is a `role="alert"`/`aria-live="assertive"` region so screen-reader users are told immediately that submission failed and how many problems exist, without needing to discover it visually.
- Global banners (session expired, rate-limited, service unavailable) use `aria-live="polite"` (or "assertive" for the session-expiry redirect, since it changes what the user can do next) so they are announced without needing focus to move to them.

## Zoom and reflow
- Layout uses relative units (rem/%, no fixed pixel-width containers) so the page reflows correctly with no horizontal scrolling or clipped content, per WCAG 2.2 SC 1.4.10 — tested at 320 px CSS width. (A11Y-10, rev 2: corrected from an earlier "200% zoom" framing — a 1280 px baseline viewport at 400% zoom, not 200%, is what maps to a 320 px effective width; SC 1.4.10 itself is framed in terms of viewport width, not a zoom percentage, so 320 px CSS width is stated directly as the test point rather than via a zoom-percentage equivalence.)
- No content is conveyed only through a fixed-size image or icon; the product uses almost no icons at all (see visual-direction.md).

## Document language (A11Y-07)
- **Build requirement:** every HTML document shipped by this product declares `<html lang="en">` — this is an explicit build requirement (for whichever templating/static-export mechanism architecture selects), not left implicit, so assistive technology uses the correct pronunciation/voice rules from first paint. Ties to OQ-1 (UI language default of English): if OQ-1's answer changes to a different primary language, this attribute changes with it as a single-point edit.
- **Out of scope:** per-fragment `lang` attributes on individual free-text fields (e.g. a citizen's typed name or a clerk's note, which may contain non-English characters/words per the Noto Sans fallback in design-tokens.md) are explicitly out of scope for MVP — detecting and marking the language of arbitrary user-entered text is a non-trivial feature in its own right, and its absence does not block the page-level `lang` declaration from being correct for all the product's own authored UI copy.

## Motion
- No animation beyond an optional ≤150 ms opacity fade for state transitions (e.g., a banner appearing), and that is skipped entirely when `prefers-reduced-motion: reduce` is set. No auto-playing content, no parallax, no attention-seeking motion anywhere — consistent with the "minimal decoration" visual direction and the performance budget (no animation library is used or needed).

## Language and comprehension (beyond WCAG's letter, in its spirit)
- Every user-facing string in this product uses short sentences, common words, and avoids technical terms ("session", "CSRF", "cookie" appear only in the one unavoidable "enable cookies" message, phrased around the user action rather than the mechanism).
- Error messages state **what happened and what to do next** in the same sentence, never a bare error code.
