"""Tests for `app.canary.below_limit`: true only when strictly below the limit."""

import pytest

from app.canary import CANARY_LIMIT, below_limit, within_limit


def test_below_limit_rejects_the_limit_itself():
    assert below_limit(CANARY_LIMIT) is False


def test_below_limit_accepts_a_value_one_below_the_limit():
    assert below_limit(CANARY_LIMIT - 1) is True


def test_below_limit_rejects_a_value_above_the_limit():
    assert below_limit(CANARY_LIMIT + 1) is False


def test_below_limit_is_stricter_than_within_limit_at_the_boundary():
    assert within_limit(CANARY_LIMIT) is True
    assert below_limit(CANARY_LIMIT) is False


@pytest.mark.parametrize("offset,expected", [(-10, True), (-1, True), (0, False), (1, False)])
def test_below_limit_relative_to_the_limit(offset, expected):
    assert below_limit(CANARY_LIMIT + offset) is expected
