"""Tests for the canary `below_limit` helper.

`within_limit`'s behaviour is the specification in tests/test_canary.py and must not be changed;
these tests cover the additional `below_limit` helper.
"""

from app.canary import CANARY_LIMIT, below_limit


def test_the_limit_itself_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT)


def test_a_value_below_the_limit_is_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1)


def test_a_value_above_the_limit_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT + 1)
