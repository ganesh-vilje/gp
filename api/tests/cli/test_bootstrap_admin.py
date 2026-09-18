"""`app.cli.bootstrap_admin` (T-007, FR-015, AC-019).

TC-API-130 (fresh deployment -> exactly one admin clerk exists) and
TC-API-132 (second run -> no duplicate, first row unchanged) both call the
`bootstrap_admin()` callable directly against the per-test rollback
`db_session` fixture (self-contained: no fixture/migration/raw INSERT
seeds an admin ahead of time). `main()` is exercised separately for the
argparse/TTY/env-var wrapper behaviour, with `get_session` patched to
yield that same `db_session` so `main()`-level tests still run inside the
test's own rolled-back transaction.

(TC-API-131 - logging in as the bootstrapped admin and using FR-017/FR-018
- belongs to T-033 per the task row and is not in scope here.)
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from app.cli import bootstrap_admin as cli
from app.db.models.clerk_account import ClerkAccount
from sqlalchemy import event
from sqlalchemy.orm import Session

_STRONG_PASSWORD = "Correct Horse Battery 42"
_WEAK_PASSWORD = "short"


def _admin_rows(db_session: Session) -> list[ClerkAccount]:
    return list(
        db_session.scalars(sa.select(ClerkAccount).where(ClerkAccount.is_admin_clerk.is_(True)))
    )


@pytest.fixture
def fake_get_session(db_session: Session):
    """A `get_session()`-shaped generator bound to the test's own
    `db_session`, for patching `app.cli.bootstrap_admin.get_session` so
    `main()` runs inside the test's rollback transaction instead of
    building a real engine from `DATABASE_URL`."""

    def _fake_get_session() -> Iterator[Session]:
        try:
            yield db_session
            db_session.commit()
        except Exception:
            db_session.rollback()
            raise

    return _fake_get_session


# --- TC-API-130 / TC-API-132: the `bootstrap_admin()` callable itself -----


@pytest.mark.integration
def test_bootstrap_admin_fresh_deployment_creates_exactly_one_admin_interactive(
    db_session: Session,
) -> None:
    """TC-API-130 (interactive path): fresh DB -> one admin clerk row,
    `must_change_password=False`."""
    result = cli.bootstrap_admin(
        db_session, "first_admin", _STRONG_PASSWORD, must_change_password=False
    )

    assert result.created is True
    rows = _admin_rows(db_session)
    assert len(rows) == 1
    assert rows[0].username == "first_admin"
    assert rows[0].must_change_password is False
    assert rows[0].is_admin_clerk is True


@pytest.mark.integration
def test_bootstrap_admin_fresh_deployment_from_env_forces_must_change_password(
    db_session: Session,
) -> None:
    """TC-API-130 (`--from-env` path): `must_change_password=True`."""
    result = cli.bootstrap_admin(
        db_session, "env_admin", _STRONG_PASSWORD, must_change_password=True
    )

    assert result.created is True
    rows = _admin_rows(db_session)
    assert len(rows) == 1
    assert rows[0].must_change_password is True


@pytest.mark.integration
def test_bootstrap_admin_second_run_is_a_no_op(db_session: Session) -> None:
    """TC-API-132: an admin already exists -> no duplicate, first row
    unchanged."""
    first = cli.bootstrap_admin(
        db_session, "first_admin", _STRONG_PASSWORD, must_change_password=False
    )
    assert first.created is True
    first_id = first.clerk_id

    second = cli.bootstrap_admin(
        db_session, "second_admin", _STRONG_PASSWORD, must_change_password=False
    )

    assert second.created is False
    assert second.clerk_id is None
    rows = _admin_rows(db_session)
    assert len(rows) == 1
    assert rows[0].id == first_id
    assert rows[0].username == "first_admin"


@pytest.mark.integration
def test_bootstrap_admin_weak_password_rejected_no_row_created(db_session: Session) -> None:
    from app.core.errors import ValidationFailed

    with pytest.raises(ValidationFailed):
        cli.bootstrap_admin(db_session, "first_admin", _WEAK_PASSWORD, must_change_password=False)

    assert _admin_rows(db_session) == []


@pytest.mark.integration
def test_bootstrap_admin_issues_advisory_lock_statement_before_existence_check(
    db_session: Session,
) -> None:
    """Review F2: `bootstrap_admin()` takes `pg_advisory_xact_lock` on the
    session before its existence check, to serialise concurrent invocations.
    A true concurrency test is not required (review note) — this captures
    the actual SQL text sent to the driver, per the query-counter fixture
    pattern in `tests/integration/test_append_only_guard.py`."""
    statements: list[str] = []
    connection = db_session.connection()

    def _listener(_conn: object, _cursor: object, statement: str, *_rest: object) -> None:
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", _listener)
    try:
        cli.bootstrap_admin(db_session, "first_admin", _STRONG_PASSWORD, must_change_password=False)
    finally:
        event.remove(connection, "before_cursor_execute", _listener)

    assert any("pg_advisory_xact_lock" in statement for statement in statements)


# --- `main()`: argparse / TTY / env-var wrapper ---------------------------


@pytest.mark.integration
def test_main_non_tty_without_from_env_refuses_exit_2(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, fake_get_session
) -> None:
    monkeypatch.setattr(cli, "get_session", fake_get_session)
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: False))

    exit_code = cli.main([])

    assert exit_code == 2
    assert _admin_rows(db_session) == []


@pytest.mark.integration
def test_main_from_env_missing_vars_exit_1(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    fake_get_session,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "get_session", fake_get_session)
    monkeypatch.delenv("BOOTSTRAP_ADMIN_USERNAME", raising=False)
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    exit_code = cli.main(["--from-env"])

    assert exit_code == 1
    assert _admin_rows(db_session) == []
    # Review F1: the "delete the env vars" reminder still prints even on
    # this early failure path (--from-env was used, regardless of outcome).
    assert "reminder" in capsys.readouterr().out


@pytest.mark.integration
def test_main_from_env_fresh_deployment_creates_admin_with_must_change_password(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, fake_get_session
) -> None:
    monkeypatch.setattr(cli, "get_session", fake_get_session)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "env_admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", _STRONG_PASSWORD)

    exit_code = cli.main(["--from-env"])

    assert exit_code == 0
    rows = _admin_rows(db_session)
    assert len(rows) == 1
    assert rows[0].username == "env_admin"
    assert rows[0].must_change_password is True


@pytest.mark.integration
def test_main_second_run_no_op_exit_0(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    fake_get_session,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "get_session", fake_get_session)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "env_admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", _STRONG_PASSWORD)

    first_exit_code = cli.main(["--from-env"])
    assert first_exit_code == 0
    capsys.readouterr()  # drain the first run's own reminder before asserting on the second

    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "second_admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", _STRONG_PASSWORD)
    second_exit_code = cli.main(["--from-env"])

    assert second_exit_code == 0
    rows = _admin_rows(db_session)
    assert len(rows) == 1
    assert rows[0].username == "env_admin"
    # Review F1: the reminder still prints on the no-op path, not only on
    # first-time creation.
    second_output = capsys.readouterr().out
    assert "reminder" in second_output
    assert "already exists" in second_output


@pytest.mark.integration
def test_main_from_env_weak_password_exit_1_prints_reminder(
    monkeypatch: pytest.MonkeyPatch,
    db_session: Session,
    fake_get_session,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Review F1: the reminder must print on this failure path too, not
    only on success."""
    monkeypatch.setattr(cli, "get_session", fake_get_session)
    monkeypatch.setenv("BOOTSTRAP_ADMIN_USERNAME", "first_admin")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", _WEAK_PASSWORD)

    exit_code = cli.main(["--from-env"])

    assert exit_code == 1
    assert _admin_rows(db_session) == []
    assert "reminder" in capsys.readouterr().out


