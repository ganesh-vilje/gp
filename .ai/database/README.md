Summary: 7 tables (clerk_account, session, complaint, complaint_status_history, complaint_edit_history, rate_limit_counter, security_event), 2 enums, 12 indexes, additive-only Alembic migrations, app-level append-only guard on 3 history/event tables, no hard delete anywhere except bounded session/rate-limit sweeps (`ctid`-bounded, on login, on limiter rollover); complaint creation idempotent via `client_request_id`; rate limiter carries `lookup`/`login_ip`/`login_userip`/`login_user`/`detail`/`write`/`search` scopes, `detail`/`write`/`search` keyed on `user_id`; OTP consumed at login by overwriting `password_hash` with a discarded random hash, not by clearing a flag (R4-1); `login_failure` events bounded to one row per `(actor_username_hash, derived_ip, 15-min window)` and none while the `login_ip` tier is already tripped (R4-5).

# Database — panchayat-complaint-tracker

rev 4 (2026-09-09), rework loop 3 (final). Owned by the data-api-architect. PostgreSQL 17, SQLAlchemy 2.x
(sync) + Alembic, additive-only migrations, per solution-architecture.md D-B and
`## Rev 2/3/4 decisions for the API and schema`, and backend-architecture.md §3/§5/§6/§7-10. Closes
SEC-F2, SEC-F4, SEC-F14, ARCH-F5, REL-F1, REL-F5, PERF-F4 (rework loop 1), SEC-S3, SEC-S4, SEC-S5,
SEC-S6, SEC-S10, ARCH-F2/R3-9, PERF-F5 (rework loop 2), and ARCH-F1/SEC-F2 (R4-1), SEC-F3 (R4-2),
ARCH-F2 (R4-3), ARCH-F3 (R4-4), ARCH-F4/SEC-F4 (R4-5), SEC-F3 (R4-6) (rework loop 3).

## Contents

- **[schema.md](./schema.md)** — entities, columns, types, constraints, indexes, ERD, enums,
  append-only enforcement, soft-delete policy, retention, migration strategy, compact DDL, transaction
  boundaries. Start here.
- **[data-dictionary.md](./data-dictionary.md)** — per-column meaning and PII classification, for
  anyone deciding what a new column, log line, or export may contain.

## How this maps to the rest of the project

- Every table cross-references the business rule(s) it enforces (`business-rules.md` BR-001..BR-016)
  and, where relevant, the acceptance criterion that verifies it.
- Schema follows `solution-architecture.md` D-B (mutable current-state row + append-only history) and
  `backend-architecture.md` §9 (audit history writes) exactly; it does not redesign either.
- The SQLAlchemy models themselves live in `app/db/models/` (backend-architecture.md §1) — this folder
  is the contract those models must satisfy, not the code itself.

## Non-negotiables carried from /architecture

- No hard delete of a complaint, ever (BR-008). No purge job, no auto-deletion before 12 months
  (NFR-010).
- `complaint_status_history`, `complaint_edit_history`, `security_event` are append-only — insert
  only, enforced by an app-level guard hook (and a best-effort DB-level `REVOKE` where the platform
  allows a second role).
- `complaint_number` is never sequential, never reused, and never a DB column exposed through a URL
  path segment on the public surface (D-C).
- `rate_limit_counter` lives outside the request transaction, on its own AUTOCOMMIT engine — do not
  add a foreign key to it or query it from the request `Session`.
- Rev 2: `clerk_account.password_is_otp`/`password_set_at` (OTP state), `complaint.client_request_id`
  (idempotent create), `security_event.target_user_id` (who an event is about) are additive;
  `session.user_agent_hash` is removed (written, never checked).
- Rev 3: `password_is_otp` is now also cleared **at the login that consumes it**, not only at password
  change (R3-4); `rate_limit_counter` gains a `write` scope and a `window_start` index shipped in
  migration 0001, not later (R3-3, R3-10); session/rate-limit sweep SQL is restated as the only form
  PostgreSQL accepts — `ctid` sub-selects, never `DELETE … LIMIT` (R3-9). No column removed or renamed.
- Rev 4 (final): OTP consumption is corrected again — clearing the flag alone left the OTP's Argon2
  hash valid, so the login transaction now **overwrites `password_hash`** with a discarded random hash
  instead (R4-1, supersedes R3-4). `rate_limit_counter` gains a `search` scope and `detail` is widened
  to cover `GET /api/complaints/{id}/activity` (R4-2); `POST /api/complaints` counts against both
  `write` and `detail` pre-handler (R4-3); `security_event.event_type` gains `throttle_search` (R4-6);
  `login_failure` writes are bounded to one row per `(actor_username_hash, derived_ip, 15-min window)`
  and suppressed entirely while the `login_ip` tier is tripped (R4-5). `invalid_credentials` is
  confirmed to not exist as a code anywhere in these documents (R4-4). No column removed or renamed.
