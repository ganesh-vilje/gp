"""Complaint creation (api-contract.md §7; AC-002/003/012/015/016;
BR-001/006/007/009/012/014; ADR-016; ADR-022; T-009).

Scope note (implementation-plan.md task row): creation and its
idempotent-replay/number-collision-retry semantics only — status updates
(`services/complaints/transitions.py`, later task) and edit-details are out
of scope here.

Never imports from `app.api` (coding-guidelines.md § Layering) and never
raises anything but the typed errors in `app.core.errors`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core import strings, validation
from app.core.errors import DependencyUnavailable
from app.db.models.complaint import Complaint
from app.db.repositories import complaint as complaint_repo
from app.db.repositories import user as user_repo
from app.db.repositories.complaint import NumberGenerationExhausted

# FR-012/AC-008 (backend-architecture.md §9): "now() < created_at +
# EDIT_WINDOW_DAYS checked in the service." Only the derived
# `edit_window_expires_at` value on the create response is this task's
# concern — the edit-details route itself (T-0xx) owns enforcing it.
EDIT_WINDOW_DAYS = 7

# BR-002 (backend-architecture.md §8): the single frozen transition map.
# Only the "new" entry is exercised by this task (every freshly created
# complaint starts "new") — the full map is reproduced here so the create
# response's `legal_next_statuses` (api-contract.md §7) never drifts from
# the status-update route's own copy of this rule once that route
# (services/complaints/transitions.py, a later task) exists.
_LEGAL_NEXT_STATUSES: dict[str, tuple[str, ...]] = {
    "new": ("in_progress",),
    "in_progress": ("resolved", "rejected"),
    "resolved": ("closed",),
    "rejected": ("closed",),
    "closed": (),
}


@dataclass(frozen=True)
class CreateComplaintResult:
    complaint: Complaint
    duplicate: bool
    created_by_username: str
    legal_next_statuses: list[str]
    edit_window_expires_at: datetime


def create(
    session: Session,
    *,
    client_request_id: UUID,
    citizen_name: str,
    citizen_phone: str,
    description: str,
    created_by: int,
) -> CreateComplaintResult:
    """Validate and create a complaint (BR-001/006/007/009/012/014), or —
    if `client_request_id` matches a row that already exists — return that
    existing row unchanged with `duplicate=True` (ADR-022/R2-6): the
    idempotent-replay path never creates a second row and never re-runs
    validation against the resubmitted body.

    A pre-check against `client_request_id` short-circuits the common case
    (the client's own retry of its own prior submission) without ever
    reaching the database's unique index; `complaint_repo.insert_new` still
    handles the rarer, genuinely concurrent race (two requests for the same
    `client_request_id` reaching the INSERT at once) via the unique-
    violation path, so correctness never depends on this pre-check alone.
    """
    existing = complaint_repo.get_by_client_request_id(
        session, client_request_id, created_by=created_by
    )
    if existing is not None:
        return _result(session, existing, duplicate=True)

    validation.validate_citizen_phone(citizen_phone)
    validation.validate_citizen_name(citizen_name)
    validation.validate_description(description)

    try:
        complaint, duplicate = complaint_repo.insert_new(
            session,
            client_request_id=client_request_id,
            citizen_name=citizen_name,
            citizen_phone=citizen_phone,
            description=description,
            created_by=created_by,
        )
    except NumberGenerationExhausted as exc:
        raise DependencyUnavailable(
            strings.get("errors.complaint_number_generation_failed")
        ) from exc

    # Not committed here — `app.db.session.get_session()` (this session's
    # owner) commits once after the route handler returns successfully,
    # exactly like `services.auth.login` (T-006/T-008's established
    # pattern): a service never owns the request's transaction boundary.
    return _result(session, complaint, duplicate=duplicate)


def _result(session: Session, complaint: Complaint, *, duplicate: bool) -> CreateComplaintResult:
    creator = user_repo.get_by_id(session, complaint.created_by)
    if creator is None:  # pragma: no cover - defensive; FK guarantees a row exists
        raise DependencyUnavailable(strings.get("errors.complaint_creator_unavailable"))
    return CreateComplaintResult(
        complaint=complaint,
        duplicate=duplicate,
        created_by_username=creator.username,
        legal_next_statuses=list(_LEGAL_NEXT_STATUSES.get(complaint.status, ())),
        edit_window_expires_at=complaint.created_at + timedelta(days=EDIT_WINDOW_DAYS),
    )
