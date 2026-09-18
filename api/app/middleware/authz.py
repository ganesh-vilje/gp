"""Deny-by-default authorization — row 6 of the ADR-007 middleware chain
(security-architecture.md §2, D-A).

Every route not in the 4-entry `PUBLIC_ALLOW_LIST` requires
`request.state.user` (attached by `session_loader.py`, row 4) to be set;
anything else is `401 not_authenticated`. Role checks
(`require_admin_clerk`, BR-013) and the `must_change_password` gate live
deeper — at the router/dependency layer (row 7, `app/api/deps.py`) and a
later task respectively; this task's scope is authentication only ("no
OTP/expiry edge cases yet").

`is_public` matches `(method, path)` **exactly** — no prefix/glob/regex —
so a route added later is closed unless someone edits this table
(security-architecture.md §2: "a route-table-parametrised test proves it").

**Interpretation (T-006):** FastAPI's own `/docs`, `/redoc` and
`/openapi.json` are framework tooling, not one of the "four entries" this
allow-list fixes (security-architecture.md §2/§5: "OpenAPI docs return 404
in production... this is hygiene, not an anti-enumeration control...
Authorization is the control" — i.e. the actual protection is on the data
routes, not on whether the schema page itself loads). They are already
gated by `docs_enabled`/`Settings.environment` (T-001, `app/main.py`) and
are exempted from the *authentication* gate here so that gate continues to
mean exactly what T-001 already tests: reachable outside prod, 404 in
prod — never `401`.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core import strings
from app.core.errors import NotAuthenticated, to_envelope

PUBLIC_ALLOW_LIST: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/lookup"),
        ("POST", "/api/login"),
        ("GET", "/api/session"),
        ("GET", "/healthz"),
    }
)


# FastAPI's own docs/schema routes — see the module docstring's
# "Interpretation (T-006)" note. Not part of `PUBLIC_ALLOW_LIST` itself:
# that set stays exactly the 4 entries security-architecture.md §2 fixes.
_DOCS_PATHS = frozenset({"/docs", "/redoc", "/openapi.json"})


def is_public(method: str, path: str) -> bool:
    """Deny-by-default allow-list decision (security-architecture.md §2)."""
    return (method.upper(), path) in PUBLIC_ALLOW_LIST


def is_docs_route(path: str) -> bool:
    """`True` for FastAPI's own docs/schema paths (see module docstring)."""
    return path in _DOCS_PATHS


def _request_id_of(request: Request) -> str:
    # T-010a wires request-ID middleware (row 2); until then this falls
    # back to a fixed placeholder rather than raising.
    return str(getattr(request.state, "request_id", "unknown"))


class AuthzMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if is_public(request.method, request.url.path) or is_docs_route(request.url.path):
            return await call_next(request)

        if getattr(request.state, "user", None) is None:
            error = NotAuthenticated(strings.get("errors.not_authenticated"))
            return JSONResponse(
                status_code=401, content=to_envelope(error, request_id=_request_id_of(request))
            )

        return await call_next(request)
