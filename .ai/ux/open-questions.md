# UX Open Questions

Every item below has a default applied so design work was not blocked. None are re-litigations of the blocking requirements questions (Q-001/Q-002/Q-003), which are already resolved.

## OQ-1 — UI language
**Human answer (GATE_4, 2026-09-09):** English now; Telugu to be added later. All user-facing strings MUST live in one strings module (build requirement, carried to /architecture and /plan).
**Default applied:** English, matching requirements Assumption A5 (open, Q-004). All copy in this deliverable is English. **Design note carried into implementation:** every user-facing string should live in one place (a strings/constants module), not inline in components, so a future localization pass doesn't require re-touching every screen — cheap to do now, expensive to retrofit. **Needs human:** confirm Q-004; if the answer is a language other than English, or bilingual, this whole deliverable's copy needs re-authoring (not just translation — sentence length/plain-language choices differ by language).

## OQ-2 — Brand, logo, panchayat name
**Human answer (GATE_4, 2026-09-09):** use the defaults for the test project (plain wordmark, no logo, generic office copy). Also settles OQ-8.
**Default applied:** no logo; a plain-text wordmark "Panchayat Complaint Tracker" in the header. No specific panchayat name/office identity is used anywhere (error copy says "the panchayat office" generically). **Needs human:** the actual panchayat's name (for the header and for citizen-facing copy), a logo/emblem if one exists, and office contact details (phone/hours) to print in the "not found"/"contact the office" messages — currently a placeholder.

## OQ-3 — Existing style guide
**Confirmed:** none was supplied in requirements or tech-stack. This deliverable originates a new, minimal design system (design-tokens.md, component-spec.md) built to fit the ≤120 KB / no-framework performance budget. No conflict to resolve.

## OQ-4 — Terminology: "complaint" vs. "grievance"
**Resolved by usage:** requirements (FRs, BRs, user stories) use "complaint" exclusively; "grievance" does not appear. Adopted as the sole UI term throughout every screen and message.

## OQ-5 — Data-entry correction window (FR-012)
**Human answer (GATE_4, 2026-09-09):** 7 days confirmed (resolves requirements Q-007).
**Default applied:** 7 days, matching requirements Assumption A8 (open, Q-007). The "Edit details" action's enabled/disabled boundary uses this number. **Needs human:** if Q-007 resolves to a different number, only the threshold constant and its caption change — the interaction pattern (disable + tooltip, not a hidden failure) stays the same.

## OQ-6 — Concurrent-edit UX preference (Q-012 in requirements, "nice-to-know")
**Resolved by this document:** a non-blocking advisory banner rather than a hard conflict lock (user-flows.md Flow 3; interaction-patterns.md). Consistent with BR-011's explicit allowance of last-write-wins as long as both edits survive in history.

## OQ-7 — Admin self-lockout (Q-015 in requirements, "nice-to-know")
**Resolved by this document:** a persistent advisory banner on the Accounts screen when only one admin account exists (user-flows.md Flow 6, step 2). **Needs human/ops:** confirm the console break-glass paths (`unlock-account`, `bootstrap-admin`, per tech-stack.md) are documented for whoever holds platform shell access, since the UI cannot help an admin clerk who is completely locked out with no colleague to reset them.

## OQ-8 — Panchayat office contact details in citizen-facing copy
**Human answer (GATE_4, 2026-09-09):** defaults accepted for the test project.
**Default applied:** generic "contact the panchayat office" phrasing wherever a real phone number/hours would be more helpful (not-found message, noscript message, cookies-disabled message). **Needs human:** the real contact details, once known, to make these messages actionable rather than generic.

## OQ-10 — Name/phone search on the clerk complaints list
**Human answer (GATE_4, 2026-09-09):** ACCEPTED — committed MVP scope. requirements-analyst to add a matching FR (extends FR-005) at the next requirements revision.
FR-005 requires only that a clerk can "find an existing complaint (by number or from a list)" — it does not mention searching by name or phone. The Complaints screen (rev 2) added a **"Search by name or phone"** text input above the list as a UX addition, not a functional requirement. **Default applied: include it.** Rationale: the list has no delete and no MVP date filter (NFR-010), so it only grows over the life of the office's use of the tool, and a clerk fielding a phone call often does not have the complaint number in hand; the search uses only data clerks already see on this authenticated route (FR-016, citizen name/phone), and exposes nothing new and nothing to the public lookup page. **Needs human:** confirm at Gate 4 that this UX addition is acceptable scope beyond FR-005's literal text. **If declined:** remove the "Search by name or phone" box from screen-inventory.md Screen 4, interaction-patterns.md, and user-flows.md Flow 4, leaving "Find by complaint number" plus the 25-row pagination as the sole find mechanism.

## OQ-9 — Voluntary (non-forced) self-service password change
**Human answer (GATE_4, 2026-09-09):** ACCEPTED — committed MVP scope. requirements-analyst to add a matching FR at the next requirements revision; remove the "pending" flags in information-architecture.md and screen-inventory.md Screen 3 during /architecture.
Not an explicit functional requirement, but tech-stack.md's session-revocation design already anticipates a "self password change" event (session rotation on self-change is listed alongside login and admin-reset). **Default applied:** expose a "Change password" action in the user menu for any authenticated clerk at any time, not only when forced — this lets a clerk react to a suspected compromise without waiting for the admin clerk, at negligible added cost since the backend mechanism is already assumed to exist. **PROD-F2 (product-reviewer, rev 2): marked explicitly as pending, not committed scope.** There is no backing FR for the voluntary path — only the forced path (redirect after first login/admin reset) is committed MVP scope. The voluntary menu entry, the "current password" field, and its associated states are drawn in information-architecture.md and screen-inventory.md (Screen 3) but flagged there as pending. **Needs human/product owner:** confirm this voluntary path is in scope for MVP build at Gate 4, or should be deferred (in which case only the forced path from Flow 1 remains, and the menu item, current-password field, and voluntary states/tests are removed before build).
