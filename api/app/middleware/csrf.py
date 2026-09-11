"""CSRF protection — row 5 of the ADR-007 middleware chain (security-
architecture.md §4, backend-architecture.md §4).

Applies to every unsafe method (`GET`/`HEAD`/`OPTIONS` are safe; per
backend-architecture.md §2 row 3 the API only ever routes `GET`/`POST`, so
in practice this means every `POST`) on every route — **no exemption list**
(coding-guidelines.md: "There is no exemption decorator and no exempt-path
list anywhere in the package"), including the public-lookup `POST` (an
attacker must not be able to drive complaint-number guessing through
unwitting visitors' browsers).

Two layers, both required:

1. `Origin` header present and in the allow-list (missing or unlisted ->
   403) — `SameSite=Lax` is layer one but that is a browser-side cookie
   attribute, not something this middleware re-checks.
2. `X-CSRF-Token`, compared with `hmac.compare_digest`:
   - **session-bound** (an authenticated request — `request.state.user` is
     not `None`): compared against `request.state.csrf_token`, the current
     session row's own `csrf_token` (set by `session_loader.py`, row 4).
   - **anonymous stateless** (no session): recomputed as
     `base64url(hmac_sha256(SECRET_KEY, __Host-csrfseed))` from the
     `__Host-csrfseed` cookie — zero SQL, so an anonymous flood cannot grow
     a table or trip the fail-closed limiter (security-architecture.md §4).
     A request with no `__Host-csrfseed` cookie at all has no token to
     compare against and is rejected.
"""

from __future__ import annotations

import base64
import hmac
from collections.abc import Awaitable, Callable
from hashlib import sha256

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core import strings
from app.core.errors import Forbidden, to_envelope

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_CSRF_HEADER = "x-csrf-token"
ANON_SEED_COOKIE = "__Host-csrfseed"


def compute_anonymous_csrf_token(secret_key: str, seed: str) -> str:
    """`base64url(hmac_sha256(SECRET_KEY, seed))` (backend-architecture.md
    §4) — unpadded, matching the `X-CSRF-Token` header format a client
    would send back verbatim."""
    digest = hmac.new(secret_key.encode("utf-8"), seed.encode("utf-8"), sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _request_id_of(request: Request) -> str:
    # T-010a wires request-ID middleware (row 2); until then this falls
    # back to a fixed placeholder rather than raising.
    return str(getattr(request.state, "request_id", "unknown"))


def _forbidden(request: Request) -> Response:
    error = Forbidden(strings.get("errors.forbidden"))
    return JSONResponse(
        status_code=403, content=to_envelope(error, request_id=_request_id_of(request))
    )


class CsrfMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, secret_key: str, allowed_origins: frozenset[str]) -> None:
        super().__init__(app)
        self._secret_key = secret_key
        self._allowed_origins = allowed_origins

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        origin = request.headers.get("origin")
        if origin is None or origin not in self._allowed_origins:
            return _forbidden(request)

        presented = request.headers.get(_CSRF_HEADER)
        if not presented:
            return _forbidden(request)

        session_bound_token = getattr(request.state, "csrf_token", None)
        if session_bound_token is not None:
            if not hmac.compare_digest(presented, session_bound_token):
                return _forbidden(request)
        else:
            seed = request.cookies.get(ANON_SEED_COOKIE)
            if not seed:
                return _forbidden(request)
            expected = compute_anonymous_csrf_token(self._secret_key, seed)
            if not hmac.compare_digest(presented, expected):
                return _forbidden(request)

        return await call_next(request)
