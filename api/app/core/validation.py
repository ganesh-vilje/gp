"""Phone, username, and password-policy validation (BR-012, BR-014, BR-016).

Each `validate_*` function raises `core.errors.ValidationFailed` with
`fields={field_name: reason_code}` (never the submitted value,
coding-guidelines.md § Error handling) on failure, and returns `None` on
success. Messages are keyed strings from `core.strings` (AD-12) — no
literal user-visible text lives here.

Spec ambiguities resolved here (business-rules.md left the exact
regex/format to the architect):

- BR-012 phone: "digits only, optionally with a leading + and country code,
  length between 7 and 15 characters" is read as 7-15 ASCII *digits*, with
  the optional leading `+` not counted toward that length (E.164-shaped,
  per the rule's own "loosely E.164-shaped" wording), and matching
  schema.md's `CHECK (phone ~ '^\\+?[0-9]{7,15}$')` exactly (not `\\d`,
  which also matches non-ASCII Unicode decimal digits) -> `^\\+?[0-9]{7,15}$`.
- BR-016 username: the exact regex the rule names -> `^[A-Za-z0-9_]{3,30}$`.
- BR-016 password (security-architecture.md §3, `core/validation
  .validate_password`): >= 12 characters; not similar to the username
  (casefold containment, or a difflib similarity ratio >= 0.7 — the
  threshold Django's own `UserAttributeSimilarityValidator` uses, since
  security-architecture.md names the check but not a number); not entirely
  numeric; not in the vendored common-password list
  (`common_passwords.txt`, casefold match).
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path

from app.core import strings
from app.core.errors import ValidationFailed

_PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")

_CITIZEN_NAME_MAX_LENGTH = 100
_DESCRIPTION_MAX_LENGTH = 2000
_PASSWORD_MIN_LENGTH = 12
_PASSWORD_USERNAME_SIMILARITY_THRESHOLD = 0.7

_COMMON_PASSWORDS_PATH = Path(__file__).with_name("common_passwords.txt")


def _load_common_passwords() -> frozenset[str]:
    entries = set()
    for line in _COMMON_PASSWORDS_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        entries.add(stripped.casefold())
    return frozenset(entries)


# Read once at import (module layout comment: "core: ... pure functions and
# small wrappers only"; this is the one read the module needs to do its job).
_COMMON_PASSWORDS = _load_common_passwords()


def validate_citizen_phone(value: str) -> None:
    """BR-012: reject a phone number that isn't plausibly shaped."""
    if not _PHONE_RE.match(value):
        raise ValidationFailed(
            strings.get("validation.citizen_phone.invalid_format"),
            fields={"citizen_phone": "invalid_format"},
        )


def validate_citizen_name(value: str) -> None:
    """BR-014: reject a citizen name over the 100-character cap."""
    if len(value) > _CITIZEN_NAME_MAX_LENGTH:
        raise ValidationFailed(
            strings.get("validation.citizen_name.too_long"),
            fields={"citizen_name": "too_long"},
        )


def validate_description(value: str) -> None:
    """BR-014: reject a complaint description over the 2,000-character cap."""
    if len(value) > _DESCRIPTION_MAX_LENGTH:
        raise ValidationFailed(
            strings.get("validation.description.too_long"),
            fields={"description": "too_long"},
        )


def validate_username(value: str) -> None:
    """BR-016: reject a username outside `^[A-Za-z0-9_]{3,30}$`."""
    if not _USERNAME_RE.match(value):
        raise ValidationFailed(
            strings.get("validation.username.invalid_format"),
            fields={"username": "invalid_format"},
        )


def _is_similar_to_username(password_casefold: str, username_casefold: str) -> bool:
    if not username_casefold:
        return False
    if username_casefold in password_casefold or password_casefold in username_casefold:
        return True
    ratio = difflib.SequenceMatcher(a=password_casefold, b=username_casefold).ratio()
    return ratio >= _PASSWORD_USERNAME_SIMILARITY_THRESHOLD


def validate_password(value: str, username: str | None = None) -> None:
    """BR-016 / security-architecture.md §3: reject a password that is too
    short, similar to `username`, entirely numeric, or in the vendored
    common-password list.

    `username` is optional (account creation/reset both have one to compare
    against; a caller with none — none exists in this task's scope — simply
    skips that one check).
    """
    if len(value) < _PASSWORD_MIN_LENGTH:
        raise ValidationFailed(
            strings.get("validation.password.too_short"),
            fields={"password": "too_short"},
        )

    if username and _is_similar_to_username(value.casefold(), username.casefold()):
        raise ValidationFailed(
            strings.get("validation.password.similar_to_username"),
            fields={"password": "similar_to_username"},
        )

    if value.isdigit():
        raise ValidationFailed(
            strings.get("validation.password.entirely_numeric"),
            fields={"password": "entirely_numeric"},
        )

    if value.casefold() in _COMMON_PASSWORDS:
        raise ValidationFailed(
            strings.get("validation.password.common_password"),
            fields={"password": "common_password"},
        )
