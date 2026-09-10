# Test Cases — panchayat-complaint-tracker

rev 3 (2026-09-10) — rework after rev 2 GATE_6 reviewer findings (arch F16/F17/F18, test-review
F1/F2): added **TC-SEC-039** (backend-architecture.md §2's middleware-registration-order assertion,
tech-stack.md assertion 16, previously unmapped — arch F16) and its row in the "Architecture
assertion → TC id(s)" table; recounted every total to **142** now that TC-SEC-039 exists (arch F17;
see Coverage summary for the exact per-level always-run/nightly/release-gate breakdown); replaced
every wrong-meaning "OQ-9"/"OQ-10" reference with **ADR-014 Q4** (voluntary password change) and
**ADR-014 Q3** (name/phone search) — those OQ numbers belong to different, unrelated open questions
in architecture/open-questions.md (arch F18). rev 2's changes (fixed two fabricated traceability IDs,
added TC-COMP-011..014/TC-SEC-025..038, the architecture-assertion mapping table, and the
clock-injection reclassifications) stand unchanged. IDs are stable; do not renumber, append instead.
"Reg" column: Y = in the always-run regression set (test-strategy.md §6), N = nightly, R =
release-gate only. Every row traces to a real ID from acceptance-criteria.md / business-rules.md /
api-contract.md / error-catalog.md / threat-model.md / backend-architecture.md — none invented.

## Unit (pytest, no marker — real DB not needed)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-UNIT-001 | AC-002, BR-012 | none | Validate phone `"abc1234"` (letters) | Rejected, `fields.citizen_phone` reason code | Y |
| TC-UNIT-002 | AC-002, BR-012 | none | Validate phone `"123"` (3 digits) | Rejected — below 7-char floor | Y |
| TC-UNIT-003 | AC-002, BR-014 | none | Validate `citizen_name` of 101 chars | Rejected — over 100-char cap | Y |
| TC-UNIT-004 | AC-002, BR-014 | none | Validate `description` of 2001 chars | Rejected — over 2000-char cap | Y |
| TC-UNIT-005 | AC-004, BR-002 | none | Evaluate transition map for `new`→`closed` | Not in the frozen legal-transition set | Y |
| TC-UNIT-006 | BR-002 | none | Evaluate every (from,to) pair in the frozen map | Exactly {new→in_progress, in_progress→{resolved,rejected}, resolved/rejected→closed} legal; all others illegal | Y |
| TC-UNIT-007 | BR-016 | none | Validate username `"ab"` (2 chars), `"a"*31` (31 chars), `"a b"` (space) | All three rejected per `^[A-Za-z0-9_]{3,30}$` | Y |
| TC-UNIT-008 | AC-017, BR-016 | none | Validate password of 11 chars vs exactly 12 chars | 11 rejected, 12 accepted | Y |
| TC-UNIT-009 | api-contract §4 | none | Run `core.complaint_number.normalise()` on `" 4t9k-m2xq8 "` (whitespace, lowercase, hyphen) | Canonical 9-symbol uppercase value, matching the stored form | Y |
| TC-UNIT-010 | error-catalog.md | none | Serialize an `invalid_input` error with `fields={"citizen_phone": "..."}` | Envelope matches the documented shape exactly (`code`,`message`,`fields`,`request_id`) | Y |

## Integration/API (pytest -m integration, real Postgres, httpx/TestClient)

### Auth (AC-001)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-API-001 | AC-001 | Seeded clerk `clerk_test` | POST /api/login with correct credentials | 200, session cookie set, `csrf_token` returned | Y |
| TC-API-002 | AC-001 | Seeded clerk | POST /api/login with wrong password | 401 `not_authenticated`, generic message, no field says which was wrong | Y |
| TC-API-003 | AC-001 | Seeded clerk | POST /api/login with unknown username | 401 `not_authenticated`, byte-identical body/status to TC-API-002 | Y |
| TC-API-004 | AC-001, BR-003 | No session cookie | GET a clerk-only route directly (e.g. `POST /api/complaints`) | 401 `not_authenticated`, no record created | Y |

### Log a complaint (AC-002, AC-003)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-API-010 | AC-002 | Logged-in clerk | POST /api/complaints, all fields valid | 201, `status:"new"`, `created_at` set, `complaint_number` returned | Y |
| TC-API-011 | AC-002, BR-006 | Logged-in clerk | POST with `description` blank | 422 `invalid_input`, `fields.description`, no row inserted | Y |
| TC-API-012 | AC-002, BR-007 | Logged-in clerk | POST with `citizen_name` blank | 422 `invalid_input`, `fields.citizen_name`, no row inserted | Y |
| TC-API-013 | AC-002, BR-007 | Logged-in clerk | POST with `citizen_phone` blank | 422 `invalid_input`, `fields.citizen_phone`, no row inserted | Y |
| TC-API-014 | AC-002, BR-012 | Logged-in clerk | POST with malformed phone | 422 `invalid_input`, no row inserted | Y |
| TC-API-015 | AC-002, BR-014 | Logged-in clerk | POST with name/description over the length caps | 422 `invalid_input`, no row inserted | Y |
| TC-API-016 | AC-002, NFR-011 | Logged-in clerk | Simulate a stalled backend response past the client's 10s AbortController | Client-observable timeout path exercised (see TC-E2E-002 for the UI assertion); server side: request still completes or is safely retryable | Y |
| TC-API-017 | api-contract §7, ADR-022 | Logged-in clerk | POST twice with the same `client_request_id` | Second call returns 200 `duplicate:true`, same `id`/`complaint_number`, no second row | Y |
| TC-API-018 | AC-012, BR-009 | Logged-in clerk | POST with an extra field shaped like a government ID (e.g. `aadhaar`) | 422 `invalid_input` (`extra="forbid"`) — value never persisted | Y |
| TC-API-019 | api-contract §7 | Logged-in clerk | Force 5 consecutive complaint-number collisions (monkeypatched generator) | 503 `service_unavailable`, no wrong/reused number assigned | Y |
| TC-API-020 | AC-003, BR-001, FR-013 | Logged-in clerk(s) | Create 100 complaints in sequence | All 100 `complaint_number` values distinct | Y |
| TC-API-021 | AC-003, FR-013 | 20 logged-in clerk sessions | Fire 20 concurrent `POST /api/complaints` via `concurrent.futures` against `live_server` | All 20 succeed with 20 distinct complaint numbers, zero collisions | Y |

