"""Boundary tests for the canary's below_limit helper.

Kept out of tests/test_canary.py so the canary's four existing tests stay untouched.
"""

from app.canary import CANARY_LIMIT, below_limit, within_limit


def test_the_limit_itself_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT)


def test_a_value_below_the_limit_is_below_it():
    assert below_limit(CANARY_LIMIT - 1)


def test_a_value_above_the_limit_is_not_below_it():
    assert not below_limit(CANARY_LIMIT + 1)


def test_within_limit_keeps_allowing_the_limit_itself():
    assert within_limit(CANARY_LIMIT)
