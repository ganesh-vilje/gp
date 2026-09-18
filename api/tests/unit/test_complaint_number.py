"""Unit tests for `core.complaint_number` (ADR-016, api-contract.md §4)."""

from __future__ import annotations

from app.core import complaint_number


def test_normalise_trims_uppercases_strips_hyphen_and_maps_confusables() -> None:
    """TC-UNIT-009: `normalise()` on `" 4t9k-m2xq8 "` (whitespace, lowercase,
    hyphen) returns the canonical 9-symbol uppercase stored form."""
    result = complaint_number.normalise(" 4t9k-m2xq8 ")

    assert result == "4T9KM2XQ8"
    assert len(result) == 9


def test_normalise_maps_i_l_to_1_and_o_to_0() -> None:
    """Supporting check for TC-UNIT-009 (not itself test-case-mapped):
    normalisation maps the visually confusable symbols the alphabet excludes."""
    assert complaint_number.normalise("iIlLoO") == "111100"


def test_generate_round_trips_through_validate() -> None:
    """Supporting check (ADR-016, not test-case-mapped): a generated number
    is a valid 9-symbol code with a correct checksum."""
    value = complaint_number.generate()

    assert len(value) == 9
    assert complaint_number.validate(value)


def test_checksum_detects_a_single_symbol_transcription_error() -> None:
    """Supporting check (ADR-016, not test-case-mapped): corrupting one body
    symbol changes the checksum."""
    value = complaint_number.generate()
    body, check = value[:8], value[8]
    corrupted_body = ("0" if body[0] != "0" else "1") + body[1:]

    assert complaint_number.checksum(corrupted_body) != check


def test_validate_rejects_wrong_length() -> None:
    """Supporting check (ADR-016, not test-case-mapped): a too-short value is
    never valid, regardless of alphabet."""
    assert complaint_number.validate("ABCDEFGH") is False
