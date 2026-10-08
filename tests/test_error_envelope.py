"""The documented app-wide error envelope for 400 responses."""

import pytest


@pytest.mark.anyio
async def test_400_response_uses_only_the_documented_envelope(client):
    """A route-level 400 must not leak the raised detail into the body."""
    response = await client.get("/api/fib/5001")

    assert response.status_code == 400
    assert response.json() == {"error": "Bad request"}
    assert "detail" not in response.json()
