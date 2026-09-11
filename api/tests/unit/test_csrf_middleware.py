"""Behavioural coverage for `CsrfMiddleware.dispatch` (F1, T-006 review
fix) — `tests/unit/test_csrf.py` only covers the pure
`compute_anonymous_csrf_token` helper; this exercises every branch of the
middleware itself over HTTP via `TestClient`, using a fake state-setting
middleware in place of `session_loader.py` so no database is touched.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.db.models.clerk_account import ClerkAccount
from app.middleware.csrf import ANON_SEED_COOKIE, CsrfMiddleware, compute_anonymous_csrf_token
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.testclient import TestClient

_HMAC_KEY = "s" * 32
_ALLOWED_ORIGIN = "https://app.example.in"
# The session row's own csrf_token value (security-architecture.md §4) —
# an opaque value the fixture below hands to the fake state middleware.
_VALID_SESSION_CSRF_VALUE = "sess-csrf-abc123"
_WRONG_CSRF_VALUE = "nope"


class _FakeStateMiddleware(BaseHTTPMiddleware):
    """Test-only stand-in for `middleware/session_loader.py`: sets
    `request.state.user`/`csrf_token` directly, with no database."""

    def __init__(
        self,
        app,  # type: ignore[no-untyped-def]
        *,
        user: ClerkAccount | None,
        csrf_token: str | None,
    ) -> None:
        super().__init__(app)
        self._user = user
        self._csrf_token = csrf_token

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request.state.user = self._user
        request.state.csrf_token = self._csrf_token
        return await call_next(request)


def _build_app(*, user: ClerkAccount | None = None, csrf_token: str | None = None) -> FastAPI:
    app = FastAPI()

    @app.get("/api/__test_only")
    def _get() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/__test_only")
    def _post() -> dict[str, bool]:
        return {"ok": True}

    # Registration order matters (main.py's ordering comment applies here
    # too): the *last*-added middleware is outermost, so the fake state
    # setter must be added after CsrfMiddleware to run before it.
    app.add_middleware(
        CsrfMiddleware, secret_key=_HMAC_KEY, allowed_origins=frozenset({_ALLOWED_ORIGIN})
    )
    app.add_middleware(_FakeStateMiddleware, user=user, csrf_token=csrf_token)
    return app


def _authenticated_app() -> FastAPI:
    user = ClerkAccount(username="clerk_test", password_hash="x", is_admin_clerk=False)
    return _build_app(user=user, csrf_token=_VALID_SESSION_CSRF_VALUE)


def _anonymous_app() -> FastAPI:
    return _build_app(user=None, csrf_token=None)


def _assert_forbidden_envelope(response) -> None:  # type: ignore[no-untyped-def]
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "forbidden"
    assert "request_id" in body["error"]


def test_missing_origin_on_unsafe_method_is_403() -> None:
    client = TestClient(_authenticated_app())

    response = client.post("/api/__test_only", headers={"x-csrf-token": _VALID_SESSION_CSRF_VALUE})

    _assert_forbidden_envelope(response)


def test_origin_not_in_allow_list_is_403() -> None:
    client = TestClient(_authenticated_app())

    response = client.post(
        "/api/__test_only",
        headers={"origin": "https://evil.example", "x-csrf-token": _VALID_SESSION_CSRF_VALUE},
    )

    _assert_forbidden_envelope(response)


def test_missing_csrf_token_header_is_403() -> None:
    client = TestClient(_authenticated_app())

    response = client.post("/api/__test_only", headers={"origin": _ALLOWED_ORIGIN})

    _assert_forbidden_envelope(response)


def test_wrong_session_bound_token_with_valid_session_cookie_is_403() -> None:
    client = TestClient(_authenticated_app())

    response = client.post(
        "/api/__test_only",
        headers={"origin": _ALLOWED_ORIGIN, "x-csrf-token": _WRONG_CSRF_VALUE},
    )

    _assert_forbidden_envelope(response)


def test_correct_session_bound_token_is_200() -> None:
    client = TestClient(_authenticated_app())

    response = client.post(
        "/api/__test_only",
        headers={"origin": _ALLOWED_ORIGIN, "x-csrf-token": _VALID_SESSION_CSRF_VALUE},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_anonymous_wrong_token_with_seed_cookie_is_403() -> None:
    client = TestClient(_anonymous_app())
    client.cookies.set(ANON_SEED_COOKIE, "some-seed-value")

    response = client.post(
        "/api/__test_only",
        headers={"origin": _ALLOWED_ORIGIN, "x-csrf-token": _WRONG_CSRF_VALUE},
    )

    _assert_forbidden_envelope(response)


def test_anonymous_missing_seed_cookie_is_403() -> None:
    client = TestClient(_anonymous_app())

    response = client.post(
        "/api/__test_only",
        headers={"origin": _ALLOWED_ORIGIN, "x-csrf-token": _WRONG_CSRF_VALUE},
    )

    _assert_forbidden_envelope(response)


def test_correct_anonymous_token_is_200() -> None:
    client = TestClient(_anonymous_app())
    seed = "some-seed-value"
    client.cookies.set(ANON_SEED_COOKIE, seed)
    expected = compute_anonymous_csrf_token(_HMAC_KEY, seed)

    response = client.post(
        "/api/__test_only", headers={"origin": _ALLOWED_ORIGIN, "x-csrf-token": expected}
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_head_is_exempt_from_csrf() -> None:
    """`HEAD` with no Origin/token is never rejected *by CSRF*; whatever
    the router does with it (this app registers no explicit `HEAD`
    handler) is not this middleware's 403."""
    client = TestClient(_anonymous_app())

    response = client.head("/api/__test_only")

    assert response.status_code != 403


def test_options_is_exempt_from_csrf() -> None:
    """An OPTIONS request with no Origin/token is never rejected *by
    CSRF* — whatever the router does with it (405 here, no OPTIONS
    handler is registered) is not this middleware's 403."""
    client = TestClient(_anonymous_app())

    response = client.options("/api/__test_only")

    assert response.status_code != 403
