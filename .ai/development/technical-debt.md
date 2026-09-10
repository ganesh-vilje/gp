# Technical Debt — panchayat-complaint-tracker

rev 2 (2026-09-10), rework: added a TD-002 row for the tech-stack.md/technology-comparison.md
start-command wording cleanup [A-F11], added a TD-003 row for the real OQ-10 [A-F3], added the real
OQ-9 as a restated closed decision under TD-005 [A-F3]. Every item names an id, why it is deferred (not a `/build` task), and the trigger
to revisit. Items already carried as **accepted risk** at the architecture gate (threat-model.md rev 4:
18 accepted, 10 n-a; e.g. threat #24 hijacked-session PII-read rate, threat #28 single-vendor backups,
threat #39 no HA) are **not** repeated here — those are recorded decisions, not debt, and are
unaffected by anything in `/plan`. This file is only what `/plan` itself is choosing not to build now.

## TD-001 — Clock-boundary tests: resolved, not deferred (test-architect's flagged gap a)

**Status: not debt.** implementation-plan.md adopts an injectable clock (`core/clock.py`, task T-005,
adopted by T-027/T-029/T-040), which moves TC-SEC-011b/014/015 and the two limiter/session sweep
boundary tests out of test-strategy.md's nightly-only classification and into always-run. Recorded
here only so a future reviewer sees the decision was made deliberately, with an owner (whoever builds
T-005) and a check (task T-046 re-verifies the always-run wall-clock budget after the move). **No
revisit trigger** — this is done once T-027/T-029/T-040 land; if a future engineer proposes reverting
to `freezegun` or real elapsed-time waits, that is a new ADR, not a silent regression.

## TD-002 — Documentation-only advisories not actioned by `/build`

These are carried in `.ai/architecture/review-advisories.md` with an owner other than the
implementation team. They do not block `/build` and are listed here purely so nothing "disappears":

| ID | What it asks | Owner | Why not a `/build` task | Trigger to revisit |
|---|---|---|---|---|
| SEC-F3 (rev4) | Reword infrastructure.md §12.4 to name the three real append-only tables conditionally, not as REVOKE-guaranteed fact | solution-architect | Wording fix in an architecture document `/build` does not own or edit | Next `/architecture` revision, or before the operator runbook (§12.4) is executed for real |
| ARCH-F1 (rev4) | error-catalog.md:72-74 should read "every call, pre-handler" for the `detail` counter on `POST /api/complaints`, matching api-contract.md:276 | data-api-architect | Doc drift between two already-approved documents; api-contract.md's fuller statement is what T-026 implements, so the *behaviour* is already correct — only error-catalog.md's shorter phrase is stale | Next `/architecture` or `/plan` revision |
| SEC-F4/F5/F6/F7/F8/F9 (low, rev4) | Wording/cross-reference touch-ups across security-architecture.md, error-catalog.md, schema.md | solution-architect / data-api-architect | All low-severity wording, no behavioural gap; the schema.md rows this file cites (`search` scope, PERF-F5 cost note) were checked during `/plan` and are **already present** in schema.md rev 4 — moot for two of the six | Next `/architecture` revision |
| screen-inventory.md:62 (wrong-current-password wording) | Screen inventory still describes a wrong current password as session-ending | ux-designer | `/build` implements the **correct** behaviour regardless (422 `invalid_current_password`, field-level, per api-contract.md/security-architecture.md — see task T-029); only the UX document's prose is stale, and T-029/T-036 do not follow it | Next `/ux` revision |
| acceptance-criteria.md AC-006 "latest status note" wording | First bullet still says "latest status note" though the public DTO carries `public_update`, an enumerated value, not the clerk's note | requirements-analyst | `/build` implements what api-contract.md/BR-005 actually specify (T-010); the AC's own later bullets already say this correctly, so no behavioural ambiguity exists for the builder | Next `/requirements` revision |
| tech-stack.md:804/:1126, technology-comparison.md:413/:731/:747 still show the start command as `--worker-class uvicorn_worker.UvicornWorker ... --proxy-headers --forwarded-allow-ips=...` [A-F11] | These example commands were superseded by `app.worker.RawPeerWorker` with no proxy flags (ADR-023, backend-architecture.md §2 row 0) but the wording was never corrected in the technology-evaluation documents | technology-evaluator | Doc drift only — `/build` already implements and ships the correct behaviour (T-025's `RawPeerWorker`, T-043's Dockerfile CMD, `.claude/project-config.md`'s `start:`, all fixed at /plan); only these two architecture-evaluation documents' example commands are stale | Next `/tech-stack` or `/architecture` revision |

## TD-003 — Blocked on a human answer already tracked as an open question

| ID | What | Blocked on | Interim state | Trigger to revisit |
|---|---|---|---|---|
| OQ-2 | Encrypted monthly off-platform `pg_dump` destination | Human names a destination + scoped credential | Dump stays dormant; platform daily backups (~7 days retention, to confirm) are the only mechanism; threat #28 recorded `accepted` | Human names a destination — enable at ~$0-1/mo, no code change (mechanism already exists per infrastructure.md §8) |
| OQ-3 | Registrable `.in` domain for both hosts | Human owns hosting/domain (ADR-002 Q3) | `base_url_prod`/`base_url_api_prod` stay `TBD` in `.claude/project-config.md`, explicitly (not silently) | Domain purchased and attached to both hosts — a `/release` gate item, not a `/build` blocker (M1-M5 run entirely on `localhost`) |
| OQ-10 (real — the platform's actual log-retention window; **not** the name/phone search wrongly labeled OQ-10 in rev 1, see implementation-plan.md § "ADR-014 scope note" [A-F3]) | Platform log retention figure, open-questions.md:93-96 | Human confirms the figure with the hosting platform at signup | Default applied: assume "days," treat `security_event` as the durable record; T-049's runbook prep records the confirmed figure once known | Human confirms at signup/`/release` — if very short, strengthens the case for a second durable sink (not a `/build` change) |

## TD-004 — Named architectural fallback, taken only if a spike fails

| ID | What | Condition | Fallback if triggered | Cost of the fallback |
|---|---|---|---|---|
| CSP `unsafe-inline` | Post-build inline-script hashing (task T-042) is meant to produce a CSP with no `unsafe-inline` | The hashing spike in T-042 fails (non-deterministic hash set, or Render rejects per-path headers of the required size) | `script-src 'self' 'unsafe-inline'`, recorded as a **stated weakening** with the ADR-010 H-C fallback (c) amended, not silently taken | Widens the residual in dependency-strategy.md's R16 (npm supply chain) — a malicious inline script would no longer need a hash collision, only injection. Must be called out at the next `/architecture` touch if taken |
| 120KB public-route byte budget (AD-1/C8) | `next build`'s first-load JS on `/` must be ≤120KB gzipped, gated in CI (T-042) | The budget cannot be met after reasonable trimming | ADR-004's named fallbacks: (i) hand-written ~2KB static public page in vanilla JS while the clerk app stays Next.js, or (ii) accept >3s on 3G and record it as a requirement change | Either is a GATE-visible decision (ADR-004), not a build-time improvisation — do not silently ship over budget |

## TD-005 — Explicitly out of scope for this MVP (not debt — a scope decision, restated for visibility)

- Load/performance testing beyond AC-010/AC-011 (no k6/Locust suite) — test-strategy.md §8, unchanged.
- NFR-006 (cost) and NFR-007 (uptime) have no product test case — assessed at architecture review and
  post-launch pinger monitoring respectively, per their own Verification columns.
- A `disabled_at`/soft-delete column on `clerk_account` (R2-10) — offboarding is the documented
  admin-resets-and-discards-OTP workaround; revisit only if clerk turnover becomes frequent enough to
  need a real disable flag (an additive migration if it happens).
- `pyotp`/TOTP for the admin clerk (OQ-8) — offered, not adopted; add only on explicit human request
  (+1 dependency, ~0.5-1 day, per dependency-strategy.md).
- The **real** OQ-9 (open-questions.md:80-91 — should complaint *detail views* be audited, not just
  writes?) — default applied and reconfirmed at rev 2 of the architecture review: **no** per-view
  audit trail. What exists instead is a rate **ceiling** (`detail`/`search` limiter scopes, T-026),
  not an audit log; the residual (a hijacked session reading contact details at a bounded rate) is
  carried as **accepted** in threat #24, not as debt. Nothing for `/build` to do unless a future
  human answer changes the default. (This is distinct from T-036/T-037, which implement ADR-014 Q3/Q4
  and are ordinary in-scope build tasks, not debt — see implementation-plan.md § "ADR-014 scope
  note.")

## Build-phase additions (appended by the /implement orchestrator; documentation drift, not code)

| id | Found at | Item | Owner | Revisit trigger |
|---|---|---|---|---|
| TD-B01 | T-001 code review (2026-09-10) | backend-architecture.md §1 line 14 labels `app/settings.py` "pydantic-settings", but dependency-strategy.md § "Deliberately not added" excludes that package. Code follows the dependency budget: a frozen dataclass over `os.environ`. The architecture label is stale. | solution-architect (doc fix) | next architecture doc revision |
| TD-B02 | T-001 security review (2026-09-10) | Task rows and tests cite BR-010 for the "docs/redoc/openapi 404 in prod" control, but BR-010's text is "no bulk public access". Real sources: backend-architecture.md §11 and dependency-strategy.md ("/docs → 404 test"). Behaviour is correct; the citation is wrong. | requirements-analyst (AC/BR linkage) | next requirements revision |
| TD-B03 | T-001 (2026-09-10) | ENVIRONMENT is fail-closed at settings level (unset/invalid → startup error). selfcheck (T-025/T-043) must additionally assert ENVIRONMENT == prod under the production profile so a mis-set non-prod value cannot reach a prod deploy. | backend-developer at T-043 | T-043 done-condition |
| TD-B04 | T-003 security review (2026-09-10) | DB-level `REVOKE UPDATE, DELETE` on the three append-only tables was removed from migration 0001: it was keyed on an ambient `DB_APP_ROLE` env var that cannot be verified as the real runtime role (an existing-but-wrong name silently "succeeds"). Until the platform provisions a second, non-owning application role, append-only enforcement is the application-level `before_execute` guard (T-004) only. When that role exists, add a dedicated migration that pins it by name and re-run against prod. | human (provision role at /release) + backend-developer (migration) | /release; infrastructure.md §12 runbook |
| TD-B05 | T-005 security review (2026-09-10) | `validate_password` uses a vendored 298-entry curated weak-password list (`app/core/common_passwords.txt`) instead of the ~10k-entry Django `common-passwords.txt.gz` (BSD-3) that security-architecture.md §3 references — no network access in the build session to fetch it with licence attribution (dependency-strategy.md §5). Swap in the real list with source URL, version and licence text. | backend-developer (needs human to supply/approve the file) | before /release; M3 security pass (T-032) |

## Self-audit

- Every carried advisory in `.ai/architecture/review-advisories.md` appears either as a task in
  implementation-plan.md (SEC-F1→T-025, SEC-F2→T-030, REL "reset-admin-password"→T-035) or as a row in
  TD-002 above with an owner and a reason it is not a `/build` task — **including the
  tech-stack.md/technology-comparison.md start-command wording item** (review-advisories.md:31-33),
  which rev 1 of this file omitted from TD-002 [A-F11, fixed this rework]. None is silently dropped.
- Every accepted/n-a threat-model.md item is deliberately **not** repeated here (it is architecture-
  owned residual risk, not implementation debt) — see the header note.
- Every item above has an id, a reason, and a revisit trigger, per this role's brief.
