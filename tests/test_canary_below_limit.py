"""Tests for the canary below_limit helper."""

from app.canary import CANARY_LIMIT, below_limit


def test_below_limit_returns_true_strictly_below():
    assert below_limit(CANARY_LIMIT - 1) is True


def test_below_limit_is_false_at_the_limit():
    assert below_limit(CANARY_LIMIT) is False


def test_below_limit_is_false_above_the_limit():
    assert below_limit(CANARY_LIMIT + 1) is False


def test_below_limit_agrees_with_the_limit_value():
    assert CANARY_LIMIT == 10
    assert below_limit(9) is True
    assert below_limit(10) is False
