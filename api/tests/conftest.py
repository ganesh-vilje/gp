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

T-006a adds (test-strategy.md §3): `live_server` (a real `uvicorn.Server` on
a background thread, OS-assigned port); `truncate_tables` (explicit cleanup
for rows committed for real through `live_server`); `query_counter` (a
`before_cursor_execute` listener collecting touched tables); and
`seeded_accounts`/`live_seeded_accounts` (`admin_test`/`clerk_test`, created
through `bootstrap_admin`/the ORM factory — never a raw INSERT).
"""

from __future__ import annotations

import os
import re
import secrets
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx
import pytest
import uvicorn
from alembic import command
from alembic.config import Config
from app.cli.bootstrap_admin import bootstrap_admin
from app.db import engine as engine_module
from app.db.guard import register_append_only_guard
from app.db.models import ClerkAccount, Complaint
from app.db.models.session import Session as SessionRow
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Connection, Engine, make_url
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
    silently falls back to a guessed database.

    F3 (security-review, T-018 rework): the `ENVIRONMENT` check now applies
    to *both* the explicit-`TEST_DATABASE_URL` path and the derived-default
    path — an explicit `TEST_DATABASE_URL` no longer skips it — and,
    regardless of which path produced `url`, the resolved database name must
    be `panchayat_test` (or otherwise end with `_test`) or this raises. This
    module's fixtures use `Connection.exec_driver_sql` to `DELETE` from the
    three append-only tables for test teardown (a documented, test-only
    bypass of `app/db/guard.py`); both checks together are the only thing
    standing between that bypass and a real (non-`_test`) database, so a
    failure here must always raise loudly, never proceed.

    Pure/no I/O: safe to call at collection time.
    """
    environment = os.environ.get("ENVIRONMENT")
    if environment not in (None, "", "test", "dev"):
        raise RuntimeError(
            "Refusing to resolve a test database URL: ENVIRONMENT="
            f"{environment!r} is not one that may run integration tests "
            "(expected unset, 'test', or 'dev') — this check applies "
            "whether or not TEST_DATABASE_URL is set explicitly."
        )

    explicit = os.environ.get("TEST_DATABASE_URL")
    url = explicit if explicit else _DEFAULT_TEST_DATABASE_URL

    database_name = make_url(url).database
    if database_name != "panchayat_test" and not (database_name or "").endswith("_test"):
        raise RuntimeError(
            "Refusing to run integration tests against database "
            f"{database_name!r} — TEST_DATABASE_URL (or the default) must "
            "resolve to 'panchayat_test' or another name ending in '_test'. "
            "This guards the test-only append-only-table DELETE bypass in "
            "this file from ever running against a real database."
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


# --- T-006a: live_server, query_counter, seeded accounts -------------------

# Non-append-only tables, in FK-safe delete order (children before the
# `clerk_account` parent they reference; `complaint.created_by` is
# `ondelete="RESTRICT"` so it must go before `clerk_account`, and `session
# .user_id` is `ondelete="CASCADE"` but is deleted explicitly anyway for
# clarity). The three append-only tables (`complaint_status_history`,
# `complaint_edit_history`, `security_event`) are never listed here — the
# guard registered on `db_engine` would raise (BR-008) — they are cleared
# separately, below, via a documented bypass.
_TRUNCATE_ORDER: tuple[str, ...] = ("session", "complaint", "rate_limit_counter", "clerk_account")

# The three append-only tables, child-before-parent order (both history
# tables reference `complaint`/`clerk_account` with `ondelete="RESTRICT"`,
# so they must be cleared before `_TRUNCATE_ORDER`'s `complaint`/
# `clerk_account` rows, or that DELETE fails on the FK). Cleared via
# `Connection.exec_driver_sql` (T-018), the one documented, test-only
# bypass of `app/db/guard.py`'s `before_execute` hook (its own docstring:
# "What this runtime guard does NOT cover") — legitimate here only because
# this is test-isolation cleanup, not application code (the static
# `tests/unit/test_no_raw_sql_bypass.py` check that forbids this pattern is
# scoped to `app/`, not `tests/`).
_APPEND_ONLY_TRUNCATE_ORDER: tuple[str, ...] = (
    "complaint_status_history",
    "complaint_edit_history",
    "security_event",
)


def _env_setdefault(key: str, value: str) -> bool:
    """Like `os.environ.setdefault`, but reports whether it introduced the
    value (so the caller pops it, rather than merely restoring, at
    teardown) — an ambient value already set for this key is left alone."""
    if key in os.environ:
        return False
    os.environ[key] = value
    return True


@dataclass
class _LiveServerEnv:
    """What `_live_server_set_env` changed, so `_live_server_cleanup` can
    undo exactly that (never guess) regardless of which path got there."""

    previous_database_url: str | None
    introduced_keys: list[str]


def _live_server_set_env() -> _LiveServerEnv:
    """F1 (code-reviewer rework): factored out of the fixture body so it —
    and its paired `_live_server_cleanup` below — can be exercised directly
    by a plain (non-fixture) test with no real server involved.

    `DATABASE_URL` is always pointed at `resolve_test_database_url()`
    (restored unconditionally in `_live_server_cleanup`, regardless of any
    ambient value — never let a live HTTP server reach `panchayat`).
    `ENVIRONMENT`/`SECRET_KEY`/`USERNAME_HASH_SALT`/`ALLOWED_ORIGINS`/
    `ALLOWED_HOSTS` are set only if not already present.
    """
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = resolve_test_database_url()

    introduced_keys = [
        key
        for key, value in (
            ("ENVIRONMENT", "test"),
            ("SECRET_KEY", secrets.token_urlsafe(32)),
            ("USERNAME_HASH_SALT", secrets.token_urlsafe(32)),
            ("ALLOWED_ORIGINS", "https://example.test"),
            ("ALLOWED_HOSTS", "127.0.0.1,localhost,testserver"),
        )
        if _env_setdefault(key, value)
    ]
    return _LiveServerEnv(previous_database_url, introduced_keys)


def _live_server_cleanup(
    server: uvicorn.Server | None, thread: threading.Thread | None, env: _LiveServerEnv
) -> None:
    """F1 (code-reviewer rework): the one cleanup routine `live_server` runs
    on *every* exit path (a raise during setup, or the normal
    yield/teardown path) — stop/join the server thread (if it was ever
    started), dispose and reset the memoised request engine, then restore
    the environment `_live_server_set_env` changed. `server`/`thread` are
    `None` when setup raised before either was created (e.g. `create_app()`
    itself failing) — nothing to stop in that case."""
    if server is not None:
        server.should_exit = True
    if thread is not None:
        thread.join(timeout=5.0)

    if engine_module._request_engine is not None:
        engine_module._request_engine.dispose()
    engine_module._request_engine = None

    if env.previous_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = env.previous_database_url
    for key in env.introduced_keys:
        os.environ.pop(key, None)


def _wait_for_server_started(server: uvicorn.Server, *, timeout: float) -> None:
    """Poll `server.started` until it flips `True` or `timeout` elapses.

    Factored out (F1 code-reviewer rework) so the startup-timeout path —
    `server.started` never flipping — is directly exercisable by a plain
    unit test with a fake `server` object, no real uvicorn/thread involved.
    """
    deadline = time.monotonic() + timeout
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)
    if not server.started:
        raise RuntimeError(f"live_server: uvicorn did not report started within {timeout}s")


