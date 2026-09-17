"""Integration tests for `POST /api/complaints` (T-009).

Same `live_server` + `live_seeded_accounts` approach as
`test_auth_routes.py` (T-008) — chosen for the same reason: cookie/CSRF
behaviour on an authenticated `POST` is a real-server, real-cookie concern.
Every request logs in first (through the real `/api/login` route) and
carries the session cookie + session-bound CSRF token back by hand, never
via the client's automatic cookie jar (see test_auth_routes.py's module
docstring for why: `Secure` cookies over a plain-`http://` `live_server`).
"""

from __future__ import annotations

import concurrent.futures
import os
import uuid
from collections.abc import Callable

import httpx
import pytest
from app.middleware.csrf import ANON_SEED_COOKIE, compute_anonymous_csrf_token
from sqlalchemy import text
from sqlalchemy.engine import Engine

from tests.conftest import SeededAccounts


def _complaint_row_count(engine: Engine) -> int:
    with engine.connect() as connection:
        return connection.execute(text("SELECT COUNT(*) FROM complaint")).scalar_one()


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
        client,
        base_url,
        username=accounts.clerk_username,
        password=accounts.clerk_password,
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


# --- TC-API-004 -------------------------------------------------------------


def test_create_complaint_without_session_is_401_and_creates_no_row(
    live_server: str, db_engine: Engine, truncate_tables: Callable[[], None]
) -> None:
    """TC-API-004. A valid anonymous CSRF pair is supplied (Origin + the
    stateless `__Host-csrfseed` HMAC) so the request clears the CSRF layer
    and the 401 asserted here is genuinely authz's own "no session" answer,
    not a CSRF-layer 403 (rows 5 vs 6 of the ADR-007 middleware chain —
    same distinction test_auth_routes.py's logout tests draw)."""
    seed = "tc-api-004-anon-seed"
    token = compute_anonymous_csrf_token(_secret_key(), seed)
    row_count_before = _complaint_row_count(db_engine)

    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/complaints",
            json=_valid_body(),
            headers={
                "Origin": _origin(),
                "X-CSRF-Token": token,
                "Cookie": f"{ANON_SEED_COOKIE}={seed}",
            },
        )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"
    assert _complaint_row_count(db_engine) == row_count_before


# --- TC-API-010 --------------------------------------------------------------


