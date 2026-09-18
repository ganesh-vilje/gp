"""Append-only enforcement guard (schema.md § Audit / append-only
enforcement, backend-architecture.md §9, BR-008).

Registers a `before_execute` listener on a given `Engine`. `before_execute`
fires for every `Connection.execute()` call. Two layers of matching, both
inside this one listener:

1. **Precise:** an ORM/Core `update()`/`delete()` construct — a
   hand-written one or the statements the ORM unit-of-work flush emits for
   `session.delete(obj)`/`session.execute(update(Model)...)`/attribute
   mutation on a persistent history row — is matched by inspecting the
   *compiled statement construct* (`clauseelement.table.name`), never
   user-supplied data.
2. **Defense-in-depth, regex on the statement template:** a hand-written
   `text()` construct (e.g. `session.execute(text("UPDATE security_event
   ..."))`) does not compile to an `Update`/`Delete` object, so layer 1
   cannot see it. `Select`/`CompoundSelect`/`Insert` constructs are excluded
   before this layer runs (performance-scalability rework): they are the two
   hottest statement types by request volume, neither can ever be an
   `UPDATE`/`DELETE`, and this layer's `str(clauseelement)` compile is real
   per-statement cost not worth paying for them. Every remaining
   `ClauseElement` — `text()`, and any future/unknown clause type as a
   fail-closed default — has its statement **template** rendered —
   `str(clauseelement)`, which is the SQL text with bind-parameter
   placeholders (`:name`), never the bound *values* — and matched against a
   conservative, case-insensitive regex for `UPDATE`/`DELETE FROM`/`TRUNCATE`
   followed anywhere by one of the three table names. This never inspects
   bound parameters, so no citizen/clerk data is ever pattern-matched.

Both layers raise before the statement reaches the database — `before_execute`
fires strictly ahead of `before_cursor_execute`, so nothing is sent to the
server.

**What this runtime guard does NOT cover:** `Connection.exec_driver_sql()`
and a raw DBAPI `.cursor()` obtained via `Connection.connection`/`.driver_connection`
both skip SQLAlchemy's Core execute-event pipeline entirely — no
`before_execute` fires for either. Those are prevented statically instead,
by `tests/unit/test_no_raw_sql_bypass.py` (an `ast` walk of `app/`) and by
the mirroring grep in T-016's CI job — not by this module.

Primary layer only — the belt-and-braces DB-level `REVOKE` is TD-B04 (see
migrations/versions/0001_initial.py's comment ahead of `upgrade()`).
"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.sql import ClauseElement
from sqlalchemy.sql.dml import Delete, Insert, Update
from sqlalchemy.sql.selectable import CompoundSelect, Select

from app.core.errors import AppendOnlyViolation

APPEND_ONLY_TABLES = frozenset(
    {"complaint_status_history", "complaint_edit_history", "security_event"}
)

# Never a mutation, and the two hottest statement types by request volume —
# skipped before the layer-2 regex compile (performance-scalability rework).
_NEVER_A_MUTATION_CLAUSE_TYPES = (Select, CompoundSelect, Insert)

# Defense-in-depth only (layer 2 above): matched against the statement
# *template* (bind-parameter placeholders, never bound values).
_RAW_SQL_MUTATION_PATTERN = re.compile(
    r"\b(update|delete\s+from|truncate)\b[\s\S]*\b"
    r"(complaint_status_history|complaint_edit_history|security_event)\b",
    re.IGNORECASE,
)


def _raise_if_append_only_mutation(
    conn: Connection,
    clauseelement: ClauseElement,
    multiparams: Any,
    params: Any,
    execution_options: Any,
) -> None:
    if isinstance(clauseelement, (Update, Delete)):
        table = clauseelement.table
        table_name = getattr(table, "name", None)
        if table_name in APPEND_ONLY_TABLES:
            verb = "UPDATE" if isinstance(clauseelement, Update) else "DELETE"
            raise AppendOnlyViolation(
                f"{verb} against append-only table {table_name!r} is forbidden (BR-008)."
            )
        return

    if isinstance(clauseelement, _NEVER_A_MUTATION_CLAUSE_TYPES):
        return

    # Layer 2: a text()/other ClauseElement. `str(...)` renders the
    # statement template only — SQLAlchemy's default compilation uses
    # placeholders for bind parameters, never literal bound values.
    try:
        statement_template = str(clauseelement)
    except Exception:  # pragma: no cover - defensive; unrenderable clause
        return
    if _RAW_SQL_MUTATION_PATTERN.search(statement_template):
        raise AppendOnlyViolation(
            "Raw SQL mutation against an append-only table "
            f"{sorted(APPEND_ONLY_TABLES)!r} is forbidden (BR-008): "
            f"{statement_template!r}"
        )


def register_append_only_guard(engine: Engine) -> None:
    """Attach the append-only guard's `before_execute` listener to `engine`.

    Called on the request engine in production (`app/db/engine.py`) and on
    the integration-test engine in `tests/conftest.py`, so both the real
    app and the test suite exercise the same enforcement.
    """
    event.listen(engine, "before_execute", _raise_if_append_only_mutation)