@pytest.fixture(scope="module")
def live_server() -> Iterator[str]:
    """Runs the real app (`create_app()`) under a real `uvicorn.Server` in a
    background thread, bound to `127.0.0.1` on an OS-assigned port (port 0),
    and yields its base URL once `/healthz` answers 200.

    Module-scoped, not function-scoped: starting/stopping a real uvicorn
    server pays real wall-clock cost (socket bind, thread start, graceful
    shutdown) that per-test would dominate a module's run time; module scope
    pays it once per test *file* while still bounding this fixture's
    environment-variable overrides (below) to that one file. Not
    session-scoped: test-strategy.md §3 sizes this fixture for "only the
    tests that need it" (real concurrent connections/a real HTTP target),
    and a suite-wide shared server would let one module's overrides leak
    into every other module that also uses `live_server`.

    `DATABASE_URL` is always pointed at `resolve_test_database_url()` for
    the fixture's duration (restored after), regardless of any ambient
    value — this is the one override that is a safety property, not a
    convenience default (never let a live HTTP server started by tests
    reach the `panchayat` dev database). `ENVIRONMENT`/`SECRET_KEY`/
    `USERNAME_HASH_SALT`/`ALLOWED_ORIGINS`/`ALLOWED_HOSTS` are set only if
    not already present in the environment, per this task's design
    constraints.

    `app.db.engine.get_engine()` memoises its engine at module scope inside
    `app/db/engine.py`; this fixture resets that module attribute directly
    (a test-only technique — never done from `app/` code) so the request
    engine the running app actually uses is always freshly built against
    the test database, never a stale singleton from an earlier module.

    **Real commits, no rollback:** every request made through this
    fixture's base URL is handled by the app's own request engine on its
    own connection/transaction and COMMITs for real — it is never rolled
    back by `db_session`'s SAVEPOINT machinery. A test using `live_server`
    must clean up explicitly with the `truncate_tables` fixture. Note the
    one thing `truncate_tables` cannot do: a test that creates rows in the
    three append-only tables through the live server has no cleanup path
    here (the guard forbids `DELETE`/`UPDATE`/`TRUNCATE` against them) —
    that case is deliberately out of scope for T-006a and is left to
    T-009+.
    """
    env = _live_server_set_env()
    # Test-only reset (see docstring): force a fresh request engine bound to
    # the test database, never one memoised by an earlier module.
    engine_module._request_engine = None

    server: uvicorn.Server | None = None
    thread: threading.Thread | None = None
    try:
        # Imported here, not at module scope: `app.main` builds its
        # module-level `app = create_app()` at import time (required so
        # `uvicorn app.main:app` works without `--factory`), which calls
        # `get_settings()` immediately — importing it before the env vars
        # above are set would fail closed.
        from app.main import create_app

        app = create_app()
        config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        _wait_for_server_started(server, timeout=5.0)

        port = server.servers[0].sockets[0].getsockname()[1]
        base_url = f"http://127.0.0.1:{port}"

        last_error: Exception | None = None
        healthy = False
        healthz_deadline = time.monotonic() + 5.0
        while time.monotonic() < healthz_deadline:
            try:
                response = httpx.get(f"{base_url}/healthz", timeout=1.0)
            except httpx.HTTPError as exc:
                last_error = exc
            else:
                if response.status_code == 200:
                    healthy = True
                    break
            time.sleep(0.05)

        if not healthy:
            raise RuntimeError(f"live_server: /healthz never answered 200 ({last_error})")
    except Exception:
        # F1 (code-reviewer rework): a raise anywhere during setup above —
        # uvicorn never reporting `started`, or `/healthz` never answering —
        # must still run the exact same cleanup as the normal path below
        # (stop/join the thread, dispose/reset the engine, restore env vars)
        # before propagating, never leaving a thread running or an env var
        # leaked into the next module.
        _live_server_cleanup(server, thread, env)
        raise

    try:
        yield base_url
    finally:
        _live_server_cleanup(server, thread, env)


