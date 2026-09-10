"""Small tests for `core.clock` (not test-case-mapped; supports the
clock-injection decision in implementation-plan.md § Clock injection
decision)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.core import clock


def test_now_returns_timezone_aware_utc_datetime() -> None:
    """Supporting test: `now()` is timezone-aware UTC."""
    value = clock.now()

    assert value.tzinfo is not None
    assert value.utcoffset() == UTC.utcoffset(None)


def test_now_is_monkeypatchable(monkeypatch: pytest.MonkeyPatch) -> None:
    """Supporting test: `core.clock.now` can be monkeypatched to a fixed
    value, per the clock-injection decision's `conftest.py` fixture design."""
    fixed = datetime(2026, 1, 1, tzinfo=UTC)
    monkeypatch.setattr(clock, "now", lambda: fixed)

    assert clock.now() == fixed
