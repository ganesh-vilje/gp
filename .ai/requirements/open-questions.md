# Open Questions for the Human

## Changelog
- rev 1 (2026-09-09) — initial population by requirements-analyst; no prior
  findings to address (greenfield).
- rev 2 (2026-09-09) — rework pass 1/3:
  - Q-F1: added Q-012 (nice-to-know) — concurrent-edit UX preference. The
    underlying behavior (no silent audit loss) was resolved directly as
    BR-011/AC-014 since it did not require a human product decision; only
    the optional UX nicety (warn-on-conflict) is left as a question.
  - P-F4: added Q-013 (important) — the public-lookup rate-limit threshold
    is now a tracked, numbered open question instead of a dangling
    "pending Open Questions" reference with no corresponding item.
  - Q-001, Q-002, Q-003 (blocking) intentionally left unanswered — the
    analyst does not resolve blocking human questions itself.
- rev 3 (2026-09-09):
  - H1: Q-003 answered by the human (recorded verbatim below under
    Resolved) — the pilot needs a second role, "admin clerk." Moved to
    Resolved.
  - Q2-F7: added a line to Q-002 asking whether immediate New→Rejected
    transitions should be allowed for duplicate/invalid complaints, given
    BR-008's guidance to reject duplicates rather than delete them.
  - H1 (follow-on): added Q-015 (nice-to-know) — how an admin clerk
    recovers if they are themselves locked out of their password, since H1
    did not specify this.
- rev 4 (2026-09-09) — rework pass 3/3 (final): no question-list changes
  required by this pass's findings (Q3-F1–F4, P3-F1–F3 were all
  answerable without a new human question). Q-015 is now also referenced
  from BR-013's new mitigation line (P3-F3, see business-rules.md). Per
  explicit instruction, Q-001 and Q-002 (blocking) were NOT touched in this
  pass.
- rev 5 (2026-09-09) — post-GATE_1, tech-stack phase: added Q-016
  (important), raised by the security-reviewer, about whether the public
  status page's free-text "latest note" (FR-009) can leak PII a clerk
  types into it; affects the already-resolved Q-001 masking decision.
- rev 6 (2026-09-09) — post-GATE_2 amendment (technology stack approved):
  Q-013 and Q-016 moved to Resolved with the human's verbatim GATE_2
  answers. Q-013 resolved by GATE_2 Q4 ("keep 20/min."). Q-016 resolved by
  GATE_2 Q7 ("option (b), fixed status messages."). No new questions added
  by this pass.

