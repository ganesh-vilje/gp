"""The single exception-handler set (ADR-018, backend-architecture.md §6).

Three handlers, registered once in `create_app()` (`app/main.py`) — never a
second error-handling scheme anywhere else (coding-guidelines.md §
Forbidden patterns):

1. `DomainError` (and every subclass, matched via the MRO by Starlette's
   own handler lookup) → the envelope, HTTP status from
   `_STATUS_BY_ERROR_TYPE` (error-catalog.md's table).
2. `RequestValidationError` (FastAPI/pydantic request-body validation) →
   `422 invalid_input` with `fields` keyed by field name and a catalogued
   reason code — never a pydantic message or the submitted value
   (coding-guidelines.md § Error handling: "never put a submitted value in
   `fields`").
3. Any other unhandled `Exception` → `500 internal_error`, logged at error
   level with the request id **only** — never the exception text, which
   could contain a bound value (coding-guidelines.md § PII and logging).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any, cast

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from app.core import strings
from app.core.errors import (
    DependencyUnavailable,
    DomainError,
    EditWindowExpired,
    Forbidden,
    IllegalStatusTransition,
    InvalidCurrentPassword,
    NotAuthenticated,
    NotFound,
    OtpExpired,
    PasswordChangeRequired,
    PayloadTooLarge,
    RateLimited,
    UsernameTaken,
    ValidationFailed,
    to_envelope,
)

logger = logging.getLogger("app.errors")

# error-catalog.md "## Codes" / backend-architecture.md §6 "## Error model".
# A `DomainError` subclass with no row here (e.g. `AppendOnlyViolation`,
# which deliberately keeps the base `internal_error` code — see its
# docstring) falls through to the 500 default below.
_STATUS_BY_ERROR_TYPE: dict[type[DomainError], int] = {
    ValidationFailed: 422,
    NotFound: 404,
    NotAuthenticated: 401,
    InvalidCurrentPassword: 422,
    PayloadTooLarge: 413,
    OtpExpired: 401,
    PasswordChangeRequired: 403,
    Forbidden: 403,
    IllegalStatusTransition: 422,
    EditWindowExpired: 422,
    UsernameTaken: 409,
    RateLimited: 429,
    DependencyUnavailable: 503,
}
_DEFAULT_DOMAIN_ERROR_STATUS = 500


def _request_id_of(request: Request) -> str:
    # T-010a wires the request-ID middleware; until then this falls back to
    # a fixed placeholder rather than raising (matches the same fallback in
    # middleware/csrf.py and middleware/authz.py).
    return str(getattr(request.state, "request_id", "unknown"))


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    # FastAPI only ever invokes this handler for `DomainError` (registered
    # via `app.add_exception_handler(DomainError, ...)`) or one of its
    # subclasses (Starlette's handler lookup walks the MRO) — the signature
    # is `Exception` only because that is what `add_exception_handler`
    # requires.
    error = cast(DomainError, exc)
    status_code = _STATUS_BY_ERROR_TYPE.get(type(error), _DEFAULT_DOMAIN_ERROR_STATUS)
    return JSONResponse(
        status_code=status_code,
        content=to_envelope(error, request_id=_request_id_of(request)),
    )


# Pydantic v2 error `type` -> a stable, catalogued reason code. Never the
# pydantic message itself and never the submitted value (coding-
# guidelines.md § Error handling) — this table is intentionally small and
# generic; a route with a business-specific format rule (e.g. the
# complaint-number checksum) raises its own `ValidationFailed` with its own
# `fields` reason instead of relying on this generic fallback.
_VALIDATION_REASON_BY_PYDANTIC_TYPE: dict[str, str] = {
    "missing": "required",
    "string_too_short": "too_short",
    "string_too_long": "too_long",
    "extra_forbidden": "unexpected_field",
    "string_type": "invalid_format",
    "int_type": "invalid_format",
    "int_parsing": "invalid_format",
    "bool_type": "invalid_format",
    "bool_parsing": "invalid_format",
}
_DEFAULT_VALIDATION_REASON = "invalid_format"

# `loc` tuples FastAPI/pydantic produce for a JSON body field look like
# `("body", "username")`; strip the location-kind markers so `fields` is
# keyed by the field name a client actually sent, matching error-
# catalog.md's `{field_name: reason_code}` shape.
_LOC_MARKERS = frozenset({"body", "query", "path", "header", "cookie"})


def _validation_field_name(loc: Sequence[int | str]) -> str:
    parts = [str(part) for part in loc if part not in _LOC_MARKERS]
    return ".".join(parts) if parts else "_"


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    validation_error = cast(RequestValidationError, exc)
    fields: dict[str, str] = {}
    for error in validation_error.errors():
        field_name = _validation_field_name(tuple(error.get("loc", ())))
        reason = _VALIDATION_REASON_BY_PYDANTIC_TYPE.get(
            str(error.get("type", "")), _DEFAULT_VALIDATION_REASON
        )
        fields[field_name] = reason

    body: dict[str, Any] = {
        "error": {
            "code": "invalid_input",
            "message": strings.get("errors.invalid_input"),
            "fields": fields,
            "request_id": _request_id_of(request),
        }
    }
    return JSONResponse(status_code=422, content=body)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = _request_id_of(request)
    # Never the exception text — it can contain a bound value (a password,
    # a complaint number, ...) even with hide_parameters on; log only the
    # request id, the one thing an operator needs to find the matching
    # stdout log line (error-catalog.md).
    logger.error("Unhandled exception while handling request %s", request_id)
    body: dict[str, Any] = {
        "error": {
            "code": "internal_error",
            "message": strings.get("errors.internal_error"),
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=500, content=body)
