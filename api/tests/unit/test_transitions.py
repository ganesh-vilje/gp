"""Unit tests for `app.services.complaints.transitions` (BR-002, T-018)."""

from __future__ import annotations

from app.services.complaints import transitions

_ALL_STATUSES = ("new", "in_progress", "resolved", "rejected", "closed")


def test_new_to_closed_is_not_a_legal_transition() -> None:
    """TC-UNIT-005: `new -> closed` is not in the frozen legal-transition
    set (BR-002 forbids skipping `in_progress`)."""
    assert transitions.is_legal_transition("new", "closed") is False
    assert "closed" not in transitions.legal_next_statuses("new")


def test_every_pair_matches_the_frozen_map_exactly() -> None:
    """TC-UNIT-006: evaluate every `(from, to)` pair in the frozen map.
    Exactly `{new->in_progress, in_progress->{resolved,rejected},
    resolved/rejected->closed}` are legal; every other pair, including every
    self-transition and `closed`'s (terminal, no legal next status), is
    illegal."""
    expected_legal = {
        ("new", "in_progress"),
        ("in_progress", "resolved"),
        ("in_progress", "rejected"),
        ("resolved", "closed"),
        ("rejected", "closed"),
    }

    actual_legal = {
        (previous, new)
        for previous in _ALL_STATUSES
        for new in _ALL_STATUSES
        if transitions.is_legal_transition(previous, new)
    }

    assert actual_legal == expected_legal
    assert transitions.legal_next_statuses("closed") == []
