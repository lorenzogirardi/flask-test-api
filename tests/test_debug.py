"""Tests for the debug router."""

import pytest


@pytest.mark.anyio
async def test_random_error(client, auth_headers):
    resp = await client.get("/debug/random-error", headers=auth_headers)
    assert resp.status_code in [400, 401, 403, 404, 500, 502, 503, 504]


@pytest.mark.anyio
async def test_echo_headers(client, auth_headers):
    resp = await client.get("/debug/headers", headers=auth_headers)
    assert resp.status_code == 200
    assert "host" in resp.json()


@pytest.mark.anyio
async def test_echo_body(client, auth_headers):
    resp = await client.post("/debug/echo", content=b"hello", headers={**auth_headers, "content-type": "text/plain"})
    assert resp.status_code == 200
    assert resp.text == "hello"


@pytest.mark.anyio
async def test_dns_invalid(client, auth_headers):
    resp = await client.get("/debug/dns?name=a;b", headers=auth_headers)
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_tcp_check_missing(client, auth_headers):
    resp = await client.get("/debug/tcp-check?host=localhost&port=1", headers=auth_headers)
    assert resp.status_code == 400  # port 1 should fail


@pytest.mark.anyio
async def test_debug_requires_auth(client):
    resp = await client.get("/debug/headers")
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_auth_rate_limit(client):
    """After 3 failed attempts, subsequent requests should be rate limited (429)."""
    import base64
    from app.auth import _fail_tracker

    # Clear any previous state
    _fail_tracker.clear()

    bad_creds = base64.b64encode(b"admin:wrongpass").decode()
    bad_headers = {"Authorization": f"Basic {bad_creds}"}

    # First 3 attempts: 401
    for _ in range(3):
        resp = await client.get("/debug/headers", headers=bad_headers)
        assert resp.status_code == 401

    # 4th attempt: 429 rate limited
    resp = await client.get("/debug/headers", headers=bad_headers)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers

    # Clean up
    _fail_tracker.clear()


@pytest.mark.anyio
async def test_cpu_spike(client, auth_headers):
    resp = await client.post(
        "/debug/cpu/spike",
        json={"duration": 1, "cores": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
