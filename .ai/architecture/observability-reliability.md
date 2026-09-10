# Observability & Reliability

rev 3 (2026-09-09). Binding: ADR-011 (stdout logs + uptime pinger + `security_event`, no Sentry),
ADR-006 (`/healthz` checks the DB), ADR-008 (limiter fails closed). Drivers: AD-2 (no third-party
PII processor), AD-5 ($0 observability), AD-6 (one part-time ops owner), AD-7 (99% office hours).

## 1. Logging

**Format.** One structured JSON line per event to stdout, captured by the platform.
Fields: `timestamp`, `level`, `event`, `request_id`, `method`, `path`, `status`, `duration_ms`,
`user_id` (when authenticated), `derived_ip`, and for errors `error_code` + `exc_type`.

**Request ID.** Minted in middleware (2) if the client did not send `X-Request-ID`, attached to
every log line for the request, returned in the response header and in the error envelope. That id
is what a clerk reads out over the phone when something breaks — the only correlation mechanism we
have without an error tracker.

**Levels.** `INFO` for request completion and lifecycle events · `WARNING` for auth failures,
throttle trips, illegal transitions, fail-closed 503s · `ERROR` for unhandled exceptions (traceback
to stdout, never to the client) · no `DEBUG` in production.

**Never-log list — binding, and asserted by tests:**

> passwords (submitted or issued) · one-time passwords · session tokens or cookie values · CSRF
> tokens or seeds · **complaint numbers** · citizen name, phone, description, clerk notes ·
> `Cookie` / `Authorization` / `X-CSRF-Token` headers · full request or response bodies ·
> `DATABASE_URL`, `SECRET_KEY` or any environment value · client-visible stack traces.

A redaction filter in `core/logging.py` is the backstop; the rule is not to pass these values in.
Tests assert that the submitted password string and the issued OTP appear in no captured record.

**The gunicorn access log, stated exactly (rev 2, SEC-F3/ARCH-F1).** Gunicorn's access log is enabled
(`--access-logfile -`) and it records the **request line — method, path *and* query string** — plus
status, byte count and duration. It is a separate logger from `core/logging.py`, so **the redaction
filter does not protect it.** Two consequences, both binding:

1. **No sensitive value may ever appear in a path segment or a query string.** Not a complaint
   number, not a citizen name, not a phone number, not a session or CSRF token. This is why the
   public lookup is a POST with a body, why clerk search is `POST /api/complaints/search` with a
   JSON body rather than `?q=`, and why the clerk UI keeps the selected complaint in memory rather
   than in a URL (R2-1, frontend §2). The never-log list depends on it.
2. The access log is therefore **effectively path-only** in practice: the only variable part any URL
   carries is an opaque internal complaint id, which is not a citizen-facing credential and is
   meaningless without a session. If a future route ever needs a value in the URL, either the access
   log is reconfigured to a path-only format **first**, or the route does not ship. A CI grep over
   the route table asserts no path parameter is named `number`, `phone`, `name` or `q`.

## 2. `security_event` table

Append-only, in the same Postgres, inside the platform's daily backups — the durable answer to
"was there a brute-force attempt last month?", which platform log retention (days) cannot give.

**Column names below are the schema's, verbatim (rev 3, ARCH-F5).** Rev 2 called two of them `actor`
and `occurred_at` here and `actor_hash` in two other documents, and omitted `target_user_id`
entirely; there is now one set of names across architecture, schema and contract.

| Column | Content |
|--------|---------|
| `event_type` | `login_success`, `login_failure`, `password_reset_issued`, `account_created`, `throttle_lookup`, `throttle_login`, `throttle_detail`, `throttle_write` (rev 3, SEC-S4), **`throttle_search`** (rev 4, R4-6), `account_unlocked`. **No `complaint_viewed`** — OQ-9's default stands, see security-architecture §7 |
| `actor_user_id` | FK to the clerk account when the actor is authenticated, else `NULL` |
| `actor_username_hash` | `h(username)` (fixed-width hash over `USERNAME_HASH_SALT`, same shape as the limiter key; that salt is never rotated precisely so these rows stay correlatable — R2-11). Set when the actor is not authenticated, e.g. a login failure |
| `target_user_id` | the account the action was performed **on** — the only way to answer "who reset whose password"; `NULL` for events with no target |
| `derived_ip` | five-step rule, IPv6 already /64-normalised |
| `created_at` | timestamptz |
| `reason_code` | short enum, no free text |

