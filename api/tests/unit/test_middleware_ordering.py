"""TC-SEC-039 (test-cases.md) — walks the *actual* registered middleware
stack `create_app()` builds and asserts the exact final ADR-007 sequence
(backend-architecture.md §2 rows 1-6), plus TC-SEC-027/TC-SEC-028
(backend-architecture.md SEC-T24/SEC-T31, SEC-S8): the CORS
`allow_methods` invariant and the 413 body-size rejection ahead of the
route handler.

No database, no `live_server` — `Starlette.user_middleware` is
introspected directly on a fresh `create_app()` instance (TC-SEC-039's own
precondition: "before any request is served"), and `TestClient` drives the
body-size behaviour end to end with no session cookie.
"""

from __future__ import annotations

import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost:5432/x")
os.environ.setdefault("SECRET_KEY", "x" * 32)
os.environ.setdefault("USERNAME_HASH_SALT", "y" * 32)
os.environ.setdefault("ALLOWED_ORIGINS", "https://app.example.in")
os.environ.setdefault("ALLOWED_HOSTS", "testserver,127.0.0.1,localhost")

import pytest  # noqa: E402
from app.main import create_app  # noqa: E402
from app.middleware.authz import AuthzMiddleware  # noqa: E402
from app.middleware.csrf import CsrfMiddleware  # noqa: E402
from app.middleware.security_headers import (  # noqa: E402
    MAX_REQUEST_BODY_BYTES,
    SecurityHeadersMiddleware,
)
from app.middleware.session_loader import SessionLoaderMiddleware  # noqa: E402
from starlette.middleware.cors import CORSMiddleware  # noqa: E402
from starlette.middleware.trustedhost import TrustedHostMiddleware  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import JSONResponse, Response  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402


