"""Scaffold tests proving the T-003a rollback fixture (test-strategy.md §3).

Evidence for T-003a's done-condition: running `uv run pytest -m integration`
twice in a row must show, both times, that `test_second_test_starts_with_zero_rows`
sees zero rows in `clerk_account` — proving the row inserted by
`test_make_clerk_is_visible_within_its_own_transaction` never survives past
its own test, whether that is the next test in the same run or the first
test of a brand-new run.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from app.db.models import ClerkAccount
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.conftest import resolve_test_database_url

# Module-level (collection-time) check: this suite must be configured
# against `panchayat_test`, never any other database. Pure string check —
# no DB connection is opened here (design constraint, T-003a).
_configured_database = resolve_test_database_url()
assert _configured_database.rsplit("/", maxsplit=1)[-1] == "panchayat_test", (
    "Integration tests must run against 'panchayat_test', got a URL ending "
    f"in {_configured_database.rsplit('/', maxsplit=1)[-1]!r}"
)

pytestmark = pytest.mark.integration


def test_make_clerk_is_visible_within_its_own_transaction(
    db_session: Session, make_clerk: Callable[..., ClerkAccount]
) -> None:
    clerk = make_clerk(username="test_clerk_rollback_scaffold")

    row = (
        db_session.execute(
            text("SELECT username FROM clerk_account WHERE id = :id"),
            {"id": clerk.id},
        )
        .mappings()
        .one()
    )

    assert row["username"] == "test_clerk_rollback_scaffold"


def test_second_test_starts_with_zero_rows(db_session: Session) -> None:
    """Proves rollback: if the fixture leaked, this would see the row the
    previous test inserted."""
    count = db_session.execute(text("SELECT count(*) FROM clerk_account")).scalar_one()
    assert count == 0
