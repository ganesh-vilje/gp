"""Scaffold integration tests for the `query_counter` fixture and the
`seeded_accounts` fixture (T-006a, test-strategy.md §3).
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest
import sqlalchemy as sa
from app.db.models import ClerkAccount
from app.services import auth as auth_service
from sqlalchemy.orm import Session

from tests.conftest import QueryCounter, SeededAccounts

pytestmark = pytest.mark.integration


def test_db_session_query_on_clerk_account_shows_touched_table(
    db_session: Session,
    query_counter: QueryCounter,
    make_clerk: Callable[..., ClerkAccount],
) -> None:
    make_clerk()
    query_counter.reset()

    db_session.execute(sa.select(ClerkAccount))

    assert "clerk_account" in query_counter.touched_tables


def test_anonymous_healthz_through_live_server_touches_no_tables(
    live_server: str, query_counter: QueryCounter
) -> None:
    """test-strategy.md §3: the zero-SQL claim — no cookie means
    `session_loader.py` never opens a `Session`, so a public route with no
    DB-backed logic touches nothing at all (not merely no `complaint` row).
    """
    response = httpx.get(f"{live_server}/healthz", timeout=5.0)

    assert response.status_code == 200
    assert query_counter.touched_tables == set()


def test_seeded_accounts_yields_two_rows_usable_for_login(
    db_session: Session, seeded_accounts: SeededAccounts
) -> None:
    assert seeded_accounts.admin_username == "admin_test"
    assert seeded_accounts.admin_clerk.is_admin_clerk is True
    assert seeded_accounts.clerk_username == "clerk_test"
    assert seeded_accounts.clerk.is_admin_clerk is False

    user, raw_token = auth_service.login(
        db_session, seeded_accounts.admin_username, seeded_accounts.admin_password
    )

    assert user.id == seeded_accounts.admin_clerk.id
    assert raw_token
