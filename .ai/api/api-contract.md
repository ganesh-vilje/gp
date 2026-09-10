Summary: 15 endpoints (4 public, 8 clerk, 3 admin-only), one error envelope (error-catalog.md), keyset pagination on the clerk search with a two-field exact-number/free-text split (R3-1), complaint creation idempotent by `client_request_id` (no general idempotency-key framework), 20/min public rate limit + 120/user/hour `detail` ceiling (now also covers `/activity`, R4-2) + 120/user/hour `search` ceiling (R4-2) + 60/user/hour `write` ceiling (now 3 routes, R4-5), `POST /api/complaints` counted against both `write` and `detail` pre-handler including the duplicate replay (R4-3), OTP consumed at login by destroying `password_hash` (R4-1), `invalid_credentials` is not a code anywhere in this document (R4-4), `413 payload_too_large` on oversized bodies, additive-only evolution, OpenAPI docs 404 in production.

# API Contract — panchayat-complaint-tracker

rev 4 (2026-09-09), rework loop 3 (final). Binding inputs: solution-architecture.md D-A/D-C and
`## Rev 2/3/4 decisions for the API and schema` (R2-1…R2-11, R3-1…R3-10, R4-1…R4-6),
security-architecture.md, backend-architecture.md §2-6/§8-10/§12, business-rules.md,
acceptance-criteria.md, screen-inventory.md.
Closes ARCH-F1…F5, ARCH-F8, ARCH-F11, ARCH-F12, SEC-F2…F4, SEC-F6, SEC-F8…F10, SEC-F14, REL-F1
(rework loop 1), ARCH-F1/ARCH-F3/ARCH-F4/ARCH-F5, SEC-S3/SEC-S4/SEC-S5/SEC-S6/SEC-S9, R3-6, R3-8
(rework loop 2), and ARCH-F1/SEC-F2 (R4-1), SEC-F3 (R4-2), ARCH-F2 (R4-3), ARCH-F3 (R4-4),
ARCH-F4/SEC-F4 (R4-5), SEC-F3 (R4-6) (rework loop 3) on the API side.
This document is the frontend's only source of truth alongside the generated `api-types.ts`
(backend-architecture.md §1); the frontend never assumes a field this document does not declare.

## Conventions

- **Base path:** `/api` for everything except `GET /healthz` (root, platform/pinger convention).
- **No sensitive value in a path segment or a query string, ever (R2-1, binding invariant).** A
  complaint number, a citizen name, and a citizen phone number never appear in a URL — not in a path,
  not in a query string — because the gunicorn access log, browser history, and any `Referer` header
  all capture them. Every criteria-bearing read is therefore a `POST` with the criteria in the JSON
  body. Path segments carry only the opaque internal `id` (never `complaint_number`).
- **Verbs: `GET` and `POST` only, everywhere (R2-2).** There is no `PATCH`, `PUT`, or `DELETE` in this
  API. CORS `allow_methods` is exactly `GET,POST`, asserted by `selfcheck`. Field correction is
  `POST /api/complaints/{id}/details`, not `PATCH /api/complaints/{id}`.
- **Versioning:** none in the URL. API evolution is additive-only (D-C) — new optional fields and new
  endpoints only; a field is never removed, renamed, or repurposed, and an enum value is never removed.
  A breaking change would require a new base path and is a GATE-level decision, not expected in MVP.
- **Content type:** `application/json; charset=utf-8` for every request body and response body; no
  `multipart/form-data`, no file upload.
- **Body size (rev 3, R3-6/SEC-S8):** every route may return `413 payload_too_large` — a request whose
  `Content-Length` exceeds `MAX_REQUEST_BODY_BYTES` (64 KB) is rejected **before parsing**, and a
  length-less stream is capped at the same figure while reading. Not repeated per-endpoint below;
  treat it as implicit on every request body row in this document.
- **Auth:** `__Host-session` cookie (`httpOnly`, `Secure`, `SameSite=Lax`, no `Max-Age`), sent
  automatically by the browser with `credentials: "include"`. No `Authorization: Bearer` header exists
  in this API.
- **CSRF:** every unsafe method requires `X-CSRF-Token` matching either the session-bound token
  (authenticated) or `hmac_sha256(SECRET_KEY, __Host-csrfseed)` (anonymous, public routes only) —
  security-architecture.md §4. Missing/mismatched, or an unlisted/missing `Origin` ⇒ `403 forbidden`.
- **Error envelope:** see `error-catalog.md` — identical shape on every non-2xx response.
- **Authorization failure rule (ARCH-F7):** no valid session presented ⇒ `401 not_authenticated`.
  Authenticated but wrong role (`require_admin_clerk`), or a failed CSRF/`Origin` check ⇒
  `403 forbidden`. The two are never conflated in either direction.
