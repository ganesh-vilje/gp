"""`POST /api/complaints` (api-contract.md §7, T-009).

Never a business rule here (coding-guidelines.md § Layering) — validation,
the idempotent-replay lookup, and the complaint-number-collision retry all
live in `app.services.complaints`; this module only validates the request
DTO, calls the service, and shapes the HTTP response (status code, response
DTO).

No rate limiting yet: the `write`/`detail` limiter scopes (api-contract.md
§7) depend on `app/services/limiter.py`, which does not exist yet (later
task) — this route is otherwise complete per this task's done-condition.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_session
from app.api.schemas.complaints import ComplaintDTO, CreateComplaintRequest
from app.db.models.clerk_account import ClerkAccount
from app.services import complaints as complaints_service

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
    return ComplaintDTO(
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
