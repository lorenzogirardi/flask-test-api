"""Tests of the canary `below_limit` helper."""

from app.canary import CANARY_LIMIT, below_limit


def test_below_limit_accepts_a_value_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1)


def test_below_limit_rejects_the_limit_itself():
    assert not below_limit(CANARY_LIMIT)


def test_below_limit_rejects_a_value_above_the_limit():
    assert not below_limit(CANARY_LIMIT + 1)
