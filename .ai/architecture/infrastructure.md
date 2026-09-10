# Infrastructure & Deployment Architecture

rev 3 (2026-09-09). Binding: ADR-006 (managed Postgres 17), ADR-009 (Fly.io `bom` + Render Static
Site, human-only deploys, no staging), ADR-010 (CI, supply chain). Drivers: AD-4 scale, AD-5 cost,
AD-6 one part-time ops owner, AD-7 office-hours 99%, AD-10 residency.

## 1. Topology

| Component | Provider / plan | Region | Cost/mo |
|-----------|-----------------|--------|---------|
| API | Fly Machine `shared-cpu-1x`, 512 MB, `min_machines_running = 1` (no scale-to-zero) | `bom` (Mumbai) | $3–5 |
| Database | Fly Managed Postgres 17, smallest plan | `bom` | $7–9 |
| Frontend | Render Static Site (free tier): build + global CDN + TLS + custom domain | CDN | $0 |
| Domain | one registrable `.in` | — | ~$1 |
| Encrypted monthly dump (dormant) | Fly scheduled machine → destination TBD | `bom` → TBD | $0–1 |
| **Total** | | | **≈$11–16/mo** (inside the ≤$16 envelope, AD-5) |

**24-month total (rev 2, cost-F2): ≈$265–385**, i.e. 24 × $11–16 plus the one-off domain years
already counted in the monthly line. Stated so the human sees the number a pilot is actually
committing to, not just a monthly figure. Nothing in the design has a usage-priced component, so the
range does not widen with traffic at AD-4 scale; the only step change is Postgres plan size.

**Two figures are unverified and are /release gates, not assumptions (rev 2, PERF-F1 / cost-F1).**
**Max connections** — measured before go-live with `SHOW max_connections` and `pg_stat_activity`
under the real deploy; if the usable limit is **<25**, run **`--workers 1`** (10 connections, plus
release-command and `psql` headroom), which costs nothing measurable at <1 rps, improves memory
headroom, halves the 8-concurrent-hash burst figure to 4, and means §10's arithmetic is re-recorded.
**Verified price** — read from the actual plan page at signup; if it pushes the monthly total
**above $16** this is *not* absorbed silently, it returns to **GATE_2 for human sign-off** with two
priced options: accept a higher envelope, or move to the next cheapest in-region managed Postgres.

Also verify at signup and record in /release: backup retention days, encryption at rest for instance
and backups, egress allowance, published CA certificate for `sslmode=verify-full` (SEC-F11), platform
log retention (OQ-10), and that the machine *and* the cluster are actually in `bom`.

## 2. DNS, domain and TLS

| Name | Target | Notes |
|------|--------|-------|
| `<domain>.in`, `www.<domain>.in` | Render Static Site | apex + www; one canonical, the other redirects |
| `api.<domain>.in` | Fly Machine | the only origin the browser calls with credentials |

One registrable domain across both vendors is a **hard requirement** of the cookie design
(ADR-007): it is what lets a `SameSite=Lax` `__Host-` cookie ride cross-origin/same-site requests.
The custom domain must be attached to **both** hosts before any real citizen data is entered
(/release gate). TLS certificates are issued and renewed by each platform; no certificate is ours.
`SameSite=None` is forbidden; if a single registrable domain is impossible the design returns to
GATE_2 for a BFF proxy, it is not patched.

## 3. Container image

```dockerfile
# outline; exact content is /plan's
FROM python:3.13-slim@sha256:<digest>          # digest-pinned, Dependabot 'docker' ecosystem
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN adduser --system --no-create-home appuser
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv==<pinned> && uv sync --frozen --no-dev   # no build toolchain left in the layer
COPY app ./app
COPY migrations ./migrations
USER appuser
EXPOSE 8080
CMD ["uv","run","gunicorn","app.main:app","--worker-class","app.worker.RawPeerWorker", \
     "--workers","2","--timeout","30","--graceful-timeout","30","--keep-alive","5", \
     "--max-requests","1000","--max-requests-jitter","100","--bind","0.0.0.0:8080", \
     "--access-logfile","-","--error-logfile","-"]
```

