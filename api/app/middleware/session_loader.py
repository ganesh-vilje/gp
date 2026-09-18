"""Session loader — row 4 of the ADR-007 middleware chain (backend-
architecture.md §2/§3, security-architecture.md §1/§5).

Reads the session cookie, resolves it via `services.auth`, and attaches the
result to `request.state`:

- `request.state.user`: the `ClerkAccount`, or `None` for no cookie / an
  invalid, unknown, or revoked token. **Never raises** — an anonymous
  request is not an error at this layer (that is `middleware/authz.py`'s
  job, row 6).
- `request.state.csrf_token`: the resolved session row's own `csrf_token`
  (`services.auth.session_csrf_token`), or `None` when there is no active
  session — `middleware/csrf.py` (row 5) uses this for the session-bound
  verification path.

Cookie name: `__Host-session` when `cookie_secure` is true — the `__Host-`
prefix itself requires `Secure`, so it can never be sent over plain HTTP;
the bare `session` name is used in dev over http (backend-architecture.md
§3: "Dev over http uses the unprefixed name with COOKIE_SECURE=false").
T-006 derives `cookie_secure` from `settings.environment != "dev"` rather
than adding a dedicated `COOKIE_SECURE` setting — an interpretation left
for T-010a/selfcheck to revisit if a finer-grained flag is wanted.

A `Session` (app/db/session.py) is opened and closed strictly within this
middleware's own `dispatch` — never held across `call_next`/the response
(coding-guidelines.md § Security-sensitive modules).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import contextmanager

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.db.session import get_session
from app.services import auth as auth_service

COOKIE_NAME_SECURE = "__Host-session"
COOKIE_NAME_INSECURE = "session"

# `get_session` is a plain generator dependency (FastAPI drives it manually);
# wrapping it as a context manager here gets the same commit-on-success/
# rollback-on-exception/always-close behaviour without duplicating it.
_session_scope = contextmanager(get_session)


class SessionLoaderMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, *, cookie_secure: bool) -> None:
        super().__init__(app)
        self._cookie_name = COOKIE_NAME_SECURE if cookie_secure else COOKIE_NAME_INSECURE

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.user = None
        request.state.csrf_token = None

        raw_token = request.cookies.get(self._cookie_name)
        if raw_token:
            with _session_scope() as db_session:
                request.state.user = auth_service.resolve_session(db_session, raw_token)
                request.state.csrf_token = auth_service.session_csrf_token(db_session, raw_token)

        return await call_next(request)