def test_create_complaint_all_fields_valid_returns_201(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-API-010."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        response = client.post(
            f"{live_server}/api/complaints", json=_valid_body(), headers=headers
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"
    assert body["created_at"]
    assert len(body["complaint_number"]) == 9
    assert body["duplicate"] is False
    assert body["legal_next_statuses"] == ["in_progress"]
    assert body["created_by"] == live_seeded_accounts.clerk_username


# --- TC-API-011/012/013/014/015 ----------------------------------------------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("description", ""),
        ("citizen_name", ""),
        ("citizen_phone", ""),
        ("citizen_phone", "abc-not-a-phone"),
        ("citizen_name", "a" * 101),
        ("description", "a" * 2001),
    ],
    ids=[
        "TC-API-011-blank-description",
        "TC-API-012-blank-citizen-name",
        "TC-API-013-blank-citizen-phone",
        "TC-API-014-malformed-phone",
        "TC-API-015-name-too-long",
        "TC-API-015-description-too-long",
    ],
)
def test_create_complaint_invalid_field_returns_422_and_creates_no_row(
    live_server: str,
    live_seeded_accounts: SeededAccounts,
    db_engine: Engine,
    field: str,
    value: str,
) -> None:
    row_count_before = _complaint_row_count(db_engine)
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        response = client.post(
            f"{live_server}/api/complaints",
            json=_valid_body(**{field: value}),
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert _complaint_row_count(db_engine) == row_count_before


# --- TC-API-017 (REL-T25) -----------------------------------------------------


def test_create_complaint_same_client_request_id_replay_is_idempotent(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-API-017 / REL-T25: POSTing twice with the same `client_request_id`
    returns the same `id`/`complaint_number` on the second call, with
    `duplicate: true` and `200` — no second row created. Also stands in for
    TC-API-016's server-side half (a retried submit after a client-side
    timeout is exactly this same replay path, and it is provably safe)."""
    body = _valid_body()

    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        first = client.post(f"{live_server}/api/complaints", json=body, headers=headers)
        second = client.post(f"{live_server}/api/complaints", json=body, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    first_body, second_body = first.json(), second.json()
    assert first_body["duplicate"] is False
    assert second_body["duplicate"] is True
    assert second_body["id"] == first_body["id"]
    assert second_body["complaint_number"] == first_body["complaint_number"]


def test_create_complaint_client_request_id_replay_by_different_clerk_is_422(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """Security review F1: a `client_request_id` collision belonging to a
    *different* clerk must never be returned as if it were the replaying
    clerk's own complaint. Clerk B (here, `admin_test`, a distinct clerk
    account) reuses clerk A's (`clerk_test`) `client_request_id` and gets a
    `422 invalid_input` on the `client_request_id` field, not clerk A's
    complaint data, and no second row is created."""
    shared_client_request_id = str(uuid.uuid4())

    with httpx.Client() as client:
        clerk_a_headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        first = client.post(
            f"{live_server}/api/complaints",
            json=_valid_body(client_request_id=shared_client_request_id),
            headers=clerk_a_headers,
        )
        assert first.status_code == 201
        row_count_after_first = _complaint_row_count(db_engine)

        clerk_b_headers = _logged_in_headers(
            client,
            live_server,
            SeededAccounts(
                admin_username=live_seeded_accounts.admin_username,
                admin_password=live_seeded_accounts.admin_password,
                admin_clerk=live_seeded_accounts.admin_clerk,
                clerk_username=live_seeded_accounts.admin_username,
                clerk_password=live_seeded_accounts.admin_password,
                clerk=live_seeded_accounts.admin_clerk,
            ),
        )
        second = client.post(
            f"{live_server}/api/complaints",
            json=_valid_body(client_request_id=shared_client_request_id),
            headers=clerk_b_headers,
        )

    assert second.status_code == 422
    body = second.json()
    assert body["error"]["code"] == "invalid_input"
    assert body["error"]["fields"] == {"client_request_id": "conflict"}
    # Never clerk A's complaint data leaked back to clerk B.
    assert "complaint_number" not in body
    assert _complaint_row_count(db_engine) == row_count_after_first


def test_create_complaint_different_client_request_id_creates_a_new_complaint(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """Control for TC-API-017: a *different* `client_request_id` always
    creates a new complaint (api-contract.md §7)."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        first = client.post(
            f"{live_server}/api/complaints", json=_valid_body(), headers=headers
        )
        second = client.post(
            f"{live_server}/api/complaints", json=_valid_body(), headers=headers
        )

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert first.json()["complaint_number"] != second.json()["complaint_number"]


# --- TC-API-018 / TC-API-091 --------------------------------------------------


@pytest.mark.parametrize(
    "extra_field",
    ["aadhaar", "voter_id"],
    ids=["TC-API-018", "TC-API-091"],
)
def test_create_complaint_extra_government_id_field_returns_422_and_never_persisted(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine, extra_field: str
) -> None:
    extra_value = "1234-5678-9012"
    row_count_before = _complaint_row_count(db_engine)
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        response = client.post(
            f"{live_server}/api/complaints",
            json=_valid_body(**{extra_field: extra_value}),
            headers=headers,
        )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_input"
    # The submitted government-ID value itself must never reach the client
    # back (AC-012/BR-009) — a tautological "or 'fields' in body" check
    # (security review F3) is not enough since a 422 envelope always has
    # "fields".
    assert extra_value not in response.text
    assert _complaint_row_count(db_engine) == row_count_before


# --- TC-API-019 ---------------------------------------------------------------


