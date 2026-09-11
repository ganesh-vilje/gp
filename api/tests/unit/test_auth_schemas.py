"""Unit tests for `app/api/schemas/auth.py` (T-008): `extra="forbid"`
rejects an unexpected field on the request DTO (coding-guidelines.md §
Validation and typing)."""

from __future__ import annotations

import pytest
from app.api.schemas.auth import LoginRequest, LoginResponse, LogoutResponse, UserDTO
from pydantic import ValidationError


def test_login_request_accepts_a_well_formed_body() -> None:
    request = LoginRequest(username="asha", password="correct horse battery staple")

    assert request.username == "asha"
    assert request.password == "correct horse battery staple"


def test_login_request_rejects_an_extra_field() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username="asha", password="x" * 12, otp="123456")  # type: ignore[call-arg]


def test_login_request_rejects_empty_username() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username="", password="x" * 12)


def test_login_request_rejects_empty_password() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username="asha", password="")


def test_login_request_rejects_username_over_30_chars() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username="a" * 31, password="x" * 12)


def test_login_request_rejects_password_over_256_chars() -> None:
    with pytest.raises(ValidationError):
        LoginRequest(username="asha", password="x" * 257)


def test_login_response_rejects_an_extra_field() -> None:
    user = UserDTO(id=1, username="asha", is_admin_clerk=False, must_change_password=False)
    with pytest.raises(ValidationError):
        LoginResponse(user=user, csrf_token="t", extra="nope")  # type: ignore[call-arg]


def test_user_dto_rejects_an_extra_field() -> None:
    with pytest.raises(ValidationError):
        UserDTO(  # type: ignore[call-arg]
            id=1,
            username="asha",
            is_admin_clerk=False,
            must_change_password=False,
            password_hash="should-never-be-here",
        )


def test_logout_response_rejects_an_extra_field() -> None:
    with pytest.raises(ValidationError):
        LogoutResponse(csrf_token="t", session_id=1)  # type: ignore[call-arg]
