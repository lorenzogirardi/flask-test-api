"""Tests for the `below_limit` helper in app/canary.py."""

from app.canary import CANARY_LIMIT, below_limit


def test_a_value_below_the_limit_is_below_it():
    assert below_limit(CANARY_LIMIT - 1)


def test_the_limit_itself_is_not_below_it():
    assert not below_limit(CANARY_LIMIT)


def test_a_value_above_the_limit_is_not_below_it():
    assert not below_limit(CANARY_LIMIT + 1)
