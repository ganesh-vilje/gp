"""Request-ID + security-headers middleware — row 2 of the ADR-007
middleware chain (backend-architecture.md §2, security-architecture.md
§7).

Two responsibilities, both required at this exact position (outermost of
the three T-010a rows, i.e. it runs before `TrustedHostMiddleware` rejects
nothing it needs and after nothing — see `app/main.py`'s registration
comment for the full outermost/innermost picture):

1. **Body-size rejection ahead of body parsing (rev 3, SEC-S8; threat
   #37).** A `Content-Length` above `MAX_REQUEST_BODY_BYTES` (64 KB), or one
   that is unparseable or negative, is rejected with `413 payload_too_large`
   before `call_next` is ever invoked — the route handler never starts, and
   no field-level validation ever sees the body. A request with no
   `Content-Length` (a length-less / chunked stream) is read up front,
   capped at the same figure while reading, and — only if it stayed under
   the cap — handed to the downstream app by setting `request._body`
   directly (the same attribute `Request.body()` itself populates).
   `BaseHTTPMiddleware.call_next` is wired to `request.wrapped_receive`,
   which prefers `request._body` when set (starlette's `base.py`); if
   `_body` is unset and the stream has already been drained, it returns an
   empty body — so `_body` is the only attribute that reliably replays a
   drained stream to the downstream handler (verified against starlette
   1.6.0, the currently pinned version — re-verify if that version
   changes).
2. **Request-ID + the fixed set of security response headers**
   (backend-architecture.md §2 row 2): mints an `X-Request-ID` if the
   client did not send one, stores it on `request.state.request_id` (every
   error envelope and `middleware/csrf.py`/`middleware/authz.py` read this
   — see their own `_request_id_of` fallbacks), and sets it plus HSTS,
   `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
   `Referrer-Policy: no-referrer`, `Permissions-Policy`, the fixed `CSP`,
   and — on authenticated or public-lookup responses only —
   `Cache-Control: no-store` (security-architecture.md §7/§1).
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core import strings
from app.core.errors import PayloadTooLarge, to_envelope

# error-catalog.md R3-6/SEC-S8: "64 KB is ~30x the largest legitimate body."
MAX_REQUEST_BODY_BYTES = 65536

_REQUEST_ID_HEADER = "x-request-id"

# F5 (security review): only an inbound X-Request-ID matching this pattern is
# ever propagated into logs/error envelopes/response headers verbatim — an
# arbitrary client-supplied value could otherwise poison the operator's audit
# trail (log injection) or push an oversized value into logs. Anything else
# (missing, too short/long, disallowed characters) results in a fresh UUID4
# being minted instead, exactly as if the header had not been sent.
_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

_SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    ("Strict-Transport-Security", "max-age=31536000; includeSubDomains"),
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    ("Permissions-Policy", "geolocation=(), camera=(), microphone=()"),
    (
        "Content-Security-Policy",
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    ),
)

# Public-lookup routes never carry an authenticated session, so the
# "authenticated or lookup" `Cache-Control: no-store` rule (security-
# architecture.md §7) needs an explicit path check for the anonymous half.
_LOOKUP_PATH_PREFIX = "/api/lookup"


def _payload_too_large(request_id: str) -> Response:
    error = PayloadTooLarge(strings.get("errors.payload_too_large"))
    return JSONResponse(status_code=413, content=to_envelope(error, request_id=request_id))


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        inbound_request_id = request.headers.get(_REQUEST_ID_HEADER)
        if inbound_request_id and _REQUEST_ID_PATTERN.match(inbound_request_id):
            request_id = inbound_request_id
        else:
            request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        content_length = request.headers.get("content-length")
        if content_length is not None:
            # F6: an unparseable or negative Content-Length must never fall
            # through with no size check at all — reject fail-closed rather
            # than silently letting the request proceed unchecked.
            try:
                declared_length = int(content_length)
            except ValueError:
                return _payload_too_large(request_id)
            if declared_length < 0 or declared_length > MAX_REQUEST_BODY_BYTES:
                return _payload_too_large(request_id)
        else:
            # F1: `request.stream()` + overriding `request._receive` does NOT
            # reliably make `BaseHTTPMiddleware.call_next` replay the body —
            # Starlette wires `call_next` to `request.wrapped_receive`, which
            # (see starlette/middleware/base.py, verified against 1.6.0, the
            # currently pinned version — re-verify if that version changes)
            # prefers `request._body` when set; if `_body` is unset and the
            # stream has already been drained, it returns an empty body.
            # `Request.body()` populates `request._body`, which
            # `wrapped_receive` DOES correctly honor, so read the
            # length-less body via a capped incremental accumulation and set
            # `request._body` directly (the same attribute `body()` itself
            # would set), never touching `_receive`.
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > MAX_REQUEST_BODY_BYTES:
                    return _payload_too_large(request_id)
            request._body = bytes(body)  # noqa: SLF001 - same attr Request.body() sets

        response = await call_next(request)

        response.headers[_REQUEST_ID_HEADER] = request_id
        for name, value in _SECURITY_HEADERS:
            response.headers[name] = value

        is_authenticated = getattr(request.state, "user", None) is not None
        is_lookup = request.url.path.startswith(_LOOKUP_PATH_PREFIX)
        # F4: also cover the OUTGOING response minting a fresh session
        # cookie / CSRF token (login, logout) — those responses must never
        # be cached even though the INBOUND request carried no session yet.
        sets_cookie = "set-cookie" in response.headers
        if is_authenticated or is_lookup or sets_cookie:
            response.headers["Cache-Control"] = "no-store"

        return response
