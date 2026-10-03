"""Shared fixtures for integration tests against the live Docker stack."""

import httpx
import pytest

_BASE_URL = "http://localhost:8000"
_AUTH = ("admin", "password")


def _service_is_up() -> bool:
    try:
        with httpx.Client(timeout=3) as c:
            return c.get(f"{_BASE_URL}/api/mgmt/ready").status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def live_service() -> str:
    """Skip the entire integration suite if the Docker stack is not running."""
    if not _service_is_up():
        pytest.skip("Live service not reachable at http://localhost:8000 — start with: docker compose up -d")
    return _BASE_URL


# Synchronous on purpose. These tests make real network calls and need no event
# loop of their own; with an async fixture, httpx closed its connections after
# anyio had already closed the loop and every test errored in teardown
# ("Event loop is closed") -- which went unnoticed because CI always skipped
# this suite. Only test_mcp.py needs async (the MCP SDK client is async).
@pytest.fixture
def client(live_service: str):
    with httpx.Client(base_url=live_service, timeout=10) as c:
        yield c


@pytest.fixture
def auth_client(live_service: str):
    with httpx.Client(base_url=live_service, timeout=10, auth=_AUTH) as c:
        yield c
