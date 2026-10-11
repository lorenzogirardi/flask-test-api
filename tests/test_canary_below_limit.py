"""Tests for the canary below_limit helper."""

from app.canary import CANARY_LIMIT, below_limit


def test_below_limit_is_true_for_a_value_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1) is True


def test_below_limit_is_false_at_the_limit_itself():
    assert below_limit(CANARY_LIMIT) is False


def test_below_limit_is_false_above_the_limit():
    assert below_limit(CANARY_LIMIT + 1) is False
