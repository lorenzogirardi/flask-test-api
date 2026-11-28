"""MCP streamable-HTTP mount: Host header allow-list (DNS-rebinding protection stays on).

The SDK only trusts loopback by default, so a request that arrives through an ingress
hostname is answered 421 Invalid Host header. MCP_ALLOWED_HOSTS adds hosts to the list.
The ASGI app is driven in-process; the session manager only runs inside the app lifespan,
hence `app.router.lifespan_context`.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config.settings import get_settings
from app.main import create_app

_INIT = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}},
}
# admin:test-password-only (see tests/conftest.py)
_HEADERS = {
    "Accept": "application/json, text/event-stream",
    "Content-Type": "application/json",
    "Authorization": "Basic YWRtaW46dGVzdC1wYXNzd29yZC1vbmx5",
}


async def _initialize_status(monkeypatch, host: str, allowed: str | None, origin: str | None = None) -> int:
    if allowed is None:
        monkeypatch.delenv("MCP_ALLOWED_HOSTS", raising=False)
    else:
        monkeypatch.setenv("MCP_ALLOWED_HOSTS", allowed)
    get_settings.cache_clear()
    app = create_app()
    headers = {**_HEADERS, "Host": host}
    if origin is not None:
        headers["Origin"] = origin
    try:
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post("/api/mcp/", json=_INIT, headers=headers)
        return resp.status_code
    finally:
        get_settings.cache_clear()


@pytest.mark.anyio
async def test_ingress_host_rejected_by_default(monkeypatch):
    assert await _initialize_status(monkeypatch, "pytbak.example.com", None) == 421


@pytest.mark.anyio
@pytest.mark.parametrize("host", ["localhost:8000", "127.0.0.1", "[::1]:8000"])
async def test_loopback_host_accepted_by_default(monkeypatch, host):
    assert await _initialize_status(monkeypatch, host, None) == 200


@pytest.mark.anyio
async def test_configured_host_accepted(monkeypatch):
    assert await _initialize_status(monkeypatch, "pytbak.example.com", "pytbak.example.com") == 200


@pytest.mark.anyio
async def test_configured_host_with_wildcard_port_accepted(monkeypatch):
    assert await _initialize_status(monkeypatch, "pytbak.example.com:8443", "pytbak.example.com:*") == 200


@pytest.mark.anyio
async def test_unlisted_host_still_rejected_and_entries_are_trimmed(monkeypatch):
    allowed = " pytbak.example.com , other.example.com "
    assert await _initialize_status(monkeypatch, "evil.example.net", allowed) == 421
    assert await _initialize_status(monkeypatch, "other.example.com", allowed) == 200


@pytest.mark.anyio
async def test_configured_host_with_matching_origin_accepted(monkeypatch):
    status = await _initialize_status(
        monkeypatch, "pytbak.example.com", "pytbak.example.com", origin="https://pytbak.example.com"
    )
    assert status == 200


@pytest.mark.anyio
async def test_configured_host_with_foreign_origin_rejected(monkeypatch):
    status = await _initialize_status(
        monkeypatch, "pytbak.example.com", "pytbak.example.com", origin="http://evil.example.net"
    )
    assert status == 403
