"""`GET /api/session` — two documented response variants (api-contract.md
§2, backend-architecture.md §4, R2-3/ARCH-F3/SEC-F9, T-010).

Never a business rule here (coding-guidelines.md § Layering): both
branches are pure HTTP/cookie shaping over state `middleware/
session_loader.py` (row 4) already resolved — `request.state.user`/
`request.state.csrf_token` — and the anonymous-CSRF-seed mechanics
`middleware/csrf.py` already exposes (`ANON_SEED_COOKIE`,
`compute_anonymous_csrf_token`). This route calls no service and touches
`app.db` for nothing.

**Zero-SQL guarantee (D-A step 2, TC-DB-003/TC-SEC-013):** this handler
declares no `Session` dependency and never imports `app.db`. When no
session cookie is presented, `session_loader.py` itself skips its DB read
(it only resolves a session when a cookie is actually present) — so a
cookie-less request to this route executes zero SQL statements end to end,
exactly as those test cases require. When a session cookie *is* presented,
the loader's own indexed lookup (already paid before this handler runs)
is the "same cost as any authenticated request" the contract describes;
this handler adds none of its own.

Cookie attributes mirror `app/api/routers/auth.py`'s `_set_anon_seed_cookie`
exactly (same duplication rationale as that module's docstring: the loader
only ever *reads* the seed cookie, so the "set it" logic belongs with the
routes that issue tokens).
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Request, Response

from app.api.schemas.session import (
    AnonymousSessionResponse,
    AuthenticatedSessionResponse,
    SessionUserDTO,
)
from app.db.models.clerk_account import ClerkAccount
from app.middleware.csrf import ANON_SEED_COOKIE, compute_anonymous_csrf_token
from app.settings import get_settings

router = APIRouter(prefix="/api")


def _set_anon_seed_cookie(response: Response, *, seed: str) -> None:
    # The __Host- prefix REQUIRES Secure on every environment, including dev
    # (localhost is treated as a secure context by browsers, but the Secure
    # attribute itself must still be present on the Set-Cookie header or the
    # browser silently drops the cookie entirely, breaking CSRF everywhere).
    response.set_cookie(
        ANON_SEED_COOKIE,
        seed,
        httponly=True,
        secure=True,
        samesite="lax",
        path="/",
    )


@router.get("/session", response_model=AnonymousSessionResponse | AuthenticatedSessionResponse)
def get_session_info(
    request: Request,
    response: Response,
) -> AnonymousSessionResponse | AuthenticatedSessionResponse:
    user: ClerkAccount | None = getattr(request.state, "user", None)
    session_csrf_token: str | None = getattr(request.state, "csrf_token", None)

    if user is not None and session_csrf_token is not None:
        return AuthenticatedSessionResponse(
            authenticated=True,
            csrf_token=session_csrf_token,
            user=SessionUserDTO(
                id=user.id,
                username=user.username,
                is_admin_clerk=user.is_admin_clerk,
                must_change_password=user.must_change_password,
            ),
        )

    settings = get_settings()
    seed = request.cookies.get(ANON_SEED_COOKIE)
    if not seed:
        seed = secrets.token_urlsafe(32)
        _set_anon_seed_cookie(response, seed=seed)

    csrf_token = compute_anonymous_csrf_token(settings.secret_key, seed)
    return AnonymousSessionResponse(authenticated=False, csrf_token=csrf_token)
