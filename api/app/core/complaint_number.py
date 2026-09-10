"""Complaint-number codec: generate / normalise / validate / checksum (ADR-016).

- Alphabet: Crockford base32, 32 symbols, no I/L/O/U.
- Body: 8 symbols (40 random bits) from `secrets.choice`.
- Checksum: one further symbol, `alphabet[(sum((i+1) * value_i for i in
  range(8))) % 32]` over the body's alphabet indices.
- Canonical storage/comparison form: 9 uppercase symbols, no separator.
  Display/read-aloud form (`XXXX-XXXXX`) is built by the layer that renders
  it, not here (this module owns the codec, not presentation).
- Normalisation on input (api-contract.md §4): trim, uppercase, strip `-`
  and spaces, map `I`/`L`->`1`, `O`->`0`.
- The number is never logged and never appears in a URL (ADR-016) — no
  function here does either.
"""

from __future__ import annotations

import re
import secrets

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_BODY_LENGTH = 8
_CANONICAL_LENGTH = _BODY_LENGTH + 1  # body + checksum symbol
_CANONICAL_RE = re.compile(rf"^[{_ALPHABET}]{{{_CANONICAL_LENGTH}}}$")
_NORMALISE_TABLE = str.maketrans({"I": "1", "L": "1", "O": "0"})


def checksum(body: str) -> str:
    """Return the single checksum symbol for an 8-symbol `body`.

    `body` must already consist only of `_ALPHABET` symbols — callers that
    accept external input must normalise and validate the alphabet/length
    first (BR-015's "length+alphabet regex, then checksum" order).
    """
    total = sum((index + 1) * _ALPHABET.index(symbol) for index, symbol in enumerate(body))
    return _ALPHABET[total % len(_ALPHABET)]


def generate() -> str:
    """Return a fresh 9-symbol canonical complaint number."""
    body = "".join(secrets.choice(_ALPHABET) for _ in range(_BODY_LENGTH))
    return body + checksum(body)


def normalise(raw: str) -> str:
    """Canonicalise citizen-entered input: trim, uppercase, strip separators,
    and map the visually confusable symbols the alphabet excludes.

    The result is not guaranteed to be a *valid* complaint number — call
    `validate()` before using it for a lookup (BR-015).
    """
    value = raw.strip().upper()
    value = value.replace("-", "").replace(" ", "")
    return value.translate(_NORMALISE_TABLE)


def validate(value: str) -> bool:
    """Return `True` iff `value` is a well-formed 9-symbol complaint number
    with a matching checksum. Does not normalise its input — callers pass a
    value already run through `normalise()`."""
    if not _CANONICAL_RE.match(value):
        return False
    body, check = value[:_BODY_LENGTH], value[_BODY_LENGTH]
    return checksum(body) == check