### Update status (AC-004, AC-014)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-API-030 | AC-004, BR-002 | Complaint in `new` | POST status → `in_progress`, note "site visit scheduled" | 200, status updated, note stored, history row timestamped | Y |
| TC-API-031 | AC-004, BR-002 | Complaint in `new` | POST status → `closed` directly | 422 `illegal_transition`, status unchanged | Y |
| TC-API-032 | AC-004 | Status just changed | GET complaint detail | New status + note visible immediately | Y |
| TC-API-033 | AC-004, NFR-011 | Logged-in clerk | Status-change POST with note > 2000 chars | 422 `invalid_input` | Y |
| TC-API-034 | AC-004, BR-003 | No session | POST status change directly | 401 `not_authenticated`, complaint unchanged | Y |
| TC-API-100 | AC-014, BR-011 | Complaint in `in_progress` loaded by two sessions | Clerk A saves →`resolved`/"fixed same day"; Clerk B (stale load) saves →`rejected`/"duplicate" without reloading | Final current status = last write to commit; **both** history rows present with correct actor/note/timestamp, neither silently dropped | Y |

### List/filter/search (AC-005)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-API-040 | AC-005 | Complaints in multiple statuses, multiple clerks | POST /api/complaints/search `{status:"in_progress"}` | Only `in_progress` rows returned, regardless of creator | Y |
| TC-API-041 | AC-005 | No filter | POST search with no body fields | All complaints, most-recently-created first (single deterministic order) | Y |
| TC-API-042 | AC-005 | Search for a non-existent complaint number | POST search `{complaint_number:"<valid-format, no match>"}` | 200, `items: []` — not an error, not a blank body | Y |
| TC-API-043 | AC-005 | Zero complaints exist | POST search, no filters | 200, `items: []`, `next_cursor: null` (empty-state is a UI concern; API contract: empty list) | Y |
| TC-API-044 | AC-005, api-contract §Pagination | > 25 complaints exist | POST search first page, then again with returned `next_cursor` | Second page contains the next 25 by `(created_at,id)`, no overlap/gap | Y |
| TC-API-045 | AC-005, BR-015 | Logged-in clerk | POST search with malformed `complaint_number` | 422 `invalid_input`, `fields.complaint_number`, before any `complaint`-table statement (query-counter fixture) | Y |
| TC-API-046 | api-contract §8, SEC-F6 | Complaint has both name+phone set | POST search matching by name | Response `items[]` contains no `citizen_name`/`citizen_phone` field at all | Y |

### Detail / edit / history (AC-008, AC-009)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-API-060 | AC-008, FR-012 | Complaint created < 7 days ago | POST /api/complaints/{id}/details with corrected name | 200, updated value stored, `created_at` unchanged | Y |
| TC-API-061 | AC-008, FR-012 | Complaint created > 7 days ago (fixture backdates `created_at`) | POST edit-details | 422 `edit_window_expired`, no change applied, no override path exists | Y |
| TC-API-062 | AC-008 | Complaint > 7 days old, UI-independent | POST edit-details directly via API bypassing any client check | Same 422 as TC-API-061 — server is the authority regardless of what UI shows | Y |
| TC-API-063 | AC-002/AC-008, BR-014 | Within edit window | POST edit-details with description over 2000 chars | 422 `invalid_input`, no change applied | Y |
| TC-API-070 | AC-009, FR-011 | Complaint with 2 status changes | GET /api/complaints/{id}/activity | Both entries listed, chronological, each with timestamp/status/note | Y |
| TC-API-071 | AC-009, FR-014 | Complaint with one field edit | GET activity | Edit entry shows previous value, new value, editing clerk, timestamp; distinguishable `type:"edit"` from `type:"status"` | Y |
| TC-API-072 | AC-009, FR-016 | Any complaint | GET /api/complaints/{id} as clerk (regular or admin) | Full `citizen_name`/`citizen_phone` present, unlike the public DTO | Y |

