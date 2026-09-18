"""The frozen status-transition map (BR-002) and `update_status`
(BR-002/BR-011, ADR-017, api-contract.md #11, T-018).

`LEGAL_TRANSITIONS` is the single source of truth for which `(previous,
new)` status pairs are legal — `app.services.complaints.create` imports it
too (via `legal_next_statuses`) so a freshly created complaint's
`legal_next_statuses` field can never drift from this route's own copy of
the rule. No DB `CHECK` expresses this (schema.md: "the legal map depends on
the *current* row value under a row lock, not a static rule").

`update_status` follows the row-lock pattern backend-architecture.md §9
mandates for every audited state change: one transaction, `SELECT ... FOR
UPDATE` on the complaint row -> validate the transition against the
*locked* row's current status -> update the row -> INSERT the history row.
Two concurrent status-update transactions on the same complaint serialise on
this row lock (BR-011) — the second transaction to acquire the lock sees
the *first* transaction's committed `status`, not a stale value read before
the first transaction started, so neither a lost update nor a
duplicate/skipped transition is possible. The later commit wins the
complaint's current status/note; **both** history rows persist regardless
(BR-011, AC-014) because the history insert is unconditional, not decided by
who "wins".

Never imports from `app.api` (coding-guidelines.md § Layering) and never
raises anything but the typed errors in `app.core.errors`.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core import clock, strings
from app.core.errors import DependencyUnavailable, IllegalStatusTransition, NotFound
from app.db.models.complaint import Complaint
from app.db.repositories import complaint as complaint_repo
from app.db.repositories import history as history_repo
from app.db.repositories import user as user_repo

# BR-002 (backend-architecture.md §8, schema.md § Enums): the single frozen
# transition map. Every status-update route call and every create-response
# `legal_next_statuses` computation reads this same object — there is no
# second copy anywhere in the codebase.
LEGAL_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "new": ("in_progress",),
    "in_progress": ("resolved", "rejected"),
    "resolved": ("closed",),
    "rejected": ("closed",),
    "closed": (),
}


def legal_next_statuses(status: str) -> list[str]:
    """Return the legal next statuses for `status` (empty for `closed`, a
    terminal state, or for any unrecognised value)."""
    return list(LEGAL_TRANSITIONS.get(status, ()))


def is_legal_transition(previous_status: str, new_status: str) -> bool:
    """`True` iff `previous_status -> new_status` is one of the frozen
    map's legal pairs (BR-002). `new_status == previous_status` (a no-op
    "transition") is always illegal — it is not in any status's tuple."""
    return new_status in LEGAL_TRANSITIONS.get(previous_status, ())


@dataclass(frozen=True)
class UpdateStatusResult:
    complaint: Complaint
    updated_by_username: str
    legal_next_statuses: list[str]


def update_status(
    session: Session,
    *,
    complaint_id: int,
    new_status: str,
    note: str | None,
    actor_id: int,
) -> UpdateStatusResult:
    """Validate and apply a status change (BR-002/BR-011, ADR-017).

    Raises `NotFound` (404) if no such complaint exists, and
    `IllegalStatusTransition` (422 `illegal_transition`) if `new_status` is
    not legal from the row's *locked, current* status. `note`'s
    ≤2,000-character cap (api-contract.md #11) is enforced by the request
    DTO (`api.schemas.complaints.UpdateStatusRequest`), a 422 `invalid_input`
    before this function is ever called.
    """
    complaint = complaint_repo.get_by_id_for_update(session, complaint_id)
    if complaint is None:
        raise NotFound(strings.get("errors.complaint_not_found"))

    previous_status = complaint.status
    if not is_legal_transition(previous_status, new_status):
        raise IllegalStatusTransition(strings.get("errors.illegal_transition"))

    now = clock.now()
    complaint.status = new_status
    complaint.updated_at = now

    # Unconditional (BR-011): inserted every time, regardless of which
    # concurrent writer's update ultimately "wins" the row — never decided
    # by a comparison against some other transaction's outcome.
    history_repo.insert_status_change(
        session,
        complaint_id=complaint.id,
        previous_status=previous_status,
        new_status=new_status,
        note=note,
        actor_id=actor_id,
        created_at=now,
    )

    # Not committed here — `app.db.session.get_session()` commits once after
    # the route handler returns successfully (same pattern as
    # `services.complaints.create`).
    session.flush()

    actor = user_repo.get_by_id(session, actor_id)
    if actor is None:  # pragma: no cover - defensive; FK guarantees a row exists
        raise DependencyUnavailable(strings.get("errors.complaint_creator_unavailable"))

    return UpdateStatusResult(
        complaint=complaint,
        updated_by_username=actor.username,
        legal_next_statuses=legal_next_statuses(complaint.status),
    )
