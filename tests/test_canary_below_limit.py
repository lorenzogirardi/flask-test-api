from app.canary import CANARY_LIMIT, below_limit, within_limit


def test_a_value_below_the_limit_is_below():
    assert below_limit(CANARY_LIMIT - 1) is True


def test_the_limit_itself_is_not_below():
    assert below_limit(CANARY_LIMIT) is False


def test_a_value_above_the_limit_is_not_below():
    assert below_limit(CANARY_LIMIT + 1) is False


def test_within_limit_still_allows_the_limit_itself():
    assert within_limit(CANARY_LIMIT) is True
