"""Unit tests for the deny-by-default allow-list decision function
(security-architecture.md §2, D-A). Middleware end-to-end behaviour over
HTTP is covered cheaply in tests/unit/test_middleware_smoke.py; full
route-table-parametrised end-to-end coverage is T-008/T-010a (AC-015)."""

from __future__ import annotations

import pytest
from app.middleware.authz import PUBLIC_ALLOW_LIST, is_docs_route, is_public


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/lookup"),
        ("POST", "/api/login"),
        ("GET", "/api/session"),
        ("GET", "/healthz"),
    ],
)
def test_is_public_true_for_every_allow_list_entry(method: str, path: str) -> None:
    assert is_public(method, path) is True


def test_is_public_is_case_insensitive_on_method() -> None:
    assert is_public("post", "/api/lookup") is True
    assert is_public("get", "/healthz") is True


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/lookup"),  # right path, wrong method
        ("POST", "/api/session"),  # right path, wrong method
        ("POST", "/api/complaints"),
        ("GET", "/api/complaints"),
        ("GET", "/api/complaints/42"),
        ("POST", "/api/logout"),
        ("GET", "/api/accounts"),
        ("POST", "/api/accounts"),
        ("GET", "/"),
        ("POST", "/healthz"),
    ],
)
def test_is_public_false_for_everything_else(method: str, path: str) -> None:
    assert is_public(method, path) is False


def test_public_allow_list_has_exactly_four_entries() -> None:
    """security-architecture.md §2: 'The entire public allow-list is four
    entries.'"""
    assert len(PUBLIC_ALLOW_LIST) == 4


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_is_docs_route_true_for_fastapi_schema_paths(path: str) -> None:
    assert is_docs_route(path) is True


def test_is_docs_route_false_for_an_api_path() -> None:
    assert is_docs_route("/api/complaints") is False
