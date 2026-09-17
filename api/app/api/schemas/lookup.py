"""`POST /api/lookup` request/response DTOs (api-contract.md §4, T-010).

`extra="forbid"` everywhere — an unexpected field on the request is a
`422`, and the response is the exhaustive public DTO (BR-005/NFR-009):
no `citizen_name`, `citizen_phone`, or clerk note field exists on this
model at all.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class LookupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Raw as typed by the citizen (api-contract.md §4) — normalised and
    # validated server-side (BR-015) before any DB access. `min_length=0`
    # is deliberate: BR-015 requires blank/whitespace-only input to fail
    # with the *same* 400 `lookup.invalid_format` the malformed-format case
    # gets, not a generic 422 from Pydantic's own length check — so the
    # empty string is let through to `app.services.lookup`, which raises
    # the typed error this router maps to 400. The upper bound is a
    # payload-size cap only (a well-formed number is 9 symbols, plus room
    # for stray spaces/hyphens a citizen might type/paste).
    complaint_number: str = Field(min_length=0, max_length=64)


class LookupResponseDTO(BaseModel):
    """The entire public DTO, exhaustive (api-contract.md §4)."""

    model_config = ConfigDict(extra="forbid")

    complaint_number: str
    status: str
    public_update: str
    date_logged: date
