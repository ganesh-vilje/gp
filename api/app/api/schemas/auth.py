"""`POST /api/login` / `POST /api/logout` request/response DTOs
(api-contract.md §3/§5, T-008).

`extra="forbid"` on every model (coding-guidelines.md § Validation and
typing) — an unexpected field on the request is a `422`, and every
response field is exhaustive, never "the object".
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # api-contract.md #3: 1-30 chars; an unknown/malformed username returns
    # the identical generic failure, so the bound here is a payload-size
    # cap only, not a policy check.
    username: str = Field(min_length=1, max_length=30)
    # api-contract.md #3: 1-256 chars; the upper bound caps payload size
    # only — password policy is enforced at creation/change, not at login.
    password: str = Field(min_length=1, max_length=256)


class UserDTO(BaseModel):
    """The `user` object embedded in the login response (api-contract.md
    §3) — exactly the four fields the contract names, no more."""

    model_config = ConfigDict(extra="forbid")

    id: int
    username: str
    is_admin_clerk: bool
    must_change_password: bool


class LoginResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user: UserDTO
    csrf_token: str


class LogoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    csrf_token: str
