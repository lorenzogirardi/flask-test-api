"""Tests for the canary helper's `below_limit` function."""

from app.canary import CANARY_LIMIT, below_limit, within_limit


def test_below_limit_rejects_the_limit_itself():
    assert below_limit(CANARY_LIMIT) is False


def test_below_limit_accepts_a_value_strictly_below():
    assert below_limit(CANARY_LIMIT - 1) is True


def test_below_limit_rejects_a_value_above():
    assert below_limit(CANARY_LIMIT + 1) is False


def test_below_limit_is_stricter_than_within_limit():
    assert within_limit(CANARY_LIMIT) is True
    assert below_limit(CANARY_LIMIT) is False
