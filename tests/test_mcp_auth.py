"""MCP mount (/api/mcp/): Basic Auth, per-client failure counting and 429 lockout.

The mount shares one backoff budget with /api/debug/* and keys it on the real client IP
(app.auth.resolve_client_ip). Rejections happen in the ASGI guard before the MCP app runs,
so they need no lifespan. Anything that reaches the MCP app needs the session manager, which
only starts inside the app lifespan, hence `app.router.lifespan_context(app)` (without it the
SDK raises "Task group is not initialized. Make sure to use run()."). The shared
`reset_auth` fixture in conftest.py clears the in-process counters around every test.
"""

import base64
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import _MAX_FAILURES
from app.config.settings import get_settings
from app.main import create_app

PROXY = "10.42.0.44"  # private peer: forwarding headers are honoured
# Public peer: forwarding headers are ignored. Not a documentation range (TEST-NET): ipaddress treats those as private.
PUBLIC_PEER = "8.8.8.8"

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}},
}


def _basic(user: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        "Authorization": f"Basic {token}",
    }


GOOD = _basic("admin", "test-password-only")  # see tests/conftest.py
BAD = _basic("admin", "wrong-password")


@asynccontextmanager
async def _mcp_client(peer: str = PROXY, lifespan: bool = False):
    """ASGI client whose direct peer is `peer`, with or without the app lifespan running."""
    get_settings.cache_clear()
    app = create_app()
    transport = ASGITransport(app=app, client=(peer, 50000))
    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        if lifespan:
            async with app.router.lifespan_context(app):
                yield ac
        else:
            yield ac


async def _fail(ac: AsyncClient, times: int, **extra_headers: str) -> None:
    for _ in range(times):
        resp = await ac.post("/api/mcp/", json=_INIT, headers={**BAD, **extra_headers})
        assert resp.status_code == 401


# --- authentication -------------------------------------------------------------------------


@pytest.mark.anyio
async def test_no_credentials_is_401():
    async with _mcp_client() as ac:
        resp = await ac.post("/api/mcp/", json=_INIT, headers={"Content-Type": "application/json"})
    assert resp.status_code == 401
    assert resp.headers["www-authenticate"].startswith("Basic")


@pytest.mark.anyio
async def test_wrong_password_is_401():
    async with _mcp_client() as ac:
        resp = await ac.post("/api/mcp/", json=_INIT, headers=BAD)
    assert resp.status_code == 401
    assert resp.json() == {"error": "Invalid credentials"}


@pytest.mark.anyio
async def test_wrong_username_is_401():
    async with _mcp_client() as ac:
        resp = await ac.post("/api/mcp/", json=_INIT, headers=_basic("root", "test-password-only"))
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_malformed_authorization_header_is_401():
    async with _mcp_client() as ac:
        headers = {**GOOD, "Authorization": "Basic !!!not-base64!!!"}
        resp = await ac.post("/api/mcp/", json=_INIT, headers=headers)
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_correct_credentials_get_a_valid_initialize_response():
    async with _mcp_client(lifespan=True) as ac:
        resp = await ac.post("/api/mcp/", json=_INIT, headers=GOOD)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    assert '"serverInfo"' in resp.text
    assert '"name":"pytbak"' in resp.text


@pytest.mark.anyio
async def test_correct_credentials_can_list_tools():
    async with _mcp_client(lifespan=True) as ac:
        resp = await ac.post(
            "/api/mcp/",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers=GOOD,
        )
    assert resp.status_code == 200
    assert '"tools"' in resp.text
    assert '"fibonacci"' in resp.text


# --- failure counting and lockout -----------------------------------------------------------


@pytest.mark.anyio
async def test_lockout_after_max_failures_returns_429_with_retry_after():
    async with _mcp_client() as ac:
        await _fail(ac, _MAX_FAILURES)
        resp = await ac.post("/api/mcp/", json=_INIT, headers=BAD)
    assert resp.status_code == 429
    assert int(resp.headers["retry-after"]) >= 1
    assert "Too many failed attempts" in resp.json()["error"]


@pytest.mark.anyio
async def test_limit_is_checked_before_the_password():
    """During a lockout even the correct password gets 429: the guard must not act as a password oracle."""
    async with _mcp_client() as ac:
        await _fail(ac, _MAX_FAILURES)
        resp = await ac.post("/api/mcp/", json=_INIT, headers=GOOD)
    assert resp.status_code == 429


