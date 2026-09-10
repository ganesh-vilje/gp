"""Integration tests for the append-only guard (app/db/guard.py).

TC-SEC-018 (threat #14, BR-008): an `UPDATE`/`DELETE` at the ORM layer
against each of the three append-only tables (`complaint_status_history`,
`complaint_edit_history`, `security_event`) raises before reaching the
database.
TC-SEC-006 ORM-half (AC-016, BR-008, "raises at the data-access layer"):
same guarantee for a `session.delete(obj)` flush path on a real history
row created via the factory, plus the control proving `UPDATE` on
`complaint` itself (not one of the three append-only tables) is allowed.

"No statement reached the DB" is proven with a `before_cursor_execute`
counter bound to the exact `Connection` `db_session` uses (test-strategy.md
§3 "Query-counter fixture") — the guard's `before_execute` listener must
raise ahead of that event ever firing.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from app.core.errors import AppendOnlyViolation
from app.db.models import (
    ClerkAccount,
    Complaint,
    ComplaintEditHistory,
    ComplaintStatusHistory,
    SecurityEvent,
)
from sqlalchemy import delete, event, text, update
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


@pytest.fixture
def cursor_execute_count(db_session: Session) -> Iterator[Callable[[], int]]:
    """Counts `before_cursor_execute` events on `db_session`'s own
    connection, so a test can assert the guard raised strictly before any
    statement reached the database driver."""
    counts = {"n": 0}
    connection = db_session.connection()

    def _listener(*_args: object, **_kwargs: object) -> None:
        counts["n"] += 1

    event.listen(connection, "before_cursor_execute", _listener)
    try:
        yield lambda: counts["n"]
    finally:
        event.remove(connection, "before_cursor_execute", _listener)


@pytest.fixture
def cursor_statements(db_session: Session) -> Iterator[Callable[[], list[str]]]:
    """Query-counter fixture (test-strategy.md §3): collects the raw SQL
    text of every statement that reaches the database driver on
    `db_session`'s own connection, so a test can assert a specific
    table/verb never appeared — stronger than a bare count, which a SAVEPOINT
    issued by `flush()`'s own transaction-control machinery would also move.
    """
    statements: list[str] = []
    connection = db_session.connection()

    def _listener(_conn: object, _cursor: object, statement: str, *_rest: object) -> None:
        statements.append(statement)

    event.listen(connection, "before_cursor_execute", _listener)
    try:
        yield lambda: list(statements)
    finally:
        event.remove(connection, "before_cursor_execute", _listener)


@pytest.mark.parametrize(
    ("model", "update_values"),
    [
        (ComplaintStatusHistory, {"note": "attempted edit"}),
        (ComplaintEditHistory, {"new_value": "attempted edit"}),
        (SecurityEvent, {"reason_code": "attempted_edit"}),
    ],
    ids=[
        ComplaintStatusHistory.__tablename__,
        ComplaintEditHistory.__tablename__,
        SecurityEvent.__tablename__,
    ],
)
def test_update_append_only_table_raises_before_reaching_db(
    db_session: Session,
    cursor_execute_count: Callable[[], int],
    model: type,
    update_values: dict[str, str],
) -> None:
    stmt = update(model).where(model.id == 999_999).values(**update_values)

    with pytest.raises(AppendOnlyViolation):
        db_session.execute(stmt)

    assert cursor_execute_count() == 0


@pytest.mark.parametrize(
    "model",
    [ComplaintStatusHistory, ComplaintEditHistory, SecurityEvent],
    ids=lambda model: model.__tablename__,
)
def test_delete_append_only_table_raises_before_reaching_db(
    db_session: Session,
    cursor_execute_count: Callable[[], int],
    model: type,
) -> None:
    stmt = delete(model).where(model.id == 999_999)

    with pytest.raises(AppendOnlyViolation):
        db_session.execute(stmt)

    assert cursor_execute_count() == 0


def test_session_delete_flush_on_history_row_raises(
    db_session: Session,
    cursor_statements: Callable[[], list[str]],
    make_clerk: Callable[..., ClerkAccount],
    make_complaint: Callable[..., Complaint],
) -> None:
    """TC-SEC-006 ORM-half: `session.delete(obj)` + `flush()` on a real
    `complaint_status_history` row (created via the factory path) raises
    the same guard, and no `DELETE ... complaint_status_history` statement
    reaches the database (a SAVEPOINT statement from flush()'s own
    transaction-control machinery is allowed — only the guarded DML is
    asserted against)."""
    clerk = make_clerk()
    complaint = make_complaint(created_by=clerk.id)
    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        previous_status="new",
        new_status="in_progress",
        actor_id=clerk.id,
    )
    db_session.add(history)
    db_session.flush()
    baseline = len(cursor_statements())

    db_session.delete(history)
    with pytest.raises(AppendOnlyViolation):
        db_session.flush()

    new_statements = cursor_statements()[baseline:]
    assert not any("complaint_status_history" in stmt.lower() for stmt in new_statements)


def _make_history_row(
    db_session: Session, model: type, complaint: Complaint, clerk: ClerkAccount
) -> ComplaintStatusHistory | ComplaintEditHistory | SecurityEvent:
    """Ad hoc factory (not a named fixture — F2 rework) for one row of
    whichever append-only model is under test."""
    row: ComplaintStatusHistory | ComplaintEditHistory | SecurityEvent
    if model is ComplaintStatusHistory:
        row = ComplaintStatusHistory(
            complaint_id=complaint.id,
            previous_status="new",
            new_status="in_progress",
            actor_id=clerk.id,
        )
    elif model is ComplaintEditHistory:
        row = ComplaintEditHistory(
            complaint_id=complaint.id,
            field_name="citizen_name",
            previous_value="Old Synthetic Name",
            new_value="New Synthetic Name",
            actor_id=clerk.id,
        )
    else:
        row = SecurityEvent(event_type="login_success")
    db_session.add(row)
    db_session.flush()
    return row


@pytest.mark.parametrize(
    ("model", "attribute", "value"),
    [
        (ComplaintStatusHistory, "note", "tampered"),
        (ComplaintEditHistory, "new_value", "tampered"),
        (SecurityEvent, "reason_code", "tampered"),
    ],
    ids=[
        ComplaintStatusHistory.__tablename__,
        ComplaintEditHistory.__tablename__,
        SecurityEvent.__tablename__,
    ],
)
def test_mutate_attribute_flush_on_history_row_raises(
    db_session: Session,
    cursor_statements: Callable[[], list[str]],
    make_clerk: Callable[..., ClerkAccount],
    make_complaint: Callable[..., Complaint],
    model: type,
    attribute: str,
    value: str,
) -> None:
    """F2 (code-reviewer rework): fetch/hold a history/security_event row
    created via the factory path, mutate one attribute on the persistent
    ORM object (not `session.delete`), and `flush()` must raise before any
    `UPDATE` for that table reaches the database."""
    clerk = make_clerk()
    complaint = make_complaint(created_by=clerk.id)
    row = _make_history_row(db_session, model, complaint, clerk)
    baseline = len(cursor_statements())

    setattr(row, attribute, value)
    with pytest.raises(AppendOnlyViolation):
        db_session.flush()

    new_statements = cursor_statements()[baseline:]
    assert not any(model.__tablename__ in stmt.lower() for stmt in new_statements)


@pytest.mark.parametrize(
    "table_name",
    ["complaint_status_history", "complaint_edit_history", "security_event"],
)
def test_raw_text_update_append_only_table_raises_before_reaching_db(
    db_session: Session,
    cursor_execute_count: Callable[[], int],
    table_name: str,
) -> None:
    """F1 (code-reviewer rework): a hand-written `text()` UPDATE — which
    never compiles to a `sqlalchemy.sql.dml.Update` object — is still
    caught, by the guard's regex-on-template defense-in-depth layer."""
    stmt = text(f"UPDATE {table_name} SET id = id WHERE id = :id")  # noqa: S608

    with pytest.raises(AppendOnlyViolation):
        db_session.execute(stmt, {"id": 999_999})

    assert cursor_execute_count() == 0