def test_create_complaint_five_consecutive_number_collisions_returns_503(
    live_server: str, live_seeded_accounts: SeededAccounts, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC-API-019: force 5 consecutive `complaint_number` collisions via a
    monkeypatched generator — `503 service_unavailable`, no wrong/reused
    number assigned. The generator is patched inside the live server's own
    process (this test process, since `live_server` runs the app in-process
    on a background thread) so every attempt in `insert_new`'s retry loop
    produces the exact same, already-taken, number."""
    from app.db.repositories import complaint as complaint_repo

    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)

        # Take the fixed number first, for real, through the normal path.
        fixed_number = "4T9KM2XQ8"
        monkeypatch.setattr(complaint_repo.complaint_number, "generate", lambda: fixed_number)
        first = client.post(
            f"{live_server}/api/complaints", json=_valid_body(), headers=headers
        )
        assert first.status_code == 201
        assert first.json()["complaint_number"] == fixed_number

        # Every subsequent attempt collides on the same taken number.
        second = client.post(
            f"{live_server}/api/complaints", json=_valid_body(), headers=headers
        )

    assert second.status_code == 503
    assert second.json()["error"]["code"] == "service_unavailable"


# --- TC-API-020 ---------------------------------------------------------------


def test_create_complaint_100_sequential_have_distinct_numbers(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-API-020: 100 complaints created in sequence all get distinct
    `complaint_number` values."""
    numbers = set()
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        for _ in range(100):
            response = client.post(
                f"{live_server}/api/complaints", json=_valid_body(), headers=headers
            )
            assert response.status_code == 201
            numbers.add(response.json()["complaint_number"])

    assert len(numbers) == 100


# --- TC-API-021 ---------------------------------------------------------------


def test_create_complaint_20_concurrent_have_distinct_numbers(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-API-021: 20 concurrent `POST /api/complaints` via
    `concurrent.futures` against `live_server`, all succeeding with 20
    distinct complaint numbers."""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)

    def _create() -> httpx.Response:
        with httpx.Client() as thread_client:
            return thread_client.post(
                f"{live_server}/api/complaints", json=_valid_body(), headers=headers
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        responses = list(executor.map(lambda _: _create(), range(20)))

    assert all(response.status_code == 201 for response in responses)
    numbers = {response.json()["complaint_number"] for response in responses}
    assert len(numbers) == 20


# --- Security review F5 -------------------------------------------------------


@pytest.mark.parametrize("field", ["citizen_name", "description"])
def test_create_complaint_nul_byte_in_field_returns_422_and_creates_no_row(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine, field: str
) -> None:
    """Security review F5: a C0 control character (including NUL, `\\u0000`)
    must be rejected as a normal 422 `invalid_input` at the schema layer,
    never reach psycopg (which raises an uncatalogued `DataError` on NUL and
    would otherwise surface as an uncaught 500)."""
    row_count_before = _complaint_row_count(db_engine)
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        response = client.post(
            f"{live_server}/api/complaints",
            json=_valid_body(**{field: "bad" + chr(0) + "value"}),
            headers=headers,
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"
    assert _complaint_row_count(db_engine) == row_count_before


# --- Security review F7 (round 2) --------------------------------------------


def test_create_complaint_multiline_description_is_accepted_and_roundtrips(
    live_server: str, live_seeded_accounts: SeededAccounts, db_engine: Engine
) -> None:
    """F7: `description` is a multi-line textarea (component-spec.md /
    screen-inventory.md), so `\\n` must not be rejected as a control
    character the way it correctly is for the single-line `citizen_name`/
    `citizen_phone` fields. The value must round-trip unchanged (no `\\n`
    stripped or mangled)."""
    multiline_description = "Line one\nLine two"
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        response = client.post(
            f"{live_server}/api/complaints",
            json=_valid_body(description=multiline_description),
            headers=headers,
        )

    assert response.status_code == 201
    assert response.json()["description"] == multiline_description


# --- TC-SEC-006 (router half — no DELETE endpoint exists at all) -------------


def test_no_delete_route_exists_for_complaints(
    live_server: str, live_seeded_accounts: SeededAccounts
) -> None:
    """TC-SEC-006, router half: a direct delete-style HTTP request never
    reaches any handler — there is no `DELETE` route registered for
    `/api/complaints` (or any resource), so Starlette's own routing answers
    `405`/`404` before any application code runs. (The ORM-layer half — an
    `UPDATE`/`DELETE` construct against the three append-only history
    tables raising at the data-access layer — is proven in
    tests/integration/test_append_only_guard.py, T-004.)"""
    with httpx.Client() as client:
        headers = _logged_in_headers(client, live_server, live_seeded_accounts)
        create_response = client.post(
            f"{live_server}/api/complaints", json=_valid_body(), headers=headers
        )
        assert create_response.status_code == 201
        complaint_id = create_response.json()["id"]

        delete_response = client.delete(
            f"{live_server}/api/complaints/{complaint_id}", headers=headers
        )

    assert delete_response.status_code in (404, 405)
    assert "error" not in delete_response.json()
