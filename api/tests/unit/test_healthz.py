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
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("USERNAME_HASH_SALT", "y" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "https://app.example.in")
os.environ.setdefault("ALLOWED_HOSTS", "testserver,127.0.0.1,localhost")

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


def _build_settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "environment": "dev",
        "database_url": "postgresql+psycopg://x:x@localhost:5432/x",
        "secret_key": "s" * 32,
        "username_hash_salt": "u" * 32,
        "allowed_origins": ("http://localhost:3000",),
        "allowed_hosts": ("localhost",),
    }
    defaults.update(overrides)
    return Settings(**defaults)  # type: ignore[arg-type]


def test_settings_repr_shows_only_field_names_and_environment_value() -> None:
    settings = _build_settings(environment="dev")

    text = repr(settings)

    assert "environment" in text
    assert "dev" in text
    # Locks the contract for future secret fields: __repr__ must never fall
    # back to the dataclass default, which would print every field's value.
    assert text.startswith("Settings(")


def test_settings_repr_redacts_database_url() -> None:
    settings = _build_settings(
        database_url="postgresql+psycopg://secretuser:secretpass@db/panchayat"
    )

    text = repr(settings)

    assert "secretuser" not in text
    assert "secretpass" not in text
    assert "database_url=<redacted>" in text


def test_settings_repr_redacts_secret_key_and_username_hash_salt() -> None:
    settings = _build_settings(
        secret_key="super-secret-csrf-key-value-000",
        username_hash_salt="super-secret-username-salt-0000",
    )

    text = repr(settings)

    assert "super-secret-csrf-key-value-000" not in text
    assert "super-secret-username-salt-0000" not in text
    assert "secret_key=<redacted>" in text
    assert "username_hash_salt=<redacted>" in text


def test_get_settings_missing_database_url_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_get_settings_missing_secret_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_get_settings_missing_username_hash_salt_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.delenv("USERNAME_HASH_SALT", raising=False)

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_get_settings_missing_allowed_origins_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_get_settings_parses_comma_separated_allowed_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://www.example.in, https://api.example.in")

    settings = get_settings()

    assert settings.allowed_origins == ("https://www.example.in", "https://api.example.in")


# --- F2 (T-006 review): ALLOWED_ORIGINS entries fail closed ---------------


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "null",
        "https://example.in/some/path",
        "https://example.in?x=1",
        "https://example.in#fragment",
        "not-a-url-at-all",
        "ftp://example.in",
    ],
)
def test_get_settings_rejects_malformed_allowed_origin_entries(
    monkeypatch: pytest.MonkeyPatch, origin: str
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("ALLOWED_ORIGINS", origin)

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_get_settings_rejects_non_https_origin_outside_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://example.in")

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_get_settings_accepts_http_localhost_origin_in_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")

    settings = get_settings()

    assert settings.allowed_origins == ("http://localhost:3000",)


def test_get_settings_accepts_a_well_formed_https_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "prod")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://www.example.in")

    settings = get_settings()

    assert settings.allowed_origins == ("https://www.example.in",)


# --- F3 (T-006 review): SECRET_KEY / USERNAME_HASH_SALT length + distinctness --


def test_get_settings_rejects_short_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("SECRET_KEY", "too-short")

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_get_settings_rejects_short_username_hash_salt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("USERNAME_HASH_SALT", "too-short")

    with pytest.raises(ImproperlyConfigured):
        get_settings()


@pytest.mark.parametrize(
    "host",
    [
        "*",
        "null",
        "http://example.in",
        "example.in/path",
        "example.in?x=1",
        "example.in#frag",
        "example.in:8080",
        "a*b.example.in",
    ],
)
def test_get_settings_rejects_malformed_allowed_host_entries(
    monkeypatch: pytest.MonkeyPatch, host: str
) -> None:
    """F2 (T-010a review): ALLOWED_HOSTS=* (or any other malformed entry)
    must raise at settings load, fail-closed — Starlette sets
    `allow_any=True` (accepts every Host) when '*' is anywhere in the list,
    which would silently disable TrustedHostMiddleware entirely."""
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("ALLOWED_HOSTS", host)

    with pytest.raises(ImproperlyConfigured):
        get_settings()


def test_get_settings_accepts_wildcard_subdomain_allowed_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.setenv("ALLOWED_HOSTS", "*.example.in")

    settings = get_settings()

    assert settings.allowed_hosts == ("*.example.in",)


def test_get_settings_rejects_equal_secret_key_and_username_hash_salt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    same_value = "z" * 32
    monkeypatch.setenv("SECRET_KEY", same_value)
    monkeypatch.setenv("USERNAME_HASH_SALT", same_value)

    with pytest.raises(ImproperlyConfigured):
        get_settings()
