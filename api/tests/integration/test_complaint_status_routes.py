"""Integration tests for `POST /api/complaints/{id}/status` and
`GET /api/complaints/{id}` (T-018, api-contract.md #9/#11, BR-002/BR-011,
ADR-017).

Same `live_server` + `live_seeded_accounts` approach as
`test_complaints_routes.py` (T-009) — every request logs in through the real
`/api/login` route and carries the session cookie + CSRF token back by hand.
"""

from __future__ import annotations

import concurrent.futures
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


def _status_history_rows(engine: Engine, complaint_id: int) -> list[dict]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT previous_status, new_status, note, actor_id "
                "FROM complaint_status_history WHERE complaint_id = :id ORDER BY id"
            ),
            {"id": complaint_id},
        ).mappings()
        return [dict(row) for row in rows]


# --- TC-API-030 ---------------------------------------------------------------


def test_status_update_new_to_in_progress_returns_200_and_records_history(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """TC-API-030: `POST` status `new -> in_progress` with a note is `200`,
    the status is updated, the note is stored, and a history row is
    written."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)

        response = client.post(
            f"{live_server}/api/complaints/{created['id']}/status",
            json={"new_status": "in_progress", "note": "site visit scheduled"},
            headers=headers,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["legal_next_statuses"] == ["resolved", "rejected"]

    history = _status_history_rows(db_engine, created["id"])
    assert len(history) == 1
    assert history[0]["previous_status"] == "new"
    assert history[0]["new_status"] == "in_progress"
    assert history[0]["note"] == "site visit scheduled"


# --- TC-API-031 ---------------------------------------------------------------


def test_status_update_new_to_closed_directly_is_422_and_unchanged(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """TC-API-031: `new -> closed` directly (skipping `in_progress`) is
    `422 illegal_transition`; the complaint's status is unchanged and no
    history row is written."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)

        response = client.post(
            f"{live_server}/api/complaints/{created['id']}/status",
            json={"new_status": "closed", "note": None},
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "illegal_transition"
    assert _status_history_rows(db_engine, created["id"]) == []

    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        detail = client.get(f"{live_server}/api/complaints/{created['id']}", headers=headers)
    assert detail.json()["status"] == "new"


# --- TC-API-032 ---------------------------------------------------------------


def test_get_complaint_detail_shows_new_status_and_note_immediately(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-API-032: after a status change, `GET` the complaint detail shows
    the new status immediately."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)

        update = client.post(
            f"{live_server}/api/complaints/{created['id']}/status",
            json={"new_status": "in_progress", "note": "checked"},
            headers=headers,
        )
        assert update.status_code == 200

        detail = client.get(f"{live_server}/api/complaints/{created['id']}", headers=headers)

    assert detail.status_code == 200
    body = detail.json()
    assert body["status"] == "in_progress"
    assert body["legal_next_statuses"] == ["resolved", "rejected"]


# --- TC-API-033 ---------------------------------------------------------------


def test_status_update_note_over_2000_chars_is_422_invalid_input(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """TC-API-033: a status-change note over 2,000 chars is `422
    invalid_input`."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)

        response = client.post(
            f"{live_server}/api/complaints/{created['id']}/status",
            json={"new_status": "in_progress", "note": "a" * 2001},
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert _status_history_rows(db_engine, created["id"]) == []


# --- F4 (security-review, T-018 rework) --------------------------------------


def test_status_update_note_with_nul_byte_is_422_not_500(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """F4: a NUL byte in `note` is `422 invalid_input` (the schema-level
    control-character rejection `CreateComplaintRequest.description` already
    uses), never an uncatalogued `500` from psycopg raising on a NUL byte at
    flush time into the immutable `complaint_status_history` table."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)

        response = client.post(
            f"{live_server}/api/complaints/{created['id']}/status",
            json={"new_status": "in_progress", "note": "bad\x00note"},
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert _status_history_rows(db_engine, created["id"]) == []


# --- TC-API-034 ---------------------------------------------------------------


def test_status_update_without_session_is_401_and_unchanged(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """TC-API-034: a status-change POST directly with no session is `401
    not_authenticated`; the complaint is unchanged."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)

    anon_seed = "tc-api-034-anon-seed"
    anon_token = compute_anonymous_csrf_token(_secret_key(), anon_seed)
    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/complaints/{created['id']}/status",
            json={"new_status": "in_progress", "note": None},
            headers={
                "Origin": _origin(),
                "X-CSRF-Token": anon_token,
                "Cookie": f"{ANON_SEED_COOKIE}={anon_seed}",
            },
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
    assert _status_history_rows(db_engine, created["id"]) == []


# --- TC-API-072 ---------------------------------------------------------------


def test_get_complaint_detail_includes_full_citizen_name_and_phone(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-API-072: `GET /api/complaints/{id}` as a clerk returns the full
    `citizen_name`/`citizen_phone`, unlike the public lookup DTO."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        body = _valid_body(citizen_name="Ravi Kumar", citizen_phone="+919876500000")
        created = client.post(f"{live_server}/api/complaints", json=body, headers=headers).json()

        response = client.get(f"{live_server}/api/complaints/{created['id']}", headers=headers)

    assert response.status_code == 200
    detail = response.json()
    assert detail["citizen_name"] == "Ravi Kumar"
    assert detail["citizen_phone"] == "+919876500000"


# --- TC-API-100 ----------------------------------------------------------------


def test_concurrent_status_updates_last_write_wins_but_both_history_rows_persist(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """TC-API-100/BR-011/ADR-017: two clerks update the same complaint
    (`in_progress`) concurrently — Clerk A to `resolved`/"fixed same day",
    Clerk B (stale load, no reload) to `rejected`/"duplicate". The final
    current status is whichever write commits last (serialised by the row
    lock — never a lost update or a corrupted intermediate state), and
    **both** history rows persist with the correct actor/note, neither
    silently dropped."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        created = _create_complaint(client, live_server, headers)
        first = client.post(
            f"{live_server}/api/complaints/{created['id']}/status",
            json={"new_status": "in_progress", "note": None},
            headers=headers,
        )
        assert first.status_code == 200

    def _send(new_status: str, note: str) -> httpx.Response:
        # Each worker gets its own `httpx.Client` and its own independent
        # `/api/login` call (its own session cookie + CSRF token) — never a
        # session/client shared across threads. Sharing one login across
        # concurrent requests was the source of the ~15-20% flake this test
        # used to exhibit (code-reviewer T-018 rework, Fix 1): a shared
        # client/session raced its own cookie jar and CSRF token between the
        # two "concurrent" requests, occasionally producing an intermittent
        # non-200 (e.g. a CSRF/session hiccup) that then surfaced as an
        # opaque `KeyError` below rather than a clear assertion failure.
        with httpx.Client() as thread_client:
            thread_headers = _logged_in_headers(thread_client, live_server, live_seeded_accounts)
            return thread_client.post(
                f"{live_server}/api/complaints/{created['id']}/status",
                json={"new_status": new_status, "note": note},
                headers=thread_headers,
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(_send, "resolved", "fixed same day")
        future_b = executor.submit(_send, "rejected", "duplicate")
        response_a = future_a.result()
        response_b = future_b.result()

    # The row lock serialises the two transactions — exactly one of them
    # observes `in_progress` as the current status and succeeds; the other,
    # having been blocked on the lock until the first committed, observes
    # the *first* transaction's new status and finds its own requested
    # transition illegal (both `resolved` and `rejected` only accept
    # `in_progress` as their previous status, and neither one is a legal
    # next status of the other). `resolved` and `rejected` are mutually
    # unreachable siblings of `in_progress`, so under a correctly-working
    # row lock BOTH writers succeeding (`{200}`) is impossible — that
    # outcome would mean the second writer validated against a stale,
    # pre-lock status, exactly the TOCTOU bug ADR-017's lock exists to
    # prevent. Asserting the exact set (rather than `in ({200}, {200,
    # 422})`) means this test would actually fail if the lock were silently
    # removed (security-reviewer F-review note).
    statuses = {response_a.status_code, response_b.status_code}
    assert statuses == {200, 422}, (
        response_a.status_code,
        response_a.text,
        response_b.status_code,
        response_b.text,
    )

    history = _status_history_rows(db_engine, created["id"])
    # The seed transition (new->in_progress) plus exactly one committed
    # status change.
    assert len(history) == 2

    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        final = client.get(f"{live_server}/api/complaints/{created['id']}", headers=headers)
    assert final.status_code == 200, final.text
    final_status = final.json()["status"]
    committed_statuses = {
        r.json()["status"] for r in (response_a, response_b) if r.status_code == 200
    }
    assert final_status in committed_statuses
