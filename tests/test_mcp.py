"""Base layer — MCP tool functions called directly, in-memory backend.

Same tier as test_api.py / test_debug.py / test_mgmt.py: no network, no live
server, uses the same reset_storage/reset_auth autouse fixtures from
tests/conftest.py. Exercises app.mcp.tools functions directly (not the
streamable-HTTP transport — that's covered by tests/integration/test_mcp.py).
"""

import pytest

from app.mcp import tools as mcp_tools


@pytest.mark.anyio
async def test_context_crud_roundtrip():
    created = await mcp_tools.create_context(title="mcp-tool-test", description="d")
    assert created["title"] == "mcp-tool-test"

    fetched = await mcp_tools.get_context(created["id"])
    assert fetched["id"] == created["id"]

    updated = await mcp_tools.update_context(created["id"], done=True)
    assert updated["done"] is True

    deleted = await mcp_tools.delete_context(created["id"])
    assert deleted["result"] is True

    missing = await mcp_tools.get_context(created["id"])
    assert missing["error"] is True
    assert missing["status_code"] == 404


@pytest.mark.anyio
async def test_list_contexts_empty():
    assert await mcp_tools.list_contexts() == []


@pytest.mark.anyio
async def test_fibonacci():
    result = await mcp_tools.fibonacci(10)
    assert result["result"] == "55"


@pytest.mark.anyio
async def test_fibonacci_too_large_returns_error_dict_not_raise():
    result = await mcp_tools.fibonacci(999999)
    assert result["error"] is True
    assert result["status_code"] == 400


@pytest.mark.anyio
async def test_sleep_too_long_returns_error_dict():
    result = await mcp_tools.sleep(999)
    assert result["error"] is True
    assert result["status_code"] == 400


@pytest.mark.anyio
async def test_health_reports_not_configured_in_test_env():
    result = await mcp_tools.health()
    assert result["status"] in ("UP", "DEGRADED")
    names = {c["name"] for c in result["checks"]}
    assert {"redis", "postgresql"} <= names


@pytest.mark.anyio
async def test_ready():
    assert await mcp_tools.ready() == {"status": "READY"}


@pytest.mark.anyio
async def test_app_info():
    result = await mcp_tools.app_info()
    assert result["app"]["name"] == "pytbak"


@pytest.mark.anyio
async def test_app_env_only_returns_allowlisted_vars():
    result = await mcp_tools.app_env()
    assert set(result.keys()) <= {
        "PATH", "HOSTNAME", "REDIS_HOST", "REDIS_PORT", "REDIS_DB",
        "OTEL_ENABLED", "APP_ENV", "DD_PROFILING_ENABLED", "DD_LOGS_INJECTION",
    }


@pytest.mark.anyio
async def test_echo_body_passthrough():
    assert await mcp_tools.echo_body("round trip") == "round trip"


@pytest.mark.anyio
async def test_random_error_returns_error_dict_not_raise():
    result = await mcp_tools.random_error()
    assert result["error"] is True
    assert result["status_code"] in (400, 401, 403, 404, 500, 502, 503, 504)


@pytest.mark.anyio
async def test_cpu_spike_bounded():
    result = await mcp_tools.cpu_spike(duration=1, cores=1)
    assert result["status"] == "started"


@pytest.mark.anyio
async def test_dns_resolve_invalid_host_returns_error_dict():
    result = await mcp_tools.dns_resolve("not a valid host!!")
    assert result["error"] is True
    assert result["status_code"] == 400
