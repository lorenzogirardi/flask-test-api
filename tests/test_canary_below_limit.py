"""Tests for the canary's new `below_limit` helper (kept in a separate file so the
canary-owned tests/test_canary.py is left untouched)."""

from app.canary import CANARY_LIMIT, below_limit, within_limit


def test_a_value_below_the_limit_is_below_it():
    assert below_limit(CANARY_LIMIT - 1)


def test_the_limit_itself_is_not_below_the_limit():
    assert not below_limit(CANARY_LIMIT)


def test_a_value_above_the_limit_is_not_below_it():
    assert not below_limit(CANARY_LIMIT + 1)


def test_within_limit_still_allows_the_limit_itself():
    assert within_limit(CANARY_LIMIT)
