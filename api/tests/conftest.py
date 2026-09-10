"""Base integration-test fixtures (T-003a).

Delivers test-strategy.md §3 "Tooling detail" / §4 "Test data strategy":

- Pytest markers (`unit`/`integration`/`e2e`) are already registered in
  `pyproject.toml` by T-001 — nothing to duplicate here.
- A session-scoped fixture that runs `alembic upgrade head` against the
  integration test database exactly once per test session, not once per
  test (test-strategy.md §3).
- A function-scoped transaction-rollback fixture (`db_session`): each
  integration test runs inside an outer transaction + SAVEPOINT so that
  application code under test may call `session.commit()` without ending
  the outer transaction; the outer transaction is rolled back at teardown,
  so tests never leak rows into one another and never depend on execution
  order.
- Fixture-factory **skeletons** for synthetic test rows: `make_clerk`,
  `make_complaint`, `make_session`. These insert via SQLAlchemy Core
  `text()` statements (not ORM models) because `app.db.models` does not
  exist yet — T-004 switches every one of these to ORM models.

The rate-limiter AUTOCOMMIT exception (test-strategy.md §3) is deliberately
out of scope here — it is a later task's fixture, not this one's.
"""

from __future__ import annotations

import os
import secrets
import string
from collections.abc import Callable, Iterator, Mapping
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

try:
    from app.core.clock import now as _clock_now
except ImportError:  # pragma: no cover - app/core is mid-rework by another task

    def _clock_now() -> datetime:
        # TODO(T-005): remove this fallback once app.core.clock is stable
        # again; this fixture module must use the injectable clock like
        # everything else in app/ (coding-guidelines.md § Validation/typing).
        from datetime import UTC

        return datetime.now(UTC)


_API_DIR = Path(__file__).resolve().parents[1]
_ALEMBIC_INI = _API_DIR / "alembic.ini"

_DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://panchayat:panchayat@localhost:5432/panchayat_test"
)

# Crockford base-32 alphabet (excludes I, L, O, U) — matches the complaint
# CHECK constraint `complaint_number ~ '^[0-9A-HJKMNP-TV-Z]{9}$'` exactly
# (schema.md "Compact DDL sketch" / migrations/versions/0001_initial.py).
_CROCKFORD32_ALPHABET = "0123456789" + "ABCDEFGH" + "JK" + "MN" + "PQRST" + "VWXYZ"

