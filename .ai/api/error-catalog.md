# API Error Catalog — panchayat-complaint-tracker

rev 4 (2026-09-09), rework loop 3 (final). Single envelope, binding per backend-architecture.md §6.
Closes ARCH-F7, ARCH-F12, SEC-F2 (`otp_expired`) (rework loop 1), ARCH-F3/R3-5 (`invalid_current_password`),
R3-6/SEC-S8 (`payload_too_large`), SEC-S3/SEC-S4 (rate-limit scope/key table) (rework loop 2), and
ARCH-F3/R4-4 (`invalid_credentials` removed — every failed login is `401 not_authenticated`), SEC-F3/R4-2
(`search` scope, `detail` widened to `/activity`), ARCH-F2/R4-3 (`POST /api/complaints` counts against
both `write` and `detail`), ARCH-F4/SEC-F4/R4-5 (`reset-password` joins `write`) (rework loop 3) on the
error-catalog side.

```json
{
  "error": {
    "code": "invalid_input",
    "message": "Enter a valid complaint number",
    "fields": { "complaint_number": "invalid_format" },
    "request_id": "b3f1..."
  }
}
```

- `code` — stable machine string, the only thing the frontend switches on.
- `message` — server-rendered English string from `core/strings.py`, shown only as a fallback; the
  client renders its own copy keyed by `code` so translation later touches one module per side (AD-12).
- `fields` — present only for `invalid_input`; `{field_name: reason_code}`, never the submitted value.
- `request_id` — echoes `X-Request-ID`; the only thing an operator needs to find the matching stdout
  log line. Never a stack trace, never SQL, never a field value.

**Never in `message` or `fields`:** a password, an OTP, a complaint number, a citizen name/phone, a
session/CSRF token, or anything from the never-log list (security-architecture.md §8) — the same rule
applies to responses, not only logs.

## Codes

