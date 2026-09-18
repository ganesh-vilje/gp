# T-017 (infrastructure.md §3, ADR-023). Production image for the API.
#
# Digest pinned 2026-09-18 via CI registry lookup; ADR-002 Q6 assigns
# ONGOING patching (monthly Dependabot "docker" ecosystem bump) to the
# human, not this initial pin.
FROM python:3.13-slim@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Non-root user for the application process.
RUN adduser --system --no-create-home appuser

WORKDIR /app

# Install uv pinned to the version tracked in .claude/project-config.md
# (build:/toolchain: lines) and kept in sync here.
RUN pip install --no-cache-dir uv==0.10.8

# Dependency layer first for build-cache efficiency.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Application code.
COPY app ./app
COPY migrations ./migrations

USER appuser

EXPOSE 8080

CMD ["uv", "run", "gunicorn", "app.main:app", "--worker-class", "app.worker.RawPeerWorker", \
     "--workers", "2", "--timeout", "30", "--graceful-timeout", "30", "--keep-alive", "5", \
     "--max-requests", "1000", "--max-requests-jitter", "100", "--bind", "0.0.0.0:8080", \
     "--access-logfile", "-", "--error-logfile", "-"]
