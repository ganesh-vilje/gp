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
