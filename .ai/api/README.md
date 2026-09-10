Summary: 15 endpoints (4 public, 8 clerk, 3 admin-only), one error envelope (error-catalog.md), keyset pagination on the clerk search with a two-field exact-number/free-text split (R3-1), complaint creation idempotent by `client_request_id` (no general idempotency-key framework), 20/min public rate limit + 120/user/hour `detail` ceiling (now also covers `/activity`, R4-2) + 120/user/hour `search` ceiling (R4-2) + 60/user/hour `write` ceiling (now 3 routes, R4-5), `POST /api/complaints` counted against both `write` and `detail` pre-handler including the duplicate replay (R4-3), OTP consumed at login by destroying `password_hash` (R4-1), `invalid_credentials` is not a code anywhere in this document (R4-4), `413 payload_too_large` on oversized bodies, additive-only evolution, OpenAPI docs 404 in production.

# API — panchayat-complaint-tracker

rev 4 (2026-09-09), rework loop 3 (final). Owned by the data-api-architect. FastAPI JSON API, `/api`
base path (plus root `/healthz`), per solution-architecture.md D-C and `## Rev 2/3/4 decisions for the
API and schema`, and backend-architecture.md §1-6/§12. Closes ARCH-F1…F5, ARCH-F8, ARCH-F11, ARCH-F12,
SEC-F2…F4, SEC-F6, SEC-F8…F10, SEC-F14, REL-F1 (rework loop 1), ARCH-F1/F3/F4/F5, SEC-S3/S4/S5/S6/S9,
R3-6, R3-8 (rework loop 2), and ARCH-F1/SEC-F2 (R4-1), SEC-F3 (R4-2), ARCH-F2 (R4-3), ARCH-F3 (R4-4),
ARCH-F4/SEC-F4 (R4-5), SEC-F3 (R4-6) (rework loop 3).

## Contents

- **[api-contract.md](./api-contract.md)** — conventions (auth, CSRF, pagination, filtering,
  idempotency, rate limiting, caching, docs), the full endpoint inventory, and per-endpoint
  request/response schemas with validation rules, mapped to FR/AC/BR IDs and screens. Start here.
- **[error-catalog.md](./error-catalog.md)** — every error code, HTTP status, when it's raised, and the
  public-safe message key. The single envelope shape used by every endpoint.

## How this maps to the rest of the project

- Auth model, CSRF, rate limiting and the error-envelope shape are taken as binding from
  `security-architecture.md` and `backend-architecture.md` §2/§4-6 — this contract applies them to
  every route, it does not redesign them.
- `app/api/routers/` and `app/api/schemas/` (backend-architecture.md §1) implement exactly this
  contract; `openapi-typescript` generates the frontend's `api-types.ts` from the running app's
  OpenAPI schema, with a CI staleness check keeping the two in sync.
- Every endpoint cites the FR/AC/BR it satisfies so a reviewer can trace UI → API → business rule → DB
  constraint in one pass (see also `../database/schema.md`'s constraints table for the DB side of the
  same rules).

## Non-negotiables carried from /architecture

- The public allow-list is exactly 4 endpoints: `GET /healthz`, `GET /api/session`, `POST /api/login`,
  `POST /api/lookup`. Everything else denies by default.
- **No sensitive value (complaint number, citizen name, citizen phone) in a URL path segment or a query
  string, ever (R2-1)** — `/api/complaints/{id}` uses the internal surrogate key, never
  `complaint_number`; clerk list/search is `POST /api/complaints/search` with criteria in the body.
- **Only `GET` and `POST` exist in this API (R2-2)** — no `PATCH`/`PUT`/`DELETE` anywhere; field
  correction is `POST /api/complaints/{id}/details`.
- The public lookup response is exactly four fields — `complaint_number`, `status`, `public_update`,
  `date_logged` — never citizen name, phone, or the clerk's free-text note.
- Complaint creation is idempotent by client-supplied `client_request_id`; no other endpoint carries an
  idempotency key (R2-6).
- Clerk search (`POST /api/complaints/search`) keeps two body fields — `complaint_number` (exact-match
  quick jump) and `q` (name/phone free text) — never merged into one (rev 3, R3-1/ARCH-F1).
- Limiter scope `detail` (120/user/hour) covers every route in the per-route PII table (api-contract.md
  Conventions) marked `detail`, including `GET /api/complaints/{id}/activity` (rev 4, R4-2 — it returns
  name/phone as edit-history values); `search` (120/user/hour, rev 4 R4-2) covers
  `POST /api/complaints/search`; `write` (60/user/hour) covers `POST /api/complaints`,
  `POST /api/accounts` and `POST /api/accounts/{id}/reset-password` (rev 4, R4-5) — all keyed on
  `user_id`. `POST /api/complaints` counts against both `write` and `detail`, pre-handler, including the
  `duplicate: true` replay (rev 4, R4-3).
- OTP login is consumed by **destroying** the credential — the login transaction overwrites
  `password_hash` with a discarded random hash, not by clearing a flag (rev 4, R4-1). There is no
  `invalid_credentials` code anywhere in this contract; every failed login is `401 not_authenticated`
  (rev 4, R4-4).
- `Cache-Control: no-store` on every response, `Referrer-Policy: no-referrer` everywhere; every route
  may return `413 payload_too_large` on a body over 64 KB (rev 3, R3-6).
- OpenAPI docs (`/docs`, `/redoc`, `/openapi.json`) return 404 in production.