**The worker class is the security control (rev 4, SEC-F1/ADR-023 rewritten).** Rev 3 said "pass
neither `--proxy-headers` nor `--forwarded-allow-ips`". That does not work, and the reason matters:
**gunicorn has no `--proxy-headers` option at all**, and with the stock
`uvicorn_worker.UvicornWorker` uvicorn's `Config.proxy_headers` defaults to **True** while gunicorn
passes its own `forwarded_allow_ips` (default `127.0.0.1`, overridable by the **`FORWARDED_ALLOW_IPS`
environment variable**) into that config — so `ProxyHeadersMiddleware` is installed and rewrites
`scope["client"]` from `X-Forwarded-For` before the application runs, exactly the failure rev 3
thought it had removed. The fix is in the repo, not the command line:

```python
# app/worker.py — outline; exact content is /plan's
from uvicorn_worker import UvicornWorker

class RawPeerWorker(UvicornWorker):
    CONFIG_KWARGS = {"proxy_headers": False, "forwarded_allow_ips": []}
```

With that worker, `scope["client"][0]` is the raw TCP peer the peer-first client-IP rule (backend §5)
depends on, and `core/client_ip.py` is the sole interpreter of `Fly-Client-IP` and `X-Forwarded-For`
(`X-Forwarded-Proto` has no consumer — grep block-list only). `selfcheck` asserts the **behaviour** —
effective `proxy_headers is False`, no `ProxyHeadersMiddleware` in the built stack,
`FORWARDED_ALLOW_IPS` unset — because an argv grep tests for a string that was never going to be
there. SEC-T21 runs a real process started with this CMD and asserts the limiter key **value**.
The only side effect is that `request.url.scheme` is `http` inside the container; nothing reads it
(security §5).

> **Action for /plan (this file may not change it):** `.claude/project-config.md`'s `start:` command
> must be updated to `--worker-class app.worker.RawPeerWorker` and must **drop**
> `--proxy-headers --forwarded-allow-ips` (gunicorn rejects the first outright). `FORWARDED_ALLOW_IPS`
> must not be set in any environment. `selfcheck` will fail the dev server until this is done.

`fly.toml`: `primary_region = "bom"`, `internal_port = 8080`,
`release_command = "uv run alembic upgrade head"`, health check
`GET /healthz` every 15 s (grace 10 s, timeout 2 s, **3 consecutive failures** — §9),
`min_machines_running = 1`.

Base-image patching is the human's obligation (ADR-002 Q6): digest-pinned `FROM`, Dependabot on the
`docker` ecosystem, a **monthly scheduled CI rebuild** that proves the image still builds and tests
green, and the digest bump landing as a reviewed PR.

## 4. Environments

| | dev | test / CI | PR preview | prod |
|---|---|---|---|---|
| API | local uvicorn :8000 | in-process TestClient + `live_server` fixture | — | Fly `bom` machine |
| Frontend | `next dev` :3000 | exported `out/` served with production rewrite + headers | Render preview URL | Render Static Site |
| DB | local Postgres 17 (Docker) | Postgres service container | — | Fly Managed Postgres |
| Data | synthetic | synthetic | none | real |
| Cookies | unprefixed, `Secure=false` | as dev | — | `__Host-`, `Secure` |

**There is no staging** (ADR-009, AD-5). Compensating controls: CI applies `alembic upgrade head`
from the previous revision against real Postgres; `alembic check` gates model/migration drift;
migrations are **additive-only / forward-compatible**; frontend PR previews give a real deployed UI
to look at — and preview origins are deliberately **not** in the API's CORS allow-list, so a preview
can never touch production data. Production data is never copied to dev, CI, fixtures or any AI tool.

## 5. CI/CD pipeline

Runs on every push and PR. No deploy job exists anywhere; no deploy credential exists in CI.

**API job:** `ruff check` → `ruff format --check` → `mypy app` → `pytest` (Postgres service
container, includes the parallel-concurrency specs for AC-003 and AC-011) →
`alembic upgrade head` from the previous revision → `alembic check` → `pip-audit` →
`selfcheck` with production-shaped env → build the digest-pinned image → dump the OpenAPI schema.

**Frontend job:** `npm ci --ignore-scripts` → `biome ci .` → `tsc --noEmit` →
regenerate `openapi-typescript` from the dumped schema and fail if the committed `api-types.ts`
differs → `vitest run` → `next build` with the **first-load-JS gate on `/`** → `npm run gen:csp` →
`npm audit --audit-level=high` → `npm audit signatures`.

