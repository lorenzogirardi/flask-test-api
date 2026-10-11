"""Tests of the canary module. They are the specification the canary scenarios rely on."""

from app.canary import CANARY_LIMIT, within_limit


def test_the_limit_itself_is_allowed():
    assert within_limit(CANARY_LIMIT)


def test_a_value_below_the_limit_is_allowed():
    assert within_limit(CANARY_LIMIT - 1)


def test_a_value_above_the_limit_is_rejected():
    assert not within_limit(CANARY_LIMIT + 1)


def test_below_limit_is_true_for_a_value_below_the_limit():
    from app.canary import below_limit

    assert below_limit(9) is True


def test_below_limit_is_false_at_the_limit():
    from app.canary import below_limit

    assert below_limit(10) is False


def test_below_limit_is_false_above_the_limit():
    from app.canary import below_limit

    assert below_limit(11) is False


def test_the_limit_is_ten():
    assert CANARY_LIMIT == 10
