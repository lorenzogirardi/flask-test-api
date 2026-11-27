"""Dashboard Chaos & Tools panel."""

import pytest

from app.config.settings import get_settings

pytestmark = pytest.mark.anyio


async def test_dashboard_shows_tools_when_debug_enabled(client):
    resp = await client.get("/api/")
    assert resp.status_code == 200
    html = resp.text
    assert 'id="tools-root"' in html
    assert 'data-tool="chaos"' in html
    assert 'data-tool="cpu"' in html
    assert "/static/js/tools.js" in html


async def test_dashboard_hides_debug_tools_when_disabled(monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    monkeypatch.setenv("DEBUG_ENDPOINTS_ENABLED", "false")
    get_settings.cache_clear()
    try:
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            html = (await ac.get("/api/")).text
        assert 'data-tool="chaos"' in html
        assert 'data-tool="fib"' in html
        assert 'data-tool="cpu"' not in html
        assert "DEBUG_ENDPOINTS_ENABLED=true" in html
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


async def test_tools_script_served(client):
    resp = await client.get("/api/static/js/tools.js")
    assert resp.status_code == 200
    assert "tool-result" in resp.text


async def test_chaos_card_omitted_when_error_injection_disabled(monkeypatch):
    from httpx import ASGITransport, AsyncClient

    from app.main import create_app

    monkeypatch.setenv("ERROR_INJECTION_ENABLED", "false")
    get_settings.cache_clear()
    try:
        app = create_app()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            html = (await ac.get("/api/")).text
        assert 'data-tool="chaos"' not in html
        assert 'data-tool="fib"' in html
        assert 'data-tool="sleep"' in html
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
