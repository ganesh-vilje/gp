"""Two engines per worker (backend-architecture.md §10, ADR-005):

- request engine: `pool_size=4, max_overflow=2, pool_pre_ping=True,
  pool_recycle=1800`; the append-only guard (`app/db/guard.py`) is attached
  here.
- limiter engine: `pool_size=4, max_overflow=0` (deliberate — the limiter
  must not expand connections under the load it exists to refuse),
  `AUTOCOMMIT` isolation, so a counter write survives the surrounding
  request's rollback (TC-SEC-024).

Both set `statement_timeout=10s` on connect via psycopg's `options`
connect arg, and `hide_parameters=True` so bound values (which may be
citizen PII) never appear in exception text or logs (security-
architecture.md §8).

`build_request_engine`/`build_limiter_engine` are the plain factories
(used directly by tests that want their own throwaway engine).
`get_engine`/`get_limiter_engine` are the per-worker singletons every
application code path should use instead — each lazily builds its engine
from `Settings` on first call and memoises it, so no caller can
accidentally construct a second pool alongside the real one.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.db.guard import register_append_only_guard
from app.settings import Settings, get_settings

_STATEMENT_TIMEOUT_CONNECT_ARGS = {"options": "-c statement_timeout=10000"}

_request_engine: Engine | None = None
_limiter_engine: Engine | None = None


def build_request_engine(settings: Settings) -> Engine:
    """Build the request engine: pool 4+2, pre-ping, 30-minute recycle.

    The append-only guard is registered on this engine — it is the one
    used for ordinary request-scoped reads/writes (app/db/session.py).
    """
    engine = create_engine(
        settings.database_url,
        pool_size=4,
        max_overflow=2,
        pool_pre_ping=True,
        pool_recycle=1800,
        hide_parameters=True,
        connect_args=_STATEMENT_TIMEOUT_CONNECT_ARGS,
    )
    register_append_only_guard(engine)
    return engine


def build_limiter_engine(settings: Settings) -> Engine:
    """Build the limiter engine: pool 4+0, AUTOCOMMIT.

    No append-only guard here — the limiter only ever writes
    `rate_limit_counter`, never one of the three guarded tables.
    """
    return create_engine(
        settings.database_url,
        pool_size=4,
        max_overflow=0,
        isolation_level="AUTOCOMMIT",
        hide_parameters=True,
        connect_args=_STATEMENT_TIMEOUT_CONNECT_ARGS,
    )


def get_engine() -> Engine:
    """Lazily build and memoise the per-worker request engine singleton."""
    global _request_engine
    if _request_engine is None:
        _request_engine = build_request_engine(get_settings())
    return _request_engine


def get_limiter_engine() -> Engine:
    """Lazily build and memoise the per-worker limiter engine singleton."""
    global _limiter_engine
    if _limiter_engine is None:
        _limiter_engine = build_limiter_engine(get_settings())
    return _limiter_engine
