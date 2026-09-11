"""Unit tests for `tests.conftest`'s `live_server` cleanup helpers (T-006a
F1 code-reviewer rework) — no DB, no real uvicorn server: a fake `server`
object (just a `should_exit`/`started` attribute) and a real, short-lived
`threading.Thread` stand in for the real ones.
"""

from __future__ import annotations

import os
import threading
import time
from unittest.mock import Mock

import pytest
from app.db import engine as engine_module

from tests.conftest import (
    _live_server_cleanup,
    _live_server_set_env,
    _wait_for_server_started,
)


class _FakeServer:
    def __init__(self, *, started: bool) -> None:
        self.started = started
        self.should_exit = False


def _run_until_should_exit(server: _FakeServer) -> None:
    while not server.should_exit:
        time.sleep(0.01)


def test_cleanup_restores_env_stops_thread_and_resets_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://prior:prior@localhost/prior_db")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://t:t@localhost/panchayat_test")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("USERNAME_HASH_SALT", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    env = _live_server_set_env()
    assert os.environ["DATABASE_URL"] == "postgresql+psycopg://t:t@localhost/panchayat_test"
    assert "SECRET_KEY" in os.environ  # introduced by _live_server_set_env

    fake_engine = Mock()
    engine_module._request_engine = fake_engine
    server = _FakeServer(started=True)
    thread = threading.Thread(target=_run_until_should_exit, args=(server,), daemon=True)
    thread.start()

    _live_server_cleanup(server, thread, env)

    assert server.should_exit is True
    assert not thread.is_alive()
    fake_engine.dispose.assert_called_once()
    assert engine_module._request_engine is None
    assert os.environ["DATABASE_URL"] == "postgresql+psycopg://prior:prior@localhost/prior_db"
    assert "SECRET_KEY" not in os.environ
    assert "USERNAME_HASH_SALT" not in os.environ
    assert "ALLOWED_ORIGINS" not in os.environ


def test_startup_timeout_path_raises_and_cleanup_still_restores_everything(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simulates the fixture's own `except Exception: _live_server_cleanup(...); raise`
    branch: `server.started` never flips, `_wait_for_server_started` raises,
    and the same cleanup call the fixture makes on that path must still stop
    the thread and restore the environment."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://prior:prior@localhost/prior_db")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://t:t@localhost/panchayat_test")
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    env = _live_server_set_env()
    assert "ENVIRONMENT" in os.environ  # introduced by _live_server_set_env

    engine_module._request_engine = None
    server = _FakeServer(started=False)  # never flips - the timeout case
    thread = threading.Thread(target=_run_until_should_exit, args=(server,), daemon=True)
    thread.start()

    with pytest.raises(RuntimeError, match="did not report started"):
        try:
            _wait_for_server_started(server, timeout=0.05)
        except Exception:
            _live_server_cleanup(server, thread, env)
            raise

    assert server.should_exit is True
    assert not thread.is_alive()
    assert os.environ["DATABASE_URL"] == "postgresql+psycopg://prior:prior@localhost/prior_db"
    assert "ENVIRONMENT" not in os.environ
