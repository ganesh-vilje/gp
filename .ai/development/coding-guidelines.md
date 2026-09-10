# Coding Guidelines — panchayat-complaint-tracker

rev 1 (2026-09-10). Derived from ADR-015…ADR-023, backend-architecture.md, frontend-architecture.md,
security-architecture.md, error-catalog.md. These are project-specific rules on top of the org's
default engineering standards; where this file is silent, the global standard applies.

## Layering (ADR-015 — modular monolith, dependencies point downward only)

`api/routers → services → repositories → db/models`; everything may import `core`; `core` never
imports `services` or `routers`. `middleware` may call `services` but must not know about complaints
or accounts as domain concepts (only "is this request allowed"). A test in `api/tests/unit/` asserts
this by import-graph inspection (no `services` module imports `api`, no `core` module imports
`services`) — this test is written in **T-005/T-006** and must never be weakened. It is a ~15-line
hand-written AST/import-walk check, not a third-party tool: `import-linter` is **deliberately not
adopted** (it is not in dependency-strategy.md's dev-dependency list, §153) — one more dependency for
a single-repo, two-layer rule is not worth it at this size. This check (plus the six forbidden-pattern
greps below) is a **named step in T-016's `ci.yml`**, not an unenforced convention — see
implementation-plan.md's T-016 row.

- **Routers**: request/response DTOs, HTTP status codes, dependency wiring. Never a business rule,
  never a direct repository call, never hand-built SQL.
- **Services**: every business rule, transaction boundaries, audit writes, OTP issuance, status
  transitions. Never import from `api/`; raise typed domain errors instead of touching HTTP.
- **Repositories**: queries, row locks, uniqueness retries, pagination. Never enforce a rule or decide
  a status transition — that is a service's job even if it "would be one line here."
- **core**: settings, error taxonomy, complaint-number codec, clock, hashing, log setup, strings.
  Pure functions and small wrappers only; no I/O beyond what a wrapper module (`hashing.py`,
  `client_ip.py`) explicitly owns.

## Error handling (ADR-018 — single envelope)

- Every domain error is a typed exception in `core/errors.py`; there is exactly one exception-handler
  set that converts it to `{"error":{"code","message","fields","request_id"}}`. **Never** raise a bare
  `HTTPException(detail=...)` from a router — that produces a second, untranslatable error shape.
  Ruff/mypy do not catch this; a route-table test does (walks every router, asserts no
  `HTTPException` import outside `core/errors.py` and the exception-handler registration).
- `code` values are exactly the enum in error-catalog.md — no new code without updating that document
  first (it is not owned by `/build`; a new code is a rework request back to the data-api-architect).
- `invalid_credentials` must never appear anywhere in code, tests, or comments (R4-4) — every failed
  login is `not_authenticated`; the only login-specific code is `otp_expired`.
- Never put a submitted value in `fields` — only a reason code (e.g. `"invalid_format"`), never the
  value itself (a password, a complaint number, a phone number).

## PII and logging (security-architecture.md §8, never-log list)

- **Never pass** a password (submitted or issued), an OTP, a session token, a CSRF token/seed, a
  complaint number, a citizen name/phone/description/clerk note, or a raw request/response body into
  `core/logging.py`, `security_event`, or an exception message that reaches stdout unredacted. The
  redaction filter is a backstop, not the rule — write code that never passes these values to a log
  call in the first place.
- `security_event` writes go **only** through `services/security_events.py`; nothing else constructs
  a row for that table. Column names are exactly `event_type`, `actor_user_id`, `actor_username_hash`,
  `target_user_id`, `derived_ip`, `reason_code`, `created_at` — no renaming, no free text in
  `reason_code`.
- No complaint number, citizen name, or phone number is ever placed in a URL path segment or a query
  string — every criteria-bearing read is a `POST` body (R2-1). A CI grep blocks path parameters named
  `number`, `phone`, `name`, or `q`.

## Validation and typing

- Every request DTO is a Pydantic model with `extra="forbid"` — an unexpected field is a `422`, not a
  silently ignored one (this is also how BR-009's "no government ID field" stays true structurally).
- Every response DTO declares an explicit `response_model` with `extra="forbid"` — no route "returns
  the object." The clerk **list** DTO must never include `citizen_name`/`citizen_phone`; a test walks
  every route and asserts this for the ones the per-route PII table (api-contract.md Conventions)
  marks as not carrying PII.
- `mypy app` runs clean with no `# type: ignore` except where a third-party stub is missing — and
  that exception is commented with which package and why.
- All "now" reads go through `core.clock.now()`, never `datetime.now()`/`datetime.utcnow()` directly,
  anywhere in `app/` — this is what makes session/OTP/limiter-window tests clock-injectable instead of
  nightly-only (implementation-plan.md § Clock injection decision). A grep in CI enforces it.

## Naming

- Python modules/functions: `snake_case`; classes: `PascalCase`; test files `test_<module>.py`; test
  functions `test_<unit>_<scenario>_<expected>` (e.g. `test_update_status_illegal_transition_422`).
- Pytest markers: no marker = unit; `@pytest.mark.integration`; `@pytest.mark.e2e`. A test with real
  Postgres or `live_server` and no marker is a defect, not a style choice — it breaks
  `run_test_unit`'s speed guarantee.
- React components: `PascalCase.tsx`; hooks: `useCamelCase.ts`; every user-visible string is a key in
  `src/strings/en.ts`, never a literal in a component/island (AD-12; CI grep enforces this).
- API routes/paths: exactly as api-contract.md names them — no renaming en route to implementation.

## Module size and forbidden patterns

- Soft limit: a router file handles one resource family (e.g. `complaints.py`, not
  `complaints_and_accounts.py`); a service module ≤ ~300 lines before splitting by sub-concern (as
  `services/complaints/` already does: `__init__.py`, `transitions.py`, `search.py`).
- **Forbidden everywhere:** string-built SQL (Ruff `S` flags it — use SQLAlchemy constructs or the one
  hand-written bound `pg_insert(...)` in the limiter); `datetime.now()`/`utcnow()` outside
  `core/clock.py`; a second exception-handling scheme; a `PATCH`/`PUT`/`DELETE` route (CORS is
  `GET,POST` only, `selfcheck`-asserted); an `UPDATE`/`DELETE` construct against
  `complaint_status_history`, `complaint_edit_history`, or `security_event` (the `before_execute` guard
  raises, but do not write code that relies on being caught — do not write it at all); a route with no
  `response_model`; a `HTTPException(detail=...)` outside the one exception-handler registration.
- **Forbidden in `web/`:** `dangerouslySetInnerHTML`, `innerHTML`, `eval(`, `new Function(`, inline
  `style=`/`style={`, a state library, a CSS framework, a third-party script/font/analytics tag, an
  `href` built from user input without the `https:`/`mailto:` scheme allow-list, a complaint
  number/name/phone in a URL or `history` entry. CI greps for all of these (frontend-architecture §10).
- Every grep in this section (API-side and web-side, six checks total) is a **named step in
  T-016's `ci.yml` job**, not an unenforced convention — a diff that only "should have" been caught is
  a defect in T-016, not a one-off oversight.

## Migrations

- **Additive-only** (schema.md § Migration strategy): add a table, a nullable column (or NOT NULL with
  a server default in the same migration), a pilot-scale index, or an enum value via `ALTER TYPE …
  ADD VALUE` in its own revision ahead of any code that writes it. Never drop/rename/narrow/reorder.
- `alembic revision --autogenerate` output is **always human-reviewed before commit** — read the
  generated SQL, do not trust the diff blindly, especially for CHECK constraints and enum changes
  which autogenerate handles poorly. Before GATE_6 human availability, the reviewing agent (never the
  producing agent) reads it as the required second pair of eyes.
- `alembic check` must be clean in CI before merge (drift gate, compensates for no staging).

## Commit message format and evidence

`T-0NN: <imperative summary>` subject; body names the ACs/BRs/ADRs delivered and the exact TC ids
proven (see implementation-plan.md § Git workflow). **What "evidence" means for a `/build` task:** the
literal stdout tail of the cited command (from `.claude/project-config.md`) showing the specific TC
ids passing, pasted into the PR description — not a claim of "tests pass," not a screenshot with no
command visible, not a summary written after the fact without the terminal output alongside it. A
reviewer re-runs the command; they do not accept the paste as fact.

## Security-sensitive modules — extra care

`app/worker.py`, `app/core/client_ip.py`, `app/main.py` (middleware assembly and ordering — T-010a),
`app/middleware/{session_loader,csrf,authz}.py`, `app/services/{auth,accounts}.py`,
`app/services/limiter.py` — any change to these files triggers the full security regression subset
(see change-impact-map.md) regardless of how small the diff looks. These are exactly the modules
where the architecture review found and reworked bugs three to four times before GATE_5; treat a
"trivial" change here as never trivial.
