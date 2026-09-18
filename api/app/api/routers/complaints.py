"""`POST /api/complaints`, `GET /api/complaints/{id}` and
`POST /api/complaints/{id}/status` (api-contract.md §7/§9/§11, T-009/T-018).

Never a business rule here (coding-guidelines.md § Layering) — validation,
the idempotent-replay lookup, the complaint-number-collision retry, the
frozen transition map, and the row-locked status update all live in
`app.services.complaints`/`app.services.complaints.transitions`; this module
only validates the request DTO, calls the service, and shapes the HTTP
response (status code, response DTO).

No rate limiting yet: the `write`/`detail` limiter scopes (api-contract.md
§7/§9/§11) depend on `app/services/limiter.py`, which does not exist yet
(later task) — these routes are otherwise complete per each task's
done-condition.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session
from app.api.schemas.complaints import (
    ComplaintDetailDTO,
    ComplaintDTO,
    CreateComplaintRequest,
    UpdateStatusRequest,
)
from app.db.models.clerk_account import ClerkAccount
from app.db.models.complaint import Complaint
from app.services import complaints as complaints_service
from app.services.complaints import transitions as transitions_service

router = APIRouter(prefix="/api")


@router.post("/complaints", response_model=ComplaintDTO)
def create_complaint(
    body: CreateComplaintRequest,
    response: Response,
    session: Session = Depends(get_session),  # noqa: B008 - standard FastAPI DI idiom
    user: ClerkAccount = Depends(current_user),  # noqa: B008 - 401 if unreachable via middleware
) -> ComplaintDTO:
    result = complaints_service.create(
        session,
        client_request_id=body.client_request_id,
        citizen_name=body.citizen_name,
        citizen_phone=body.citizen_phone,
        description=body.description,
        created_by=user.id,
    )

    # api-contract.md §7: 201 on first submission, 200 on a duplicate replay.
    response.status_code = 200 if result.duplicate else 201

    complaint = result.complaint
    body_out = ComplaintDTO(
        id=complaint.id,
        complaint_number=complaint.complaint_number,
        status=complaint.status,
        citizen_name=complaint.citizen_name,
        citizen_phone=complaint.citizen_phone,
        description=complaint.description,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
        created_by=result.created_by_username,
        legal_next_statuses=result.legal_next_statuses,
        edit_window_expires_at=result.edit_window_expires_at,
        duplicate=result.duplicate,
    )

    # B-001: commit here, before the response is sent — see
    # `app/db/session.py`'s docstring ("B-001 root cause note"). A client
    # may act on this response (e.g. immediately fetch the new complaint)
    # before `get_session()`'s own post-yield commit has even run. Committed
    # last (security review F1) so nothing after this line can turn an
    # already-durable write into an error response.
    session.commit()

    return body_out


def _detail_dto(
    complaint: Complaint,
    *,
    created_by: str,
    legal_next_statuses: list[str],
    edit_window_expires_at: datetime,
) -> ComplaintDetailDTO:
    return ComplaintDetailDTO(
        id=complaint.id,
        complaint_number=complaint.complaint_number,
        status=complaint.status,
        citizen_name=complaint.citizen_name,
        citizen_phone=complaint.citizen_phone,
        description=complaint.description,
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
        created_by=created_by,
        legal_next_statuses=legal_next_statuses,
        edit_window_expires_at=edit_window_expires_at,
    )


@router.get("/complaints/{complaint_id}", response_model=ComplaintDetailDTO)
def get_complaint(
    complaint_id: int,
    session: Session = Depends(get_session),  # noqa: B008 - standard FastAPI DI idiom
    user: ClerkAccount = Depends(current_user),  # noqa: B008 - 401 if unreachable via middleware
) -> ComplaintDetailDTO:
    result = complaints_service.get_detail(session, complaint_id)
    return _detail_dto(
        result.complaint,
        created_by=result.created_by_username,
        legal_next_statuses=result.legal_next_statuses,
        edit_window_expires_at=result.edit_window_expires_at,
    )


@router.post("/complaints/{complaint_id}/status", response_model=ComplaintDetailDTO)
def update_complaint_status(
    complaint_id: int,
    body: UpdateStatusRequest,
    session: Session = Depends(get_session),  # noqa: B008 - standard FastAPI DI idiom
    user: ClerkAccount = Depends(current_user),  # noqa: B008 - 401 if unreachable via middleware
) -> ComplaintDetailDTO:
    result = transitions_service.update_status(
        session,
        complaint_id=complaint_id,
        new_status=body.new_status,
        note=body.note,
        actor_id=user.id,
    )
    complaint = result.complaint
    body_out = _detail_dto(
        complaint,
        created_by=result.updated_by_username,
        legal_next_statuses=result.legal_next_statuses,
        edit_window_expires_at=complaint.created_at
        + timedelta(days=complaints_service.EDIT_WINDOW_DAYS),
    )

    # B-001: same reasoning as `create_complaint` above. Committed last
    # (security review F1) — this route has no idempotency key, so a 500
    # after an earlier commit would otherwise turn an already-committed
    # transition into a confusing client-side retry (422 illegal_transition
    # on the next attempt, since the transition already happened).
    session.commit()

    return body_out
