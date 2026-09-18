"""Unit tests for `app/api/exception_handlers.py` (T-008) — the single
exception-handler set (ADR-018): the `DomainError` -> HTTP status mapping
table, the `RequestValidationError` -> `422 invalid_input` `fields` shape,
and the unhandled-`Exception` -> generic `500` with no exception text.

A small standalone FastAPI app (not `create_app()`) wires only the three
handlers under test, so this stays a fast, DB-free unit test — no
`live_server`, no Postgres.
"""

from __future__ import annotations

import pytest
from app.api.exception_handlers import (
    domain_error_handler,
    unhandled_exception_handler,
    validation_error_handler,
)
from app.core import errors as errors_module
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

_ERROR_CLASS_BY_CODE: dict[str, type[errors_module.DomainError]] = {
    "invalid_input": errors_module.ValidationFailed,
    "not_found": errors_module.NotFound,
    "not_authenticated": errors_module.NotAuthenticated,
    "invalid_current_password": errors_module.InvalidCurrentPassword,
    "payload_too_large": errors_module.PayloadTooLarge,
    "otp_expired": errors_module.OtpExpired,
    "must_change_password": errors_module.PasswordChangeRequired,
    "forbidden": errors_module.Forbidden,
    "illegal_transition": errors_module.IllegalStatusTransition,
    "edit_window_expired": errors_module.EditWindowExpired,
    "username_taken": errors_module.UsernameTaken,
    "rate_limited": errors_module.RateLimited,
    "service_unavailable": errors_module.DependencyUnavailable,
}

# error-catalog.md "## Codes" table.
_EXPECTED_STATUS_BY_CODE: dict[str, int] = {
    "invalid_input": 422,
    "not_found": 404,
    "not_authenticated": 401,
    "invalid_current_password": 422,
    "payload_too_large": 413,
    "otp_expired": 401,
    "must_change_password": 403,
    "forbidden": 403,
    "illegal_transition": 422,
    "edit_window_expired": 422,
    "username_taken": 409,
    "rate_limited": 429,
    "service_unavailable": 503,
}


class _ValidateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


def _build_probe_app() -> FastAPI:
    app = FastAPI()
    app.add_exception_handler(errors_module.DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/raise/{code}")
    def _raise(code: str) -> None:
        raise _ERROR_CLASS_BY_CODE[code]("boom")

    @app.get("/raise-unmapped")
    def _raise_unmapped() -> None:
        # `AppendOnlyViolation` deliberately has no row in the mapping
        # table (see its docstring) — must fall back to the 500 default.
        raise errors_module.AppendOnlyViolation("should never happen")

    @app.get("/blow-up")
    def _blow_up() -> None:
        raise RuntimeError("never-echo-this-secret-password-marker")

    @app.post("/validate")
    def _validate(body: _ValidateBody) -> dict[str, str]:
        return {"name": body.name}

    return app


@pytest.mark.parametrize("code", sorted(_EXPECTED_STATUS_BY_CODE))
def test_domain_error_mapping_table(code: str) -> None:
    client = TestClient(_build_probe_app(), raise_server_exceptions=False)

    response = client.get(f"/raise/{code}")

    assert response.status_code == _EXPECTED_STATUS_BY_CODE[code]
    body = response.json()
    assert body["error"]["code"] == code
    assert "request_id" in body["error"]


def test_unmapped_domain_error_falls_back_to_500_internal_error() -> None:
    client = TestClient(_build_probe_app(), raise_server_exceptions=False)

    response = client.get("/raise-unmapped")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"


def test_unhandled_exception_returns_generic_500_with_no_exception_text() -> None:
    client = TestClient(_build_probe_app(), raise_server_exceptions=False)

    response = client.get("/blow-up")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert "request_id" in body["error"]
    assert "never-echo-this-secret-password-marker" not in response.text
    assert "RuntimeError" not in response.text
    assert "fields" not in body["error"]


def test_validation_error_reports_fields_without_pydantic_internals_or_values() -> None:
    client = TestClient(_build_probe_app(), raise_server_exceptions=False)

    response = client.post("/validate", json={"name": 123, "extra": "nope-should-not-echo"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "invalid_input"
    assert set(body["error"]["fields"]) == {"name", "extra"}
    assert body["error"]["fields"]["extra"] == "unexpected_field"
    assert "nope-should-not-echo" not in response.text
    assert "pydantic" not in response.text.lower()


def test_validation_error_reports_missing_field_as_required() -> None:
    client = TestClient(_build_probe_app(), raise_server_exceptions=False)

    response = client.post("/validate", json={})

    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {"name": "required"}
