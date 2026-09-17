"""Queries and the number-collision-retry insert for `complaint`
(coding-guidelines.md § Layering: retries live here, business rules do
not — `app.services.complaints` decides what to validate and when to call
this module).

ADR-016 / backend-architecture.md §7: "Generation: `INSERT` with the
candidate; on unique-violation retry with a fresh number, max 5 attempts
inside a savepoint." backend-architecture.md §10 (ADR-022/R2-6): "on a
unique violation [on `client_request_id`] the service re-reads the row ...
and returns it ... instead of creating a second complaint." Both
unique-violation paths are handled here, distinguished by the violated
constraint's name, so a concurrent replay of the same `client_request_id`
and a genuine `complaint_number` collision are never confused.
"""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import complaint_number, strings
from app.core.errors import ValidationFailed
from app.db.models.complaint import Complaint

_MAX_NUMBER_GENERATION_ATTEMPTS = 5

_COMPLAINT_NUMBER_CONSTRAINT = "uq_complaint_number"
_CLIENT_REQUEST_ID_CONSTRAINT = "uq_complaint_client_request_id"


class NumberGenerationExhausted(Exception):
    """Raised after `_MAX_NUMBER_GENERATION_ATTEMPTS` consecutive
    `complaint_number` collisions inside `insert_new` — the service maps
    this to `DependencyUnavailable` (503 `service_unavailable`), never a
    wrong/reused number (api-contract.md §7)."""


def get_by_client_request_id(
    session: Session, client_request_id: UUID, *, created_by: int
) -> Complaint | None:
    """Return the `complaint` row matching `client_request_id` **and**
    `created_by`, or `None`. Scoped to the owning clerk (security-review F1):
    a `client_request_id` collision belonging to a different clerk must never
    be returned as if it were the caller's own row."""
    return session.scalar(
        sa.select(Complaint).where(
            Complaint.client_request_id == client_request_id,
            Complaint.created_by == created_by,
        )
    )


def get_by_id(session: Session, complaint_id: int) -> Complaint | None:
    """Return the `complaint` row with primary key `complaint_id`, or `None`."""
    return session.get(Complaint, complaint_id)


def _violated_constraint_name(error: IntegrityError) -> str | None:
    """Best-effort constraint name from a psycopg 3 `IntegrityError` —
    reads `orig.diag.constraint_name` (the structured diagnostic psycopg
    populates from the server's error response). Returns `None` if it is
    unavailable (e.g. a different driver), so the caller re-raises rather
    than silently mis-handling an unrelated integrity error."""
    diag = getattr(error.orig, "diag", None)
    return getattr(diag, "constraint_name", None) if diag is not None else None


def insert_new(
    session: Session,
    *,
    client_request_id: UUID,
    citizen_name: str,
    citizen_phone: str,
    description: str,
    created_by: int,
) -> tuple[Complaint, bool]:
    """Insert a new `complaint` row, generating a fresh `complaint_number`
    and retrying up to `_MAX_NUMBER_GENERATION_ATTEMPTS` times inside a
    SAVEPOINT on a `complaint_number` unique-violation (ADR-016).

    Returns `(complaint, duplicate)`. `duplicate=True` means a concurrent
    request already committed a row for this exact `client_request_id`
    (caught via `uq_complaint_client_request_id`, ADR-022/R2-6) — the
    existing row is re-read and returned rather than a second one created.
    `duplicate=False` is the normal, first-time creation path.

    Raises `NumberGenerationExhausted` after `_MAX_NUMBER_GENERATION_ATTEMPTS`
    consecutive `complaint_number` collisions.
    """
    for _attempt in range(_MAX_NUMBER_GENERATION_ATTEMPTS):
        candidate_number = complaint_number.generate()
        complaint = Complaint(
            complaint_number=candidate_number,
            client_request_id=client_request_id,
            citizen_name=citizen_name,
            citizen_phone=citizen_phone,
            description=description,
            created_by=created_by,
        )
        try:
            with session.begin_nested():
                session.add(complaint)
                session.flush()
        except IntegrityError as exc:
            constraint_name = _violated_constraint_name(exc)
            if constraint_name == _CLIENT_REQUEST_ID_CONSTRAINT:
                existing = get_by_client_request_id(
                    session, client_request_id, created_by=created_by
                )
                if existing is None:
                    # The row exists (the constraint fired) but does not
                    # belong to this caller (security-review F1): a
                    # cross-clerk `client_request_id` collision is a
                    # validation error, never another clerk's complaint.
                    raise ValidationFailed(
                        strings.get("validation.client_request_id.conflict"),
                        fields={"client_request_id": "conflict"},
                    ) from exc
                return existing, True
            if constraint_name == _COMPLAINT_NUMBER_CONSTRAINT:
                continue
            raise
        else:
            return complaint, False

    raise NumberGenerationExhausted(
        "Could not generate a unique complaint_number after "
        f"{_MAX_NUMBER_GENERATION_ATTEMPTS} attempts."
    )