**E2E job (PRs to `main` and pre-release):** the exported frontend served with the host's rewrite and
header rules + the `live_server` API + Playwright — login, log a complaint (in-flight + 10 s timeout),
illegal transition, public lookup success/not-found, malformed input, deep-link rewrite, stale-chunk
reload prompt, deployed-CSP assertions.

**Monthly scheduled job:** re-audit both ecosystems, rebuild the base image, run the full suite,
open a PR if the digest moved.

Hardening: all third-party actions SHA-pinned; `permissions: contents: read`; no
`pull_request_target`; no secrets to fork PRs. `main` is protected — require a PR, green checks,
linear history, no force-push, no deletion, **no required human review** (Dependabot auto-merge
would be impossible otherwise); a *new* dependency in either ecosystem still needs two eyes.

## 6. Deploy / promotion procedure (human-only)

1. Confirm the commit is on `main` and CI is green (all three jobs).
2. Prefer a window outside panchayat office hours (single machine, brief restart — R1).
3. **API first:** `fly deploy` from a local checkout of that commit. Fly runs
   `alembic upgrade head` on the new image in a temporary machine **before** shifting traffic and
   **aborts the deploy if it exits non-zero**.
4. Verify: `fly status` shows the machine in `bom` and healthy; `GET /healthz` returns `ok`.
5. **Then the frontend:** promote the build in the Render dashboard (auto-deploy is OFF; turning it
   off is a /release checklist item).
6. Post-deploy smoke: run the production Playwright spec — login → log a complaint → public lookup.
   That result is the evidence the two deployables match.
7. Order matters (R14): the API must stay compatible with the previous frontend, because a citizen's
   cached bundle can be one version behind for minutes. **API changes are additive only** — a rename
   or removal is a two-step deploy.

**Merged ≠ deployed.** Dependabot keeps `main` current while production runs the old image until
step 3 happens. ~20 min per security release, ≈1–2 h/year; owned by the human (ADR-002 Q6). The
/release runbook makes the promotion the closing action of any security merge.

## 7. Rollback

| Failure | Action |
|---------|--------|
| Bad API release | `fly deploy --image <previous digest>` (Fly keeps prior releases addressable) |
| Bad frontend release | redeploy the previous build in Render |
| Both | roll back in reverse order: frontend first, then API |
| Bad migration | it never reaches traffic — the release command aborts the deploy. If a migration succeeded but the code is bad, roll back the image only: additive-only migrations mean the previous code still runs against the new schema |
| Data corruption | restore from backup (§8) — a decision for the human, never automated |

There is no "down" migration path in the deploy flow. Forward-compatibility is what makes
rollback-by-redeploy safe without staging.

## 8. Backup and restore

- **Primary:** Fly Managed Postgres platform backups, daily; retention confirmed at signup (assume ~7 days until verified).
- **Secondary (dormant):** a monthly `pg_dump` **encrypted before it leaves the machine**
  (`pg_dump … | age -r <recipient-public-key> > dump-YYYY-MM.age`) written straight to a named
  destination with its own narrowly scoped credential and an automatic ~90-day lifecycle rule.
  Precondition (a) key holder is met — the human (ADR-002 Q6). Precondition (b) destination is
  **still open (OQ-2)**; until it is named, this does not run. Plaintext dumps never touch disk or a
  laptop.
- **Decision on the dormant copy (rev 2, REL-F4 / SEC-F15).** Go-live is **not** gated on it. Instead
  the gap is a **named accepted residual**: *until a destination is named, every copy of the citizen
  database lives with one vendor (Fly) — a vendor-level account loss, billing termination or
  region-wide data event has no independent recovery path, and history older than the platform's
  retention (~7 days, to be confirmed) does not exist anywhere.* The human accepts that at GATE_5 by
  leaving OQ-2 unanswered; naming a destination retires it for ~$0–1/mo. Threat #28 is recorded as
  **accepted** for the same reason — rev 1 marked it mitigated on the strength of a control that is
  switched off. The /release checklist asks the question once more before real data is entered.
