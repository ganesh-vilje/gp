"""`edit_details` — the 7-day edit window service (api-contract.md #12,
FR-012/014, BR-014, AC-008, T-019).

Follows the same row-lock pattern as `services.complaints.transitions.
update_status` (backend-architecture.md §9): one transaction, `SELECT ...
FOR UPDATE` on the complaint row -> validate the edit window against the
*locked* row's `created_at` -> apply only the fields that actually changed
-> INSERT one `complaint_edit_history` row per changed field.

`now() < created_at + EDIT_WINDOW_DAYS` is enforced here, server-side,
regardless of what the client/UI shows (AC-008 — no override path exists).
A field resubmitted with its current (post-trim) value is silently skipped
by this service — no history row, no `updated_at` bump for that field alone
(api-contract.md #12) — matching the DB `CHECK (new_value IS DISTINCT FROM
previous_value)` (REL-F5) so that constraint is never reached by a
resubmitted-unchanged field in the first place.

Never imports from `app.api` (coding-guidelines.md § Layering) and never
raises anything but the typed errors in `app.core.errors`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core import clock, strings, validation
from app.core.errors import DependencyUnavailable, EditWindowExpired, NotFound
from app.db.models.complaint import Complaint
from app.db.repositories import complaint as complaint_repo
from app.db.repositories import history as history_repo
from app.db.repositories import user as user_repo
from app.services.complaints import EDIT_WINDOW_DAYS
from app.services.complaints.transitions import legal_next_statuses


@dataclass(frozen=True)
class EditDetailsResult:
    complaint: Complaint
    created_by_username: str
    legal_next_statuses: list[str]
    edit_window_expires_at: datetime


def edit_details(
    session: Session,
    *,
    complaint_id: int,
    citizen_name: str | None,
    citizen_phone: str | None,
    description: str | None,
    actor_id: int,
) -> EditDetailsResult:
    """Validate and apply an edit-details request (FR-012/014, BR-014,
    AC-008).

    Raises `NotFound` (404) if no such complaint exists, and
    `EditWindowExpired` (422 `edit_window_expired`) if the *locked* row's
    `created_at` is more than `EDIT_WINDOW_DAYS` in the past — checked
    before any per-field validation or write, and with no override path.
    Per-field format/length rules (BR-007/012/014) are enforced by the
    request DTO (`api.schemas.complaints.EditDetailsRequest`) plus
    `core.validation`, a 422 `invalid_input` before this function is ever
    reached for the shape checks, and inside this function for the phone
    format (`core.validation.validate_citizen_phone`, not expressible as a
    Pydantic field constraint alone).
    """
    complaint = complaint_repo.get_by_id_for_update(session, complaint_id)
    if complaint is None:
        raise NotFound(strings.get("errors.complaint_not_found"))

    now = clock.now()
    edit_window_expires_at = complaint.created_at + timedelta(days=EDIT_WINDOW_DAYS)
    if now >= edit_window_expires_at:
        raise EditWindowExpired(strings.get("errors.edit_window_expired"))

    if citizen_phone is not None:
        validation.validate_citizen_phone(citizen_phone)
    if citizen_name is not None:
        validation.validate_citizen_name(citizen_name)
    if description is not None:
        validation.validate_description(description)

    changed = False
    for field_name, new_value in (
        ("citizen_name", citizen_name),
        ("citizen_phone", citizen_phone),
        ("description", description),
    ):
        if new_value is None:
            continue
        previous_value = getattr(complaint, field_name)
        if new_value == previous_value:
            # api-contract.md #12: a field resubmitted unchanged is silently
            # skipped — no history row, matching REL-F5's `CHECK`.
            continue
        setattr(complaint, field_name, new_value)
        history_repo.insert_edit_change(
            session,
            complaint_id=complaint.id,
            field_name=field_name,
            previous_value=previous_value,
            new_value=new_value,
            actor_id=actor_id,
            created_at=now,
        )
        changed = True

    if changed:
        complaint.updated_at = now

    # Not committed here — a service never owns the request's transaction
    # boundary. B-001: the caller (`app.api.routers.complaints.
    # edit_complaint_details`) commits explicitly before building its
    # response, same reasoning as `services.complaints.create`/
    # `services.complaints.transitions.update_status`.
    session.flush()

    # security review F1 (T-019): `created_by` on the response DTO means
    # "which clerk logged the complaint" (data-dictionary.md), not "which
    # clerk just made this edit" — look up the complaint's original
    # creator, never the acting clerk, so this response agrees with GET.
    creator = user_repo.get_by_id(session, complaint.created_by)
    if creator is None:  # pragma: no cover - defensive; FK guarantees a row exists
        raise DependencyUnavailable(strings.get("errors.complaint_creator_unavailable"))

    return EditDetailsResult(
        complaint=complaint,
        created_by_username=creator.username,
        legal_next_statuses=legal_next_statuses(complaint.status),
        edit_window_expires_at=complaint.created_at + timedelta(days=EDIT_WINDOW_DAYS),
    )
