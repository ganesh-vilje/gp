"""Integration tests for `GET /api/session` (T-010, api-contract.md §2).

`live_server` is used throughout: the zero-SQL claim (TC-DB-003/TC-SEC-013)
is about the real middleware chain + route wiring, not a bare ASGI call.
"""

from __future__ import annotations

import os

import httpx
import pytest
from app.middleware.csrf import ANON_SEED_COOKIE, compute_anonymous_csrf_token

from tests.conftest import SeededAccounts

pytestmark = pytest.mark.integration

_SESSION_COOKIE = "__Host-session"


def _origin() -> str:
    return os.environ["ALLOWED_ORIGINS"].split(",")[0].strip()


def _secret_key() -> str:
    return os.environ["SECRET_KEY"]


def _login(client: httpx.Client, base_url: str, *, username: str, password: str) -> httpx.Response:
    import secrets

    seed = secrets.token_urlsafe(16)
    token = compute_anonymous_csrf_token(_secret_key(), seed)
    return client.post(
        f"{base_url}/api/login",
        json={"username": username, "password": password},
        headers={
            "Origin": _origin(),
            "X-CSRF-Token": token,
            "Cookie": f"{ANON_SEED_COOKIE}={seed}",
        },
    )


# --- TC-DB-003 / TC-SEC-013 ---------------------------------------------------


def test_anonymous_session_is_zero_sql(live_server: str, query_counter) -> None:
    """TC-DB-003/TC-SEC-013: no session cookie presented -> 200
    `authenticated: false`; literally zero SQL statements of any kind."""
    with httpx.Client() as client:
        response = client.get(f"{live_server}/api/session")

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is False
    assert "csrf_token" in body
    assert query_counter.statements == []


def test_anonymous_session_sets_csrfseed_cookie_when_absent(live_server: str) -> None:
    with httpx.Client() as client:
        response = client.get(f"{live_server}/api/session")

    assert response.status_code == 200
    assert ANON_SEED_COOKIE in response.cookies


# --- Authenticated variant (api-contract.md §2) -------------------------------


def test_authenticated_session_returns_user_and_csrf_token(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
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

        response = client.get(
            f"{live_server}/api/session",
            headers={"Cookie": f"{_SESSION_COOKIE}={session_cookie_value}"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["username"] == live_seeded_accounts.clerk_username
    assert body["user"]["is_admin_clerk"] is False
    assert body["user"]["must_change_password"] is False
    assert "csrf_token" in body
