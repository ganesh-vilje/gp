# Architecture Decision Records

Every human gate and every major internal decision gets an ADR. Never delete an
ADR; supersede it with a new one and mark the old `Status: superseded by ADR-00n`.

## ADR-000 — Template
Date: YYYY-MM-DD | Gate: — | Status: accepted | superseded | rejected
Decision:
Alternatives considered:
Reasoning:
Risks & mitigations:
Human notes:

## ADR-001 — Requirements approved (GATE_1)
Date: 2026-09-09 | Gate: GATE_1 | Status: accepted
Decision: Approve requirements rev 4 (.ai/requirements/) as the product baseline
for the panchayat-complaint-tracker MVP: single-panchayat pilot, clerk-mediated
complaint intake, auto-generated unique complaint number, status updates with
notes and full audit history, public unauthenticated status lookup by exact
number, two clerk permission levels (regular / admin clerk), minimal PII (name,
phone, complaint text; no government IDs).
Alternatives considered: (a) show citizen name/phone on the public page —
rejected for privacy (Q-001); (b) allow direct New→Rejected for duplicates —
rejected, all complaints pass through In Progress (Q-002 sub-question); (c)
single clerk role with out-of-band account admin — superseded by human decision
H1 (admin clerk role); (d) photo upload, SMS/WhatsApp, multi-tenant,
self-service filing in MVP — deferred to Future scope.
Reasoning: Both internal reviewers (product-reviewer rev 3, requirements-qa-
reviewer rev 4) returned APPROVED after 3 rework loops; 20 FRs, 11 NFRs, 17
user stories, 19 ACs, 16 business rules, all traced. Remaining findings are
medium/low advisories carried forward to the analyst for the next revision.
Risks & mitigations: Q-001/Q-002 accepted as defaults rather than deliberated —
easy to revisit before GATE_3 (data model) if the panchayat disagrees. Admin
self-lockout (Q-015) mitigated by recommending a second admin account (BR-013).
Human notes: "yes, accept defaults" — human also decided H1 (one admin clerk
creates accounts and resets passwords) and H2 (blank/malformed public lookup
input shows "Enter a valid complaint number", no lookup) during rework.

## ADR-002 — Technology stack approved (GATE_2)
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: Approve .ai/technology/ rev 5 (tech-stack.md, technology-comparison.md,
dependency-strategy.md) as the technology baseline. Layer decisions are ADR-003
to ADR-012 below. Internal approvals: architecture-reviewer, security-reviewer,
cost-reviewer, all APPROVED on rev 5 after three internal rework loops plus two
human-directed revisions (H3, H4). Reviewer advisories (11 medium, 5 low, none
blocking) are recorded in the artifacts and carried forward to /architecture.
Alternatives considered: rev 3 (Django monolith, server-rendered, internally
approved) — superseded by human decisions H3/H4 at the first GATE_2 presentation.
Reasoning: the human owns the framework choices; the org re-derived every
dependent layer around them and the reviewers verified the mechanisms.
Risks & mitigations: top risks R16 (npm supply chain — explicitly not fully
mitigated), R11 (~350–450 lines of owned security code, 20 test assertions),
C8/R17 (3 s/3G budget at risk, public page requires JavaScript; measured at
/build with a 2 KB fallback page), R9 (merged ≠ deployed — two human promotions).
Human notes (verbatim, GATE_2 answers 2026-09-09): "yes. Q1: India — use the
Mumbai region. Q2: $14-16/month is fine, no SSR. Q3: I own hosting, card and
domain. Q4: keep 20/min. Q5: yes, team knows FastAPI and TypeScript/React. Q6: I
own patching and backups; I hold the backup key. Q7: option (b), fixed status
messages. Q8: confirmed, public page may require JavaScript. Q9: a single .in
domain will be provided before real citizen data."
Consequences of the answers: Q1 selects the pre-analysed Fly.io Mumbai (bom)
variant for the API and database (ADR-009); Q6 names the human as ops owner,
which assigns the Dockerfile patching obligation that Fly.io requires and
enables the encrypted off-platform backup (human holds the key); Q7 and Q8 are
requirement changes routed to the requirements-analyst (ADR-013).

