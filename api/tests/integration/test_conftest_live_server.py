"""Scaffold integration tests for the `live_server` fixture (T-006a).

Proves the fixture itself works end to end: a real HTTP request reaches a
real `uvicorn.Server` running the real app, against the test database, and
the deny-by-default authz gate (`app/middleware/authz.py`) is live for a
route with no allow-list entry.
"""

from __future__ import annotations

import httpx
import pytest

pytestmark = pytest.mark.integration


def test_healthz_returns_200_via_live_server(live_server: str) -> None:
    response = httpx.get(f"{live_server}/healthz", timeout=5.0)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unauthenticated_get_to_a_non_allow_listed_route_returns_401_envelope(
    live_server: str,
) -> None:
    """`/api/anything` is not registered by any router (nor in
    `AuthzMiddleware.PUBLIC_ALLOW_LIST`) — the deny-by-default gate must
    reject it with the single error envelope before routing ever runs."""
    response = httpx.get(f"{live_server}/api/anything", timeout=5.0)

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "not_authenticated"
    assert "request_id" in body["error"]
