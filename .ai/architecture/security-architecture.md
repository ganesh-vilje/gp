# Security Architecture

rev 3 (2026-09-09). Binding: ADR-007 (auth/sessions/CSRF), ADR-008 (limiter, number entropy),
ADR-023 (rev 4: the app is the only interpreter of forwarding headers, enforced by a worker class),
ADR-010 (supply chain), ADR-011 (security_event), ADR-013 (public DTO). Threat coverage lives in
`.ai/security/threat-model.md`; this document defines the controls.

## 1. Authentication model

| Aspect | Decision |
|--------|----------|
| Credential | username + password only (NFR-003). No email, no SMS, no OAuth, no MFA at launch (TOTP for the admin clerk is a costed, non-adopted option) |
| Hashing | Argon2id via `argon2-cffi`, `m=9216 KiB, t=4, p=1`; `check_needs_rehash()` on successful login. Memory chosen for the 512 MB instance; raise `m` first if it is upsized |
| Credential check | constant-time by construction; the same generic failure for unknown user and wrong password — never "user does not exist" |
| Session | opaque `secrets.token_urlsafe(32)`; DB stores only SHA-256; cookie `__Host-session`, `httpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, no `Max-Age` |
| Idle / absolute | 45 min idle (ADR-019) / 9 h absolute / browser-close |
| **Issuance on login** (ADR-021, rev 2) | **Always** mint a new token and row; revoke **only the session presented in this request's cookie**, if any. Fixation is defeated (the planted cookie's session is the one killed) *and* a clerk's other device stays logged in — office desktop plus phone is a real pattern here. Rev 1 said "revoke old on login", which the API contract had read as "no rotation at all"; this row is the single answer (SEC-F5 / ARCH-F4) |
| Revocation | **all** rows for a user on self password change, admin reset and the `reset-admin-password` CLI; the current row only on plain logout; `revoked_at` checked on every request |

### Session lifecycle

```
login OK ──► issue NEW row (csrf_token, absolute_expires_at = now+9h) ──► set __Host-session
   │         └─ revoke ONLY the session whose token arrived in this request's cookie (if any).
   │            Other devices' sessions are untouched. (ADR-021)
   ├─ each request: token hash → row; revoked? absolute passed? idle > 45m? ─► 401 + revoke
   ├─ each request: last_seen_at = now
   ├─ password change / admin reset / reset-admin-password CLI
   │        ─► revoke ALL rows for the user; self-change then issues one fresh row
   ├─ successful login also runs the two bounded session-sweep DELETEs (backend §3)
   └─ logout ─► revoke this row, clear cookie
