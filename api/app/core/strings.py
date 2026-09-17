"""Every server-side user-visible message, keyed (AD-12, solution-architecture.md:33).

English now, Telugu later: keeping every user-visible string in one module
per side is the build requirement that makes that swap a one-module change
later. No user-visible string literal belongs anywhere else in `app/`
(coding-guidelines.md — the equivalent CI grep for the web side is
frontend-architecture.md §10; the backend has no such grep yet, but the
rule is the same).

This module is seeded with only the keys the current build tasks need.
error-catalog.md's `Public-safe message key` column names the full set of
keys a later task (the error-catalog HTTP mapping in T-006, and the
services/routers that raise each domain error) will add here — this module,
not a literal in that code, is where that copy belongs.

AD-12's scope is product-facing (HTTP response / frontend) text. Operator-
only output — `app/cli/*` terminal prints, reachable only via `fly ssh
console`, never HTTP (T-007) — is not a "user-visible string" in AD-12's
sense and may print literals directly; there is no citizen/clerk-facing
audience and no Telugu-localisation need for an operator shell. T-035's
CLI commands should follow the same convention.
"""

from __future__ import annotations

_STRINGS: dict[str, str] = {
    # core.errors — generic fallback for the invalid_input envelope (the
    # client renders its own copy keyed by `code`; this is shown only if it
    # doesn't, ADR-018).
    "errors.invalid_input": "There is a problem with your input.",
    # core.validation (BR-012, BR-014, BR-016).
    "validation.citizen_phone.invalid_format": "Enter a valid phone number.",
    "validation.citizen_name.too_long": "Name must be 100 characters or fewer.",
    "validation.description.too_long": "Description must be 2,000 characters or fewer.",
    "validation.username.invalid_format": (
        "Username must be 3-30 characters using only letters, digits, and underscores."
    ),
    "validation.password.too_short": "Password must be at least 12 characters.",
    "validation.password.similar_to_username": "Password must not be similar to the username.",
    "validation.password.entirely_numeric": "Password must not be entirely numbers.",
    "validation.password.common_password": "That password is too common. Choose a different one.",
    # T-006 — services.auth / middleware.authz / middleware.csrf
    # (error-catalog.md's "Public-safe message key" column).
    "errors.not_authenticated": "Please sign in to continue.",
    "errors.forbidden": "You don't have permission to do that.",
    # T-008 — the single exception-handler set (ADR-018).
    "errors.internal_error": "Something went wrong. Please try again.",
    # T-009 — services.complaints / db.repositories.complaint
    # (error-catalog.md's "Public-safe message key" column).
    "validation.client_request_id.conflict": (
        "This request could not be completed. Please submit it again."
    ),
    "errors.complaint_number_generation_failed": (
        "Could not create the complaint right now; please try again."
    ),
    "errors.complaint_creator_unavailable": (
        "This complaint could not be created right now; please try again."
    ),
    # T-010 — services.lookup / api.routers.lookup (error-catalog.md's
    # "Public-safe message key" column).
    "lookup.invalid_format": "Enter a valid complaint number.",
    "lookup.not_found": "We couldn't find a complaint with that number.",
    "errors.rate_limited.lookup": "Too many attempts. Please try again in a moment.",
    "errors.service_unavailable": "The service is temporarily unavailable. Please try again.",
}


def get(key: str) -> str:
    """Return the user-visible string for `key`.

    Raises `KeyError` for an unregistered key rather than silently falling
    back to the key itself — a missing key is a bug to fix here, not a
    string to guess at the call site.
    """
    try:
        return _STRINGS[key]
    except KeyError:
        raise KeyError(f"No user-visible string registered for key {key!r}") from None