**Throttle events are written once per window, not once per refused request (rev 3, SEC-S2).** The
table is append-only and the application cannot delete from it, so a `throttle_*` row per `429` on an
unauthenticated path would be an attacker-driven, unshrinkable table — the shape of threat #34. The
limiter's `RETURNING count` makes the fix free: the event is written **only** when
`count == limit + 1`, the single request that crosses the threshold for that
`(scope, key, window_start)`. A 20 rps flood produces one row per window per key instead of ~72 000
an hour, and the operator's question ("was this key throttled, when?") is answered identically.

**`login_failure` rows are bounded too (rev 4, R4-5/SEC-F4).** Rev 3 fixed the throttle rows and left
the failure rows unbounded, which is the same defect one table over: a wrong password writes a row
*before* any limiter refuses anything, so up to the tier-1 ceiling of 100 failures/15 min per IP —
and with a rotating username, one row each — went into an undeletable table. The rule now: **at most
one `login_failure` row per `(actor_username_hash, derived_ip, 15-minute window)`**, and once the
`login_ip` counter for that key is past its limit the request short-circuits before the event
service, so **no further rows at all**. Arithmetic for a single attacking IP: previously up to
100 rows per 15 min (≈400/hour, ≈9 600/day, permanent); now at most one row per distinct username
tried in that window, and zero once the IP is throttled — so the worst case is bounded by the
tier-1 limit itself, ~100 rows per 15-minute window per IP even if every attempt uses a new username,
and in the realistic case (one or a few usernames) **one to a handful of rows per window**. The
operator signal is unchanged: "this account, from this address, was failing in this window", plus the
`throttle_login` crossing row. Test SEC-T33.

Never stored: the password (any form), the OTP, the complaint number, request bodies, headers.
Growth is a few rows/day at AD-4 scale, and bounded above by the per-window rules; trimming is a later
decision, and it holds no complaint data so NFR-010 does not apply to it. Writes go through `services/security_events.py`; `UPDATE`/`DELETE`
against the table raise at the data-access layer.

## 3. Health checks

`GET /healthz` — executes `SELECT 1` with a short statement timeout **and caches the result
in-process for 10 s** (rev 2, ARCH-F9: it is unauthenticated, unlimited and hits the database, so
without the cache a flood is a free query amplifier against the one resource everything else needs;
10 s is well inside the 15 s check interval, so nothing detects slower), returns a bare
`{"status":"ok"}` / `503 {"status":"unavailable"}`. No version, no dependency detail, no build hash:
it is an unauthenticated endpoint on the public allow-list. Consumers: the Fly platform check every
15 s with a 3-consecutive-failure threshold (a machine with a dead database is pulled from rotation
rather than serving 503s; the threshold stops a single slow moment from removing the only
machine — infrastructure §9) and a free
external pinger every 5 min emailing a shared office address — the latter is the NFR-007 evidence
trail, because a platform check leaves no record we own.

No separate liveness/readiness endpoints: one process, one dependency (§ infrastructure.md §9).

## 4. Metrics

Deliberately none beyond the platform's own machine metrics (CPU, memory, connections) and the Fly
memory alert at ~420 MB. A metrics backend would cost more than the application (AD-5) and needs an
owner (AD-6). The questions a pilot actually asks — "is it up?", "did someone brute-force us?",
"how slow was that request?" — are answered by the pinger, `security_event`, and `duration_ms` in
the logs respectively. Revisit only if the pilot grows past one panchayat.

## 5. Failure modes and behaviour

