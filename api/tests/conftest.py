"""Base integration-test fixtures (T-003a, ORM-ified at T-004).

Delivers test-strategy.md §3 "Tooling detail" / §4 "Test data strategy":

- Pytest markers (`unit`/`integration`/`e2e`) are already registered in
  `pyproject.toml` by T-001 — nothing to duplicate here.
- A session-scoped fixture that runs `alembic upgrade head` against the
  integration test database exactly once per test session, not once per
  test (test-strategy.md §3), and registers the append-only guard
  (`app/db/guard.py`) on the same engine the tests use, so integration
  tests exercise the real enforcement path.
- A function-scoped transaction-rollback fixture (`db_session`): each
  integration test runs inside an outer transaction + SAVEPOINT so that
  application code under test may call `session.commit()` without ending
  the outer transaction; the outer transaction is rolled back at teardown,
  so tests never leak rows into one another and never depend on execution
  order.
- Fixture factories for synthetic test rows: `make_clerk`, `make_complaint`,
  `make_session`. These build ORM models (`app.db.models`) via
  `tests/factories.py` (T-004 — replaces the T-003a Core-`text()`
  skeletons, which existed only because `app.db.models` did not exist yet).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.db.guard import register_append_only_guard
from app.db.models import ClerkAccount, Complaint
from app.db.models.session import Session as SessionRow
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from tests import factories

_API_DIR = Path(__file__).resolve().parents[1]
_ALEMBIC_INI = _API_DIR / "alembic.ini"

_DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://panchayat:panchayat@localhost:5432/panchayat_test"
)


def resolve_test_database_url() -> str:
    """Resolve the Postgres URL used for integration tests.

    `TEST_DATABASE_URL` always wins when set. Absent that, the local literal
    default is used **only** when `ENVIRONMENT` is unset, `"test"`, or
    `"dev"` — an unexpected `ENVIRONMENT` (e.g. `"staging"`/`"prod"`) never
    silently falls back to a guessed database. As a second belt-and-braces
    check, refuse outright if the resolved database is literally
    `panchayat` (the dev database, per project-config.md `db_start`) —
    integration tests must run against `panchayat_test` only.

    Pure/no I/O: safe to call at collection time.
    """
    explicit = os.environ.get("TEST_DATABASE_URL")
    if explicit:
        url = explicit
    else:
        environment = os.environ.get("ENVIRONMENT")
        if environment not in (None, "", "test", "dev"):
            raise RuntimeError(
                "TEST_DATABASE_URL is not set and ENVIRONMENT="
                f"{environment!r} is not one that may fall back to the local "
                "default test database — set TEST_DATABASE_URL explicitly."
            )
        url = _DEFAULT_TEST_DATABASE_URL

    database_name = make_url(url).database
    if database_name == "panchayat":
        raise RuntimeError(
            "Refusing to run integration tests against the 'panchayat' dev "
            "database — TEST_DATABASE_URL (or the default) must point at "
            "'panchayat_test'."
        )
    return url


def _run_migrations(database_url: str) -> None:
    """Run `alembic upgrade head` against `database_url`.

    `migrations/env.py` reads `DATABASE_URL` from the process environment
    (T-003), so it is set for the duration of this call and restored
    afterwards regardless of outcome.
    """
    config = Config(str(_ALEMBIC_INI))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.upgrade(config, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous


@pytest.fixture(scope="session")
def db_engine() -> Iterator[Engine]:
    """Session-scoped engine bound to the integration test database.

    Verifies connectivity with a clear error message, migrates the schema
    to head exactly once per test session (test-strategy.md §3), and
    registers the append-only guard on this engine so every integration
    test using `db_session` exercises the real enforcement path.
    """
    database_url = resolve_test_database_url()
    engine = create_engine(database_url, future=True)
    register_append_only_guard(engine)
    try:
        with engine.connect():
            pass
    except OperationalError as exc:
        engine.dispose()
        redacted_url = make_url(database_url).render_as_string(hide_password=True)
        raise RuntimeError(
            "Could not connect to the integration test database at "
            f"{redacted_url!r}. Is local PostgreSQL 16 running with the "
            "'panchayat_test' database and 'panchayat' role available "
            "(see db_start in .claude/project-config.md)? "
            f"Original error: {exc}"
        ) from exc

    _run_migrations(database_url)

    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    """Function-scoped transaction-rollback session (test-strategy.md §3).

    Opens a connection, begins an outer transaction, and binds a `Session`
    to it with `join_transaction_mode="create_savepoint"` (SQLAlchemy 2.x)
    so code under test may call `session.commit()` — that only releases a
    SAVEPOINT, it never ends the outer transaction. The outer transaction is
    rolled back at teardown, so nothing written during the test survives.
    """
    connection = db_engine.connect()
    outer_transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture
def make_clerk(db_session: Session) -> Callable[..., ClerkAccount]:
    """Factory fixture for a synthetic `clerk_account` ORM row."""

    def _make_clerk(
        username: str | None = None,
        is_admin: bool = False,
        must_change_password: bool = False,
    ) -> ClerkAccount:
        return factories.make_clerk(
            db_session,
            username=username,
            is_admin=is_admin,
            must_change_password=must_change_password,
        )

    return _make_clerk


@pytest.fixture
def make_complaint(
    db_session: Session, make_clerk: Callable[..., ClerkAccount]
) -> Callable[..., Complaint]:
    """Factory fixture for a synthetic `complaint` ORM row."""

    def _make_complaint(
        status: str = "new",
        created_by: int | None = None,
        citizen_name: str | None = None,
        citizen_phone: str | None = None,
        description: str | None = None,
    ) -> Complaint:
        return factories.make_complaint(
            db_session,
            status=status,
            created_by=created_by,
            citizen_name=citizen_name,
            citizen_phone=citizen_phone,
            description=description,
        )

    return _make_complaint


@pytest.fixture
def make_session(
    db_session: Session, make_clerk: Callable[..., ClerkAccount]
) -> Callable[..., SessionRow]:
    """Factory fixture for a synthetic `session` ORM row."""

    def _make_session(
        user_id: int | None = None,
        absolute_expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> SessionRow:
        return factories.make_session(
            db_session,
            user_id=user_id,
            absolute_expires_at=absolute_expires_at,
            revoked_at=revoked_at,
        )

    return _make_session
