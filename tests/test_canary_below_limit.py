"""Tests for the below_limit canary helper (strictly below the limit)."""

from app.canary import CANARY_LIMIT, below_limit


def test_a_value_below_the_limit_is_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1) is True


def test_the_limit_itself_is_not_below_the_limit():
    assert below_limit(CANARY_LIMIT) is False


def test_a_value_above_the_limit_is_not_below_the_limit():
    assert below_limit(CANARY_LIMIT + 1) is False
