"""Thin queries/persistence over `session` (backend-architecture.md §3).

No business rule lives here: rotation-on-login (ADR-021), the generic
failure on bad credentials, and (later, T-027) idle/absolute-expiry
rejection are all `services/auth.py`'s job. This module only knows how to
create a row, look one up by its token hash, mark it revoked, and refresh
`last_seen_at` — coding-guidelines.md § Layering.
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.models.session import Session as SessionRow


def create(
    session: Session,
    *,
    user_id: int,
    token_hash: str,
    csrf_token: str,
    absolute_expires_at: datetime,
) -> SessionRow:
    """Insert and flush a new `session` row. `token_hash`/`csrf_token` are
    already-computed values (the caller — `services/auth.py` — owns
    generating the raw token and hashing it; this function never sees a
    plaintext token)."""
    row = SessionRow(
        user_id=user_id,
        token_hash=token_hash,
        csrf_token=csrf_token,
        absolute_expires_at=absolute_expires_at,
    )
    session.add(row)
    session.flush()
    return row


def get_by_token_hash(session: Session, token_hash: str) -> SessionRow | None:
    """Return the `session` row matching `token_hash`, or `None`."""
    return session.scalar(sa.select(SessionRow).where(SessionRow.token_hash == token_hash))


def revoke(session: Session, row: SessionRow, *, now: datetime) -> None:
    """Set `revoked_at = now` on `row` (never delete — backend-architecture.md
    §3). Idempotent: calling this on an already-revoked row simply
    overwrites the timestamp; callers are expected to check `revoked_at is
    None` first when "already revoked" is meaningful to them."""
    row.revoked_at = now
    session.flush()


def touch_last_seen(session: Session, row: SessionRow, *, now: datetime) -> None:
    """Refresh `last_seen_at` on an active session row.

    T-027 hook: this function does not check `absolute_expires_at` or the
    idle window before refreshing — that rejection/expiry logic (and the
    bounded sweep DELETEs, backend-architecture.md §3) is explicitly out of
    scope for T-006 ("no OTP/expiry edge cases yet") and lands in T-027.
    """
    row.last_seen_at = now
    session.flush()
