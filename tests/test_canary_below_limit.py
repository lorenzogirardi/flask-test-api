"""Tests for the below_limit helper in app/canary.py."""

from app.canary import CANARY_LIMIT, below_limit


def test_the_limit_itself_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT)


def test_a_value_below_the_limit_is_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1)


def test_a_value_above_the_limit_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT + 1)


def test_below_limit_stays_strict_at_the_boundary():
    assert below_limit(CANARY_LIMIT - 1)
    assert not below_limit(CANARY_LIMIT)
    assert below_limit(CANARY_LIMIT) is False