## ADR-003 — Backend: FastAPI JSON API (human decision H3/H4)
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: FastAPI (0.11x) on Python 3.13, JSON API only, sync handlers, one
monolithic service, gunicorn + uvicorn-worker (2 workers, timeout 30,
max-requests 1000), anyio threadpool capped at 4 tokens/worker.
Alternatives considered: Django 5.2 LTS (rev 1–3 recommendation, near-tie with
Rails 8); Node/TypeScript; Go.
Reasoning: human decision H3 ("changes: use FastAPI for the backend"), then H4
("Use FastAPI as a JSON API with a separate Next.js frontend"). Not re-litigated.
Risks & mitigations: R11 — sessions, CSRF, password policy, headers and the
production config gate become ~350–450 lines of owned code; mitigated by small
well-known libraries, no custom crypto, 20 named test assertions. R12 — no LTS
line; mitigated by version ceilings and a suite that exercises every middleware.
Human notes: Q5 — team knows FastAPI and TypeScript/React.

## ADR-004 — Frontend: Next.js 15 fully static export (human decision H4)
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: Next.js 15 (App Router, React 19, TypeScript 5) on Node 22 LTS, built
with output: "export"; public lookup prerendered with one client island; clerk
screens are static shells hydrated client-side; no dynamic route segments; no
SSR, ISR, server actions, route handlers or middleware; no Node process in
production. Target ≤120 KB gzipped first-load JS on the public route, gated in
CI. npm with committed package-lock.json.
Alternatives considered: rev 3 server-rendered templates + vanilla JS
(superseded by H4); Vite + React SPA (kept as the named fallback if Next.js's
payload fails NFR-001); Next.js on a Node server with SSR (+$7/mo, rejected on
PII-in-second-process and cost; human confirmed "no SSR").
Reasoning: static export is the only H4 variant that keeps citizen PII in one
server process, costs $0 to host, and adds no production runtime to patch.
Risks & mitigations: C8 — 3 s/3G budget at risk, measured at /build and
/test-app with a 2 KB hand-written public page as fallback (i). R17 — public
page requires JavaScript (see ADR-013). R14 — version skew: additive-only API
changes, API-first promotion order, chunk-load failure shows a reload prompt.
R16 — npm supply chain (see ADR-010).
Human notes: Q2 — "no SSR". Q8 — "confirmed, public page may require JavaScript."

## ADR-005 — ORM and migrations: SQLAlchemy 2.x (sync) + Alembic + psycopg 3
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: SQLAlchemy 2.x ORM, sync, psycopg[binary] 3 driver; Alembic
migrations committed, `alembic upgrade head` as the release command,
`alembic check` as the CI drift gate; migrations additive-only /
forward-compatible; statement_timeout ~10 s; request engine pool_size 4 +
max_overflow 2 per worker plus a separately sized AUTOCOMMIT engine for the
rate limiter (≤10 connections/worker, ≤20 total).
Alternatives considered: SQLModel (rejected: public DTO must differ from the row
shape); raw SQL with hand-written migrations; asyncpg/async SQLAlchemy
(rejected: blocking-call footguns for no benefit at <1 rps).
Reasoning: one schema authority for the append-only history and the limiter
table; fully typed so mypy pays for itself.
Risks & mitigations: psycopg 3 is LGPL-3.0 — recorded under the licence
"review required" class in dependency-strategy.md.
Human notes: none.

## ADR-006 — Database: managed PostgreSQL 17
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: Managed PostgreSQL 17, sslmode=require asserted by a settings test;
platform-run daily backups; an encrypted off-platform monthly dump is now
enabled because the human named themself as key holder (Q6), with a named
destination, ~90-day retention and a deletion step; go-live restore test into a
throwaway database. Production data never copied to dev, CI or AI tools.
Alternatives considered: SQLite on a VPS (cheaper, rejected on audit-trail
durability and backup ownership); document store (rejected: transactional
multi-row audit writes and a global uniqueness constraint).
Reasoning: FR-011/FR-014 audit history and AC-003 uniqueness under concurrency
need real transactions and constraints.
Risks & mitigations: single DB is one failure domain for data, sessions and the
limiter — fail-closed 503 with a friendly page; /healthz checks the DB.
Human notes: Q6 — "I own patching and backups; I hold the backup key."

