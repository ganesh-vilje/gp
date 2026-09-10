"""Unit tests for `core.errors` (ADR-018, error-catalog.md)."""

from __future__ import annotations

from app.core.errors import NotFound, ValidationFailed, to_envelope


def test_to_envelope_invalid_input_matches_documented_shape() -> None:
    """TC-UNIT-010: serializing an `invalid_input` error with
    `fields={"citizen_phone": "..."}` matches the documented envelope shape
    exactly (`code`, `message`, `fields`, `request_id`)."""
    error = ValidationFailed(
        "Enter a valid phone number.",
        fields={"citizen_phone": "invalid_format"},
    )

    envelope = to_envelope(error, request_id="b3f1-test-request-id")

    assert envelope == {
        "error": {
            "code": "invalid_input",
            "message": "Enter a valid phone number.",
            "fields": {"citizen_phone": "invalid_format"},
            "request_id": "b3f1-test-request-id",
        }
    }


def test_to_envelope_omits_fields_when_absent() -> None:
    """TC-UNIT-010 (supporting case): an error with no field-level detail
    omits `fields` from the envelope entirely, per error-catalog.md
    ("`fields` — present only for `invalid_input`")."""
    error = NotFound("We couldn't find a complaint with that number.")

    envelope = to_envelope(error, request_id="b3f1-test-request-id")

    assert envelope == {
        "error": {
            "code": "not_found",
            "message": "We couldn't find a complaint with that number.",
            "request_id": "b3f1-test-request-id",
        }
    }
    assert "fields" not in envelope["error"]
