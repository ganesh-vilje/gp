"""`POST /api/complaints` request/response DTOs (api-contract.md §7, T-009).

`extra="forbid"` on every model (coding-guidelines.md § Validation and
typing) — an unexpected field on the request is a `422` (this is also how
BR-009's "no government ID field" stays true structurally, AC-012), and
every response field is exhaustive, never "the object".
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_C0_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
# F7 (security review, round 2): `description` is a multi-line textarea
# (component-spec.md / screen-inventory.md) so it must accept \t, \n, \r;
# only the remaining C0 controls and DEL are rejected there.
_C0_CONTROL_RE_MULTILINE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _trim_multiline_value(value: object) -> object:
    """Shared body for every multi-line field's `mode="before"` validator
    (`CreateComplaintRequest.description`, `UpdateStatusRequest.note`): reject
    C0 controls/NUL/DEL other than \\t/\\n/\\r, then strip."""
    if isinstance(value, str):
        if _C0_CONTROL_RE_MULTILINE.search(value):
            raise ValueError("must not contain control characters")
        return value.strip()
    return value


class CreateComplaintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # api-contract.md #7: required, UUID, generated client-side once per
    # form submission and reused verbatim only on an automatic retry of the
    # *same* submit (R2-6/REL-F1).
    client_request_id: UUID
    # BR-007/BR-014: 1-100 chars after trim. The `_trim` validator below
    # strips before the length constraints below are checked, so a
    # whitespace-only value is rejected as too short, not accepted as
    # non-blank.
    citizen_name: str = Field(min_length=1, max_length=100)
    # BR-012: `^\+?[0-9]{7,15}$`, checked in `app.services.complaints`
    # (core.validation) — the max length here is a payload-size cap only
    # (15 digits + an optional leading `+` = 16).
    citizen_phone: str = Field(min_length=1, max_length=16)
    # BR-006/BR-014: 1-2000 chars after trim.
    description: str = Field(min_length=1, max_length=2000)

    @field_validator("citizen_name", "citizen_phone", mode="before")
    @classmethod
    def _trim_single_line(cls, value: object) -> object:
        # F5 (security review): reject C0 control characters (including a
        # NUL byte) before they ever reach the database. Otherwise psycopg
        # raises an uncatalogued DataError on a NUL byte at execute time,
        # surfacing as an uncaught 500 instead of a normal 422 invalid_input.
        # citizen_name/citizen_phone are single-line fields, so \t/\n/\r are
        # rejected too.
        if isinstance(value, str):
            if _C0_CONTROL_RE.search(value):
                raise ValueError("must not contain control characters")
            return value.strip()
        return value

    @field_validator("description", mode="before")
    @classmethod
    def _trim_multiline(cls, value: object) -> object:
        # F7 (security review, round 2): description is a multi-line
        # textarea and must accept \t/\n/\r; other C0 controls and NUL/DEL
        # are still rejected for the same reason as above.
        return _trim_multiline_value(value)


class ComplaintDTO(BaseModel):
    """The create response (api-contract.md §7) — exactly the fields the
    contract names, no more (no `history`; that is a separate route)."""

    model_config = ConfigDict(extra="forbid")

    id: int
    complaint_number: str
    status: str
    citizen_name: str
    citizen_phone: str
    description: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    legal_next_statuses: list[str]
    edit_window_expires_at: datetime
    duplicate: bool


class ComplaintDetailDTO(BaseModel):
    """`GET /api/complaints/{id}` and `POST /api/complaints/{id}/status`
    response (api-contract.md #9/#11) — the same fields as `ComplaintDTO`
    minus `duplicate`, which only the create route's response carries."""

    model_config = ConfigDict(extra="forbid")

    id: int
    complaint_number: str
    status: str
    citizen_name: str
    citizen_phone: str
    description: str
    created_at: datetime
    updated_at: datetime
    created_by: str
    legal_next_statuses: list[str]
    edit_window_expires_at: datetime


class UpdateStatusRequest(BaseModel):
    """`POST /api/complaints/{id}/status` request (api-contract.md #11,
    BR-002/BR-011, T-018)."""

    model_config = ConfigDict(extra="forbid")

    new_status: Literal["in_progress", "resolved", "rejected", "closed"]
    # api-contract.md #11: optional, <=2000 chars. F4 (security-review, T-018
    # rework): a status-change note is written into an immutable append-only
    # `complaint_status_history` row that can never be corrected, so — like
    # `description` — it must reject C0 control characters (including a NUL
    # byte) before they ever reach the database; otherwise a NUL byte makes
    # psycopg raise at flush time, an uncatalogued 500 rather than a normal
    # 422 invalid_input, permanently. It is multi-line like `description`
    # (\t/\n/\r are legitimate), so it reuses the same `_trim_multiline`
    # validator, not `_trim_single_line`.
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note", mode="before")
    @classmethod
    def _trim_note(cls, value: object) -> object:
        return _trim_multiline_value(value)


class EditDetailsRequest(BaseModel):
    """`POST /api/complaints/{id}/details` request (api-contract.md #12,
    FR-012/014, BR-014, AC-008, T-019). Every field is optional but at least
    one must be present — same per-field rules as `CreateComplaintRequest`
    (BR-007/012/014); `extra="forbid"` keeps this structurally free of any
    government-ID-shaped field too (BR-009, TC-API-090), same as the create
    request."""

    model_config = ConfigDict(extra="forbid")

    citizen_name: str | None = Field(default=None, min_length=1, max_length=100)
    citizen_phone: str | None = Field(default=None, min_length=1, max_length=16)
    description: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("citizen_name", "citizen_phone", mode="before")
    @classmethod
    def _trim_single_line(cls, value: object) -> object:
        if isinstance(value, str):
            if _C0_CONTROL_RE.search(value):
                raise ValueError("must not contain control characters")
            return value.strip()
        return value

    @field_validator("description", mode="before")
    @classmethod
    def _trim_multiline(cls, value: object) -> object:
        return _trim_multiline_value(value)

    @model_validator(mode="after")
    def _at_least_one_field(self) -> EditDetailsRequest:
        if self.citizen_name is None and self.citizen_phone is None and self.description is None:
            raise ValueError("At least one of citizen_name, citizen_phone, description is required")
        return self
