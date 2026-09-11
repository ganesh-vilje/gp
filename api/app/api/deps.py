"""FastAPI dependencies (backend-architecture.md §1 module layout).

`current_user`/`require_admin_clerk` read `request.state.user` — populated
by `middleware/session_loader.py` (row 4) and already gated by
`middleware/authz.py` (row 6) for any non-public route by the time a route
handler runs. They stay defensive (raise rather than assume) so a route
wired without the middleware chain (e.g. a unit test) still fails closed.

Both raise the typed domain errors in `app.core.errors` — never a bare
FastAPI exception with a `detail=` kwarg (coding-guidelines.md § Error
handling); the single exception-handler set that converts them to the
envelope is added in a later task (T-008).
"""

from __future__ import annotations

from fastapi import Depends, Request

from app.core import strings
from app.core.errors import Forbidden, NotAuthenticated
from app.db.models.clerk_account import ClerkAccount
from app.db.session import get_session as get_session

__all__ = ["current_user", "require_admin_clerk", "get_session"]


def current_user(request: Request) -> ClerkAccount:
    """Return the authenticated `ClerkAccount` attached to
    `request.state.user`, or raise `NotAuthenticated` (401)."""
    user: ClerkAccount | None = getattr(request.state, "user", None)
    if user is None:
        raise NotAuthenticated(strings.get("errors.not_authenticated"))
    return user


def require_admin_clerk(
    user: ClerkAccount = Depends(current_user),  # noqa: B008 - standard FastAPI DI idiom
) -> ClerkAccount:
    """BR-013: only an admin clerk may pass; `Forbidden` (403) otherwise —
    a non-admin clerk is denied even with a perfectly valid session."""
    if not user.is_admin_clerk:
        raise Forbidden(strings.get("errors.forbidden"))
    return user
