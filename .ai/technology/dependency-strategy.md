# Dependency Strategy — panchayat-complaint-tracker

Companion to `tech-stack.md`. Date 2026-09-09. Baseline: requirements rev 4 (GATE_1).

**Rev 5.1 — GATE_2 APPROVED (2026-09-09); post-approval housekeeping only. Three changes, no policy
change:** (1) **ownership is resolved** — every **UNASSIGNED** row in §4 now reads **"Owner: the
human (GATE_2, 2026-09-09)"** per answer Q6 ("I own patching and backups; I hold the backup key"),
and the encrypted off-platform dump is **enabled** with its **destination TBD — human to name at
/release**; (2) **a container image enters the supply chain** — answer Q1 ("India — use the Mumbai
region") triggered the Fly.io swap, so §2 gains a **digest-pinned `python:3.13-slim`** row and §4's
OS-patching row splits between the platform and the human, with a **monthly scheduled CI rebuild**;
(3) §8's residency, ops-owner, no-JS and SSR review triggers **have fired and are applied**. Full
record: `tech-stack.md` § Changelog (rev 5 → rev 5.1).

**Rev 5 — third internal review pass.** The policy is unchanged; five things are added or corrected,
all of them supply-chain findings from the security review (**sec F7**) plus one adopted dependency:

1. **npm auto-merge now has a cooldown.** A Dependabot **npm** security PR may auto-merge only if the
   target version has been on the registry for **≥7 days** (a *minimum release age*). Rationale: the
   npm attack that actually happens is a compromised maintainer account publishing a malicious patch
   release, and it is typically detected and yanked within hours to days — auto-merging on the day of
   publication is the one window where our automation would install it for us. A 7-day lag on a
   *security* patch is a real cost and is accepted deliberately: `npm audit` keeps reporting the
   advisory throughout, and a human may always merge sooner on purpose. Applies to **npm only** —
   PyPI keeps the same-day rule, because the Python surface is 8 direct packages we can eyeball.
2. **`npm audit signatures`** joins `npm audit --audit-level=high` in the frontend CI job, verifying
   the registry's signatures/provenance attestations for the installed tree.
3. **The `--ignore-scripts` question is answered now, not at /build (§1 item 10).**
4. **`openapi-typescript`** is adopted as npm dev dependency **10 of 12** (arch F7) — dev-only, MIT,
   generates the committed API client types so a contract change breaks CI, not production.
5. **R16's residual is worded identically to `tech-stack.md`** (H-B): the `httpOnly` cookie prevents
   *theft of a reusable token*, **not use of the session from the page**, and **no control in this
   document detects a zero-day malicious release of a package we already trust.**

**Rev 4** — rebuilt for the two human decisions taken at GATE_2:

> **H3: "changes: use FastAPI for the backend"**
> **H4: "Use FastAPI as a JSON API with a separate Next.js frontend."**

**This is the pass in which this document changes the most, and it should be read as such.**
Rev 3 could say "4 runtime dependencies, 0 npm packages, nothing phones home". Rev 4 says
**8 Python runtime dependencies and ~350–450 resolved npm packages**. Nothing about the *policy*
has been relaxed; what changed is the size of the surface the policy has to cover, and the honest
statement of what is and is not reviewable at that size.

**Summary of rev-4 changes:**
1. **§1** now has **two ecosystems**. The Python baseline goes from 4 to **8** (`django`,
   `psycopg`, `gunicorn`, `whitenoise` → `fastapi`, `uvicorn`, `uvicorn-worker`, `gunicorn`,
   `sqlalchemy`, `alembic`, `psycopg[binary]`, `argon2-cffi`); `whitenoise` is **retired**;
   **npm enters the trust boundary** with 3 direct runtime and 9 direct dev packages.
2. **§1** records the maintenance checks that actually changed a decision: **`passlib` rejected**
   (last release 2020; `crypt`-based backends target a stdlib module removed in Python 3.13),
   **`slowapi`/`fastapi-limiter` rejected** (0.x, and correctness depends on a backend we do not
   have — the FastAPI-ecosystem repeat of rev 2's `django-ratelimit` finding), **`SQLModel`
   rejected** (PII shape + thin maintenance), **`Typer` rejected** (+2 packages to save ~20 lines),
   **`itsdangerous` never needed** (server-side sessions), **`pwdlib` rejected** (young wrapper over
   a library we can use directly).
3. **§2** adds npm pinning: exact versions with **no carets**, committed `package-lock.json`,
   `npm ci` everywhere, and a pinned Node 22 LTS via `.nvmrc`.
4. **§3** withdraws the **"zero npm packages"** budget — it is no longer achievable and pretending
   otherwise would be dishonest — and replaces it with explicit npm budgets.
5. **§4** records **two patching streams** (Python API and frontend/npm/Node), folds in the rev-3
   advisories **arch F3 / sec F25** (`main` now also **requires a pull request before merging**, and
   **auto-merge is narrowed to patch/minor bumps of packages already present in the lockfiles**),
   and notes that **"merged ≠ deployed" now has two doors**.
6. **§5** corrects an **inherited rev-3 licence error**: `psycopg` 3 is **LGPL-3.0**, not
   BSD/MIT/Apache, so the claim "the whole stack is BSD/MIT/Apache/PSF" was wrong. It is handled
   under the existing "review required" class. §5 also adds a **vendored-asset** row for Django's
   BSD-3-licensed common-password list.
7. **§6** adds `npm audit`, extends two-eyes to **new npm dependencies**, and states plainly that
   ~400 transitive npm packages **cannot** be individually reviewed.
8. **§7** retires the Django-specific "do not add" rows and adds the ones H4 creates
   (`next-auth`, a client-side state library, a CSS framework, an AI npm package, RUM/analytics).

Context that shapes everything below, unchanged: a single-panchayat pilot, 1–5 clerks, ~$14/mo of
hosting (NFR-006), **no ongoing operations owner** (the Operator persona is a one-time bootstrap
actor, FR-015/A11), and a Must-priority audit trail holding citizen PII (FR-011, FR-014, NFR-008,
NFR-009). The strategy is therefore still biased hard toward *fewer, older, duller* dependencies.
**A dependency that nobody will patch is a liability, not a feature** — and after H4 there are
several hundred more of them.

---

## 1. How a dependency gets in

A new dependency — **Python or npm** — must pass **all** of these before it is added. Failing any
one means it is not added; disagreement is resolved by an ADR, not by a merge.

1. **A named requirement needs it.** Cite an FR/NFR/BR/AC ID in the PR description. "It might be
   useful later" is a rejection.
2. **Nothing already in the stack does the job.** Check, in order: the **standard library**
   (Python's `secrets`, `hmac`, `hashlib`, `argparse`, `getpass`, `ipaddress`; the browser's
   `fetch`, `AbortController`, `FormData`) → **something already present** (Starlette middleware,
   Pydantic validators, SQLAlchemy constructs, React itself) → an existing dependency. Rev 3 could
   point at Django for this; rev 4 has to point at the standard library and at the framework
   primitives, which is a weaker filter and therefore has to be applied more deliberately.
3. **Licence is on the allow list** (§5).
4. **Maintenance signals are healthy:** a release within the last 12 months, an issue tracker with
   maintainer replies, more than one maintainer *or* clear organisational backing, and a public
   changelog/release-notes practice. **This criterion did real work in rev 4** — see the rejections
   listed below.
5. **Adoption is real:** widely used in the Python or React ecosystem, not a package with a few
   thousand downloads and one contributor. For anything less than mainstream, record the licence and
   last-release date in the PR.
6. **Transitive cost is acceptable:** run `uv tree` or `npm ls --all` and state how many packages it
   drags in. A dependency that pulls a dozen transitive packages to save twenty lines of code is
   rejected. **For npm this check matters more, not less** — a single "small" package can add
   dozens.
7. **The exit is cheap:** we can state, in one sentence, how the app would work without it.
8. **The dependency budget still holds** (§3).
9. **It does not phone home.** No telemetry-by-default, no analytics, no third-party network calls
   at import, request or **page-load** time (NFR-008/NFR-009). **Zero runtime dependencies talk to a
   third party**, and that now includes the browser: no CDN asset, no web font, no analytics
   endpoint, no error-reporting beacon. Next.js's own telemetry is **disabled**
   (`next telemetry disable` / `NEXT_TELEMETRY_DISABLED=1` in the build environment) and that is a
   /build checklist item. If an ops owner is named at GATE_2 and the hardened Sentry recipe is
   adopted, that becomes the single documented exception, with the compensating test in
   `tech-stack.md` § Observability.
10. **(New in rev 4; decided in rev 5 — sec F7) No install-time code execution.** Prefer packages
    without `postinstall` scripts, and **the decision is taken now rather than deferred to /build:**
    **`npm ci --ignore-scripts` is the standard install command everywhere** — CI, the static host's
    build command, and local development (it is written into `install_web`/`build_web` in
    `tech-stack.md` § Expected commands). The two things that could break under it are named:
    - **`next`/SWC platform binaries.** Next.js ships its native SWC binaries as **optional
      platform-specific packages resolved by the lockfile**, not as a `postinstall` download, so a
      `--ignore-scripts` install is expected to work. **If a specific version proves otherwise**, the
      exception is recorded here as `next` + the exact version + the reason, and the install becomes
      `npm ci --ignore-scripts && npm rebuild next` (a **named, minimal** re-enable — never a blanket
      drop of the flag).
    - **Any package that turns out to require a build step** (`sharp`-class native modules): we have
      none, and adding one is a new-dependency decision under §6's two-eyes rule, where the script
      requirement must be stated in the PR.
    **Recorded exceptions at rev 5: none.** If that changes, this list — not a comment in CI — is
    where it is written.

### Expected baseline set (post-/plan; an ADR is required to exceed the budget)

**Python runtime (8, was 4):**

| Package | Licence | Why it is here | Maintenance note (checked 2026-09) |
|---|---|---|---|
| `fastapi` | MIT | H3. Installed as **`fastapi`, not `fastapi[standard]`** — the extras would pull `fastapi-cli`, `rich`, `email-validator`, `httptools`, `watchfiles`, `websockets`, `python-dotenv`, none of which a requirement needs | Very widely used, active, but **0.x with no LTS** (risk R12) |
| `uvicorn` | BSD-3 | ASGI server. Installed as **`uvicorn`, not `uvicorn[standard]`** — no `uvloop`/`httptools`/`watchfiles`/`websockets` at <1 rps (D1) | encode, active |
| `uvicorn-worker` | MIT | The gunicorn worker class, which **moved out of uvicorn** (the in-tree `uvicorn.workers.UvicornWorker` is deprecated). Kept because gunicorn gives `--timeout` and `--max-requests`, which uvicorn's supervisor does not | Small but **maintained by the uvicorn/encode team**; recorded as a non-mainstream item |
| `gunicorn` | MIT | Process supervisor: `--timeout 30` (kills a wedged worker) and `--max-requests 1000` (bounds a slow leak on 512 MB) | Long-standing, stable |
| `sqlalchemy` | MIT | H3 forced an ORM. One schema authority for the append-only history and the limiter/session tables (D6, D7); fully typed, which is why `django-stubs` could be dropped | Top-20 PyPI, conservative release policy |
| `alembic` | MIT | Migrations for SQLAlchemy; `alembic check` is the CI drift gate | Same maintainer as SQLAlchemy |
| `psycopg[binary]` | **LGPL-3.0** | Postgres driver (v3). **See the §5 licence note — this is a "review required" licence and rev 3 mis-described the stack as entirely BSD/MIT/Apache** | Actively maintained; `[binary]` avoids compiling on the build host |
| `argon2-cffi` | MIT | H3 removed the framework hasher. Gives `hash()`/`verify()`/`check_needs_rehash()` and a self-describing encoded string, so **we write no crypto** | Hynek Schlawack; the library Django's own Argon2 backend used |

**Retired from rev 3:** `django` (H3), `whitenoise` (H4 — the API serves no static files).

**Python dev (7, was 8):** `pytest`, `pytest-cov`, `httpx`, `playwright`, `ruff`, `mypy`,
`pip-audit`.
**Retired:** `pytest-django` (replaced by ~80 lines of in-repo fixtures — engine/session,
`live_server`, query counter) and `django-stubs` (FastAPI/Pydantic/SQLAlchemy ship their own types).
**Added:** `httpx` (needed by Starlette's `TestClient`).

**npm runtime (3 — new):** `next`, `react`, `react-dom`. All MIT, all top-tier, all pinned to exact
versions. Next.js has **its own security-release cadence and roughly annual majors with real
migration work** — this is the second patching stream in §4.

**npm dev (10 — rev 5 adds one):** `typescript`, `@types/node`, `@types/react`, `@types/react-dom`,
`vitest`, `@vitejs/plugin-react`, `jsdom`, `@testing-library/react`, `@biomejs/biome`,
**`openapi-typescript`** (MIT, mainstream, **dev-only and build-time-only — it ships no code to the
browser**). It exists because rev 4 *claimed* a typed client/server contract while nothing generated
types (arch F7): CI dumps the API's OpenAPI schema, this tool generates `api-types.ts`, the file is
committed, and CI fails if a regeneration differs — so a renamed field breaks CI instead of a
citizen's lookup. The alternative (hand-written types plus the additive-only rule and the post-deploy
smoke spec) was the honest cheaper option and is rejected for one dev dependency, because
hand-written types drift silently and that is the exact failure being guarded against.
`@biomejs/biome` (MIT, active, Rust) is the only non-obvious one: **one** package replaces
ESLint + Prettier + `eslint-config-next` + plugins, mirroring the Ruff decision. Trade-off recorded
in `tech-stack.md`: no Next.js-specific lint rules.

**Optional, offered to the human, not adopted:** `pyotp` (MIT) for admin-clerk TOTP; `sentry-sdk` if
an ops owner is named. Either is +1 Python runtime dependency and stays inside the budget.
(Rev 3 offered `django-otp`; it is Django-only and is retired.)

**Deliberately *not* added, where the obvious FastAPI/Next.js answer would have been to add
something** — each of these is a decision, and each saved at least one package:

| Candidate | Why not |
|---|---|
| `passlib[bcrypt]` | **Unmaintained** — last release 1.7.4, **October 2020** — and its `crypt`-based backends target a stdlib module **removed in Python 3.13** (PEP 594), which is our interpreter. Fails criterion 4 outright. `argon2-cffi` instead. |
| `pwdlib` | A young 0.x wrapper over `argon2-cffi` with a small maintainer base. Use the wrapped library directly (criterion 2). |
| `itsdangerous` / Starlette `SessionMiddleware` | Not needed at all: sessions are **server-side rows**, because a signed cookie cannot be revoked and rev 3 requires revoke-on-reset and logout-everywhere (sec F20, BR-016). |
| `slowapi`, `fastapi-limiter` | 0.x, small maintainer bases, and **their correctness depends on a storage backend we do not have** (in-memory = per-worker and wrong; Redis = a $10/mo component we rejected). This is exactly the rev-2 `django-ratelimit` finding repeating itself in a new ecosystem, and it is checked rather than assumed. |
| `sqlmodel` | Its premise — one class is both the table and the API schema — pushes against NFR-009, which requires the public response to be a **different shape** from the row (risk R15). Thinner maintenance than SQLAlchemy. |
| `typer` / `click` | +2 packages to save ~20 lines of `argparse` for **two** commands (`bootstrap-admin`, `unlock-account`). |
| `python-dotenv`, `pydantic-settings` | `os.environ` plus a small typed settings module is sufficient; one fewer place a secret can be read from a file. |
| `jinja2`, `python-multipart` | Added by H3, then **removed again by H4**: the API serves JSON only — no templates, no form parsing. A good example of why the count is recomputed per pass rather than assumed. |
| `next-auth` / `@auth/core` | Auth is the API's job, and BR-016's on-screen one-time password does not fit an email-centric provider library. The client holds no credential at all — only an `httpOnly` cookie it cannot read. |
| A client state library (`redux`, `zustand`, `@tanstack/react-query`) | Six screens, one fetch helper with `AbortController` (which NFR-011 requires anyway). Revisit only if /ux produces something genuinely stateful. |
| A CSS framework or component library (Tailwind, MUI, shadcn deps) | Hand-written CSS is ~4–8 KB for ~6 screens, and **Conflict C8 means every kilobyte on the public route is contested**. |
| `next/font`, an icon package, an image library | Same reason: payload. System font stack, no icons that are not inline SVG, no images. |

Non-mainstream items and their status are listed inline in the tables above rather than in a
separate paragraph, so the licence and maintenance note sits next to the package it describes.
`uv` (tool, not a library) — Apache-2.0/MIT, Astral-backed, the youngest thing here and the one
tracked as an accepted risk (`tech-stack.md` R4). **In-repo instead of a dependency, by design:**
the rate limiter (~60 lines over one atomic SQL statement), the session layer, the CSRF check
(~30 lines), the security-header middleware (~20 lines), the deny-by-default middleware, the
password policy, `selfcheck`, and the two console scripts. That is ≈350–450 lines we own
(**R11**) — a deliberate trade against packages nobody is assigned to patch (D3), and the reason
every one of those mechanisms carries a named test assertion in `tech-stack.md` § Tooling.

---

## 2. Pinning

| What | How | Why |
|---|---|---|
| Python version | `.python-version` pins 3.13.x, honoured by CI, by local `uv` **and by the container image** | Same interpreter minor version everywhere. **Rev 5.1: the Fly.io residency swap has triggered (GATE_2 answer Q1, "India — use the Mumbai region"), so a Docker base image now exists.** The condition arch F2 attached to it is met: **`FROM python:3.13-slim@sha256:<digest>` — pinned by digest, with a named owner for the monthly rebuild: the human (GATE_2, 2026-09-09, Q6).** Mechanism: Dependabot's **`docker` ecosystem** watches the base image, a **monthly scheduled CI job** rebuilds and runs the full suite, the digest bump lands as a **reviewed PR** (never auto-merged — it is not a lockfile patch bump), and the deploy is a manual `fly deploy` |
| **Node version (new)** | **Node 22 LTS** pinned in `.nvmrc` and in the static host's build setting; CI uses the same | Node exists **only at build time** (the frontend is a static export), so this is a build-supply-chain pin rather than a production runtime. Still a patching stream (§4) |
| Direct Python dependencies | Declared in `pyproject.toml` with a **compatible-release lower bound and a ceiling** (e.g. `sqlalchemy>=2.0,<3.0`). **For the 0.x packages the ceiling is a *minor* bound** (e.g. `fastapi>=0.118,<0.120`, `starlette` likewise via FastAPI) | Patch/minor security updates flow; majors never arrive unannounced. **0.x libraries break in minors (R12)**, so they get a tighter ceiling — a rev-4 addition |
| **Direct npm dependencies (new)** | **Exact versions, no `^` and no `~`** (`"next": "15.x.y"`), including dev dependencies | The npm default (`^`) means a fresh `npm install` can silently change dozens of packages. Exact versions plus the lockfile make every change a reviewable diff |
| Full resolved Python tree | **`uv.lock` committed**; `uv sync --frozen` in CI and in the platform build command | Byte-identical installs; a lockfile diff is a reviewable event |
| **Full resolved npm tree (new)** | **`package-lock.json` committed**; **`npm ci`** in CI and in the static host's build command — **never `npm install`** | `npm install` mutates the lockfile and can resolve differently; `npm ci` fails if the lockfile and `package.json` disagree |
| Tooling versions | `uv` pinned by exact version in the CI workflow **and in the image build** (`pip install uv==<version>` inside the Dockerfile; rev 5 pinned it in the Render build command) | The build tool is part of the supply chain |
| **Container image (new in rev 5.1)** | Base image **pinned by digest**, not by tag; no `:latest` anywhere; the deployed artefact is the image `fly deploy` built from the reviewed commit | A moving tag is an unpinned dependency with root in the container. Digest pinning makes a base-image change a **reviewable diff** with a named owner |
| GitHub Actions | Third-party actions pinned by **full commit SHA**, never by tag or branch (sec F9) | A moved tag is a supply-chain compromise of CI |
| **Frontend assets** | Everything is **bundled at build time from the lockfile** and served from our own origin with content-hashed filenames; **no CDN reference, no `<script src>` to a third party, no remote font** | No third-party origin on a page handling citizen data (NFR-009). The trust shift is to **build time**, which is what §6's npm controls cover |
| Vendored data assets | Django's BSD-3-licensed `common-passwords.txt.gz` (if adopted — see §5) committed with the version, source URL and licence recorded next to it | It is a licensed artefact, not a dependency, and must be attributable |
| Database schema | Alembic revisions committed alongside the code that needs them; `alembic check` in CI | Deploy = code + schema together, and drift fails the build |

Not allowed: unpinned/floating versions in either ecosystem, `git+https://` or URL dependencies,
local wheels or tarballs of unknown provenance, `--pre`/pre-release installs in any environment,
`npm install` in CI or on a build host, or editing either lockfile by hand.

---

## 3. Dependency budget

| Bucket | Budget | Expected at launch |
|---|---|---|
| Direct **Python runtime** dependencies | ≤ 10 (unchanged) | **8** (was 4 in rev 3) |
| Direct **Python dev** dependencies | ≤ 12 | **7** (was 8) |
| **Direct npm runtime dependencies** | ≤ **6** *(new)* | **3** — `next`, `react`, `react-dom` |
| **Direct npm dev dependencies** | ≤ **12** *(new)* | **10** (rev 5 adds `openapi-typescript` — arch F7; budget holds, no ADR needed) |
| Total resolved **Python** packages | ≤ **70** (was 60) | ~50–60 (`pip-audit` alone accounts for ~20 dev-only transitives) |
| **Total resolved npm packages** | ≤ **600** *(new)* | **~350–450** |
| JavaScript/npm packages | ~~**0**~~ **— budget withdrawn** | Rev 3's zero is **not achievable under H4** and is retired rather than quietly missed. The replacement is the two rows above plus the §6 controls |
| External network services in the request path | **0** | 0 |
| Third-party processors of citizen data (any path) | **0** | 0 |
| **Third-party origins loaded by the browser at runtime** | **0** *(new, and the honest replacement for "0 npm")* | 0 — every package is bundled and self-hosted; no CDN, no font, no analytics, no beacon |
| Billable infrastructure components | ≤ 2 | 2 (API web service + Postgres; the static site is free) |

Breaching a budget is allowed only with an ADR that names the requirement and the alternative
rejected. The budget exists because of **D3** (nobody owns ongoing patching) — every dependency is a
future security bulletin someone has to read. **Say the uncomfortable thing plainly:** going from
**0** to **~400** npm packages is the largest single increase in this project's attack surface, it is
the direct content of human decision H4, and the budget rows above **manage** it rather than
mitigate it away. Risk **R16** in `tech-stack.md` states that the residual risk is not fully
mitigated.

---

## 4. Updating

**Ownership — RESOLVED at GATE_2 (2026-09-09).** Rev 1 assigned every row below to "whoever holds the
repo"; the requirements named no such person (D3), so rev 3–5 marked the rows **UNASSIGNED — GATE_2
question 6**. **The human has now answered: "Q6: I own patching and backups; I hold the backup key."**

> **Owner: the human (GATE_2, 2026-09-09)** — for every row below that is not marked **Platform** or
> **Automated**. **There is no UNASSIGNED row left in this document.** The SLAs below may now be
> claimed in /release, against the time budget `tech-stack.md` § Ops ownership costed
> (~20 min/security release ⇒ ≈1–2 h/year for the two promotions; ~1.5–2 h/quarter batched).
> The "what degrades if the answer is nobody" section of `tech-stack.md` § Ops ownership is
> **not applicable** and is retained only as a historical record.

**Three patching streams now (rev 5.1).** Rev 3 had one; H3/H4 created two; **Q1's Fly.io Mumbai swap
adds a third.** **(a) Python** — FastAPI, Starlette, Pydantic, SQLAlchemy, Alembic, psycopg,
argon2-cffi, gunicorn, uvicorn, uvicorn-worker; **(b) frontend** — Next.js, React, TypeScript, the
~350–450-package npm tree, and Node 22 LTS on the build host; **(c) the `python:3.13-slim` base
image** — ours because Fly deploys images. All three are automated for *detection*, but there are
**three release cadences to watch, two lockfiles plus one image digest to keep green, and two
deployables to promote.**

| Trigger | Response | Owner |
|---|---|---|
| **Dependabot *security* PR, patch/minor, in either ecosystem** | **Auto-merged to `main` when CI is green** (both jobs). **Narrowed in rev 4 (sec F25): only version bumps of packages already present in `uv.lock`/`package-lock.json`** — never a package new to the lockfile, never a major. Requires **no required human review** on `main` (arch F2) — a bot cannot satisfy one. **Narrowed again in rev 5 (sec F7): for the `npm` ecosystem the target version must have been published for ≥7 days** (`cooldown`/minimum-release-age in `dependabot.yml`, enforced again by the merge condition), so our automation cannot be the thing that installs a compromised release on publication day. **PyPI keeps the same-day rule** (8 direct packages, all top-tier, human-reviewable). The accepted cost is stated: a genuine npm security fix lands in `main` up to a week later, `npm audit` reports it the whole time, and a human may merge sooner deliberately | **Automated** |
| **Promoting a deploy after a security merge (arch F1) — now *two* promotions** | **"Merged" is not "deployed."** Auto-deploy is OFF on **both** the API and the static site, so patched code sits in `main` while **production keeps running the vulnerable version** — with the repo, both lockfiles, Dependabot and CI all reading green. Someone must promote **the API, then the static site**, and confirm the release command ran. **~20 minutes per security release** (up from ~15: two dashboards), **≈1–2 hours/year**. A frontend security merge that only the API gets promoted for leaves the vulnerable bundle live on the CDN | **Owner: the human (GATE_2, 2026-09-09)** |
| **FastAPI / Starlette / Pydantic security release** | Arrives as the row above; target **within 7 days** of the advisory. **0.x with no LTS (R12)**, so read the release notes: a security *patch* can carry a behaviour change | Automated; escalation **Owner: the human (GATE_2, 2026-09-09)** |
| **Next.js / React security release** | Same, and Next.js ships them on its own schedule. **`npm audit --audit-level=high` in CI** is the second detector | Automated; escalation **Owner: the human (GATE_2, 2026-09-09)** |
| High/critical `pip-audit` **or** `npm audit` finding with **no fix available** | Document a mitigating control or accept the risk in writing; may require a code change. For a *transitive* npm finding, check whether the path is even reachable from our bundle before panicking — and record the reasoning | **Owner: the human (GATE_2, 2026-09-09)** |
| **Medium/low findings, either ecosystem** | Reported by every CI run but do **not** fail the build; folded into the 30-day batch below (sec F14) | Automated report; batch **Owner: the human (GATE_2, 2026-09-09)** |
| Routine minor/patch updates | Batched ~monthly (30-day window): `uv lock --upgrade` **and** `npm update` within the exact-version policy (i.e. a deliberate bump of the pinned versions), full CI, then **two** human-promoted deploys | **Owner: the human (GATE_2, 2026-09-09)** |
| **Major version bumps** (Pydantic, SQLAlchemy, **Next.js**, React) | Deliberate, planned work with its own branch and an ADR; **never auto-merged**. **Next.js majors are roughly annual and involve real migration work** — this is the rev-4 replacement for rev 3's single dated Django-EOL item | **Owner: the human (GATE_2, 2026-09-09)** |
| **Node 22 LTS security releases** | Bump `.nvmrc` and the host's build setting; CI proves the build. Node is **build-time only** (static export), so the exposure is the supply chain, not production | **Owner: the human (GATE_2, 2026-09-09)** |
| OS / runtime image patches | **Split in rev 5.1 (Q1).** Fly patches the **host** and the **Managed Postgres** instance; Render patches the static site's build image. **The `python:3.13-slim` base image inside our container is ours:** digest-pinned `FROM`, Dependabot `docker` ecosystem, **monthly scheduled CI rebuild** running the full suite, digest bump via reviewed PR (**never auto-merged**), then a manual `fly deploy`. This is the obligation arch F2 refused to accept while it was unowned | **Platform** (host, DB, static build image) + **Owner: the human (GATE_2, 2026-09-09)** (base image) |
| TLS certificates | **Platform** (both the API host and the static host) | **Platform** |
| Database patches and daily backups | **Platform** (managed Postgres) | **Platform** |
| Backup **restore verification** and the encrypted off-platform copy | Go-live restore test into a throwaway platform DB, destroyed afterwards, with evidence. The monthly encrypted `pg_dump` (a **Fly scheduled machine** in rev 5.1) is **ENABLED**: condition (a) is met — **Q6, "I hold the backup key"** — and condition (b), **the destination, is TBD (human to name at /release)** with its own scoped credential and an automatic ~90-day expiry rule. Until the destination exists the dump does not run, but it is **no longer dropped** (sec F18's "either is missing ⇒ drop it" no longer applies, since only the destination remains). No manual-download substitute (arch F5) | **Owner: the human (GATE_2, 2026-09-09)** — holder of the encryption key by his own statement; **destination still to be named** |
| Python minor version (3.13 → 3.14) | Only when the dependency set officially supports it; not chased | **Owner: the human (GATE_2, 2026-09-09)** |
| ~~Django 5.2 end of support — April 2028~~ | **Retired by H3** — there is no Django and no LTS deadline. Replaced by the continuous obligation in the two "major version bumps" and "0.x" rows above. A dated cliff traded for a steady trickle; record "who upgrades Next.js and FastAPI" as the handover item instead | — |

Rules: never update a dependency and change application behaviour in the same commit; every update
lands via CI with the run cited as evidence; a lockfile change with no manifest change is a
legitimate PR and should say what moved and why; auto-merge applies **only** to Dependabot security
PRs that are patch/minor bumps of already-present packages with all checks green.

**Branch protection — stated once (arch F2 + arch F3 / sec F25), identically in
`tech-stack.md` § Hosting and `technology-comparison.md` Layer 8.3:** `main` requires
**a pull request before merging (no direct pushes)**, **green required checks**, **linear history**,
**no force-push** and **no deletion** — and **does *not* require a human review.** Rev 2 asked for
both a required review and bot auto-merge; those cannot both hold, and the required review would
have silently blocked every security auto-merge. Rev 3 took option (b) but left direct pushes
possible; **rev 4 closes that** at zero cost to the bot, since Dependabot opens PRs anyway. What
replaces a required review: CI as the gate (both jobs), **two human promotion steps for every
production deploy**, and **two-eyes retained specifically for new dependency additions in either
ecosystem** (§6) — the place where supply-chain risk actually enters. Major version bumps still get
their own branch and an ADR, which is a human decision by construction.

---

## 5. Licence policy

| Class | Licences | Action |
|---|---|---|
| **Allowed** | MIT, BSD-2/3-Clause, Apache-2.0, ISC, PSF, MPL-2.0 (as an unmodified library) | Use freely |
| **Review required** | **LGPL-2.1/3.0** | Only as an **unmodified, dynamically imported library**, recorded in an ADR; prefer an alternative where one exists |
| **Forbidden** | GPL-2.0/3.0 (for linked libraries), AGPL-3.0, SSPL, BUSL, Elastic Licence, "source-available"/non-OSI, any licence with a field-of-use or user-count restriction | Do not add |
| **Unclear or missing** | No `LICENSE` file, or conflicting metadata | Treat as forbidden |

**Correction of an inherited error (rev 4).** Rev 3 stated that "the whole stack as recommended is
BSD/MIT/Apache/PSF, so there is currently nothing in the review or forbidden classes." **That was
wrong, and it was wrong in rev 3 too:** **`psycopg` 3 is licensed LGPL-3.0** (psycopg2 was LGPL with
an OpenSSL exception; psycopg3 is LGPL-3.0). It has been in the recommended stack since rev 1. The
correct handling under our own policy:
- It sits in the **"review required"** class and is **recorded here as the ADR entry**.
- We use it **unmodified**, installed from PyPI, **imported dynamically** at runtime, and we
  distribute no derivative work of it. Under LGPL-3.0 that is the intended usage pattern and imposes
  no obligation on our application code.
- We **do not** vendor, patch or statically link it. If that ever changes, this row must be revisited
  before the change merges.
- Alternative if a reviewer or the panchayat's IT contact objects: `pg8000` (BSD-3, pure Python) or
  `psycopg2-binary` (LGPL + exception) — both would work, both are slower or older, and neither is
  needed unless the licence class is a hard blocker for the customer.
This is exactly the kind of thing a licence inventory is supposed to catch, and it is recorded rather
than quietly fixed.

**Everything else in the recommended stack is MIT/BSD-3/Apache-2.0/PSF**, in both ecosystems
(`fastapi`, `sqlalchemy`, `alembic`, `argon2-cffi`, `gunicorn`, `uvicorn-worker`, `next`, `react`,
`react-dom`, `typescript`, `@biomejs/biome`, `vitest`, `jsdom`, `@testing-library/react`,
`openapi-typescript` — MIT or
BSD; `uvicorn` — BSD-3).

**Vendored assets (new row in rev 4).** If the common-password check is implemented, the word list is
**Django's `common-passwords.txt.gz` (BSD-3-Clause)**, committed with its source URL, version and the
Django licence text alongside it, and attributed in the licence inventory. It is a **licensed
artefact, not a dependency** — it needs attribution, not patching. If the human prefers no vendored
data file, the check is dropped and `tech-stack.md` says so rather than leaving a silent gap.

**npm licences (new).** A ~400-package tree cannot be eyeballed. Policy: the **direct** dependencies
are checked individually (all MIT above), and the **transitive** tree is checked mechanically — a
licence-inventory step at /release (`npm ls --all --json` plus a licence report) that **fails on any
licence in the forbidden class**. That is the honest limit of what is checkable at this scale, and it
is stated rather than implied.

A **licence inventory** covering both ecosystems (`uv tree` + npm licence report, with the licence
field per package, plus the vendored-asset row) is generated at /release and attached to the
handover, so a future maintainer or a panchayat/state IT reviewer can answer "what is in this and can
we use it" without archaeology. AGPL matters here specifically because this is government-adjacent
software that may later be shared with other panchayats (Future scope).

---

## 6. Auditing and supply-chain posture

**In CI, on every push and PR — API job:**
1. `uv sync --frozen` — fails if the lockfile and `pyproject.toml` disagree.
2. `uv run ruff check .` including the `S` (flake8-bandit) security rules, and `ruff format --check`.
3. `uv run mypy <app_package>` — **the application package only**, not `.`. Exact path set in /plan.
4. `uv run pytest` against a real Postgres service container, then **`alembic upgrade head` from the
   previous revision** and **`alembic check`** — the compensating control for having no staging
   environment (arch F5) plus a model/migration drift gate.
5. `uv run pip-audit` — **reports every severity** in the resolved tree, **fails the build on high or
   critical**, and routes medium/low findings into the 30-day batch in §4 (sec F14). Rationale
   unchanged: a build that fails on a medium in a dev-only dependency trains people to bypass the
   gate; a build that never mentions mediums hides them.
6. **`uv run selfcheck`** with production-shaped environment variables — must pass. **This is the
   replacement for `manage.py check --deploy`** and it catches insecure cookie flags, `DEBUG=True`,
   a missing `TRUSTED_PROXY_HOPS`, a missing `sslmode=require`, an empty or `*` allowed-hosts list,
   `allow_origins=["*"]` with credentials, and exposed OpenAPI docs before they reach production.

**In CI, on every push and PR — frontend job:**
7. `npm ci` — fails if `package-lock.json` and `package.json` disagree.
8. `npx biome ci .` — lint + format check.
9. `npx tsc --noEmit` — typecheck.
10. `npx vitest run` — component tests.
11. `npm run build` — **with a first-load-JS size gate on the public route** (Conflict C8): the build
    fails if the public lookup route exceeds the agreed gzipped budget. A performance requirement
    that is not gated in CI is a performance requirement that regresses.
12. `npm audit --audit-level=high` — fails on high/critical; mediums batched as above.
13. **`npm audit signatures` (new in rev 5 — sec F7)** — verifies the registry signatures /
    provenance attestations of the installed tree, so a tampered tarball or an unsigned substitute
    for a package we think we pinned fails CI. Cheap, no dependency, no account.
14. **The CSP inline-script hashing step and the size gate** (`tech-stack.md` H-C, C8) run in the
    same job, so a build whose CSP cannot be generated does not produce a deployable artefact.

**What none of the above detects, stated plainly (sec F7):** a **zero-day malicious release of a
package we already trust**. `npm audit`/`pip-audit` need an advisory to exist; signature verification
proves *who published*, not *what they published*; the lockfile proves *what we installed*, not that
it is benign; and the 7-day npm cooldown only buys the time in which someone else usually notices.
This is the honest limit of the posture, it is why **R16's residual is "not fully mitigated"**, and it
is why the containment controls in `tech-stack.md` (CSP `connect-src`, the idle window, response
minimisation) matter more than the prevention controls here.

**E2E job (PRs to `main` and before a release):** the exported frontend served locally + the
`live_server` API fixture + Playwright, including the security assertions that can only be made
against a real browser and a real deployed preview (static-site headers, the CSP).

**Workflow hardening (sec F9):** third-party actions pinned by full commit SHA; workflow-level
`permissions: contents: read`, raised per-job only where genuinely required; `pull_request_target`
not used; **no secrets available to fork-PR workflows**; **no deploy job and no platform deploy
credential in CI at all** — production promotion is a human dashboard action, twice. `main` is
protected as stated in §4.

**Monthly, on a schedule:** re-run `pip-audit` **and** `npm audit` against current advisory
databases, and review any Dependabot PR that did not auto-merge. No image rebuild (arch F2).

**Posture rules:**
- **PyPI and the public npm registry only.** No alternative or private indexes, no
  `--extra-index-url`, no `--find-links`, no `.npmrc` registry overrides, no tarball or git
  dependencies.
- **Typosquat check on every addition, in both ecosystems.** Confirm the exact project name and its
  repository URL against the official documentation — not a search-engine result and **not an AI
  suggestion**. Hallucinated or near-miss package names are a live attack vector, and npm is where it
  is most active.
- **Prefer wheels / prebuilt.** A package that must compile from source on the build host gets extra
  scrutiny; `psycopg[binary]` and Next.js's SWC binaries are the deliberate exceptions.
- **Read the release notes for major bumps** — and for 0.x minors (R12). A green test suite is not a
  substitute.
- **Two-eyes on new dependencies — and *only* on new dependencies (arch F2), now covering npm.** A
  dependency addition (a new entry in `pyproject.toml` or `package.json`, **or a lockfile diff
  introducing a package nobody asked for, in either lockfile**) is never approved by its own author;
  it needs a second pair of eyes and an FR/NFR/BR/AC citation per §1. This is the **one place
  two-eyes survives** after required PR reviews were dropped from `main` (§4): it is a supply-chain
  decision, not a routine merge, and it is the class of change a green CI run cannot judge.
- **Lockfile diffs are reviewed, not rubber-stamped** — with the honest caveat that a Next.js minor
  bump can move dozens of transitive packages. The reviewable question in that case is "is this the
  upstream's own release, at the version Dependabot claims?", not "do I recognise all forty of
  these".
- **What is *not* individually reviewable, stated plainly:** the ~350–450 resolved npm packages. They
  are covered by the lockfile, exact pinning, `npm ci --ignore-scripts`, `npm audit` +
  `npm audit signatures`, Dependabot with the 7-day npm cooldown, the direct-dependency budget, the
  no-runtime-third-party-origin rule and the mechanical licence gate — **not** by human reading.
- **And what the controls do not bound, worded as in `tech-stack.md` R16 (H-B/sec F2):** if one of
  those packages is malicious, it runs **inside the authenticated clerk page**. The `httpOnly`
  session cookie prevents **theft of a reusable token** — it does **not** prevent **use of the
  session from the page**: the package can read the CSRF token from our own JSON and act with the
  **full capability of the signed-in clerk** (all citizen name/phone data that clerk may see, and
  **every one-time password issued while the page is open**). The bounding controls are **CSP
  `connect-src`/`img-src`** (which does **not** stop top-level-navigation exfiltration), the
  **30–60 min idle window**, and **response minimisation** (every route declares a `response_model`;
  the clerk list response carries no `name`/`phone`). Risk **R16** says exactly this, and the ADR
  must not soften it into a cookie-flag claim.
- **Secrets never enter the dependency chain.** No credentials in `pyproject.toml`, `package.json`,
  migrations, fixtures, test files or CI logs. GitHub secret scanning and push protection enabled.
  **New in rev 4:** anything in the frontend build environment prefixed `NEXT_PUBLIC_` is **compiled
  into the browser bundle and is public by construction** — only `NEXT_PUBLIC_API_BASE_URL` may use
  it, and a /build review item checks that no other variable does. The FR-015 bootstrap **prompts
  interactively on stdin**, so in the normal case **no admin credential exists as an environment
  variable at all**; it is deliberately **not** a data migration. If the `--from-env` fallback is
  used, `BOOTSTRAP_ADMIN_PASSWORD` must be **deleted from the platform environment immediately
  afterwards**, with that deletion and the resulting `must_change_password=True` both evidenced on
  the /release checklist.
- **Test fixtures use synthetic data only** — invented names and phone numbers, never a real citizen
  record (NFR-008, NFR-009). This now includes frontend test fixtures and any mocked API response.
- **Production data never leaves production (sec F8).** No production database dump, table export,
  screenshot of real records or copy/paste of complaint text may be loaded into a development
  machine, a CI run, a test fixture, a bug report, an issue tracker, or **any AI/LLM tool**
  (including the agents building this system). Debugging uses synthetic data reproducing the shape of
  the problem. The only sanctioned movement of production data is (a) the platform's own backups and
  (b) **if it exists at all**, the **encrypted** off-platform `pg_dump` described in `tech-stack.md`
  § Database — which is **conditional**, not assumed: it exists only if **(a)** a named person holds
  the private decryption key **and (b)** a named destination exists with its own narrowly scoped
  credential and an **automatic lifecycle/expiry rule** (≈90 days). If either is missing, **the dump
  is dropped from the design and the ~$1/mo cron is not offered** — platform daily backups become the
  only mechanism. There is **no** "manual monthly download" fallback (arch F5). Restore tests target
  a **throwaway platform database destroyed immediately afterwards**, never a laptop and never a
  shared dev database.

---

## 7. Explicitly out — do not add these

Each entry is a decision, not an oversight. Adding one requires an ADR that names the requirement
forcing it.

| Not adding | Why |
|---|---|
| **Any AI/LLM SDK** — Python (`openai`, `anthropic`, `langchain`, `llama-index`, transformers) **or npm** (`ai`, `@ai-sdk/*`, any client-side model) | No requirement needs generation, classification, summarisation or fuzzy search; **BR-004 forbids** partial/"did you mean" matching. Also fights NFR-006 (cost), NFR-001 (latency — already tight after C8) and NFR-008/009 (a new PII processor). H4 creates a *frontend* place to add one, so the ban is stated for both ecosystems. See `tech-stack.md` § AI/LLM decision. |
| **Vector database / embedding libraries** | No semantic search requirement exists. |
| **Celery / RQ / any task queue, and Redis/Valkey** | Nothing is asynchronous in the MVP; NFR-010 forbids an automatic deletion job. The rate-limit counter is an **atomic Postgres upsert**, so no shared cache service is needed. Redis remains costed at ~$10/mo for the day load exceeds ~50 rps — which no driver predicts. |
| **`slowapi` / `fastapi-limiter` / any cache-backed limiter package** | Their correctness depends on a storage backend we do not have (in-memory is per-worker; Redis is a rejected component). This is rev 2's `django-ratelimit` finding in a new ecosystem — see §1. AC-011 must be provable under **parallel** requests. |
| **`passlib`** | Unmaintained since 2020 and its `crypt` backends target a module removed in Python 3.13. `argon2-cffi` instead. |
| **Any async ORM / driver (`asyncpg`, Tortoise, Piccolo) while handlers stay sync** | The execution model is sync by decision (`tech-stack.md` § Language & backend framework); mixing them is how a blocking call ends up on an event loop. |
| **A second ORM, query builder or migration tool** | SQLAlchemy + Alembic are already chosen; two schema authorities is how audit tables get out of sync (FR-011/FR-014). |
| **Error-tracking / APM SaaS** (`sentry-sdk`, Rollbar, Datadog, New Relic) **and any frontend RUM/session-replay** | `send_default_pii=False` plus a field scrubber does not prevent **local-variable capture**, so citizen name/phone can reach a third party from a traceback frame; and it is an account nobody owns after launch (D3). A *frontend* tracker would additionally be a third-party script on a page handling citizen data. Platform logs + a free `/healthz` pinger + the `security_event` table cover NFR-007. The hardened Sentry recipe is pre-approved **if GATE_2 question 6 names an ops owner**, with its compensating test. |
| **Analytics / tag managers** (GA, Hotjar, PostHog snippets, Vercel Analytics) | Third-party scripts on a page handling citizen data conflict with NFR-008/NFR-009. If usage counts are ever needed, count server-side. |
| **CDN-hosted scripts, fonts or stylesheets** | Same reason; also an availability dependency inside the NFR-001 budget. Self-host and bundle everything. |
| **`next-auth` / `@auth/core` / any client-side auth library** | Auth is the API's job; BR-016's on-screen one-time password does not fit an email-centric provider library; and the client deliberately holds no readable credential — only an `httpOnly` cookie. |
| **A client-side state library** (`redux`, `zustand`, `@tanstack/react-query`) | Six screens and one `fetch` helper with `AbortController` (which NFR-011 requires anyway). Revisit only if /ux produces something genuinely stateful. |
| **CSS frameworks / component / icon libraries / `next/font`** | Hand-written CSS is ~4–8 KB for ~6 screens, and **Conflict C8** makes every kilobyte on the public route contested. |
| **Auth SaaS SDKs** (Auth0, Clerk, Firebase, Supabase) | BR-016's "password shown once on screen, handed over verbally" cannot be expressed in an email-centric product, and ≤6 accounts make per-MAU pricing pure cost. |
| **SMS/WhatsApp gateway SDKs** (Twilio, Gupshup, MSG91) | Explicitly excluded from the MVP by intake; Future scope. |
| **Object storage / image-processing libraries** (`boto3`, `Pillow`, `sharp`) | No attachments in the MVP (Future scope, and pushed back in Scope challenges). |
| **Kubernetes, Helm, Terraform, service meshes** | One API service, one database and a static site. Operational surface must shrink, not grow (D3). |
| **GraphQL, or a second API style** | One JSON API with explicit response models serves every FR; a second surface is a second place to leak `name`/`phone` (NFR-004/BR-010, R15). |
| **`python-dotenv`, `pydantic-settings`, `django-environ` and similar** | `os.environ` plus a small typed settings module is sufficient. One dependency saved, one fewer place a secret can be read from a file. |
| **`typer` / `click`** | Two console scripts, ~40 lines of `argparse`. +2 packages for convenience is not a trade we make under D3. |
| **`itsdangerous` / cookie-session middleware** | Sessions are server-side rows, because BR-016 and sec F20 require revocation. |
| **CAPTCHA / bot-detection services** | Q-013 explicitly keeps CAPTCHA out of the MVP; the rate limiter is the chosen control (NFR-005). |
| **A logging/metrics stack** (Grafana, Loki, Prometheus, OpenTelemetry collectors) | stdout logs captured by the platform + a free uptime pinger on a DB-checking `/healthz` + the `security_event` table already satisfy NFR-007's mechanism at $0, with no account and no owner required. |
| **`pyotp` / TOTP** | *Not rejected — offered.* No requirement asks for MFA (NFR-003 is username+password), and it adds a lockout mode to an office with one admin clerk. Costed for the human in `tech-stack.md` (MIT, +1 dependency, ~0.5–1 day, $0/mo) for the admin clerk only; add it only on the human's word (sec F14). |
| ~~`django.contrib.admin`, `django-ratelimit`, `django-csp`, `django-otp`, `argon2-cffi` as "optional"~~ | **Rows retired by H3** — there is no Django. Their *reasoning* survives where it still applies: the "no unnecessary admin surface" argument is now **OpenAPI docs disabled in production with a `/docs` → 404 test**; the "static CSP needs no package" argument is now ~20 lines of Starlette middleware plus committed static-host headers; and `argon2-cffi` moved from "optional, not adopted" to **required**, because H3 removed the framework hasher it was an alternative to. |

---

## 8. Review triggers for this document

**Four triggers fired at GATE_2 (2026-09-09) and are now applied rather than pending:**
**(1) India data residency (Q1)** — the Dockerfile exists, so **§2's base-image row and §4's
OS-patching row are back, with a named owner**; **(2) an ops owner is named (Q6)** — **§4's
UNASSIGNED rows now say "Owner: the human (GATE_2, 2026-09-09)"** and the hardened Sentry recipe
became *adoptable* (still **not adopted**: the D5 argument against a third-party PII processor does
not depend on ownership); **(3) the no-JS public page (Q8)** — answered "confirmed, public page may
require JavaScript", so the public route **stays** Next.js and the npm surface does not shrink;
**(4) SSR (Q2)** — answered "no SSR", so no production Node runtime is added.

Revisit this strategy if any of the following happens: attachments or SMS notifications are pulled
out of Future scope; multi-panchayat support is approved; **the human later asks for SSR/ISR** (which
adds a **production Node runtime** and a fourth patching stream — §4 and `tech-stack.md` § Ops
ownership both change); **the residency rule is read to cover static assets** (then the frontend
moves to a Fly static machine in `bom`, +$2–5/mo, and Render leaves the vendor list);
**the named owner steps away without a replacement** (then §4's rows are unowned again and
`tech-stack.md` § Ops ownership's retained "if nobody" list becomes live);
**the CSP inline-script hashing spike fails** (then `script-src 'self' 'unsafe-inline'` is accepted as
a recorded weakening and R16's residual widens — `tech-stack.md` H-C fallback (c)); **a single
registrable domain cannot be attached to both hosts** (then the auth model becomes a BFF proxy — a
production Node runtime and a third patching stream — and returns to GATE_2, sec F6);
a **Next.js or Pydantic/SQLAlchemy major** is released; a dependency budget is breached; load grows
enough to justify Redis; or `pip-audit`/`npm audit` reports an unfixable high/critical advisory in a
direct dependency.