# A syntactically Argon2-looking hash. Not a real hash of any real password —
# only used to satisfy `password_hash TEXT NOT NULL` in synthetic test rows.
_FAKE_ARGON2_LOOKING_HASH_FOR_TESTS = (
    "$argon2id$v=19$m=65536,t=3,p=4$c3ludGhldGljdGVzdHNhbHQ$c3ludGhldGljdGVzdGhhc2h2YWx1ZQ"
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

    Verifies connectivity with a clear error message, then migrates the
    schema to head exactly once per test session (test-strategy.md §3).
    """
    database_url = resolve_test_database_url()
    engine = create_engine(database_url, future=True)
    try:
        with engine.connect():
            pass
    except OperationalError as exc:
        engine.dispose()
        raise RuntimeError(
            "Could not connect to the integration test database at "
            f"{database_url!r}. Is local PostgreSQL 16 running with the "
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


def _random_digits(n: int) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(n))


def _synthetic_complaint_number() -> str:
    return "".join(secrets.choice(_CROCKFORD32_ALPHABET) for _ in range(9))


@pytest.fixture
def make_clerk(db_session: Session) -> Callable[..., Mapping[str, Any]]:
    """Factory for a synthetic `clerk_account` row.

    Skeleton — T-004 switches this to ORM models. Inserts via SQLAlchemy
    Core `text()` because `app.db.models` does not exist yet.
    """

    def _make_clerk(
        username: str | None = None,
        is_admin: bool = False,
        must_change_password: bool = False,
    ) -> Mapping[str, Any]:
        username = username or f"test_clerk_{uuid4().hex[:10]}"
        stmt = text(
            """
            INSERT INTO clerk_account
                (username, password_hash, is_admin_clerk, must_change_password,
                 password_is_otp, password_set_at)
            VALUES
                (:username, :password_hash, :is_admin_clerk, :must_change_password,
                 false, :password_set_at)
            RETURNING id, username, password_hash, is_admin_clerk,
                      must_change_password, password_is_otp, password_set_at,
                      created_at, updated_at, created_by
            """
        )
        return (
            db_session.execute(
                stmt,
                {
                    "username": username,
                    "password_hash": _FAKE_ARGON2_LOOKING_HASH_FOR_TESTS,
                    "is_admin_clerk": is_admin,
                    "must_change_password": must_change_password,
                    "password_set_at": _clock_now(),
                },
            )
            .mappings()
            .one()
        )

    return _make_clerk


@pytest.fixture
def make_complaint(
    db_session: Session, make_clerk: Callable[..., Mapping[str, Any]]
) -> Callable[..., Mapping[str, Any]]:
    """Factory for a synthetic `complaint` row.

    Skeleton — T-004 switches this to ORM models. `created_by` defaults to
    a freshly-created synthetic clerk via `make_clerk` when not given.
    """

    def _make_complaint(
        status: str = "new",
        created_by: int | None = None,
        citizen_name: str | None = None,
        citizen_phone: str | None = None,
        description: str | None = None,
    ) -> Mapping[str, Any]:
        if created_by is None:
            created_by = make_clerk()["id"]
        stmt = text(
            """
            INSERT INTO complaint
                (complaint_number, client_request_id, citizen_name, citizen_phone,
                 description, status, created_by)
            VALUES
                (:complaint_number, :client_request_id, :citizen_name, :citizen_phone,
                 :description, :status::complaint_status, :created_by)
            RETURNING id, complaint_number, client_request_id, citizen_name,
                      citizen_phone, description, status, created_at,
                      updated_at, created_by
            """
        )
        return (
            db_session.execute(
                stmt,
                {
                    "complaint_number": _synthetic_complaint_number(),
                    "client_request_id": uuid4(),
                    "citizen_name": citizen_name or f"Test Citizen {uuid4().hex[:6]}",
                    "citizen_phone": citizen_phone or f"+9190000{_random_digits(4)}",
                    "description": description
                    or "Synthetic test complaint for automated integration tests.",
                    "status": status,
                    "created_by": created_by,
                },
            )
            .mappings()
            .one()
        )

    return _make_complaint


@pytest.fixture
def make_session(
    db_session: Session, make_clerk: Callable[..., Mapping[str, Any]]
) -> Callable[..., Mapping[str, Any]]:
    """Factory for a synthetic `session` row.

    Skeleton — T-004 switches this to ORM models. `user_id` defaults to a
    freshly-created synthetic clerk via `make_clerk` when not given.
    """

    def _make_session(
        user_id: int | None = None,
        absolute_expires_at: datetime | None = None,
        revoked_at: datetime | None = None,
    ) -> Mapping[str, Any]:
        if user_id is None:
            user_id = make_clerk()["id"]
        if absolute_expires_at is None:
            absolute_expires_at = _clock_now() + timedelta(hours=24)
        stmt = text(
            """
            INSERT INTO session
                (user_id, token_hash, csrf_token, absolute_expires_at, revoked_at)
            VALUES
                (:user_id, :token_hash, :csrf_token, :absolute_expires_at, :revoked_at)
            RETURNING id, user_id, token_hash, csrf_token, created_at,
                      last_seen_at, absolute_expires_at, revoked_at
            """
        )
        return (
            db_session.execute(
                stmt,
                {
                    "user_id": user_id,
                    "token_hash": sha256(uuid4().bytes).hexdigest(),
                    "csrf_token": sha256(uuid4().bytes).hexdigest(),
                    "absolute_expires_at": absolute_expires_at,
                    "revoked_at": revoked_at,
                },
            )
            .mappings()
            .one()
        )

    return _make_session
