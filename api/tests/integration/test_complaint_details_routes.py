"""Integration tests for `POST /api/complaints/{id}/details` (T-019,
api-contract.md #12, FR-012/014, BR-014, AC-008).

Same `live_server` + `live_seeded_accounts` approach as
`test_complaint_status_routes.py` (T-018) — every request logs in through
the real `/api/login` route and carries the session cookie + CSRF token
back by hand.
"""

from __future__ import annotations

import os
import uuid

import httpx
import pytest
from app.middleware.csrf import ANON_SEED_COOKIE, compute_anonymous_csrf_token
from sqlalchemy import text
from sqlalchemy.engine import Engine

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


def _logged_in_headers(client: httpx.Client, base_url: str, accounts: SeededAccounts) -> dict:
    login_response = _login(
        client, base_url, username=accounts.clerk_username, password=accounts.clerk_password
    )
    assert login_response.status_code == 200
    session_cookie_value = login_response.cookies.get(_SESSION_COOKIE)
    assert session_cookie_value is not None
    csrf_token = login_response.json()["csrf_token"]
    return {
        "Origin": _origin(),
        "X-CSRF-Token": csrf_token,
        "Cookie": f"{_SESSION_COOKIE}={session_cookie_value}",
    }


def _valid_body(**overrides: object) -> dict:
    body = {
        "client_request_id": str(uuid.uuid4()),
        "citizen_name": "Test Citizen",
        "citizen_phone": "+919876543210",
        "description": "Streetlight near the bus stop has been out for a week.",
    }
    body.update(overrides)
    return body


def _create_complaint(client: httpx.Client, base_url: str, headers: dict) -> dict:
    response = client.post(f"{base_url}/api/complaints", json=_valid_body(), headers=headers)
    assert response.status_code == 201
    return response.json()


def _backdate_created_at(engine: Engine, complaint_id: int, *, days: int) -> None:
    """Test-only fixture helper: push `created_at` (and `updated_at`, to
    keep the row internally consistent) `days` into the past so the 7-day
    edit window has already elapsed, without touching application code."""
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE complaint SET created_at = created_at - make_interval(days => :days), "
                "updated_at = updated_at - make_interval(days => :days) WHERE id = :id"
            ),
            {"days": days, "id": complaint_id},
        )


def _edit_history_rows(engine: Engine, complaint_id: int) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT field_name, previous_value, new_value, actor_id "
                "FROM complaint_edit_history WHERE complaint_id = :id ORDER BY id"
            ),
            {"id": complaint_id},
        ).mappings()
        return [dict(row) for row in rows]


# --- TC-API-060 ---------------------------------------------------------------


def test_edit_details_within_window_updates_value_and_records_history(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """TC-API-060: a complaint created less than 7 days ago accepts a
    corrected name — `200`, the value is stored, `created_at` is unchanged,
    and one `complaint_edit_history` row is written."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)

        response = client.post(
            f"{live_server}/api/complaints/{created['id']}/details",
            json={"citizen_name": "Corrected Name"},
            headers=headers,
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["citizen_name"] == "Corrected Name"
    assert body["created_at"] == created["created_at"]

    history = _edit_history_rows(db_engine, created["id"])
    assert len(history) == 1
    assert history[0]["field_name"] == "citizen_name"
    assert history[0]["previous_value"] == "Test Citizen"
    assert history[0]["new_value"] == "Corrected Name"


# --- TC-API-061 ---------------------------------------------------------------


def test_edit_details_after_window_expired_is_422_and_unchanged(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """TC-API-061: a complaint created more than 7 days ago (fixture
    backdates `created_at`) is `422 edit_window_expired` — no change applied,
    no history row, no override path exists."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)

        _backdate_created_at(db_engine, created["id"], days=8)

        response = client.post(
            f"{live_server}/api/complaints/{created['id']}/details",
            json={"citizen_name": "Should Not Apply"},
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "edit_window_expired"
    assert _edit_history_rows(db_engine, created["id"]) == []

    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        detail = client.get(f"{live_server}/api/complaints/{created['id']}", headers=headers)
    assert detail.json()["citizen_name"] == "Test Citizen"


# --- TC-API-062 ---------------------------------------------------------------


def test_edit_details_after_window_expired_direct_api_call_still_422(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """TC-API-062: a complaint over 7 days old is rejected identically when
    hit directly via the API — the server is the sole authority, regardless
    of what any UI shows."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)

        _backdate_created_at(db_engine, created["id"], days=30)

        response = client.post(
            f"{live_server}/api/complaints/{created['id']}/details",
            json={"description": "A brand new description, unrelated to the original."},
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "edit_window_expired"
    assert _edit_history_rows(db_engine, created["id"]) == []


# --- TC-API-063 ---------------------------------------------------------------


def test_edit_details_description_over_2000_chars_is_422_invalid_input(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """TC-API-063: within the edit window, a `description` over 2,000 chars
    is `422 invalid_input` — no change applied."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)

        response = client.post(
            f"{live_server}/api/complaints/{created['id']}/details",
            json={"description": "a" * 2001},
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert _edit_history_rows(db_engine, created["id"]) == []

    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        detail = client.get(f"{live_server}/api/complaints/{created['id']}", headers=headers)
    assert detail.json()["description"] == created["description"]
