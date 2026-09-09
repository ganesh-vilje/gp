# Project Config (project-specific; the global org reads this)
# Filled at GATE_2 (2026-09-09) from .ai/technology/tech-stack.md rev 5 § Expected commands.
# Two stacks: API (Python) and web (TypeScript). Paths marked <…> are set in /plan.

stack: FastAPI (Python 3.13, JSON API only, sync handlers) + SQLAlchemy 2.x + Alembic + psycopg 3 | PostgreSQL 17 (managed) | Next.js 15 / React 19 / TypeScript 5 on Node 22 LTS, fully static export (output: "export") | hosting: Fly.io Mumbai (bom) Machine + Fly Managed Postgres for the API/DB (human answer Q1), free Render Static Site for the exported frontend | AI/LLM: none
package_manager: uv (API, committed uv.lock)
package_manager_web: npm (Node 22 LTS pinned in .nvmrc, committed package-lock.json)
install: uv sync --frozen
install_web: npm ci --ignore-scripts
run_dev: uv run uvicorn app.main:app --reload --port 8000
run_dev_web: npm run dev   # Next.js dev server on port 3000; NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
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
typecheck: uv run mypy <app_package>   # app package only — exact path TBD (set in /plan)
typecheck_web: npx tsc --noEmit
security_audit: uv run pip-audit   # reports all severities; fails on high/critical
security_audit_web: npm audit --audit-level=high && npm audit signatures
gen_api_types: npm run gen:api-types   # openapi-typescript → src/api-types.ts, committed; CI fails if stale
gen_csp_headers: npm run gen:csp   # post-build: hashes inline scripts, writes per-path CSP headers
deploy_check: uv run selfcheck   # production-config gate; CI + every startup
build: none locally — platform build: pip install uv==<pinned> && uv sync --frozen   # Fly.io: Dockerfile (required by Fly; base-image patching owned by the human, Q6)
build_web: npm ci --ignore-scripts && npm run build && npm run gen:csp   # static export in out/
start: uv run gunicorn app.main:app --worker-class uvicorn_worker.UvicornWorker --workers 2 --timeout 30 --graceful-timeout 30 --keep-alive 5 --max-requests 1000 --max-requests-jitter 100 --bind 0.0.0.0:$PORT --access-logfile - --error-logfile - -- --proxy-headers --forwarded-allow-ips=<platform proxy>
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
base_url_prod: TBD (set in /plan)   # expected https://www.<domain>.in
base_url_api_prod: TBD (set in /plan)   # expected https://api.<domain>.in
production_deploy: human-only, twice — promote the API first, then the static site; auto-deploy OFF on both

# app-qa integration: the global app-qa skill reads .claude/project-testing.md,
# generated at GATE_2 from the values above. /plan refines paths marked <…>.