### Public lookup (AC-006, AC-007, AC-018)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-API-050 | AC-006 | Complaint exists, known number | POST /api/lookup with exact number | 200, DTO = exactly `{complaint_number,status,public_update,date_logged}` | Y |
| TC-API-051 | AC-006, BR-005, NFR-009 | Complaint has name+phone+note set | POST /api/lookup | Response body contains no `citizen_name`, `citizen_phone`, or clerk note value anywhere (asserted by full-body string search, not just field absence) | Y |
| TC-API-052 | AC-006, BR-005/GATE_2 Q7 | Complaint in each of the 5 statuses | POST /api/lookup once per status | `public_update` is always one of the 5 enumerated values, never free text | Y |
| TC-API-053 | AC-006 | Complaint number has mixed case/extra spaces | POST /api/lookup with `" 4t9k-m2xq8 "` | Normalises and succeeds (same result as canonical form) | Y |
| TC-API-054 | AC-006, NFR-011 | — | Simulate slow backend past 10s | Same reasoning as TC-API-016; UI assertion is TC-E2E-004 | Y |
| TC-API-055 | AC-018, BR-015 | — | POST /api/lookup with a well-formed-but-unassigned number | 404 `not_found`, generic "not found" family message | Y |
| TC-API-056 | AC-007 | — | POST /api/lookup, no match | 404 `not_found`; response reveals nothing about any other complaint | Y |

### No-gov-ID / retention (AC-012, AC-013)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-API-090 | AC-012, BR-009 | New-complaint and edit-details schemas | Inspect Pydantic model fields for both requests | No field named/labelled for any government ID | Y |
| TC-API-091 | AC-012, BR-009 | — | POST /api/complaints with an extra `voter_id` field | 422 `invalid_input` (`extra="forbid"`), never persisted | Y |
| TC-API-092 | AC-013, NFR-010 | Complaint created "today" with a simulated reduced retention window | Assert record still retrievable by number before the simulated window elapses | Complaint retrievable, unaffected by a shortened window used only for the test | Y |

