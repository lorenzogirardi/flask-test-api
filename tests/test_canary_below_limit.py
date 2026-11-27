"""Tests of the `below_limit` helper added to the canary module.

tests/test_canary.py is the specification for `within_limit` and is left untouched.
"""

from app.canary import CANARY_LIMIT, below_limit, within_limit


def test_the_limit_itself_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT)


def test_a_value_below_the_limit_is_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1)


def test_a_value_above_the_limit_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT + 1)


def test_within_limit_allows_the_limit_itself():
    assert within_limit(CANARY_LIMIT)
    assert within_limit(CANARY_LIMIT - 1)
    assert not within_limit(CANARY_LIMIT + 1)
