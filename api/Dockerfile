# T-017 (infrastructure.md §3, ADR-023). Production image for the API.
#
# TODO: pin to a digest (FROM python:3.13-slim@sha256:<digest>) once a
# registry lookup can be verified from an environment with network access
# (GATE_6 Q1: no Docker/registry access on the local build machine). Track
# via the monthly scheduled CI rebuild job (infrastructure.md §5/§11) which
# opens a PR when the digest moves; base-image patching is the human's
# obligation (ADR-002 Q6).
FROM python:3.13-slim

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
