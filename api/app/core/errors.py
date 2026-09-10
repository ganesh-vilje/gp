"""Domain error taxonomy + the single HTTP error envelope (ADR-018).

Domain services raise these typed errors; a single exception-handler set
(added in a later task, in `app/api/`) converts each one to the envelope
this module serialises: `{"error":{"code","message","fields","request_id"}}`
(backend-architecture.md §6, error-catalog.md). This module intentionally
does **not** import FastAPI or know about HTTP status codes — the HTTP
mapping is an API-layer concern (coding-guidelines.md § Layering; noted as
a dependency for T-006).

`code` values are exactly the enum in error-catalog.md — no new code
without updating that document first. `invalid_credentials` must never
appear anywhere in this module (error-catalog.md rev 4, R4-4): every failed
login is `not_authenticated`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class DomainError(Exception):
    """Base class for every typed domain error.

    `fields` is present only for field-level errors (`invalid_input`,
    `invalid_current_password`) and, per error-catalog.md, holds
    `{field_name: reason_code}` only — never the submitted value.
    """

    code: str = "internal_error"

    def __init__(self, message: str, *, fields: Mapping[str, str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.fields: dict[str, str] | None = dict(fields) if fields is not None else None


class ValidationFailed(DomainError):
    """Pydantic or `core.validation` rule failure. HTTP 422, or 400 for the
    public-lookup format case (BR-015/AC-018) — that distinction is made by
    the router that catches this, not by this class."""

    code = "invalid_input"


class NotFound(DomainError):
    """No matching row for a well-formed identifier/lookup key."""

    code = "not_found"


class NotAuthenticated(DomainError):
    """No valid session presented, or a failed login (error-catalog.md:
    strictly and only these two cases — never a field error inside a valid
    session)."""

    code = "not_authenticated"


class InvalidCurrentPassword(DomainError):
    """Wrong `current_password` on a voluntary password change — a field
    error inside a valid, untouched session, never `not_authenticated`."""

    code = "invalid_current_password"


class PayloadTooLarge(DomainError):
    """`Content-Length` (or a length-less stream) exceeds `MAX_REQUEST_BODY_BYTES`."""

    code = "payload_too_large"


class OtpExpired(DomainError):
    """Un-consumed one-time password past `OTP_EXPIRY_HOURS`."""

    code = "otp_expired"


class PasswordChangeRequired(DomainError):
    """Authenticated with `must_change_password=true`, on any route other
    than the three exempt ones."""

    code = "must_change_password"


class Forbidden(DomainError):
    """Authenticated but wrong role, or a failed CSRF/Origin check."""

    code = "forbidden"


class IllegalStatusTransition(DomainError):
    """Status update requests a transition outside the frozen map (BR-002)."""

    code = "illegal_transition"


class EditWindowExpired(DomainError):
    """Edit-details attempted after `EDIT_WINDOW_DAYS`."""

    code = "edit_window_expired"


class UsernameTaken(DomainError):
    """Account creation with a username already in use (BR-016)."""

    code = "username_taken"


class RateLimited(DomainError):
    """A rate-limiter ceiling was reached; the raiser attaches `Retry-After`
    separately (an HTTP-layer concern)."""

    code = "rate_limited"


class DependencyUnavailable(DomainError):
    """The limiter or the database is unreachable (fail-closed)."""

    code = "service_unavailable"


def to_envelope(error: DomainError, *, request_id: str) -> dict[str, Any]:
    """Serialise `error` into the single envelope shape (ADR-018).

    `fields` is included only when the error carries field-level detail —
    matching error-catalog.md's "present only for `invalid_input`" rule
    (also true, structurally, for `invalid_current_password`).
    """
    body: dict[str, Any] = {
        "code": error.code,
        "message": error.message,
        "request_id": request_id,
    }
    if error.fields is not None:
        body["fields"] = error.fields
    return {"error": body}
