"""ASGI application factory.

`create_app()`: settings -> selfcheck -> middleware (in order) -> routers
(backend-architecture.md §1). This task (T-001) wires only settings and the
`/healthz` route; `selfcheck`, middleware and routers land in later tasks.
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from app.settings import get_settings


class HealthzResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    @app.get("/healthz", response_model=HealthzResponse)
    def healthz() -> HealthzResponse:
        return HealthzResponse(status="ok")

    return app


app = create_app()
