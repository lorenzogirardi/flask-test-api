"""Tests for the below_limit helper in app.canary.

Kept in a separate file so the canary-owned tests/test_canary.py is left
untouched.
"""

from app.canary import CANARY_LIMIT, below_limit


def test_a_value_below_the_limit_is_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1) is True


def test_the_limit_itself_is_not_below_the_limit():
    assert below_limit(CANARY_LIMIT) is False


def test_a_value_above_the_limit_is_not_below_the_limit():
    assert below_limit(CANARY_LIMIT + 1) is False
