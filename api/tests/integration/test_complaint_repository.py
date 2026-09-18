"""Integration tests for `app.db.repositories.complaint` (T-018 rework,
security-review F2).
"""

from __future__ import annotations

from collections.abc import Callable

import pytest
from app.db.models.complaint import Complaint
from app.db.repositories import complaint as complaint_repo
from sqlalchemy import text
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration


def test_get_by_id_for_update_refreshes_a_stale_identity_map_entry(
    db_session: Session, make_complaint: Callable[..., Complaint]
) -> None:
    """F2 (security-review, T-018 rework): if `complaint_id` is already in
    this `Session`'s identity map from an earlier plain read, a later
    `get_by_id_for_update` call must still return the row's *current*
    committed status — not the stale in-memory instance — or the "validate
    against the current, post-lock status" safety property silently breaks.

    Simulates "current status changed since this session first read the
    row" with a raw `UPDATE` (bypassing the ORM's own change-tracking, the
    same way a truly concurrent, separately-committed transaction would)
    and asserts the locked re-read observes the new value.
    """
    complaint = make_complaint(status="in_progress")
    db_session.flush()

    # First, ordinary (unlocked) read — this is what populates the identity
    # map with the pre-change instance.
    stale = complaint_repo.get_by_id(db_session, complaint.id)
    assert stale is not None
    assert stale.status == "in_progress"

    # Mutate the row directly via SQL, bypassing the ORM instance already in
    # the identity map (standing in for a status change some other
    # transaction committed between the stale read above and the locked
    # read below).
    db_session.execute(
        text("UPDATE complaint SET status = 'resolved' WHERE id = :id"),
        {"id": complaint.id},
    )

    locked = complaint_repo.get_by_id_for_update(db_session, complaint.id)
    assert locked is not None
    assert locked.status == "resolved", (
        "get_by_id_for_update returned the stale identity-map instance "
        "instead of refreshing it from the row it just locked — "
        "populate_existing=True regressed."
    )
    # And the identity-mapped stale reference itself is refreshed too (same
    # Python object, same identity-map slot).
    assert stale.status == "resolved"
