# Architecture review — advisories carried forward to /plan

Non-blocking medium/low findings from the APPROVING verdicts (rev 4, 2026-09-10). Owners fix
them in the next touch of the named file; /plan must not contradict them.

## Medium
- SEC-F1 (rev 4): two of the three RawPeerWorker selfcheck assertions (uvicorn Config.proxy_headers
  is False; no ProxyHeadersMiddleware in the stack) cannot be made from the ASGI app — move them into
  `app/worker.py` (refuse to serve) and keep only the FORWARDED_ALLOW_IPS check in `selfcheck`;
  restate SEC-T21 case 4. Owner: solution-architect.
- SEC-F2 (rev 4): `login_success` is the only unbounded writer into `security_event` — count
  successful logins in a per-IP or per-user scope, or apply the once-per-window rule; name it in
  threat #34(c). Owner: solution-architect.
- SEC-F3 (rev 4): infrastructure.md §12.4 states the DB-level REVOKE as fact and names
  `complaint_history`/`complaint` — rewrite conditionally, naming the three real append-only tables;
  reconcile threat #64 with #20. Owner: solution-architect.
- ARCH-F1 (rev 4): error-catalog.md:72-74 scopes the `detail` counter on POST /api/complaints to
  the replay only; must read "every call, pre-handler" like api-contract.md:276. Owner: data-api-architect.

## Low
- SEC-F4: state the `login_failure` dedup mechanism as "write only when the `login_userip` upsert
  RETURNING count == 1". SEC-F5: record in threats #7/#50 that theft of a must-change session allows a
  password set without any credential (bounded: seconds-long window, three routes, revoke-all).
  SEC-F6: mark `POST /api/complaints/search` as "matches on name/phone" in both PII tables and #24.
  SEC-F7: bump five doc headers from rev 3 to rev 4. SEC-F8: R4-4's error-code list is wrong — point
  to error-catalog.md. SEC-F9: error-catalog `detail` wording (same as ARCH-F1). ARCH-F2: schema.md:431
  limiter row omits the `search` scope. PERF-F5: noted in schema retention. REL lows: runbook §11 lists
  reset-admin-password (done); client_request_id does not survive a closed tab (noted).
- Upstream cleanups (not architecture-owned): acceptance-criteria.md AC-006 first bullet still says
  "latest status note" (requirements-analyst); screen-inventory.md:62 wrong-current-password is now a
  field-level error (ux-designer); technology-comparison.md:747 and tech-stack.md start commands must
  use `--worker-class app.worker.RawPeerWorker` with no proxy flags (technology-evaluator);
  `.claude/project-config.md` `start:` likewise — set at /plan.
