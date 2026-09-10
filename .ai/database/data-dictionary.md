# Data Dictionary — panchayat-complaint-tracker

rev 4 (2026-09-09), rework loop 3 (final) — adds `clerk_account.password_is_otp`/`password_set_at`
(R2-5, consumption corrected R4-1: an OTP is consumed by overwriting `password_hash` with a discarded
random hash, not by clearing a flag), `complaint.client_request_id` (R2-6), `security_event.target_user_id`
(ARCH-F5); removes `session.user_agent_hash` (R2-8); documents the full `rate_limit_counter.key`
form list including the `detail`/`write`/`search` `user_id` keys (SEC-S10, extended R4-2) and the
bounded `login_failure` write rule (R4-5). Per-column meaning and PII
classification. Classes used:
**PII-direct** (identifies a specific citizen), **PII-quasi** (identifying only combined with other
fields, or citizen-adjacent free text), **Internal** (operational, not personal data), **Public-safe**
(may appear in the public DTO or a public-adjacent context).

Never-log list (security-architecture.md §8) applies regardless of class: passwords, OTPs, session
tokens, CSRF tokens/seeds, complaint numbers, citizen name/phone/description/clerk notes, and full
request/response bodies are never written to stdout logs or `security_event`, no matter which table
they live in.

## clerk_account

