"""`get_session()` dependency — one `Session` per request (backend-
architecture.md §10): commit on success, rollback on exception, close in
`finally`.

Binds to the module-level request-engine singleton (`app.db.engine.get_engine()`,
lazily built from `get_settings()` on first use, never at import time) — so
importing this module in a unit test that never calls `get_session()`
requires no `DATABASE_URL`.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session as SqlAlchemySession

from app.db.engine import get_engine


def get_session() -> Iterator[SqlAlchemySession]:
    """FastAPI dependency: yield a `Session` bound to the request engine.

    Commits on success, rolls back on exception, always closes in
    `finally` — regardless of which branch ran. `expire_on_commit=False`:
    the dependency commits before the route builds its response DTO, and
    routes must still be able to read attributes off the (now-detached)
    ORM objects to populate that DTO without a second round-trip.
    """
    session = SqlAlchemySession(bind=get_engine(), expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
