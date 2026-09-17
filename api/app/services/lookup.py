"""Public complaint status lookup (api-contract.md §4; BR-004/005/010/015;
AC-006/007/011/018; ADR-013, ADR-016; T-010).

Never a rate-limiting concern here — that is `app.services.limiter`, called
by the router before this module ever runs (coding-guidelines.md §
Layering: HTTP/rate-limit concerns stay out of the domain service).

Never imports from `app.api` and never raises anything but the typed
errors in `app.core.errors`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core import complaint_number, strings
from app.core.errors import NotFound, ValidationFailed
from app.db.repositories import complaint as complaint_repo

# ADR-013 / api-contract.md §4: the fixed, enumerated public-facing status
# message — never the clerk's free-text note (BR-005). One entry per
# `complaint.status` enum value; a status added later without an entry here
# is a `KeyError`, deliberately, rather than silently leaking an unmapped
# value to the public DTO.
_PUBLIC_UPDATE_BY_STATUS: dict[str, str] = {
    "new": "received",
    "in_progress": "in_progress",
    "resolved": "resolved",
    "rejected": "not_accepted",
    "closed": "closed",
}


@dataclass(frozen=True)
class LookupResult:
    """The exact, exhaustive public DTO shape (api-contract.md §4) — no
    `citizen_name`, `citizen_phone`, or clerk note field exists here at
    all, so BR-005 holds structurally, not by omission at the router."""

    complaint_number: str
    status: str
    public_update: str
    date_logged: date


def lookup(session: Session, raw_complaint_number: str) -> LookupResult:
    """BR-015's validation order: normalise, then regex+checksum validate,
    and only then a single equality read against `complaint` (BR-004 —
    exact match only, never a partial/wildcard search, never a list).

    Raises `ValidationFailed` for blank/whitespace-only/malformed input —
    **before any statement touches `complaint`** (AC-018/TC-DB-001/002).
    The router maps this to `400 invalid_input` (BR-015/AC-018's HTTP
    status is a router-layer decision — see `app.core.errors.ValidationFailed`'s
    docstring), not this service's default 422.

    Raises `NotFound` for a well-formed number with no matching row
    (AC-007) — the identical generic "not found" family as any other
    well-formed-but-absent lookup, never distinguishing "malformed" from
    "not assigned" in wording (BR-015).
    """
    normalised = complaint_number.normalise(raw_complaint_number)
    if not complaint_number.validate(normalised):
        raise ValidationFailed(
            strings.get("lookup.invalid_format"),
            fields={"complaint_number": "invalid_format"},
        )

    complaint = complaint_repo.get_by_complaint_number(session, normalised)
    if complaint is None:
        raise NotFound(strings.get("lookup.not_found"))

    return LookupResult(
        complaint_number=complaint.complaint_number,
        status=complaint.status,
        public_update=_PUBLIC_UPDATE_BY_STATUS[complaint.status],
        date_logged=complaint.created_at.date(),
    )