| Column | Meaning | PII class |
|---|---|---|
| id | Internal surrogate key, used in FKs and admin-list responses (never a citizen identifier) | Internal |
| username | Clerk's login handle (a work identifier, not a citizen's) | Internal (staff-identifying, not citizen PII) |
| password_hash | Argon2id hash; never the plaintext password or OTP | Internal, secret-adjacent — never logged, never returned |
| is_admin_clerk | Role flag (BR-013) | Internal |
| must_change_password | Forces the change-password screen | Internal |
| created_at, updated_at | Audit timestamps for the account row itself | Internal |
| created_by | Which admin clerk created this account (self-FK) | Internal |
| password_is_otp | Whether the current credential is a one-time password (rev 2, R2-5); consumed at the login that uses it (rev 4, R4-1 — supersedes rev 3's flag-only clear) by **also overwriting `password_hash` with a discarded random hash in the same transaction**, so a second login with the same OTP fails Argon2 verification rather than just failing an already-cleared-flag check | Internal |
| password_set_at | When `password_hash` was last set; anchors the 72 h OTP expiry (rev 2, R2-5) | Internal |

## session

| Column | Meaning | PII class |
|---|---|---|
| id | Surrogate key | Internal |
| user_id | Which clerk this session belongs to | Internal |
| token_hash | SHA-256 of the opaque session token; the plaintext lives only in the browser cookie | Internal, secret-adjacent |
| csrf_token | Session-bound CSRF secret | Internal, secret-adjacent |
| created_at, last_seen_at, absolute_expires_at, revoked_at | Session lifecycle timestamps | Internal |

`user_agent_hash` removed rev 2 (R2-8/SEC-F14) — it was written and never checked.

## complaint

| Column | Meaning | PII class |
|---|---|---|
| id | Internal surrogate key; used in authenticated URLs (`/api/complaints/{id}`) — never shown to a citizen | Internal |
| client_request_id | Client-generated UUID that makes creation idempotent (rev 2, R2-6); never shown to a citizen | Internal |
| complaint_number | The public reference number a citizen holds and quotes back | Public-safe (by design — it is meaningless without also knowing/guessing it; BR-001/BR-004) |
| citizen_name | The complainant's full name | **PII-direct** — clerk detail view only (FR-016); never in the public DTO, list view, or logs |
| citizen_phone | The complainant's phone number | **PII-direct** — same handling as citizen_name |
| description | Free-text complaint description, may itself contain identifying detail (an address, a neighbour's name) | **PII-quasi** — clerk-only (list shows a snippet, detail shows full text); never public, never logged |
| status | Current lifecycle state | Public-safe (shown directly; also the basis for the derived `public_update`) |
| created_at | "Date logged"; also the FR-012 edit-window anchor | Public-safe (shown as "date logged" on both public and clerk views) |
| updated_at | Last time the current row changed (status or edit) | Internal (not shown to the citizen directly — the public view shows only `date_logged` per BR-005) |
| created_by | Which clerk logged the complaint | Internal (staff-identifying; visible to clerks, not citizens) |

## complaint_status_history

| Column | Meaning | PII class |
|---|---|---|
| id | Surrogate key; also used by the client to detect a concurrent update (BR-011 staleness advisory) | Internal |
| complaint_id | Parent complaint | Internal |
| previous_status, new_status | The transition recorded | Public-safe in isolation, but the *row* is clerk-only (BR-005: only the derived `public_update` for the *current* status reaches the public DTO, never history) |
| note | Clerk's free-text note on that status change | **PII-quasi** — clerk-only, never public (BR-005/ADR-013), never logged |
| actor_id | Which clerk made the change | Internal (staff-identifying) |
| created_at | Timestamp of the change | Internal/clerk-only in this context |

## complaint_edit_history

| Column | Meaning | PII class |
|---|---|---|
| id | Surrogate key | Internal |
| complaint_id | Parent complaint | Internal |
| field_name | Which of citizen_name/citizen_phone/description was edited | Internal |
| previous_value, new_value | The before/after values of that field | **PII-direct or PII-quasi**, matching the field named — a `citizen_name`/`citizen_phone` edit row carries the same sensitivity as the live column; clerk-only, never public, never logged |
| actor_id | Which clerk made the edit | Internal |
| created_at | Timestamp of the edit | Internal |

## rate_limit_counter

| Column | Meaning | PII class |
|---|---|---|
| scope | Which limiter this row belongs to: `lookup`, `login_ip`, `login_userip`, `login_user`, `detail`, `write`, `search` (`write` new rev 3, R3-3/SEC-S4, third route added rev 4 R4-5; `search` new rev 4, R4-2/R4-6; `detail` widened rev 4 to also cover `GET /api/complaints/{id}/activity`, R4-2) | Internal |
| key | **rev 3 (SEC-S10), extended rev 4 (R4-2) — full form list, by scope:** derived client IP for `lookup` and `login_ip`; `h(username)` (first 16 hex of SHA-256 over casefolded username + `USERNAME_HASH_SALT`) for `login_user`; `h(username)\|ip` for `login_userip`; `user_id` cast to text for `detail`, `write` and `search` (rev 3, R3-2/R3-3, `search` rev 4 R4-2 — re-keyed off the session hash because `POST /api/login` mints unlimited sessions) | Internal for every form. The IP forms are the requester's network address, not citizen PII, retained only as a short-lived counter key and never joined to complaint data. The `h(username)` forms are a keyed, non-reversible-without-the-salt digest of a **staff** identifier, not a citizen's. The `user_id` forms are an internal surrogate key, not citizen-identifying |
| window_start, count | Counter mechanics | Internal |

## security_event

| Column | Meaning | PII class |
|---|---|---|
| id | Surrogate key | Internal |
| event_type | Login success/failure, account created, password reset issued, throttle event (`throttle_lookup`/`throttle_login`/`throttle_detail`/`throttle_write`/`throttle_search` — `throttle_write` rev 3 R3-3/SEC-S4, `throttle_search` rev 4 R4-6), account unlocked. **`login_failure` write rule (rev 4, R4-5):** at most one row per `(actor_username_hash, derived_ip, 15-minute window)`, and none at all once the `login_ip` tier for that key is already past its limit | Internal |
| actor_user_id | The clerk who performed the action, when authenticated | Internal (staff-identifying) |
| target_user_id | The account the event is *about* when different from the actor — reset/created/unlocked account (rev 2, ARCH-F5) | Internal (staff-identifying) |
| actor_username_hash | `h(username)` for a pre-auth event (e.g., a failed login for an unknown/not-yet-loaded user) — fixed-width, not reversible without `USERNAME_HASH_SALT` (rev 2 — not `SECRET_KEY`, R2-11) | Internal, deliberately non-identifying at rest |
| derived_ip | Requester's derived IP, /64-normalised for IPv6 | Internal |
| reason_code | Short fixed code (e.g., `bad_password`), never free text | Internal |
| created_at | Event timestamp | Internal |

## What this schema deliberately never stores

- Any government-issued ID number (Aadhaar, voter ID, ration card) — no column exists anywhere
  (BR-009); an injected field on any request DTO is rejected by `extra="forbid"` before it reaches SQL.
- A plaintext password or one-time password, anywhere, ever (BR-016, security-architecture §3) — only
  the Argon2id hash is persisted.
- A complaint number in `security_event` or in any log line (security-architecture §8).