| # | Component / failure | Detection | System behaviour | User-visible | Recovery |
|---|---------------------|-----------|------------------|--------------|----------|
| 1 | **Postgres down / unreachable** | `pool_pre_ping`, `/healthz` 503, pinger email | limiter upsert fails ⇒ **fail closed**; all data routes 503 with `service_unavailable` | Public: "The service is temporarily unavailable. Please try again in a few minutes." Clerk: same, per-screen | platform recovery; machine rejoins when `/healthz` passes |
| 2 | **Slow query** | `statement_timeout` 10 s | statement aborted, mapped to 503 | same as (1), scoped to the action | investigate via `request_id` in logs |
| 3 | **Wedged worker** | gunicorn `--timeout 30` | the worker is killed and replaced (all its in-flight requests die — accepted at 2 workers, <1 rps) | "The server is taking too long." | automatic |
| 4 | **Slow memory growth** | Fly alert ~420 MB; `--max-requests 1000 --max-requests-jitter 100` | worker recycled periodically | none | fallback `--workers 1` with 8 threadpool tokens |
| 5 | **API entirely down** | pinger | the CDN still serves the static shell — the page loads and shows an error state instead of a platform error page (a genuine gain from the H4 split) | "temporarily unavailable" / "taking too long" | human redeploy or platform recovery |
| 6 | **CDN / static host down** | pinger only covers the API; a citizen phones | nothing to serve | browser error page | Render status; the API is unaffected, so clerk work is also blocked (no shell) |
| 7 | **Stale bundle after a promotion** (chunk 404) | client catches `ChunkLoadError`/asset 404 | reload prompt instead of a blank screen | "A new version is available — reload" | user reloads; window is one navigation (`no-cache` HTML) |
| 8 | **Rate limit trips a legitimate shared-NAT user** | `throttle_lookup` rows | 429 with soft wording, never a CAPTCHA or a hard block | "Too many attempts from this network. Please wait a minute…" | raise `RATE_LIMIT_LOOKUP_PER_MIN` (env change, no code change) |
| 9 | **Login brute force** | `login_failure` + `throttle_login` rows | per-IP ceiling short-circuits; username+IP blocks; per-account backoff is `429 + Retry-After`, never a lock | "Too many attempts. Please wait {n}s." | window elapses; `unlock-account` as break-glass |
| 10 | **Session expired mid-use** | 401 on the next call | client clears state | non-dismissible "Your session has expired." banner; unsaved input is reported as not saved | re-login |
| 10b | **Create request timed out, outcome unknown** (rev 2, REL-F1) | 10 s client abort with no response | nothing server-side; the write either committed or rolled back atomically | "We didn't get a confirmation — your complaint may already have been saved. Check the complaints list before entering it again." + "Check the list" / "Try again" | "Try again" resends the same `client_request_id`; a duplicate returns the existing complaint (R2-6) |
| 10c | **PII-read ceiling tripped** (rev 2 R2-7, re-keyed in rev 3, widened in rev 4 by R4-2) | one `throttle_detail` row per window | 429 on any further response carrying name/phone **for that user**, across all their sessions — including `GET /api/complaints/{id}/activity` | "Too many records opened in a short time. Please wait." | window elapses; investigate the account if it was not a real clerk |
| 10c2 | **Search ceiling tripped** (rev 4, R4-2) | one `throttle_search` row per window | 429 on `POST /api/complaints/search` for that user | "Too many searches in a short time. Please wait." | window elapses; 120 searches/hour is far above paging behaviour, so investigate the account |
| 10d | **Write ceiling tripped** (rev 3, SEC-S4; routes extended in rev 4, R4-5) | one `throttle_write` row per window | 429 on `POST /api/complaints`, `POST /api/accounts` and `POST /api/accounts/{id}/reset-password` for that user | "Too many records created in a short time. Please wait." | window elapses; 60/hour is only 2–3× a busy clerk's real peak (SEC-F6), so **investigate and confirm with the office** before concluding the session is compromised |
| 11 | **CSRF seed blocked (cookies disabled)** | distinct CSRF error code | lookup POST rejected 403 | "This page needs cookies enabled…" | user enables cookies |
| 12 | **Concurrent status update** | row lock serialises | last write wins current state; **both** history rows persist (BR-011) | non-blocking advisory: "This complaint was updated by {clerk} a moment ago." | refresh |
| 13 | **Complaint-number collision on insert** | unique violation | retry with a fresh number inside a savepoint, max 5 | none | automatic |
| 14 | **Migration failure on deploy** | Fly `release_command` non-zero | deploy aborted before traffic shifts | none — old version still serving | fix forward, redeploy |
| 15 | **Deploy skew (frontend newer than API)** | E2E smoke after promotion | additive-only API rules mean the old bundle still works | none | promote in the correct order (API first) |
| 16 | **Secret misconfigured** | `selfcheck` at startup and in CI | **process refuses to start** | 503 from the platform until fixed | fix the env var, redeploy |
| 17 | **Unhandled exception** | `ERROR` log + traceback to stdout | 500 with `internal_error` + request id only | "Something went wrong." | grep the log by request id (no error tracker — accepted, ADR-011) |

**Accepted gap (R7):** a 500 on a page the pinger does not hit is discovered when a clerk phones.
At 1–5 clerks in one office that is minutes, and the platform log search holds the traceback.

## 6. Timeouts and retries — one coherent ladder

| Layer | Value | Why |
|-------|-------|-----|
| Browser `AbortController` | **10 s** | NFR-011: the user-visible message comes from our UI on all three workflows, never a platform page |
| Postgres `statement_timeout` | **10 s** | catches the common cause (a slow query) before gunicorn's blunt instrument |
| gunicorn `--timeout` | **30 s** | backstop for a wedged worker only |
| Fly health check timeout | 2 s, every 15 s, grace 10 s | pull an unhealthy machine quickly |
| Login backoff `Retry-After` | ≤5 s | never approaches the 10 s client abort |

