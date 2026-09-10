"""The append-only guard's regex layer (layer 2, app/db/guard.py) must
never run for `Select`/`CompoundSelect`/`Insert` constructs
(performance-scalability rework): these are the two hottest statement
types by request volume and neither can ever be an `UPDATE`/`DELETE`, so
paying the `str(clauseelement)` compile + regex cost for them on every
request is needless.

`re.Pattern` is a C-level object whose `.search` attribute is read-only, so
the module-level compiled pattern itself is replaced (not one of its
attributes) for the duration of each test.
"""

from __future__ import annotations

from unittest.mock import patch

from app.db import guard
from app.db.models import ClerkAccount
from sqlalchemy import insert, select, union


def test_select_never_reaches_regex_layer() -> None:
    stmt = select(ClerkAccount)

    with patch.object(guard, "_RAW_SQL_MUTATION_PATTERN") as mock_pattern:
        guard._raise_if_append_only_mutation(None, stmt, None, None, None)

    mock_pattern.search.assert_not_called()


def test_insert_never_reaches_regex_layer() -> None:
    stmt = insert(ClerkAccount)

    with patch.object(guard, "_RAW_SQL_MUTATION_PATTERN") as mock_pattern:
        guard._raise_if_append_only_mutation(None, stmt, None, None, None)

    mock_pattern.search.assert_not_called()


def test_compound_select_never_reaches_regex_layer() -> None:
    stmt = union(select(ClerkAccount), select(ClerkAccount))

    with patch.object(guard, "_RAW_SQL_MUTATION_PATTERN") as mock_pattern:
        guard._raise_if_append_only_mutation(None, stmt, None, None, None)

    mock_pattern.search.assert_not_called()
