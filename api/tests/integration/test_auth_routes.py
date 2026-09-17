"""Integration tests for `POST /api/login` / `POST /api/logout` (T-008).

Approach: `live_server` (a real `uvicorn.Server`) + `live_seeded_accounts`
(`clerk_test`, committed for real) over real HTTP via `httpx.Client` —
chosen over a bare `TestClient(create_app())` because CSRF/session-cookie
behaviour (the exact thing this task's done-condition cares about) is a
real-server, real-cookie concern (backend-architecture.md §3/§4), and the
`live_server`/`live_seeded_accounts`/`truncate_tables` fixture trio is
exactly what `tests/conftest.py` (T-006a) built for this.

**Cookies are passed by hand, never via the client's automatic cookie
jar.** Every session/seed cookie this app sets carries `Secure` (the
`__Host-` prefix requires it) once `ENVIRONMENT != "dev"` — `live_server`
defaults to `ENVIRONMENT=test` — and `httpx`'s cookie jar (like every
RFC 6265 jar) never re-sends a `Secure` cookie over a plain-`http://`
connection, which is exactly what `live_server` is. Verified directly
against a throwaway real server before writing this file. Extracting the
`Set-Cookie` value and sending it back as an explicit `Cookie:` header
sidesteps the jar entirely and is the only way to integration-test a
`Secure` cookie over `live_server`'s plain-http socket — a gap in the test
setup, not a product bug (real browsers only ever see this app over
`https://`).

**No real-looking credential is ever a literal in this file** — every
password value used here is a short, obviously-synthetic placeholder
bound to a module constant (never a literal in the call itself), per
`CLAUDE.md`'s "no secrets in any file" and the repo's secret-guard hook.
"""

from __future__ import annotations

import os
import secrets

import httpx
import pytest
from app.middleware.authz import PUBLIC_ALLOW_LIST
from app.middleware.csrf import ANON_SEED_COOKIE, CsrfMiddleware, compute_anonymous_csrf_token
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import SeededAccounts

pytestmark = pytest.mark.integration

_SESSION_COOKIE = "__Host-session"

# Short, obviously-synthetic placeholders — never a real credential, never
# the seeded accounts' own (real, working) passwords.
_WRONG_PASSWORD = "nope1"
_ANOTHER_WRONG_PASSWORD = "nope2"


def _secret_key() -> str:
    return os.environ["SECRET_KEY"]


def _origin() -> str:
    return os.environ["ALLOWED_ORIGINS"].split(",")[0].strip()


def _anon_csrf(secret_key: str) -> tuple[str, str]:
    """A synthetic `(seed, token)` pair for the anonymous CSRF path
    (backend-architecture.md §4) — stands in for the seed/token a real
    browser would have gotten from `GET /api/session` (T-010, not built
    yet)."""
    seed = secrets.token_urlsafe(16)
    return seed, compute_anonymous_csrf_token(secret_key, seed)


def _login(
    client: httpx.Client,
    base_url: str,
    *,
    username: str,
    password: str,
) -> httpx.Response:
    seed, token = _anon_csrf(_secret_key())
    return client.post(
        f"{base_url}/api/login",
        json={"username": username, "password": password},
        headers={
            "Origin": _origin(),
            "X-CSRF-Token": token,
            "Cookie": f"{ANON_SEED_COOKIE}={seed}",
        },
    )


def _set_cookie_values(response: httpx.Response, name: str) -> list[str]:
    """Every `Set-Cookie` header value whose cookie name is `name` (there
    can be more than one `Set-Cookie` header on a response)."""
    return [
        value
        for key, value in response.headers.multi_items()
        if key.lower() == "set-cookie" and value.startswith(f"{name}=")
    ]


# --- TC-API-001/002/003 ------------------------------------------------


