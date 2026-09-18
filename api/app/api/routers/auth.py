"""`POST /api/login` / `POST /api/logout` (api-contract.md §3/§5, T-008).

Never a business rule here (coding-guidelines.md § Layering) — every rule
(credential check, session issuance/revocation, the generic-failure
constant-time behaviour) lives in `app.services.auth`; this module only
validates the request DTO, calls the service, and shapes the HTTP
response (cookie attributes, status code, response DTO).

Cookie attributes mirror `app/middleware/session_loader.py` exactly (same
name-by-environment rule, backend-architecture.md §3) — duplicated here
rather than imported as a single "set the session cookie" helper in that
module, because the session loader only ever *reads* the cookie; the
constants (`COOKIE_NAME_SECURE`/`COOKIE_NAME_INSECURE`) are imported so
the name itself can never drift between the two modules.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session
from app.api.schemas.auth import LoginRequest, LoginResponse, LogoutResponse, UserDTO
from app.core.errors import DependencyUnavailable
from app.db.models.clerk_account import ClerkAccount
from app.middleware.csrf import ANON_SEED_COOKIE, compute_anonymous_csrf_token
from app.middleware.session_loader import COOKIE_NAME_INSECURE, COOKIE_NAME_SECURE
from app.services import auth as auth_service
from app.settings import get_settings

router = APIRouter(prefix="/api")


def _session_cookie_name(environment: str) -> str:
    """Same rule as `middleware/session_loader.py`: `__Host-` prefixed
    (requires `Secure`) everywhere except `dev`, which uses the bare name
    over plain http (backend-architecture.md §3)."""
    return COOKIE_NAME_INSECURE if environment == "dev" else COOKIE_NAME_SECURE


def _set_session_cookie(response: Response, *, raw_token: str, environment: str) -> None:
    response.set_cookie(
        _session_cookie_name(environment),
        raw_token,
        httponly=True,
        secure=environment != "dev",
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response, *, environment: str) -> None:
    response.delete_cookie(
        _session_cookie_name(environment),
        path="/",
        secure=environment != "dev",
        httponly=True,
        samesite="lax",
    )


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


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: Session = Depends(get_session),  # noqa: B008 - standard FastAPI DI idiom
) -> LoginResponse:
    settings = get_settings()

    presented_raw_token = request.cookies.get(_session_cookie_name(settings.environment))

    user, raw_token = auth_service.login(
        session,
        body.username,
        body.password,
        presented_raw_token=presented_raw_token,
    )

    csrf_token = auth_service.session_csrf_token(session, raw_token)
    if csrf_token is None:  # pragma: no cover - defensive, should be unreachable
        # The row was just created, in this same session, by the call
        # above — a `None` here would mean it vanished mid-request.
        raise DependencyUnavailable("Could not read back the session just created.")

    _set_session_cookie(response, raw_token=raw_token, environment=settings.environment)

    return LoginResponse(
        user=UserDTO(
            id=user.id,
            username=user.username,
            is_admin_clerk=user.is_admin_clerk,
            must_change_password=user.must_change_password,
        ),
        csrf_token=csrf_token,
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    session: Session = Depends(get_session),  # noqa: B008 - standard FastAPI DI idiom
    _user: ClerkAccount = Depends(current_user),  # noqa: B008 - 401 if unreachable via middleware
) -> LogoutResponse:
    settings = get_settings()

    raw_token = request.cookies.get(_session_cookie_name(settings.environment))
    if raw_token:
        auth_service.logout(session, raw_token)

    _clear_session_cookie(response, environment=settings.environment)

    # ARCH-T33: the session is gone, so a session-bound token cannot exist;
    # return a fresh anonymous token instead, exactly like the anonymous
    # `GET /api/session` variant (backend-architecture.md §4), so the
    # now-anonymous client can immediately POST /api/lookup or /api/login
    # without a second round trip.
    seed = request.cookies.get(ANON_SEED_COOKIE)
    if not seed:
        seed = secrets.token_urlsafe(32)
        _set_anon_seed_cookie(response, seed=seed)

    csrf_token = compute_anonymous_csrf_token(settings.secret_key, seed)

    return LogoutResponse(csrf_token=csrf_token)
