# Technology Comparison — panchayat-complaint-tracker

Companion to `tech-stack.md`. Date 2026-09-09. Baseline: requirements rev 4 (GATE_1).

**Rev 5.1 — GATE_2 APPROVED (2026-09-09); post-approval housekeeping only.** Nothing is re-scored
and no layer is re-litigated. Two changes: **(a) Layer 8 records the selected hosting configuration
as Fly.io `bom` (Mumbai) Machine + Fly Managed Postgres, with the free Render Static Site kept for
the frontend** — the tie in table 8.0 is now broken by **GATE_2 answer Q1 ("India — use the Mumbai
region")** rather than by OPS, and the Dockerfile it requires is acceptable because **Q6 named an
owner** ("I own patching and backups"); **(b) the coherence table's NFR-008/009 row moves from
PARTIAL to "full once the enumerated `public_update` field exists", because Q7 chose option (b)
(fixed status messages)**, and the C7/R17 requirements change is now **accepted by the human** (Q8).
Costs in this document are superseded by `tech-stack.md` § Estimated monthly cost (**≈$11–16/mo,
working figure ≈$13 — inside the approved ≤$16**). Full answer-by-answer record:
`tech-stack.md` § Changelog (rev 5 → rev 5.1).
**Rev 5** — third internal review pass on rev 4. Layer choices are **unchanged**; what changed is
(a) Layer 4.3 now evaluates and rejects the **tiered CSRF alternative** and records the **stateless
anonymous token** (H-A/arch F9), (b) Layer 4.1's `httpOnly`-cookie note is corrected to say what the
flag does and does not bound (H-B/sec F2), (c) Layer 2/2a record the **no-dynamic-segment route
shape** (arch F3) and the **CSP inline-script hashing decision** (H-C), (d) Layer 9 gains
`openapi-typescript`, `npm audit signatures`, `--ignore-scripts` and the host-mirroring E2E server,
and (e) the carried-forward table carries every new binding constraint. Full finding-by-finding
changelog: `tech-stack.md` § Changelog (rev 4 → rev 5).

**Rev 4** — rebuilt for the two human decisions taken at GATE_2:

> **H3: "changes: use FastAPI for the backend"**
> **H4: "Use FastAPI as a JSON API with a separate Next.js frontend."**

**How decided layers are handled in this document.** Layer 1 (backend framework) and Layer 2
(frontend) are marked **selected by human decision**. Their rev-3 scoring tables are **kept
unchanged for the record**, and the newly selected options are scored **honestly** — including
where they score *below* the rev-3 recommendation on this particular requirement set. **No table
was re-weighted to make the chosen option win.** Recording the trade is how it stays visible to
/architecture and to the ADR; overriding the human is not on the table and does not happen anywhere
in these three documents.

**Layers rescored in rev 4** (because H3/H4 genuinely opened them): **Layer 1a — ORM & migrations**
(new), **Layer 2a — frontend rendering mode** (new), **Layer 4 — auth**, split into session
mechanism / password hashing / CSRF, **Layer 8 — hosting**, extended with frontend hosting and the
deploy model for two deployables, and **Layer 9 — tooling**, rewritten for two toolchains.
**Layers unchanged in substance:** 3 (database engine), 5 (rate limiting, with one new rejected
option), 6 (background jobs), 7 (file storage), 10 (observability), 11 (AI/LLM).

Full finding-by-finding and decision-by-decision changelog lives in `tech-stack.md`
§ Changelog (rev 3 → rev 4) and § Changelog (rev 4, second pass).

## How to read these tables

Scores are **1 (poor) to 5 (excellent)** *against this project's requirements only* — not
a general verdict on the technology. A 2 here can be a 5 on a different project.

Weights (W) reflect how strongly each criterion is driven by the requirements:

| Criterion | W | Requirement it comes from |
|-----------|---|---------------------------|
| **COST** — low recurring cost | 3 | NFR-006 (Must), MVP scope "low-cost hosting" |
| **SCALE** — right-sized for 1–5 clerks / few hundred lookups/day | 2 | NFR-002, AC-010, intake |
| **OPS** — low operational burden; no ongoing ops owner exists | 3 | Personas (Operator is one-time only), FR-015, A11 |
| **PII** — keeps name/phone tightly held, few third-party processors | 3 | NFR-008, NFR-009, BR-005, BR-009, AC-006, AC-012 |
| **AUDIT** — transactional append-only history, safe under concurrency | 3 | FR-011, FR-014 (Must), BR-008, BR-011, AC-009, AC-014 |
| **UNIQ** — complaint-number uniqueness under concurrent creation | 3 | FR-013, BR-001, AC-003 |
| **RATE** — enforceable per-IP rate limit, no enumeration surface | 2 | NFR-004, NFR-005, BR-010, AC-011, Q-013 |
| **AUTH** — username/password + admin-created accounts + admin reset shown once on screen + forced change + URL-level role denial | 3 | NFR-003, FR-001, FR-017–019, BR-013, BR-016, AC-017 |
| **3G** — small payload, few round trips, works on low-end devices | 3 | NFR-001, AC-010, persona, FR-020/BR-015/AC-018 |
| **SKILL** — mainstream, hireable, no stack preference stated | 2 | Constraints (human), D11 |
| **SUPPLY** — size and reviewability of the dependency/supply-chain surface (new in rev 4) | 2 | D3 (nobody patches), NFR-008/009, dependency-strategy.md §1 |

Weighted totals are shown for the layers where a genuine trade-off exists. Where a
layer's answer is "none needed", the table records why rather than scoring.

---

## Layer 1 — Language & backend framework — **SELECTED BY HUMAN DECISION H3/H4**

**Rev-3 table, kept unchanged for the record** (weights as above, SUPPLY not yet in use;
maximum possible = 135):

| Option | COST(3) | SCALE(2) | OPS(3) | PII(3) | AUDIT(3) | UNIQ(3) | RATE(2) | AUTH(3) | 3G(3) | SKILL(2) | Weighted |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Django 5.2 LTS / Python 3.13 *(rev 3's recommendation — superseded)* | 5 | 5 | 4 | 5 | 5 | 5 | 4 | 5 | 5 | 5 | **130** |
| Rails 8 / Ruby 3.3 | 5 | 5 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 4 | **130** |
| Node 22 / TypeScript (Next.js or Express + Prisma) | 5 | 5 | 3 | 4 | 4 | 4 | 4 | 3 | 3 | 5 | **106** |
| Go / `net/http` + templates + sqlc | 5 | 5 | 5 | 5 | 4 | 4 | 4 | 2 | 5 | 3 | **114** |
| **FastAPI 0.11x / Python 3.13** ✅ **(H3)** | 5 | 5 | 4 | 5 | 5 | 5 | 4 | **3** | 5 | 5 | **124** |

**The FastAPI row, scored honestly and not massaged:**
- **AUTH = 3, not 5.** This is the whole difference and it is the same reason Node scored 3 in
  rev 1: BR-016's "admin sets a password, shown once, forced change at next login", FR-019's
  URL-level role denial, session revocation on reset, CSRF and password policy are **assembled by
  us** rather than configured. `tech-stack.md` § Auth turns that into a concrete design with sixteen
  test assertions, which is what makes 3 acceptable rather than dangerous — but it is not a 5, and
  pretending otherwise would hide risk **R11** (≈350–450 lines of security-relevant code we own).
- **AUDIT/UNIQ = 5** because SQLAlchemy 2.x + Alembic + real Postgres give the same guarantees
  Django's ORM did (Layer 1a), and the concurrency tests (AC-003, AC-014) are written the same way.
- **RATE = 4** unchanged: the atomic upsert was always ours, not the framework's. FastAPI neither
  helps nor hurts.
- **PII = 5, on a different basis than Django's 5.** Django scored 5 because templates render only
  what they name. FastAPI scores 5 because `response_model` **filters output to a declared schema**
  — a mechanically stronger control — but only if it is used on every route, which is why it is
  a binding constraint and a test (risk **R15**).
- **OPS = 4** — same as Django: one service, platform-managed runtime. The 0.x/no-LTS problem
  (**R12**) is a maintenance risk rather than an operations-burden one, and it is offset by the
  retirement of the April 2028 Django EOL cliff.
- **SKILL = 5.** FastAPI is mainstream, heavily documented and highly AI-assistable (D11).

**Conclusion for the record:** FastAPI scores **124 against Django's 130** on *this* requirement
set, and the gap is entirely the auth/forms/CSRF batteries. That is a real cost, it is fully
itemised in `tech-stack.md` (R11, R12), and it is **accepted because the human decided it**. On a
project with a public API, a mobile client or heavy async I/O the ranking would invert — which is
exactly the point of scoring against requirements rather than in the abstract.

**Also considered and rejected within H3's scope (not scored):** Litestar (closest FastAPI
alternative, better batteries, materially smaller community — against D11/D3); Flask + extensions
(would need Flask-Login, Flask-WTF, Flask-SQLAlchemy… four small dependencies to approximate what we
build in one place); Django REST Framework as a "JSON API on Django" compromise (would have kept
`contrib.auth` and satisfied H4's "JSON API" too — **not offered, because H3 named FastAPI and this
document does not re-litigate it**; recorded only so nobody thinks it was overlooked).

**Rejected without scoring (rev 3, unchanged):** PHP/Laravel, Java/Spring Boot, any
serverless-first framework (cold starts fight the 3 s budget).

---

## Layer 1a — ORM & migrations (new in rev 4 — forced by H3)

Django supplied both. FastAPI supplies neither, so this is a genuine new decision.

| Option | OPS(3) | AUDIT(3) | UNIQ(3) | PII(3) | SKILL(2) | SUPPLY(2) | Weighted |
|---|---|---|---|---|---|---|---|
| **SQLAlchemy 2.x (sync) + Alembic + `psycopg[binary]` 3** ✅ | 4 | 5 | 5 | 5 | 5 | 4 | **75** |
| SQLModel (+ Alembic) | 4 | 4 | 5 | **2** | 4 | 3 | **59** |
| Raw `psycopg` 3 + hand-written SQL migrations | 2 | 3 | 5 | 5 | 3 | **5** | **61** |
| Tortoise ORM / Piccolo (async-native) | 3 | 4 | 4 | 4 | 2 | 3 | **55** |

(Maximum possible = 85.)

Notes on the numbers:
- **SQLModel scores 2 on PII** — the decisive number. Its selling point is that *one class is both
  the table and the API schema*, and NFR-009 requires the public response to be a **different
  shape** from the row (no `name`, no `phone`). A library that encourages conflating them pushes
  directly against the single most important PII control in the project (R15). Maintenance is also
  thinner than SQLAlchemy's (effectively one maintainer, 0.0.x versions) against D3.
- **Raw SQL scores 5 on SUPPLY** (two fewer packages) and **2 on OPS**: every history insert,
  the session table, and any drift detection become hand-maintained SQL with no schema authority.
  That is how audit tables get out of sync (FR-011/FR-014). It wins on dependency count and loses
  on the thing that matters.
- **SQLAlchemy loses one point on OPS** for its genuine learning curve (session/identity map) and
  because `alembic revision --autogenerate` misses some constraint changes, so migrations must be
  **reviewed** and `alembic check` must gate CI. That is a process cost, stated rather than assumed.
- **Async-native ORMs score 2 on SKILL**: smaller ecosystems, and they force the async execution
  model that `tech-stack.md` rejected on safety grounds at <1 rps (D1).
- **Sync vs async is decided here, not in the framework layer:** all handlers are `def`, the
  threadpool is capped at 4 tokens per worker, and the reason is that one accidentally blocking call
  (Argon2, a sync driver, a `sleep`) stalls an entire async worker — a failure mode that is hard to
  catch in review, which is exactly the wrong kind of risk under D11.

---

## Layer 2 — Frontend — **SELECTED BY HUMAN DECISION H4**

**Rev-3 table, kept unchanged for the record** (maximum possible = 80):

| Option | COST(3) | OPS(3) | PII(3) | RATE(2) | 3G(3) | SKILL(2) | Weighted |
|---|---|---|---|---|---|---|---|
| Server-rendered templates, hand CSS, ~100 lines vanilla JS, no npm *(rev 3's recommendation — superseded)* | 5 | 5 | 5 | 5 | 5 | 5 | **80** |
| Server-rendered templates + HTMX 2.x (vendored) | 5 | 5 | 5 | 5 | 4 | 4 | **75** |
| React SPA (Vite) + JSON API | 4 | 3 | 3 | 4 | 2 | 5 | **54** |
| Next.js (React) | 4 | 3 | 3 | 4 | 3 | 5 | **57** |

**Rev-4 rescore of the *selected* option, with SUPPLY added** (maximum possible = 90):

| Option | COST(3) | OPS(3) | PII(3) | RATE(2) | 3G(3) | SKILL(2) | SUPPLY(2) | Weighted |
|---|---|---|---|---|---|---|---|---|
| **Next.js 15, static export, small client island** ✅ **(H4)** | **5** | 4 | 4 | 4 | **2** | 5 | **2** | **65** |
| Next.js 15 with a Node/SSR server (`next start`) | 3 | 2 | **2** | 4 | 2 | 5 | 2 | **51** |
| Next.js static export + BFF proxy through a Node server | 3 | 2 | 2 | 5 | 2 | 5 | 2 | **53** |
| Vite + React SPA (no Next.js) | 5 | 4 | 4 | 4 | 3 | 4 | 3 | **69** |

Notes — these are the numbers that matter for /architecture:
- **COST = 5 for the static export** because Render Static Sites are free: the frontend adds **$0**
  to the bill. The SSR variants score 3 (+$7/mo, ~50% on top of the hosting line, against D2).
- **3G = 2 for every Next.js variant.** This is the honest cost of H4 and the source of
  **Conflict C8**: React 19 + the App Router runtime is a floor of ~90–110 KB gzipped against a
  ~25 KB rev-3 page, inside a hard 3 s / 3G Must (NFR-001). The static export mitigates it (the HTML
  shell is CDN-cached and paints before hydration) but does not remove it. **Vite + React scores 3**
  because it ships less framework — which is why it is the named fallback if the measurement fails.
  **Rev 5 adds a second reason Vite would score better, and the reason it is still not chosen (H-C):**
  a Vite SPA emits **no inline bootstrap script**, so `script-src 'self'` is trivially achievable,
  whereas the Next.js App Router static export emits an inline bootstrap **plus per-page
  `self.__next_f.push` RSC payload scripts** with per-build contents, and there is **no Node process
  to mint a nonce**. We handle that with a **committed post-build hashing step** (option (a)) rather
  than by switching framework: switching would satisfy H4's *intent* but not its *letter*, so it
  remains a **named fallback** that would be raised as a **GATE_2 question**, never taken as an
  evaluator decision. Fallback (c) — accepting `script-src 'self' 'unsafe-inline'` as a recorded
  weakening — is the documented outcome if the hashing spike fails.
- **Rev 5 route-shape note (arch F3):** `output: "export"` **cannot build a dynamic segment**
  without `generateStaticParams`, and there is no legitimate build-time list of complaint ids. The
  clerk detail view is therefore **client state inside the non-dynamic `/complaints` route** — which
  also satisfies sec F11 (the complaint number never enters a URL, referrer or `history` entry) — with
  a **committed host rewrite** for `/complaints/*` and a Playwright deep-link spec run against the
  exported build served the way the host serves it.
- **PII = 4 for the static export, 2 for anything with a Node server.** With `output: "export"` no
  server-side process ever touches citizen data; with SSR or a BFF proxy, every complaint record
  passes through a second process that can log it (D5, NFR-008/009). It scores 4 rather than 5
  because the JSON API surface itself is a new leak path (**R15**), mitigated by the public DTO +
  `response_model` + a test.
- **OPS = 4 vs 2.** A static export adds **no production runtime**; a Node service adds a second
  one for an ops owner who does not exist (D3) — and Next.js's patch cadence is faster than the
  API's.
- **SUPPLY = 2 for all Next.js variants.** ~350–450 resolved npm packages where rev 3 had **zero**
  (**R16**). Vite+React scores 3 (materially fewer). This criterion did not exist in rev 3 because
  the answer was trivially 5; H4 makes it the second-largest change in the document.
- **BFF proxy scores 5 on RATE/CSRF-adjacent grounds** (same-origin, `SameSite=Strict` possible) and
  is still rejected: it re-imports the PII and OPS penalties to remove a CSRF complexity that three
  layered controls already handle (`tech-stack.md` § Auth).
- **What is lost, recorded once:** JS-disabled operation. Rev 3 called that "a hard constraint, not a
  preference" (AC-018 + BR-015 + the persona). **H4 removes it by decision** ⇒ Conflict **C7**,
  risk **R17**, and **GATE_2 question 8**. The surviving half — malformed input performs **no
  lookup** — moves entirely into the API and is asserted by a table-scoped query-count test.

**Still explicitly rejected inside H4:** Tailwind or any CSS framework (hand-written CSS is ~4–8 KB
for 6 screens and every KB now counts against C8); a component library; an icon package;
`next/font` (system font stack instead); CDN-hosted scripts or fonts (third-party origin on a page
handling citizen data); analytics/session replay; a client-side data-fetching library
(`fetch` + `AbortController` is ~40 lines and already required by NFR-011).

---

## Layer 2a — Rendering mode (new in rev 4 — the sub-decision inside H4)

| Option | Verdict |
|---|---|
| **Static export: public lookup prerendered + small client island; clerk screens are static shells hydrated client-side, with *no dynamic route segments* (rev 5)** ✅ | **Chosen.** No Node process in production ⇒ $0 hosting, no second runtime to patch (D2/D3), citizen data never enters a second process (D5), and the public HTML shell paints from a CDN edge before any API call (D4). Uses none of Next.js's server features, all of which the requirement set can do without. **Two rev-5 constraints that make it actually buildable and actually safe:** (1) **no `[id]` segment anywhere** — `output: "export"` would demand `generateStaticParams`, and the complaint number must not appear in a URL (arch F3 + sec F11); detail views are client state, with a committed host rewrite for `/complaints/*` mirrored by the CI static server. (2) **inline scripts are hashed post-build** into the host's per-path `script-src`, with an assertion that the deployed policy contains no `unsafe-inline` (H-C). |
| SSR for the clerk screens | Rejected. Would forward the session cookie to a Node server that then holds `name`/`phone` in memory and possibly in logs — a second PII processor for a 6-screen internal UI (D5). |
| ISR / revalidation for the public page | Rejected. There is nothing to cache: a lookup is a per-request POST with a unique key, and caching it would be a privacy defect, not an optimisation. |
| Server actions / route handlers | Rejected. They require a Node server and would create a second write path to the API — exactly the "second un-audited path" concern that removed Django admin in rev 2 (sec F5), in new clothes. |

---

## Layer 3 — Database

**Unchanged from rev 3** (H3/H4 change nothing here). Maximum possible = 100.

| Option | COST(3) | SCALE(2) | OPS(3) | AUDIT(3) | UNIQ(3) | PII(3) | 3G(3) | Weighted |
|---|---|---|---|---|---|---|---|---|
| **PostgreSQL 17, managed by the platform** ✅ | 4 | 5 | 5 | 5 | 5 | 5 | 5 | **97** |
| PostgreSQL 17, self-hosted on the same VPS | 5 | 5 | 2 | 5 | 5 | 5 | 5 | **91** |
| SQLite (WAL) on a persistent volume + Litestream | 5 | 5 | 3 | 4 | 5 | 5 | 5 | **91** |
| MySQL 8 / MariaDB, managed | 4 | 5 | 5 | 5 | 5 | 5 | 5 | **97** |
| Firestore / document store | 2 | 4 | 4 | 2 | 2 | 3 | 4 | **59** |

Notes:
- **SQLite is not rejected for performance** — at under 1 request/second with WAL it is adequate and
  it wins on cost. It loses on **OPS/AUDIT**: a persistent volume (which rules out the native-runtime
  deploy model) and backup verification becoming a human's job. Documented fallback only (Conflict C1).
- **MySQL ties Postgres at 97**, but rev 4 adds a tie-break reason that did not exist in rev 3: the
  limiter statement uses **`RETURNING`**, which MySQL lacks, so the counter would need a second
  round trip. Postgres also has first-class `psycopg` 3 / SQLAlchemy support. Preference plus one
  concrete mechanism, stated honestly.
- **Firestore scores 2 on AUDIT/UNIQ** — multi-row transactional history writes (BR-011) and a global
  unique constraint (FR-013) are what document stores make awkward; per-read pricing fights NFR-006.
- **Free auto-pausing tiers deliberately excluded** (Neon free, Supabase free): cold starts threaten
  NFR-001's 3 s budget.
- **Rev 4 adds one table** to the rev-3 set: **`session`** (server-side sessions, forced by H3 —
  Layer 4). It holds a token *hash*, a user FK and timestamps; no PII, and it is swept
  deterministically like the limiter windows.

---

## Layer 4 — Auth — **rescored in rev 4 (H3 removed `contrib.auth`)**

The rev-3 table compared *auth providers*. That comparison still holds and is kept, but the winning
row no longer exists as a product, so rev 4 splits the layer into the three sub-decisions H3 forced.

### 4.0 Auth provider (rev-3 table, updated winner)

| Option | COST(3) | OPS(3) | PII(3) | AUTH(3) | 3G(3) | SKILL(2) | Weighted |
|---|---|---|---|---|---|---|---|
| `django.contrib.auth` *(rev 3's recommendation — no longer available)* | 5 | 4 | 5 | 5 | 5 | 5 | **82** |
| **Own thin layer on framework-independent primitives** ✅ **(forced by H3)** | 5 | **3** | 5 | 5 | 5 | 5 | **79** |
| Auth0 / Clerk (hosted identity) | 2 | 5 | 2 | 2 | 3 | 4 | **50** |
| Supabase Auth | 3 | 4 | 2 | 2 | 3 | 4 | **50** |
| OAuth / "Sign in with Google" for clerks | 4 | 5 | 3 | 1 | 3 | 4 | **56** |
| Hand-rolled auth **including its own crypto** | 5 | 2 | 4 | 3 | 5 | 2 | **61** |

(Maximum possible = 85.)

Notes:
- **The chosen row scores 3 on OPS, where `contrib.auth` scored 4.** That single point is
  risk **R11**: session lifecycle, CSRF, deny-by-default, `must_change_password`, password policy and
  the production-config gate are ours to maintain and to patch. It keeps **AUTH = 5** because it
  satisfies BR-016/FR-017–019 exactly — better than any SaaS row can.
- **It is emphatically *not* the "hand-rolled auth" row (61).** That row means owning hashing and
  session crypto. We own *glue*: tokens from `secrets`, comparisons via `hmac.compare_digest`,
  hashing by `argon2-cffi`. **No custom crypto** is the line, and it is stated in three places.
- **AUTH is decided by BR-016**, which requires the admin clerk to see a new password **once, on
  screen**, because no email or SMS channel exists in the MVP. Hosted providers are built around
  emailed invite/reset links — hence the 2s. **OAuth scores 1** because NFR-003 specifies "at
  minimum, username + password" and clerks share an office computer.
- **Cost reality check:** ≤6 accounts (A12). Per-MAU pricing is overhead with no benefit, plus a
  third-party processor of clerk PII against NFR-008's spirit.
- **Rev-3 rows now retired:** `django.contrib.admin` as a fifth option (there is no Django admin to
  reject). **Its reasoning survives in new clothes:** FastAPI's **OpenAPI docs are disabled in
  production** and a test asserts `/docs`, `/redoc` and `/openapi.json` all return **404** — the same
  "no unnecessary surface enumerating every route and schema" argument (D5, BR-010).
- **Login-limiter keying is still part of this layer** (sec F7/F16/arch F4/arch F7): the primary
  **blocking** decision is **username+IP**, behind a generous **per-IP ceiling evaluated first that
  short-circuits before any username-keyed row is written**; the username component is **hashed and
  truncated to a fixed width** everywhere it appears (limiter keys and `security_event`); stale
  windows are cleaned on a **deterministic** trigger.
- **The per-account control is a backoff, not a lock (arch F4) — and in rev 4 it is a *response*,
  not a *wait* (sec F23):** it returns **`429` with `Retry-After`** instead of sleeping a request
  thread, because with only 4 threadpool tokens per worker a sleeping thread is a self-DoS. Skipped
  entirely for an IP with a recent successful login for that account. Unlock paths unchanged (wait
  out the window, another admin resets the password, or the operator runs the **`unlock-account`**
  console script — the answer sketch for Q-015).
- **The counter commits independently of the request it counts (arch F3)** — in rev 4 by
  construction: a **dedicated `AUTOCOMMIT` engine**, not the request session. Test that a *failed*
  login still increments.
- **Optional, costed:** TOTP for the admin clerk only (**`pyotp`**, MIT, +1 dependency, ~0.5–1 day,
  $0/mo) — offered to the human (sec F14), not adopted. Rev 3's `django-otp` is retired.

### 4.1 Session mechanism (new in rev 4)

| Option | OPS(3) | PII(3) | AUTH(3) | SUPPLY(2) | Weighted |
|---|---|---|---|---|---|
| **Opaque token cookie + `session` row in Postgres — authenticated rows only (`user_id` NOT NULL, rev 5)** ✅ | 4 | 5 | **5** | 5 | **52** |
| Starlette `SessionMiddleware` (signed cookie, `itsdangerous`) | 5 | 4 | **1** | 4 | **38** |
| JWT access+refresh in cookies | 3 | 4 | 2 | 3 | **33** |
| JWT in `localStorage` | 4 | **2** | 2 | 3 | **30** |

(Maximum possible = 55.)
- **AUTH = 1 for the signed cookie** is the decisive score: rev 3 requires **revocation on password
  reset**, **logout everywhere**, an **idle timeout** and **browser-close expiry** (sec F20, BR-016).
  A signed cookie is a bearer assertion that cannot be revoked; idle timeout could only be advisory.
  It would save one table and ~40 lines and it cannot meet the requirement. It also keeps
  `itsdangerous` out of the dependency list entirely.
- **JWT in `localStorage` scores 2 on PII/exposure**: after H4 there are ~400 npm packages on that
  page (**R16**); a credential readable by page scripts is one malicious transitive dependency away
  from **exfiltration**, i.e. a *durable* token an attacker can replay from their own machine after
  the clerk goes home. **Corrected in rev 5 (H-B/sec F2):** the `httpOnly` cookie is better because
  the token cannot be *taken*, **not** because the npm tree cannot *act*. A malicious package on our
  own origin can still issue credentialed requests from the page with the clerk's full capability, so
  the cookie buys "no offline replay, and revocation actually works", bounded further by the idle
  window, CSP `connect-src` and response minimisation. That is a real 3-point gap, not a 4-point one,
  and rev 4 overstated it in prose while scoring it correctly.
- The chosen row loses one OPS point for the sweep of expired rows — the same deterministic cleanup
  mechanism the limiter already needs, so no new machinery. **Rev 5 removes the anonymous rows
  entirely (H-A)**, which makes this the *only* sweep and removes an unauthenticated write path; the
  anonymous CSRF token is now a stateless HMAC (Layer 4.3) and touches no table.

### 4.2 Password hashing (new in rev 4)

| Option | Verdict |
|---|---|
| **`argon2-cffi`, Argon2id, `m=9216 KiB, t=4, p=1`** ✅ | Chosen. MIT, Hynek Schlawack, top-tier PyPI, and the same library Django's own Argon2 backend used. Provides `hash()`/`verify()`/`check_needs_rehash()` and a self-describing encoded string, so **we write no hash format, no salt handling and no constant-time compare**. `m=9216` rather than OWASP's first-listed `m=19456` **because of the 512 MB instance**: 8 concurrent hashes × 19 MiB would peak ~450 MB. It is still an OWASP-listed configuration, and the reason is recorded rather than the parameters silently weakened. |
| Stdlib `hashlib.pbkdf2_hmac`, 600k iterations | Rejected narrowly. Zero dependencies, OWASP-acceptable, and what rev 3 used *via Django*. Without Django we would own the encoded format, salt generation, the upgrade-on-login path and the constant-time compare (~30 lines of crypto-adjacent code). Documented fallback if the C extension ever causes a platform build problem. |
| `passlib[bcrypt]` | **Rejected on maintenance, checked 2026-09.** Last release **1.7.4 (October 2020)**; effectively unmaintained, and its `crypt`-based backends target a stdlib module **removed in Python 3.13** (PEP 594) — our interpreter. Fails dependency-strategy.md §1 criterion 4 outright. |
| `pwdlib[argon2]` | Rejected. A young 0.x wrapper over `argon2-cffi` with a small maintainer base; we can use the wrapped library directly (D3). |

### 4.3 CSRF for a cookie-authenticated JSON API (new in rev 4 — H4)

| Option | Verdict |
|---|---|
| **Three layered controls: `SameSite=Lax` cookie + `Origin` allow-list check + `X-CSRF-Token` — session-bound when authenticated, *stateless* `hmac_sha256(SECRET_KEY, __Host-csrfseed)` when not** ✅ **(rev 5 — H-A)** | **Chosen, ~40 lines.** The rev-5 change is the unauthenticated half: rev 4 minted the public token from a **`session` row created by an unauthenticated, unlimited `GET /api/session`**, which is an anonymous write primitive in front of a **fail-closed** limiter — a flood grew the table and could 503 the public lookup it was protecting. The stateless variant keeps all three layers with **zero SQL before authentication**: the seed lives in an `httpOnly` `__Host-csrfseed` cookie, the token is its HMAC under a named server key, verification is a `compare_digest`, and there is nothing to sweep, nothing to grow and no connection to consume. **No cookie carries the token** in either path (both cookies are `httpOnly`), which satisfies sec F26 and removes rev 3's deliberate `CSRF_COOKIE_HTTPONLY=False`. Applies to **every unsafe method on every route, with no exemption decorator and no exempt-path list in the codebase**, including the **public lookup POST**. **Tests:** 403 without a token and 403 on a bad/missing `Origin` on **both** an authenticated write and the public lookup; a token minted under a different key or replayed with a different seed is rejected; the **rotated token is returned in the login/password-change/logout response** (arch F10); and **assertion 17** — an anonymous burst from one IP leaves the `session` table unchanged and the public lookup at 200. |
| **Tiered: `Origin` allow-list + `SameSite=Lax` only on the public lookup POST; session-bound token only on authenticated writes** (evaluated in rev 5 — arch F9) | **Evaluated and rejected, but narrowly, and the reason is worth recording.** *For it:* it deletes the anonymous token entirely, so the public route needs **no cookie at all** (retiring **R13**) and **no `GET /api/session` round trip inside NFR-001's budget** (helping **C8**) — genuinely attractive on the two drivers that are most under pressure (D4, and the "citizen who blocks cookies" case). *Against it, decisively:* the public lookup POST is exactly where a **cross-site abuse case is concrete rather than theoretical** — an attacker page can drive complaint-number guessing through unwitting visitors' browsers, spreading the attempts across *their* IP addresses and defeating the per-IP limiter (D8/BR-010), and `SameSite=Lax` is a **browser behaviour we cannot assert at the API boundary** while the token requirement **forces a CORS preflight** the allow-list fails. Removing the token would leave the public POST defended only by controls we cannot test server-side. Since H-A made the token **free of state and of database cost**, the argument for dropping it lost its main benefit: what remains is one cached round trip, which **C8 now measures as part of time-to-result and issues in parallel with hydration**. Rejected on that basis, not by habit. |
| Double-submit cookie (token in a readable cookie + mirrored in a header) | Rejected. It reintroduces a **script-readable cookie** — precisely what sec F26 asked us to avoid, and after H-B a readable credential-adjacent value is exactly what the npm tree should not be handed — for no gain, since the authenticated path already has a session row to bind to and the anonymous path has an HMAC. |
| Same-origin via a BFF proxy + `SameSite=Strict`, no token | Rejected with Layer 2a: strongest CSRF posture, but it needs a Node server that would then see every citizen record (D5), cost +$7/mo (D2) and add a runtime to patch (D3). |
| Nothing (rely on `SameSite` alone) | Rejected. `SameSite=Lax` is a browser behaviour, not an assertion we can test at the API boundary, and it does not cover a same-site subdomain compromise. Defence in depth is the point. |

---

## Layer 5 — Rate limiting (NFR-005 / AC-011)

**Ranking unchanged from rev 2/3.** One new option is evaluated and rejected because the framework
change makes it the obvious thing for someone to reach for.

| Option | COST(3) | OPS(3) | RATE(2) | SCALE(2) | Weighted |
|---|---|---|---|---|---|
| **In-repo limiter over a Postgres counter table (atomic `INSERT … ON CONFLICT DO UPDATE … RETURNING`)** ✅ | 5 | 4 | 5 | 4 | **45** |
| `slowapi` / `fastapi-limiter` (**new in rev 4**) | 5 | 4 | **1–2** | 4 | **37–39** |
| Single worker + an in-process counter | 5 | 4 | **2** | 3 | **37** |
| Managed Redis / Valkey (Render Key Value, Upstash) | 2 | 3 | 5 | 5 | **35** |
| Cloudflare free edge rate-limit rule | 5 | 4 | 3 | 5 | **43** |

Notes:
- **`slowapi`/`fastapi-limiter` score 1–2 on RATE for exactly the rev-2 reason `django-ratelimit` was
  dropped:** `slowapi` wraps `limits` and defaults to **in-memory** storage (per-worker, wrong) or
  Redis (which is option 4 with its cost); `fastapi-limiter` **requires** Redis. Both are 0.x
  packages with small maintainer bases that would own a security control (D3,
  dependency-strategy.md §1 criterion 4). Checked, not assumed — the FastAPI-ecosystem repeat of a
  finding this project already paid for once.
- **The Postgres counter scores 5 because the increment is one statement**, atomic under any number
  of processes/threads/connections, with no eviction policy to defeat, provable in CI against real
  Postgres. It costs 1 OPS point because ~60 lines are ours (R2). In rev 4 it also gains a
  structural improvement: it runs on a **dedicated `AUTOCOMMIT` engine**, so arch F3's "commits
  independently of the request" is enforced by construction rather than by remembering not to nest a
  transaction.
- **Redis is still correct and still rejected** (COST 2): a third billable component at ~$10/mo,
  ~70% on top of the hosting bill, for a counter one SQL statement handles. Revisit above ~50 rps.
- **Cloudflare scores 3** not because it is weak but because it moves a Must-verifiable behaviour
  outside the application and the test suite. Welcome later as defence in depth.
- **Evidence bar for AC-011:** >20 **concurrent** requests from one IP, via `concurrent.futures` +
  `httpx` against the in-repo `live_server` fixture. A sequential loop passes even against a broken
  counter and remains unacceptable evidence.
- **Client-IP derivation is part of this layer's correctness** (sec F2/F17): the five-step rule
  (right-most untrusted hop, explicit `TRUSTED_PROXY_HOPS`, IPv6 → /64, fail closed on a missing
  header), three negative tests, **a positive multi-hop test**, a **startup check** that the hop
  count is explicitly set (now inside the in-repo **`selfcheck`**, since `django.core.checks` is
  gone), and a **live /release verification** from a known source address with the temporary log line
  removed afterwards. Rev 4 also names the uvicorn equivalents:
  **`--proxy-headers --forwarded-allow-ips`** for scheme/redirect correctness, while the *limiter's*
  client identity stays our own rule.
- **Window cleanup is deterministic, not probabilistic** (sec F16): a bounded, `LIMIT`ed delete on
  window rollover for the key being touched (or an exact every-Nth-call counter), no cron, no job
  runner. The `session` table's **expired (authenticated) rows** use the same trigger — **rev 5 has no
  anonymous rows to sweep at all (H-A)**, because the anonymous CSRF token became a stateless HMAC.
- Known limitation of all per-IP options: carrier NAT and shared kiosks (R3, Conflict C4). Feed back
  into Q-013. Mitigated in depth by the complaint-number entropy floor (sec F11).

---

## Layer 6 — Background jobs

| Option | Verdict |
|---|---|
| **None** ✅ | Nothing in the MVP is asynchronous. Notifications are Future scope; there are no exports, no attachment processing, and **NFR-010 forbids automatic deletion**, so there is no retention job either. Limiter-window and expired-session cleanup are inline, deterministic and bounded. |
| Celery / RQ + Redis broker | Rejected — two extra components and a broker for zero async work. Textbook over-engineering at 1–5 clerks. |
| Platform scheduled job (**Fly scheduled machine** in rev 5.1; Render Cron in rev 5) | Rejected as a *requirement*. **ENABLED in rev 5.1 as a ~$0–1/mo option** for the **monthly, encrypted** off-platform `pg_dump` described in `tech-stack.md` § Database: condition (a) is met — **GATE_2 answer Q6, "I hold the backup key"**, names the key holder — and condition (b), **a named destination with its own scoped credential and an automatic lifecycle/expiry rule, is TBD (human to name at /release)**. Until then the dump does not run, but it is **no longer dropped**: only the destination is outstanding, so sec F18's "either is missing ⇒ drop it" no longer bites. Mechanism on Fly is one **scheduled machine** running the same digest-pinned image — still **no broker, no queue, no job runner**. **There is no manual-download substitute** (arch F5) — that would put a plaintext full citizen-PII export on someone's laptop. |

If SMS notifications are later pulled out of Future scope, the first step is a small
**console-script entry point** driven by a platform cron — still no broker.

---

## Layer 7 — File storage

| Option | Verdict |
|---|---|
| **None; the API serves no static files at all, and frontend assets are the Next.js build output on the static host's CDN** ✅ (rev 4: WhiteNoise is **retired** — it is WSGI-first and there is nothing left for it to serve) | There are no user uploads. Photo/attachment upload was explicitly pushed back in the Scope challenges section and lives in Future scope. Frontend assets are ~120–150 KB total, content-hashed, immutable-cached at the edge. |
| S3 / Cloudflare R2 (+ CDN) | Rejected — a bucket, credentials and a cache-invalidation concern for ~150 KB of build output, with no gain over the static host's own CDN. |
| Serving the exported frontend from the FastAPI process (Starlette `StaticFiles`) | Rejected — it would put the 3 s / 3G budget behind a single 512 MB Singapore instance instead of a CDN edge (C8 makes every millisecond count), and spend worker threads on file serving. Since H4 already accepted a second deployable, this buys nothing. |

Pulling attachments forward from Future scope reopens this layer (object storage, MIME/size
validation, and a fresh look at the NFR-001 payload budget) — treat it as a GATE_2 change.

---

## Layer 8 — Hosting & deployment

### 8.0 API + database hosting (rev-3 table, unchanged; maximum possible = 85)

| Option | COST(3) | OPS(3) | SCALE(2) | 3G/latency(3) | PII/residency(3) | AUDIT/backups(3) | Weighted |
|---|---|---|---|---|---|---|---|
| Render Starter — *native Python runtime* + Render Postgres (Singapore) — *rev 5's choice; **now the rejected default**, because it has **no India region** and Q1 requires one* | 4 | **5** | 5 | 4 | **1 — fails a stated requirement** | 5 | **76** *(score kept; the requirement, not the score, disqualifies it)* |
| Render Starter — *Docker image* + Render Postgres (rev 1's choice — **withdrawn**) | 4 | **3** | 5 | 4 | 4 | 5 | **70** |
| **Fly.io — Machines + Managed Postgres (`bom`, Mumbai)** ✅ **(SELECTED at GATE_2 by answer Q1)** | 4 | 4 | 5 | 5 | 5 | 4 | **76** |
| Single VPS (Hetzner CX22 / DigitalOcean BLR1) + Docker Compose | 5 | 2 | 5 | 5 | 5 | 2 | **67** |
| Railway (Hobby, usage-based, Singapore) | 4 | 5 | 5 | 4 | 4 | 4 | **73** |
| AWS ap-south-1 (App Runner/ECS + RDS) | 2 | 2 | 5 | 5 | 5 | 5 | **67** |
| Render **free** web tier + free Postgres | 5 | 5 | 3 | **1** | 4 | **2** | **57** |

Notes:
- **Docker re-scored from 5 to 3 on OPS and withdrawn (arch F2).** A Dockerfile makes *us* the owner
  of the base OS and its CVEs — the responsibility OPS exists to push onto the platform. Render's
  native Python runtime patches the underlying image itself. A Dockerfile enters the repo **only** if
  the Fly.io residency swap triggers, and that swap re-imports the patching obligation.
- **Render and Fly tie at 76, and rev 5.1 breaks the tie the other way — by requirement, not by
  score.** Rev 5 broke it on **OPS** (Render's native runtime, one dashboard) because residency was
  an open question with a Singapore default. **GATE_2 answer Q1 — "India — use the Mumbai region" —
  closes that question**, and Render has no India region, so it is disqualified by a stated
  requirement rather than out-scored. Fly wins latency and residency; Render's operational
  simplicity was and remains genuinely better, which is why `tech-stack.md` § Hosting lists it as the
  **documented rejected default** rather than pretending Fly was always superior. **The swap's cost
  is a Dockerfile** (`python:3.13-slim`, digest-pinned, scheduled rebuild) — acceptable only because
  **GATE_2 answer Q6 names the owner** ("I own patching and backups"), which is exactly the condition
  arch F2 attached to any image entering the repo. **Docker's OPS = 3 therefore still stands as a
  score**; what changed is that the obligation now has a name attached to it.
- **Frontend hosting stays on the free Render Static Site (8.1), so the launch topology is two
  vendors, one registrable domain** (`www.<domain>.in` → Render, `api.<domain>.in` → Fly). The
  assumption that makes this compatible with Q1 is stated in `tech-stack.md` **A-T1a**: the exported
  bundle contains **no citizen data**.
- **Render free web tier scores 1 on latency and 2 on backups (cost F3):** free web services spin
  down, so the first citizen of the morning pays a cold start out of NFR-001's budget. **Note the
  asymmetry rev 4 introduces:** the *static site's* free tier has **no such objection**, because a
  CDN asset never spins down. Free is rejected for the server and accepted for the CDN, for a stated
  reason rather than by habit.
- **No paid support tier is assumed on any option (cost F4).**

### 8.1 Frontend hosting (new in rev 4 — H4)

| Option | Cost | Verdict |
|---|---|---|
| **Render Static Site (free) serving the `output: "export"` build** ✅ **(kept in rev 5.1)** | **$0** | **Chosen.** Free build minutes, global CDN, TLS, custom domains, and **free PR preview URLs** — which give the frontend half of the staging environment rev 3 could not afford. No production Node runtime. **Rev 5.1 correction to the rationale:** the "same vendor, same dashboard as the API and database" argument **no longer applies** — Q1 moved the API and database to Fly, so this is now a **second vendor**. It is still chosen because it is free, CDN-backed and already configured, and because the bundle holds **no citizen data** (A-T1a); the honest cost is one extra account and dashboard for the named owner (Q6). |
| **Serve `out/` from a Fly static Machine in `bom`** | **+$2–5/mo** | **The named alternative if the residency rule is later read to cover static assets too.** Zero code change (same `out/`), one vendor again, one more machine to patch. Raise it as a decision with the human; do not adopt it silently. |
| Vercel Hobby + API on Render | $0 *or* ~$20/mo | Rejected. **Hobby is licensed for non-commercial use**; a government-funded panchayat deployment is not obviously inside those terms, and the honest reading pushes it to **Pro (~$20/mo per member)** — more than the entire rest of the bill (D2). Also a second vendor, dashboard and account for nobody to own (D3), and its value (SSR, edge functions, ISR) is exactly what the static export does not use. **Recorded so nobody adopts it for the free tier without reading the terms.** |
| Both on Render as web services (`next start`) | +$7/mo ⇒ **≈$21–23/mo** | Rejected as the default, **kept as a costed option** (GATE_2 question 2) for the day SSR/ISR/middleware is genuinely needed. Re-imports a second production runtime and routes citizen data through it (D5). |
| Cloudflare Pages / GitHub Pages / Netlify free | $0 | Not rejected on merit — functionally equivalent for a static export. Rejected on **vendor count**: a third account and dashboard for an unnamed ops owner, to save nothing. Fallback if the Render static tier ever changes. |
| Serving the build from the FastAPI service | $0 | Rejected — see Layer 7. |

### 8.2 Deploy model (arch F5, sec F9) — one model, now with two doors

| Option | Verdict |
|---|---|
| **Auto-deploy OFF on *both* deployables; a human promotes a specific commit for each — API first, then the static site; `alembic upgrade head` as the API release command** ✅ **(rev 5.1: the API door is now `fly deploy` run by the human from the reviewed, CI-green commit, with `release_command = "uv run alembic upgrade head"` in `fly.toml`; no Fly token exists in CI, and the CI-built-image variant was considered and rejected because it would need a registry-push credential there)** | Chosen. The only option compatible with **CLAUDE.md** ("no production deploy — the human does those") *and* with R1's "deploy outside office hours". The deploy aborts if the migration fails, before traffic shifts. Rollback = promote the previous build (reverse order). **New in rev 4:** turning auto-deploy off on the *static site* is an explicit /release checklist item — static hosts default it on, and "it's only a frontend" is exactly how an unreviewed production change happens. **Ordering is a constraint, not a preference (R14):** the static bundle in a citizen's cache can lag the API, so **API changes must be additive** — a new field is fine, a rename or removal is a two-step deploy. One post-deploy E2E smoke spec, run against production by the human, is the evidence that the two halves match. **Consequence restated (arch F1): an auto-merged Dependabot security PR reaches `main` but *not* production until a human promotes — and now there are two things to promote.** |
| Deploy on push to `main` | **Withdrawn — it contradicted a stated constraint.** |
| GitHub Actions deploy job with a platform API key | Rejected — same constraint conflict, plus a production deploy credential in CI for no gain over a dashboard click. |

Supporting controls: third-party Actions **pinned by full commit SHA**; workflow-level
`permissions: contents: read`; no `pull_request_target`; **no secrets exposed to fork-PR workflows**;
CI additionally runs `alembic upgrade head` from the previous revision against a Postgres service
container, plus `alembic check` for drift.

### 8.3 Branch protection — one rule, stated identically in all three documents

| Option | Verdict |
|---|---|
| **Require a pull request before merging + green required checks + linear history + no force-push + no deletion; *no* required human review** ✅ | **Chosen (option b, now with the arch F3 / sec F25 advisories folded in).** Rev 3 took option (b) but left direct pushes to `main` possible; adding **"require a PR"** closes that at zero cost to the bot, since Dependabot opens PRs anyway. **No required human review**, because a bot cannot satisfy one and a 1–5-person pilot with an unknown team (D11) and no ops owner (D3) cannot supply a second reviewer on demand. **Auto-merge is narrowed (sec F25): patch/minor version bumps of packages already present in `uv.lock`/`package-lock.json` only — never a package new to the lockfile, never a major.** Two-eyes is retained where it earns its keep: **a new dependency addition in either ecosystem** (dependency-strategy.md §6). |
| Required review **plus** a ruleset bypass for Dependabot | Workable (option a) but rejected: it needs someone to configure and *maintain* a bypass list, and an unaudited bypass is weaker than an honest "no required review". |
| Required review with no exemption | **Withdrawn — internally contradictory.** Security patches would never auto-merge. |

### 8.4 Environments

| Option | Verdict |
|---|---|
| **No staging; four compensating controls** ✅ | Chosen and stated rather than left silent (arch F5): (1) CI runs the full suite **and `alembic upgrade head` from the previous revision** against real Postgres, plus `alembic check`; (2) migrations are **additive-only / forward-compatible**, and rev 4 extends the same rule to **API response shapes** (R14); (3) rollback = promote the previous build; (4) **new in rev 4 — the static host's free PR previews give every frontend change a real deployed environment**, with preview origins deliberately absent from the API's CORS allow-list so they touch no production data. |
| Staging web service + cheap DB | **Costed at +$7–13/mo** and offered, not assumed. It now buys an API/DB rehearsal only, since the frontend previews are free. |
| Deploy straight to production with no compensating controls | Rejected — not acceptable for a Must-priority audit trail. |

- **VPS scores 2 on OPS and 2 on AUDIT** — cheapest by ~$8/mo, but kernel/TLS/Postgres patching and
  *verified* backups fall on a human who is not named anywhere in the requirements. Fallback only,
  conditional on assigning an owner.
- **Railway** is a close second; usage-based billing scored down for a fixed government budget line.
- **AWS scores 2/2 on cost and ops**: correct residency, best latency, but IAM/VPC/RDS administration
  is disproportionate to 1–5 clerks and RDS alone exceeds the whole budget.
- Latency sanity check for NFR-001: from India the 3G mobile leg (~100–200 ms RTT) dominates;
  Singapore added roughly 60–80 ms per round trip. **Rev 5.1: that penalty is gone** — the API and
  database are now in **`bom` (Mumbai)**, which is a real, if modest, gain for **C8**'s contested
  time-to-result budget (it removes ~60–80 ms from each of the session and lookup round trips).
  **Rev 4 caveat still stands:** the static HTML comes from a CDN edge (better than rev 3), but the
  ~120 KB JS bundle must arrive before the form works (worse than rev 3). To be **measured** at
  /build and /test-app (AC-010), not assumed — the region change reduces the risk, it does not
  retire it.

---

## Layer 9 — Tooling — **rewritten in rev 4 (two toolchains)**

### Package managers

| Option | Reproducibility | Speed / build time | Boring-ness | Verdict |
|---|---|---|---|---|
| **uv (`pyproject.toml` + committed `uv.lock`)** ✅ | 5 | 5 | 3 | Chosen — one tool for env/resolve/lock/run; standard `pyproject.toml` keeps the exit cheap. Youngest tool in the stack (R4). |
| pip + pip-tools (hashed `requirements.txt`) | 5 | 3 | 5 | The safest fallback; ~1 hour to switch. |
| Poetry | 4 | 2 | 4 | Rejected — slower, heavier, no advantage here. |
| **npm (`package.json` exact versions + committed `package-lock.json`, `npm ci`)** ✅ | 5 | 3 | 5 | Chosen — bundled with Node, nothing extra to install on the build host or in CI (D3/D11); `npm audit` and Dependabot work natively. |
| pnpm | 5 | 5 | 3 | Rejected on tool count, not merit: genuinely faster and disk-efficient, and better for monorepos — none of which applies to one small app. |
| yarn / bun | 4–5 | 4–5 | 3–2 | Rejected — same argument; bun is young (D3). |

### Test frameworks

| Option | Verdict |
|---|---|
| **pytest + `httpx` (`TestClient`/`AsyncClient`) against real Postgres** ✅ | Chosen. Running tests on Postgres (never SQLite) is what makes AC-003's 20-**parallel**-submission uniqueness test, AC-014's concurrent-history test and **AC-011's parallel rate-limit test** meaningful — the `ON CONFLICT … RETURNING` counter has no SQLite equivalent worth testing. **`pytest-django` is dropped and not replaced:** ~40 lines of in-repo fixtures (engine, session, transaction rollback) plus a **~25-line `live_server` fixture** (uvicorn in a thread) and a **~15-line query-counter fixture** (`before_cursor_execute`) cover everything it provided. The query counter asserts **which tables were touched**, which is *stronger* than `django_assert_num_queries`' count — see AC-018 below. |
| **Vitest + `@testing-library/react` + `jsdom`** ✅ | Chosen for frontend component tests: the lookup island's format check and its error/timeout rendering, the login form, clerk list rendering against a mocked API. Native to the Vite toolchain Next.js already uses. |
| **Playwright for Python, 4–6 specs** ✅ | Chosen, and it now drives the **real exported frontend against the real API**: AC-001 login; AC-002/NFR-011 in-flight indicator **and the 10 s `AbortController` timeout against a stubbed slow response**; AC-004 transition rejection; AC-006/AC-007 public lookup; AC-018's exact message. **Kept on the Python side deliberately** — one browser install, one E2E runner. |
| Jest | Rejected — slower, more configuration, no Vite integration. |
| Playwright for Node / Cypress | Rejected — a **second** E2E runner and browser install when we already have one. |
| `unittest` alone | Rejected — clumsier fixtures, less machine-readable output for the org's QA agents. |
| Selenium | Rejected — slower and flakier for the same specs. |
| k6 / Locust | Rejected — a load platform for a 20-request concurrency check; `concurrent.futures` suffices. |

**AC-018 note (arch F9, adjusted in rev 4):** the contract is **not** "no network request", and it is
**not** "zero queries" either — the session/CSRF middleware legitimately reads the `session` table
and the limiter legitimately increments before validation runs. It is: **no statement touching the
`complaint` table executes** for blank/whitespace/malformed input (asserted by table name), and the
response carries exactly "Enter a valid complaint number." Pydantic makes this structural — the
handler body never runs. The Playwright assertion is the secondary, client-side half.
**The rev-3 "same page with JS disabled" spec is deleted** — H4 removed that capability (C7/R17).

### Lint / format / typecheck

| Option | Verdict |
|---|---|
| **Ruff (`E,F,I,B,UP,S`)** ✅ | One dependency replaces flake8 + black + isort + bandit; `S` (flake8-bandit) provides security linting. **The `DJ` rules are removed** — there is no Django. |
| flake8 + black + isort + bandit | Rejected — four dependencies and four configs for the same result. |
| **Biome (`@biomejs/biome`)** ✅ | Chosen for the frontend: **one** dev dependency replaces ESLint + Prettier + `eslint-config-next` + plugins (4+ packages, 2 configs), mirroring the Ruff decision. MIT, actively maintained, Rust. **Trade-off stated:** no Next.js-specific rules, so mistakes `eslint-config-next` would catch are not caught — accepted at ~6 screens with no images and a static export. |
| ESLint + Prettier (+ `eslint-config-next`) | Rejected on package count and config surface; would be the right call if the frontend grew substantially. |
| **mypy (non-strict, app package only)** ✅ | Kept, with a *better* driver than rev 3 had: **D11** plus the fact that FastAPI, Pydantic v2 and SQLAlchemy 2.x are **fully typed**, so **`django-stubs` is dropped** — one fewer dev dependency and materially better inference than Django ever gave. If it costs time in /build, drop it and mark the slot "not used". |
| **`tsc --noEmit`** ✅ | Chosen — free (TypeScript is already present). **Rev 5 (arch F7) makes the "typed contract" real instead of conditional:** rev 4 said the OpenAPI schema *could* generate client types, but nothing generated them, so the claim rested on nothing. |
| **`openapi-typescript` (npm dev dependency)** ✅ **(new in rev 5 — arch F7)** | **Chosen.** MIT, mainstream, dev-only, no runtime footprint. The API job dumps the OpenAPI schema in CI (docs stay unserved in production), `openapi-typescript` generates `api-types.ts`, the file is **committed** (so a reviewer sees contract changes in the diff), and **CI fails if a fresh generation differs from the committed copy** — which is what makes a field rename break CI rather than production and lets **R14** rest on more than "we promised to be additive". Cost: one dev dependency inside the ≤12 budget (10 used). *Alternative considered:* hand-written response types — rejected, they drift silently, which is the exact failure this control exists to catch. *Alternative considered:* delete the claim and rely only on additive-only changes plus the post-deploy smoke spec — a legitimate cheaper option, rejected because the generator costs one dev dependency and removes a whole class of skew. |
| **Biome rule groups, stated explicitly** ✅ **(rev 5 — sec F8)** | `biome.json` enables the **`security`** and **`correctness`** rule groups by name rather than inheriting whatever a given Biome release considers recommended, so `dangerouslySetInnerHTML` and unsafe `href` construction are caught by the linter and not only by review. Backed by a **grep assertion** (no `dangerouslySetInnerHTML`, `innerHTML`, `eval(`, `new Function(`, inline `style=`/`style={`) because a lint rule can be disabled inline and a grep cannot. **React's JSX escaping is named as the primary XSS control**; the CSP is the second layer. |
| Pyright | Rejected — less objectionable now that Node exists, but two type checkers is one too many. |
| Astral `ty` | Rejected for now — too new to hang a CI gate on. |
| No typechecking | Rejected — the org requires evidence-backed quality claims. |

### Migrations

| Option | Verdict |
|---|---|
| **Alembic, committed, applied as the API release command; `alembic check` in CI** ✅ | Chosen — SQLAlchemy's native tool, reviewable diffs (important for the append-only audit tables), and `alembic check` replaces `makemigrations --check` as the drift gate. `--autogenerate` output is **always human-reviewed** because it misses some constraint changes. |
| Hand-written SQL + a runner | Rejected — loses model/schema coherence (Layer 1a). |
| `yoyo` / `sqlalchemy-migrate` | Rejected — smaller and less maintained (D3). |
| Django migrations | Not applicable — no Django. |
| Seeding the first admin via a data migration | **Rejected on security grounds** — it would put a credential in version control. FR-015/AC-019 uses an **idempotent `bootstrap-admin` console script that prompts interactively on stdin** and refuses non-interactive use without an explicit `--from-env` flag, which then forces `must_change_password=True` and a /release evidence item for deleting the variable. |

### Production-config gate

| Option | Verdict |
|---|---|
| **An in-repo `selfcheck` console script, also called on app startup** ✅ | Chosen — the explicit replacement for `manage.py check --deploy`. Fails startup in production and fails CI when run with production-shaped env vars. Checks: secret key present and ≥32 bytes, debug off, **`TRUSTED_PROXY_HOPS` explicitly set**, `sslmode=require` in the DSN, secure-cookie flag on, `TrustedHostMiddleware` non-empty and free of `*`, CORS not `*`-with-credentials, OpenAPI docs disabled. |
| Rely on code review | Rejected — the whole point of the rev-3 sec F13/F17 findings is that production settings must be **asserted**, not intended. |

### CI

| Option | Verdict |
|---|---|
| **GitHub Actions — two jobs plus an E2E job** ✅ | Repo is already git/GitHub; free at this size. *API:* `ruff check` + `ruff format --check` → `mypy <app package>` → `pytest` (Postgres service) → **`alembic upgrade head` from the previous revision** + **`alembic check`** → `pip-audit` → **`selfcheck`**. *Frontend:* **`npm ci --ignore-scripts`** → `biome ci` → `tsc --noEmit` → **`openapi-typescript` regenerated from the API job's schema dump and compared with the committed `api-types.ts` (fails if stale — arch F7)** → `vitest run` → `next build` **with a first-load-JS size gate on the public route (C8)** → **the CSP inline-script hashing step (H-C)** → `npm audit --audit-level=high` → **`npm audit signatures` (sec F7)**. *E2E:* exported frontend + `live_server` + Playwright, on PRs to `main` and before a release — **and the CI static server applies the same fallback-rewrite/cache rules as the host, from the same committed file (sec F9)**, so the deep-link (arch F3) and stale-chunk (arch F8) specs test production behaviour. Monthly scheduled re-audit of **both** ecosystems. Hardened per sec F9: actions SHA-pinned, `permissions: contents: read`, no secrets to fork PRs, **no deploy job at all**. Dependabot on **`pip`/`uv` and `npm`**, security PRs auto-merging on green CI **only for patch/minor bumps of packages already in the lockfiles** (sec F25) — which requires **no required human review** on `main` (arch F2) and still leaves the **two human promotion steps** before production is patched (arch F1). |
| No CI | Rejected — every "passes/secure" claim in this org must cite evidence. |
| Self-hosted runner | Rejected — another machine to patch. |

---

## Layer 10 — Observability

**Unchanged from rev 3.** Maximum possible = 55.

| Option | COST(3) | OPS(3) | PII(3) | Fits NFR-007(2) | Weighted |
|---|---|---|---|---|---|
| **Platform logs (stdout) + free uptime pinger on a DB-checking `/healthz` + the append-only `security_event` table** ✅ | 5 | 5 | 5 | **4** | **53** |
| Sentry free tier, hardened (rev 1's choice — **withdrawn**) | 5 | **4** | **3** | 5 | **46** |
| Sentry as configured in rev 1 (`send_default_pii=False` + a field scrubber only) | 5 | 4 | **2** | 5 | **43** |
| Self-hosted Grafana/Loki/Prometheus | 2 | 1 | 5 | 5 | **34** |

Notes:
- **Rev 1's Sentry configuration scores 2 on PII, not 4.** `send_default_pii=False` plus a
  `before_send` scrubber does **not** stop **local-variable capture** — a traceback frame holding a
  request model or an ORM instance ships the citizen's name and phone to a third party. Even hardened
  (`include_local_variables=False`, `max_request_body_size="never"`, an explicit deny-list, a pinned
  data region) it scores 3, because the residual risk is a framework internal capturing something we
  did not anticipate (D5).
- **Hardened Sentry also loses an OPS point**: an account, a DSN, a quota and a data-region setting
  that nobody owns after launch (D3).
- **Platform-logs-only gains a point on NFR-007 (2 → 4)** because `/healthz` executes `SELECT 1` with
  a short statement timeout, so the pinger detects the outage that actually matters. Still 4, not 5:
  there is no proactive alert for a 500 on an unpinged page.
- **Decision: Sentry stays dropped at launch.** The hardened recipe is recorded in `tech-stack.md`
  as **pre-approved the moment GATE_2 question 6 names an ops owner** ($0, ~2 hours).
- **Rev 4 note:** H4 adds a *second* place errors can occur (the browser bundle). We deliberately add
  **no** frontend error tracker and **no** RUM/analytics — same PII reasoning (D5), and it would be a
  third-party script on a page handling citizen data. A frontend exception is diagnosed the same way
  a 500 is: a clerk or citizen phones the office (R7), and the API's logs plus `security_event` hold
  the server side.

---

## Layer 11 — AI / LLM

| Option | Verdict |
|---|---|
| **No AI/LLM anywhere in the MVP** ✅ | All 20 FRs are deterministic CRUD, validation, role checks and exact-match retrieval. **BR-004 explicitly forbids** partial matches, wildcards and "did you mean" suggestions on the public lookup — the one plausible LLM use case is ruled out by a business rule. **Unchanged by H3 and H4**; neither decision creates or removes an AI use case. |
| LLM auto-categorisation of complaint text | Rejected — Q-008's accepted default is free-text only, no category field; categorisation and routing are Future scope. |
| LLM-assisted search over complaints | Rejected — FR-007 needs status filtering and exact-number search; NFR-004/BR-010 actively forbid broad retrieval surfaces. |
| LLM translation for a multi-language UI | Rejected for MVP — Q-004's default is English only. If it changes, **`next-intl`/`react-i18next` with human translations** (the H4-era equivalent of Django i18n) is cheaper, deterministic and testable. |
| Vector database / embeddings | Rejected — no semantic search requirement exists; would add a service, a cost and a PII copy. |
| An AI SDK in the **frontend** (new surface after H4) | Rejected explicitly, because H4 creates a place someone could add one: no AI npm package, no client-side model, no "AI-powered" widget. Also a hard "out" in dependency-strategy.md §7. |

Cross-cutting reasons to say no: per-request cost against NFR-006 (total budget ~$14/mo), an
inference hop inside NFR-001's 3 s / 3G budget (which C8 has already made tight), a new third-party
processor of citizen complaint text against NFR-008/NFR-009, and no one to own prompt regressions or
model deprecations. **Revisit only if the human pulls categorisation/routing or multi-language out of
Future scope — and even then, try the deterministic option first.**

---

## Cross-layer coherence check

| Requirement cluster | How the chosen stack satisfies it | Where it is verified |
|---|---|---|
| FR-013 / BR-001 unique complaint number under concurrency | Postgres `UNIQUE` constraint + one transaction via SQLAlchemy; tests run on real Postgres; number carries ≥40 random bits + a checksum char (sec F11) | AC-003 (pytest, **20 parallel** submissions via `concurrent.futures` + `httpx` against the `live_server` fixture) |
| FR-011 / FR-014 / BR-008 / BR-011 audit history | Append-only history tables written in the same transaction; no delete endpoint; **and, new in rev 4, a SQLAlchemy `before_execute` hook that raises on any `UPDATE`/`DELETE` targeting an append-only table** — enforcement at the data-access layer, not by convention | AC-009, AC-014, AC-016; test that an update/delete against each append-only table raises, plus a grep assertion that no such statement is constructed |
| FR-017–019 / BR-013 / BR-016 account management | Own auth layer: `is_admin_clerk` + `must_change_password` (**enforced in middleware (6)**) + a `require_admin_clerk` dependency; Argon2id hashing; 60-bit one-time password, single-use, 72 h, `no-store`, **all sessions revoked on reset** | AC-017 (incl. direct-URL denial and a deep-link bypass attempt) |
| FR-015 / AC-019 first-admin bootstrap | Idempotent **`bootstrap-admin` console script** (`argparse`), **interactive stdin by default** (no standing credential); `--from-env` only, with forced `must_change_password` + /release evidence of variable deletion | AC-019 (incl. the re-run case) + /release checklist |
| FR-020 / BR-015 / AC-018 malformed input, no lookup | **Pydantic validation before the handler body runs** is the contract; the client island's check is a UX nicety. **BR-015/AC-018 need analyst rewording** because the "JS disabled" half is gone (C7) | AC-018 restated: (1) **no statement touching the `complaint` table** (query-counter fixture, by table name); (2) Playwright asserts the exact message in the island |
| NFR-004 / NFR-005 / BR-010 anti-enumeration | No public list endpoint; in-repo limiter over an **atomic Postgres counter table** on a **dedicated `AUTOCOMMIT` engine**, 20/IP/min, config-driven; five-step client-IP rule; fails **closed** to a 503 the client renders as a friendly message; **CSRF on the public POST also blocks distributed guessing through other people's browsers** | AC-011 asserted **under parallel requests**, plus spoofed-XFF, positive multi-hop, IPv6-/64-rotation and missing-header tests |
| NFR-001 / NFR-002 / AC-010 performance | **Weaker than rev 3 and stated as such (C8):** static HTML shell from a CDN edge (better than rev 3) but **~120 KB gzipped first-load JS** before the form works (much worse than rev 3's ~25 KB). Single in-region DB hop, no cold start on the paid API tier, no cold start possible on the CDN | **A first-load-JS size gate in CI at /build** *and* a 3G-throttled measurement at /test-app (AC-010). Two named fallbacks if it fails (a 2 KB vanilla-JS public route, or an accepted requirement change) |
| NFR-008 / NFR-009 PII | **FULL once the enumerated `public_update` field exists in /architecture** (rev 5.1 — was PARTIAL). **GATE_2 answer Q7 is "option (b), fixed status messages"**, so the public page renders **enumerated status messages with no clerk free text** — the leak-proof option, chosen by the human over the public-safe-field variant. **Q-016 is resolved** and the requirements-analyst is amending **FR-009/BR-005**; the only remaining step is mechanical (define the enumeration and the `response_model` field in /architecture), after which the leak test below is claimable. No gov-ID field; **an explicit public DTO with `response_model` + `extra="forbid"`** (mechanically stronger than rev 3's template discipline); **no SSR, so no second process holds citizen data**; every npm package bundled at build time with no runtime third-party origin; no error tracker, no analytics; `no-store` + `no-referrer`; encrypted short-retention backups. **But** the resolved Q-001 puts a clerk free-text note on the public page (FR-009) — **replaced by enumerated status messages per GATE_2 answer Q7, binding on /architecture** (sec F3) | AC-006, AC-012 + **the test that a complaint holding a name and phone leaks neither into the serialised public response** — claimable only once that field exists |
| NFR-003 / AC-015 auth boundary | **Own deny-by-default middleware** with a public allow-list of exactly four entries (`POST /api/lookup`, `POST /api/login`, `GET /api/session`, `GET /healthz`); the Next.js redirect is **UX only** — the API is the security boundary | AC-015 tested **both directions against the API**, parametrised over the whole route table so a newly added route is covered automatically |
| NFR-010 retention | No deletion job exists anywhere in the stack (no job runner at all); limiter-window and expired-session cleanup are inline, bounded and touch no complaint data | AC-013 |
| NFR-006 low cost | **Rev 5.1, recomputed for Fly.io Mumbai: ≈$11–16/mo (≈$11–15 excluding optional items; working figure ≈$13)** — Fly Machine $3–5 + Fly Managed Postgres $7–9 + frontend $0 + domain ~$1 + optional dump destination $0–1; flat and predictable; **≈$265–385 over 24 months**. **The human approved ≈$14–16/mo at GATE_2 (Q2), so the envelope holds**; the only figure that could breach it is Fly Managed Postgres' smallest plan (verify at signup). *Superseded rev-5 figure: ≈$14–16/mo on Render Singapore.* **The frontend adds $0** — Render's static-site/free-tier docs **verified 2026-09-09: no commercial/organisational/government-use restriction**, bandwidth and pipeline-minute allowances shared with the workspace, exact figure **to confirm at signup** (A-T13); egress <1% of any plausible allowance | Costed in `tech-stack.md` (both totals printed) |
| NFR-007 uptime **and durable security-event evidence** | Single API instance + free 5-minute pinger on a **DB-checking** `/healthz`, scoped to office hours, **plus the append-only `security_event` table** (login success/failure, admin password reset, account creation, throttle events; actor as a hashed username on failure, derived IP, timestamp; **never the password, never the complaint number**) | Post-launch monitoring evidence; test that `security_event` rows are written on login success/failure and contain no password and no complaint number |
| NFR-011 in-flight/timeout UX | **Uniform on all three workflows now:** the client island disables the control, shows a spinner, and uses `fetch` + `AbortController` with a **10 s** abort rendering the message in-page. The API's gunicorn `--timeout 30` and the DB `statement_timeout` (~10 s) are backstops, so the user never sees a platform error page. **Conflict C6 is retired** — there is no no-JS path left to degrade | AC-002, AC-004, AC-006 via Playwright against a stubbed slow response, plus Vitest unit tests of the island's error/timeout rendering |
| Transport / headers (sec F10, F13) | `sslmode=require` in the DSN (asserted, and checked by `selfcheck`); **`--proxy-headers --forwarded-allow-ips`** for scheme correctness; **`TrustedHostMiddleware`** instead of `ALLOWED_HOSTS`; platform-edge HTTP→HTTPS redirect + **HSTS**; API CSP `default-src 'none'`; **static-site CSP `default-src 'self'` with `connect-src` naming the API origin** and **`script-src 'self'` plus generated per-page inline-script hashes — no `unsafe-inline`, with fallback (c) recorded if the hashing spike fails (H-C)**; `Referrer-Policy: no-referrer`, `Permissions-Policy`, `nosniff`, `X-Frame-Options: DENY` | Header tests on a public and an authenticated API response; the static-site headers checked against a deployed preview in the E2E suite; **`selfcheck` in CI replaces `manage.py check --deploy`** |
| **CSRF across the whole API (sec F15, sec F26; mechanism updated in rev 5 by H-A)** | **Three layered controls with no exemption mechanism in the codebase:** `SameSite=Lax` `httpOnly` `__Host-` cookies + an **`Origin` allow-list check** on every unsafe method + a token echoed in **`X-CSRF-Token`** — **session-bound when authenticated** (rotated with the session, returned in the login/password-change/logout responses) and **stateless `hmac_sha256(SECRET_KEY, __Host-csrfseed)` when not**, so **no database row and no SQL exist before authentication**. No cookie carries the token. Covers the **public lookup POST** (also an anti-enumeration control) | **Tests: 403 without a valid token on (a) an authenticated write and (b) the public lookup; 403 on a missing/foreign `Origin` on both; wrong-key and wrong-seed tokens rejected; rotated token present in the login/password-change/logout bodies; no exemption decorator or exempt-path list anywhere in the app package; and assertion 17 — an anonymous burst from one IP leaves the `session` table unchanged and the public lookup at 200** |
| **Unauthenticated write surface (new in rev 5 — H-A / arch F1 / sec F1)** | The public allow-list is unchanged (`POST /api/lookup`, `POST /api/login`, `GET /api/session`, `GET /healthz`), but **`GET /api/session` no longer writes anything**: `session.user_id` is **NOT NULL**, anonymous rows are gone, and the anonymous CSRF path performs **zero SQL**. So the only unauthenticated DB writes left are the limiter's own bounded upserts on `POST /api/lookup`/`POST /api/login`, which are exactly what the limiter is designed to bound | Assertion 17 (row count unchanged, public lookup still 200 under a one-IP burst) + a unit test that the anonymous CSRF path issues **no** statements (query-counter fixture) |
| **XSS and inline script/style policy (new in rev 5 — sec F8 / H-C)** | **React JSX escaping** is the primary control; `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function` and inline `style` are **forbidden in source**; user-supplied `href` values pass a **scheme allow-list**; the deployed static-site CSP carries **generated per-page script hashes and no `unsafe-inline`** (fallback (c) recorded if the spike fails) | Biome `security`+`correctness` groups, grep assertion 19, and CSP assertion 18 against the deployed preview |
| **Session hygiene on a shared office computer (sec F20)** | Server-side `session` table: rolling **30–60 min idle window** inside a ~9 h absolute ceiling; **no cookie `Max-Age`/`Expires`** ⇒ browser-close expiry; rotation on login and password change; **revoke-all on admin password reset / logout everywhere** (impossible with a signed cookie, which is why the table exists); a **visible logout control on every authenticated screen** (carried to /ux) | Tests for idle expiry, absolute expiry, the missing `Max-Age` attribute, rotation, and revoke-all after a reset |
| **CORS / two-origin topology (new, H4; confirmed by GATE_2 answer Q9 in rev 5.1)** | Static site on `www.<domain>.in` (**Render**), API on `api.<domain>.in` (**Fly**) — **two vendors, one registrable domain**, which is what `SameSite=Lax` actually depends on, so the split changes nothing about the cookie design; the human has confirmed a single `.in` domain **provided before real citizen data**, and the platform default hostnames (`*.onrender.com`, `*.fly.dev`) are **not** same-site with each other, so attach-before-real-data is a binding /release gate item. `SameSite=Lax` cookies flow with `credentials: "include"`; **explicit CORS allow-list**, never `*`, never a regex; **preview URLs deliberately excluded** so a preview build cannot reach production data | `selfcheck` fails on `allow_origins=["*"]` with credentials; a test asserts a foreign origin is refused; A-T12 records that the same-registrable-domain assumption is load-bearing |
| **Two deployables / version skew (new, H4 — R14)** | **Additive-only API responses** (the migration discipline extended to the API contract); **fixed promotion order** (API first, then the static site; reverse for rollback); short `Cache-Control` on HTML, immutable hashed assets; auto-deploy **OFF on both**. **Rev 5:** the additive-only rule is now backed by **committed generated client types with a CI staleness check** (arch F7), promotions land **outside office hours**, and a **chunk-load failure produces a "new version available — reload" prompt** instead of a blank screen (arch F8) | One **post-deploy E2E smoke spec run against production by the human** is the /release evidence that the two halves match; plus Playwright specs for the **deep-link rewrite** (arch F3) and the **stale-chunk reload prompt** (arch F8), run against `out/` served with the host's own rewrite/cache rules |
| **npm supply chain (H4 — R16; residual restated in rev 5 by H-B)** | *Prevention:* committed `package-lock.json` + **`npm ci --ignore-scripts`** everywhere (recorded exceptions), exact versions, `npm audit --audit-level=high` **plus `npm audit signatures`** in CI and monthly, Dependabot on `npm` with **auto-merge only for patch/minor bumps of already-present packages and a 7-day minimum release age**, two-eyes on any new direct dependency, direct budgets (≤6 runtime, ≤12 dev), no runtime CDN script. *Containment, which is the part rev 4 got wrong:* the `httpOnly` cookie prevents **theft of a reusable token**, **not use of the session from the page** — a malicious package retains **full clerk capability** (all PII that clerk may see, every OTP issued while the page is open). The controls that actually bound it are **CSP `connect-src`/`img-src`** (with the caveat that CSP does not stop top-level-navigation exfiltration), the **30–60 min idle window**, and **response minimisation** (every route has a `response_model`; the clerk list carries no `name`/`phone`) | CI gates; dependency-strategy.md §3/§4/§6; assertions 18 and 20. **Residual explicitly not fully mitigated, and stated in attacker-capability terms:** ~350–450 resolved packages cannot be individually reviewed and **no control here detects a zero-day malicious release of a package we already trust** — the ADR must say exactly that |

**Note (arch F14):** the resolutions of Q-001 (public page shows number, status, date logged, latest
note) and Q-002 (New → In Progress → Resolved/Rejected → Closed, no skipping) change **no layer
choice in this document** — both are application logic on the chosen stack. Q-001 does create the
public free-text exposure that GATE_2 question 7 / Q-016 and the PARTIAL marker above address.

---

## Carried forward to /architecture

Decisions this document *records* but does not design. /architecture owns the design; the constraint
in the right column is binding, and came either from a reviewer finding or from a human decision.

| Item | Binding constraint from this phase |
|---|---|
| Rate-limit counter model + limiter code | One atomic statement (`INSERT … ON CONFLICT DO UPDATE … RETURNING`); no read-modify-write; no eviction; thresholds from environment settings; **deterministic** (not 1%-probabilistic) `LIMIT`-bounded cleanup of old windows; no job runner (arch F1, sec F1, sec F16) |
| **Limiter transaction boundary (arch F3) — mechanism updated by H3** | The upsert executes on a **dedicated engine/connection in `AUTOCOMMIT`**, never on the request-scoped `Session`, so it **commits independently of the request being counted** by construction. Django's `ATOMIC_REQUESTS` has no equivalent and needs none. Test: a **failed login** (and a handler that raises) still increments the counter |
| **Login-limiter key shape and evaluation order (sec F16)** | Evaluate the **per-IP ceiling first and short-circuit before writing any username-keyed row**; the username component is **normalised, hashed and truncated to a fixed width** in every key and in `security_event`; test that a burst of distinct usernames from one IP neither grows the counter table unboundedly nor 503s the public lookup |
| **Anti-lockout rule (arch F4) + no request-thread sleep (sec F23)** | The per-account control is a **capped progressive backoff (~1→5 s), not a hard lock**, and it is expressed as an **immediate `429` with `Retry-After` — never a `sleep`**, because the anyio threadpool is capped at 4 tokens per worker and a sleeping thread is a self-DoS. **Skipped for an IP with a recent successful login for that account.** Blocking is carried only by username+IP and the per-IP ceiling. Test: attacker IP gets a **fast** 429 while the office IP logs in undelayed |
| Client-IP derivation helper | The five-step rule; `TRUSTED_PROXY_HOPS` as an explicit setting **confirmed against Fly's proxy behaviour (rev 5.1 — `Fly-Client-IP` plus an appended `X-Forwarded-For`; the Render assumption is withdrawn and must not be inherited)**; IPv6 → /64; fail closed on a missing header; three negative tests **plus a positive multi-hop test, a `selfcheck` startup check that the setting is explicitly present, and a live /release verification from a known source address with the temporary log line removed afterwards** (sec F2, sec F17). Separately, **uvicorn `--proxy-headers --forwarded-allow-ips`** is for scheme/redirect correctness only and is **not** the limiter's source of client identity |
| **ORM / migrations (new — H3)** | **SQLAlchemy 2.x sync + Alembic + `psycopg[binary]` 3.** One session per request via a dependency with explicit commit/rollback in a `finally`; pool sizing and the **≤20-connection ceiling** are in the *Connection budget* row below (rev 5 replaces rev 4's "≤12", which costed only one of the two engines — arch F2); `statement_timeout` ~10 s on connect; `alembic check` in CI; autogenerated revisions **always human-reviewed**; **additive-only / forward-compatible** migrations |
| **Append-only enforcement (D6 — strengthened by H3)** | A SQLAlchemy `before_execute` hook **raises on any `UPDATE`/`DELETE` targeting `complaint_status_history`, `complaint_edit_history` or `security_event`**. Optional and recorded, not required: `REVOKE UPDATE, DELETE` on those tables from the application role in a migration, if the platform permits a second role |
| **Session table + cookie (H3; rewritten in rev 5 by H-A)** | Server-side `session(id, token_hash, **user_id NOT NULL**, csrf_token, created_at, last_seen_at, absolute_expires_at, revoked_at)` — **no anonymous rows exist and none may be reintroduced**; cookie value `secrets.token_urlsafe(32)` with **only its SHA-256 hash stored**; `httpOnly` + `Secure` + `SameSite=Lax` + `Path=/` + `__Host-` prefix + **no `Max-Age`/`Expires`** and **no `Domain`**; rolling **30–60 min** idle window inside a **~9 h** absolute ceiling; **rotation on login and on password change**, with the **rotated CSRF token returned in that response** (arch F10); **revoke-all on admin reset, self-change and "log out everywhere"**; expired rows swept by the same deterministic trigger as the limiter. **`SameSite=None` is forbidden** — if one registrable domain is unavailable, the model becomes a BFF proxy and returns to GATE_2 (sec F6) |
| **CSRF (sec F15, sec F26) — mechanism replaced by H3/H4, split in rev 5 by H-A** | Three layered controls on **every unsafe method on every route**, with **no exemption decorator and no exempt-path list anywhere in the codebase**: `SameSite=Lax` cookies; an **`Origin` check against the CORS allow-list**; and a token echoed in **`X-CSRF-Token`** — **session-bound when authenticated**, and **stateless `hmac_sha256(SECRET_KEY, __Host-csrfseed)` when not, so the unauthenticated path performs no SQL and creates no row**. `SECRET_KEY`'s only two consumers are this HMAC and the `h(username)` salt (sec F9). **403-without-token test on an authenticated write *and* the public lookup POST**, plus 403 on a missing/foreign `Origin` on both, wrong-key/wrong-seed rejection, and **assertion 17** (anonymous burst ⇒ `session` row count unchanged, public lookup still 200) |
| **Route-level response contracts (sec F4 — new binding constraint in rev 5)** | **Every route declares an explicit `response_model`** with `extra="forbid"` — asserted by a test **parametrised over `app.routes`** that fails on any route with `response_model=None`. The clerk **list** response carries **no `phone` and no `name`** (both move to the detail response, per FR-016), which is the response-minimisation half of the H-B containment story |
| **Frontend route shape (arch F3 + sec F11 — new in rev 5)** | **No dynamic route segments are emitted**, so `generateStaticParams` is never needed under `output: "export"`; the clerk detail view is **client state inside `/complaints`**, and the complaint number appears in **no URL, query string or `history` entry**. A **committed rewrite/header file** (`/complaints/*` → the exported shell; HTML `no-cache`; hashed assets immutable) is consumed by **both the static host and the CI/E2E static server**. One Playwright spec asserts deep-link behaviour against the exported build served that way; one asserts the **stale-chunk reload prompt** (arch F8) |
| **Static-site CSP (H-C — decided, with a fallback)** | A **committed post-build step** hashes every inline `<script>` in every emitted HTML file and generates the per-path `script-src 'self' 'sha256-…'`. **Assertion 18** fails the E2E suite if the deployed policy contains `unsafe-inline`/`unsafe-eval` or if any served inline script is unhashed. `style-src 'self'` is kept, so **inline styles are forbidden in source** (Biome + grep assertion 19). **Spike task for /architecture:** prove the hash set is deterministic and the host accepts the headers; **if it fails, fallback (c)** — `script-src 'self' 'unsafe-inline'` as a **recorded weakening** with R16 restated. Switching to Vite + React (no inline bootstrap) is a **GATE_2 question**, not an evaluator decision |
| **Connection budget (arch F2 — new in rev 5)** | **Two engines per worker, both sized:** request `QueuePool(pool_size=4, max_overflow=2)` ⇒ ≤6, limiter `QueuePool(pool_size=4, max_overflow=0)` ⇒ 4 (the limiter must not be able to expand the pool under the load it exists to refuse). **Ceiling ≤10/worker, ≤20 at 2 workers**, plus release-command/`psql` transients. **Verify the plan's connection limit at signup**; if under ~25, drop to `--workers 1`. The rev-4 claim "a thread never waits on a connection" is **withdrawn as false** |
| **Typed client contract (arch F7 — new in rev 5)** | CI dumps the OpenAPI schema (never served in production) and **`openapi-typescript`** generates `api-types.ts`, which is **committed**; **CI fails if it is stale**. This is what R14's "additive-only" discipline rests on, alongside the post-deploy smoke spec |
| **Middleware order (new — H3)** | Outermost → innermost: uvicorn `--proxy-headers` → `TrustedHostMiddleware` → security headers → CORS → session loader → CSRF → deny-by-default authorisation + `must_change_password` → router. **A test asserts the registered order** |
| **Deny-by-default + public allow-list (arch F8) — mechanism replaced by H3** | Own middleware; the allow-list is **exactly** `POST /api/lookup`, `POST /api/login`, `GET /api/session`, `GET /healthz`; everything else, including future routes, is closed. AC-015 tested in both directions, **parametrised over the route table**. A `require_admin_clerk` dependency on the two account-management endpoints |
| **OpenAPI docs (new — H3/H4; value restated in rev 5 by sec F5)** | `docs_url=None, redoc_url=None, openapi_url=None` in production. **Test: `/docs`, `/redoc`, `/openapi.json` all return 404.** **This is hygiene, not an anti-enumeration control:** under H4 the route paths, schemas and the entire clerk UI ship in a public bundle. **Authorisation is the control** (deny-by-default over the route table + `require_admin_clerk`). The schema **is** generated in CI to produce the committed client types (arch F7); it is never served |
| **Public response DTO (R15 — new, H4)** | The public lookup route declares an explicit **`response_model`** (`complaint_number`, `status`, `date_logged`, `public_update`) with **`extra="forbid"`**; no ORM object is ever returned unfiltered. **Test:** a complaint holding a name and a phone number leaks neither string into the serialised response. This control must survive every future refactor |
| **Frontend rendering + payload (H4, C8)** | Next.js 15 App Router, **`output: "export"`** (no Node process in production); the public lookup route is **prerendered with one small client island**; **no SSR of authenticated data**; **≤120 KB gzipped first-load JS** on the public route, gated in CI at /build and measured on a throttled 3G profile at /test-app; no CSS framework, no component library, no `next/font`, no runtime CDN asset. Named fallback if the budget fails: a hand-written static HTML public route with ~2 KB of vanilla JS |
| **Frontend↔API topology (H4, A-T12)** | Static site on `<domain>.in`/`www.<domain>.in`, API on `api.<domain>.in` — **same registrable domain** (load-bearing for `SameSite=Lax`); **explicit CORS allow-list**, `allow_credentials=True`, methods `GET, POST`, headers `content-type, x-csrf-token`; **never `*`, never a regex, preview origins excluded**. **No BFF proxy** |
| **Two-deployable discipline (R14 — new, H4; extended in rev 5 by arch F7/F8)** | **Additive-only API response shapes**, now backed by **generated-and-committed client types that CI checks for staleness** (arch F7) rather than by discipline alone; **promotion order API → frontend** (reverse for rollback) and **promotions land outside office hours**; auto-deploy **OFF on both**; a **post-deploy E2E smoke spec run against production** as /release evidence. **Stale-chunk mode (arch F8):** a cached HTML shell that requests a content-hashed chunk deleted by the promotion must produce a **"new version available — reload" prompt**, not a blank screen — client helper behaviour, a /ux wording item, and one Playwright spec that serves a shell with a missing chunk |
| **Password policy (new — H3)** | In-repo `validate_password(password, *, username)`: **min length 12** (Conflict C5 — BR-016's floor is 8), not similar to the username, not all-numeric, not in a common-password list. The list is **Django's BSD-3-licensed `common-passwords.txt.gz` vendored with attribution** and recorded as a *vendored asset* in dependency-strategy.md §5 — or the check is dropped and that is stated, not silently missing |
| **Password hashing (new — H3)** | **Argon2id via `argon2-cffi`** at **`m=9216 KiB, t=4, p=1`** (an OWASP-listed configuration chosen *below* the first-listed one because of the 512 MB instance — the arithmetic is in `tech-stack.md` § Auth). `check_needs_rehash()` on login. **No custom crypto anywhere**; `passlib` is forbidden (unmaintained, breaks on 3.13) |
| **Production-config gate (new — H3)** | An in-repo **`selfcheck`** console script, also called on startup, asserting the nine production invariants listed in Layer 9. It **fails startup** in production and **fails CI**. This is the replacement for `manage.py check --deploy` |
| **`security_event` table (sec F19)** | One **append-only** table in the existing Postgres — no new dependency, no new service. Login success/failure, admin password reset, account creation, throttle events, with actor (hashed username on failure), derived IP, timestamp, reason code. **Never** the password (in any form) and **never** the complaint number. No application update/delete path, now enforced by the `before_execute` hook |
| DB-failure behaviour | Limiter fails **closed**; public lookup and login return **503 with a stable JSON error code** that the client renders as a friendly message; `/healthz` runs `SELECT 1` with a short statement timeout and leaks no version or dependency detail (arch F6) |
| Public "latest note" | **DECIDED at GATE_2 (Q7): option (b) — a fixed set of enumerated status messages, no clerk free text on the public page.** The clerk's free-text note stays **clerk-only**. **Q-016 resolved**; the analyst is amending FR-009/BR-005; /architecture defines the enumeration and the public `response_model` field (sec F3) |
| **Base image (new in rev 5.1 — created by Q1, owned per Q6)** | Fly deploys images, so a **`Dockerfile` is committed**: `FROM python:3.13-slim@sha256:<digest>`, non-root, `uv sync --frozen`, no build toolchain in the final layer. **Digest-pinned, Dependabot `docker` ecosystem, monthly scheduled CI rebuild that runs the full suite, digest bump via reviewed PR, deploy still a manual `fly deploy`. Owner: the human (GATE_2, 2026-09-09)** — this named owner is what satisfies arch F2's condition for allowing an image at all |
| **Fly platform specifics to verify, not assume (rev 5.1)** | `primary_region = "bom"` for the machine **and** the Managed Postgres cluster (verified at /release — a machine created elsewhere would break Q1); `release_command = "uv run alembic upgrade head"`; `[[http_service.checks]]` on **`/healthz`**; `min_machines_running = 1` (**no scale-to-zero** — cold start fights D4/NFR-001, the same reason the free Render web tier was rejected); secrets via **`fly secrets`**; **`TRUSTED_PROXY_HOPS` re-derived for Fly's proxy** (`Fly-Client-IP` / appended `X-Forwarded-For`) with the positive multi-hop test, the `selfcheck` startup check and the **live /release verification** — the Render hop assumption must not be carried forward (A-T9); **Managed Postgres price, backup retention and connection limit (≤20 at 2 workers) confirmed at signup** (A-T10) |
| Complaint-number format | ≥40 bits random, non-sequential, one checksum character; lookup by **POST**; `no-store` + `no-referrer`; number excluded from logs and URLs — **and, with H4, never placed in a client-side route, query string or `history` entry** (sec F11) |
| `must_change_password` enforcement | Enforced in middleware for **every** authenticated request (except change-password, logout and `GET /api/session`) as a **403 with `{"must_change_password": true}`**; the client redirect is cosmetic. One-time password single-use with 72 h expiry, returned in exactly one response, and **all sessions revoked when it is issued** (sec F12) |
| Security-header middleware | ~20 lines in the API (static policy, no dependency) **plus committed header configuration on the static host**, including `connect-src` naming the API origin and, per the *Static-site CSP* row, **generated inline-script hashes instead of `unsafe-inline` — with fallback (c) recorded if the hashing spike fails**. Asserted in tests on both sides (assertions 3, 18) |
| Migration discipline | Additive-only / forward-compatible so rollback-by-redeploy is safe with no staging environment (arch F5) |
| Backup runbook | Go-live restore into a throwaway platform DB destroyed afterwards, with evidence (sec F8). The **off-platform copy exists only if** a named key holder **and** a named destination with a scoped credential and an automatic expiry rule both exist; it is encrypted before leaving the platform shell, with ≈90-day lifecycle-enforced retention. **Otherwise it is dropped and platform daily backups are the only mechanism — no manual-download substitute** (sec F18, arch F5) |
| Branch protection (arch F2 + arch F3 / sec F25) | `main`: **require a pull request before merging** + green required checks + linear history + no force-push + no deletion; **no required human review**, so Dependabot security auto-merge works. **Auto-merge only for patch/minor bumps of packages already present in `uv.lock`/`package-lock.json`.** Two-eyes applies to **new dependency additions in either ecosystem** |
| **Requirements change, ACCEPTED BY THE HUMAN (C7 / R17 — from H4; confirmed at GATE_2 by answer Q8)** | The public lookup page **requires JavaScript**, and the human has confirmed that explicitly ("confirmed, public page may require JavaScript"). The requirements-analyst **is amending** BR-015's "or at the very first server check" phrasing, the **"with JS disabled" half of AC-018**, and the "not assumed to have a smartphone" persona line, with **H4 recorded as the cause**. The surviving contract — **no query before validation** — is unchanged and asserted. Nothing further is pending from the human; /ux still owns the `<noscript>` wording |