- **Pagination (`POST /api/complaints/search` only):** keyset, in the JSON body — `cursor` (opaque
  base64 token encoding `(created_at, id)` of the last row seen; omit for the first page). `limit` is
  fixed at 25 server-side (not client-configurable, matching the UX's fixed "Load more" page size).
  Response includes `next_cursor` (`null` at the end). Example cursor payload before encoding:
  `{"created_at": "2026-08-15T09:03:41.221Z", "id": 42}` (full RFC 3339 timestamp with time and offset —
  date-only would collide within a day of inserts).
- **Filtering/search (`POST /api/complaints/search` only, rev 3 R3-1 corrects ARCH-F1 —
  two fields, not one merged `q`).** The screen inventory's Complaints list (#4) has **two separate
  controls** — an exact-number quick jump and a free-text find-by-name/phone box — and the body keeps
  them as two fields so both stay usable: `status?` (exact enum match); `complaint_number?` (the
  quick-jump field — server runs `core.complaint_number.normalise()` on it, the same trim/uppercase/
  strip-hyphen/`I`·`L`→`1`/`O`→`0` pipeline as `POST /api/lookup`, then matches by **equality** on the
  canonical 9-symbol column via `uq_complaint_number`; a malformed/bad-checksum value is `422
  invalid_input` with `fields.complaint_number`, **before** any statement touches `complaint`, BR-015
  — never a `400`, this route is authenticated); `q?` (free text, server-side `ILIKE '%…%'` over
  `citizen_name` and `citizen_phone` **only** — never `complaint_number`, which cannot ever match a
  hyphenated `XXXX-XXXXX` typed against the `CHAR(9)` canonical column via `LIKE`); `cursor?`. All
  supplied fields combine with AND. **None of these ever appear in a query string.**
- **Idempotency — one key, one endpoint (R2-6/ADR-022/REL-F1).** `POST /api/complaints` carries a
  client-generated `client_request_id` (UUID). If the client's 10 s `AbortController` fires after the
  server already committed the insert and the client resubmits with the **same** `client_request_id`,
  the unique index rejects the second insert; the service re-reads the existing row and the route
  returns it with `200` and `"duplicate": true` — never a second complaint row, never a `409`. This is
  not a general `Idempotency-Key` framework and applies to no other endpoint: status updates and edits
  are audited by design, so a genuine duplicate there is a visible extra history row, not a hidden
  double-write. A **different** `client_request_id` always creates a new complaint, by design.
- **Rate limiting:** see error-catalog.md "Rate-limit specifics". `rate_limit_counter.scope` enum:
  `lookup | login_ip | login_userip | login_user | detail | write | search`. Scopes: `lookup` (public),
  `login_ip` / `login_userip` / `login_user` (login); **`detail`** (rev 2 R2-7, re-keyed rev 3
  R3-2/SEC-S3, widened rev 4 R4-2) — key = `user_id`, 120/user/hour, `429` over it, on **every** route
  the per-route PII table below marks `detail`: `GET /api/complaints/{id}` (#9),
  `GET /api/complaints/{id}/activity` (#10, rev 4 — it returns `citizen_name`/`citizen_phone` as
  edit-history `previous_value`/`new_value`, not a live field, which is why rev 3's schema-introspection
  test missed it), `POST /api/complaints/{id}/status` (#11), `POST /api/complaints/{id}/details` (#12),
  and `POST /api/complaints` (#7, pre-handler, alongside `write` — R4-3); **`search`** (rev 4, R4-2/R4-6)
  — key = `user_id`, 120/user/hour, `429` over it, on `POST /api/complaints/search` (#8) — a clerk paging
  25 rows at a time cannot approach 120 calls/hour, so this bounds a bulk-walk *rate* (3,000 rows/hour)
  rather than an eventual total at pilot scale (threat #24, accepted); **`write`** (rev 3, R3-3/SEC-S4;
  third route rev 4 R4-5) — key = `user_id`, 60/user/hour, `429` over it, on `POST /api/complaints` (#7,
  pre-handler alongside `detail`), `POST /api/accounts` (#14) and
  `POST /api/accounts/{id}/reset-password` (#15). `detail`/`write`/`search` write a `security_event` row
  (`throttle_detail`/`throttle_write`/`throttle_search`) **once per `(scope, key, window_start)`**, on
  the request where the limiter's `RETURNING count` first equals `limit + 1` — never once per refused
  request (R3-8). No other route is rate-limited.

- **Per-route PII classification (rev 4, R4-2 — binding; copied verbatim from backend-architecture.md
  §5; a route without a row here fails SEC-T29):**

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
- **Caching:** `Cache-Control: no-store` on every response from every route (security headers
  middleware, backend-architecture.md §2). `Referrer-Policy: no-referrer` everywhere.
- **Documentation:** FastAPI's generated OpenAPI schema is the source for `openapi-typescript`'s
  committed `api-types.ts` (CI fails on staleness). `/docs`, `/redoc`, `/openapi.json` all return 404
  in production (`selfcheck` gate).
- **response_model discipline:** every route below declares an explicit response schema with
  `extra="forbid"`; there is no endpoint that "returns the object" — every field below is exhaustive.

## Endpoint inventory (15, per R2-9)

The public allow-list is **exactly** the first four rows (D-A, security-architecture.md §2); every
other row requires a valid, non-revoked session, and the three `/api/accounts*` rows additionally
require `is_admin_clerk`.

| # | Method & path | Auth | Role | Maps to | Screen |
|---|---|---|---|---|---|
| 1 | `GET /healthz` | none | anon | AD-7, D-E | (pinger only) |
| 2 | `GET /api/session` | none/session | anon or any clerk (two variants, R2-3) | FR-008, D-A step 2 | Public Status Lookup; nav (all clerk screens) |
| 3 | `POST /api/login` | none | anon | FR-001, AC-001 | Login |
| 4 | `POST /api/lookup` | none | anon | FR-008/009/010/020, BR-004/005/010/015, AC-006/007/011/018 | Public Status Lookup |
| 5 | `POST /api/logout` | session | any clerk | security-architecture §1 session lifecycle | nav (all clerk screens) |
| 6 | `POST /api/password/change` | session | any clerk | BR-016, screen-inventory #3 | Change Password |
| 7 | `POST /api/complaints` | session | any clerk | FR-002/003/004/013, BR-001/006/007/012/014, AC-002/003 | Complaints (new-complaint form) |
| 8 | `POST /api/complaints/search` | session | any clerk | FR-005/007, NFR-010, AC-005 | Complaints (list) |
| 9 | `GET /api/complaints/{id}` | session | any clerk | FR-016, AC-009 | Complaints (detail panel) |
| 10 | `GET /api/complaints/{id}/activity` | session | any clerk | FR-011/014 | Complaints (detail panel, activity tab) |
| 11 | `POST /api/complaints/{id}/status` | session | any clerk | FR-005/006, BR-002/011, AC-004/014 | Complaints (status-update form) |
| 12 | `POST /api/complaints/{id}/details` | session | any clerk | FR-012/014, BR-014, AC-008 | Complaints (edit-details form) |
| 13 | `GET /api/accounts` | session | admin clerk | FR-017/018, BR-013 | Accounts |
| 14 | `POST /api/accounts` | session | admin clerk | FR-017, BR-013/016, AC-017 | Accounts (create form) |
| 15 | `POST /api/accounts/{id}/reset-password` | session | admin clerk | FR-018, BR-013/016, AC-017 | Accounts (reset action) |

`must_change_password=true` blocks every route above except #5, #6, #2 (middleware §6) — a `403
must_change_password` on any other attempt, including a direct API call (FR-019-equivalent enforcement).

---

## Public endpoints (data-minimisation: exact response shape)

### 1. `GET /healthz`
- **Response `200`:** `{ "status": "ok" }` after a (10 s process-cached, backend §10) `SELECT 1`
  succeeds.
- **Response `503`:** `{ "status": "unavailable" }` (not the standard error envelope — polled by an
  infrastructure pinger, not a browser client).

### 2. `GET /api/session` — two documented response variants (R2-3/ARCH-F3/SEC-F9)
One path, discriminated on `authenticated`.
- **Anonymous variant** — no session cookie presented. Sets `__Host-csrfseed` if absent. **Zero SQL
  statements** (D-A step 2; this guarantee applies to this variant only — see below).
  - **Response `200`:** `{ "authenticated": false, "csrf_token": string }`
- **Authenticated variant** — a session cookie is presented and resolves to a live row (one indexed
  session read, `last_seen_at` refreshed, same cost as any authenticated request — **not** zero-SQL).
  - **Response `200`:**
    ```json
    { "authenticated": true, "csrf_token": "…",
      "user": { "id": 12, "username": "asha", "is_admin_clerk": false, "must_change_password": false } }
    ```
- **Errors:** none domain-specific; infra failures are `503 service_unavailable`.

### 3. `POST /api/login`
- **Request:** `{ "username": string, "password": string }`
  - `username`: required, 1-30 chars (an unknown username and a malformed one return the identical
    generic failure).
  - `password`: required, 1-256 chars (upper bound caps payload size only; policy enforced at
    creation/change, not at login).
- **Response `200`:**
  ```json
  { "user": { "id": 12, "username": "asha", "is_admin_clerk": false, "must_change_password": false },
    "csrf_token": "…" }
  ```
  Sets a **new** `__Host-session` cookie every time (R2-4/ADR-021). If a valid session cookie was
  presented on *this* login request, only that one row is revoked; any other session the same user
  holds elsewhere (a second device, a second tab that never presented this cookie) is **untouched** —
  this contract does not claim other devices are logged out. On success, the two bounded session-sweep
  deletes run for this user and globally (schema.md § Retention and cleanup).
  **OTP consumed at login by destroying the credential (rev 4, R4-1 — supersedes rev 3's flag-only
  clear, R3-4, which left the OTP's own hash valid and re-usable).** If the verified password is the
  account's one-time password (`password_is_otp=true`) and it is still in date, the login succeeds and,
  in the **same transaction**, the server **overwrites `password_hash` with the Argon2 hash of a
  freshly generated 256-bit random value that is generated, used, and immediately discarded inside the
  transaction** — never stored in a variable that outlives the call, never returned, never logged, known
  to nobody — and sets `password_is_otp=false` while **`must_change_password` stays `true`**. The
  session returned is a must-change-password session, confined by the middleware gate to
  `POST /api/password/change`, `POST /api/logout` and `GET /api/session`. A **second** login presenting
  the same OTP now fails Argon2 verification against the discarded hash and returns the generic
  **`401 not_authenticated`** (rev 4, R4-4 — `invalid_credentials` is not a code in this system; every
  failed login looks identical). If the clerk abandons the browser before completing the change, the
  OTP is spent and unrecoverable — the admin must issue a **new** OTP
  (`POST /api/accounts/{id}/reset-password`, or `reset-admin-password` for an admin); there is no
  reissue-the-same-OTP path. `POST /api/password/change` reached from this session takes **no
  `current_password`** — see #6.
- **Errors:** `422 invalid_input` (missing field), `401 not_authenticated` (every failed login looks
  identical: unknown username, wrong password, or an already-consumed OTP — generic, AC-001, R4-4),
  `401 otp_expired` (password verified but is an **un-consumed** one-time password past
  `OTP_EXPIRY_HOURS`, R2-5/SEC-F2 — the message directs the clerk to ask their admin for a new one, no
  session is created), `403 forbidden` (CSRF/Origin failure), `429 rate_limited` (login limiter tiers),
  `503 service_unavailable`.

### 4. `POST /api/lookup` — the AD-8/D-C route; number never in a URL
- **Request:** `{ "complaint_number": string }` — raw as typed; normalised server-side per ADR-016.
- **Validation order (BR-015):** trim/normalise → regex `^[0-9A-HJKMNP-TV-Z]{9}$` → checksum symbol →
  only then a DB lookup. Failure ⇒ `400 invalid_input` (`lookup.invalid_format`, "Enter a valid
  complaint number") with **zero** statements against `complaint` (AC-018).
- **Response `200`** — the entire public DTO, exhaustive, `extra="forbid"` (BR-005, NFR-009):
  ```json
  { "complaint_number": "4T9K-M2XQ8", "status": "in_progress",
    "public_update": "in_progress", "date_logged": "2026-08-15" }
  ```
  `public_update` is one of the fixed enum values below (ADR-013), never the clerk's free-text note:

  | `status` | `public_update` | Citizen-facing wording (owned by /ux) |
  |---|---|---|
  | `new` | `received` | "We've received your complaint." |
  | `in_progress` | `in_progress` | "Your complaint is being worked on." |
  | `resolved` | `resolved` | "Your complaint has been resolved." |
  | `rejected` | `not_accepted` | "Your complaint was not accepted." |
  | `closed` | `closed` | "Your complaint is closed." |

- **Errors:** `400 invalid_input` (malformed, above — a distinct HTTP status from the next row so the
  client can tell "fix what you typed" from "that number doesn't exist" without the response body
  wording itself distinguishing the two, per BR-015), `404 not_found` (well-formed, no row — AC-007,
  same generic wording family), `429 rate_limited` (20/IP/min, AC-011), `403 forbidden` (CSRF/Origin),
  `503 service_unavailable` (limiter write failure — fails closed, no lookup performed).
- Never returns `citizen_name`, `citizen_phone`, or the clerk's `note`/history.

---

## Clerk endpoints (any authenticated clerk — regular or admin, identical access per BR-013)

### 5. `POST /api/logout`
- **Request:** none (empty body).
- **Response `200`:** `{ "csrf_token": "…" }` — a fresh anonymous CSRF seed/token (ARCH-F11), so the
  client can immediately render the anonymous UI (e.g. redirect to Login) without a second round trip
  to `GET /api/session`. Revokes the current session row (`revoked_at = now()`); clears the cookie.
- **Errors:** `401 not_authenticated` if already unauthenticated.

### 6. `POST /api/password/change`
- **Request — two documented variants (rev 4, R4-1):**
  - **From a must-change session** (`must_change_password=true` — reached from an OTP login or a
    `bootstrap-admin --from-env` account): `{ "new_password": string, "confirm_new_password": string }`
    — **no `current_password` field at all.** The session itself is the proof of possession; after
    R4-1 the previous credential is a discarded random value nobody, including the operator, can
    supply, so requiring it would lock the clerk out of their own forced change.
  - **From a normal session** (`must_change_password=false`):
    `{ "current_password": string, "new_password": string, "confirm_new_password": string }` —
    `current_password` is required; a wrong one is `422 invalid_current_password`, never `401`.
  - `current_password` (normal-session variant only): required, max 256 chars (SEC-F14).
  - `new_password`: ≥12 chars, **max 256 chars** (SEC-F14), not username-similar, not entirely numeric,
    not in the common-password list (BR-016) — checked server-side; failures return per-rule messages
    in `fields`.
  - `confirm_new_password`: must equal `new_password`.
  - One route, one response shape; the server picks the required field set from
    `request.state.user.must_change_password`, not from which fields the client happened to send — a
    `current_password` sent on the must-change variant is rejected exactly as any other unexpected
    field would be (`extra="forbid"`).
- **Response `200`:** `{ "csrf_token": "…" }` (rotated). Sets `password_is_otp=false`,
  `password_set_at=now()` (R2-5) and `must_change_password=false`; revokes **all** sessions for this
  account (R2-4) and **sets a new `__Host-session` cookie on this same response** (rev 3, R3-5/ARCH-F4)
  — otherwise revoke-all would log the clerk out of their own password-change request.
- **Errors:** `422 invalid_input` (`fields`: `new_password`, `confirm_new_password`, or a missing
  `current_password` on the normal-session variant); **`422 invalid_current_password` with
  `fields.current_password`** (rev 3, R3-5/ARCH-F3 — a wrong *current* password on the normal-session
  path is a field error inside a valid session, **never** `401`: `401 not_authenticated` means strictly
  and only "no valid session presented," and the client maps it to a forced logout, which one typo must
  not trigger; this error cannot occur on the must-change variant, which has no `current_password`
  field to be wrong); `401 not_authenticated` only if the session itself is no longer valid.

### 7. `POST /api/complaints`
**Subject to both the `write` scope (60/user/hour) and the `detail` scope (120/user/hour), both
checked pre-handler on every call to this route, including the `duplicate: true` replay (rev 4, R4-3 —
chosen over a post-handler branch because a pre-handler pair is one dependency ordering with no branch;
the cost, a normal creation also spending one `detail` token, is irrelevant at 60 writes/hour against a
120/hour read ceiling).** `429` over either ceiling is possible on this one route, with a distinct
`reason_code` per scope (error-catalog.md).
- **Request:**
  ```json
  { "client_request_id": "b1f2...uuid", "citizen_name": "…", "citizen_phone": "…", "description": "…" }
  ```
  - `client_request_id`: required, UUID, generated client-side once per form submission and reused
    verbatim only on an automatic retry of the *same* submit (R2-6/REL-F1) — never reused across two
    different complaints.
  - `citizen_name`: required, 1-100 chars after trim (BR-007, BR-014).
  - `citizen_phone`: required, `^\+?[0-9]{7,15}$` (BR-012).
  - `description`: required, 1-2000 chars after trim (BR-006, BR-014).
  - `extra="forbid"` — an injected field (e.g., a government-ID-shaped key) is a `422` (BR-009, AC-012).
- **Response `201`** (first submission) **or `200`** (duplicate `client_request_id`, R2-6):
  ```json
  { "id": 42, "complaint_number": "4T9K-M2XQ8", "status": "new",
    "citizen_name": "…", "citizen_phone": "…", "description": "…",
    "created_at": "2026-09-09T10:03:00Z", "updated_at": "2026-09-09T10:03:00Z",
    "created_by": "asha", "legal_next_statuses": ["in_progress"],
    "edit_window_expires_at": "2026-09-16T10:03:00Z", "duplicate": false }
  ```
  On a duplicate, the **same** `id`/`complaint_number` as the original is returned with `"duplicate":
  true` and `200` — no second row is ever created, and the client shows a distinct "your complaint may
  already be saved" state rather than a bare error (ADR-022).
- **Errors:** `422 invalid_input` (per-field, `fields` keyed by name), `401 not_authenticated`,
  `429 rate_limited` (either the `write` or the `detail` scope may cross first — both are checked
  pre-handler on every call, R4-3).
- Number generation retries up to 5 times inside a savepoint on a unique-violation (ADR-016); a fifth
  consecutive collision surfaces as `503 service_unavailable` rather than a wrong/reused number.

### 8. `POST /api/complaints/search` — replaces any `GET .../complaints?…` (R2-1/ARCH-F1, two-field
split corrected rev 3 R3-1)
**Subject to the `search` limiter scope: 120/user/hour, `429` over it** (rev 4, R4-2/R4-6 — new in
this revision; the fixed 25-row page size means 120 calls bound a bulk walk to 3,000 rows/hour, the
whole table at pilot scale, so this bounds the *rate* of a scrape, not its eventual total; threat #24
records the residual as accepted).
- **Request:** `{ "status"?: string, "complaint_number"?: string, "q"?: string, "cursor"?: string }` —
  **all criteria in the body; never a query string.** Screen-inventory.md #4 (Complaints list) has
  **two** search controls, kept as two fields here (rev 3 corrects the rev-2 contract's mis-citation,
  which merged them into one field that could never satisfy the exact-number control — see Conventions
  § Filtering/search for the full validation and matching rule): `complaint_number` is the exact-match
  quick jump (normalised, equality on the canonical column, `422 invalid_input` before any DB statement
  on a bad checksum/format); `q` is free text `ILIKE`-matched against `citizen_name`/`citizen_phone`
  only. Both may be sent together; they AND with `status`.
- **Response `200`:**
  ```json
  { "items": [
      { "id": 42, "complaint_number": "4T9K-M2XQ8", "status": "in_progress",
        "description_snippet": "Streetlight near the bus stop has been out for…",
        "date_logged": "2026-08-15" } ],
    "next_cursor": "eyJjcmVhdGVkX2F0IjoiMjAyNi0wOC0xNVQwOTowMzo0MS4yMjFaIiwiaWQiOjQyfQ" }
  ```
  `description_snippet` is `description` truncated to 140 chars with an ellipsis if longer. **No
  `citizen_name`/`citizen_phone` field on this DTO** (response-minimisation, backend-architecture §10)
  — a test asserts these strings never appear in the list response even when present in the row.
  Empty result: `{ "items": [], "next_cursor": null }`.
- **Errors:** `401 not_authenticated`, `422 invalid_input` (unrecognised `status` value, or a malformed
  `complaint_number` — `fields.complaint_number`, checked before any statement touches `complaint`,
  BR-015), `429 rate_limited` (`search` scope, rev 4 R4-2).

### 9. `GET /api/complaints/{id}`
`{id}` is the internal surrogate key, never the public complaint number (D-C's ban is on the guessable
*public* number; an authenticated clerk already has full list visibility, so a sequential internal ID
here creates no new disclosure). **Subject to the `detail` limiter scope: 120/user/hour, `429` over
it** (R2-7/SEC-F4, re-keyed off `user_id` rev 3 R3-2/SEC-S3 — login mints unlimited sessions, so a
session-keyed ceiling cost an attacker nothing) — bounds, does not prevent, a hijacked-session walk of
the complaint list for name/phone; threat #24 is accepted, not mitigated, and **no `complaint_viewed`
audit event exists**.
- **Response `200`:**
  ```json
  { "id": 42, "complaint_number": "4T9K-M2XQ8", "status": "in_progress",
    "citizen_name": "…", "citizen_phone": "…", "description": "…",
    "created_at": "…", "updated_at": "…", "created_by": "asha",
    "legal_next_statuses": ["resolved", "rejected"],
    "edit_window_expires_at": "2026-09-16T10:03:00Z" }
  ```
  `citizen_name`/`citizen_phone` are present in full here (FR-016, AC-009), unlike #8's list DTO. No
  `history` field — that is #10.
- **Errors:** `404 not_found`, `401 not_authenticated`, `429 rate_limited` (`detail` scope).

### 10. `GET /api/complaints/{id}/activity`
The merged, chronologically ordered status+edit timeline (FR-011/FR-014, AC-009) as its own read, split
out from the detail DTO in rev 2 so a plain activity re-fetch (e.g. after a status update) doesn't also
re-fetch the full complaint record. **Subject to the `detail` limiter scope: 120/user/hour, `429` over
it** (rev 4, R4-2 — this route's `previous_value`/`new_value` **are** `citizen_name`/`citizen_phone`
whenever a name/phone edit is in the history, so it is a PII-bearing route despite not declaring those
fields on its own DTO; rev 3's schema-introspection coverage rule missed it for exactly that reason,
which is why coverage is now the explicit per-route table in Conventions, not a field-declaration test).
- **Response `200`:**
  ```json
  { "items": [
      { "id": 5, "type": "status", "created_at": "…", "actor_username": "asha",
        "previous_status": "new", "new_status": "in_progress", "note": "site visit scheduled" },
      { "id": 6, "type": "edit", "created_at": "…", "actor_username": "ravi",
        "field_name": "citizen_phone", "previous_value": "…", "new_value": "…" }
    ] }
  ```
  `items[].id` lets the client detect a concurrent update by comparing the highest id it last saw
  (BR-011 non-blocking staleness advisory, UX decision 4) — the API never blocks or 409s on staleness.
- **Errors:** `404 not_found`, `401 not_authenticated`, `429 rate_limited` (`detail` scope, R4-2).

### 11. `POST /api/complaints/{id}/status`
- **Request:** `{ "new_status": "in_progress" | "resolved" | "rejected" | "closed", "note": string | null }`
  - `new_status`: required, must be a legal transition from the row's *current* status at commit time
    (BR-002) — checked inside the row-locked transaction.
  - `note`: optional, ≤2000 chars.
- **Response `200`:** the updated detail DTO (#9 shape) — carries `citizen_name`/`citizen_phone`, so
  **subject to the `detail` limiter scope** (rev 3, R3-2/SEC-S3). The client re-fetches #10 to see the
  new history row (additive-only DTOs, no embedded history here).
- **Errors:** `422 illegal_transition`, `422 invalid_input` (note too long), `404 not_found`, `401
  not_authenticated`, `429 rate_limited` (`detail` scope).

### 12. `POST /api/complaints/{id}/details` — replaces `PATCH /api/complaints/{id}` (R2-2/ARCH-F2/SEC-F8)
- **Request:** `{ "citizen_name"?: string, "citizen_phone"?: string, "description"?: string }` — at
  least one field required; same per-field rules as #7 (BR-007/012/014).
- **Precondition:** `now() < created_at + 7 days` (FR-012, `EDIT_WINDOW_DAYS`), checked server-side
  regardless of what the UI shows (AC-008 — no override path exists).
- **Response `200`:** updated detail DTO (#9 shape) — **subject to the `detail` limiter scope** (rev 3,
  R3-2/SEC-S3). One `complaint_edit_history` row per **changed** field only — a field resubmitted with
  its current value is silently skipped by the service (and would fail the DB `CHECK (new_value IS
  DISTINCT FROM previous_value)` if it weren't, REL-F5).
- **Errors:** `422 edit_window_expired`, `422 invalid_input`, `404 not_found`, `401 not_authenticated`,
  `429 rate_limited` (`detail` scope).

---

## Admin-only endpoints (`require_admin_clerk` — BR-013, FR-017/018/019)

A non-admin clerk calling any of these three, including directly (bypassing the UI), gets `403
forbidden` — same check for the hidden nav link and a raw API call (AC-017).

### 13. `GET /api/accounts`
- **Response `200`:** `{ "items": [ { "id": 3, "username": "ravi", "is_admin_clerk": false,
  "created_at": "…" } ] }` — no password hash, no OTP, ever.
- **Errors:** `401 not_authenticated`, `403 forbidden` (non-admin).

### 14. `POST /api/accounts`
**Subject to the `write` limiter scope: 60/user/hour, `429` over it** (rev 3, R3-3/SEC-S4).
- **Request:** `{ "username": string, "is_admin_clerk": boolean }` — **no `initial_password` field**
  (ARCH-F8/SEC-F10, rev 2 removes it): the server **always** generates the one-time password itself;
  there is no path, in-app or API, for a client to set an account's initial credential.
  - `username`: required, `^[A-Za-z0-9_]{3,30}$`, must not already exist (BR-016, AC-017).
  - `is_admin_clerk`: required boolean; no cap on the number of admin accounts (A12).
- **Response `201`:**
  ```json
  { "id": 8, "username": "priya", "is_admin_clerk": false,
    "one_time_password": "7fH4-mQ9x-Rk2Z", "created_at": "…" }
  ```
  `Cache-Control: no-store, no-cache, must-revalidate`. `one_time_password` is returned **exactly
  once**; `GET /api/accounts` never includes it. Sets `password_is_otp=true`, `password_set_at=now()`.
- **Errors:** `422 invalid_input`, `409 username_taken`, `401 not_authenticated`, `403 forbidden`,
  `429 rate_limited` (`write` scope).
- Writes a `security_event` row (`account_created`, `target_user_id` = the new account) — never the
  password (ADR-011, ARCH-F5, column names per R3-7 below).

### 15. `POST /api/accounts/{id}/reset-password`
**Subject to the `write` limiter scope: 60/user/hour, `429` over it** (rev 4, R4-5 — this was the one
write route with no ceiling; it is an admin-triggered permanent state change: revoke-all plus a new
credential).
- **Request:** none (empty body) — a single confirmed action (screen-inventory #5).
- **Response `200`:** `{ "one_time_password": "9kR2-tN6w-Xz4V" }`, same `no-store` headers, same
  once-only guarantee. Sets `password_is_otp=true`, `password_set_at=now()`; revokes every existing
  session for the target account and sets `must_change_password=true`.
- **Errors:** `404 not_found` (no such account id), `401 not_authenticated`, `403 forbidden`,
  `429 rate_limited` (`write` scope, R4-5).
- Writes a `security_event` row (`password_reset_issued`, `actor_user_id` = the admin, `target_user_id`
  = the reset account — a real FK, not an "equivalent linkage" — ARCH-F5). The operator CLI
  `reset-admin-password` (backend-architecture §12) writes the identical event shape with
  `reason_code=operator_cli` and the same `target_user_id` population.

## Self-audit

- Every endpoint above has an explicit, exhaustive response schema — no "returns the object" phrasing.
- Every FR/AC/BR cited in the inventory table is addressed by at least one endpoint; every screen in
  screen-inventory.md maps to at least one row (# column cross-referenced).
- The public allow-list in the inventory table is exactly 4 rows, matching D-A/security-architecture §2
  byte-for-byte: `GET /healthz`, `GET /api/session`, `POST /api/login`, `POST /api/lookup`.
- The public lookup response (#4) is checked against NFR-008/NFR-009/BR-005/BR-009: no field beyond
  `complaint_number`, `status`, `public_update`, `date_logged` exists on that model.
- No response model contains `password_hash`, a raw password, or an OTP outside its single once-only
  response (#14, #15). No request field named `initial_password` exists anywhere (ARCH-F8/SEC-F10).
- No sensitive value (complaint number, citizen name, citizen phone) appears in a path segment or a
  query string on any route above (R2-1) — every criteria-bearing read is a `POST` body.
- No verb outside `{GET, POST}` appears anywhere (R2-2).
- `POST /api/complaints/search` (#8) keeps the screen inventory's two controls as two body fields
  (`complaint_number` exact-match, `q` name/phone free text) — rev 3, R3-1 fixes the rev-2 mis-citation
  that merged them into one field and made the exact-number jump unsatisfiable.
- Every `security_event`-writing endpoint (#3 login failure, #14, #15, and both `throttle_*` writers)
  uses exactly `event_type`/`actor_user_id`/`actor_username_hash`/`target_user_id`/`derived_ip`/
  `reason_code`/`created_at` — rev 3, R3-7/ARCH-F5, matching schema.md byte-for-byte.
- The `detail` scope (120/user/hour) covers #7 (pre-handler, alongside `write`), #9, #10, #11, #12 —
  the coverage source is the explicit per-route PII table in Conventions (rev 4, R4-2), not a
  schema-introspection rule; the `search` scope (120/user/hour) covers #8 (rev 4, R4-2/R4-6); the
  `write` scope (60/user/hour) covers #7 (pre-handler, alongside `detail` — R4-3), #14 and #15 (rev 4,
  R4-5) — rev 3, R3-2/R3-3/SEC-S3/SEC-S4, rev 4, R4-2/R4-3/R4-5.
- **`invalid_credentials` does not appear anywhere in this document** (rev 4, R4-4) — every failed
  login is `401 not_authenticated`; the only login-specific code is `otp_expired`.
- `413 payload_too_large` is a documented possible response on every request-body route (rev 3, R3-6).
- Endpoint count is still **15**; the public allow-list is still exactly the 4 rows above; no `PATCH`
  exists; no complaint number, citizen name or phone appears in any path segment or query string
  anywhere in this document (verified against every endpoint above, rev 3 included).
- Rev 2 findings closed here: ARCH-F1…F5, ARCH-F8, ARCH-F11, ARCH-F12, SEC-F2, SEC-F3, SEC-F4, SEC-F6,
  SEC-F8, SEC-F9, SEC-F10, SEC-F14, REL-F1.
- Rev 3 findings closed here: ARCH-F1/R3-1 (search two-field split), ARCH-F3/R3-5 (`invalid_current_password`
  never `401`), ARCH-F4/R3-5/R3-6 (password-change sets a new cookie; logout's token stays anonymous),
  ARCH-F5/R3-7 (security_event column names), SEC-S3/R3-2 (`detail` re-keyed to `user_id`, all four
  routes covered), SEC-S4/R3-3 (`write` scope), SEC-S5/R3-4 (OTP consumed at login), SEC-S9 (`"duplicate":
  true` retained as the contract form), R3-6/SEC-S8 (`413 payload_too_large`), R3-8 (one throttle event
  per window, not per request).
- Rev 4 findings closed here: ARCH-F1/SEC-F2/R4-1 (OTP consumed by destroying `password_hash` in the
  login transaction; `POST /api/password/change`'s two request variants documented explicitly),
  SEC-F3/R4-2 (`/activity` moved under `detail`; new `search` scope on #8; per-route PII table added to
  Conventions), ARCH-F2/R4-3 (`POST /api/complaints` counts against both `write` and `detail`
  pre-handler, including the duplicate replay), ARCH-F3/R4-4 (`invalid_credentials` removed; every
  failed login is `401 not_authenticated`), ARCH-F4/SEC-F4/R4-5 (`reset-password` joins `write`),
  SEC-F3/R4-6 (`throttle_search` referenced in the rate-limit convention).
