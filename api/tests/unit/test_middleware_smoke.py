"""Minimal TestClient smoke test for the rows 4-6 middleware chain
(backend-architecture.md §2) registered by `create_app()`. Full
middleware end-to-end behaviour (including rows 1-3 and the exact final
sequence) is T-008/T-010a — this is deliberately cheap: no database is
touched (no session cookie is ever sent), so `/healthz` and a fake
protected route are enough to prove rows 4+6 compose correctly."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("USERNAME_HASH_SALT", "y" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "https://app.example.in")

from app.main import create_app  # noqa: E402


@pytest.fixture
def app_with_fake_protected_route(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    app = create_app()

    @app.get("/api/__test_only_protected_route")
    def _fake_protected_route() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_unauthenticated_healthz_returns_200(
    app_with_fake_protected_route,  # noqa: ANN001
) -> None:
    client = TestClient(app_with_fake_protected_route)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unauthenticated_request_to_a_non_allow_listed_route_returns_401_envelope(
    app_with_fake_protected_route,  # noqa: ANN001
) -> None:
    client = TestClient(app_with_fake_protected_route)

    response = client.get("/api/__test_only_protected_route")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "not_authenticated"
    assert "request_id" in body["error"]
