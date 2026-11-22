"""Tests of the canary's `below_limit` helper.

Kept in its own file: `tests/test_canary.py` is the specification of `within_limit` and must not be
changed by the agents. `below_limit` is strictly below, so the limit itself is not below the limit.
"""

from app.canary import CANARY_LIMIT, below_limit


def test_the_limit_itself_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT)


def test_a_value_below_the_limit_is_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1)


def test_a_value_above_the_limit_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT + 1)
