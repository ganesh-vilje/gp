"""Small round-trip tests for `core.hashing` (not test-case-mapped;
supports H3/security-architecture.md §1/§9)."""

from __future__ import annotations

from app.core import hashing
from argon2.low_level import Type


def test_hash_password_verify_password_round_trip() -> None:
    """Supporting test: a hashed password verifies against its own plaintext
    and rejects a wrong one."""
    hashed = hashing.hash_password("correct horse battery staple")

    assert hashing.verify_password(hashed, "correct horse battery staple") is True
    assert hashing.verify_password(hashed, "wrong password") is False


def test_verify_password_rejects_a_malformed_hash() -> None:
    """Supporting test: an unparseable hash never raises — it verifies False."""
    assert hashing.verify_password("not-an-argon2-hash", "anything") is False


def test_password_hasher_uses_security_architecture_parameters() -> None:
    """F2: the hasher is constructed with security-architecture.md §1's
    `m=9216 KiB, t=4, p=1` (Argon2id), not the library defaults (100 MiB, p=8)."""
    hasher = hashing._password_hasher  # noqa: SLF001 - asserting the pinned construction

    assert hasher.time_cost == 4
    assert hasher.memory_cost == 9216
    assert hasher.parallelism == 1
    assert hasher.type == Type.ID


def test_hash_password_output_encodes_security_architecture_parameters() -> None:
    """F2: a produced hash string encodes `m=9216,t=4,p=1`, so the pinned
    parameters actually reach the stored credential, not just the hasher
    object."""
    hashed = hashing.hash_password("correct horse battery staple")

    assert "m=9216,t=4,p=1" in hashed


def test_h_returns_16_hex_characters() -> None:
    """F1: `h()` returns exactly 16 hex characters, matching
    `security_event.actor_username_hash CHAR(16)`."""
    digest = hashing.h("clerk_test", b"s" * 32)

    assert len(digest) == 16
    int(digest, 16)  # must be valid hex; raises ValueError otherwise


def test_h_is_case_insensitive_on_username() -> None:
    """F1: `h()` casefolds the username first, so `Admin` and `admin` map to
    the same hash."""
    salt = b"s" * 32

    assert hashing.h("Admin", salt) == hashing.h("admin", salt)


def test_h_differs_across_salts() -> None:
    """F1: `h()` is keyed by the salt — the same username under two
    different salts produces two different hashes."""
    salt_a = b"a" * 32
    salt_b = b"b" * 32

    assert hashing.h("clerk_test", salt_a) != hashing.h("clerk_test", salt_b)


def test_h_is_deterministic_for_a_fixed_username_and_salt() -> None:
    """Supporting test: `h(username, salt)` is deterministic."""
    salt = b"a" * 32

    assert hashing.h("clerk_test", salt) == hashing.h("clerk_test", salt)


def test_sha256_is_deterministic_hex_digest() -> None:
    """T-006: `sha256(token)` matches `session.token_hash CHAR(64)`."""
    digest = hashing.sha256("some-opaque-session-token")

    assert digest == hashing.sha256("some-opaque-session-token")
    assert len(digest) == 64
    int(digest, 16)  # must be valid hex; raises ValueError otherwise


def test_sha256_differs_across_tokens() -> None:
    assert hashing.sha256("token-a") != hashing.sha256("token-b")