- **Restore test (go-live gate):** restore one dump into a **throwaway** Fly Managed Postgres in
  `bom`, record row counts per table, the newest complaint number present, and the destroy
  confirmation; then destroy it. Repeat at any Postgres major-version change. Never restore into
  dev, CI or a shared database.
- Recovery objectives at pilot scale: **RPO ≈ 24 h** (daily platform backup), **RTO ≈ 2–4 h**
  (human-driven restore + redeploy). Stated so nobody assumes better.

## 9. Health checks and monitoring

| Check | Who | Frequency | On failure |
|-------|-----|-----------|-----------|
| `GET /healthz` — process + `SELECT 1`, **result cached in-process for 10 s** (ARCH-F9: the endpoint is unauthenticated and unlimited, so a flood must not become one query per request), returns bare `ok`/`unavailable`, no version or dependency detail | Fly platform check, `interval 15s`, `timeout 2s`, `grace_period 10s`, **`consecutive_failures = 3`** | 15 s | after 3 consecutive failures (~45 s) the machine is marked unhealthy |
| `GET /healthz` | free external pinger (UptimeRobot / Better Stack) | 5 min | email to a shared office address — the NFR-007 evidence trail |
| Memory | Fly free alert at ~420 MB | continuous | investigate; fallback is `--workers 1` with 8 threadpool tokens |

The threshold is **3 consecutive failures, not 1** (rev 2, REL-F7): with a single machine, a
one-off 2 s timeout during a slow query must not remove the only server from rotation — a flap costs
more availability than the failure it reacts to. Three failures ≈45 s is still well inside the
office-hours 99% budget (AD-7).

**What a client actually sees when the sole machine is unhealthy (rev 2, REL-F3).** There is no
second machine, so "out of rotation" does not mean "requests go elsewhere" — it means the Fly proxy
has no healthy backend and returns a platform-generated `502`/`503`, not our JSON envelope and not
our wording. The public page still *loads* (static, on the CDN) and the fetch wrapper turns that
status into our "temporarily unavailable" state — the genuine gain from the H4 split; the clerk app
behaves the same. **This is an assumption about Fly with zero healthy machines, so it is a /release
verification item (§13): stop the machine, record verbatim what `curl` and the browser receive, and
confirm the frontend renders our error state.** The frontend reads status codes only, so a branded
Fly error page would break nothing — but it gets recorded rather than assumed.

There is no liveness/readiness split: one process, one dependency, one endpoint. Adding a second
endpoint would be complexity without a driver.

## 10. Capacity and limits

2 workers × (6 request connections + 4 limiter connections) = **≤20 Postgres connections**, plus one
or two transient for the release command and an operator `psql`. **This arithmetic is only valid if
the verified Managed Postgres connection limit is ≥25 — §1 makes that a /release gate with
`--workers 1` (≤10 connections) as the recorded fallback.** Memory: ~240–304 MB steady,
peak ≈376 MB during an 8-concurrent-hash login burst, ~136 MB headroom — measured at /test-app, not
trusted. Expected load is <1 rps (AD-4), so the binding constraint is memory, not CPU.

## 11. Runbook outline (expanded at /release)

Deploy · rollback · restore from backup · rotate `SECRET_KEY` (never `USERNAME_HASH_SALT` — R2-11) ·
rotate `DATABASE_URL` · `bootstrap-admin` (first admin) · **`reset-admin-password` (lost admin
password — the full procedure is §12.1)** · `unlock-account` (Q-015 break-glass) · **reissue an
abandoned OTP** (rev 3, SEC-S5: an OTP is consumed at the login that uses it, so a clerk who closes
the tab before changing their password needs a **new** one — admin does it in the UI, or
`reset-admin-password` for an admin) ·
"public page is down" (is it the CDN or the API? the static shell loads either way, so a 503 state
means the API) · "citizen reports too many attempts" (shared NAT — raise
`RATE_LIMIT_LOOKUP_PER_MIN`, an env change, not a code change) · offboard a clerk (admin issues a
password reset and **discards** the OTP — R2-10: that revokes all sessions and leaves an unusable
credential that dies in 72 h; note it in the office's own records because the account still appears
in the list) · monthly base-image rebuild · quarterly dependency batch · domain/card renewal.