| Code | HTTP | Raised when | Public-safe message key |
|---|---|---|---|
| `invalid_input` | 422 (400 for the public-lookup format case, BR-015/AC-018) | A request body fails Pydantic validation or a `core.validation` rule (phone shape, username shape, password policy, complaint-number format/checksum) | `errors.invalid_input` (generic); `lookup.invalid_format` for the public-lookup 400 case ("Enter a valid complaint number") |
| `not_found` | 404 | Public lookup: well-formed number, no matching row (BR-004, AC-007). Clerk detail/activity: `{id}` doesn't exist | `lookup.not_found` ("We couldn't find a complaint with that number…"); `complaints.not_found` ("Couldn't load this complaint.") — same code, context-specific wording key |
| `not_authenticated` | 401 | **No valid session presented** on any route requiring auth: no cookie, or the session row is missing/expired/revoked (ARCH-F7 — this is the anonymous-request case, distinct from the row below). **Also the single generic response to every failed `POST /api/login` attempt** — unknown username, wrong password, or an already-consumed OTP (rev 4, R4-4: **there is no `invalid_credentials` code in this system**; a second login with a consumed OTP fails Argon2 verification and lands here, identically to any other wrong password). **Strictly and only these two cases** (rev 3, R3-5/ARCH-F3; rev 4, R4-4) — never used for a field error inside a valid session; the client maps this code to a forced logout, so any other meaning would destroy a session over a typo | `errors.not_authenticated` |
| `invalid_current_password` | 422 | **rev 3 (R3-5/ARCH-F3).** `POST /api/password/change`, voluntary path: the submitted `current_password` does not verify against the stored hash. A field error inside a valid, untouched session — never `401` (rev 2's answer here was wrong: it forced a logout on one typo, and on the OTP forced-change screen left the clerk unable to get back in without the now-spent OTP) | `fields.current_password`; message key `password_change.invalid_current_password` ("That's not your current password.") |
| `payload_too_large` | 413 | **rev 3 (R3-6/SEC-S8).** Any request whose `Content-Length` exceeds `MAX_REQUEST_BODY_BYTES` (64 KB), rejected before the body is parsed; also raised while reading a length-less stream that exceeds the same cap | `errors.payload_too_large` ("That request is too large.") |
| `otp_expired` | 401 | **rev 2 (R2-5/SEC-F2), mechanism corrected rev 4 (R4-1).** Login: the Argon2 hash verified, but the credential is still `password_is_otp` (i.e., **un-consumed**) and `now() >= password_set_at + OTP_EXPIRY_HOURS`. Distinct from `not_authenticated` so the clerk is told to ask their admin for a new one-time password rather than retry a correct one. **Distinct from a spent (already-consumed) OTP, which is a plain `not_authenticated`** (rev 4, R4-1/R4-4) — the consuming login destroyed `password_hash`, so a second login with the same OTP fails Argon2 verification outright and is indistinguishable from any other wrong password, by design (no "this OTP was already used" signal to a guesser) | `login.otp_expired` ("This one-time password has expired — ask your admin for a new one.") |
| `must_change_password` | 403 | Authenticated, but `must_change_password=true`, calling any route except `/api/password/change`, `/api/logout`, `GET /api/session` | `errors.must_change_password` |
| `forbidden` | 403 | **Authenticated but wrong role or a failed check** (ARCH-F7, corrected in rev 2 — this row never fires for an anonymous caller, that is always `not_authenticated` above): deny-by-default with a *valid* session on a route the session can't use; `require_admin_clerk` on the three account routes for a non-admin clerk (BR-013, FR-019); CSRF `Origin`/token check failure on any route, authenticated or not (security-architecture §4) | `errors.forbidden` (generic); `accounts.forbidden` for the admin-only case ("You don't have permission…") |
| `illegal_transition` | 422 | Status update requests a transition not in the frozen map (BR-002) | `complaints.illegal_transition` |
| `edit_window_expired` | 422 | Edit-details attempted more than `EDIT_WINDOW_DAYS` (7) after `created_at` (FR-012, AC-008) | `complaints.edit_window_expired` |
| `username_taken` | 409 | Account creation with a username already in `clerk_account` (BR-016, AC-017) | `accounts.username_taken` |
| `rate_limited` | 429 (+ `Retry-After` header) | Public lookup >20/IP/min (NFR-005, AC-011); login limiter tiers (`login_ip`, `login_userip`, `login_user`); PII-bearing reads >120/user/hour (**`detail` scope, R2-7/SEC-F4, re-keyed to `user_id` rev 3 R3-2/SEC-S3, widened rev 4 to cover `GET /api/complaints/{id}/activity`, R4-2**); searches >120/user/hour (**`search` scope, rev 4, R4-2/R4-6**); authenticated writes >60/user/hour (**`write` scope, rev 3, R3-3/SEC-S4, third route `POST /api/accounts/{id}/reset-password` added rev 4 R4-5**). **`POST /api/complaints` checks both `write` and `detail` pre-handler, including on the `duplicate: true` replay (rev 4, R4-3) — either ceiling can produce this code on that one route, with a distinct `reason_code` per scope** | `errors.rate_limited.lookup`; `errors.rate_limited.login` (countdown copy); `errors.rate_limited.detail` ("Too many complaint views this hour."); `errors.rate_limited.search` ("Too many searches this hour."); `errors.rate_limited.write` ("Too many complaints/accounts created this hour.") |
| `service_unavailable` | 503 | Limiter statement fails (fail-closed, no lookup performed, backend-architecture §5); DB unreachable on any request; `/healthz`'s `SELECT 1` fails | `errors.service_unavailable` ("The service is temporarily unavailable…") |
| `internal_error` | 500 | Any unhandled exception | `errors.internal_error` — generic only, `request_id` is the only diagnostic surfaced |

## HTTP-level failures that never reach the envelope

`TrustedHostMiddleware` (unknown `Host`) returns a bare 400 with no body before the app's exception
handlers run — there is no citizen/clerk-facing route where this is reachable in production
(`ALLOWED_HOSTS` is a fixed, small list). CORS preflight denial is a browser-level failure, not a
server JSON response. Both are configuration-layer rejections, not domain errors, and are documented
here only so their absence from the table above is not mistaken for a gap.

## Rate-limit specifics (for the `Retry-After` header)

| Scope | Window | Threshold | Key | `Retry-After` |
|---|---|---|---|---|
| Public lookup (`lookup`) | 1 min fixed | 20/IP | derived client IP | Seconds remaining in the current window (≤60) |
| Login, per IP (`login_ip`) | 15 min fixed | 100/IP (short-circuits before any username-keyed row is written) | derived client IP | Seconds remaining in the window |
| Login, per user+IP (`login_userip`) | 15 min fixed | 20 | `h(username)\|ip` | Seconds remaining in the window |
| Login, per user (`login_user`) | progressive | — | `h(username)` | `1`, `3`, then `5` seconds (never a lock, never longer) |
| PII-bearing reads (`detail`) | 1 h fixed | 120/user (**rev 2, R2-7; re-keyed rev 3, R3-2/SEC-S3; widened rev 4, R4-2 to cover `/activity`**) | `user_id` | Seconds remaining in the window |
| Searches (`search`) | 1 h fixed | 120/user (**rev 4, R4-2/R4-6**) | `user_id` | Seconds remaining in the window |
| Authenticated writes (`write`) | 1 h fixed | 60/user (**rev 3, R3-3/SEC-S4; third route `POST /api/accounts/{id}/reset-password` added rev 4, R4-5**) | `user_id` | Seconds remaining in the window |

`detail` applies to `GET /api/complaints/{id}`, `GET /api/complaints/{id}/activity`,
`POST /api/complaints/{id}/status`, `POST /api/complaints/{id}/details`, and the `duplicate: true` replay
of `POST /api/complaints` (pre-handler, alongside `write` — R4-3) — the **per-route PII classification
table** in api-contract.md Conventions is the binding source for this coverage, not a schema-introspection
rule (rev 4, R4-2 — `/activity` returns `citizen_name`/`citizen_phone` as edit-history values and was
missed by rev 3's "declares `citizen_name`" test). `search` applies to `POST /api/complaints/search`
(rev 4, R4-2/R4-6) — 120/user/hour bounds a 25-row-per-call walk to 3,000 rows/hour, i.e. bounds the
*rate* of a bulk scrape, not its eventual total at pilot scale (threat #24, accepted). `write` applies to
`POST /api/complaints` (pre-handler, alongside `detail`), `POST /api/accounts` and
`POST /api/accounts/{id}/reset-password` (rev 3, R3-3/SEC-S4; third route rev 4, R4-5). All three scopes
write a `security_event` row (`throttle_detail`/`throttle_write`/`throttle_search`) **once per `(scope,
key, window_start)`**, on the request where the limiter's `RETURNING count` first equals `limit + 1` —
never once per refused request (R3-8/SEC-S2).

There is no `login_useript`-style "recent successful login" exemption scope — rev 2 (SEC-F6) removed
that carve-out; it had no backing store, so it was documentation of a control that did not exist.

## What a client is guaranteed never to see

No stack trace, no SQL fragment, no internal file path, no library exception name, no distinction
between "wrong username" and "wrong password" (both return `not_authenticated` with the identical
generic message, per AC-001/security-architecture §1 constant-time-by-construction rule).

**Lookup 400 vs 404, stated precisely (reworded, ARCH-F12):** the two cases are told apart only by
**HTTP status** (`400` for a malformed/unparseable number, `404` for a well-formed number with no
matching row) — the response **body wording is drawn from the same generic family** in both cases
(BR-015), so neither status nor body ever confirms "the number was well-formed and specifically
absent" in a way that would help a guesser distinguish a typo from a real, unused number.
