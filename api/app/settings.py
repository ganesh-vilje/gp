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
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields

_VALID_ENVIRONMENTS = frozenset({"dev", "test", "staging", "prod"})


class ImproperlyConfigured(RuntimeError):
    """Raised when a required environment variable is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    # `environment` is not a secret, so it is the one field allowed in
    # __repr__. Every field added later that IS a secret (e.g. a future
    # `secret_key`) must be declared with `field(repr=False)` so it can never
    # be printed, logged, or captured in a traceback — see __repr__ below,
    # which enforces the same rule independently of dataclass's own repr.
    environment: str = field()

    @property
    def docs_enabled(self) -> bool:
        """BR-010 / selfcheck §11: OpenAPI docs are served only outside prod."""
        return self.environment != "prod"

    def __repr__(self) -> str:
        """Emit field names, and values only for fields not marked repr=False.

        `environment` is the only value ever shown today; any future secret
        field must be declared with `field(repr=False)` so it is never
        printed, logged, or captured in a traceback.
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
    return Settings(environment=environment)
