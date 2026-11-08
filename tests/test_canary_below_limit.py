"""Tests for the canary module's below_limit helper.

Kept in a separate file so the specification in tests/test_canary.py stays untouched.
"""

from app.canary import CANARY_LIMIT, below_limit


def test_below_limit_a_value_under_the_limit_is_true():
    assert below_limit(CANARY_LIMIT - 1)


def test_below_limit_the_limit_itself_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT)


def test_below_limit_a_value_above_the_limit_is_false():
    assert not below_limit(CANARY_LIMIT + 1)