@pytest.fixture
def truncate_tables(db_engine: Engine) -> Iterator[Callable[[], None]]:
    """Yields a callable that deletes every row from the four
    non-append-only tables, in FK-safe order (`_TRUNCATE_ORDER`) — never
    from `complaint_status_history`/`complaint_edit_history`/
    `security_event` (the guard registered on `db_engine` would raise).

    Also runs once more at teardown regardless of whether the test called
    it, so `panchayat_test` is left empty after every test that requests
    this fixture (directly, or via `live_seeded_accounts`) — the
    Environment note's "leave panchayat_test empty after the run."
    """

    def _truncate() -> None:
        with db_engine.begin() as connection:
            for table in _APPEND_ONLY_TRUNCATE_ORDER:
                # exec_driver_sql bypasses app/db/guard.py's before_execute
                # hook (see _APPEND_ONLY_TRUNCATE_ORDER's comment) — this is
                # test-isolation cleanup, never application code.
                connection.exec_driver_sql(f"DELETE FROM {table}")  # noqa: S608 - fixed table names
            for table in _TRUNCATE_ORDER:
                connection.execute(text(f"DELETE FROM {table}"))  # noqa: S608 - fixed table names

    try:
        yield _truncate
    finally:
        _truncate()


# F2 (code-reviewer note, T-006a): scans the raw statement *text* only —
# bound values are placeholders (`:name`/`%(name)s`), never inlined
# literals, for every statement this repo's own code emits (ORM/Core
# constructs, `text()` with bound params). It does not strip *string
# literals* out of the statement first, so a hand-written `text()` query
# that inlines a table-shaped word inside a quoted literal could false-
# positive. Harmless today (no test does that); T-009/T-010 lean on this
# fixture harder (AC-018) and should add literal-stripping before then if
# a real query ever needs one.
_TOUCHED_TABLE_PATTERN = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE)\s+\"?([A-Za-z_][A-Za-z0-9_]*)\"?",
    re.IGNORECASE,
)


@dataclass
class QueryCounter:
    """`.statements`: raw SQL text of every statement counted so far.
    `.touched_tables`: table names parsed from `FROM`/`JOIN`/`INTO`/
    `UPDATE` targets via a conservative regex over the statement text
    (test-strategy.md §3) — used by AC-018's "not touched" assertions and
    the anonymous `GET /api/session` zero-SQL assertion."""

    statements: list[str] = field(default_factory=list)
    touched_tables: set[str] = field(default_factory=set)

    def reset(self) -> None:
        self.statements.clear()
        self.touched_tables.clear()


