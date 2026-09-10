# Architecture — panchayat-complaint-tracker

Produced in the `/architecture` phase (rev 1, 2026-09-09) from requirements rev 5, tech-stack
rev 5.1, UX rev 3 and ADR-001…ADR-014. **ADRs are binding**: nothing here re-litigates them; where
an ADR deferred a choice to /architecture, this folder makes it and records it.

## Index

| File | Contents | Read it when |
|------|----------|--------------|
| [solution-architecture.md](solution-architecture.md) | Architecture drivers · complexity budget · the 5 constraining decisions · system context · module boundaries · request lifecycle · **business-rule enforcement map** · configuration & secrets · environments · ADR proposals ADR-015…ADR-020 | you need the whole picture, or the human gate |
| [frontend-architecture.md](frontend-architecture.md) | Next.js static-export structure · routing & islands · state · API client and generated types · strings module · CSP hashing step · error/reload handling · byte-budget gates | building or reviewing the web app |
| [backend-architecture.md](backend-architecture.md) | FastAPI module layout · middleware chain order · sessions/CSRF/authz mechanics · rate limiter · error model · complaint-number algorithm · status transitions · audit writes · concurrency · `selfcheck` · CLI | building or reviewing the API |
| [security-architecture.md](security-architecture.md) | Authn/authz model · **permission matrix** · session lifecycle · password & OTP lifecycle · CSRF · headers/CORS/CSP · input validation · PII & data minimisation · **never-log list** · secrets · supply chain | any security review |
| [infrastructure.md](infrastructure.md) | Fly Machine + Managed Postgres (`bom`) · Render Static Site · DNS/TLS · Dockerfile outline · environments · CI/CD stages · deploy & rollback procedure · backup/restore · health checks · capacity · runbook outline | deploying, or /release |
| [observability-reliability.md](observability-reliability.md) | Structured logging · `security_event` · `/healthz` + uptime pinger · **failure-mode table** · timeout ladder · retry/idempotency policy · capacity assumptions | designing for failure, or on-call |
| [open-questions.md](open-questions.md) | 13 questions, each with the default already applied | GATE_5 |
| [../security/threat-model.md](../security/threat-model.md) | STRIDE table, 59 numbered threats (36 mitigated / 14 accepted / 9 n-a), assets, trust boundaries, review triggers | any security review |

## Not designed here

- **Database schema and API contract** — the data-api-architect derives them from the boundaries in `solution-architecture.md` (`.ai/database/`, `.ai/api/`).
- **Implementation plan and task breakdown** — `/plan`.
- **Test plan** — `.ai/testing/`; the security assertions this design must satisfy are listed in `backend-architecture.md` §13.

## Shape of the system, in six lines

One FastAPI monolith (2 gunicorn workers, Fly `bom`) over one PostgreSQL 17 database, plus a
statically exported Next.js bundle on a free CDN with no server. The API is the only security
boundary and the only place citizen PII exists. Business rules live in the service layer; the audit
trail is append-only and enforced at the data-access layer. No queue, no cache, no second runtime,
no third-party processor of citizen data, no AI. Two human-promoted deploys per release, API first.
Total ≈$11–16/month.
