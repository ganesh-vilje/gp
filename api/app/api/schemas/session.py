"""`GET /api/session` — two response variants (api-contract.md §2, T-010).

`extra="forbid"` on every model; each variant is exhaustive.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class AnonymousSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authenticated: Literal[False]
    csrf_token: str


class SessionUserDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    username: str
    is_admin_clerk: bool
    must_change_password: bool


class AuthenticatedSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authenticated: Literal[True]
    csrf_token: str
    user: SessionUserDTO
