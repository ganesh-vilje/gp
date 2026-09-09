# Information Architecture

## Sitemap — Citizen (unauthenticated, public)
```
/  (Public Status Lookup — the entire public site)
```
One page, one purpose. No navigation menu, no footer links to clerk areas (BR-010 — no discoverable path to any bulk or clerk surface from the public page).

## Sitemap — Clerk (regular)
```
/login
/change-password        (forced on must_change_password=true — committed scope; the voluntary "Change password" menu entry point is PENDING HUMAN CONFIRMATION, OQ-9 — not committed scope until answered at Gate 4, see open-questions.md and screen-inventory.md Screen 3)
/complaints              (default landing page after login)
  ├─ list (all complaints, filter by status, quick "find by number", search by name/phone — UX-F1)
  └─ detail (inline panel/drawer, client-state — no dynamic route; see below)
       ├─ status history + edit history ("Activity")
       ├─ update-status action
       └─ edit-details action (only inside the edit window, default 7 days — A8)
```
No `/accounts` link is rendered in navigation for a regular clerk (FR-019).

## Sitemap — Admin clerk (regular clerk's IA plus)
```
/login
/change-password
/complaints               (identical to regular clerk — same permissions on complaint data, BR-013)
/accounts
  ├─ list of clerk accounts (username, role, created date)
  ├─ create account action → one-time password shown once
  └─ reset password action (per account) → one-time password shown once
```

## Why no `/complaints/[id]` route
The complaint detail is rendered as client-side state inside `/complaints`, not a separate URL — an architecture decision (static export has no dynamic segment, and a complaint number must never appear in a URL, browser history, or referrer per the security floor in tech-stack.md). UX consequence: selecting a complaint expands a detail panel in place; there is no bookmarkable/shareable deep link to a single complaint, and browser back/forward does not step between complaints. A host-level rewrite sends any stray `/complaints/*` request back to the list shell, so no dead link is possible.

## Navigation model
- **Public page:** no nav — a single form is the entire experience.
- **Clerk app:** one persistent top bar containing: app name (plain text, no logo — see open-questions.md), primary links (**Complaints**; **Accounts** only if `is_admin_clerk`), and a user menu (username, **Change password** — pending human confirmation, OQ-9, see screen-inventory.md Screen 3, **Log out**) that is always visible and reachable on every authenticated screen (tech-stack requires a visible logout control everywhere). No sidebar — with 1–2 nav destinations a sidebar would add chrome with no benefit (driver U7).
- **Skip link (A11Y-09):** a visually-hidden-until-focused "Skip to main content" link is the first focusable element on every clerk-app page, jumping past the top bar straight to the `<main>` region — with only 2–3 nav items the bar is short, but a keyboard/screen-reader user still repeats it on every route change (there is no client-side router keeping focus state across "pages" here, since navigation is a full static-export page load), so the cost of including it is one link versus real repeated-tab-stop friction for that user.
- **Mobile clerk access:** not the primary use case (A6: office desktop/laptop), but the nav bar collapses to a simple stacked/hamburger-free list (links + user menu wrap) down to tablet width as a defensive minimum — see design-tokens.md breakpoints.

## Access control reflected in IA (UX layer only — the API is the enforced boundary)
- Any `/complaints` or `/accounts` request without a valid session redirects to `/login` (no confusing partial render).
- `/accounts` requested directly by a non-admin clerk renders an in-app **"Not authorized"** state (see screen-inventory.md), not a silent redirect — FR-019 requires the denial to be clear, and hiding the nav link alone is not a security control (client-side guards are UX only; the API enforces the 403).
- `must_change_password=true` intercepts every authenticated route except the change-password screen and logout, redirecting there until resolved.
