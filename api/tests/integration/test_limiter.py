"""Integration tests for `app.services.limiter` (T-010, lookup scope).

TC-SEC-024 is the one test in this module that matters for the task's
done-condition; the others are basic correctness checks for the mechanism
this task adds (rev 4/backend-architecture.md §5's fixed-window upsert).
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.db import engine as engine_module
from app.services import limiter as limiter_service
from sqlalchemy import text
from sqlalchemy.engine import Engine

from tests.conftest import resolve_test_database_url

pytestmark = pytest.mark.integration

_SCOPE = "lookup"


@pytest.fixture(autouse=True)
def _limiter_engine_env(db_engine: Engine) -> Iterator[None]:
    """`app.services.limiter` reads `Settings` (via `app.db.engine
    .get_limiter_engine()`), which needs the same env vars `live_server`
    sets — these tests never start a real server, so they set (and
    restore) the same variables directly, and reset the memoised limiter
    engine so it is always built against the test database."""
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = resolve_test_database_url()

    introduced = []
    for key, value in (
        ("ENVIRONMENT", "test"),
        ("SECRET_KEY", secrets.token_urlsafe(32)),
        ("USERNAME_HASH_SALT", secrets.token_urlsafe(32)),
        ("ALLOWED_ORIGINS", "https://example.test"),
    ):
        if key not in os.environ:
            os.environ[key] = value
            introduced.append(key)

    engine_module._limiter_engine = None

    try:
        yield
    finally:
        if engine_module._limiter_engine is not None:
            engine_module._limiter_engine.dispose()
        engine_module._limiter_engine = None

        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        for key in introduced:
            os.environ.pop(key, None)


def _counter_count(engine: Engine, *, scope: str, key: str) -> int | None:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT count FROM rate_limit_counter WHERE scope = :scope AND key = :key"),
            {"scope": scope, "key": key},
        ).scalar_one_or_none()


# --- TC-SEC-024 ----------------------------------------------------------------


def test_counter_increment_survives_surrounding_request_rollback(
    db_engine: Engine, truncate_tables
) -> None:
    """TC-SEC-024: force a request that increments the limiter counter,
    then let the surrounding request fail/rollback — the increment must
    persist (dedicated AUTOCOMMIT connection, never rolled back with the
    request)."""
    from sqlalchemy.orm import Session as SqlAlchemySession

    key = "tc-sec-024-client"

    # Simulate "the surrounding request": its own Session/transaction,
    # exactly like `app.db.session.get_session()` hands a route.
    request_session = SqlAlchemySession(bind=db_engine, expire_on_commit=False)
    try:
        # The limiter check happens *inside* this simulated request, on its
        # own dedicated AUTOCOMMIT engine — never `request_session`.
        result = limiter_service.check_and_increment(
            scope=_SCOPE,
            key=key,
            limit=20,
            window_seconds=60,
            now=datetime.now(UTC),
        )
        assert result.count == 1

        # The "request" now fails and its own transaction is rolled back —
        # this must not touch the limiter's already-committed increment.
        request_session.rollback()
    finally:
        request_session.close()

    persisted_count = _counter_count(db_engine, scope=_SCOPE, key=key)
    assert persisted_count == 1

    truncate_tables()


# --- Basic mechanism correctness -----------------------------------------------


def test_check_and_increment_allows_up_to_limit_then_refuses(truncate_tables) -> None:
    key = "mechanism-check-client"
    now = datetime.now(UTC)

    for expected_count in range(1, 4):
        result = limiter_service.check_and_increment(
            scope=_SCOPE, key=key, limit=3, window_seconds=60, now=now
        )
        assert result.count == expected_count
        assert result.allowed is True

    over_limit = limiter_service.check_and_increment(
        scope=_SCOPE, key=key, limit=3, window_seconds=60, now=now
    )
    assert over_limit.count == 4
    assert over_limit.allowed is False
    assert over_limit.retry_after_seconds >= 1

    truncate_tables()


def test_check_and_increment_distinct_keys_have_independent_counters(truncate_tables) -> None:
    now = datetime.now(UTC)
    first = limiter_service.check_and_increment(
        scope=_SCOPE, key="key-a", limit=20, window_seconds=60, now=now
    )
    second = limiter_service.check_and_increment(
        scope=_SCOPE, key="key-b", limit=20, window_seconds=60, now=now
    )

    assert first.count == 1
    assert second.count == 1

    truncate_tables()
