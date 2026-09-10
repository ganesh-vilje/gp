"""Argon2 password hashing + the keyed username hash `h()` (security-architecture.md §1/§9).

- `hash_password`/`verify_password`/`needs_rehash` wrap `argon2-cffi`
  (dependency-strategy.md — H3 removed the framework hasher) so no crypto is
  hand-written here. Parameters are pinned to security-architecture.md §1's
  `m=9216 KiB, t=4, p=1` (Argon2id, chosen for the 512 MB instance) rather
  than the library defaults (100 MiB, p=8), which would not fit.
- `h(username, salt)` is `security-architecture.md`'s "Username component"
  definition (backend-architecture.md:168, schema.md's `actor_username_hash
  CHAR(16)`): the first 16 hex characters of
  `SHA-256(casefold(username) + USERNAME_HASH_SALT)` — fixed width, no PII,
  no enumeration. `USERNAME_HASH_SALT` is a secret (>=32 bytes, never
  rotated); this module does not read settings (out of scope for T-005) —
  the caller passes the salt in. **Dependency for T-006:** wire
  `Settings.username_hash_salt` and pass it to this function; `selfcheck`
  must also assert `len(salt) >= 32` and that it differs from `SECRET_KEY`
  (security-architecture.md §9), which belongs to that later task, not here.
- `sha256(token)` (also named for this module in backend-architecture.md
  §1's module layout, for hashing the opaque session token before it is
  stored) is **deferred to T-006** (session lifecycle) — no test in T-005
  needs it, and adding it now without a caller would be speculative.
"""

from __future__ import annotations

import hashlib

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError

# security-architecture.md §1: "Hashing | Argon2id via argon2-cffi,
# m=9216 KiB, t=4, p=1" — sized for the 512 MB instance; raise `m` first if
# the instance is upsized. `argon2-cffi`'s `PasswordHasher` already defaults
# to `type=Type.ID` (Argon2id), so it is not overridden here.
_password_hasher = PasswordHasher(time_cost=4, memory_cost=9216, parallelism=1)

_USERNAME_HASH_HEX_LENGTH = 16


def hash_password(password: str) -> str:
    """Return a self-describing Argon2id hash of `password`."""
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return `True` iff `password` matches `password_hash`.

    Never raises: a malformed hash or a mismatch both return `False` — the
    caller (a later task's `services.auth`) treats every failure identically
    per error-catalog.md's "no `invalid_credentials` code" rule.
    """
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Return `True` iff `password_hash` was produced with weaker-than-current parameters."""
    return _password_hasher.check_needs_rehash(password_hash)


def h(username: str, salt: bytes) -> str:
    """Return `security_event.actor_username_hash`: the first 16 hex
    characters of `SHA-256(casefold(username) + USERNAME_HASH_SALT)`.

    Casefolding first makes the hash (and therefore the `login_user`/
    `login_userip` rate-limiter keys and the `security_event` actor hash)
    case-insensitive, matching username lookups. Deterministic for a given
    `(username, salt)` pair.
    """
    digest = hashlib.sha256(username.casefold().encode("utf-8") + salt).hexdigest()
    return digest[:_USERNAME_HASH_HEX_LENGTH]
