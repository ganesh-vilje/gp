"""Injectable clock (implementation-plan.md § Clock injection decision).

Decision: an injectable clock, not a third-party freezing library. Every
module that needs "now" (session expiry, OTP expiry, rate-limiter window
truncation) calls `core.clock.now()` rather than `datetime.now()` /
`datetime.utcnow()` directly — a grep assertion in CI enforces this
(coding-guidelines.md § Validation and typing, § Forbidden patterns). Tests
monkeypatch this single function to a controllable value instead of
depending on a freezing library, keeping the standard-library-first budget
(dependency-strategy.md §1).
"""

from __future__ import annotations

from datetime import UTC, datetime


def now() -> datetime:
    """Return the current, timezone-aware time in UTC."""
    return datetime.now(UTC)
