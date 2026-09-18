"""Login, logout, and session resolution (ADR-007 core, ADR-021, BR-003).

Scope note (T-006, implementation-plan.md task row): session issue/revoke
only — no OTP handling, no `must_change_password` gating, no rate
limiting, no `security_event` writes, and no idle/absolute expiry
enforcement. Those are later tasks (`services/accounts.py` for OTP;
`middleware/authz.py`'s `must_change_password` gate; `services/limiter.py`;
`services/security_events.py`; T-027 for expiry/sweep). Hooks for each are
marked below where they will attach.

Never imports from `app.api` (coding-guidelines.md § Layering) and never
raises anything but the typed errors in `app.core.errors`.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core import hashing, strings
from app.core.clock import now as clock_now
from app.core.errors import NotAuthenticated
from app.db.models.clerk_account import ClerkAccount
from app.db.repositories import session as session_repo
from app.db.repositories import user as user_repo

# ADR-019: 9h absolute ceiling stored on every new session row. T-027 owns
# actually *enforcing* it (and the idle window) on resolution/sweep.
_SESSION_ABSOLUTE_HOURS = 9

# A fixed, precomputed Argon2id hash of a constant placeholder value — never
# a real credential, never derived from user input. `login()` verifies
# against this when the username does not exist, so an unknown-username
# attempt and a wrong-password attempt both pay the cost of exactly one
# Argon2 verification (security-architecture.md §1: "Credential check |
# constant-time by construction"). Computed once at import time.
_DUMMY_PASSWORD_HASH = hashing.hash_password("T-006 dummy hash - never a real credential")


def _generic_auth_failure() -> NotAuthenticated:
    """error-catalog.md: the single `not_authenticated` response for every
    failed login — never a distinct code for "unknown user" vs "wrong
    password" (security-architecture.md §1)."""
    return NotAuthenticated(strings.get("errors.not_authenticated"))


def login(
    session: Session,
    username: str,
    password: str,
    *,
    presented_raw_token: str | None = None,
) -> tuple[ClerkAccount, str]:
    """Verify `username`/`password`; on success, mint and store a new
    session (ADR-021 issuance) and return `(user, raw_token)`.

    `presented_raw_token` is the token from *this request's own* `__Host-
    session` cookie, if any (the caller — the login route, T-008 — reads
    the cookie; this function never touches HTTP). Per ADR-021, only the
    session that token names is revoked — never every session for the
    user, and never a session named by anything other than this request's
    own cookie. A login with no `presented_raw_token` simply adds a row.

    Raises `NotAuthenticated` — identically, and after doing comparable
    work — for both an unknown username and a wrong password; never
    reveals which. Callers must not add a branch that distinguishes the two
    (error-catalog.md rev 4: there is no `invalid_credentials` code).

    T-027/accounts hooks not implemented here: OTP expiry/consumption
    (`password_is_otp`), `must_change_password` gating, the two bounded
    session-sweep DELETEs backend-architecture.md §3 runs "on every
    successful login", rate limiting, and `security_event` writes.
    """
    user = user_repo.get_by_username(session, username)
    if user is None:
        # Pay the same Argon2 cost as a real, wrong-password attempt so the
        # two cases are not distinguishable by timing.
        hashing.verify_password(_DUMMY_PASSWORD_HASH, password)
        raise _generic_auth_failure()

    if not hashing.verify_password(user.password_hash, password):
        raise _generic_auth_failure()

    if presented_raw_token:
        presented_hash = hashing.sha256(presented_raw_token)
        presented_row = session_repo.get_by_token_hash(session, presented_hash)
        if presented_row is not None and presented_row.revoked_at is None:
            session_repo.revoke(session, presented_row, now=clock_now())

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashing.sha256(raw_token)
    csrf_token = secrets.token_hex(32)  # 256 bits, 64 hex chars — session.csrf_token CHAR(64)
    absolute_expires_at = clock_now() + timedelta(hours=_SESSION_ABSOLUTE_HOURS)

    session_repo.create(
        session,
        user_id=user.id,
        token_hash=token_hash,
        csrf_token=csrf_token,
        absolute_expires_at=absolute_expires_at,
    )

    return user, raw_token


def logout(session: Session, raw_token: str) -> None:
    """Revoke the session named by `raw_token` (set `revoked_at`, never
    delete). A no-op if the token does not match a row, or the row is
    already revoked — logout is idempotent; the caller (middleware/routes,
    T-008/T-010a) is responsible for having already authenticated the
    request before calling this."""
    token_hash = hashing.sha256(raw_token)
    row = session_repo.get_by_token_hash(session, token_hash)
    if row is None or row.revoked_at is not None:
        return
    session_repo.revoke(session, row, now=clock_now())


def session_csrf_token(session: Session, raw_token: str) -> str | None:
    """Return the resolved session row's own `csrf_token` (the session-
    bound CSRF path, backend-architecture.md §4), or `None` if `raw_token`
    does not resolve to a present, non-revoked session.

    Exposed separately from `resolve_session` so `middleware/session_loader
    .py` (which must not import `app.db.repositories` directly for a
    domain-shaped value like this — coding-guidelines.md § Layering) can
    populate `request.state.csrf_token` through the service layer only.
    """
    token_hash = hashing.sha256(raw_token)
    row = session_repo.get_by_token_hash(session, token_hash)
    if row is None or row.revoked_at is not None:
        return None
    return row.csrf_token


def resolve_session(session: Session, raw_token: str) -> ClerkAccount | None:
    """Hash `raw_token`, look up the session row, and return its user — or
    `None` for no row / a revoked row.

    T-027 hooks, deliberately not implemented here (task scope: "no OTP/
    expiry edge cases yet"): reject (and mark revoked) a row past
    `absolute_expires_at` or the `SESSION_IDLE_MINUTES` idle window before
    returning a user.
    """
    token_hash = hashing.sha256(raw_token)
    row = session_repo.get_by_token_hash(session, token_hash)
    if row is None or row.revoked_at is not None:
        return None
    # T-027: idle/absolute expiry check belongs here, ahead of the touch
    # below (an expired row must be rejected *and* marked revoked on the
    # same request — backend-architecture.md §3).
    session_repo.touch_last_seen(session, row, now=clock_now())
    return user_repo.get_by_id(session, row.user_id)
