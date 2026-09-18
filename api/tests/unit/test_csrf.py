"""Unit tests for the CSRF token helpers (security-architecture.md §4,
backend-architecture.md §4) — the anonymous stateless HMAC round trip and
tamper rejection. Middleware end-to-end behaviour over HTTP is T-008/
T-010a; see tests/unit/test_middleware_smoke.py for the cheap TestClient
smoke coverage this task adds."""

from __future__ import annotations

from app.middleware.csrf import compute_anonymous_csrf_token


def test_compute_anonymous_csrf_token_round_trips_for_the_same_seed() -> None:
    secret_key = "s" * 32
    seed = "some-random-seed-value"

    token_a = compute_anonymous_csrf_token(secret_key, seed)
    token_b = compute_anonymous_csrf_token(secret_key, seed)

    assert token_a == token_b


def test_compute_anonymous_csrf_token_differs_across_seeds() -> None:
    secret_key = "s" * 32

    token_a = compute_anonymous_csrf_token(secret_key, "seed-one")
    token_b = compute_anonymous_csrf_token(secret_key, "seed-two")

    assert token_a != token_b


def test_compute_anonymous_csrf_token_differs_across_secret_keys() -> None:
    seed = "some-random-seed-value"

    token_a = compute_anonymous_csrf_token("s" * 32, seed)
    token_b = compute_anonymous_csrf_token("t" * 32, seed)

    assert token_a != token_b


def test_compute_anonymous_csrf_token_tampered_token_does_not_match_recomputed() -> None:
    secret_key = "s" * 32
    seed = "some-random-seed-value"

    genuine = compute_anonymous_csrf_token(secret_key, seed)
    tampered = genuine[:-1] + ("a" if genuine[-1] != "a" else "b")

    recomputed = compute_anonymous_csrf_token(secret_key, seed)

    assert tampered != recomputed


def test_compute_anonymous_csrf_token_is_url_safe_and_unpadded() -> None:
    token = compute_anonymous_csrf_token("s" * 32, "seed")

    assert "=" not in token
    assert "+" not in token
    assert "/" not in token
