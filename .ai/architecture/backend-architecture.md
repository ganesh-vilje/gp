# Backend Architecture — FastAPI service

rev 3 (2026-09-09). Binding: ADR-003, ADR-005, ADR-006, ADR-007, ADR-008, ADR-010, ADR-011,
ADR-020…ADR-022 (rev 2), ADR-023 (rev 3) and
`solution-architecture.md § Rev 2/3 decisions for the API and schema`.
Schema and endpoint contracts belong to the data-api-architect; this document defines the module
layout, the mechanisms and where each rule lives.

## 1. Module layout

```
app/
  main.py                  # create_app(): settings → selfcheck → middleware (in order) → routers
  settings.py              # pydantic-settings; every value from env; no defaults for secrets
  selfcheck.py             # production-config gate; console script + startup hook
  core/
    errors.py              # domain error taxonomy + the single HTTP error envelope
    complaint_number.py    # generate() / normalise() / validate() / checksum()
    validation.py          # phone, username, password policy (BR-012, BR-016)
    hashing.py             # argon2 wrapper, h(username), sha256(token)
    clock.py               # now() — injectable, so windows/expiries are testable
    client_ip.py           # peer-gated client-IP derivation (§5); the ONLY module that reads
                           # Fly-Client-IP / X-Forwarded-For — a grep assertion enforces that
    logging.py             # structured JSON logger + redaction filter
    strings.py             # every server-side user-visible message, keyed (AD-12)
  db/
    engine.py              # request engine (pool 4+2) and limiter engine (AUTOCOMMIT, pool 4+0)
    session.py             # get_session() dependency; commit/rollback in finally
    models/                # SQLAlchemy 2.x Mapped[...] models (data-api-architect owns the fields)
    guard.py               # before_execute hook: raise on UPDATE/DELETE of append-only tables
    repositories/          # complaint.py, history.py, user.py, session.py, security_event.py
  services/
    auth.py                # login, logout, session issue/rotate/revoke
    accounts.py            # create clerk, reset password, OTP issuance (BR-013, BR-016)
    complaints.py          # create, update_status, edit_details, transitions.py
    lookup.py              # public lookup + status → public_update mapping
    limiter.py             # atomic upsert, key derivation, deterministic cleanup
    security_events.py     # append-only event writer
  api/
    deps.py                # current_user, require_admin_clerk, get_session
    routers/               # session.py, auth.py, lookup.py, complaints.py, accounts.py, health.py
    schemas/               # request/response DTOs; every response has extra="forbid"
  middleware/              # security_headers.py, session_loader.py, csrf.py, authz.py, request_id.py
  cli/                     # bootstrap_admin.py, reset_admin_password.py, unlock_account.py
migrations/                # Alembic, additive-only
```

Dependency rule: `api → services → repositories → db`, everything may import `core`, nothing
imports upward. A test asserts no `services` module imports `api`, and no `core` module imports
`services`.

## 2. Middleware chain (order is code, and asserted by a test)

Outermost → innermost, exactly as ADR-007 fixes it:

