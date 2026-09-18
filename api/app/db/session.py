"""`get_session()` dependency — one `Session` per request (backend-
architecture.md §10): commit on success, rollback on exception, close in
`finally`.

Binds to the module-level request-engine singleton (`app.db.engine.get_engine()`,
lazily built from `get_settings()` on first use, never at import time) — so
importing this module in a unit test that never calls `get_session()`
requires no `DATABASE_URL`.

**B-001 root cause note (2026-09-18):** the code *after* `yield` in a plain
`Depends(...)` generator dependency does **not** run before the response is
sent to the client on this FastAPI version (0.141.1) — `fastapi/routing.py`'s
`request_response()` resolves path-operation-level `Depends(...)` against
`scope["fastapi_inner_astack"]`, which is only closed *after*
`await response(scope, receive, send)` has already transmitted the response
(see `request_response()`: `response = await f(request)` runs the endpoint,
then `await response(...)` sends it, and only then does the `async with
AsyncExitStack() as request_stack:` block — the one holding this
generator's post-`yield` code — exit). This was verified directly: a
sequential login-then-immediate-request repro
(`tests/integration/test_b001_repro.py`, deleted after this investigation)
instrumented with wall-clock timestamps showed the client receiving the
`200` login response *before* this function's `session.commit()` call had
even started executing, on every reproduction of the bug — not a
cross-connection DB read-visibility race (Postgres MVCC under READ
COMMITTED, confirmed the only isolation level in play here, guarantees a
new transaction sees all prior commits immediately; there was no such
race), not a test-harness cookie bug, and not a middleware-ordering bug.
`request.state.csrf_token` ends up `None` (the just-created session row's
own `SELECT` genuinely finds nothing yet), so `middleware/csrf.py` falls
into its anonymous-CSRF branch and 403s (no `__Host-csrfseed` cookie was
sent) — the intermittent 401/403 B-001 tracked.

**Fix:** the commit here must remain (`get_session()` is still the
backstop that guarantees every session closes, cleanly, exactly once,
including on unhandled-exception paths that never reach a "successful"
write) but it can no longer be the *only* place a durable write commits —
every route that performs a write a client may immediately depend on
(`app/api/routers/auth.py`'s `login`/`logout`,
`app/api/routers/complaints.py`'s `create_complaint`/
`update_complaint_status`) now calls `session.commit()` itself, inline,
as the last statement before returning — after the response DTO and any
response-header/cookie mutations are prepared, so nothing that can raise
runs after the write is durable (security review F1) — i.e. inside
`f(request)` at line ~144 of FastAPI's `request_response()`, strictly
before the response is sent. The commit performed here, later, is then a
safe no-op (no pending state left to flush) for those routes, and remains
the *only* commit for any future route that does not need this guarantee.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session as SqlAlchemySession

from app.db.engine import get_engine


def get_session() -> Iterator[SqlAlchemySession]:
    """FastAPI dependency: yield a `Session` bound to the request engine.

    Commits on success, rolls back on exception, always closes in
    `finally` — regardless of which branch ran. `expire_on_commit=False`:
    routes must still be able to read attributes off the (now-detached) ORM
    objects to populate their response DTO without a second round-trip.

    This function's own `session.commit()` runs **after** the response has
    already been sent to the client (see this module's docstring, "B-001
    root cause note") — it is a backstop, never the synchronization point a
    route can rely on for "this write is durable by the time my response
    reaches the caller." A route whose write a client might immediately act
    on (e.g. by presenting a cookie/token minted from it) must call
    `session.commit()` itself before returning.
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
