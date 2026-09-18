"""Append-only INSERT for `complaint_status_history` (BR-008, T-018;
coding-guidelines.md § Layering: "Repositories: queries, row locks,
uniqueness retries, pagination. Never enforce a rule ... that is a
service's job.").

This module contains **only** an INSERT — no `UPDATE`/`DELETE` function
exists here, and none may ever be added (BR-008: `complaint_status_history`
is one of the three append-only tables `app.db.guard`'s `before_execute`
listener protects). That guard is defense-in-depth; the primary defence is
this module never having such a function to call in the first place
(coding-guidelines.md § Forbidden patterns: "do not write code that relies
on being caught — do not write it at all").
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.db.models.complaint_edit_history import ComplaintEditHistory
from app.db.models.complaint_status_history import ComplaintStatusHistory


def insert_status_change(
    session: Session,
    *,
    complaint_id: int,
    previous_status: str,
    new_status: str,
    note: str | None,
    actor_id: int,
    created_at: datetime,
) -> ComplaintStatusHistory:
    """Append one `complaint_status_history` row. Always called — BR-011:
    a history row is written for every status-update transaction that
    commits, regardless of whether it is later "superseded" as the
    complaint's current status by a concurrent writer."""
    history_row = ComplaintStatusHistory(
        complaint_id=complaint_id,
        previous_status=previous_status,
        new_status=new_status,
        note=note,
        actor_id=actor_id,
        created_at=created_at,
    )
    session.add(history_row)
    session.flush()
    return history_row


def insert_edit_change(
    session: Session,
    *,
    complaint_id: int,
    field_name: str,
    previous_value: str,
    new_value: str,
    actor_id: int,
    created_at: datetime,
) -> ComplaintEditHistory:
    """Append one `complaint_edit_history` row (FR-014, T-019). Only called
    for a field the caller has already confirmed actually changed
    (`services.complaints.edit_details`) — `new_value IS DISTINCT FROM
    previous_value` is also a DB `CHECK` (REL-F5), belt-and-braces."""
    history_row = ComplaintEditHistory(
        complaint_id=complaint_id,
        field_name=field_name,
        previous_value=previous_value,
        new_value=new_value,
        actor_id=actor_id,
        created_at=created_at,
    )
    session.add(history_row)
    session.flush()
    return history_row
