"""ORM factories for synthetic test rows (test-strategy.md §3 "Fixture-
factory pattern"), used by the `make_clerk`/`make_complaint`/`make_session`
fixtures in `tests/conftest.py`.

Each function takes the test's `Session` (the SAVEPOINT-rollback session
from `conftest.db_session`), builds the ORM object, `session.add()`s and
`session.flush()`s it (so the row is visible within the test's own
transaction and gets its generated `id`/server-defaulted columns back
without committing), and returns the object. Rolled back at test teardown
by `db_session`, same as the old Core-`text()` skeleton this replaces
(T-003a -> T-004).

Synthetic-only data: no real name, phone, or credential ever appears here.
"""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from app.core import hashing
from app.core.clock import now as clock_now
from app.db.models import ClerkAccount, Complaint
from app.db.models.session import Session as SessionRow
from sqlalchemy.orm import Session

# Crockford base-32 alphabet (excludes I, L, O, U) — matches the complaint
# CHECK constraint `complaint_number ~ '^[0-9A-HJKMNP-TV-Z]{9}$'`
# (migrations/versions/0001_initial.py).
_CROCKFORD32_ALPHABET = "0123456789" + "ABCDEFGH" + "JK" + "MN" + "PQRST" + "VWXYZ"

# A syntactically Argon2-looking hash. Not a real hash of any real password —
# only used to satisfy `password_hash TEXT NOT NULL` in synthetic test rows.
_FAKE_ARGON2_LOOKING_HASH_FOR_TESTS = (
    "$argon2id$v=19$m=65536,t=3,p=4$c3ludGhldGljdGVzdHNhbHQ$c3ludGhldGljdGVzdGhhc2h2YWx1ZQ"
)


def _random_digits(n: int) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(n))


def _synthetic_complaint_number() -> str:
    return "".join(secrets.choice(_CROCKFORD32_ALPHABET) for _ in range(9))


def make_clerk(
    session: Session,
    *,
    username: str | None = None,
    is_admin: bool = False,
    must_change_password: bool = False,
    password: str | None = None,
) -> ClerkAccount:
    """Factory for a synthetic `clerk_account` row.

    `password`, when given, is hashed with the real `core.hashing
    .hash_password` (the same call `app.cli.bootstrap_admin` uses) so the
    row can actually authenticate via `services.auth.login` — used by
    `tests/conftest.py`'s `seeded_accounts`/`live_seeded_accounts`
    (`clerk_test`, T-006a) until FR-017's account-creation service
    (T-033) exists. Omitted (the default), the row gets the syntactic-only
    placeholder hash below, which cannot be used to log in.
    """
    clerk = ClerkAccount(
        username=username or f"test_clerk_{uuid4().hex[:10]}",
        password_hash=(
            hashing.hash_password(password) if password else _FAKE_ARGON2_LOOKING_HASH_FOR_TESTS
        ),
        is_admin_clerk=is_admin,
        must_change_password=must_change_password,
        password_is_otp=False,
        password_set_at=clock_now(),
    )
    session.add(clerk)
    session.flush()
    return clerk


def make_complaint(
    session: Session,
    *,
    status: str = "new",
    created_by: int | None = None,
    citizen_name: str | None = None,
    citizen_phone: str | None = None,
    description: str | None = None,
) -> Complaint:
    """Factory for a synthetic `complaint` row.

    `created_by` defaults to a freshly-created synthetic clerk via
    `make_clerk` when not given.
    """
    if created_by is None:
        created_by = make_clerk(session).id
    complaint = Complaint(
        complaint_number=_synthetic_complaint_number(),
        client_request_id=uuid4(),
        citizen_name=citizen_name or f"Test Citizen {uuid4().hex[:6]}",
        citizen_phone=citizen_phone or f"+9190000{_random_digits(4)}",
        description=description or "Synthetic test complaint for automated integration tests.",
        status=status,
        created_by=created_by,
    )
    session.add(complaint)
    session.flush()
    return complaint


def make_session(
    session: Session,
    *,
    user_id: int | None = None,
    absolute_expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> SessionRow:
    """Factory for a synthetic `session` row.

    `user_id` defaults to a freshly-created synthetic clerk via `make_clerk`
    when not given.
    """
    if user_id is None:
        user_id = make_clerk(session).id
    if absolute_expires_at is None:
        absolute_expires_at = clock_now() + timedelta(hours=24)
    row = SessionRow(
        user_id=user_id,
        token_hash=sha256(uuid4().bytes).hexdigest(),
        csrf_token=sha256(uuid4().bytes).hexdigest(),
        absolute_expires_at=absolute_expires_at,
        revoked_at=revoked_at,
    )
    session.add(row)
    session.flush()
    return row
