"""Thin queries over `clerk_account` (coding-guidelines.md § Layering:
"Repositories: queries, row locks, uniqueness retries, pagination. Never
enforce a rule or decide a status transition — that is a service's job even
if it 'would be one line here.'").

`get_by_username` is an exact (case-sensitive) match against the
`uq_clerk_account_username` unique constraint (app/db/models/clerk_account.py)
— interpretation note (T-006): security-architecture.md/ADR-007 do not state
that login itself is case-insensitive; only `core.hashing.h()`'s *rate-limiter
key* casefolds the username. Login-time case-folding, if wanted, is a
decision for whoever owns `services/accounts.py` (username creation), not
this repository.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.db.models.clerk_account import ClerkAccount


def get_by_username(session: Session, username: str) -> ClerkAccount | None:
    """Return the `clerk_account` row matching `username` exactly, or `None`."""
    return session.scalar(sa.select(ClerkAccount).where(ClerkAccount.username == username))


def get_by_id(session: Session, user_id: int) -> ClerkAccount | None:
    """Return the `clerk_account` row with primary key `user_id`, or `None`."""
    return session.get(ClerkAccount, user_id)


def any_admin_clerk_exists(session: Session) -> bool:
    """Return `True` iff at least one `clerk_account` row has
    `is_admin_clerk=True` (T-007, `app.cli.bootstrap_admin`'s idempotency
    check — AC-019: a second bootstrap run must be a no-op, never a
    duplicate/conflicting admin account)."""
    return bool(session.scalar(sa.select(sa.exists().where(ClerkAccount.is_admin_clerk.is_(True)))))