def test_login_success_sets_session_cookie_and_returns_csrf_token(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-API-001."""
    with httpx.Client() as client:
        response = _login(
            client,
            live_server,
            username=live_seeded_accounts.clerk_username,
            password=live_seeded_accounts.clerk_password,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["user"] == {
        "id": live_seeded_accounts.clerk.id,
        "username": live_seeded_accounts.clerk_username,
        "is_admin_clerk": False,
        "must_change_password": False,
    }
    assert isinstance(body["csrf_token"], str) and body["csrf_token"]

    session_cookies = _set_cookie_values(response, _SESSION_COOKIE)
    assert len(session_cookies) == 1
    cookie_attrs = session_cookies[0]
    assert "HttpOnly" in cookie_attrs
    assert "Secure" in cookie_attrs
    assert "SameSite=lax" in cookie_attrs
    assert "Path=/" in cookie_attrs
    assert "Max-Age" not in cookie_attrs  # backend-architecture.md §3: browser-close expiry


def test_login_wrong_password_returns_generic_401(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-API-002."""
    with httpx.Client() as client:
        response = _login(
            client,
            live_server,
            username=live_seeded_accounts.clerk_username,
            password=_WRONG_PASSWORD,
        )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "not_authenticated"
    assert "request_id" in body["error"]
    assert not _set_cookie_values(response, _SESSION_COOKIE)


def test_login_unknown_username_is_byte_identical_to_wrong_password(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-API-003."""
    with httpx.Client() as client:
        wrong_password_response = _login(
            client,
            live_server,
            username=live_seeded_accounts.clerk_username,
            password=_WRONG_PASSWORD,
        )
        unknown_username_response = _login(
            client,
            live_server,
            username="no-such-clerk-account-exists",
            password=_ANOTHER_WRONG_PASSWORD,
        )

    assert wrong_password_response.status_code == unknown_username_response.status_code == 401
    # T-010a wires the real request-ID middleware, which mints a fresh
    # `X-Request-ID` per request — so `request_id` is the one field these
    # two bodies are expected to differ on; mask it out before asserting
    # everything else is byte-identical (never leak "which case" from body
    # shape/length either, so compare the same masked structure both ways).
    wrong_password_body = wrong_password_response.json()
    unknown_username_body = unknown_username_response.json()
    del wrong_password_body["error"]["request_id"]
    del unknown_username_body["error"]["request_id"]
    assert wrong_password_body == unknown_username_body


# --- TC-SEC-001 ----------------------------------------------------------


def test_repeated_wrong_password_then_correct_login_succeeds_no_lockout(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-SEC-001. Exactly 3 wrong attempts then 1 correct (<=4 total per
    this task's note — the login-attempt limiter is T-026, not built yet;
    this test must stay valid after it lands)."""
    with httpx.Client() as client:
        for _ in range(3):
            failure = _login(
                client,
                live_server,
                username=live_seeded_accounts.clerk_username,
                password=_WRONG_PASSWORD,
            )
            assert failure.status_code == 401
            assert failure.json()["error"]["code"] == "not_authenticated"

        success = _login(
            client,
            live_server,
            username=live_seeded_accounts.clerk_username,
            password=live_seeded_accounts.clerk_password,
        )

    assert success.status_code == 200
    assert success.json()["user"]["username"] == live_seeded_accounts.clerk_username


# --- Malformed body -------------------------------------------------------


def test_login_malformed_body_returns_422_with_fields(live_server: str) -> None:
    seed, token = _anon_csrf(_secret_key())

    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/login",
            json={"username": ""},
            headers={
                "Origin": _origin(),
                "X-CSRF-Token": token,
                "Cookie": f"{ANON_SEED_COOKIE}={seed}",
            },
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_input"
    assert body["error"]["fields"]["username"] == "too_short"
    assert body["error"]["fields"]["password"] == "required"
    assert "request_id" in body["error"]


# --- Logout ----------------------------------------------------------------


def test_logout_revokes_session_clears_cookie_and_returns_anon_token_that_verifies(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """Logout revokes the session, clears the cookie, and the returned
    `csrf_token` is a real anonymous token — proven two ways: (1) it
    equals an independent recomputation of the anonymous HMAC, and (2) it
    is actually accepted by a live `CsrfMiddleware` instance on a fresh
    "fake anonymous-allowed route" app wired with the same secret key
    (ARCH-T33)."""
    secret_key = _secret_key()

    with httpx.Client() as client:
        login_response = _login(
            client,
            live_server,
            username=live_seeded_accounts.clerk_username,
            password=live_seeded_accounts.clerk_password,
        )
        assert login_response.status_code == 200
        session_cookie_value = login_response.cookies.get(_SESSION_COOKIE)
        assert session_cookie_value is not None
        session_csrf_token = login_response.json()["csrf_token"]

        seed = secrets.token_urlsafe(16)  # the seed the now-anonymous client already holds

        logout_response = client.post(
            f"{live_server}/api/logout",
            headers={
                "Origin": _origin(),
                "X-CSRF-Token": session_csrf_token,
                "Cookie": f"{_SESSION_COOKIE}={session_cookie_value}; {ANON_SEED_COOKIE}={seed}",
            },
        )

    assert logout_response.status_code == 200
    anon_token = logout_response.json()["csrf_token"]

    # The session cookie is cleared (Max-Age=0 in the deletion Set-Cookie).
    cleared = _set_cookie_values(logout_response, _SESSION_COOKIE)
    assert len(cleared) == 1
    assert "Max-Age=0" in cleared[0]

    # The seed cookie was already present in the request, so it must not be
    # re-set (backend-architecture.md §4: "sets __Host-csrfseed if absent").
    assert not _set_cookie_values(logout_response, ANON_SEED_COOKIE)

    # (1) Independent recomputation.
    assert anon_token == compute_anonymous_csrf_token(secret_key, seed)

    # (2) A real CsrfMiddleware, wired with the same secret key, accepts it
    # on a fake anonymous-allowed route — never a 403.
    probe_app = FastAPI()
    probe_path = "/api/_t008_fake_anon_probe"
    probe_app.add_middleware(
        CsrfMiddleware, secret_key=secret_key, allowed_origins=frozenset({_origin()})
    )

    @probe_app.post(probe_path)
    def _probe() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(probe_app, base_url=_origin()) as probe_client:
        probe_response = probe_client.post(
            probe_path,
            headers={
                "Origin": _origin(),
                "X-CSRF-Token": anon_token,
                "Cookie": f"{ANON_SEED_COOKIE}={seed}",
            },
        )

    assert probe_response.status_code == 200
    assert probe_response.json() == {"ok": True}


def test_logout_without_session_returns_401_envelope(live_server: str) -> None:
    seed, token = _anon_csrf(_secret_key())

    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/logout",
            headers={
                "Origin": _origin(),
                "X-CSRF-Token": token,
                "Cookie": f"{ANON_SEED_COOKIE}={seed}",
            },
        )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "not_authenticated"


def test_logout_missing_csrf_token_is_forbidden_not_not_authenticated(live_server: str) -> None:
    """Sanity check the 401-vs-403 split (api-contract.md § Conventions
    "Authorization failure rule"): a failed CSRF check is `403 forbidden`,
    never conflated with the no-session `401`."""
    with httpx.Client() as client:
        response = client.post(f"{live_server}/api/logout", headers={"Origin": _origin()})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


# --- Unknown-route shape untouched ------------------------------------------


def test_unknown_route_error_shape_is_untouched(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """A path with no registered route, hit by an authenticated caller
    (so it clears the authz allow-list gate and actually reaches
    Starlette's own routing 404), must still get the framework's default
    `{"detail": ...}` shape — never the ADR-018 envelope. Proves the
    exception-handler registration did not touch Starlette's own 404."""
    with httpx.Client() as client:
        login_response = _login(
            client,
            live_server,
            username=live_seeded_accounts.clerk_username,
            password=live_seeded_accounts.clerk_password,
        )
        session_cookie_value = login_response.cookies.get(_SESSION_COOKIE)

        response = client.get(
            f"{live_server}/api/this-route-does-not-exist",
            headers={"Cookie": f"{_SESSION_COOKIE}={session_cookie_value}"},
        )

    assert response.status_code == 404
    body = response.json()
    assert "error" not in body
    assert "detail" in body


def test_public_allow_list_has_not_grown_beyond_the_four_documented_entries() -> None:
    """api-contract.md § Endpoint inventory: "The public allow-list is
    exactly the first four rows" — `POST /api/logout` must not be one of
    them (security-architecture.md §2)."""
    assert ("POST", "/api/logout") not in PUBLIC_ALLOW_LIST
    assert PUBLIC_ALLOW_LIST == frozenset(
        {
            ("POST", "/api/lookup"),
            ("POST", "/api/login"),
            ("GET", "/api/session"),
            ("GET", "/healthz"),
        }
    )