```

## 2. Authorization model

Deny-by-default in middleware (6). The **entire** public allow-list is four entries:
`POST /api/lookup`, `POST /api/login`, `GET /api/session`, `GET /healthz`. Any route added later is
closed unless someone edits that list — and a route-table-parametrised test proves it (AC-015, both
directions). `is_admin_clerk` is the only elevation; there is no staff/superuser concept.

### Permission matrix

| Capability | Citizen (anon) | Clerk | Admin clerk | Operator (shell) |
|---|---|---|---|---|
| Public lookup by exact number | ✅ | ✅ | ✅ | — |
| List / search / filter complaints | ❌ 401 | ✅ | ✅ | — |
| View complaint detail incl. name/phone (FR-016) | ❌ | ✅ | ✅ | — |
| Create complaint | ❌ | ✅ | ✅ | — |
| Update status + note | ❌ | ✅ | ✅ | — |
| Edit citizen details within 7 days (FR-012) | ❌ | ✅ | ✅ | — |
| View status + edit history | ❌ | ✅ | ✅ | — |
| Delete anything | ❌ (no such capability exists for anyone) | ❌ | ❌ | ❌ |
| List clerk accounts | ❌ | ❌ 403 | ✅ | — |
| Create clerk account (FR-017) | ❌ | ❌ 403 | ✅ | — |
| Reset a clerk password (FR-018) | ❌ | ❌ 403 | ✅ | — |
| Change own password | ❌ | ✅ | ✅ | — |
| Bootstrap first admin (FR-015) | ❌ | ❌ | ❌ | ✅ one-time |
| Clear login counters (`unlock-account`) | ❌ | ❌ | ❌ | ✅ break-glass |
| **Reset a *lost admin* password (`reset-admin-password`)** | ❌ | ❌ | ❌ | ✅ break-glass, rev 2 |
| Disable/offboard a clerk | ❌ | ❌ | ✅ *via* reset-and-discard-OTP (R2-10) — no dedicated capability | ✅ same |

Enforcement points: the allow-list (anonymous), `require_admin_clerk` (role), and the service layer
(ownership/window rules). The frontend's hidden nav link is cosmetic; FR-019 is tested by a direct
API call from a regular clerk's session.

## 3. Password lifecycle

- **Policy** (`core/validation.validate_password`, used by both creation and change): ≥ **12** characters (ADR-007 C5, BR-016 rev 6); not similar to the username (casefold containment + ratio); not entirely numeric; not in the vendored ~10k common-password list (Django's BSD-3 file, attributed in dependency-strategy.md §5). Returns a list of failures so the UI can show field-specific errors.
- **One-time password (BR-016):** `secrets.choice` over a 32-character unambiguous alphabet (no `0/O/1/l/I`), **12 chars = 60 bits**; returned **exactly once** in the create/reset JSON response with `Cache-Control: no-store, no-cache, must-revalidate` and `Referrer-Policy: no-referrer`; sets `must_change_password=true`; revokes every existing session for that user; **never logged, never in `security_event`, never retrievable again**.
- **How "single-use" is actually true (rev 4, R4-1 — this replaces rev 3's version, which retired a flag but not the credential).** The clerk account carries `password_is_otp boolean NOT NULL DEFAULT false` and `password_set_at timestamptz NOT NULL`, both written by `services.accounts.issue_otp`. Rev 2 claimed single-use because a password *change* clears the flag — but nothing forced the change, so an abandoned OTP stayed valid for 72 h. Rev 3 cleared `password_is_otp` at login and called that consumption; it was not. The OTP's **Argon2 hash was still the account's password hash**, so a second login with the same OTP verified successfully, and worse, clearing the flag switched **off** the expiry check in step 2 below, which is guarded by it — the "consumed" OTP became a permanent password. The marker `must_change_password=true AND password_is_otp=false` could not be used to detect the spent state either, because `bootstrap-admin --from-env` produces exactly that state legitimately. **Consumption must destroy the credential.** The login transaction, in order:
  1. Argon2 verifies the submitted password against the stored hash, as for any login.
  2. If `password_is_otp` and `now() >= password_set_at + OTP_EXPIRY_HOURS` ⇒ fail with `otp_expired` (401), no session. This check stays live for as long as the OTP is **un-consumed**, which is exactly what step 3 preserves.
  3. If `password_is_otp` and it is still in date, the login succeeds and, in the **same transaction**, the server **overwrites `password_hash` with the Argon2 hash of a freshly generated 256-bit random value** (`secrets.token_bytes(32)`) that is **discarded**: never stored, never returned, never logged, never displayed, known to nobody including the operator. It then sets `password_is_otp = false` and **leaves `must_change_password = true`**. No counter, no consumed-token table, no new column.
  4. The session issued by that login is a **must-change-password session**: the middleware gate confines it to change-password, logout and `GET /api/session`.
  5. That session's password change **takes no current password** — see the next-but-one bullet — so the unknowable hash never blocks the real clerk. This is why destroying the hash is safe as well as sufficient.
  A **second** login presenting the same OTP now fails Argon2 verification and returns the generic **`401 not_authenticated`** (rev 4, R4-4: `invalid_credentials` is not a code in this system; every failed login looks identical, which is threat #30's control). **Operational consequence, in the runbook:** if the clerk abandons the browser before completing the change, the OTP is spent *and* the account has no usable password, so the admin issues a **new** OTP (`POST /api/accounts/{id}/reset-password`, or `reset-admin-password` for an admin). That is a two-minute redo against a credential that would otherwise stay live for three days. Reissuing overwrites the hash and both fields, so an older OTP dies immediately. Test SEC-T22 covers reuse, expiry and the no-current-password change.
- **Forced change** is enforced in middleware, not at login: every authenticated request except change-password, logout and `GET /api/session` returns **`403` in the standard error envelope** — `{"error":{"code":"must_change_password","message":…,"request_id":…}}` (rev 3, ARCH-F7: rev 2 wrote a bare `{"must_change_password": true}` body, which would have been the one response shape the client's single error mapper could not parse). A bookmarked deep link or a direct API call cannot bypass it.
- **Changing the password itself:** `POST /api/password/change` has two shapes. **From a must-change session** (the state an OTP login or a `bootstrap-admin --from-env` account is in) it takes **`new_password` only — no `current_password`**: the session itself is the proof of possession, and after R4-1 the previous credential is a discarded random value nobody can supply. **From a normal session** it requires `current_password`, and a wrong one is `422 invalid_current_password` with `fields.current_password`, **not** `401` (rev 3, ARCH-F3). `401` means "no valid session" and nothing else, because the client turns it into a forced logout. On success the server revokes all sessions and **sets a new `__Host-session` cookie on that same response**, so the clerk stays signed in (ARCH-F4).
- **Residual, recorded (ADR-007 H-B):** the OTP transits the clerk's browser, so a malicious npm package inside that page can capture every OTP issued while it is open. Bounded by single-use + 72 h + forced change + session revocation + `connect-src` + the idle window; **not eliminated**. The named alternative (shell-only issuance) costs FR-018 and is a GATE decision, not an implementation one.
- **Login protection:** three counters, cheapest-first, with the per-IP ceiling short-circuiting before any username-keyed row is written; per-account backoff is `429 + Retry-After ≤5 s`, **never a lock, never a thread sleep** — a hard lock would be a self-DoS in an office of ≤6 accounts. **Rev 2 (SEC-F6): the "IP with a recent successful login is exempt from per-account backoff" carve-out is removed** — no component stored recent-success IPs, so it was a control that did not exist. Nothing replaces it, and nothing needs to: the office's protection against a hostile lockout attempt is that tier 3 is a ≤5 s delay on a *correct* password, not a lock (threat #36 is re-argued on that basis alone). Unlock paths: wait the window, another admin resets, or the operator runs `unlock-account`.

- **Lost admin password — the recovery path (rev 2, REL-F2).** Rev 1 had none: `bootstrap-admin` is a deliberate no-op once an admin exists, `unlock-account` clears counters but never touches a password, OQ-5's default is that no second admin is created, and A12 says one admin in practice. The path is now the operator CLI **`reset-admin-password <username>`** on a Fly shell (backend §12): it reuses `services.accounts.issue_otp`, so the OTP shape, the 72 h expiry, the forced change and the revoke-all are identical to the in-app reset; it prints the OTP once to the terminal, writes a `password_reset_issued` `security_event` with `reason_code=operator_cli`, and requires a TTY. It is distinct from `unlock-account` on purpose — throttled ≠ forgotten. Step-by-step in infrastructure.md §12 runbook. This makes the human, who holds the Fly account, the recovery authority; OQ-5 (second admin) becomes an availability convenience rather than the only way back in.

- **Offboarding a clerk without a `disabled_at` column (rev 2, ARCH-F10, decision R2-10).** There is no account-disable endpoint and no soft-delete flag. The documented procedure is: **the admin issues a password reset for that clerk and discards the OTP.** That single action revokes every live session for the account immediately, replaces the credential with one nobody has seen, and the replacement itself expires in 72 h (R2-5) after which the account cannot be logged into at all. Names stay on history rows, which BR-008 requires. The gap being accepted: the account still appears in the accounts list and an admin must remember why, so the runbook (infrastructure.md **§11**) carries the step. A real `disabled_at` is a small additive migration if the office ever has turnover worth automating.

## 4. CSRF

Three layers on every unsafe method, with **no exemption list in the codebase**:
`SameSite=Lax` cookie · `Origin` header against the same allow-list as CORS (missing or unlisted ⇒ 403) ·
`X-CSRF-Token` compared with `hmac.compare_digest`. Two token paths: session-bound when
authenticated (rotated with the session, returned in the **login** and **password-change** bodies);
**stateless** `hmac_sha256(SECRET_KEY, __Host-csrfseed)` when not — so the unauthenticated path
executes zero SQL and an anonymous flood cannot grow a table or trip the fail-closed limiter.
**`POST /api/logout` returns a fresh *anonymous* token, not a session-bound one** (rev 3, ARCH-F4):
the session it just revoked cannot carry a token, so the response seeds `__Host-csrfseed` if absent
and returns the stateless HMAC — which is what lets the now-anonymous page POST `/api/login` or
`/api/lookup` without another round trip. Rev 2 said "session-bound" here and in backend §4; the API
contract had it right and these two documents were wrong.

The public lookup POST is deliberately **not** exempt: without the token an attacker could drive
complaint-number guessing through unwitting visitors' browsers and spread it across their IPs,
defeating the per-IP limiter.

## 5. Transport, cookies, CORS, headers

- **Domain layout:** `www.<domain>.in` / `<domain>.in` (static) and `api.<domain>.in` (API) — **one registrable `.in` domain**, which is what makes a `SameSite=Lax` cookie work cross-origin/same-site. `SameSite=None` is **forbidden**. The custom domain must be attached to both hosts **before any real citizen data is entered** (/release gate). If a single registrable domain ever becomes impossible, the answer is a BFF proxy returning to GATE_2 — never `SameSite=None`.
- **TLS** terminated at each platform edge; HSTS `max-age=31536000; includeSubDomains` (no `preload`); the edge's HTTP→HTTPS redirect is verified with one `curl` at /release rather than adding a redirect middleware. **Rev 4 (SEC-F1): the server runs under `app.worker.RawPeerWorker`, which sets `proxy_headers=False`** (backend §2 row 0 — a library default had to be overridden, not a flag omitted), so `request.url.scheme` is `http` inside the container and a scheme-based redirect middleware would loop forever — one more reason it does not exist. Nothing in the API reads the scheme: `Secure`/`__Host-` come from `COOKIE_SECURE`, HSTS is unconditional in prod, and no absolute URL is generated. **`X-Forwarded-Proto` has no consumer at all** (rev 4, SEC-F8): it is not in `core/client_ip.py`'s remit and no other module reads it; it appears only on the CI grep block-list, so that a future reader of it has to justify itself in review.
- **CORS:** explicit list of the two production origins (plus `http://localhost:3000` only when the dev flag is on), `allow_credentials=True`, methods **exactly `GET,POST`**, headers `content-type,x-csrf-token`, `max_age=600`. Preview URLs are deliberately excluded, so a preview build cannot reach production data. **Rev 2 (SEC-F8/ARCH-F2):** `GET,POST` is kept as a hard, `selfcheck`-asserted invariant rather than widened for a `PATCH`; the API therefore has **no** `PATCH`/`PUT`/`DELETE` verb anywhere, and field correction is `POST /api/complaints/{id}/details`. A narrower method set is one fewer thing a future route can quietly rely on, and the assertion is cheap (`allow_methods == {"GET","POST"}` plus a route-table check).
- **No sensitive value in a URL (rev 2, SEC-F3/ARCH-F1):** complaint numbers, citizen names and phone numbers never appear in a path segment or a query string, because the gunicorn access log, the browser history, the `Referer` on any future outbound link and any intermediary all capture those. Clerk list/search is `POST /api/complaints/search` with the criteria in the JSON body. This is what makes the never-log list (§8) true rather than aspirational.
- **API response headers:** HSTS, `Referrer-Policy: no-referrer`, `Permissions-Policy: geolocation=(), camera=(), microphone=()`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store` on authenticated and lookup responses, `CSP: default-src 'none'; frame-ancestors 'none'; base-uri 'none'`.
- **Static-site headers:** see frontend-architecture.md §8 (hashed `script-src`, `connect-src` naming exactly the API origin).
- **OpenAPI docs return 404 in production.** Stated honestly: this is hygiene, not an anti-enumeration control — the bundle publishes every path and schema anyway. Authorization is the control.

## 6. Input validation and output encoding

- **Body size is capped before parsing (rev 3, SEC-S8):** middleware rejects `Content-Length > MAX_REQUEST_BODY_BYTES` (64 KB) with `413 payload_too_large`, and caps the read for length-less streams, **before** the body is buffered or JSON-parsed. Pydantic's `max_length` only applies after the whole body is in memory, and rev 2's other answer — "platform edge body limits" — is a limit we neither configured nor read. Threat #37 cites this.
- Every request body is a Pydantic model with `extra="forbid"` — an injected field is a 422, which is also how BR-009 (no government ID) stays true structurally.
- Field rules: name ≤100; description ≤2000; phone digits with optional leading `+`, 7–15; username `^[A-Za-z0-9_]{3,30}$`; complaint number regex + checksum before any DB access.
- **SQL:** SQLAlchemy parameter binding everywhere; the one hand-written statement (the limiter upsert) is a bound `pg_insert(...)` construct. No string-built SQL anywhere; Ruff `S` flags it.
- **Output:** React JSX escaping is the primary XSS control; `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function` and inline styles are grep-blocked in CI; any user-supplied `href` must pass a scheme allow-list (`https:`, `mailto:` only).
- Every response route declares a `response_model`; a route-table test fails on `response_model=None`.

## 7. PII handling and data minimisation

| Field | Collected | Stored | Public API | Clerk list | Clerk detail | Logs |
|-------|-----------|--------|------------|-----------|--------------|------|
| Citizen name | yes (BR-007) | yes | **never** | **no** | yes (FR-016) | never |
| Citizen phone | yes (BR-007) | yes | **never** | **no** | yes | never |
| Description | yes | yes | never | truncated snippet | yes | never |
| Clerk note | optional | yes | **never** (ADR-013) | no | yes | never |
| Complaint number | generated | yes | yes | yes | yes | **never** |
| Status, date logged | derived | yes | yes | yes | yes | ok |
| `public_update` | derived enum from status | — | yes | — | — | ok |
| Government ID | **never collected** (BR-009) | — | — | — | — | — |

The public DTO is exactly `{complaint_number, status, date_logged, public_update}` with
`extra="forbid"`; a test asserts that for a record holding both a name and a phone, neither string
appears anywhere in the serialised response. Clerk list responses omit `name`/`phone` entirely so a
compromised page cannot vacuum the contact list from one call — a real reduction, not a fix.

**Bulk read, stated honestly (rev 2, SEC-F4).** A clerk session can list every complaint and then
open each one, and the detail response carries name and phone. That is the requirement (FR-007,
FR-016), so it cannot be designed away; response minimisation only forces one request per record.
The bounding control, corrected in rev 3 (SEC-S3) and **completed in rev 4 (R4-2)**, is a limiter
scope `detail` keyed by **`user_id`** with `RATE_LIMIT_DETAIL_PER_HOUR = 120` (backend §5), applied to
every response that carries `citizen_name`/`citizen_phone` **in any form**: `GET /api/complaints/{id}`,
`GET /api/complaints/{id}/activity` (its `previous_value`/`new_value` pairs **are** the name and phone
whenever a `citizen_name`/`citizen_phone` edit is in the history — rev 3 missed this because the route
does not declare those field names), `POST /api/complaints/{id}/status`,
`POST /api/complaints/{id}/details` and `POST /api/complaints` (both scopes, R4-3).
`POST /api/complaints/search` returns no name or phone but hands out 25 complaint records a call and
was unbounded; it gets its own scope **`search` at 120/user/hour** (R4-2). Coverage is driven by the
**per-route PII classification table in backend §5**, which the contract repeats and SEC-T29 reads —
not by "does the response model mention `citizen_name`", which is the introspection rule that let
these two routes through. Rev 2 additionally keyed the ceiling on the session hash, which login mints
for free (ADR-021 does not revoke other devices); keyed on the user it is the smallest identity an
attacker cannot mint more of. **Stated honestly:** a hijacked session now reads at most 120 detail
records and pages at most 3 000 search rows an hour, leaving one `throttle_detail`/`throttle_search`
row per window (SEC-S2, R4-6). At pilot scale 3 000 rows/hour is still the whole table, so this
bounds the **rate** of a scrape, not its total — **threat #24 stays `accepted`, not `mitigated`**.

**Authenticated writes are also bounded (rev 3, SEC-S4; third route in rev 4, R4-5).** Scope `write`,
key `user_id`, `RATE_LIMIT_WRITE_PER_HOUR = 60`, on `POST /api/complaints`, `POST /api/accounts` and
`POST /api/accounts/{id}/reset-password`. BR-008 means
nothing can be deleted, so a hijacked session scripting inserts leaves permanent rows that an admin
can only Reject one by one. **Corrected multiple (rev 4, SEC-F6):** a busy clerk peaks at roughly
**20–30 complaints/hour** (two to three minutes of typing each), so 60/hour is **2–3× real peak**,
not the 20× rev 3 claimed — above any real day, but close enough that the operator response is
"investigate, and confirm with the office" rather than "assume compromise". Read auditing was reconsidered and
still rejected (OQ-9, whose text now records the user-keyed R3-2 ceiling rather than rev 2's
session-keyed one): at 1–5 known clerks who all legitimately read everything, a `complaint_viewed`
event per open is noise nobody will read, and the limiter gives the same "someone is vacuuming"
signal for one config value instead of a table.

**No third-party processor of citizen data exists**: no error tracker, no analytics, no CDN-hosted
script or font, no AI (ADR-012). Every npm package is bundled at build time and served from our own
origin; the trust shift is to build time, which is what §9 covers.

## 8. Logging rules

Structured JSON to stdout: `timestamp, level, event, request_id, method, path, status, duration_ms,
user_id (when authenticated), derived_ip`.

**Never-log list — binding, and asserted by tests:**
passwords (submitted or issued, in any form) · one-time passwords · session tokens or cookie values ·
CSRF tokens or seeds · **complaint numbers** · citizen name, phone, description or clerk notes ·
`Authorization`/`Cookie`/`X-CSRF-Token` headers · full request or response bodies · `DATABASE_URL`
or `SECRET_KEY` · stack traces returned to a client (they go to stdout with the request ID only).

A redaction filter in `core/logging.py` is the backstop, but the rule is "do not pass it in", and
tests assert the submitted password string and the issued OTP never appear in captured records.

`security_event` (append-only, in Postgres, inside daily backups) records: login success, login
failure, admin password reset issued, account created, throttle events. **Column names are the
schema's, used identically in every document (rev 3, ARCH-F5):** `event_type`, `actor_user_id`
(FK, when the actor is authenticated), `actor_username_hash` (`h(username)`, when they are not),
`target_user_id` (the account an admin action was performed *on* — the only way to answer "who reset
whose password"), `derived_ip`, `reason_code`, `created_at`. Never a password, never an OTP, never a
complaint number, no free text, no headers, no body. Throttle events are written **once per
`(scope, key, window)`**, not once per refused request (SEC-S2).

## 9. Secrets management

- Production secrets live only in `fly secrets` (encrypted at rest, injected as env vars). Not in the repo, not in `fly.toml`, not in CI, not in a migration, not in a fixture.
- **No deploy credential exists in CI at all** — there is no deploy job (ADR-009). GitHub Actions run with `permissions: contents: read`, third-party actions are SHA-pinned, `pull_request_target` is not used, and no secret is exposed to fork PRs.
- **Two separate secrets, not one (rev 2, SEC-F12).** `SECRET_KEY` has exactly **one** consumer, the anonymous CSRF HMAC, and is freely rotatable: rotation invalidates outstanding CSRF seeds only, a page refresh recovers, nobody is logged out. `USERNAME_HASH_SALT` is a distinct secret with one consumer, `h(username)` for limiter keys and `security_event.actor_username_hash`, and is **never rotated** — rotating it would zero every live brute-force counter and orphan every historical actor hash, i.e. destroy the exact record the table exists to keep. `selfcheck` fails if they are equal or either is <32 bytes. Recording the split is the point: rev 1 gave one key two lifetimes.
- **Transport to Postgres (SEC-F11):** `sslmode=verify-full` if Fly publishes a CA certificate for Managed Postgres (checked at /release, one env change); otherwise `sslmode=require` and the residual — TLS without server-identity verification inside Fly's private network — is **accepted and recorded here**, not silently assumed away. `selfcheck` rejects anything weaker than `require`.
- The backup encryption key is held by the human (ADR-002 Q6) and never stored in the platform.
- Local dev uses a `.env` that is git-ignored, with a committed `.env.example` containing **names only**.

## 10. Supply-chain controls

`uv.lock` and `package-lock.json` committed; exact versions, no carets · `uv sync --frozen` and
`npm ci --ignore-scripts` · `pip-audit` and `npm audit --audit-level=high` + `npm audit signatures`
in CI and on a monthly schedule · Dependabot for `pip`, `npm` and `docker`, auto-merging **only**
patch/minor bumps of packages already in the lockfiles, with a 7-day minimum release age for npm ·
any *new* dependency needs a second pair of eyes · base image digest-pinned with a monthly CI
rebuild · dependency budgets (≤10 Python runtime, ≤6 npm runtime) as a brake on tree growth.

**Stated honestly (R16):** ~350–450 resolved npm packages run inside the clerk's page. A malicious
release has full clerk-session capability, including every OTP issued while the page is open. CSP
`connect-src`, the idle window and response minimisation *bound* the damage; nothing here *detects*
a zero-day malicious release. This is accepted, not solved.

## 11. What is deliberately not built

MFA/TOTP (offered, no requirement) · CAPTCHA (out of MVP scope, ADR-008) · a WAF/edge rate-limit
rule (welcome later as defence in depth; would move AC-011 outside the test suite) · account
lockout (self-DoS at this scale) · self-service password reset (A10 — no email channel exists) ·
field-level encryption (the whole DB is encrypted at rest; per-field crypto would break search and
add a key-management burden with no named threat).
