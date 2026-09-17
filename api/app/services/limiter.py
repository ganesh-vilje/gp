"""Atomic rate-limiter upsert (backend-architecture.md §5, ADR-008).

**Scope note (T-010 task row): the `lookup` scope only.** The login/
`detail`/`write`/`search` scopes, `core/client_ip.py`'s peer-gated IP
derivation, and the deterministic-cleanup trigger's exact "only on a new
window" condition are later tasks (T-025/T-026/T-040) — this module keeps
the mechanism generic (any `scope`/`key`/`limit`/`window_seconds`) so those
tasks add call sites, not a rewrite.

One statement per check, on the **dedicated AUTOCOMMIT limiter engine**
(`app.db.engine.get_limiter_engine`, never the request `Session`), so the
increment commits independently of the surrounding request's own
transaction — this is what TC-SEC-024 verifies:

    INSERT INTO rate_limit_counter (scope, key, window_start, count)
    VALUES (:scope, :key, :window_start, 1)
    ON CONFLICT (scope, key, window_start) DO UPDATE SET count = rate_limit_counter.count + 1
    RETURNING count;

Any statement error is fail-closed: the caller sees `DependencyUnavailable`
(503 `service_unavailable`), never a silently-allowed request
(api-contract.md §4: "limiter write failure fails closed, no lookup
performed").

Windows are fixed, not sliding (ADR-008 — "allows up to 2x at a boundary,
accepted; a sliding window is a code-only change if it ever matters").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.errors import DependencyUnavailable
from app.db.engine import get_limiter_engine
from app.db.models.rate_limit_counter import RateLimitCounter

# backend-architecture.md §5: "when the upsert creates a new window_start
# for a key ... that key's rows older than two windows [and] the
# scope-agnostic sweep". This module runs the scope-agnostic half
# unconditionally (bounded by LIMIT, so it is cheap even when it finds
# nothing) rather than trying to detect "was this row newly inserted" —
# a functionally equivalent, simpler trigger for the one scope this task
# adds; later tasks may tighten the trigger without changing the shape of
# the cleanup statement itself.
_CLEANUP_SWEEP_HOURS = 2
_CLEANUP_SWEEP_ROW_LIMIT = 500

_RATE_LIMIT_COUNTER_PK = "pk_rate_limit_counter"


@dataclass(frozen=True)
class LimiterResult:
    """`allowed`: whether this request is within `limit` for its window.
    `count`: the counter's value *after* this increment (RETURNING count).
    `retry_after_seconds`: seconds remaining in the current fixed window —
    the value a caller over the limit puts in the `Retry-After` header."""

    allowed: bool
    count: int
    retry_after_seconds: int


def _window_start(now: datetime, window_seconds: int) -> datetime:
    """Floor `now` to the start of its `window_seconds`-wide fixed window."""
    epoch_seconds = int(now.timestamp())
    floored_epoch_seconds = epoch_seconds - (epoch_seconds % window_seconds)
    return datetime.fromtimestamp(floored_epoch_seconds, tz=now.tzinfo)


def _cleanup(connection: sa.Connection, *, now: datetime) -> None:
    """Bounded, scope-agnostic sweep (backend-architecture.md §5) — a
    `ctid` sub-select, since PostgreSQL has no `DELETE ... LIMIT`."""
    cutoff = now - timedelta(hours=_CLEANUP_SWEEP_HOURS)
    connection.execute(
        sa.text(
            "DELETE FROM rate_limit_counter WHERE ctid IN ("
            "SELECT ctid FROM rate_limit_counter "
            "WHERE window_start < :cutoff "
            "LIMIT :sweep_limit"
            ")"
        ),
        {"cutoff": cutoff, "sweep_limit": _CLEANUP_SWEEP_ROW_LIMIT},
    )


def check_and_increment(
    *,
    scope: str,
    key: str,
    limit: int,
    window_seconds: int,
    now: datetime,
) -> LimiterResult:
    """Atomically increment the `(scope, key, window_start)` counter for
    this fixed window and report whether this request is within `limit`.

    Raises `DependencyUnavailable` on any error from the limiter engine
    (connection failure, statement error) — the caller must treat this as
    "refuse the request", never "allow it" (fail closed).
    """
    window_start = _window_start(now, window_seconds)

    stmt = (
        pg_insert(RateLimitCounter)
        .values(scope=scope, key=key, window_start=window_start, count=1)
        .on_conflict_do_update(
            constraint=_RATE_LIMIT_COUNTER_PK,
            set_={"count": RateLimitCounter.count + 1},
        )
        .returning(RateLimitCounter.count)
    )

    try:
        with get_limiter_engine().connect() as connection:
            count = connection.execute(stmt).scalar_one()
            _cleanup(connection, now=now)
    except Exception as exc:  # noqa: BLE001 - fail closed on any limiter error
        raise DependencyUnavailable("Rate limiter is temporarily unavailable.") from exc

    window_end = window_start + timedelta(seconds=window_seconds)
    retry_after_seconds = max(1, int((window_end - now).total_seconds()))

    return LimiterResult(
        allowed=count <= limit,
        count=count,
        retry_after_seconds=retry_after_seconds,
    )
