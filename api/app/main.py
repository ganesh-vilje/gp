"""ASGI application factory.

`create_app()`: settings -> selfcheck -> middleware (in order) -> routers
(backend-architecture.md §1). T-001 wired only settings and `/healthz`;
`selfcheck` and routers still land in later tasks. T-006 registers rows 4-6
of the ADR-007 middleware chain (backend-architecture.md §2) — session
loader, CSRF, authorization — in their provisional relative order. T-010a
inserts rows 1-3 (`TrustedHostMiddleware`, request-ID + security headers,
CORS) **outermost of these three** and asserts the final exact
end-to-end sequence; nothing here should need to change for that, only
three more `add_middleware` calls placed after the ones below (Starlette
runs the *last*-added middleware outermost/first — see the ordering note
next to the calls).
"""

from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict

from app.middleware.authz import AuthzMiddleware
from app.middleware.csrf import CsrfMiddleware
from app.middleware.session_loader import SessionLoaderMiddleware
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

    # Starlette's `add_middleware` inserts each new middleware at the front
    # of its internal list, and that list order IS outermost-to-innermost
    # execution order — so registering **innermost first** here (authz,
    # then csrf, then session loader last) yields the desired execution
    # order session-loader -> csrf -> authz -> router (rows 4, 5, 6, 7).
    # T-010a's rows 1-3 must therefore be `add_middleware`d *after* these
    # three calls, so they end up outermost still.
    app.add_middleware(AuthzMiddleware)
    app.add_middleware(
        CsrfMiddleware,
        secret_key=settings.secret_key,
        allowed_origins=frozenset(settings.allowed_origins),
    )
    app.add_middleware(
        SessionLoaderMiddleware,
        cookie_secure=settings.environment != "dev",
    )

    @app.get("/healthz", response_model=HealthzResponse)
    def healthz() -> HealthzResponse:
        return HealthzResponse(status="ok")

    return app


app = create_app()