The two procedures the reviewers asked to see written now, not at /release, are §12.

## 12. Runbook — the two written procedures (rev 2, REL-F6)

### 12.1 Lost admin password (nobody can log in as an admin)

Symptom: the only admin clerk cannot log in and no second admin exists (OQ-5 default). Distinguish
first: if login says *"Too many attempts, wait n seconds"* this is a **throttle**, not a lost
password — go to `unlock-account` instead. If the password is genuinely unknown, or login returns
`otp_expired`, continue.

1. Confirm the exact username with the office.
2. `fly ssh console -a <api-app>` — this needs the Fly account, i.e. the human. That is deliberately
   the recovery authority.
3. `uv run reset-admin-password <username>`. It refuses if the account is not an admin clerk.
4. It prints the 12-character one-time password **once**. Copy it now: it is not stored, not logged
   and not recoverable — if lost, just run the command again.
5. It has already revoked every session for that account, set `must_change_password`,
   `password_is_otp=true` and `password_set_at=now()` (the 72 h clock starts here), and written a
   `password_reset_issued` / `reason_code=operator_cli` row to `security_event`.
6. Hand the OTP over **verbally** (BR-016) — never by SMS, email or chat; no such channel exists here
   and a personal one puts a live credential in a third party.
7. The admin logs in and is forced to Change Password — that screen asks for the **new password
   only**, no current password. **The OTP is spent by that login** (rev 4, R4-1): the login
   transaction replaces the stored hash with a random value nobody keeps, so the OTP is dead the
   instant it is used and the account has no usable password until the change completes. If they
   abandon the browser before finishing, re-run step 3 for a new OTP — there is no other way back.
   Confirm completion: a second attempt with the old OTP must now fail with the ordinary
   "wrong username or password" message (`401`), and the new password must work.
8. Record it in the office log (date, who authorised), and reconsider OQ-5 — a second admin turns the
   next occurrence into a two-minute in-app reset instead of a call to the human.

Failure branches: *ssh will not connect* → the machine is unhealthy, work §12.2 first (the database
is not the problem). *"no such account"* → wrong username. *"not an admin clerk"* → this is a regular
clerk; an admin resets them in the UI (FR-018).

### 12.2 Database down / API returning 503

Symptom: the public page loads but shows "temporarily unavailable"; clerks see the same on every
action; the pinger has emailed; `/healthz` returns `503 {"status":"unavailable"}` or nothing.

1. **Classify in one command.** `curl -s -o /dev/null -w '%{http_code}' https://api.<domain>.in/healthz`.
   - `200` → the API and the database are fine; the problem is the CDN or the client's network. Load
     the static site directly; check Render's status page. Clerk work is blocked only because the
     shell will not load.
   - `503` → the process is up but `SELECT 1` failed. **This is the database.** Continue at 2.
   - connection refused / platform error page / timeout → the machine is unhealthy or gone.
     Continue at 4.
