"""Tests for the below_limit helper added to the canary module.

Kept in a separate file so the pinned specification in tests/test_canary.py is not touched.
"""

from app.canary import CANARY_LIMIT, below_limit


def test_the_limit_itself_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT)


def test_a_value_below_the_limit_is_below_it():
    assert below_limit(CANARY_LIMIT - 1)


def test_a_value_above_the_limit_is_not_below_it():
    assert not below_limit(CANARY_LIMIT + 1)