| # | Component | Responsibility | Failure |
|---|-----------|----------------|---------|
| 0 | **proxy-header processing is switched off by a worker class (rev 4, SEC-F1 — this replaces rev 3's "we don't pass the flags", which was aimed at an option that does not exist)** | Under `uvicorn_worker.UvicornWorker`, uvicorn's `Config.proxy_headers` defaults to **True** and gunicorn hands its own `forwarded_allow_ips` (default `127.0.0.1`, overridable by the **`FORWARDED_ALLOW_IPS`** env var) straight into that `Config` — so `ProxyHeadersMiddleware` is built into the ASGI stack and rewrites `scope["client"]` from `X-Forwarded-For` **before any application code runs**, flag or no flag. Gunicorn has **no** `--proxy-headers` option to omit. The mechanism is therefore in the repo: `app/worker.py` defines `class RawPeerWorker(UvicornWorker)` with `CONFIG_KWARGS = {"proxy_headers": False, "forwarded_allow_ips": []}`, and the container runs `--worker-class app.worker.RawPeerWorker` (infrastructure §3). With that in force `scope["client"][0]` is the raw TCP peer that the peer-first rule in §5 is built on, and `core/client_ip.py` is the **only** reader of `Fly-Client-IP` and `X-Forwarded-For` (grep-asserted). `X-Forwarded-Proto` is read by **nothing** — it is on the grep block-list only (rev 4, SEC-F8). `selfcheck` (§11) asserts the *behaviour*, not an argv string. Consequence to be aware of: `request.url.scheme` is `http` inside the container. Nothing depends on it — `Secure`/`__Host-` come from `COOKIE_SECURE`, HSTS is emitted unconditionally in prod, no redirect middleware exists (the edge redirects, verified by `curl` at /release), and no absolute URL is ever generated | — |
| 1 | `TrustedHostMiddleware` | host allow-list from `ALLOWED_HOSTS` | 400 |
| 2 | request-ID + security headers | mint/propagate `X-Request-ID`; set HSTS, `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`, `CSP: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`, `Cache-Control: no-store` on authenticated and lookup responses | — |
| 3 | CORS | explicit origin allow-list, `allow_credentials=True`, methods **`GET,POST` only** (R2-2: no `PATCH`/`PUT`/`DELETE` verb exists in the API, so this stays a `selfcheck`-assertable invariant — the field-correction route is `POST /api/complaints/{id}/details`), headers `content-type,x-csrf-token`, `max_age=600` | preflight denied |
| 4 | session loader | cookie → `sha256` → row; check `revoked_at`, idle, absolute; refresh `last_seen_at`; set `request.state.user` | anonymous, not an error |
| 5 | CSRF | unsafe methods only; `Origin` allow-list + `X-CSRF-Token` (two paths, §4) | 403 |
| 6 | authorization | deny-by-default against the 4-entry allow-list; `must_change_password` gate | 401 / 403 |
| 7 | router + dependencies | `require_admin_clerk`, DTO validation | 403 / 422 |

There is **no exemption decorator and no exempt-path list** anywhere in the package; a grep
assertion enforces that.

**Application-level body-size rejection (rev 3, SEC-S8).** Row 2 also rejects any request whose
`Content-Length` exceeds `MAX_REQUEST_BODY_BYTES = 65536` (64 KB) with `413`
(`code: "payload_too_large"`) **before the body is read or parsed**, and streams-with-no-length are
capped at the same figure while reading. 64 KB is ~30× the largest legitimate body (a 2000-character
description plus name, phone and a UUID is under 3 KB). Rev 2 relied on "platform edge body limits"
— a limit nobody had read, on a layer we do not configure — plus Pydantic's `max_length`, which only
applies *after* the whole body is buffered and JSON-parsed. This is the control cited by threat #37.

## 3. Sessions

- Token: `secrets.token_urlsafe(32)`. Stored as SHA-256; the plaintext exists only in the cookie.
- Cookie: `__Host-session`, `httpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, **no `Max-Age`** (browser-close expiry). Dev over http uses the unprefixed name with `COOKIE_SECURE=false`.
- Row: `user_id NOT NULL` (no anonymous rows), `csrf_token`, `created_at`, `last_seen_at`, `absolute_expires_at`, `revoked_at`. **No `user_agent_hash`** — rev 2 (R2-8/SEC-F14): rev 1 stored it and never checked it, which is a fingerprint with no control attached. UA binding returns only together with a check and a test.
- **Idle window 45 min** (ADR-019, inside ADR-007's 30–60 range); **absolute 9 h**. An expired row is rejected *and* marked revoked on the same request.
- **Issuance on login (ADR-021 / R2-4 — this supersedes rev 1's "revoke old on login"):** login **always** mints a new token and a new row, and revokes **only the session presented in this request's own cookie**, if one was presented and still valid. Session fixation is defeated (the attacker-planted cookie's session is the one revoked, and the victim leaves with a token the attacker never saw); a clerk logged in on the office desktop is **not** kicked out by logging in on a phone, which is a real pattern in a one-room office. A login with no cookie simply adds a row.
- **OTP logins are consumed by destroying the credential (rev 4, R4-1 — this replaces rev 3's flag-clearing, which consumed nothing).** When the verified password is the account's OTP (`password_is_otp = true` and still in date), the login transaction does three things atomically: (a) **overwrites `password_hash` with `argon2.hash(secrets.token_bytes(32))` for a value that is generated inside the transaction, used once and discarded** — it is never stored in a variable that outlives the call, never returned, never logged, and known to no one; (b) sets `password_is_otp = false` and **keeps `must_change_password = true`**; (c) issues a session that the middleware gate confines to change-password / logout / `GET /api/session`. Why the hash must die: clearing the flag alone left the OTP's own hash in place, so the same OTP authenticated again *and* the expiry check in §3 of security-architecture stopped firing (it is guarded by `password_is_otp`). Why the clerk is unaffected: `POST /api/password/change` **takes no `current_password` when the session is a must-change session** (the OTP login already proved possession), so nobody ever needs to know the throwaway value. A **second** login with the same OTP fails Argon2 verification and returns the generic **`401 not_authenticated`** (R4-4 — `invalid_credentials` is not a code in this system). An abandoned must-change session means the OTP is spent: the admin reissues (runbook §12.1). Mechanism in security §3; test SEC-T22.
- **Revoke-all** (every non-revoked row for that user) on: self password change, admin password reset, `reset-admin-password`, and logout-everywhere. Plain logout revokes the current row only.
- **Sweep (rev 2, PERF-F2/ARCH-F6; SQL corrected in rev 3, ARCH-F2):** two bounded statements on the **request** engine, both row-capped so they can never become a long transaction. PostgreSQL has **no `DELETE … LIMIT`**, so the bound is expressed with a `ctid` sub-select — this is the exact form to implement, and `:idle` is bound from the `SESSION_IDLE_MINUTES` setting, never a hardcoded interval:
  1. on every **successful login**:
     ```sql
     DELETE FROM session WHERE ctid IN (
       SELECT ctid FROM session
       WHERE user_id = :uid
         AND (absolute_expires_at < now()
              OR last_seen_at < now() - make_interval(mins => :session_idle_minutes)
              OR revoked_at IS NOT NULL)
       LIMIT 100);
     ```
     the user's own debris, at the moment they are already paying for a write;
  2. on the **same** trigger:
     ```sql
     DELETE FROM session WHERE ctid IN (
       SELECT ctid FROM session
       WHERE absolute_expires_at < now() - make_interval(days => :session_grace_days)
       LIMIT 200);
     ```
     (`SESSION_SWEEP_GRACE_DAYS = 7`) — a global floor so an account that never logs in again cannot leave rows forever.
  **Cost of the bound (rev 3, PERF-F5):** the sub-select on `absolute_expires_at` is scan-cheap at the sizes this table is bounded to (low thousands worst case), so no index is required for correctness or latency; if the table ever grows past that, the fallback is a partial index on `absolute_expires_at` — an additive migration, not a new component.
  Ceiling arithmetic at pilot scale: ≤6 accounts × a handful of logins/day ⇒ tens of rows live, low hundreds ever; the 7-day floor caps the table in the low thousands even if every login came from a fresh browser. Never a cron, never a probability, never unbounded.

## 4. CSRF

Applies to every unsafe method on every route.

- **Anonymous path (public lookup):** `GET /api/session` **with no session cookie** takes the anonymous variant (R2-3): sets `__Host-csrfseed` (`httpOnly`, `Secure`, `SameSite=Lax`) if absent and returns `{authenticated:false, csrf_token: base64url(hmac_sha256(SECRET_KEY, seed))}`. Verification recomputes the HMAC and uses `hmac.compare_digest`. **Zero SQL on this variant** — no row, no connection, so an anonymous flood cannot trip the fail-closed limiter. The zero-SQL assertion in the test suite therefore sends **no cookie**; it is not a claim about the endpoint as a whole.
- **Authenticated path:** when a session cookie *is* presented, `GET /api/session` returns `{authenticated:true, username, is_admin_clerk, must_change_password, csrf_token}` — one indexed session read plus the normal `last_seen_at` refresh, i.e. the same cost as any authenticated request, and covered by the authenticated limiter posture rather than the zero-SQL guarantee. The 256-bit `csrf_token` lives in the session row, changes when the session does, and is returned in the JSON body of the login and password-change responses so the client is never left holding a stale token.
- **What each of the three token-changing responses returns (rev 3, ARCH-F4 — this replaces the earlier "session-bound on logout" wording, which was wrong):**
  - `POST /api/login` — new session row ⇒ new **session-bound** token, in the body, with the new `__Host-session` cookie.
  - `POST /api/password/change` — revoke-all then issue one fresh session ⇒ **a new `__Host-session` cookie is set on this response** (otherwise the clerk is logged out by their own password change) and a new **session-bound** token is in the body.
  - `POST /api/logout` — the session is gone, so a session-bound token cannot exist. The response sets `__Host-csrfseed` if absent and returns a fresh **anonymous** token, `base64url(hmac_sha256(SECRET_KEY, seed))`, exactly as the anonymous `GET /api/session` variant does. This is what lets the now-anonymous page immediately POST `/api/lookup` or `/api/login` without a second round trip.
- Layer two is the `Origin` allow-list (missing or unlisted ⇒ 403); layer one is `SameSite=Lax`.

## 5. Rate limiter

One statement per check, on the **dedicated AUTOCOMMIT engine** (never the request `Session`), so
the increment commits independently of the request it counts:

```
INSERT INTO rate_limit_counter (scope, key, window_start, count) VALUES (…,1)
ON CONFLICT (scope, key, window_start) DO UPDATE SET count = rate_limit_counter.count + 1
RETURNING count;
```

**One throttle event per window, not one per request (rev 3, SEC-S2).** `security_event` is
append-only and the application cannot delete from it, so writing a `throttle_*` row on every `429`
would let an unauthenticated flood grow a table nothing can shrink — the exact shape of threat #34.
The returned `count` is what prevents it: the limiter writes a `throttle_*` event **only on the
request where `count == limit + 1`**, i.e. the single moment the counter crosses the threshold for
that `(scope, key, window_start)`. Every subsequent `429` inside the same window is refused with no
event row. One attacker at 20 rps therefore produces **one** row per window per key, not 72 000/hour,
and the operator signal ("this key was throttled in this window") is unchanged. Restated in
observability §2.

- **Public lookup:** scope `lookup`, key = derived client IP, **20/min** (`RATE_LIMIT_LOOKUP_PER_MIN`). Over ⇒ `429`. Statement error ⇒ **fail closed, `503`**, no lookup performed.
- **Login** (rev 3, ARCH-F8 — the scope/key split matches the schema: the scope column carries no variable part, the hash lives in the key), evaluated cheapest-first: (1) scope `login_ip`, key = derived IP, 100 failures/15 min — **short-circuits before any username-keyed row is written**; (2) scope `login_userip`, key `<h(username)>|<ip>`, 20/15 min — the blocking decision; (3) scope `login_user`, key `<h(username)>` — progressive backoff expressed as `429 + Retry-After: 1|3|5`, **never a lock and never a `sleep`** (threadpool has 4 tokens/worker). **Rev 2 (SEC-F6): the "IP with a recent successful login is exempt" carve-out is deleted.** It required a store of successful-login IPs that no component owned, and it was load-bearing in threat #36's argument. Nothing replaces it: the reason a hostile third party cannot lock the office out is that tier 3 is *never a lock* — a real clerk's worst case is a `Retry-After ≤5 s` pause, on the correct password, from their own IP.
  **`login_failure` rows are bounded (rev 4, R4-5/SEC-F4).** A failed login writes **at most one** `login_failure` `security_event` per `(actor_username_hash, derived_ip, 15-minute window)`, and **once the tier-1 (`login_ip`) counter for that key is past its limit, no further rows are written at all** — the request is refused by the short-circuit before the event service is reached. `security_event` is append-only and the app cannot delete from it, so an unbounded row-per-failure was the same defect as R3-8's throttle rows. Arithmetic and the operator consequence are in observability §2.
- **PII-read ceiling (rev 2 R2-7/SEC-F4, re-keyed in rev 3 by SEC-S3, widened in rev 4 by R4-2):** scope `detail`, key = **`user_id`**, `RATE_LIMIT_DETAIL_PER_HOUR = 120`, one-hour window. Over ⇒ `429`. The rules:
  - **Keyed on the user, not the session.** `POST /api/login` mints an unlimited number of sessions (ADR-021 deliberately does not revoke other devices), so a session-keyed ceiling costs an attacker holding the credential one extra login per 120 reads — i.e. nothing. The user is the smallest identity an attacker cannot mint more of.
  - **Coverage comes from the table below, not from schema introspection (rev 4).** Rev 3 said "every route whose `response_model` declares `citizen_name`". That test would have passed while two PII paths stayed uncounted: `GET /api/complaints/{id}/activity` declares history rows whose `previous_value`/`new_value` **are** the name and phone whenever a `citizen_name`/`citizen_phone` edit is in the history, and `POST /api/complaints/search` declares neither field but hands out 25 complaint records a call. The classification is now explicit and is the single source the dependency wiring and SEC-T29 both read; the API contract carries the same table.
- **Per-route PII classification (rev 4, R4-2 — binding, and duplicated verbatim in the API contract):**

  | Route | Returns name/phone (directly or as a history value) | Returns other complaint content | Limiter scope(s) |
  |-------|------|------|------|
  | `POST /api/lookup` | no | status + `public_update` only | `lookup` (per IP) |
  | `POST /api/complaints/search` | **no** | yes — up to 25 × (`complaint_number`, `description_snippet`, status, date) | **`search`** |
  | `GET /api/complaints/{id}` | **yes** | yes | `detail` |
  | `GET /api/complaints/{id}/activity` | **yes** — `previous_value`/`new_value` of a `citizen_name`/`citizen_phone` edit | yes (status and note history) | **`detail`** |
  | `POST /api/complaints` | **yes** (echoes the record it just created, and the `duplicate: true` replay returns the existing one in full) | yes | **`write` + `detail`, both pre-handler** (R4-3) |
  | `POST /api/complaints/{id}/status` | **yes** | yes | `detail` |
  | `POST /api/complaints/{id}/details` | **yes** | yes | `detail` |
  | `GET /api/accounts` | no (usernames, not citizen PII) | no | none |
  | `POST /api/accounts` | no | no | `write` |
  | `POST /api/accounts/{id}/reset-password` | no | no | **`write`** (R4-5) |
  | `GET /api/session`, `POST /api/login`, `POST /api/logout`, `POST /api/password/change`, `GET /healthz` | no | no | login scopes / none |

  Adding a route without a row in this table fails SEC-T29: the test walks the route table and requires an entry for every path.
- **Search ceiling (rev 4, R4-2):** scope `search`, key = `user_id`, `RATE_LIMIT_SEARCH_PER_HOUR = 120`, one-hour window, on `POST /api/complaints/search`. Over ⇒ `429` + one `throttle_search` event on the crossing request (R4-6). Honest arithmetic: the page size is fixed at 25, so 120 calls bound a bulk walk to **3 000 rows/hour** — at pilot scale that is the whole complaint table, which means this ceiling bounds the **rate** of a scrape, not its eventual total. It is still worth having (it is the difference between "the table in one minute" and "a sustained hour that leaves a `throttle_search` row"), and threat #24 records the residual as **accepted** on exactly that basis. A clerk paging 25 at a time cannot get near 120 calls in an hour.
- **Authenticated write ceiling (rev 3, SEC-S4; third route added in rev 4, R4-5):** scope `write`, key = `user_id`, `RATE_LIMIT_WRITE_PER_HOUR = 60`, one-hour window, on `POST /api/complaints`, `POST /api/accounts` and `POST /api/accounts/{id}/reset-password`. Over ⇒ `429`. Rationale: BR-008 forbids deleting anything, so a hijacked or scripted session can permanently pollute the complaint table and the accounts list, and the only "recovery" is Rejecting each row by hand; a scripted reset loop is the same shape against credentials, revoking the victim's sessions repeatedly. **Honest multiple (rev 4, SEC-F6):** a busy clerk taking walk-in complaints at two to three minutes each peaks around **20–30/hour**, so 60/hour is **2–3× real peak**, not 20× — comfortably above a human day but close enough that a genuinely frantic morning could brush it, which is why the user-visible message says "please wait" and the runbook tells the operator to confirm with the office before treating a trip as a compromise. Status updates and detail edits are **not** in this scope: they create no new record and are already counted by `detail`.
- Username component is always `h(username)` = first 16 hex of SHA-256 over casefolded username + the dedicated **`USERNAME_HASH_SALT`** (R2-11 — separate from `SECRET_KEY`, which stays rotatable; this one is never rotated) — fixed width, no PII, no enumeration from the table.
- **Client IP (ADR-020, rewritten in rev 2 for SEC-F1; the peer is *made* trustworthy in rev 4, ADR-023).** `core/client_ip.py` is the only module that touches an IP header, and the rule is peer-first. **Precondition, and the reason the rule works at all: the server runs under `app.worker.RawPeerWorker`, whose `CONFIG_KWARGS = {"proxy_headers": False, "forwarded_allow_ips": []}` keeps `ProxyHeadersMiddleware` out of the ASGI stack (§2 row 0).** This is not the absence of a flag — with the stock `UvicornWorker` the middleware is present by default and rewrites `scope["client"]` from `X-Forwarded-For` before the application sees the request, so step 1 below would read an attacker-supplied value and the whole gate would invert silently. There is exactly one layer that interprets forwarding headers, and it is this module.
  1. Take the immediate peer address from the ASGI scope (`scope["client"][0]`) — with row 0 in force this is the raw TCP peer, i.e. whoever actually opened the connection to gunicorn.
  2. **If the peer is not inside `TRUSTED_PEER_CIDRS`** (the Fly proxy address set, explicitly configured — the app does not guess), **discard `Fly-Client-IP` and `X-Forwarded-For` entirely** and key the limiter on the peer address. A request that reaches the machine directly over the Fly private network therefore cannot choose its own bucket.
  3. If the peer *is* trusted: use `Fly-Client-IP` when present (Fly's proxy sets it on every forwarded request and overwrites any client-supplied value — but we do **not** rely on that overwrite alone; step 2 is what makes it safe). Otherwise fall back to the five-step XFF rule (strip `TRUSTED_PROXY_HOPS` entries from the right, never take the left-most).
  4. IPv6 normalised to /64. Unparseable result ⇒ one shared `"unknown"` bucket (fail closed, not open).
  5. `TRUSTED_PEER_CIDRS` and `TRUSTED_PROXY_HOPS` must both be explicitly set or startup fails (`selfcheck`). **There is no second layer to keep in sync** (rev 4): `selfcheck` asserts the *behaviour* of the running server — effective uvicorn `Config.proxy_headers is False`, **no `ProxyHeadersMiddleware` instance in the built ASGI stack**, and `FORWARDED_ALLOW_IPS` absent from the environment — rather than grepping `sys.argv` for a flag that gunicorn never accepted. Swapping the worker class back to the stock `UvicornWorker` in a Dockerfile therefore fails startup instead of quietly re-opening SEC-F1.
  **Named security test SEC-T21 — "the limiter key is the real peer":** runs **against a real gunicorn process started exactly as the container's CMD starts it** (the `live_server` fixture, over a TCP socket), not the bare ASGI app, because the defect it exists to catch lives in server configuration. Four cases:
    1. *Forged headers ignored.* The test peer is loopback and loopback is **not** in `TRUSTED_PEER_CIDRS`: send `RATE_LIMIT_LOOKUP_PER_MIN + 5` lookups, each with a different fabricated `Fly-Client-IP` **and** `X-Forwarded-For`; assert the tail is `429` and that `rate_limit_counter` gained **exactly one key** for the window, whose value **is the loopback address** — not any forged header value. (Asserting the key's value is what catches a stock worker: `ProxyHeadersMiddleware` would make the key the forged XFF.)
    2. *Gate not inverted.* Same server with loopback **inside** `TRUSTED_PEER_CIDRS`: the header **is** honoured.
    3. *Misconfiguration is visible (rev 4, SEC-F5).* The inverse of case 1: with loopback **not** trusted, two requests arriving from **two distinct real client addresses** produce **two distinct limiter keys**. A `TRUSTED_PEER_CIDRS` that does not match the real Fly proxy addresses collapses every client into the proxy's single bucket, which looks like "everything is 429" rather than like a security hole — this case fails if that happens.
    4. *Config assertion.* `selfcheck` fails when the app is started with the stock `UvicornWorker`, or with `FORWARDED_ALLOW_IPS` set, or when a `ProxyHeadersMiddleware` is present in the stack.
  /release repeats case 1 and case 3 against production from known source addresses (infrastructure.md §13).
- **Cleanup is deterministic (rev 2, PERF-F2; SQL corrected in rev 3, ARCH-F2):** when the upsert creates a new `window_start` for a key, two bounded `DELETE`s run on the same AUTOCOMMIT engine: (a) that key's rows older than two windows, and (b) the scope-agnostic sweep — again with a `ctid` sub-select, because PostgreSQL has no `DELETE … LIMIT`:
  ```sql
  DELETE FROM rate_limit_counter WHERE ctid IN (
    SELECT ctid FROM rate_limit_counter
    WHERE window_start < now() - make_interval(hours => :sweep_hours)   -- 2
    LIMIT 500);
  ```
  It is scope-agnostic because rev 1's per-key cleanup never touched rows whose key never recurs (one row per invented username, per rotated IP). Ceiling at pilot scale: normal traffic holds tens of rows; a sustained attacker rotating keys at 20 rps would add ~72k rows/hour, which the global sweep removes at up to 500 per limited request — enough at <1 rps of legitimate traffic. The **index on `window_start` ships in the initial migration** (rev 3, SEC-S6), so the sub-select is an index range scan from day one rather than a sequential scan that only gets attention after it hurts.
- Fixed windows allow up to 2× at a boundary — accepted (ADR-008); a sliding window is a code-only change if it ever matters.

## 6. Error model

Domain services raise typed errors; one exception handler set converts them:

| Domain error | HTTP | Envelope `code` |
|--------------|------|-----------------|
| `ValidationFailed` (Pydantic or `core.validation`) | 422 (400 for the lookup format case) | `invalid_input` + `fields[]` |
| `NotFound` | 404 | `not_found` |
| `NotAuthenticated` | 401 | `not_authenticated` — **strictly and only "there is no valid session"** (rev 3, ARCH-F3), and also the single generic answer to every failed login: unknown user, wrong password, or an OTP already spent (rev 4, R4-4). **There is no `invalid_credentials` code**; earlier documents that used that word meant this one |
| `InvalidCurrentPassword` (rev 3, ARCH-F3) | 422 | `invalid_current_password` + `fields.current_password`. A wrong *current* password on `POST /api/password/change` is a **field error inside a valid session**, not a missing session. Rev 2 returned `401 not_authenticated`, which the frontend maps to forced logout — so one typo destroyed the clerk's session and, when it happened on the forced-change screen after an OTP login, sent them back to a login they could only pass with the OTP again. The session is untouched by this error |
| `PayloadTooLarge` (rev 3, SEC-S8) | 413 | `payload_too_large` |
| `OtpExpired` (rev 2, R2-5) | 401 | `otp_expired` — distinct from `not_authenticated` so the clerk is told to ask for a new one instead of retrying a correct password |
| `PasswordChangeRequired` | 403 | `must_change_password` — **the standard envelope, no special shape** (rev 3, ARCH-F7): `{"error":{"code":"must_change_password","message":…,"request_id":…}}`. Rev 2 wrote it as a bare `{"must_change_password": true}` object in two documents, which would have been the only response in the API the client's single error mapper could not read |
| `Forbidden` | 403 | `forbidden` |
| `IllegalStatusTransition` | 422 | `illegal_transition` |
| `EditWindowExpired` | 422 | `edit_window_expired` |
| `UsernameTaken` | 409 | `username_taken` |
| `RateLimited` | 429 + `Retry-After` | `rate_limited` |
| `DependencyUnavailable` | 503 | `service_unavailable` |
| unhandled | 500 | `internal_error` (no detail, request ID only) |

Envelope: `{"error": {"code": "...", "message": "...", "fields": {...}, "request_id": "..."}}`.
`message` comes from `core/strings.py`; the **client renders its own copy keyed by `code`** so
translation later touches one module per side (AD-12). No stack trace, no SQL, no field value is
ever returned to a client.

## 7. Complaint number (ADR-016 proposal)

- Alphabet: Crockford base32 (`0123456789ABCDEFGHJKMNPQRSTVWXYZ` — no I, L, O, U).
- Body: **8 symbols = 40 bits** drawn from `secrets.randbelow`/`token_bytes` — meets the ≥40-bit, non-sequential floor (ADR-008 sec F11).
- Checksum: one further symbol = `alphabet[(Σ (i+1) × value_i) mod 32]`. Catches every single-symbol error and most transpositions.
- Canonical storage/comparison form: 9 uppercase symbols. Display and read-aloud form: `XXXX-XXXXX`.
- Normalisation on input: trim, uppercase, strip `-` and spaces, map `I`/`L`→`1`, `O`→`0`.
- Validation order (BR-015/FR-020): length+alphabet regex → checksum → **only then** a DB lookup. A typo or a dictionary sweep fails before any statement touches `complaint`, asserted by table name with the query-counter fixture.
- Generation: `INSERT` with the candidate; on unique-violation retry with a fresh number, max 5 attempts inside a savepoint (collision probability at 1.1×10¹² values and a few thousand rows is negligible; the retry exists so AC-003 holds under 20 simultaneous submissions).
- The number never appears in a URL, a log line, or a `security_event` row.

## 8. Status transitions (BR-002)

A single frozen map in `services/complaints/transitions.py`:

```
New        -> {In Progress}
In Progress-> {Resolved, Rejected}
Resolved   -> {Closed}
Rejected   -> {Closed}
Closed     -> {}
```

Enforced inside the row-locked transaction, so a concurrent update cannot slip an illegal
transition through. The API additionally returns the legal next statuses on the detail DTO, which is
what lets the UI offer only reachable options (UX decision 1) without duplicating the rule.

## 9. Audit history writes (FR-011, FR-014, BR-008, BR-011)

- `update_status` and `edit_details` both run: `SELECT … FOR UPDATE` → validate → update current row → **insert** the history row → commit. One transaction; a failure rolls back both halves, so a history row can never exist without its state change and vice versa.
- History rows record previous value, new value, actor `user_id`, timestamp, and (for status) the optional clerk note.
- Append-only is enforced twice: a `before_execute` hook raises on any `UPDATE`/`DELETE` whose target is `complaint_status_history`, `complaint_edit_history` or `security_event`; plus a grep assertion that no `update()`/`delete()` construct names those tables. Optional hardening for the data-api-architect: `REVOKE UPDATE, DELETE` from the application role in a migration if the platform permits a second role.
- **BR-011:** two concurrent updates serialise on the row lock; the later one wins the current status and **both** history rows survive. The client detects staleness by comparing the latest history id it holds and shows a non-blocking advisory (UX decision 4) — it never blocks the write.
- FR-012 window: `now() < created_at + EDIT_WINDOW_DAYS` checked in the service. The UI disabling the control is cosmetic.

## 10. Persistence and concurrency

- Two engines per worker: request engine `pool_size=4, max_overflow=2, pool_pre_ping=True, pool_recycle=1800`; limiter engine `pool_size=4, max_overflow=0` (deliberate: the limiter must not expand connections under the load it exists to refuse). Ceiling 10/worker ⇒ ≤20 at 2 workers.
- `statement_timeout = 10s` set on connect. One `Session` per request via a dependency with explicit commit/rollback in `finally`.
- Reads for the clerk list use keyset pagination (25 rows, `ORDER BY created_at DESC, id DESC`) so "Load more" is stable while rows are being inserted. The cursor is **opaque** to the client and travels in the `POST /api/complaints/search` body, never in a query string (R2-1).
- The list query never selects `name`/`phone`; the detail query does (response minimisation, ADR-007 sec F4).
- **Creation idempotency (rev 2, ADR-022/R2-6).** `POST /api/complaints` carries a client-generated `client_request_id` UUID. The insert relies on the unique index: on a unique violation the service re-reads the row with that `client_request_id` and returns it with `200` plus `duplicate: true`, instead of creating a second complaint. This is the one endpoint with an idempotency key, and the reason is REL-F1: the 10 s `AbortController` fires long before gunicorn's 30 s timeout, so a slow-but-successful create is exactly the case a clerk retries — and BR-008 means the duplicate can never be deleted, only Rejected, permanently polluting the audit trail. Status updates and edits get no key: a duplicate there is an extra history row, which is visible and harmless.
- **`/healthz` cost control (rev 2, ARCH-F9).** The endpoint is unauthenticated, on the public allow-list, and executes SQL — so its `SELECT 1` result is **cached in process memory for 10 s** (timestamp + boolean, per worker). A flood therefore costs one statement per worker per 10 s, not one per request, while the Fly check (every 15 s) and the pinger (every 5 min) still see fresh-enough truth. The cached value is never older than 10 s, which is well inside the 15 s check interval, so an unhealthy machine is still pulled from rotation within one to two checks. No limiter scope is needed on top of this.

## 11. `selfcheck` (production-config gate)

Console script *and* startup hook; fails startup in prod and fails CI with production-shaped env.
Checks: `SECRET_KEY` present and ≥32 bytes · **`USERNAME_HASH_SALT` present, ≥32 bytes and not equal
to `SECRET_KEY`** (R2-11) · `ENVIRONMENT=prod` and dev flag off · `DATABASE_URL` contains
`sslmode=require` or `verify-full` · **`TRUSTED_PEER_CIDRS` explicitly set and non-empty** (SEC-F1) ·
`TRUSTED_PROXY_HOPS` explicitly set · **proxy-header processing is provably off (rev 4, SEC-F1):
the effective uvicorn `Config.proxy_headers is False`, no `ProxyHeadersMiddleware` instance exists
anywhere in the built ASGI stack, and `FORWARDED_ALLOW_IPS` is not set in the environment — three
behavioural assertions, because the rev-3 argv grep tested for a gunicorn option that does not
exist** · **CORS `allow_methods` is exactly
`{GET, POST}`** (R2-2) ·
`COOKIE_SECURE` true ·
`samesite == "lax"` (never `"none"`) · no cookie `Domain` attribute · `__Host-` prefix on both
cookies · `ALLOWED_HOSTS` non-empty and free of `*` · CORS origins all `https://`, inside the
configured registrable domain, and not `*`-with-credentials · OpenAPI docs disabled
(`/docs`, `/redoc`, `/openapi.json` → 404).

## 12. CLI (operator, one-off Fly shell only)

| Command | Behaviour |
|---------|-----------|
| `bootstrap-admin` (FR-015/AC-019) | Interactive by default: prompts for username and `getpass` password; idempotent no-op if an admin clerk already exists; refuses to run when stdin is not a TTY unless `--from-env`; `--from-env` forces `must_change_password=True` and prints a reminder to delete the variable. Never a migration, never a fixture, no credential in the repo. |
| `reset-admin-password <username>` **(new in rev 2 — REL-F2)** | The lost-admin recovery path, and the *only* one. Works whether or not an admin already exists (unlike `bootstrap-admin`, which is a deliberate no-op then). Resolves the account, refuses if it is not `is_admin_clerk`, issues a **one-time password by exactly the same code path as `POST /api/accounts/{id}/reset-password`** (`services.accounts.issue_otp`: 12 chars/60 bits, `password_is_otp=true`, `password_set_at=now()`, 72 h expiry, all sessions for that user revoked), prints it **once** to the terminal, and writes a `security_event` row `password_reset_issued` with `reason_code=operator_cli`. Requires a TTY; refuses `--from-env`; never writes the OTP to a file or a log. Because it reuses the service, there is no second password policy and no second OTP format to keep in sync. |
| `unlock-account <username>` | Clears the login-limiter counters for that account (Q-015 break-glass). Writes a `security_event` row. **Does not change a password** — if the password itself is lost, `reset-admin-password` (admins) or an admin-issued reset in the UI (regular clerks) is the path. The two commands are deliberately distinct because they answer different questions: "I am locked out by the throttle" vs "I no longer know the password". |
| `selfcheck` | §11, also runs in CI. |

All four are `[project.scripts]` entry points on stdlib `argparse` (no Typer/click — ADR-010
dependency budget), reachable only through `fly ssh console`; none is exposed over HTTP, and a test
asserts no router imports `app.cli`.

## 13. Test hooks this layout must keep true

The 20 named security assertions from tech-stack § Tooling map onto these modules: middleware order
(§2), session behaviour (§3), CSRF both paths and the anonymous-flood containment (§4), limiter
derivation/atomicity/burst containment (§5), `response_model` on every route and no `name`/`phone`
in the list schema (§10), append-only enforcement (§9), deny-by-default over the route table (§2),
`must_change_password` on a direct API call (§2), no password or OTP in logs or `security_event`
(§6, observability-reliability.md), and `selfcheck` green with production-shaped env (§11).

**Added in rev 2** (these are new named assertions, not restatements):

| ID | Assertion |
|----|-----------|
| SEC-T21 | **(rev 4)** Four cases against a **real gunicorn process started with the container CMD**, not the ASGI app — §5: (1) forged `Fly-Client-IP`/`X-Forwarded-For` from an untrusted loopback peer produce exactly one limiter key **whose value is the loopback address**; (2) the header *is* honoured when the peer is inside `TRUSTED_PEER_CIDRS`; (3) **two distinct real client addresses produce two distinct limiter keys** (catches a `TRUSTED_PEER_CIDRS` mismatch that would collapse everyone into one bucket, SEC-F5); (4) `selfcheck` fails with the stock `UvicornWorker`, with `FORWARDED_ALLOW_IPS` set, or with a `ProxyHeadersMiddleware` in the stack |
| SEC-T22 | **(rev 4, R4-1)** OTP consumption by hash destruction: (a) an OTP login succeeds once and a **second** login with the same OTP returns **`401 not_authenticated`**, with no password change in between — and the stored `password_hash` differs from the value it had before the first login; (b) the successful OTP login yields a session that can only reach change-password / logout / `GET /api/session`, and **that session completes a password change with no `current_password` supplied**; (c) an un-consumed OTP past `password_set_at + OTP_EXPIRY_HOURS` returns `otp_expired` (R2-5/R4-1) |
| SEC-T23 | Login issues a new cookie and revokes **only** the presented session: a second, independently established session for the same user is still valid afterwards; a password change revokes both (R2-4) |
| SEC-T24 | No route in the route table uses a method outside `{GET, POST}`, and CORS `allow_methods == {GET, POST}` (R2-2) |
| REL-T25 | `POST /api/complaints` replayed with the same `client_request_id` returns the same complaint id and leaves the row count unchanged (R2-6) |
| PERF-T26 | After a burst that creates limiter rows under many never-recurring keys, the global sweep brings the table back under its ceiling within the specified number of subsequent limited requests (§5) |
| PERF-T27 | Expired session rows are gone after a subsequent successful login; the sweep statements are row-bounded via the `ctid` sub-select and use the `SESSION_IDLE_MINUTES` setting, not a literal interval (§3) |

**Added in rev 3:**

| ID | Assertion |
|----|-----------|
| SEC-T28 | A sustained `429` burst on one `(scope, key, window_start)` writes **exactly one** `throttle_*` `security_event` row, not one per request (§5, SEC-S2) |
| SEC-T29 | **(rev 4, R4-2)** Driven by the **per-route PII classification table** in §5, not by schema introspection: the test walks the route table, fails if any route has no row in the classification table, and asserts each route carries exactly the scope(s) its row names. Plus the keying property: reads split across two freshly minted sessions for the same user share one `detail` counter; and specifically `GET /api/complaints/{id}/activity` is counted under `detail` while `POST /api/complaints/search` is counted under `search` (§5, SEC-F3) |
| SEC-T30 | **(rev 4)** `POST /api/complaints`, `POST /api/accounts` and `POST /api/accounts/{id}/reset-password` return `429` past `RATE_LIMIT_WRITE_PER_HOUR` for one user; `POST /api/complaints/search` returns `429` past `RATE_LIMIT_SEARCH_PER_HOUR`; and one `POST /api/complaints` increments **both** the `write` and the `detail` counter before the handler runs (§5, R4-3/R4-5) |
| SEC-T33 | **(rev 4, R4-5)** Repeated failed logins for one `(username, IP)` write **at most one** `login_failure` row per 15-minute window, and none at all once the `login_ip` tier is past its limit (§5, observability §2) |
| SEC-T31 | A request with `Content-Length` above `MAX_REQUEST_BODY_BYTES` is rejected `413` and the route handler never runs (§2, SEC-S8) |
| ARCH-T32 | A wrong current password on `POST /api/password/change` returns `422 invalid_current_password` with `fields.current_password`, and the session is still usable afterwards (§6, ARCH-F3) |
| ARCH-T33 | `POST /api/logout` returns a token that verifies against the **anonymous** HMAC path, and `POST /api/password/change` sets a new `__Host-session` cookie (§4, ARCH-F4) |