**Retries: none, anywhere, automatically.** No external service is called during a request
(ADR-012), the database is reached through `pool_pre_ping` (which transparently replaces a dead
connection), and retrying a write without idempotency would risk a duplicate complaint. The only
retry in the system is the bounded complaint-number regeneration on unique violation (§5 row 13).
Retry is the user's decision — but **rev 2 (REL-F1) removes the blanket "Retry control on every error
state"**: a retry affordance is offered only where the call is idempotent (see below), because the
client aborts at 10 s while gunicorn allows 30 s, so "timed out" and "succeeded" are routinely the
same event on a slow create.

**Idempotency, per endpoint:**

| Endpoint | Idempotent? | Mechanism / client behaviour |
|----------|-------------|------------------------------|
| all `GET`s, `POST /api/lookup`, `POST /api/complaints/search` | yes, naturally | plain "Retry" is safe |
| **`POST /api/complaints`** | **yes, by key** (rev 2, ADR-022/R2-6) | client generates `client_request_id` (UUID) once per form and **keeps it across retries**; unique column; on a duplicate the server returns the **existing** complaint with `duplicate: true` instead of inserting. On a timeout the UI shows *"We didn't get a confirmation — your complaint may already have been saved. Check the complaints list before entering it again."* with "Check the list" and "Try again" (same key), never a bare Retry. Rationale: BR-008 forbids deleting the duplicate, so the alternative was a permanent Rejected-status scar on the audit trail for a purely infrastructural hiccup |
| `POST /api/complaints/{id}/status`, `/details` | no, and deliberately un-keyed | in-flight control disabled; a duplicate is one extra history row — visible, attributed, and harmless, which is exactly what an append-only audit trail is for. Plain Retry is fine |
| `POST /api/login`, `/logout`, `/password/change`, account endpoints | no | no retry control; the user re-submits deliberately. A repeated reset simply issues a fresh OTP and invalidates the previous one (R2-5) |

A *general* idempotency-key framework is still rejected: one endpoint needed it, one endpoint got it.

## 7. Capacity assumptions

<1 rps sustained; peaks of a few concurrent clerk actions; a few hundred public lookups/day; ≤6
accounts; the complaint table grows by tens of rows/week and is never purged (NFR-010). ≤20
Postgres connections. Memory ~240–304 MB steady, ~376 MB peak (login burst), ~136 MB headroom.
**All of these are estimates to be measured at /test-app, not trusted** — the 3 s/3G budget (AC-010)
and the memory figures are the two most likely to be wrong.

**Growth path — what breaks first, in order (rev 2, PERF-F3).** One paragraph, so nobody has to
assemble it from five documents. (1) **Memory during a login burst** is the nearest ceiling: eight
concurrent Argon2 hashes at `m=9216 KiB` put the 512 MB machine near ~376 MB, so the first symptom of
growth is a login-time OOM, not slow queries — the fix is upsizing the machine (+$3–5/mo) and raising
`m` afterwards, in that order. (2) **The Postgres connection ceiling** is next: 20 connections is
fine for 2 workers, but any third worker or a second machine needs the verified limit (§infrastructure
§1) and, past it, PgBouncer — which is a new component and therefore a GATE decision. (3) **Search**
is third: the `complaint_number` field is an indexed equality match and costs nothing, but the `q` `ILIKE` over name/phone (rev 3, R3-1) is a sequential scan, invisible at tens of thousands of rows
and unacceptable somewhere in the low hundreds of thousands; the fix is a `pg_trgm` GIN index, an
additive migration with no code change. (4) **Multi-panchayat** is the real wall: there is no tenant
column anywhere (threat #56), all clerks see all records by design, and the limiter, the session
model and the permission matrix all assume one office of ≤6 people. That is a re-architecture and a
return to GATE_1, not a scaling exercise — and it is the correct trade at pilot scale, recorded so
nobody discovers it under pressure. Everything before (4) is money or one index.

## 8. Evidence trail for NFR-007

Monthly uptime percentage from the pinger's dashboard/emails, restricted to office hours; plus
`security_event` rows for the security half. Neither requires an account nobody owns, which is why
this shape was chosen over Sentry (AD-2, AD-6).

## 9. Runbook pointers

Operational procedures live in infrastructure.md §11, and the two that need real steps —
**lost admin password** and **database down / API 503** — are written out in full in
infrastructure.md **§12**, not deferred to /release (rev 2, REL-F6). The three most likely calls:
"the public page says unavailable" → §12.2, one `curl /healthz` classifies it; "a clerk cannot log
in" → check `security_event` for `throttle_login` then `unlock-account`, and if the password itself
is lost and the account is the admin, §12.1; "a citizen says too many attempts" → shared NAT, raise
the threshold by env var.