@pytest.mark.anyio
async def test_failures_below_the_limit_do_not_lock():
    async with _mcp_client(lifespan=True) as ac:
        await _fail(ac, _MAX_FAILURES - 1)
        resp = await ac.post("/api/mcp/", json=_INIT, headers=GOOD)
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_success_clears_the_failure_history():
    async with _mcp_client(lifespan=True) as ac:
        await _fail(ac, _MAX_FAILURES - 1)
        assert (await ac.post("/api/mcp/", json=_INIT, headers=GOOD)).status_code == 200
        await _fail(ac, _MAX_FAILURES - 1)  # would be the 4th and 5th failure without the reset
        resp = await ac.post("/api/mcp/", json=_INIT, headers=GOOD)
    assert resp.status_code == 200


@pytest.mark.anyio
async def test_mcp_failures_count_against_the_debug_endpoints():
    """One backoff budget per client IP across /api/mcp and /api/debug/*."""
    async with _mcp_client() as ac:
        await _fail(ac, _MAX_FAILURES)
        resp = await ac.get("/api/debug/headers", headers={"Authorization": GOOD["Authorization"]})
    assert resp.status_code == 429


@pytest.mark.anyio
async def test_debug_failures_count_against_mcp():
    async with _mcp_client() as ac:
        for _ in range(_MAX_FAILURES):
            resp = await ac.get("/api/debug/headers", headers={"Authorization": BAD["Authorization"]})
            assert resp.status_code == 401
        resp = await ac.post("/api/mcp/", json=_INIT, headers=GOOD)
    assert resp.status_code == 429


# --- which client IP is counted -------------------------------------------------------------


@pytest.mark.anyio
async def test_cf_connecting_ip_selects_the_bucket_behind_a_private_proxy():
    async with _mcp_client(lifespan=True) as ac:
        await _fail(ac, _MAX_FAILURES, **{"CF-Connecting-IP": "203.0.113.7"})
        locked = await ac.post("/api/mcp/", json=_INIT, headers={**GOOD, "CF-Connecting-IP": "203.0.113.7"})
        other = await ac.post("/api/mcp/", json=_INIT, headers={**GOOD, "CF-Connecting-IP": "203.0.113.8"})
    assert locked.status_code == 429
    assert other.status_code != 429


@pytest.mark.anyio
async def test_one_locked_client_does_not_lock_another_behind_the_same_proxy():
    async with _mcp_client(lifespan=True) as ac:
        await _fail(ac, _MAX_FAILURES, **{"X-Forwarded-For": "198.51.100.1"})
        other = await ac.post("/api/mcp/", json=_INIT, headers={**GOOD, "X-Forwarded-For": "198.51.100.2"})
    assert other.status_code == 200


@pytest.mark.anyio
async def test_x_forwarded_for_first_valid_entry_is_the_bucket():
    async with _mcp_client() as ac:
        await _fail(ac, _MAX_FAILURES, **{"X-Forwarded-For": "unknown, 198.51.100.9, 10.0.0.2"})
        same = await ac.post("/api/mcp/", json=_INIT, headers={**GOOD, "X-Forwarded-For": "198.51.100.9"})
    assert same.status_code == 429


@pytest.mark.anyio
async def test_cf_connecting_ip_wins_over_x_forwarded_for():
    async with _mcp_client(lifespan=True) as ac:
        await _fail(ac, _MAX_FAILURES, **{"CF-Connecting-IP": "203.0.113.7", "X-Forwarded-For": "198.51.100.1"})
        by_cf = await ac.post("/api/mcp/", json=_INIT, headers={**GOOD, "CF-Connecting-IP": "203.0.113.7"})
        by_xff = await ac.post("/api/mcp/", json=_INIT, headers={**GOOD, "X-Forwarded-For": "198.51.100.1"})
    assert by_cf.status_code == 429
    assert by_xff.status_code != 429


@pytest.mark.anyio
async def test_forwarding_headers_are_ignored_from_a_public_peer():
    """A client reaching the app directly cannot pick its own bucket to dodge the limit."""
    async with _mcp_client(peer=PUBLIC_PEER) as ac:
        for i in range(_MAX_FAILURES):
            resp = await ac.post("/api/mcp/", json=_INIT, headers={**BAD, "CF-Connecting-IP": f"203.0.113.{i + 10}"})
            assert resp.status_code == 401
        spoofed = await ac.post("/api/mcp/", json=_INIT, headers={**GOOD, "CF-Connecting-IP": "203.0.113.200"})
    assert spoofed.status_code == 429


@pytest.mark.anyio
async def test_without_forwarding_headers_the_private_peer_is_the_bucket():
    async with _mcp_client() as ac:
        await _fail(ac, _MAX_FAILURES)
        resp = await ac.post("/api/mcp/", json=_INIT, headers=GOOD)
    assert resp.status_code == 429