@pytest.fixture
def app_instance(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    app = create_app()

    handler_entered: dict[str, bool] = {"value": False}
    received_body: dict[str, bytes] = {"value": b""}

    @app.post("/api/__test_only_body_size_route")
    async def _fake_route(request: Request) -> dict[str, bool]:
        handler_entered["value"] = True
        received_body["value"] = await request.body()
        return {"ok": True}

    app.state.handler_entered = handler_entered  # type: ignore[attr-defined]
    app.state.received_body = received_body  # type: ignore[attr-defined]
    return app


def test_tc_sec_039_middleware_registration_order_is_exact(
    app_instance,  # noqa: ANN001
) -> None:
    """backend-architecture.md §2 rows 1-6, ADR-007: outermost -> innermost
    is exactly TrustedHostMiddleware, request-ID+security-headers, CORS,
    session loader, CSRF, authorization. Any swap, omission, or insertion
    fails this test."""
    registered_classes = [middleware.cls for middleware in app_instance.user_middleware]

    assert registered_classes == [
        TrustedHostMiddleware,
        SecurityHeadersMiddleware,
        CORSMiddleware,
        SessionLoaderMiddleware,
        CsrfMiddleware,
        AuthzMiddleware,
    ]


def test_tc_sec_027_cors_allows_exactly_get_and_post(
    app_instance,  # noqa: ANN001
) -> None:
    """backend-architecture.md SEC-T24, R2-2: `allow_methods == {GET, POST}`
    exactly — no PATCH/PUT/DELETE verb exists in the API."""
    cors_middleware = next(
        middleware
        for middleware in app_instance.user_middleware
        if middleware.cls is CORSMiddleware
    )

    assert set(cors_middleware.kwargs["allow_methods"]) == {"GET", "POST"}


def test_tc_sec_028_oversized_content_length_is_rejected_before_handler_runs(
    app_instance,  # noqa: ANN001
) -> None:
    """backend-architecture.md SEC-T31, SEC-S8: a `Content-Length` above
    `MAX_REQUEST_BODY_BYTES` is rejected `413` before the route handler
    runs — asserted here by the handler-entry marker never being set."""
    client = TestClient(app_instance)
    oversized_body = b"x" * (MAX_REQUEST_BODY_BYTES + 1)

    response = client.post(
        "/api/__test_only_body_size_route",
        content=oversized_body,
        headers={"content-type": "application/octet-stream"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert app_instance.state.handler_entered["value"] is False


def test_tc_sec_028_length_less_stream_is_capped_at_the_same_figure(
    app_instance,  # noqa: ANN001
) -> None:
    """The streamed/length-less-body half of SEC-T31/SEC-S8: a request with
    no `Content-Length` is capped while reading, at the same figure, and
    also never reaches the handler."""
    client = TestClient(app_instance)

    def _oversized_chunks():
        yield b"x" * (MAX_REQUEST_BODY_BYTES + 1)

    response = client.post(
        "/api/__test_only_body_size_route",
        content=_oversized_chunks(),
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert app_instance.state.handler_entered["value"] is False


def test_body_within_limit_is_not_rejected_as_too_large(
    app_instance,  # noqa: ANN001
) -> None:
    """Negative control for both TC-SEC-028 tests above: a body under the
    cap is never rejected with `413` (it still hits row 5's CSRF check —
    this route sends no `Origin`/`X-CSRF-Token` — so `403`, not `200`, is
    the expected downstream outcome; the point of this test is that the
    body-size gate itself let it through)."""
    client = TestClient(app_instance)

    response = client.post(
        "/api/__test_only_body_size_route",
        content=b"{}",
        headers={"content-type": "application/json"},
    )

    assert response.status_code != 413


def test_f1_length_less_body_under_the_cap_is_replayed_exactly_to_the_handler() -> None:
    """F1: a chunked/length-less body UNDER the cap must reach the route
    handler with the *exact* bytes the client sent — not merely a 200/other
    non-413 status. Regression for the `request._receive` override, which
    `BaseHTTPMiddleware.call_next` (wired to `request.wrapped_receive`)
    never replays once the stream has been drained.

    Exercised against `SecurityHeadersMiddleware` mounted on a minimal
    Starlette app (not the full `create_app()` stack) so the assertion is
    scoped to the body-replay behaviour this middleware owns, independent
    of CSRF/authz, which are out of scope for this unit."""
    from starlette.applications import Starlette
    from starlette.routing import Route

    received_body: dict[str, bytes] = {"value": b""}

    async def _echo_route(request: Request) -> Response:
        received_body["value"] = await request.body()
        return JSONResponse({"ok": True})

    minimal_app = Starlette(routes=[Route("/echo", _echo_route, methods=["POST"])])
    minimal_app.add_middleware(SecurityHeadersMiddleware)

    client = TestClient(minimal_app)
    exact_bytes = b'{"hello": "world"}'

    def _chunks():
        yield exact_bytes

    response = client.post("/echo", content=_chunks())

    assert response.status_code == 200
    assert received_body["value"] == exact_bytes


def test_f6_malformed_content_length_is_rejected(app_instance) -> None:  # noqa: ANN001
    """F6: an unparseable Content-Length must not fall through with no size
    check at all."""
    client = TestClient(app_instance)

    response = client.post(
        "/api/__test_only_body_size_route",
        content=b"{}",
        headers={"content-type": "application/json", "content-length": "not-a-number"},
    )

    assert response.status_code == 413


def test_f6_negative_content_length_is_rejected(app_instance) -> None:  # noqa: ANN001
    client = TestClient(app_instance)

    response = client.post(
        "/api/__test_only_body_size_route",
        content=b"{}",
        headers={"content-type": "application/json", "content-length": "-1"},
    )

    assert response.status_code == 413


def test_f5_malformed_inbound_request_id_is_replaced_with_a_fresh_uuid(
    app_instance,  # noqa: ANN001
) -> None:
    """F5: a client-supplied X-Request-ID that doesn't match the narrow
    allow-pattern must never be propagated verbatim into the response
    header / error envelope / logs — a fresh UUID4 is minted instead."""
    client = TestClient(app_instance)
    forged = "<script>evil</script>" + "\n" + "x" * 200

    response = client.post(
        "/api/__test_only_body_size_route",
        content=b"{}",
        headers={"content-type": "application/json", "x-request-id": forged},
    )

    assert response.headers["x-request-id"] != forged
    assert len(response.headers["x-request-id"]) <= 64


def test_f5_well_formed_inbound_request_id_is_propagated(
    app_instance,  # noqa: ANN001
) -> None:
    client = TestClient(app_instance)
    valid_id = "abc123-_." + "z" * 10

    response = client.post(
        "/api/__test_only_body_size_route",
        content=b"{}",
        headers={"content-type": "application/json", "x-request-id": valid_id},
    )

    assert response.headers["x-request-id"] == valid_id


def test_f7_every_registered_route_uses_only_get_post_head(
    app_instance,  # noqa: ANN001
) -> None:
    """F7: TC-SEC-027 must also assert that every *actual* registered route
    uses only GET/POST/HEAD — not merely that CORS config says so."""
    allowed = {"GET", "POST", "HEAD"}
    for route in app_instance.routes:
        methods = getattr(route, "methods", None)
        if methods is None:
            continue
        assert methods.issubset(allowed), f"{route.path} allows {methods}"


def test_f8a_normal_response_carries_all_six_security_headers(
    app_instance,  # noqa: ANN001
) -> None:
    client = TestClient(app_instance)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Permissions-Policy"] == "geolocation=(), camera=(), microphone=()"
    assert response.headers["Content-Security-Policy"] == (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )


def test_f8b_unrecognized_host_is_rejected_with_400(app_instance) -> None:  # noqa: ANN001
    client = TestClient(app_instance, base_url="http://evil.example")

    response = client.get("/healthz")

    assert response.status_code == 400


def test_f8c_response_with_set_cookie_carries_cache_control_no_store() -> None:
    """F4/F8c: a response that mints a fresh Set-Cookie (e.g. login/logout)
    must carry Cache-Control: no-store even though the INBOUND request
    carried no authenticated session yet. Exercised on a minimal app so the
    assertion is scoped to `SecurityHeadersMiddleware`'s own behaviour,
    independent of CSRF/authz."""
    from starlette.applications import Starlette
    from starlette.routing import Route

    async def _set_cookie_route(request: Request) -> Response:
        response = JSONResponse({"ok": True})
        response.set_cookie("test-cookie", "value")
        return response

    minimal_app = Starlette(routes=[Route("/set-cookie", _set_cookie_route, methods=["GET"])])
    minimal_app.add_middleware(SecurityHeadersMiddleware)

    client = TestClient(minimal_app)

    response = client.get("/set-cookie")

    assert "set-cookie" in {k.lower() for k in response.headers.keys()}
    assert response.headers["Cache-Control"] == "no-store"
