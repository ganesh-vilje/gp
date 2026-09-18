"""Integration tests for `POST /api/lookup` (T-010).

Same `live_server` approach as `test_complaints_routes.py`/
`test_auth_routes.py`: an anonymous CSRF pair (Origin + the stateless
`__Host-csrfseed` HMAC — security-architecture.md §4, "the public lookup
POST is deliberately not exempt") is supplied by hand on every request,
never via the client's automatic cookie jar.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable, Iterator

import httpx
import pytest
from app.core import complaint_number
from app.db.models import ClerkAccount, Complaint
from app.middleware.csrf import ANON_SEED_COOKIE, compute_anonymous_csrf_token
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from tests import factories

pytestmark = pytest.mark.integration


def _origin() -> str:
    import os

    return os.environ["ALLOWED_ORIGINS"].split(",")[0].strip()


def _secret_key() -> str:
    import os

    return os.environ["SECRET_KEY"]


def _anon_headers() -> dict:
    seed = secrets.token_urlsafe(16)
    token = compute_anonymous_csrf_token(_secret_key(), seed)
    return {
        "Origin": _origin(),
        "X-CSRF-Token": token,
        "Cookie": f"{ANON_SEED_COOKIE}={seed}",
    }


@pytest.fixture
def live_complaint(
    live_server: str, db_engine: Engine, truncate_tables: Callable[[], None]
) -> Iterator[Callable[..., Complaint]]:
    """Committed-for-real `complaint` rows (and their creating clerk), on
    their own `Session`, visible to `live_server`'s own request engine —
    `db_session`'s SAVEPOINT-rollback fixture is invisible to a request
    made over real HTTP (same rationale as `live_seeded_accounts`,
    T-006a). Cleaned up via `truncate_tables` at teardown."""
    session = Session(bind=db_engine, expire_on_commit=False)
    created: list[Complaint] = []

    def _make(**kwargs: object) -> Complaint:
        clerk: ClerkAccount = factories.make_clerk(session)
        complaint = factories.make_complaint(session, created_by=clerk.id, **kwargs)
        # `factories.make_complaint`'s generated number is a random
        # 9-symbol string with no checksum relationship (fine for tests
        # that never call `core.complaint_number.validate()`) — the lookup
        # route does call it (BR-015), so give this row a real, checksum-
        # valid number instead.
        complaint.complaint_number = complaint_number.generate()
        session.commit()
        created.append(complaint)
        return complaint

    try:
        yield _make
    finally:
        session.close()
        truncate_tables()


def _hyphenate(canonical: str) -> str:
    return f"{canonical[:4]}-{canonical[4:]}"


# --- TC-API-050 / TC-SEC-002 --------------------------------------------------


def test_lookup_known_number_returns_exact_public_dto(
    live_server: str, live_complaint: Callable[..., Complaint]
) -> None:
    """TC-API-050: 200, DTO = exactly `{complaint_number, status,
    public_update, date_logged}`. TC-SEC-002: no occurrence of the name,
    phone, or note anywhere in the response body/headers."""
    complaint = live_complaint(
        status="in_progress",
        citizen_name="Secret Citizen Name",
        citizen_phone="+919876500000",
    )

    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/lookup",
            json={"complaint_number": complaint.complaint_number},
            headers=_anon_headers(),
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"complaint_number", "status", "public_update", "date_logged"}
    assert body["complaint_number"] == complaint.complaint_number
    assert body["status"] == "in_progress"
    assert body["public_update"] == "in_progress"

    full_text = response.text + "".join(f"{k}:{v}" for k, v in response.headers.items())
    assert "Secret Citizen Name" not in full_text
    assert "+919876500000" not in full_text


# --- TC-API-051 ----------------------------------------------------------------


def test_lookup_response_never_contains_pii(
    live_server: str, live_complaint: Callable[..., Complaint]
) -> None:
    """TC-API-051: full-body string search, not just field absence."""
    complaint = live_complaint(
        citizen_name="Another Secret Name",
        citizen_phone="+919876511111",
        description="A clerk note nobody public should ever see.",
    )

    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/lookup",
            json={"complaint_number": complaint.complaint_number},
            headers=_anon_headers(),
        )

    assert response.status_code == 200
    assert "Another Secret Name" not in response.text
    assert "+919876511111" not in response.text
    assert "A clerk note nobody public should ever see." not in response.text


# --- TC-API-052 ------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "expected_public_update"),
    [
        ("new", "received"),
        ("in_progress", "in_progress"),
        ("resolved", "resolved"),
        ("rejected", "not_accepted"),
        ("closed", "closed"),
    ],
)
def test_lookup_public_update_is_always_one_of_five_enumerated_values(
    live_server: str,
    live_complaint: Callable[..., Complaint],
    status: str,
    expected_public_update: str,
) -> None:
    """TC-API-052: `public_update` is always one of the 5 enumerated
    values, never free text."""
    complaint = live_complaint(status=status)

    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/lookup",
            json={"complaint_number": complaint.complaint_number},
            headers=_anon_headers(),
        )

    assert response.status_code == 200
    assert response.json()["public_update"] == expected_public_update


# --- TC-API-053 ------------------------------------------------------------


def test_lookup_normalises_mixed_case_and_spaces(
    live_server: str, live_complaint: Callable[..., Complaint]
) -> None:
    """TC-API-053: mixed case / extra spaces / hyphen normalise and
    succeed identically to the canonical form."""
    complaint = live_complaint()
    typed = f" {_hyphenate(complaint.complaint_number.lower())} "

    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/lookup",
            json={"complaint_number": typed},
            headers=_anon_headers(),
        )

    assert response.status_code == 200
    assert response.json()["complaint_number"] == complaint.complaint_number


# --- TC-API-055 ------------------------------------------------------------


def test_lookup_well_formed_unassigned_number_returns_404(live_server: str) -> None:
    """TC-API-055: a well-formed-but-unassigned number is a generic 404
    `not_found`, never distinguished in wording from a malformed one."""
    from app.core import complaint_number

    unassigned = complaint_number.generate()

    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/lookup",
            json={"complaint_number": unassigned},
            headers=_anon_headers(),
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


# --- TC-API-056 ------------------------------------------------------------


def test_lookup_no_match_reveals_nothing_about_other_complaints(
    live_server: str, live_complaint: Callable[..., Complaint]
) -> None:
    """TC-API-056: 404 `not_found`; the response reveals nothing about any
    other complaint."""
    existing = live_complaint(citizen_name="Unrelated Citizen")
    from app.core import complaint_number

    other_number = complaint_number.generate()
    while other_number == existing.complaint_number:  # pragma: no cover - astronomically rare
        other_number = complaint_number.generate()

    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/lookup",
            json={"complaint_number": other_number},
            headers=_anon_headers(),
        )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert "Unrelated Citizen" not in response.text
    assert existing.complaint_number not in response.text


# --- TC-DB-001 / TC-DB-002 (TC-DB-002: raw httpx, no browser — identical here) --


@pytest.mark.parametrize(
    "raw_value",
    ["", "   ", "not-a-valid-number!!"],
    ids=["blank", "whitespace-only", "malformed-format"],
)
def test_lookup_invalid_input_is_400_and_touches_no_complaint_statement(
    live_server: str, query_counter, raw_value: str
) -> None:
    """TC-DB-001/TC-DB-002: for all three sub-cases, 400 `invalid_input`,
    message "Enter a valid complaint number", and zero statements touch
    the `complaint` table (asserted by table name via `query_counter`)."""
    with httpx.Client() as client:
        response = client.post(
            f"{live_server}/api/lookup",
            json={"complaint_number": raw_value},
            headers=_anon_headers(),
        )

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "invalid_input"
    assert body["error"]["message"] == "Enter a valid complaint number."
    assert "complaint" not in query_counter.touched_tables


# --- T-010 security review F2: 429 path -----------------------------------


def test_lookup_21st_request_in_window_is_rate_limited(
    live_server: str, truncate_tables: Callable[[], None]
) -> None:
    """T-010 security review F2: 20/min fixed window (api-contract.md §4).
    Sequential, same client/IP: requests 1-20 must not be 429; the 21st
    must be 429 `rate_limited` with a `Retry-After` header >= 1. (The
    concurrency variant, TC-SEC-003, is T-026's scope.)"""
    from app.core import complaint_number

    unassigned = complaint_number.generate()

    # Other tests in this module/session share the same loopback IP (the
    # limiter's key) and window — clear any counter they left behind so
    # this test starts from a clean 20/min budget.
    truncate_tables()

    try:
        with httpx.Client() as client:
            for _ in range(20):
                response = client.post(
                    f"{live_server}/api/lookup",
                    json={"complaint_number": unassigned},
                    headers=_anon_headers(),
                )
                assert response.status_code != 429

            response = client.post(
                f"{live_server}/api/lookup",
                json={"complaint_number": unassigned},
                headers=_anon_headers(),
            )

        assert response.status_code == 429
        body = response.json()
        assert body["error"]["code"] == "rate_limited"
        retry_after = response.headers.get("Retry-After")
        assert retry_after is not None
        assert int(retry_after) >= 1
    finally:
        truncate_tables()
