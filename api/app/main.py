"""ASGI application factory.

`create_app()`: settings -> selfcheck -> middleware (in order) -> routers
(backend-architecture.md §1). T-001 wired only settings and `/healthz`;
`selfcheck` still lands in a later task. T-006 registered rows 4-6 of the
ADR-007 middleware chain (backend-architecture.md §2) — session loader,
CSRF, authorization — in their provisional relative order. T-010a inserts
rows 1-3 (`TrustedHostMiddleware`, request-ID + security headers, CORS)
**outermost of these three** and asserts the final exact end-to-end
sequence; nothing here should need to change for that, only three more
`add_middleware` calls placed after the ones below (Starlette runs the
*last*-added middleware outermost/first — see the ordering note next to
the calls).

T-008 adds: the single exception-handler set (ADR-018 — `DomainError`,
`RequestValidationError`, and any unhandled `Exception`, converted by
`app/api/exception_handlers.py`) and the routers (`/healthz` moved out of
this module into `app/api/routers/health.py`; `POST /api/login` /
`POST /api/logout` in `app/api/routers/auth.py`).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.exception_handlers import (
    domain_error_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from app.api.routers.auth import router as auth_router
from app.api.routers.complaints import router as complaints_router
from app.api.routers.health import router as health_router
from app.api.routers.lookup import router as lookup_router
from app.api.routers.session import router as session_router
from app.core.errors import DomainError
from app.middleware.authz import AuthzMiddleware
from app.middleware.csrf import CsrfMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.session_loader import SessionLoaderMiddleware
from app.settings import get_settings


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

    # T-010a: rows 1-3 of the ADR-007 chain, registered outermost-first in
    # the same "innermost call registered first" pattern as above so that
    # the *execution* order (outermost -> innermost) ends up exactly
    # TrustedHostMiddleware -> request-ID/security-headers -> CORS ->
    # session-loader -> CSRF -> authorization -> router (backend-
    # architecture.md §2 rows 1-6). CORS must be registered before
    # SecurityHeadersMiddleware and TrustedHostMiddleware (so it ends up
    # innermost of the three) so that a CORS preflight response still gets
    # the security headers row adds; TrustedHostMiddleware is registered
    # last so it runs first of all six and can 400 an unrecognised `Host`
    # before anything else — including body-size handling — ever runs.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type", "x-csrf-token"],
        max_age=600,
    )
    app.add_middleware(SecurityHeadersMiddleware)
    # F3 (security review): `www_redirect` defaults to True, which can emit
    # an absolute `http://` downgrade redirect — contradicts backend-
    # architecture.md §2 row 0's "no redirect middleware exists, no absolute
    # URL is ever generated". Disabled explicitly; an unrecognised Host
    # simply gets 400, never a redirect.
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(settings.allowed_hosts),
        www_redirect=False,
    )

    # ADR-018: exactly one exception-handler set. Starlette's handler
    # lookup walks the raised exception's MRO, so registering `DomainError`
    # once covers every typed subclass in `app/core/errors.py` — never a
    # second, per-route error-handling scheme.
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(complaints_router)
    app.include_router(lookup_router)
    app.include_router(session_router)

    return app


app = create_app()
