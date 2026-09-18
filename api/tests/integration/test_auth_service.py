"""Service-level integration tests for `app.services.auth` (T-006):
login success/failure, logout, and ADR-021 rotation-on-login. Calls
`services/auth.py` directly — no HTTP route is hit here (routes are
T-008).

`tests.factories.make_clerk` stores a syntactic-but-unverifiable Argon2
hash (it exists only to satisfy `password_hash TEXT NOT NULL`), so it
cannot be used for a login-success test. `_make_clerk_with_known_password`
below builds the same shape of row with a real, known password instead —
the `make_clerk`/`make_session` fixtures are still the right tool for
tests that don't need to authenticate as a specific plaintext (see
`test_conftest_rollback.py`, `test_append_only_guard.py`).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import sqlalchemy as sa
from app.core import hashing
from app.core.clock import now as clock_now
from app.core.errors import NotAuthenticated
from app.db.models.clerk_account import ClerkAccount
from app.db.models.session import Session as SessionRow
from app.services import auth as auth_service
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

_KNOWN_PASSWORD = "correct horse battery staple 42"


def _make_clerk_with_known_password(
    db_session: Session, *, password: str = _KNOWN_PASSWORD
) -> ClerkAccount:
    clerk = ClerkAccount(
        username=f"test_clerk_{uuid4().hex[:10]}",
        password_hash=hashing.hash_password(password),
        is_admin_clerk=False,
        must_change_password=False,
        password_is_otp=False,
        password_set_at=clock_now(),
    )
    db_session.add(clerk)
    db_session.flush()
    return clerk


def _session_row_for_token(db_session: Session, raw_token: str) -> SessionRow | None:
    return db_session.scalar(
        sa.select(SessionRow).where(SessionRow.token_hash == hashing.sha256(raw_token))
    )


def _session_row_count(db_session: Session) -> int:
    return db_session.scalar(sa.select(sa.func.count()).select_from(SessionRow)) or 0


def test_login_success_issues_a_session_row_whose_token_hash_matches(db_session: Session) -> None:
    clerk = _make_clerk_with_known_password(db_session)

    user, raw_token = auth_service.login(db_session, clerk.username, _KNOWN_PASSWORD)

    assert user.id == clerk.id
    row = _session_row_for_token(db_session, raw_token)
    assert row is not None
    assert row.user_id == clerk.id
    assert row.token_hash == hashing.sha256(raw_token)
    assert row.revoked_at is None


def test_login_wrong_password_raises_not_authenticated_and_issues_no_row(
    db_session: Session,
) -> None:
    clerk = _make_clerk_with_known_password(db_session)

    with pytest.raises(NotAuthenticated):
        auth_service.login(db_session, clerk.username, "definitely-the-wrong-password")

    row = db_session.scalar(sa.select(SessionRow).where(SessionRow.user_id == clerk.id))
    assert row is None


def test_login_unknown_username_raises_the_same_error_and_issues_no_row(
    db_session: Session,
) -> None:
    before = _session_row_count(db_session)

    with pytest.raises(NotAuthenticated):
        auth_service.login(db_session, "no_such_clerk_account_exists", "whatever-password-value")

    assert _session_row_count(db_session) == before


def test_login_unknown_username_and_wrong_password_raise_the_same_error_type(
    db_session: Session,
) -> None:
    """error-catalog.md: 'the single generic response to every failed
    POST /api/login attempt' — same exception type either way."""
    clerk = _make_clerk_with_known_password(db_session)

    with pytest.raises(NotAuthenticated) as unknown_exc_info:
        auth_service.login(db_session, "no_such_clerk_account_exists", "whatever")

    with pytest.raises(NotAuthenticated) as wrong_password_exc_info:
        auth_service.login(db_session, clerk.username, "definitely-the-wrong-password")

    assert unknown_exc_info.value.code == wrong_password_exc_info.value.code == "not_authenticated"


def test_logout_revokes_the_session_and_resolve_session_then_rejects_it(
    db_session: Session,
) -> None:
    clerk = _make_clerk_with_known_password(db_session)
    _, raw_token = auth_service.login(db_session, clerk.username, _KNOWN_PASSWORD)

    resolved_before = auth_service.resolve_session(db_session, raw_token)
    assert resolved_before is not None
    assert resolved_before.id == clerk.id

    auth_service.logout(db_session, raw_token)

    row = _session_row_for_token(db_session, raw_token)
    assert row is not None
    assert row.revoked_at is not None

    assert auth_service.resolve_session(db_session, raw_token) is None


def test_resolve_session_returns_none_for_an_unknown_token(db_session: Session) -> None:
    assert auth_service.resolve_session(db_session, "not-a-real-token") is None


def test_second_login_with_no_presented_cookie_adds_a_row_and_revokes_nothing(
    db_session: Session,
) -> None:
    """ADR-021: 'A login with no cookie simply adds a row.'"""
    clerk = _make_clerk_with_known_password(db_session)

    _, first_token = auth_service.login(db_session, clerk.username, _KNOWN_PASSWORD)
    _, second_token = auth_service.login(db_session, clerk.username, _KNOWN_PASSWORD)

    assert first_token != second_token
    first_row = _session_row_for_token(db_session, first_token)
    second_row = _session_row_for_token(db_session, second_token)
    assert first_row is not None and second_row is not None
    assert first_row.id != second_row.id
    assert first_row.revoked_at is None
    assert second_row.revoked_at is None


def test_second_login_presenting_the_first_cookie_revokes_only_that_session(
    db_session: Session,
) -> None:
    """ADR-021: 'revoke only the session presented in this request's own
    cookie' — never every session for the user."""
    clerk = _make_clerk_with_known_password(db_session)

    _, first_token = auth_service.login(db_session, clerk.username, _KNOWN_PASSWORD)
    _, second_token = auth_service.login(
        db_session, clerk.username, _KNOWN_PASSWORD, presented_raw_token=first_token
    )

    first_row = _session_row_for_token(db_session, first_token)
    second_row = _session_row_for_token(db_session, second_token)
    assert first_row is not None and second_row is not None
    assert first_row.revoked_at is not None
    assert second_row.revoked_at is None


def test_login_presenting_an_already_revoked_token_does_not_error(db_session: Session) -> None:
    clerk = _make_clerk_with_known_password(db_session)
    _, first_token = auth_service.login(db_session, clerk.username, _KNOWN_PASSWORD)
    auth_service.logout(db_session, first_token)

    # Presenting an already-revoked token on a subsequent login must not
    # raise — it simply has nothing live left to revoke.
    user, _second_token = auth_service.login(
        db_session, clerk.username, _KNOWN_PASSWORD, presented_raw_token=first_token
    )

    assert user.id == clerk.id
