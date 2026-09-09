# Design Tokens

All tokens are plain CSS custom properties (`:root { --token-name: value; }`), no preprocessor and no CSS framework, matching the ≤120 KB gzipped / hand-written-CSS budget in tech-stack.md. Total stylesheet target: 4–8 KB gzipped, one file.

## Typography
System font stack (no web-font download): `font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans", Arial, sans-serif;` — Noto Sans included in the fallback chain for broader glyph coverage (a citizen's or clerk's typed name may use characters outside basic Latin, even though the MVP UI language is English — A5/OQ-1).
Monospace (complaint numbers, one-time passwords only): `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;`

| Token | Size / line-height | Use |
|---|---|---|
| `--text-xs` | 14px / 1.5 (0.875rem) | help text, captions, field hints |
| `--text-base` | 16px / 1.5 (1rem) | body text, form labels/inputs, buttons |
| `--text-lg` | 18px / 1.5 (1.125rem) | lead paragraph, `h3` |
| `--text-xl` | 22px / 1.3 (1.375rem) | `h2` (section headings, e.g. "Activity") |
| `--text-2xl` | 28px / 1.3 (1.75rem) | `h1` (page title) |
| `--text-mono-lg` | 32px / 1.2 (2rem), monospace, letter-spacing 0.05em | complaint number / one-time password display |
| `--font-weight-normal` | 400 | body text |
| `--font-weight-medium` | 600 | button/label text, status badges |

## Color (hex, with computed WCAG contrast against the stated background)

| Token | Hex | On white (#FFFFFF) | Use |
|---|---|---|---|
| `--color-text` | `#1A1A1A` | 19.5:1 | body text |
| `--color-text-muted` | `#5B6570` | 5.93:1 | help/secondary text, captions |
| `--color-primary` | `#146C43` | 6.46:1 | primary buttons, links, focus ring, "Resolved" status |
| `--color-bg` | `#FFFFFF` | — | page background |
| `--color-bg-subtle` | `#F4F6F5` | n/a (non-text surface) | input backgrounds, subtle section separation |
| `--color-border` | `#D6DBD9` | 1.40:1 vs white — **decorative use only** (row/list dividers, section separators) | dividers only — never the sole boundary of an interactive control |
| `--color-border-interactive` | `#767676` | 4.54:1 vs white (standard relative-luminance formula; well clears the 3:1 WCAG 1.4.11 floor for UI-component boundaries, with headroom to spare) | **the only border token used for the default (non-focus, non-error) state of every interactive component boundary** — text inputs, textareas, the status-choice radios' visible outline, buttons' outlined variants (A11Y-01, rev 2). Replaces `--color-border`/`--color-bg-subtle`, which at 1.40:1/1.09:1 were not distinguishable enough from white to satisfy 1.4.11 as the sole default-state boundary. |
| `--color-status-new` | `#2B6CB0` | 5.48:1 | "New" status text/badge |
| `--color-status-in-progress` | `#92610A` | 5.33:1 | "In Progress" status text/badge |
| `--color-status-resolved` | `#146C43` | 6.46:1 (same as primary) | "Resolved" status text/badge |
| `--color-status-rejected` | `#B3261E` | 6.54:1 | "Rejected" status text/badge |
| `--color-status-closed` | `#5B6570` | 5.93:1 | "Closed" status text/badge |
| `--color-error` | `#B3261E` | 6.54:1 | error text, invalid-field border |
| `--color-focus` | `#146C43` | 6.46:1 (≥3:1 required for a non-text UI indicator — passes with margin) | focus ring on every interactive element |

All status colours are paired with a mandatory text label in every occurrence (see accessibility-strategy.md — never colour alone). Contrast ratios computed via the standard WCAG relative-luminance formula against the stated background; recompute if any hex value changes.

## Spacing (4px base unit)
`--space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-5: 24px; --space-6: 32px; --space-7: 48px; --space-8: 64px;`
Default form-field vertical gap: `--space-4` (16px). Default section gap: `--space-6` (32px).

## Radii
`--radius-sm: 4px;` (inputs, buttons) `--radius-md: 8px;` (panels/dialogs) `--radius-pill: 999px;` (status badges only — the one "chip"-like shape in the system, used because a pill reads unambiguously as a small status label, not a clickable card).
No radius is applied to dividers/rows; no drop shadows are defined anywhere in this token set (see visual-direction.md — shadows are deliberately excluded).

## Breakpoints (mobile-first)
`--bp-sm: 600px;` (form/dialog centering begins) `--bp-md: 900px;` (Complaints screen: list beside detail) `--bp-lg: 1200px;` (max content width, `max-width: 1100px` centered, applied above this point only).
Base (0–599px) is designed first and is the only layout the public page ever needs, per driver U1 (phone-primary citizens).

## Focus ring
`outline: 3px solid var(--color-focus); outline-offset: 2px;` — applied via `:focus-visible` (not `:focus`, to avoid a visible ring on mouse clicks while preserving it for keyboard use), never removed without this replacement anywhere in the codebase.

## Touch targets
Public page: minimum 44×44 CSS px hit area on every interactive element (`min-height`/`min-width` plus padding, even where the visible glyph is smaller). Clerk app: minimum 24×24 CSS px with ≥8px (`--space-2`) gap between adjacent targets; primary action buttons still sized to ≥40px height.

## Motion
`--motion-fade: 150ms;` used only for banner/panel appearance, and skipped entirely under `@media (prefers-reduced-motion: reduce)`. No other duration/easing token exists — there is no other animation in the system.

## Implementability note
Every token above is a literal CSS custom property; none requires a build step, a CSS-in-JS runtime, or a component library. This is a deliberate constraint carried over from tech-stack.md's "no CSS framework, no component library" decision and the ≤120 KB budget — the entire token set plus component styles should comfortably fit inside the 4–8 KB CSS estimate already budgeted there.