### Admin accounts (AC-017, AC-019)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-API-110 | AC-017, FR-017 | Admin session | POST /api/accounts `{username:"priya", is_admin_clerk:false}` | 201, `one_time_password` returned once; account can subsequently log in | Y |
| TC-API-111 | AC-017, FR-018 | Admin session, target account exists | POST /api/accounts/{id}/reset-password | 200, new OTP returned; old password no longer authenticates | Y |
| TC-API-112 | AC-017, BR-016 | Admin session | POST /api/accounts with a username already taken | 409 `username_taken`, no account created | Y |
| TC-API-113 | AC-017, BR-016 | Admin session | POST /api/accounts with username 2 chars / 31 chars / with a hyphen | 422 `invalid_input` in all three cases, no account created | Y |
| TC-API-114 | AC-017, BR-016 | Admin session | Attempt account create/reset resulting in an 11-char password (server-generated path is fixed-length; this targets the shared validator used by password/change) | Rejected below 12 chars; exactly 12 accepted (see TC-UNIT-008) | Y |
| TC-API-115 | AC-017, BR-016 | Admin completes create/reset | Inspect response | New/reset password shown exactly once on-screen equivalent (response body), never in `GET /api/accounts` afterward | Y |
| TC-API-116 | AC-017, BR-016 | New/reset account | Log in with the new OTP | `must_change_password:true`, session confined to `/api/password/change`, `/api/logout`, `GET /api/session` | Y |
| TC-API-117 | AC-017, BR-013 | — | No session | POST /api/accounts directly | 401 `not_authenticated`, no account created | Y |
| TC-API-118 | AC-017, BR-013, FR-019 | Regular (non-admin) clerk session | POST /api/accounts and POST /api/accounts/{id}/reset-password | Both return 403 `forbidden`, nothing created/changed — same check as the hidden nav link (both directions with TC-API-110/111 which prove the admin path works) | Y |
| TC-API-119 | AC-017, BR-013 | Regular clerk session | GET /api/accounts | 403 `forbidden` | Y |
| TC-API-130 | AC-019, FR-015 | Fresh deployment, no admin account | Run bootstrap mechanism | Exactly one admin clerk account exists afterward | Y |
| TC-API-131 | AC-019, FR-001/017/018 | Bootstrapped admin account | Log in, then create a clerk account and reset a password | Login succeeds; both admin actions succeed | Y |
| TC-API-132 | AC-019 | Admin account already exists | Run bootstrap mechanism a second time | No duplicate/conflicting admin account created; data integrity preserved (no-op or explicit error, per architect's choice) | Y |

## DB / query-counter (pytest -m integration, query-counter fixture)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-DB-001 | AC-018, BR-015, FR-020 | — | POST /api/lookup with blank / whitespace-only / malformed-format complaint number (3 sub-cases) | For all three: 400 `invalid_input`, message "Enter a valid complaint number", **zero statements touch the `complaint` table** (asserted by table name) | Y |
| TC-DB-002 | AC-018, BR-015 | Direct HTTP client bypassing any frontend | Same 3 sub-cases via a raw `httpx` call, no browser involved | Identical result to TC-DB-001 — the guarantee holds independent of caller | Y |
| TC-DB-003 | api-contract §2, threat #34(a) | No session cookie presented | GET /api/session | 200 `authenticated:false`; **zero SQL statements of any kind** (stronger than DB-001/002 — not just "no complaint table", literally none) | Y |
| TC-DB-004 | threat #34/#64, sec F16 | Burst of ~500 unauthenticated GET /api/session + lookup requests, one IP | Run burst via `live_server` + `concurrent.futures` | `SELECT count(*) FROM session` unchanged (no anonymous rows written); public lookup still returns 200s, not 503 | N — cost reason: 500 requests is 5-25x the volume of every other concurrency case in this suite (TC-API-020/021 fire 20-100); adds real wall-clock CPU/socket time, not a wait-out-a-clock-window cost, so clock injection does not remove it. Kept nightly; re-run on-demand whenever `regression-plan.md` §2's rate-limit-middleware row is triggered. |

## Frontend component (Vitest + Testing Library)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-COMP-001 | AC-018, user-flows Flow 5 step 3 | Lookup island rendered | Type blank/whitespace input, submit | "Enter a valid complaint number" shown instantly, no network call fired | Y |
| TC-COMP-002 | screen-inventory #1, NFR-011 | Lookup island, mocked slow API | Submit valid number, mock response never resolves within 10s | "The server is taking too long. Please try again." rendered, button re-enabled | Y |
| TC-COMP-003 | screen-inventory #1 | Mocked `GET /api/session` slow (>4s) | Render page | "Preparing…" label, then inline "Retry" affordance appears | Y |
| TC-COMP-004 | screen-inventory #2 | Login form | Submit with fields empty | Native `required`/`aria-required` block submission; no request fired | Y |
| TC-COMP-005 | screen-inventory #2 | Mocked 401 response | Submit login | Generic "Incorrect username or password.", password field cleared and focused | Y |
| TC-COMP-006 | screen-inventory #4 | Mocked complaints list, empty | Render list, no complaints | "No complaints logged yet. Create the first one." shown | Y |
| TC-COMP-007 | screen-inventory #4 | Mocked list of items | Render list | Each row shows number/status/snippet/date, no name/phone rendered anywhere in the DOM | Y |
| TC-COMP-008 | screen-inventory #4, A11Y-13 | Mocked search | Type in "Search by name or phone", debounce fires | `role="status"` region announces settled count or no-match message | Y |
| TC-COMP-009 | screen-inventory #3 | Change-password form, forced mode | Render with `must_change_password:true` | No `current_password` field rendered; nav hidden/disabled | Y |
| TC-COMP-010 | screen-inventory #5, UX-F2 | OTP-display dialog open, checkbox unchecked | Attempt Escape / simulated navigate-away | Dialog is not dismissed; confirmation guard fires per component-spec #9 | Y |
| TC-COMP-011 | user-flows Flow 2 step 1/2, BR-006/012/014 | New-complaint form rendered | Submit with name/phone/description empty | `required`/`aria-required` markup blocks submission client-side; on forced submit (e.g. programmatic), a top-of-form error summary appears listing each invalid field, each item linking to (focusing) its field; no network call fired | Y |
| TC-COMP-012 | user-flows Flow 4 step 3, Flow 3 step 3, AC-008/BR-011 | Complaint detail panel, one case >7 days old and one <7 days old; separately, a stale-load scenario | Render both ages; separately, load detail then simulate a newer server-side status-history entry before submit | Past-window: edit action visibly disabled with tooltip/caption "Editing is only available within 7 days of logging a complaint," no form fields enabled; within-window: edit form enabled and submittable; stale-load: non-blocking advisory banner appears ("This complaint was updated by {clerk} a moment ago...") but submit remains available (BR-011 last-write-wins, UI warns not blocks) | Y |
| TC-COMP-013 | screen-inventory #3, ADR-014 Q4 (accepted, voluntary change password in scope) | Change-password form rendered via the voluntary "Change password" user-menu entry point (`must_change_password:false`) | Render form; submit with wrong current password (mocked 422) | Unlike the forced path (TC-COMP-009), a `current_password` field is rendered and required; on a mocked wrong-current-password response, generic error matching Login's wording is shown, field retains focus, new-password fields are not cleared | Y |
| TC-COMP-014 | user-flows Flow 2 steps 3/6, api-contract §7 (client_request_id) | New-complaint form, valid data entered | (a) Click submit twice in rapid succession (double-submit); (b) submit, mock a network/timeout failure, then retry | (a) Button disables and shows spinner + "Saving…" on first click; second click is a no-op — exactly one request is fired (same `client_request_id` reused, not regenerated per click); (b) on failure all entered data is preserved (nothing cleared), button re-enables, and the retry re-sends the same `client_request_id` so a delayed-but-successful first attempt cannot create a duplicate row (cross-checked against TC-API-017) | Y |

## E2E (Playwright for Python, pytest -m e2e — 6 specs, release-gate pipeline)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-E2E-001 | AC-001 | Seeded clerk, real stack running | Open `/login`, submit valid credentials | Redirected to `/complaints`, session cookie present | R |
| TC-E2E-002 | AC-002, NFR-011 | Logged-in clerk | Fill new-complaint form, submit; separately, stub a slow response | Success shows complaint number confirmation with Copy button; timeout path shows the timeout message, form data preserved | R |
| TC-E2E-003 | AC-004, BR-002 | Complaint in `new` | Attempt to select an illegal next status | Only legal next statuses are offered/selectable; a forced illegal attempt via direct API call from the same session is rejected (cross-checked against TC-API-031) | R |
| TC-E2E-004 | AC-006, AC-007 | Real complaint exists | Open `/`, look up the number; then look up a non-existent number | Success shows number/status/date/public message, no name/phone in DOM; not-found path shows the not-found message | R |
| TC-E2E-005 | AC-017 | Admin clerk logged in | Reset a clerk's password, then log in as that clerk with the OTP | OTP shown once; forced `must_change_password` redirect works; old password no longer authenticates | R |
| TC-E2E-006 | AC-018 | Public lookup page | Submit blank/malformed number | "Enter a valid complaint number" shown, no network request observed (client-side check per BR-015 defence-in-depth) | R |

## Security (integration-level pytest unless noted; maps to threat-model.md rows)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-SEC-001 | AC-001, threat #1/#30 | Seeded clerk | 3+ wrong-password attempts, then a correct one | Each failure identical generic 401; no lockout of the correct login (anti-lockout, arch F4) | Y |
| TC-SEC-002 | AC-006, BR-005, threat #21/#22 | Complaint with name/phone/note set | Inspect full public lookup response body (headers + JSON), byte-for-byte | No occurrence of the name, phone, or note string anywhere, including headers | Y |
| TC-SEC-003 | AC-011, NFR-005, threat #33 | One IP | Fire >20 concurrent lookup requests within 1 minute via `concurrent.futures` | Exactly 20 succeed per window; remainder 429 `rate_limited` with `Retry-After`; sequential-loop evidence explicitly rejected | Y |
| TC-SEC-004 | AC-015, BR-003 | No session | Direct POST to create/status/edit endpoints | All rejected 401, no record created/changed (both write types) | Y |
| TC-SEC-005 | AC-015, BR-003, threat #41 | Parametrised over the whole route table | For every non-public route, call with no session | Every one denies with 401 (deny-by-default, not per-route allow) | Y |
| TC-SEC-006 | AC-016, BR-008, threat #14 | Complaint exists | Attempt a direct delete-style request (no DELETE endpoint exists at all) | No delete verb reaches any handler; record unchanged; `UPDATE`/`DELETE` against `complaint_status_history`/`complaint_edit_history`/`security_event` raises at the data-access layer | Y |
| TC-SEC-007 | AC-017, BR-013, threat #42 | Regular clerk session AND admin session | Call the 3 admin-only endpoints from each | Regular: 403 `forbidden` on all 3. Admin: succeeds on all 3 — both directions proven together | Y |
| TC-SEC-008 | api-contract §Conventions, threat #8 | Authenticated session, valid cookie | POST a write endpoint with missing/wrong `X-CSRF-Token` | 403 `forbidden` | Y |
| TC-SEC-009 | api-contract §Conventions, threat #9 | Anonymous, valid CSRF seed cookie | POST /api/lookup with missing/wrong CSRF token or disallowed `Origin` | 403 `forbidden` on the public route too — CSRF is not exempted for anonymous writes | Y |
| TC-SEC-010 | AC-017, BR-016 | — | See TC-UNIT-008/TC-API-114 | Password minimum length 12 enforced at both account-create and reset | Y |
| TC-SEC-011 | threat #7/#50, api-contract §3 | Account with an un-consumed OTP | Log in once with the OTP, then attempt to log in again with the same OTP | First login succeeds (must-change session); second attempt fails 401 `not_authenticated` (credential destroyed, not merely flagged) — proves single-use | Y |
| TC-SEC-011b | error-catalog `otp_expired` | OTP issued, injected clock (`core/clock.py`) advanced past 72h without being used | Log in with the still-unused, expired OTP | 401 `otp_expired`, distinct from `not_authenticated`, directs to ask admin for a new one | Y (clock-injected — no real wait) |
| TC-SEC-012 | tech-stack assertion 1, BR-010 | Production-shaped config | GET /docs, /redoc, /openapi.json | All three return 404 | R |
| TC-SEC-013 | api-contract §2, threat #34(a) | No session cookie | GET /api/session | Zero SQL statements executed (same as TC-DB-003, listed here for the security-assertion cross-reference) | Y |
| TC-SEC-014 | tech-stack §Auth, sec F20 | Authenticated session | Advance injected clock past the configured idle window (30-60 min) without activity | Session rejected and revoked on next request | Y (clock-injected — no real wait) |
| TC-SEC-015 | tech-stack §Auth | Authenticated session | Advance injected clock past `absolute_expires_at` (~9h) | Session rejected and revoked regardless of recent activity | Y (clock-injected — no real wait) |
| TC-SEC-016 | threat #36, arch F4 | Attacker IP sends many wrong-password attempts against a known username | Observe tier-3 behaviour | 429 with short `Retry-After` (≤5s), never a hard account lock; the office's own IP with a recent success is unaffected | Y |
| TC-SEC-017 | error-catalog `must_change_password` | Session with `must_change_password:true` | Call any route other than `/api/password/change`, `/api/logout`, `GET /api/session` | 403 `must_change_password` on every one, including a direct API call | Y |
| TC-SEC-018 | threat #14, BR-008 | — | Attempt `UPDATE`/`DELETE` at the ORM layer against the three append-only tables | Raises before reaching the database | Y |
| TC-SEC-019 | AC-017, both directions | Regular clerk | Attempt `/accounts` by direct URL (not just checking nav hiding) | 403-equivalent explicit "no permission" state, not a silent redirect (FR-019) — server-checked, UI is cosmetic | Y |
| TC-SEC-020 | threat #24, api-contract §Conventions | Authenticated clerk session | Call `GET /api/complaints/{id}` and `/activity` 121 times within an hour | 121st call returns 429 `rate_limited` (`detail` scope) | Y |
| TC-SEC-021 | threat #24, R4-2/R4-6 | Authenticated clerk session | Call `POST /api/complaints/search` 121 times within an hour | 121st call returns 429 `rate_limited` (`search` scope) | Y |
| TC-SEC-022 | api-contract §Conventions, R4-3 | Authenticated clerk | Call `POST /api/complaints` 61 times within an hour | 61st call returns 429 `rate_limited` (`write` scope) — distinct `reason_code` from `detail` | Y |
| TC-SEC-023 | threat #26, sec F19 | Login failure and success events occur | Inspect `security_event` rows | No row contains a password, OTP, or complaint number in any column | Y |
| TC-SEC-024 | tech-stack §Rate limiting, arch F3 | — | Force a request that increments the limiter counter, then let the surrounding request fail/rollback | Counter increment persists (dedicated AUTOCOMMIT connection, not rolled back with the request) | Y (deterministic, no clock/volume cost — reclassified from N; nothing here required a real wait) |
| TC-SEC-025 | backend-architecture.md SEC-T22, AC-017 | Account with an un-consumed OTP | Log in with the OTP; inspect `password_hash` before/after; then, from the resulting must-change session, call `POST /api/password/change` supplying no `current_password` | (a) `password_hash` differs from its pre-login value and a second login attempt with the same OTP fails 401 (hash destroyed, not a flag); (b) the must-change session's password-change call succeeds with no `current_password` field required, and is otherwise confined to change-password/logout/`GET /api/session` (cross-ref TC-API-116) | Y |
| TC-SEC-026 | backend-architecture.md SEC-T23 | Two independently established sessions for the same user | Log in again (third login) for that user; separately, change the password | New login revokes only the just-superseded/presented session — the other independent session is still valid afterward; a password change revokes **both** sessions | Y |
| TC-SEC-027 | backend-architecture.md SEC-T24, R2-2 | Full route table | Inspect every route's allowed methods and the CORS middleware config | No route uses a method outside `{GET, POST}`; `allow_methods == {GET, POST}` exactly | Y |
| TC-SEC-028 | backend-architecture.md SEC-T31, SEC-S8 | — | POST any endpoint with `Content-Length` above `MAX_REQUEST_BODY_BYTES` | 413 rejected before the route handler runs (assert handler-entry marker never set) | Y |
| TC-SEC-029 | backend-architecture.md ARCH-T32, ARCH-F3 | Authenticated session, voluntary change-password path | POST /api/password/change with a wrong `current_password` | 422 `invalid_current_password`, `fields.current_password`; the session is still usable afterward (a follow-up authenticated call succeeds) | Y |
| TC-SEC-030 | backend-architecture.md ARCH-T33, ARCH-F4 | Authenticated session | POST /api/logout; separately, POST /api/password/change | Logout's returned token verifies against the anonymous HMAC path (proves it is not a live session token); password change sets a new `__Host-session` cookie (session rotation, not reuse) | Y |
| TC-SEC-031 | backend-architecture.md SEC-T21, SEC-F5 | Real gunicorn process started with the container CMD (not the bare ASGI app), over a TCP socket | (1) forged `Fly-Client-IP`/`X-Forwarded-For` from an untrusted loopback peer; (2) same header from a peer inside `TRUSTED_PEER_CIDRS`; (3) two distinct real client addresses; (4) `selfcheck` under stock `UvicornWorker`/with `FORWARDED_ALLOW_IPS` set/with a `ProxyHeadersMiddleware` present | (1) one limiter key valued at the loopback address (header ignored); (2) header honoured, real key used; (3) two distinct limiter keys, never collapsed; (4) `selfcheck` fails in all three misconfigurations | N — cost reason: requires booting the actual production gunicorn CMD as a subprocess (worker fork + socket bind, ~1-3s per case × 4 cases), materially slower than the lightweight in-thread `live_server` fixture every other integration test uses; kept nightly and re-run whenever `core/client_ip.py` or the gunicorn/CMD config changes (regression-plan.md §2) |
| TC-SEC-032 | backend-architecture.md SEC-T28, SEC-S2 | Sustained 429 burst on one `(scope, key, window_start)` | Fire the burst via `concurrent.futures` against `live_server` | Exactly **one** `throttle_*` `security_event` row is written for the whole burst, not one per rejected request | Y |
| TC-SEC-033 | backend-architecture.md SEC-T29, SEC-F3 | Full route table; two freshly minted sessions for the same user | Walk the route table against the per-route PII-classification table; call `GET /api/complaints/{id}/activity` and `POST /api/complaints/search` from each session | Every route has a classification-table row (test fails if any route is missing one) and carries exactly the scope(s) its row names; the two sessions share one `detail` counter; `/activity` counts under `detail`, `/search` counts under `search` | Y |
| TC-SEC-034 | backend-architecture.md SEC-T30, R4-3/R4-5 | Authenticated clerk (regular and admin as applicable) | Exceed `RATE_LIMIT_WRITE_PER_HOUR` on `POST /api/complaints`, `POST /api/accounts`, `POST /api/accounts/{id}/reset-password`; exceed `RATE_LIMIT_SEARCH_PER_HOUR` on `POST /api/complaints/search`; inspect counters after one `POST /api/complaints` | All four write-scope endpoints 429 past their threshold; search 429s past its own separate threshold; one `POST /api/complaints` is shown to increment **both** the `write` and `detail` counters before the handler runs | Y |
| TC-SEC-035 | backend-architecture.md SEC-T33, R4-5 | One `(username, IP)` pair | Repeated failed logins within a 15-minute window; continue past the `login_ip` tier's own limit | At most **one** `login_failure` `security_event` row is written per 15-minute window for that pair; none at all once the `login_ip` tier is past its limit | Y |
| TC-SEC-036 | AC-015/AC-017, threat #26 (log-capture, broader than TC-SEC-023's `security_event`-table scope) | Login failure/success, OTP issuance, and a validation-error request all occur with structured application logging enabled | Capture stdout/structured log output for the whole request set and inspect every emitted line | No log line contains a password, OTP, session-cookie value, CSRF token, complaint-number-linked citizen name, or citizen phone number, in any field including exception tracebacks | Y |
| TC-SEC-037 | backend-architecture.md PERF-T26, test-strategy.md §6 (rate-limiter sweep boundary) | Burst that creates limiter rows under many never-recurring keys; injected clock advanced past the window boundary | Issue the specified number of subsequent limited requests | The counter table is brought back under its ceiling within that number of requests (deterministic sweep-on-rollover, not size-unbounded growth) | Y (clock-injected — no real wait; reclassified from the un-ID'd description in test-strategy.md rev 1 §6) |
| TC-SEC-038 | backend-architecture.md PERF-T27, test-strategy.md §6 (session-sweep boundary) | Expired session rows exist; injected clock advanced past their expiry | Perform one subsequent successful login | Expired session rows are gone afterward; the sweep statements are row-bounded via the `ctid` sub-select and keyed off `SESSION_IDLE_MINUTES`, not a literal interval | Y (clock-injected — no real wait) |
| TC-SEC-039 | backend-architecture.md §2 rows 1-6, tech-stack.md assertion 16, ADR-007, threat-model.md #8/#9 (CSRF), #41 (deny-by-default), #43 (`must_change_password` gate) | Fresh `create_app()` instance built with test settings, before any request is served | Introspect the Starlette middleware stack `create_app()` registers (e.g. `app.user_middleware`) and record the class sequence outermost→innermost | Sequence equals, exactly and in this order: (1) `TrustedHostMiddleware`, (2) request-ID + security-headers, (3) `CORSMiddleware`, (4) session loader, (5) CSRF, (6) authorization — matching backend-architecture.md §2 rows 1-6 byte-for-byte; any swap, omission, or insertion fails the test. This is the regression test for ADR-007's ordering guarantee that CSRF cannot be bypassed by running before the session is loaded and that authorization cannot be bypassed by running before CSRF | Y |

## Accessibility (A11Y — component + E2E cross-checked)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-A11Y-001 | screen-inventory #4, AC-016 | Complaint detail rendered | Inspect available actions | No delete control exists in the accessibility tree at all (nothing to focus, nothing to announce) | Y |
| TC-A11Y-002 | screen-inventory #1, A11Y-12 | Public lookup page | Trigger each state transition (Preparing→ready→Checking→result) | Single `role="status"`/`aria-live="polite"` region announces each transition without a forced focus move | Y |
| TC-A11Y-003 | screen-inventory #2, A11Y-06 | Redirected via session-expiry | Land on `/login` with the expiry banner | Focus moves to the banner on appearance | Y |
| TC-A11Y-004 | screen-inventory #4, A11Y-05 | ≥900px and <900px layouts | Tab through the complaints screen | Focus order matches the documented order at each breakpoint, including "Back to list" first below 900px | Y |
| TC-A11Y-005 | screen-inventory #1 | JavaScript disabled | Load `/` | `<noscript>` message renders without any script | R |
| TC-A11Y-006 | screen-inventory #1, #4 | 320px viewport | Load public lookup and complaints list | No horizontal scroll; touch targets ≥44×44px | R |

## Performance (E2E-driven, network-throttled)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-PERF-001 | AC-010, NFR-001 | Real complaint exists | Playwright with a 3G-equivalent throttling profile, submit lookup | Result renders within 3 seconds | R |
| TC-PERF-002 | AC-010, NFR-002 | 5 concurrent clerk sessions active and writing | A citizen lookup runs concurrently | Lookup still completes within 3 seconds | R |

## Design/config review (no automated test — evidence is a review artifact)

| ID | Traces-to | Preconditions | Steps | Expected result | Reg |
|---|---|---|---|---|---|
| TC-DESIGN-001 | AC-013, NFR-010 | Deployed configuration / scheduled-job inventory | Inspect all cron/scheduled-job definitions and application code for any deletion path | No job or code path deletes a complaint record before 12 months; evidence is a code/config review note, not a live wait | R |

## Architecture assertion → TC id(s) (backend-architecture.md §13, "Test hooks this layout must keep true")

Every named assertion SEC-T21..T33 / REL-T25 / ARCH-T32/T33 / PERF-T26/T27 (backend-architecture.md:
294-324) maps to an existing or new row below; none is left unmapped.

| Architecture assertion | Covering TC id(s) | New row? |
|---|---|---|
| SEC-T21 (real-gunicorn IP derivation, 4 cases) | TC-SEC-031 | new |
| SEC-T22 (OTP consumption by hash destruction + must-change session scope) | TC-SEC-025 (a/b), TC-SEC-011b (c, expiry) | new + existing |
| SEC-T23 (session revoke scope: presented-only, both-on-password-change) | TC-SEC-026 | new |
| SEC-T24 (GET/POST-only route table + CORS allow_methods) | TC-SEC-027 | new |
| REL-T25 (idempotent replay: same complaint id, row count unchanged) | TC-API-017 | existing |
| PERF-T26 (rate-limiter counter sweep on rollover) | TC-SEC-037 | new |
| PERF-T27 (session-sweep: expired rows gone after next login) | TC-SEC-038 | new |
| SEC-T28 (one `throttle_*` security_event row per sustained burst) | TC-SEC-032 | new |
| SEC-T29 (PII-classification route-table walk + detail-counter keying) | TC-SEC-033 | new |
| SEC-T30 (429 write/search scopes + double-counter increment) | TC-SEC-034 | new |
| SEC-T31 (413 body-limit rejection before handler) | TC-SEC-028 | new |
| SEC-T33 (login_failure dedup per 15-min window) | TC-SEC-035 | new |
| ARCH-T32 (wrong current password → 422, session still usable) | TC-SEC-029 | new |
| ARCH-T33 (logout token verifies anonymous; password change rotates cookie) | TC-SEC-030 | new |
| Middleware registration order (tech-stack.md assertion 16; backend-architecture.md §2 rows 1-6, ADR-007) | TC-SEC-039 | new |

Also confirmed present and clearly labelled per reviewer request: **TC-SEC-012** (docs/redoc/openapi
404 in prod, tech-stack assertion 1) and **TC-SEC-006** (no delete capability, traces to AC-016/
BR-008/threat #14).

## Coverage summary

- Total test cases: **142** across unit(10)/integration-API(59)/DB(4)/component(14)/E2E(6)/
  security(40)/a11y(6)/perf(2)/design(1). Recounted directly from the rows in this file after the
  rev 3 rework added TC-SEC-039 (arch F16) — this number is the single figure restated identically
  in test-strategy.md §1, regression-plan.md, test-plan.md, and README.md.
- **Always-run / nightly / release-gate totals, recounted exactly by level (grep-counted against the
  "Reg" column, not estimated):**

  | Level | Total | Always-run (Y) | Nightly (N) | Release-gate (R) |
  |---|---|---|---|---|
  | Unit | 10 | 10 | 0 | 0 |
  | Integration — API | 59 | 59 | 0 | 0 |
  | Integration — DB | 4 | 3 | 1 (TC-DB-004) | 0 |
  | Integration — Security | 40 | 38 | 1 (TC-SEC-031) | 1 (TC-SEC-012) |
  | Component | 14 | 14 | 0 | 0 |
  | E2E | 6 | 0 | 0 | 6 |
  | A11y | 6 | 4 | 0 | 2 (TC-A11Y-005/006) |
  | Perf | 2 | 0 | 0 | 2 |
  | Design review | 1 | 0 | 0 | 1 |
  | **Total** | **142** | **128** | **2** | **12** |

  This corrects rev 2's always-run enumeration, which summed to 124 by omitting the 4 always-run
  a11y cases entirely and by implicitly counting **TC-SEC-012 as always-run** when its own row has
  always carried `Reg: R` (it is a release-gate check — `/docs`/`/redoc`/`/openapi.json` 404 under
  "production-shaped config", not a CI-pipeline case). Estimated wall-clock for the 128 always-run
  cases is still **≤8 minutes** (unit + integration + component target sums per test-strategy.md §6;
  the 4 always-run a11y cases are component-level checks adding negligible time), comfortably under
  the 15-minute ceiling.
- Of the 128 always-run cases, **5 are always-run because of clock injection** (`core/clock.py`,
  implementation-plan.md T-005): TC-SEC-011b/014/015 and the two sweep-boundary cases TC-SEC-037/038
  — each moves a real-wait boundary check to milliseconds via `advance(delta)`. **TC-SEC-024,
  TC-API-019 and TC-API-054 are always-run for a separate, non-clock reason** (see each row: TC-SEC-024
  has no clock or volume cost at all; TC-API-019 forces collisions via a monkeypatched generator, no
  time dimension; TC-API-054 simulates a stalled response via mocking) — see test-strategy.md §3/§6.
- Nightly-only (Reg=N), with a concrete non-clock cost reason stated on the row: **TC-DB-004**
  (500-request burst — sheer volume, 5-25x every other concurrency case) and **TC-SEC-031**
  (spins up a real gunicorn subprocess, not the lightweight `live_server` thread).
- Every AC-001..AC-019 has ≥1 covering row (cross-check against test-strategy.md §9's traceability
  matrix — identical IDs, no drift; every ID in that matrix is grep-verified to exist in this file).
- Every item in project-testing.md § "Business rules worth checking" is covered: TC-DB-001/002
  (blank/malformed→no query), TC-API-031 (no status skip), TC-API-051/TC-SEC-002 (no PII public),
  TC-SEC-003 (20/min parallel), TC-SEC-018 (append-only), TC-SEC-007 (admin-only both directions),
  TC-SEC-008/009 (CSRF 403 both authenticated and public), TC-SEC-010/011 (password 12 / OTP 72h
  single-use).
- Voluntary change-password (**ADR-014 Q4**) and name/phone search (**ADR-014 Q3**) were accepted as
  MVP scope at GATE_4 — they carry ordinary TC coverage (TC-COMP-013; TC-COMP-008/screen-inventory
  search) with no "pending confirmation" caveat. (These are unrelated to architecture/open-questions.md's
  own OQ-9/OQ-10, which cover detail-view auditing and log retention respectively — no reference to
  either of those OQ numbers belongs in this document.)
