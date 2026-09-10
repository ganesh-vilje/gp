"""Unit tests for `core.validation` (BR-012, BR-014, BR-016)."""

from __future__ import annotations

import pytest
from app.core import validation
from app.core.errors import ValidationFailed


def test_validate_citizen_phone_letters_rejected() -> None:
    """TC-UNIT-001: a phone number containing letters is rejected with a
    `fields.citizen_phone` reason code."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_citizen_phone("abc1234")

    assert exc_info.value.fields == {"citizen_phone": "invalid_format"}


def test_validate_citizen_phone_three_digits_rejected() -> None:
    """TC-UNIT-002: a 3-digit phone number is rejected — below the 7-char floor."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_citizen_phone("123")

    assert exc_info.value.fields == {"citizen_phone": "invalid_format"}


def test_validate_citizen_phone_accepts_plausible_number() -> None:
    """Supporting check for TC-UNIT-001/002 (not itself test-case-mapped): a
    plausible E.164-shaped number is accepted."""
    validation.validate_citizen_phone("+919876543210")  # must not raise


def test_validate_citizen_phone_non_ascii_digits_rejected() -> None:
    """F4 (not test-case-mapped): non-ASCII Unicode decimal digits (which
    `\\d` matches but the DB's `[0-9]` CHECK constraint does not) are
    rejected, keeping validation and schema.md's CHECK in agreement."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_citizen_phone("٠١٢٣٤٥٦٧٨")  # Arabic-Indic digits

    assert exc_info.value.fields == {"citizen_phone": "invalid_format"}


def test_validate_citizen_name_101_chars_rejected() -> None:
    """TC-UNIT-003: a 101-character `citizen_name` is rejected — over the
    100-char cap."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_citizen_name("a" * 101)

    assert exc_info.value.fields == {"citizen_name": "too_long"}


def test_validate_citizen_name_100_chars_accepted() -> None:
    """Supporting check for TC-UNIT-003 (not itself test-case-mapped): exactly
    100 characters is accepted."""
    validation.validate_citizen_name("a" * 100)  # must not raise


def test_validate_description_2001_chars_rejected() -> None:
    """TC-UNIT-004: a 2001-character `description` is rejected — over the
    2000-char cap."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_description("a" * 2001)

    assert exc_info.value.fields == {"description": "too_long"}


def test_validate_description_2000_chars_accepted() -> None:
    """Supporting check for TC-UNIT-004 (not itself test-case-mapped): exactly
    2000 characters is accepted."""
    validation.validate_description("a" * 2000)  # must not raise


@pytest.mark.parametrize("username", ["ab", "a" * 31, "a b"])
def test_validate_username_rejected(username: str) -> None:
    """TC-UNIT-007: usernames `"ab"`, `"a"*31`, and `"a b"` are all rejected
    against `^[A-Za-z0-9_]{3,30}$`."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_username(username)

    assert exc_info.value.fields == {"username": "invalid_format"}


def test_validate_password_11_chars_rejected() -> None:
    """TC-UNIT-008: an 11-character password is rejected."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_password("a" * 11)

    assert exc_info.value.fields == {"password": "too_short"}


def test_validate_password_12_chars_accepted() -> None:
    """TC-UNIT-008: exactly 12 characters is accepted."""
    validation.validate_password("a" * 12)  # must not raise


def test_validate_password_similar_to_username_rejected() -> None:
    """F3 (not test-case-mapped): a password containing the username
    (casefold) is rejected as `similar_to_username`, ahead of the numeric
    and common-password checks."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_password("Clerktest123!", username="clerk_test")

    assert exc_info.value.fields == {"password": "similar_to_username"}


def test_validate_password_high_similarity_ratio_rejected() -> None:
    """F3 (not test-case-mapped): a password that does not contain the
    username outright, but is a close variant of it, is still rejected via
    the difflib similarity ratio."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_password("clerk_tesuxx", username="clerk_test")

    assert exc_info.value.fields == {"password": "similar_to_username"}


def test_validate_password_entirely_numeric_rejected() -> None:
    """F3 (not test-case-mapped): a 12+ digit, entirely numeric password is
    rejected even though it clears the length floor."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_password("123456789012")

    assert exc_info.value.fields == {"password": "entirely_numeric"}


def test_validate_password_common_password_rejected() -> None:
    """F3 (not test-case-mapped): a password on the vendored common-password
    list is rejected, case-insensitively."""
    with pytest.raises(ValidationFailed) as exc_info:
        validation.validate_password("Administrator")

    assert exc_info.value.fields == {"password": "common_password"}


def test_validate_password_strong_password_accepted() -> None:
    """F3 (not test-case-mapped): a long, non-numeric, non-common password
    unrelated to the username passes every check."""
    validation.validate_password("Tr0pical-Sunset-River!", username="clerk_test")
