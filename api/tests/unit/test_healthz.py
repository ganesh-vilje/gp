"""Unit tests for `/healthz`, doc-URL gating (BR-010) and Settings (T-001)."""

from __future__ import annotations

import os

# `app.main` builds a module-level FastAPI app at import time (required so
# `uvicorn app.main:app` / `gunicorn app.main:app` in project-config.md work
# without a --factory flag). Since get_settings() now fails closed with no
# default (T-001 review F1), merely *importing* app.main requires ENVIRONMENT
# to already be set in the process. `setdefault` only supplies a value for
# module collection; every test below sets its own value with
# `monkeypatch.setenv` and calls `create_app()` again to build its own app.
os.environ.setdefault("ENVIRONMENT", "test")

import pytest  # noqa: E402
from app.main import create_app  # noqa: E402
from app.settings import ImproperlyConfigured, Settings, get_settings  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def test_healthz_returns_200_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_docs_disabled_in_prod_404(monkeypatch: pytest.MonkeyPatch, path: str) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")
    client = TestClient(create_app())

    response = client.get(path)

    assert response.status_code == 404


@pytest.mark.parametrize("environment", ["dev", "test", "staging"])
def test_openapi_enabled_outside_prod_200(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", environment)
    client = TestClient(create_app())

    response = client.get("/openapi.json")

    assert response.status_code == 200


def test_get_settings_unset_environment_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_get_settings_empty_environment_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "")

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_get_settings_wrong_case_environment_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "Prod")

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_settings_repr_shows_only_field_names_and_environment_value() -> None:
    settings = Settings(environment="dev")

    text = repr(settings)

    assert "environment" in text
    assert "dev" in text
    # Locks the contract for future secret fields: __repr__ must never fall
    # back to the dataclass default, which would print every field's value.
    assert text.startswith("Settings(")