@pytest.mark.parametrize(
    "table_name",
    ["complaint_status_history", "complaint_edit_history", "security_event"],
)
def test_raw_text_delete_append_only_table_raises_before_reaching_db(
    db_session: Session,
    cursor_execute_count: Callable[[], int],
    table_name: str,
) -> None:
    stmt = text(f"DELETE FROM {table_name} WHERE id = :id")  # noqa: S608

    with pytest.raises(AppendOnlyViolation):
        db_session.execute(stmt, {"id": 999_999})

    assert cursor_execute_count() == 0


@pytest.mark.parametrize(
    "table_name",
    ["complaint_status_history", "complaint_edit_history", "security_event"],
)
def test_raw_text_select_append_only_table_is_allowed(
    db_session: Session,
    table_name: str,
) -> None:
    """A `text()` SELECT is not a mutation — the regex layer must not
    false-positive on reads of the same tables."""
    stmt = text(f"SELECT id FROM {table_name} WHERE id = :id")  # noqa: S608

    result = db_session.execute(stmt, {"id": 999_999})

    assert result.fetchall() == []


def test_raw_text_update_complaint_is_allowed(
    db_session: Session,
    make_clerk: Callable[..., ClerkAccount],
    make_complaint: Callable[..., Complaint],
) -> None:
    """Control: a `text()` UPDATE against `complaint` (not append-only)
    must succeed, not raise."""
    clerk = make_clerk()
    complaint = make_complaint(created_by=clerk.id, status="new")
    stmt = text("UPDATE complaint SET status = 'in_progress' WHERE id = :id")

    result = db_session.execute(stmt, {"id": complaint.id})

    assert result.rowcount == 1


def test_update_complaint_is_allowed(
    db_session: Session,
    make_clerk: Callable[..., ClerkAccount],
    make_complaint: Callable[..., Complaint],
) -> None:
    """Control: `complaint` is not one of the three append-only tables — an
    `UPDATE` against it must succeed, not raise."""
    clerk = make_clerk()
    complaint = make_complaint(created_by=clerk.id, status="new")

    stmt = update(Complaint).where(Complaint.id == complaint.id).values(status="in_progress")
    result = db_session.execute(stmt)

    assert result.rowcount == 1
