"""`GET /healthz` response DTO (api-contract.md § 1, moved here from
`app/main.py` at T-008 per T-001 review low finding — the DTO belongs in
`app/api/schemas/`, not inline in the app factory)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class HealthzResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