@pytest.fixture
def query_counter(request: pytest.FixtureRequest) -> Iterator[QueryCounter]:
    """Collects every SQL statement executed during this test, on whichever
    of `db_session`'s own connection / the app's request engine this test
    also uses (test-strategy.md §3): if the test also requests `db_session`
    (directly, or transitively via `make_clerk`/`make_complaint`/
    `seeded_accounts`/etc.), its connection is counted; if the test also
    requests `live_server`, the app's request engine (built fresh by that
    fixture against the test database) is counted too — so a request made
    through `live_server` is counted exactly like a `db_session` query.
    Removed at teardown either way.
    """
    counter = QueryCounter()

    def _listener(
        _conn: Connection,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        counter.statements.append(statement)
        for match in _TOUCHED_TABLE_PATTERN.finditer(statement):
            counter.touched_tables.add(match.group(1).lower())

    listened_targets: list[Connection | Engine] = []

    if "db_session" in request.fixturenames:
        session = request.getfixturevalue("db_session")
        connection = session.connection()
        event.listen(connection, "before_cursor_execute", _listener)
        listened_targets.append(connection)

    if "live_server" in request.fixturenames:
        request.getfixturevalue("live_server")
        engine = engine_module.get_engine()
        event.listen(engine, "before_cursor_execute", _listener)
        listened_targets.append(engine)

    try:
        yield counter
    finally:
        for target in listened_targets:
            event.remove(target, "before_cursor_execute", _listener)


@dataclass(frozen=True)
class SeededAccounts:
    """`admin_test`/`clerk_test`, created via the bootstrap/account-creation
    code path (never a raw INSERT) — the plaintext passwords are returned
    alongside the rows so a test can call `services.auth.login` with them."""

    admin_username: str
    admin_password: str
    admin_clerk: ClerkAccount
    clerk_username: str
    clerk_password: str
    clerk: ClerkAccount


_ADMIN_TEST_USERNAME = "admin_test"
_ADMIN_TEST_PASSWORD = "Synthetic Admin Passphrase One"
_CLERK_TEST_USERNAME = "clerk_test"
_CLERK_TEST_PASSWORD = "Synthetic Clerk Passphrase Two"


def _seed_accounts(session: Session) -> SeededAccounts:
    """Shared by `seeded_accounts` (rollback `db_session`) and
    `live_seeded_accounts` (a real, committed session) — both call this so
    neither path duplicates the account-creation logic."""
    admin_result = bootstrap_admin(
        session, _ADMIN_TEST_USERNAME, _ADMIN_TEST_PASSWORD, must_change_password=False
    )
    if not admin_result.created or admin_result.clerk_id is None:
        raise RuntimeError(
            "seeded_accounts: bootstrap_admin did not create admin_test — an "
            "admin clerk already existed on this session, which should never "
            "happen on a fresh rollback/live session."
        )
    admin_clerk = session.get(ClerkAccount, admin_result.clerk_id)
    assert admin_clerk is not None

    # TODO(T-033): switch to `services.accounts.create_clerk` once FR-017's
    # in-app account-creation service exists — there is no such service yet,
    # so this uses the `make_clerk` ORM factory with a real, known plaintext
    # password (same `hashing.hash_password` call `bootstrap_admin` itself
    # uses), never a raw INSERT.
    clerk = factories.make_clerk(
        session, username=_CLERK_TEST_USERNAME, is_admin=False, password=_CLERK_TEST_PASSWORD
    )

    return SeededAccounts(
        admin_username=_ADMIN_TEST_USERNAME,
        admin_password=_ADMIN_TEST_PASSWORD,
        admin_clerk=admin_clerk,
        clerk_username=_CLERK_TEST_USERNAME,
        clerk_password=_CLERK_TEST_PASSWORD,
        clerk=clerk,
    )


@pytest.fixture
def seeded_accounts(db_session: Session) -> SeededAccounts:
    """`admin_test`/`clerk_test` on the rollback `db_session` — rolled back
    at teardown like every other `db_session`-based fixture."""
    return _seed_accounts(db_session)


@pytest.fixture
def live_seeded_accounts(
    live_server: str, db_engine: Engine, truncate_tables: Callable[[], None]
) -> Iterator[SeededAccounts]:
    """Same two accounts as `seeded_accounts`, but committed for real
    through their own `Session` (not the SAVEPOINT-rollback `db_session`) so
    a test driving `live_server` over real HTTP can log in as them.
    `live_server`'s docstring: real commits are never rolled back — cleaned
    up via `truncate_tables` at teardown instead."""
    session = Session(bind=db_engine, expire_on_commit=False)
    try:
        accounts = _seed_accounts(session)
        session.commit()
    finally:
        session.close()

    try:
        yield accounts
    finally:
        truncate_tables()