## ADR-007 — Auth, sessions and CSRF: own thin layer on standard primitives
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: server-side session table (user_id NOT NULL — no anonymous rows) +
opaque httpOnly/Secure/SameSite=Lax __Host- cookie set by the API; Argon2id via
argon2-cffi (m=9216, t=4, p=1); roles via is_admin_clerk; must_change_password
enforced on every request; one-time passwords 60-bit from `secrets`, 72 h
expiry, single use, returned once in JSON (explicit decision to let the OTP
transit the client); password minimum length 12 (C5); idle 30–60 min, absolute
~9 h, browser-close expiry, rotation on login, revoke-all on reset; deny-by-
default middleware with a 4-entry public allow-list; django-style admin UI not
present; OpenAPI docs return 404 in production. CSRF: SameSite + Origin
allow-list + X-CSRF-Token — session-bound when authenticated, stateless
hmac_sha256(SECRET_KEY, __Host-csrfseed) when not, so the unauthenticated path
executes no SQL. Login limiter keyed username+IP with per-IP short-circuit;
per-account penalty is 429 + Retry-After, never a lock or a thread sleep.
Site and API must share one registrable .in domain; SameSite=None is forbidden.
Alternatives considered: Auth0/Clerk/Firebase Auth/Supabase Auth (rejected:
BR-016's "show the password once on screen" is inexpressible; ≤6 accounts);
JWT in localStorage (rejected: not revocable, XSS-readable); signed-cookie
sessions (rejected: cannot revoke on password reset); BFF proxy (+$7/mo, only
if a single domain is impossible).
Reasoning: D9 admin-reset flow and revocation needs.
Risks & mitigations: R11 owned code — 20 test assertions incl. CSRF 403 on both
an authenticated write and the public lookup. R13 — public lookup needs a
first-party cookie; friendly "enable cookies" message.
Human notes: Q9 — "a single .in domain will be provided before real citizen
data."

## ADR-008 — Rate limiting: in-repo atomic Postgres counter, 20/IP/min
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: fixed-window limiter over a Postgres counter table using one atomic
INSERT … ON CONFLICT DO UPDATE … RETURNING on a dedicated AUTOCOMMIT engine,
committed independently of the request; 20 lookups per IP per minute on the
public lookup (Q-013 default, confirmed); client IP from the platform's
forwarded header with an explicit TRUSTED_PROXY_HOPS, IPv6 normalised to /64,
fail-closed on a missing header; fails closed to a friendly 503; AC-011
asserted under parallel requests. Fixed window allows up to 2× at a boundary
(accepted).
Alternatives considered: django-ratelimit + DatabaseCache (rev 1, withdrawn:
non-atomic incr, culls at 300 entries); managed Redis/Valkey (~$10/mo, rejected
on cost for <1 rps); single worker (rejected: mechanism must be worker-
independent); CAPTCHA (out of MVP scope).
Reasoning: correct under any worker/thread count without a paid service.
Risks & mitigations: R3 — per-IP limiting misfires behind shared village NAT;
config-driven threshold, throttle-event logging, complaint-number entropy floor
(≥40 random bits, non-sequential, checksum) as the second defence.
Human notes: Q4 — "keep 20/min."

## ADR-009 — Hosting and deploy: Fly.io Mumbai for API + Postgres, Render Static Site for the frontend
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: Human answer Q1 ("India — use the Mumbai region") selects the
pre-analysed residency variant recorded in tech-stack.md § Hosting: the FastAPI
service runs as a Fly.io Machine in the `bom` (Mumbai) region with Fly Managed
Postgres in the same region; this requires a Dockerfile, whose base-image
patching obligation is assigned to the human (Q6). The exported Next.js
frontend contains no citizen data and stays on a free Render Static Site (CDN,
TLS, custom domain). Auto-deploy OFF on both deployables; a human promotes the
API first, then the static site; `alembic upgrade head` as the release command;
no staging (CI migration dry-run, additive-only migrations, free frontend PR
previews as compensating controls). main is protected: require a PR, green
checks, linear history, no force-push, no required human review; third-party
Actions SHA-pinned; Dependabot auto-merge only for patch/minor bumps of
already-present packages, with a 7-day minimum release age for npm.
Alternatives considered: Render Singapore for API + DB (rev 5 default, rejected
by Q1 — no India region); single VPS in Bangalore ($5–6/mo, rejected: human
would own OS/Postgres patching and backup verification, and the audit trail is
a Must); Railway (usage-based billing); hyperscaler (disproportionate); Vercel
Hobby for the frontend (non-commercial terms).
Reasoning: residency requirement stated by the human; Fly.io is the only
shortlisted option with an in-country region at similar cost. Recomputed in
tech-stack.md rev 5.1: Fly Machine shared-cpu-1x 512 MB $3–5 + Fly Managed
Postgres $7–9 + frontend $0 + domain ~$1 (+ $0–1 optional dump destination) ⇒
≈$11–16/mo, inside the approved ≤$16/mo envelope; Fly Managed Postgres' exact
plan price, connection limit and retention are verified at signup. Deploy
mechanism: the human runs `fly deploy` from a local checkout of the CI-green
reviewed commit (no Fly token in CI), then promotes the static site.
Risks & mitigations: R1 single instance, no HA (office-hours 99% only). R6 no
staging. R9 merged ≠ deployed — two human promotions per security release, ~20
min each. Fly.io is more CLI-oriented and has a weaker managed-DB story than
Render — the human now owns ops, which is what made the variant acceptable.
Frontend assets on a non-India CDN carry no citizen data; if the residency rule
also covers static assets, Fly.io can serve the static export from Mumbai
(+~$2–5/mo) — to be confirmed by the evaluator's rev 5.1 amendment.
Human notes: Q1 — "India — use the Mumbai region." Q2 — "$14-16/month is fine,
no SSR." Q3 — "I own hosting, card and domain."

## ADR-010 — Tooling, CI and supply chain
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: uv (committed uv.lock) for Python; npm (committed package-lock.json,
`npm ci --ignore-scripts`) for the frontend; pytest + httpx TestClient on real
Postgres; Vitest + Testing Library; Playwright for Python (4–6 E2E specs
against the exported frontend and the real API); Ruff (E,F,I,B,UP,S) and Biome
(security and correctness rule groups explicit); mypy (app package only) and
tsc --noEmit; openapi-typescript generates committed client types with a CI
staleness check; a post-build step hashes inline scripts to produce a CSP with
no unsafe-inline (spike A-T15; recorded fallback: unsafe-inline as a stated
weakening); pip-audit and `npm audit` + `npm audit signatures`; `selfcheck`
production-config gate; GitHub Actions with SHA-pinned actions and
`permissions: contents: read`. Budgets: ≤10 Python runtime deps (8 used), ≤12
Python dev, ≤6 npm runtime (3), ≤12 npm dev (10).
Alternatives considered: pip-tools/Poetry; pnpm; Django test runner/Selenium/
Cypress; flake8+black+isort+bandit; ESLint+Prettier; Pyright.
Reasoning: one tool per job per language; evidence-backed gates for the org.
Risks & mitigations: R16 npm supply chain — ~350–450 resolved packages; a
malicious package on the allow-listed origin has full clerk-session capability
including every OTP issued while the page is open; bounded (not eliminated) by
CSP connect-src, the idle window and response minimisation; no control detects
a zero-day malicious release. R4 uv is young — pip fallback under an hour.
Human notes: Q5 — team knows the stack.

## ADR-011 — Observability: platform logs + uptime pinger + security_event table, no Sentry
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: stdout logs captured by the platform; free uptime pinger on /healthz
(which checks the DB); an append-only security_event table in the existing
Postgres recording login success/failure, admin password resets, account
creation and throttle events with actor hash, derived IP and timestamp — never
the password or the complaint number. No error-tracking SaaS at launch.
Alternatives considered: Sentry free tier (rev 1, withdrawn: local-variable
capture leaks PII to a third-party region; hardened recipe pre-approved if
wanted later); self-hosted Grafana stack (costs more than the app).
Reasoning: removes the last third-party PII processor; keeps NFR-007 evidence.
Risks & mitigations: R7 — a 500 on an unpinged page is noticed by a phone call.
Human notes: none.

## ADR-012 — No AI/LLM in the MVP
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: No LLM, no AI SDK, no vector database. Production data never enters
an AI tool.
Alternatives considered: LLM categorisation, summarisation, fuzzy "did you
mean" lookup.
Reasoning: no FR/NFR needs generation or classification; BR-004 mandates
exact-match lookup; it would add cost, latency and a PII processor.
Risks & mitigations: none; revisit only if a requirement appears.
Human notes: none.

## ADR-013 — Requirement changes caused by H4 and GATE_2 answers Q7/Q8
Date: 2026-09-09 | Gate: GATE_2 | Status: accepted
Decision: (a) The public lookup page may require JavaScript (Q8): the
requirements-analyst relaxes BR-015's "or at the very first server check"
phrasing, deletes the "with JS disabled" half of AC-018, and changes the persona
line to "assumed to have a JavaScript-capable browser"; the FR-020 rule that
malformed input performs no lookup is retained in full and asserted at the API.
(b) The public status page shows a fixed set of public status messages instead
of the clerk's free-text latest note (Q7, option b, resolving Q-016): FR-009 and
BR-005 are amended so the public DTO carries a `public_update` drawn from an
enumerated set; the clerk free-text note is clerk-only. (c) Q-013 resolved at
20 lookups/IP/minute (Q4).
Alternatives considered: keep a no-JS public page by reverting only the public
route to plain HTML (offered, declined by Q8); a separate deliberately-public
free-text field (Q7 option a, declined).
Reasoning: H4 makes a no-JS React page impossible; free text on an
unauthenticated page is an unstructured PII channel (security-reviewer F3).
Risks & mitigations: NFR-008/NFR-009 coverage becomes full once the enumerated
field exists in /architecture.
Human notes: Q7 — "option (b), fixed status messages." Q8 — "confirmed, public
page may require JavaScript."

## ADR-014 — UX/UI direction approved (GATE_4)
Date: 2026-09-09 | Gate: GATE_4 | Status: accepted
Decision: Approve .ai/ux/ and .ai/design/ rev 3 as the UX/UI baseline: 6 screens
(Public Status Lookup; Login; Change Password; Complaints; Accounts; 404), 6
flows covering US-001..US-017; a "village-office register" visual direction —
system fonts, single deep-green primary #146C43 (6.46:1), warm light neutrals,
five labelled status colours ≥4.5:1, low-to-medium density, hand-written CSS
custom properties, no framework/icon pack/dark mode/shadows/animation; WCAG 2.2
AA commitments (keyboard, focus management, live-region announcements,
--color-border-interactive #767676 at 4.54:1, ≥44 px public / ≥24 px clerk
targets, 320 px reflow, <html lang="en">). Internal approvals: ux-reviewer
(rev 2), product-reviewer (rev 2), accessibility-reviewer (rev 3), after two
rework loops.
Key UX decisions: (1) status-update control offers only legal next statuses
(BR-002); (2) public page shows five fixed status messages, never the clerk
note (Q7/ADR-013); (3) one-time-password screen gated by an explicit
acknowledgment checkbox plus beforeunload/route guard (BR-016); (4) concurrent
edits shown as a non-blocking advisory (BR-011); (5) client-side instant
rejection of malformed complaint numbers with the API as sole authority
(FR-020/NFR-001); (6) Complaints list has find-by-number, name/phone search,
status filter and 25-row "Load more" pagination (NFR-010).
Alternatives considered: SaaS dashboard template (sidebar, cards, icon library,
dark mode) — rejected on byte budget and users; free-choice status dropdown
with server rejection; sanitized clerk note on the public page; dismissible OTP
warning; blocking 409 on concurrent edit; Unicode status glyphs (considered,
rejected — visual-direction.md UX-F6).
Requirements side-effects: BR-016 and AC-017 amended to a 12-character password
minimum (rev 6) to match ADR-007; the human accepted two UX additions as MVP
scope — name/phone search on the clerk list (OQ-10) and voluntary self-service
password change (OQ-9) — requirements-analyst adds matching FRs at the next
requirements revision. Q-007 resolved: 7-day correction window.
Risks & mitigations: 120 KB public-route budget still measured only at /build
(fallback 2 KB page per ADR-004); shared live region for search + pagination
announcements may collide (advisory, accessibility F1 rev 3); nested-dialog
aria-modal/inert handling to be clarified at code review (F2 rev 3).
Human notes (verbatim, 2026-09-09): "yes. Q1: English now; Telugu will be added
later, so keep every string in one module. Q2: use the defaults for the test
project. Q3: accept name/phone search on the clerk list. Q4: accept voluntary
password change. Q5: confirm 7 days." Consequence of Q1: a single strings
module is a build requirement for /architecture and /plan (i18n-ready, English
only at launch).

## ADR-015 — Modular monolith layering
Date: 2026-09-10 | Gate: GATE_5 | Status: accepted
Decision: routers → services → repositories, dependencies point downward only; business rules
live only in services (BR-002 transitions, 7-day window, history writes).
Alternatives considered: rules in routers; a shared "utils" layer everything imports.
Reasoning: testable without HTTP; one place per rule (AD-11).
Risks & mitigations: none beyond discipline; enforced by an import-linter check at /plan.
Human notes: none.

## ADR-016 — Complaint-number codec
Date: 2026-09-10 | Gate: GATE_5 | Status: accepted
Decision: 8 Crockford-base32 symbols from `secrets` (40 random bits) + 1 weighted checksum
symbol, displayed `XXXX-XXXXX`, case-insensitive, I/L→1 and O→0 accepted; stored canonical
CHAR(9); validated before any DB access; insert-retry on unique conflict (AC-003).
Alternatives considered: sequential/short numbers (enumerable, ADR-008 floor); UUID (unreadable by phone).
Reasoning: shortest form meeting the ≥40-bit floor plus a checksum.
Risks & mitigations: transcription errors — checksum rejects them client- and server-side.
Human notes: Q3 — "yes, XXXX-XXXXX Crockford is fine."

## ADR-017 — Concurrency on a complaint row
Date: 2026-09-10 | Gate: GATE_5 | Status: accepted
Decision: `SELECT … FOR UPDATE` on the complaint row; last-write-wins current state;
unconditional history insert in the same transaction; transition legality re-checked inside
the lock; staleness surfaced as a non-blocking advisory (BR-011, UX decision 4).
Alternatives considered: optimistic version column returning 409.
Reasoning: no audit gain from blocking a clerk mid-call; both writers' history is kept.
Risks & mitigations: none material at 1–5 clerks.
Human notes: none.

## ADR-018 — Single error envelope
Date: 2026-09-10 | Gate: GATE_5 | Status: accepted
Decision: typed domain errors → `{error:{code,message,fields}}` with stable machine codes
(error-catalog.md); the client maps codes to strings in the single strings module (AD-12).
Anonymous ⇒ 401 `not_authenticated`; wrong role / failed CSRF ⇒ 403 `forbidden`; wrong
current password ⇒ 422 `invalid_current_password`; oversized body ⇒ 413.
Alternatives considered: ad-hoc HTTPException detail strings per route.
Reasoning: translatable, testable, one client mapper.
Risks & mitigations: drift between docs — error-catalog.md is the single source.
Human notes: none.

## ADR-019 — Session idle window
Date: 2026-09-10 | Gate: GATE_5 | Status: accepted
Decision: 45 min idle, 9 h absolute, browser-close expiry (within ADR-007's 30–60 range);
both are environment variables.
Alternatives considered: 30 min (re-login during a long call); 60 min (weakest approved end).
Reasoning: office workflow.
Risks & mitigations: hijacked-session bound is 45 min; see ADR-021 and threat #24.
Human notes: Q4 — "45 min idle / 9 h absolute is fine."

## ADR-020 — Client-IP derivation
Date: 2026-09-10 | Gate: GATE_5 | Status: accepted
Decision: the raw TCP peer address is authoritative; `Fly-Client-IP` / `X-Forwarded-For` are
read by `core/client_ip.py` only when the peer is inside `TRUSTED_PEER_CIDRS`, else discarded;
`TRUSTED_PROXY_HOPS` gates the XFF fallback; `selfcheck` refuses to start without both;
verified by SEC-T21 against a real server process and by a live spoofing attempt plus a
two-address distinctness check at /release.
Alternatives considered: trusting the header because the platform "usually" sets it.
Reasoning: a wrong hop count makes the rate-limit key attacker-chosen (SEC-F1).
Risks & mitigations: a wrong CIDR collapses all keys into one bucket — runbook §12.3.
Human notes: none.

## ADR-021 — Session issuance on login
Date: 2026-09-10 | Gate: GATE_5 | Status: accepted
Decision: always mint a new session token on login; revoke only the session presented in the
request's own cookie (fixation defence); concurrent sessions per clerk allowed; revoke-all on
password change, admin reset and `reset-admin-password`. Interprets ADR-007's "rotation on login".
Alternatives considered: revoke-all on login (logs the clerk's other device out mid-shift);
reuse the presented session (fixation).
Reasoning: office desktop + phone is a real pattern; `session.user_id` is NOT NULL so there is
no pre-auth cookie to fixate.
Risks & mitigations: read ceiling is keyed on user_id, not session, so extra sessions buy no
extra PII budget (threat #24).
Human notes: none.

## ADR-022 — Idempotent complaint creation
Date: 2026-09-10 | Gate: GATE_5 | Status: accepted
Decision: `POST /api/complaints` carries a client-generated `client_request_id` UUID with a
unique index; a duplicate returns the existing complaint with `duplicate: true`; the client
shows "your complaint may already be saved — check the list" instead of a bare Retry.
Alternatives considered: generic Retry on a non-idempotent POST (REL-F1: duplicates BR-008
forbids deleting); a general idempotency-key layer (no driver).
Reasoning: the audit trail is the core deliverable (AD-3).
Risks & mitigations: key does not survive a closed tab — visible, not silent, duplicate.
Human notes: none.

## ADR-023 — The application is the only interpreter of forwarding headers
Date: 2026-09-10 | Gate: GATE_5 | Status: accepted
Decision: gunicorn runs `--worker-class app.worker.RawPeerWorker`, a `UvicornWorker` subclass
with `CONFIG_KWARGS = {"proxy_headers": False, "forwarded_allow_ips": []}`, so
`scope["client"]` is always the raw peer that ADR-020 depends on; `FORWARDED_ALLOW_IPS` must be
unset; behavioural assertions in the worker/selfcheck. `.claude/project-config.md` `start:`
and the tech-stack start commands are updated at /plan to drop `--proxy-headers` /
`--forwarded-allow-ips`.
Alternatives considered: omitting the flags (a no-op — gunicorn has no `--proxy-headers`,
uvicorn's default is True); aligning `--forwarded-allow-ips` with CIDRs (takes literal hosts).
Reasoning: SEC-S1/SEC-F1 — uvicorn rewrites the peer before app code runs.
Risks & mitigations: advisory SEC-F1 (rev 4): move two assertions into the worker class.
Human notes: none.

## ADR-024 — Architecture approved (GATE_3 + GATE_5)
Date: 2026-09-10 | Gate: GATE_3, GATE_5 | Status: accepted
Decision: Approve .ai/architecture/ (rev 4), .ai/security/threat-model.md (rev 4, 65 threats:
37 mitigated / 18 accepted / 10 n-a), .ai/database/ (rev 4: 7 tables, 12 indexes) and .ai/api/
(rev 4: 15 endpoints — 4 public, 8 clerk, 3 admin) as the architecture baseline. Decisions
D-A..D-E (auth, data core, API style, deploy, observability) and ADR-015..ADR-023 above.
Internal approvals: cost-reviewer (rev 1), performance-scalability-reviewer (rev 2),
reliability-reviewer (rev 2), security-reviewer (rev 4), architecture-reviewer (rev 4) after
three rework loops (the cap). Estimated cost $11–16/month, ≈$265–385 over 24 months.
Alternatives considered: recorded per decision in solution-architecture.md § Decisions and
§ Complexity budget (queue, cache, staging, BFF/SSR, second service, feature flags rejected).
Reasoning: every mechanism cites a driver AD-1..AD-12; every "mitigated" threat names a
mechanism a reviewer traced to a component; the three residuals the human accepts are named.
Risks & mitigations: (1) bulk PII read by a hijacked session — bounded at 120 reads/user/hour
(threat #24, accepted); (2) single-vendor backups, no off-platform dump (threat #28, accepted
per Q1); (3) captured OTP / malicious npm dependency — OTP consumed at first login, 72 h,
revoke-all (threats #7/#15/#50, accepted). Non-blocking advisories (4 medium, ~12 low) in
.ai/architecture/review-advisories.md for /plan.
Human notes (verbatim, 2026-09-10): "yes. Q1: default, no dump destination for the test
project. Q2: placeholders for now. Q3: yes, XXXX-XXXXX Crockford is fine. Q4: 45 min idle /
9 h absolute is fine. Q5: yes, provision a second admin at go-live." Consequence of Q5: the
/release go-live checklist provisions a second admin clerk (BR-013); OQ-5 default overridden.

## ADR-025 — Implementation plan approved (GATE_6)
Date: 2026-09-10 | Gate: GATE_6 | Status: accepted
Decision: Approve .ai/development/ (rev 4: implementation-plan, milestones, coding-guidelines,
change-impact-map, technical-debt) and .ai/testing/ (rev 3: test-strategy, test-cases,
regression-plan, test-plan) as the build baseline. 51 tasks (T-001..T-049 plus T-003a, T-006a,
T-010a; T-015 folded away) in 5 milestones; 19/19 ACs covered; 142 test cases (128 always-run,
~8 min; 2 nightly; 12 release-gate). Internal approvals: architecture-reviewer (rev 3),
test-architect (rev 4) after 3 rework loops (the cap). Application code is now unlocked.
Sub-decisions fixed by the plan: injectable clock (api/app/core/clock.py) instead of a
time-freezing library; middleware chain registered in two steps (rows 4-6 at T-006, rows 1-3 at
T-010a) with the exact order asserted by TC-SEC-039; gunicorn binds literal 8080 (Fly sets no
$PORT); dev server runs with --no-proxy-headers for ADR-023 parity; import-linter not adopted
(hand-written import-graph test + CI greps); voluntary password change and name/phone search are
in-scope tasks (ADR-014 Q3/Q4), not open questions.
Alternatives: Docker-based local Postgres (rejected — Docker not installed, Q1); branch per task
off main with agent merges (rejected — human merges milestone branches into master, Q4);
freezegun/time-machine (rejected in favour of an injectable clock, no new dependency).
Reasoning: every task cites a runnable command and existing TC ids; fixtures precede consumers;
the first slice is demoable end-to-end without M2-M5.
Human notes (verbatim, 2026-09-10): "yes. Q1: Python 3.11.9 on the machine (let uv install 3.13
for the project), Node 22.21.0, uv 0.10.8, Docker NOT installed — plan T-001 to work with a
locally installed PostgreSQL 17 instead, and tell me what to install. Q2: yes GitHub Actions; I
will add the remote before T-016. Q3: yes, verify and bump uv to 0.10.8 at T-001. Q4: feature
branch per milestone, I merge to master." Consequences: project-config.md db_start/toolchain/
build lines updated; T-001/T-017 and the M5 demo note that Docker builds run in CI only; git
workflow section rewritten for build/M1..M5 branches off master.
