"""Application settings.

Deliberately not `pydantic-settings` (dependency-strategy.md §1 "Deliberately
not added": "`os.environ` plus a small typed settings module is sufficient;
one fewer place a secret can be read from a file"); `pydantic-settings` is
not in the 8-package runtime baseline. Every value — including non-secret
`ENVIRONMENT` — is read with no default: fail CLOSED, never fall back to an
insecure value. An unset, empty, or wrongly-cased `ENVIRONMENT` (values are
case-sensitive: `dev`, `test`, `staging`, `prod` only) raises
`ImproperlyConfigured` rather than silently enabling production docs
(orchestrator decision on T-001 review finding F1). Every environment,
including local dev, must set `ENVIRONMENT` explicitly.

T-006 adds the two secrets security-architecture.md §9 requires ("Two
separate secrets, not one"): `SECRET_KEY` (the anonymous-CSRF HMAC key,
freely rotatable) and `USERNAME_HASH_SALT` (`core.hashing.h()`'s salt,
never rotated). Both are `field(repr=False)` and fail closed exactly like
`database_url` — including, per review finding F3, the `>= 32 characters`
and "not equal to each other" checks security-architecture.md §9 names;
`selfcheck` (a later task) re-asserts the same invariants as its own,
independent belt-and-braces gate. It also adds `allowed_origins` — not a
secret, but needed now so `middleware/csrf.py`'s Origin allow-list check
(security-architecture.md §4/§5) is functional before T-010a's CORS
middleware (row 3) exists; T-010a may read the same field rather than add
a second one. Per review finding F2, each entry is validated fail-closed
(`_validate_allowed_origin`): no `*`/`null`, no path/query/fragment, and
`https://` only outside `dev`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from urllib.parse import urlsplit

_VALID_ENVIRONMENTS = frozenset({"dev", "test", "staging", "prod"})
# security-architecture.md §9: "selfcheck fails if they are equal or either
# is <32 bytes" — enforced here too (review finding F3), not only later by
# selfcheck, so a misconfigured process never starts at all.
_MIN_SECRET_LENGTH = 32


class ImproperlyConfigured(RuntimeError):
    """Raised when a required environment variable is missing or invalid."""


def _validate_allowed_origin(origin: str, *, environment: str) -> None:
    """F2 (T-006 review): reject an `ALLOWED_ORIGINS` entry that is not a
    bare `scheme://host[:port]` origin, fail closed.

    Rejects the literal wildcard `*` and the literal `null` (the `Origin`
    a sandboxed/opaque browsing context sends — never a value we should
    ever match against); any entry carrying a path, query, or fragment
    (an `Origin` header itself never has one, so an allow-list entry that
    does is a configuration mistake, not a stricter rule); and, outside
    `dev`, any non-`https://` origin (security-architecture.md §5:
    `SameSite=None` is forbidden and the deployed site is `https` only —
    `dev` alone may list `http://localhost:...` for the local frontend).
    """
    if origin in ("*", "null"):
        raise ImproperlyConfigured(
            f"ALLOWED_ORIGINS entry {origin!r} is not a valid origin (fail closed)."
        )
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ImproperlyConfigured(
            f"ALLOWED_ORIGINS entry {origin!r} must be a bare origin "
            "(scheme://host[:port], no path/query/fragment)."
        )
    if environment != "dev" and parsed.scheme != "https":
        raise ImproperlyConfigured(
            f"ALLOWED_ORIGINS entry {origin!r} must use https:// outside the dev environment."
        )


@dataclass(frozen=True)
class Settings:
    # `environment` is not a secret, so it is the one field allowed in
    # __repr__. Every field added later that IS a secret (e.g. a future
    # `secret_key`) must be declared with `field(repr=False)` so it can never
    # be printed, logged, or captured in a traceback — see __repr__ below,
    # which enforces the same rule independently of dataclass's own repr.
    environment: str = field()
    # Connection string for both the request and limiter engines
    # (app/db/engine.py, T-004). A secret-shaped value (embeds credentials)
    # so it is declared `repr=False` — see the class docstring above and
    # `__repr__` below, which redacts it independently of dataclass's own
    # repr.
    database_url: str = field(repr=False)
    # NOTE (T-006): `environment` and `allowed_origins` are the only two
    # fields shown in __repr__ today — every secret added since must keep
    # using `field(repr=False)`, per the comment above.
    # The anonymous-CSRF HMAC key (security-architecture.md §4/§9). One
    # consumer: `middleware/csrf.py`'s stateless
    # `hmac_sha256(SECRET_KEY, __Host-csrfseed)` path. Freely rotatable.
    secret_key: str = field(repr=False)
    # `core.hashing.h()`'s salt (security-architecture.md §9). One consumer
    # today: nothing in T-006 calls `h()` yet (it is used by the limiter/
    # security_event actor hash, later tasks) — declared here now so the
    # secret exists in one place from the start, per §9's "two separate
    # secrets" rule. Never rotated.
    username_hash_salt: str = field(repr=False)
    # Origin allow-list for CORS (T-010a) and, from T-006, for
    # `middleware/csrf.py`'s Origin-header check (security-architecture.md
    # §4/§5). Not a secret — no `repr=False`. Comma-separated in
    # `ALLOWED_ORIGINS`; at least one entry is required (fail closed).
    allowed_origins: tuple[str, ...] = field()

    @property
    def docs_enabled(self) -> bool:
        """BR-010 / selfcheck §11: OpenAPI docs are served only outside prod."""
        return self.environment != "prod"

    def __repr__(self) -> str:
        """Emit field names, and values only for fields not marked repr=False.

        `environment` and `allowed_origins` are the only values shown today
        (neither is a secret); any future secret field must be declared with
        `field(repr=False)` so it is never printed, logged, or captured in a
        traceback.
        """
        parts = []
        for f in fields(self):
            if f.repr:
                parts.append(f"{f.name}={getattr(self, f.name)!r}")
            else:
                parts.append(f"{f.name}=<redacted>")
        return f"{type(self).__name__}({', '.join(parts)})"


def get_settings() -> Settings:
    """Read settings from the process environment.

    Called once per `create_app()` (not cached at import time) so tests can
    change `ENVIRONMENT` and build a fresh app.
    """
    environment = os.environ.get("ENVIRONMENT")
    if not environment or environment not in _VALID_ENVIRONMENTS:
        raise ImproperlyConfigured(
            "ENVIRONMENT must be set to exactly one of "
            f"{sorted(_VALID_ENVIRONMENTS)} (case-sensitive), got {environment!r}"
        )
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise ImproperlyConfigured(
            "DATABASE_URL must be set (e.g. "
            "postgresql+psycopg://user:pass@host:5432/db) — fail closed, no default."
        )
    secret_key = os.environ.get("SECRET_KEY")
    if not secret_key:
        raise ImproperlyConfigured(
            "SECRET_KEY must be set (security-architecture.md §9: the "
            "anonymous-CSRF HMAC key) — fail closed, no default."
        )
    if len(secret_key) < _MIN_SECRET_LENGTH:
        raise ImproperlyConfigured(
            f"SECRET_KEY must be at least {_MIN_SECRET_LENGTH} characters "
            "(security-architecture.md §9)."
        )
    username_hash_salt = os.environ.get("USERNAME_HASH_SALT")
    if not username_hash_salt:
        raise ImproperlyConfigured(
            "USERNAME_HASH_SALT must be set (security-architecture.md §9: "
            "core.hashing.h()'s salt, a secret distinct from SECRET_KEY) — "
            "fail closed, no default."
        )
    if len(username_hash_salt) < _MIN_SECRET_LENGTH:
        raise ImproperlyConfigured(
            f"USERNAME_HASH_SALT must be at least {_MIN_SECRET_LENGTH} characters "
            "(security-architecture.md §9)."
        )
    if secret_key == username_hash_salt:
        raise ImproperlyConfigured(
            "SECRET_KEY and USERNAME_HASH_SALT must not be equal — "
            "security-architecture.md §9: 'Two separate secrets, not one.'"
        )
    allowed_origins_raw = os.environ.get("ALLOWED_ORIGINS")
    if not allowed_origins_raw:
        raise ImproperlyConfigured(
            "ALLOWED_ORIGINS must be set (comma-separated origins, e.g. "
            "https://www.example.in) — fail closed, no default."
        )
    allowed_origins = tuple(
        origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()
    )
    if not allowed_origins:
        raise ImproperlyConfigured("ALLOWED_ORIGINS must contain at least one origin.")
    for origin in allowed_origins:
        _validate_allowed_origin(origin, environment=environment)
    return Settings(
        environment=environment,
        database_url=database_url,
        secret_key=secret_key,
        username_hash_salt=username_hash_salt,
        allowed_origins=allowed_origins,
    )