Only the requirements-analyst adds questions here. Only the orchestrator marks
them resolved (with the human's answer verbatim).

## Blocking (cannot design without)
(none — Q-001 and Q-002 resolved at GATE_1, see Resolved below)

## Important
- Q-004 | What language(s) must the public lookup page and clerk UI
  support — English only, or a local language (e.g., Kannada, Hindi,
  Marathi, etc., depending on the panchayat's state)? | Affects content/
  labels structure and whether the architect needs to plan for
  localization now or can add it later. | Analyst's default: English only
  for the MVP (Assumption A5).
- Q-005 | Should the complaint number be purely system-generated, or does
  the clerk need to cross-reference it with an existing paper register
  number they already use? | Affects whether the number needs a specific
  format/prefix tied to existing paperwork. | Analyst's default: purely
  system-generated, format decided by the architect (Assumption A4).
- Q-006 | Is there a required retention or archival period for complaint
  records (e.g., must data be purge-able after N years, or kept
  indefinitely for audit purposes)? | Affects data-retention design and any
  future compliance work. | Analyst's default: retain at least 12 months,
  no automatic deletion in the MVP (Assumption A9, NFR-010).
- Q-007 | How long after logging a complaint should a clerk be allowed to
  edit the citizen's name/phone/description to fix a data-entry mistake
  (e.g., same day, 7 days, unlimited)? | Affects FR-012/AC-008 and whether
  an edit-window rule needs enforcing in the design. | Analyst's default:
  7 days (Assumption A8).
- Q-008 | Does any complaint need a target/expected resolution date or a
  category (e.g., water, roads, sanitation) for internal tracking, or is
  free-text description sufficient for the MVP? | Affects whether the data
  model needs a category/SLA field now. | Analyst's default: free-text
  description only, no category or SLA field in the MVP (see Future
  scope).
## Nice to know
- Q-012 | If two clerks happen to update the same complaint at nearly the
  same time, should the second clerk to save see a warning that someone
  else just changed it (optimistic-concurrency style UI), or is silent
  last-write-wins (with both changes kept in history, per BR-011)
  acceptable for a 1–5 clerk pilot? | Purely a UX nicety — the underlying
  "no silent audit loss" behavior is already fixed by BR-011/AC-014
  regardless of the answer. | Analyst's proposed default: no warning UI in
  the MVP; rely on the preserved history if a discrepancy is ever noticed.
- Q-009 | Any preference for what the complaint number should look like
  (e.g., purely numeric vs. a prefixed code like "PC-2026-0001") to make it
  easy for a citizen to write down or read over the phone? | Cosmetic;
  architect can propose a default if not answered.
- Q-010 | Will clerks only use a shared office computer, or will some also
  need to log in from personal phones/tablets? | Helps size any
  session/device assumptions but isn't a hard blocker; a responsive web UI
  covers both cases.
- Q-011 | Is there any near-term plan to extend this tool to other
  panchayats beyond the pilot? | Purely informational — MVP explicitly
  targets a single panchayat regardless of the answer (see Scope
  challenges), but knowing the answer helps the architect judge how much
  future-proofing (if any) is worth a passing mention in the design notes.

- Q-015 | If an admin clerk forgets their own password or is otherwise
  locked out, is there a break-glass/secondary recovery mechanism, or does
  recovery require re-running the operator's bootstrap step (FR-015)? |
  H1 established that the admin clerk resets other clerks' passwords
  in-app, but did not say how the admin clerk recovers their own. | Purely
  informational for now; not a hard blocker since the pilot is expected to
  have exactly one admin clerk (Assumption A12) and a bootstrap re-run is a
  workable fallback. (Added rev 3, H1 follow-on.)

## Resolved
<!-- Q-00n | answer | date | recorded from GATE_n approval -->
- Q-001 | Human answer at GATE_1: "accept defaults". Resolved to the
  analyst's proposed default: the public complaint-status page shows no
  citizen name or phone number at all — only complaint number, status, date
  logged, and latest note (BR-005, FR-009 stand as written; the "pending
  Q-001" markers can be dropped). | 2026-09-09 | recorded from GATE_1
  approval.
- Q-002 | Human answer at GATE_1: "accept defaults". Resolved to the
  analyst's proposed default: statuses are New → In Progress →
  Resolved/Rejected → (optional) Closed, with no skipping of steps (BR-002
  stands as written). Sub-question (Q2-F7): since the default was accepted
  without exception, an immediate New→Rejected transition is NOT allowed;
  a duplicate/invalid complaint must pass through In Progress before being
  Rejected. AC-004 should be expanded to cover all prohibited
  skip-transitions (QA rev 4 advisory F4). | 2026-09-09 | recorded from
  GATE_1 approval.
- Q-003 | Resolved by human decision H1 (2026-09-09): Yes, a second role is
  needed. There are two permission levels: regular clerk and admin clerk.
  The admin clerk is one of the clerks, with two added abilities — creating
  a new clerk account and resetting an existing clerk's password — that a
  regular clerk does not have. All other permissions remain shared across
  all clerks (per Assumption A1, updated rev 3). The very first admin clerk
  account is bootstrapped out-of-band by the deploying operator (Assumption
  A11); ongoing account creation/password resets are in-app via the admin
  clerk (FR-017, FR-018). | 2026-09-09 | recorded from human decision H1
  (requirements rev 3 rework).
- Q-013 | Human answer at GATE_2 Q4 (verbatim): "keep 20/min." Resolved: the
  public-lookup rate limit is confirmed as 20 requests per IP address per
  minute, simple throttle/reject beyond that (no CAPTCHA in MVP) — NFR-005
  and AC-011 no longer carry an "analyst default" marker. | 2026-09-09 |
  recorded from GATE_2 approval.
- Q-016 | Human answer at GATE_2 Q7 (verbatim): "option (b), fixed status
  messages." Resolved: the public status page shows a fixed, enumerated set
  of public status messages (one per status, wording defined in /ux); the
  clerk's free-text note is never shown on the public view (FR-009, BR-005).
  | 2026-09-09 | recorded from GATE_2 approval.