2. Database branch. `fly status -a <api-app>` (is the machine up?) and check the Managed Postgres
   cluster in the Fly dashboard: status, region `bom`, storage headroom, recent maintenance. Also
   check the Fly status page — a regional Postgres event is the single most likely cause and there is
   no HA (R1, threat #40).
3. Confirm from the app side: `fly logs -a <api-app>`, look for `service_unavailable` /
   `DependencyUnavailable` and connection errors, note one `request_id`. Then by cause — *storage
   full* → extend the plan in the dashboard (a paid change, so the human's call); *`too many
   clients`* → close any stray `psql`, `fly machine restart`, and if it recurs take the PERF-F1
   fallback (redeploy with `--workers 1`, re-record §10); *platform incident* → wait and communicate.
   Tell the office both the public lookup and the clerk app are down and that **no data is lost**:
   every write is one transaction, so nothing was half-written.
4. Machine branch. `fly status`, `fly logs`, `fly machine restart -a <api-app>`. If it will not come
   up, redeploy the last known-good image: `fly deploy --image <previous digest>` (§7). If the
   release command is what fails, the migration is the cause and the deploy aborted before traffic
   shifted — the *old* version should still be serving; if it is not, roll the image back.
5. **Do not** point the app at another database, restore a backup to "fix" a 503, or run destructive
   SQL. A 503 is unavailability, not corruption; restore (§8) is a separate, human-only decision.
6. Recovery check: `/healthz` is `200`; run the post-deploy smoke (login → log a complaint → public
   lookup); confirm the machine is back in rotation (3 consecutive successes, ~45 s). Afterwards
   record the outage window against the NFR-007 evidence trail and whether the budget was breached.

### 12.3 "Everything is 429" — the limiter has collapsed into one bucket (rev 4, SEC-F5)

Symptom: unrelated citizens and clerks all see "too many attempts / please wait" at the same time;
`security_event` shows `throttle_lookup` (or `throttle_login`) rows for **one** key while the office
insists traffic is normal; `rate_limit_counter` holds very few keys with very high counts.

1. **First suspect is `TRUSTED_PEER_CIDRS`, not an attack.** If it does not contain the address Fly's
   proxy actually connects from, every request is treated as coming from an untrusted peer and is
   keyed on that single proxy address — the whole internet lands in one bucket. It fails *closed*
   and silently, which is why this section exists. (The opposite mistake — a CIDR too wide — is
   covered by SEC-T21 case 1.)
2. Confirm: `fly ssh console` → `select scope, key, count from rate_limit_counter order by count desc
   limit 10;`. One key with a count in the hundreds and no others is the signature.
3. Compare that key with the current Fly proxy address range, then correct `TRUSTED_PEER_CIDRS`
   (`fly secrets set` is not needed — it is not a secret; a config change plus a redeploy) and
   re-run the /release two-address check (§13) before declaring it fixed.
4. Only after ruling this out treat it as a real flood (§12.2 step 2 for load, threat #33).

### 12.4 Trimming `security_event` (rare, human-only)

The application can never delete from `security_event`, `complaint_history` or `complaint` — the
`before_execute` guard raises, and the deployed app role additionally has `UPDATE`/`DELETE`
**revoked** on those three tables. Recovery from a pathological growth (threat #64) is therefore a
human action taken as the **database owner role** — the Fly Managed Postgres superuser/owner that
created the schema, which is *not* the role in `DATABASE_URL`. That separation is the point: the
operator connects with `fly postgres connect` using the owner credential, runs a bounded
`DELETE FROM security_event WHERE created_at < …`, and records it in the office log. No application
path, no CLI command and no migration may do this.

## 13. /release verification items produced by this architecture

Each of these is a *check with a recorded result*, not a claim: Postgres connection limit and price
(§1) · CA certificate availability for `sslmode=verify-full` · platform log retention · backup
retention and encryption at rest · custom domain live on **both** hosts before real data · Render
auto-deploy OFF · edge HTTP→HTTPS redirect · **client-IP spoofing attempt (SEC-F1/SEC-S1): from a known
source address, send lookups carrying a forged `Fly-Client-IP` and a forged `X-Forwarded-For` and
confirm they are throttled together on the real source, not separately** · **the inverse check
(rev 4, SEC-F5): the same lookups sent from **two different real source addresses** land in **two
different limiter keys** — if they share one, `TRUSTED_PEER_CIDRS` is wrong and the limiter is
useless in the other direction (runbook §12.3)** · **the deployed process runs
`--worker-class app.worker.RawPeerWorker` and `FORWARDED_ALLOW_IPS` is unset (`fly ssh console` →
inspect the running command line and the environment; `selfcheck` should already have refused to
start otherwise)** · sole-machine-unhealthy
behaviour (§9) · restore test into a throwaway cluster (§8) · OQ-2 destination asked once more.

## 14. Named residual risks

R1 single machine, no HA (accepted under AD-7; client-visible behaviour written out in §9) ·
**single-vendor backups while OQ-2 is unanswered (§8, threat #28 accepted)** · R6 no staging (compensated above) · R9 merged ≠
deployed (owned, §6) · two vendors, two dashboards, two checklist items · Fly's Managed Postgres is
younger than Render's · `TRUSTED_PROXY_HOPS` must be re-derived for Fly and verified live, never
inherited from the Render assumption · static assets sit on a non-India CDN carrying no citizen data
(A-T1a); if residency is later read to cover them, moving `out/` to a second Fly machine in `bom`
costs +$2–5/mo and zero code change — raise it as a decision, do not adopt it silently.