@pytest.mark.integration
def test_main_interactive_weak_password_exit_1_no_row(
    monkeypatch: pytest.MonkeyPatch, db_session: Session, fake_get_session
) -> None:
    monkeypatch.setattr(cli, "get_session", fake_get_session)
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr("builtins.input", lambda *_a, **_kw: "first_admin")
    monkeypatch.setattr(cli.getpass, "getpass", lambda *_a, **_kw: _WEAK_PASSWORD)

    exit_code = cli.main([])

    assert exit_code == 1
    assert _admin_rows(db_session) == []


# --- layering: no router/middleware module imports app.cli ---------------

_API_DIR = Path(__file__).resolve().parents[2]
_APP_ROOT = _API_DIR / "app"


def _iter_py_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return [p for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts]


def _imports_app_cli(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app.cli" or alias.name.startswith("app.cli."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "app.cli" or module.startswith("app.cli."):
                return True
    return False


def test_no_router_or_middleware_module_imports_app_cli() -> None:
    """backend-architecture.md §12: the four CLI commands are reachable only
    via `fly ssh console`, never over HTTP — no module under `app/api/` or
    `app/middleware/` may import `app.cli`."""
    violations = []
    for subdir in ("api", "middleware"):
        for path in _iter_py_files(_APP_ROOT / subdir):
            if _imports_app_cli(path):
                violations.append(str(path))

    assert not violations, "app.cli imported from a router/middleware module:\n" + "\n".join(
        violations
    )
