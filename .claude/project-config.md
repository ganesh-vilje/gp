# Project Config (project-specific; the global org reads this)
# Filled at GATE_2 (2026-09-09) from .ai/technology/tech-stack.md rev 5 § Expected commands.
# rev 2 (2026-09-10) /plan rework: start: binds literal 8080 [A-F4], run_dev adds --no-proxy-headers
# [A-F12], added db_start [A-F13] and openapi_dump [A-F13].
# GATE_6 (2026-09-10): db_start -> locally installed PostgreSQL 17 (no Docker), uv pin 0.10.8, toolchain line added.
# rev 3 (2026-09-10): local PostgreSQL is 16 (not 17); production/CI stay on 17. Local role + databases already exist.
# Two stacks: API (Python) and web (TypeScript). Paths marked <…> are set in /plan.

stack: FastAPI (Python 3.13, JSON API only, sync handlers) + SQLAlchemy 2.x + Alembic + psycopg 3 | PostgreSQL 17 (managed) | Next.js 15 / React 19 / TypeScript 5 on Node 22 LTS, fully static export (output: "export") | hosting: Fly.io Mumbai (bom) Machine + Fly Managed Postgres for the API/DB (human answer Q1), free Render Static Site for the exported frontend | AI/LLM: none
package_manager: uv (API, committed uv.lock)
package_manager_web: npm (Node 22 LTS pinned in .nvmrc, committed package-lock.json)
install: uv sync --frozen
install_web: npm ci --ignore-scripts
run_dev: uv run uvicorn app.main:app --reload --port 8000 --no-proxy-headers   # [rework A-F12] uvicorn's own --proxy-headers defaults on; --no-proxy-headers keeps dev's scope["client"] behaviour in parity with the production app.worker.RawPeerWorker (ADR-023); parity re-verified at task T-025
run_dev_web: npm run dev   # Next.js dev server on port 3000; NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
db_start: none — locally installed PostgreSQL **16** service at C:\Program Files\PostgreSQL\16\bin (GATE_6 Q1: Docker is NOT installed on the build machine). Local role panchayat / password panchayat and databases panchayat and panchayat_test ALREADY EXIST — do not re-create them. DATABASE_URL=postgresql+psycopg://panchayat:panchayat@localhost:5432/panchayat (tests: .../panchayat_test). Production (Fly Managed Postgres) and CI (T-016 service container) stay on PostgreSQL 17 — avoid PostgreSQL 17-only SQL features, since they cannot be verified locally. infrastructure.md §4's "Docker" wording is superseded by this line.
toolchain: build machine has Python 3.11.9 (uv installs 3.13 for the project via .python-version — never the system interpreter), Node 22.21.0, uv 0.10.8, PostgreSQL 16 (psql/pg_dump at C:\Program Files\PostgreSQL\16\bin — add to PATH or call by full path), no Docker (GATE_6 Q1). Docker-based checks (T-017/T-043 image build, M5 demo step 1) run in CI, not locally.
run_test_unit: uv run pytest -m "not e2e and not integration"
run_test_integration: uv run pytest -m integration   # needs Postgres
run_test_web: npm run test   # vitest run
run_test_e2e: uv run pytest -m e2e   # needs `uv run playwright install chromium` once, the exported frontend served locally with the host's rewrite rule, and the API running
test_all: uv run pytest && npm run test
coverage: uv run pytest --cov --cov-report=term-missing
lint: uv run ruff check .
lint_web: npx biome ci .
format_check: uv run ruff format --check .
format_check_web: npx biome format .
typecheck: uv run mypy app   # run from api/; app package only (api/app/), per backend-architecture.md §1
typecheck_web: npx tsc --noEmit
security_audit: uv run pip-audit   # reports all severities; fails on high/critical
security_audit_web: npm audit --audit-level=high && npm audit signatures
openapi_dump: curl -s http://localhost:8000/openapi.json -o api/openapi.json   # [rework A-F13] source file for gen_api_types; API must be running first (run_dev)
gen_api_types: npm run gen:api-types   # openapi-typescript → src/api-types.ts, committed; CI fails if stale; consumes api/openapi.json from openapi_dump above
gen_csp_headers: npm run gen:csp   # post-build: hashes inline scripts, writes per-path CSP headers
deploy_check: uv run selfcheck   # production-config gate; CI + every startup
build: none locally — platform build: pip install uv==0.10.8 && uv sync --frozen   # Fly.io: Dockerfile (required by Fly; base-image patching owned by the human, Q6); uv pinned to 0.10.8 = the version on the build machine (GATE_6 Q3); kept in sync with api/Dockerfile
build_web: npm ci --ignore-scripts && npm run build && npm run gen:csp   # static export in out/
start: uv run gunicorn app.main:app --worker-class app.worker.RawPeerWorker --workers 2 --timeout 30 --graceful-timeout 30 --keep-alive 5 --max-requests 1000 --max-requests-jitter 100 --bind 0.0.0.0:8080 --access-logfile - --error-logfile -   # [rework A-F4] literal 8080, not $PORT — Fly Machines set no $PORT env var (that convention is Render's, tech-stack.md:804); fly.toml's internal_port is 8080 (infrastructure.md:101) and must match this literally; ADR-023/infrastructure.md §3: no --proxy-headers / --forwarded-allow-ips (gunicorn has no such flag; app.worker.RawPeerWorker sets proxy_headers=False, forwarded_allow_ips=[] in-repo); FORWARDED_ALLOW_IPS must be unset in every environment (selfcheck refuses to start otherwise); done-condition verified at task T-043
start_web: none — static host serves out/ from its CDN
db_migrate: uv run alembic upgrade head   # production: platform release command, human-triggered deploy only
db_makemigrations: uv run alembic revision --autogenerate -m "<message>"   # always human-reviewed before commit
db_check_drift: uv run alembic check
bootstrap_admin: uv run bootstrap-admin   # interactive stdin (getpass); refuses non-interactive without --from-env
unlock_account: uv run unlock-account <username>   # one-off platform shell only
environments: dev | test | staging | prod   # never mix; prod is human-only. No staging environment at launch (frontend PR previews only; not in the API CORS allow-list)
base_url_dev: http://localhost:3000   # the Next.js app — what a human or browser test opens
base_url_api_dev: http://localhost:8000
base_url_staging: not applicable (no staging)
base_url_prod: TBD — human provides domain at /release (OQ-3, architecture/open-questions.md); expected https://www.<domain>.in
base_url_api_prod: TBD — human provides domain at /release (OQ-3); expected https://api.<domain>.in; must share one registrable domain with base_url_prod (ADR-007, infrastructure.md §2)
production_deploy: human-only, twice — promote the API first, then the static site; auto-deploy OFF on both

# app-qa integration: the global app-qa skill reads .claude/project-testing.md,
# generated at GATE_2 from the values above. /plan refines paths marked <…>.
