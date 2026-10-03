"""Mid/tip layer — MCP server over the real streamable-HTTP transport.

Requires the Docker stack running at localhost:8000 (docker compose up -d).
Unlike tests/test_mcp.py (which calls tool functions directly), this drives
the actual wire protocol: session negotiation, JSON-RPC tool calls, and the
Basic Auth ASGI middleware guarding the /api/mcp mount.
"""

import httpx2
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

pytestmark = pytest.mark.integration

_AUTH = httpx2.BasicAuth("admin", "password")


def _transport(base_url: str, auth: httpx2.BasicAuth | None = None):
    """The MCP transport over a pre-configured client.

    mcp 2.3 dropped the `auth=` keyword of the streamable-HTTP client: credentials
    now travel on the httpx2 client you pass in. (The old call raised TypeError,
    and the two "is rejected" tests below passed anyway because they accepted any
    exception, so they now check that the server answered 401.)
    """
    http_client = httpx2.AsyncClient(auth=auth, timeout=10)
    return http_client, streamable_http_client(f"{base_url}/api/mcp", http_client=http_client)


async def _rejected_with_401(live_service: str, auth: httpx2.BasicAuth | None) -> None:
    # The server must answer 401 on the wire. The MCP client hides the status behind a
    # generic MCPError, so the status is asserted on a raw request, and the client is
    # then checked to refuse the session for that reason (not for some unrelated bug).
    async with httpx2.AsyncClient(auth=auth, timeout=10) as raw:
        response = await raw.post(
            f"{live_service}/api/mcp/", json={"jsonrpc": "2.0", "id": 1, "method": "ping"},
            headers={"Accept": "application/json, text/event-stream"})
    assert response.status_code == 401, response.status_code

    http_client, transport = _transport(live_service, auth)
    with pytest.raises(BaseException) as raised:
        async with http_client, transport as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
    assert "MCPError" in repr(raised.value), repr(raised.value)


@pytest.mark.anyio
async def test_tool_list_and_call_over_real_transport(live_service):
    http_client, transport = _transport(live_service, _AUTH)
    async with http_client, transport as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = {t.name for t in tools.tools}
            assert "create_context" in names
            assert "health" in names
            assert "cpu_spike" in names

            result = await session.call_tool("health", {})
            assert result.is_error is not True


@pytest.mark.anyio
async def test_full_context_lifecycle_over_real_transport(live_service):
    http_client, transport = _transport(live_service, _AUTH)
    async with http_client, transport as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            created = await session.call_tool(
                "create_context", {"title": "mcp-wire-e2e", "description": "via streamable http"}
            )
            assert created.is_error is not True

            import json

            created_data = json.loads(created.content[0].text)
            context_id = created_data["id"]

            deleted = await session.call_tool("delete_context", {"context_id": context_id})
            assert deleted.is_error is not True


@pytest.mark.anyio
async def test_unauthenticated_request_is_rejected(live_service):
    await _rejected_with_401(live_service, None)


@pytest.mark.anyio
async def test_wrong_credentials_rejected(live_service):
    await _rejected_with_401(live_service, httpx2.BasicAuth("admin", "wrong-password"))
