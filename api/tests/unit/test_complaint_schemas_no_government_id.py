"""TC-API-090 (AC-012, BR-009): neither the new-complaint request schema nor
the edit-details request schema has any field named or labelled for a
government ID. Structural proof (field name inspection), complementing the
integration-level `extra="forbid"` rejection tests (TC-API-018/091)."""

from __future__ import annotations

from app.api.schemas.complaints import CreateComplaintRequest, EditDetailsRequest

_GOVERNMENT_ID_MARKERS = (
    "aadhaar",
    "voter",
    "voter_id",
    "epic",
    "pan",
    "ration",
    "government_id",
    "gov_id",
    "national_id",
)


def _assert_no_government_id_field(model: type) -> None:
    field_names = set(model.model_fields.keys())
    for field_name in field_names:
        lowered = field_name.lower()
        for marker in _GOVERNMENT_ID_MARKERS:
            assert marker not in lowered, (
                f"{model.__name__}.{field_name} looks government-ID-shaped ({marker!r})"
            )


def test_create_complaint_request_has_no_government_id_field() -> None:
    _assert_no_government_id_field(CreateComplaintRequest)


def test_edit_details_request_has_no_government_id_field() -> None:
    _assert_no_government_id_field(EditDetailsRequest)


def test_create_complaint_request_extra_forbid_structurally_blocks_unknown_fields() -> None:
    assert CreateComplaintRequest.model_config.get("extra") == "forbid"


def test_edit_details_request_extra_forbid_structurally_blocks_unknown_fields() -> None:
    assert EditDetailsRequest.model_config.get("extra") == "forbid"
