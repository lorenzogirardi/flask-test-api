"""Tests for the canary's `below_limit` helper.

`tests/test_canary.py` is the specification for `within_limit` and stays as it is; the tests
for the newly added helper live here.
"""

from app.canary import CANARY_LIMIT, below_limit


def test_a_value_below_the_limit_is_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1)


def test_the_limit_itself_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT)


def test_a_value_above_the_limit_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT + 1)
