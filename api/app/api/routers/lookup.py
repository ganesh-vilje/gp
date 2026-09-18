"""`POST /api/lookup` (api-contract.md §4, T-010) — the AD-8/D-C public
route; the number never appears in a URL.

Never a business rule here (coding-guidelines.md § Layering) — input
normalisation/validation and the DB read live in `app.services.lookup`;
the `lookup` rate-limiter scope lives in `app.services.limiter`. This
module only checks the limiter, calls the service, and shapes the HTTP
response.

**Client-IP scope note (T-010 task row):** the full peer-gated derivation
(`core/client_ip.py`, `TRUSTED_PEER_CIDRS`/XFF handling) is T-025's scope.
Until then, `_client_ip` below reads the raw ASGI peer only — correct for
dev/test/CI, where the app is always reached directly, and the same
"unparseable/absent -> one shared fail-closed bucket" posture the later
module documents (backend-architecture.md §5 step 4) rather than trusting
any client-supplied header.

**Validation-vs-HTTP-status split (BR-015/AC-018):** `app.services.lookup`
raises the generic `ValidationFailed` for malformed input; this router is
the one place that maps it to `400` (not the usual `422`) — per
`core.errors.ValidationFailed`'s docstring, "that distinction is made by
the router that catches this, not by this class."
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.api.schemas.lookup import LookupRequest, LookupResponseDTO
from app.core import strings
from app.core.clock import now as clock_now
from app.core.errors import RateLimited, ValidationFailed, to_envelope
from app.db.session import get_session
from app.services import limiter as limiter_service
from app.services import lookup as lookup_service

router = APIRouter(prefix="/api")

_LOOKUP_SCOPE = "lookup"
# api-contract.md §4 / error-catalog.md "Rate-limit specifics":
# 20/IP/min, fixed window.
_LOOKUP_LIMIT_PER_MINUTE = 20
_LOOKUP_WINDOW_SECONDS = 60


def _client_ip(request: Request) -> str:
    client = request.client
    return client.host if client is not None else "unknown"


def _request_id_of(request: Request) -> str:
    # T-010a wires request-ID middleware; until then this falls back to a
    # fixed placeholder, matching the same fallback used throughout
    # app/middleware and app/api/exception_handlers.py.
    return str(getattr(request.state, "request_id", "unknown"))


@router.post("/lookup", response_model=LookupResponseDTO)
def public_lookup(
    body: LookupRequest,
    request: Request,
    session: Session = Depends(get_session),  # noqa: B008 - standard FastAPI DI idiom
) -> LookupResponseDTO | JSONResponse:
    limiter_result = limiter_service.check_and_increment(
        scope=_LOOKUP_SCOPE,
        key=_client_ip(request),
        limit=_LOOKUP_LIMIT_PER_MINUTE,
        window_seconds=_LOOKUP_WINDOW_SECONDS,
        now=clock_now(),
    )
    if not limiter_result.allowed:
        error = RateLimited(strings.get("errors.rate_limited.lookup"))
        return JSONResponse(
            status_code=429,
            content=to_envelope(error, request_id=_request_id_of(request)),
            headers={"Retry-After": str(limiter_result.retry_after_seconds)},
        )

    try:
        result = lookup_service.lookup(session, body.complaint_number)
    except ValidationFailed as exc:
        # BR-015/AC-018: 400, not the generic 422 — see module docstring.
        return JSONResponse(
            status_code=400,
            content=to_envelope(exc, request_id=_request_id_of(request)),
        )

    return LookupResponseDTO(
        complaint_number=result.complaint_number,
        status=result.status,
        public_update=result.public_update,
        date_logged=result.date_logged,
    )
