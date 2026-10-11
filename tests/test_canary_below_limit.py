"""Tests for `app.canary.below_limit` (strictly below the canary limit)."""

from app.canary import CANARY_LIMIT, below_limit, within_limit


def test_a_value_below_the_limit_is_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1) is True


def test_the_limit_itself_is_not_below_the_limit():
    assert below_limit(CANARY_LIMIT) is False


def test_a_value_above_the_limit_is_not_below_the_limit():
    assert below_limit(CANARY_LIMIT + 1) is False


def test_the_boundary_is_strict_while_within_limit_still_allows_it():
    assert below_limit(CANARY_LIMIT) is False
    assert within_limit(CANARY_LIMIT) is True
