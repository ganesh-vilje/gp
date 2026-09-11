"""`GET /healthz` (api-contract.md §1) — moved out of `app/main.py` at
T-008 (T-001 review low finding: the route belongs in its own router
module, per backend-architecture.md §1's module layout)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas.health import HealthzResponse

router = APIRouter()


@router.get("/healthz", response_model=HealthzResponse)
def healthz() -> HealthzResponse:
    return HealthzResponse(status="ok")
