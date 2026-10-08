"""Regression tests for the lowered Fibonacci input limit (10000 -> 5000)."""

import pytest


@pytest.mark.anyio
async def test_fibonacci_limit_is_lowered_to_5000(client):
    too_large = await client.get("/api/fib/5001")
    assert too_large.status_code == 400
    assert too_large.json()["detail"] == "Input too large, max 5000"


@pytest.mark.anyio
async def test_fibonacci_at_the_new_limit_is_still_accepted(client):
    ok = await client.get("/api/fib/5000")
    assert ok.status_code == 200
    # fib(5000) has 1045 decimal digits.
    assert len(ok.json()["result"]) == 1045
