"""/api/debug/curl and the MCP `curl` tool: browser-impersonating GET, SSRF pinning, size cap, httpx fallback."""

import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import app.routers.debug as debug
import app.services.http_fetch as http_fetch
from app.config.settings import get_settings


class _Echo(BaseHTTPRequestHandler):
    """Answers with the request headers it saw, so a test can read what the client presented."""

    def do_GET(self):  # noqa: N802
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "http://127.0.0.1:1/never")
            self.end_headers()
            return
        if self.path == "/slow":
            time.sleep(1.5)
        if self.path == "/big":
            body = b"x" * (http_fetch.MAX_RESPONSE_BYTES + 4096)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = "\n".join(f"{k}: {v}" for k, v in self.headers.items()).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Echo)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


@pytest.fixture
def curl_env(monkeypatch):
    def apply(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()

    yield apply
    get_settings.cache_clear()


def _headers_seen(text: str) -> dict[str, str]:
    return {k.lower(): v for k, v in (line.split(": ", 1) for line in text.splitlines())}


async def test_default_profile_sends_browser_headers_not_python_httpx(client, auth_headers, server):
    resp = await client.get("/api/debug/curl", params={"url": f"{server}/h"}, headers=auth_headers)
    assert resp.status_code == 200
    seen = _headers_seen(resp.text)
    assert "python-httpx" not in seen["user-agent"].lower()
    assert seen["user-agent"].startswith("Mozilla/5.0")
    assert "accept-language" in seen


async def test_extra_headers_override_profile_defaults(client, auth_headers, server, curl_env):
    curl_env(DEBUG_CURL_HEADERS='{"Accept-Language": "it-IT,it;q=0.9", "X-Probe": "1"}')
    resp = await client.get("/api/debug/curl", params={"url": f"{server}/h"}, headers=auth_headers)
    seen = _headers_seen(resp.text)
    assert seen["accept-language"] == "it-IT,it;q=0.9"
    assert seen["x-probe"] == "1"


async def test_extra_headers_keep_the_profile_defaults(client, auth_headers, server, curl_env):
    """DEBUG_CURL_HEADERS must be merged onto the impersonated defaults, not sent alone: with an extra
    Accept-Language the browser User-Agent of the profile has to survive."""
    curl_env(DEBUG_CURL_HEADERS='{"Accept-Language": "it-IT,it;q=0.9"}')
    resp = await client.get("/api/debug/curl", params={"url": f"{server}/h"}, headers=auth_headers)
    assert resp.status_code == 200
    seen = _headers_seen(resp.text)
    assert seen["accept-language"] == "it-IT,it;q=0.9"
    assert seen["user-agent"].startswith("Mozilla/5.0")
    assert "python-httpx" not in seen["user-agent"].lower()


async def test_impersonation_can_be_switched_off(client, auth_headers, server, curl_env):
    curl_env(DEBUG_CURL_PROFILE="none")
    resp = await client.get("/api/debug/curl", params={"url": f"{server}/h"}, headers=auth_headers)
    assert resp.status_code == 200
    assert "python-httpx" in _headers_seen(resp.text)["user-agent"].lower()


async def test_redirect_is_returned_not_followed(client, auth_headers, server):
    resp = await client.get("/api/debug/curl", params={"url": f"{server}/redirect"}, headers=auth_headers)
    assert resp.status_code == 302
    assert resp.headers.get("content-type") is None or "never" not in resp.text


async def test_response_body_is_capped(client, auth_headers, server):
    resp = await client.get("/api/debug/curl", params={"url": f"{server}/big"}, headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.content) == http_fetch.MAX_RESPONSE_BYTES


async def test_unknown_profile_is_a_502_with_a_generic_detail(client, auth_headers, server, curl_env):
    curl_env(DEBUG_CURL_PROFILE="no-such-browser")
    resp = await client.get("/api/debug/curl", params={"url": f"{server}/h"}, headers=auth_headers)
    assert resp.status_code == 502
    assert resp.json()["detail"] == "Upstream request failed"


@pytest.mark.parametrize("profile", ["chrome", "none"])
async def test_unreachable_target_is_a_502_without_raw_exception_text(client, auth_headers, curl_env, profile):
    curl_env(DEBUG_CURL_PROFILE=profile)
    resp = await client.get("/api/debug/curl", params={"url": "http://127.0.0.1:1/"}, headers=auth_headers)
    assert resp.status_code == 502
    assert resp.json()["detail"] == "Upstream request failed"


@pytest.mark.parametrize("profile", ["chrome", "none"])
async def test_timeout_is_a_504(client, auth_headers, server, curl_env, monkeypatch, profile):
    curl_env(DEBUG_CURL_PROFILE=profile)
    monkeypatch.setattr(http_fetch, "TIMEOUT_SECONDS", 0.3)
    resp = await client.get("/api/debug/curl", params={"url": f"{server}/slow"}, headers=auth_headers)
    assert resp.status_code == 504
    assert resp.json()["detail"] == "Upstream request timed out"


async def test_failures_are_logged_with_the_exception(client, auth_headers):
    from loguru import logger

    seen = []
    sink = logger.add(lambda m: seen.append(m.record), level="WARNING")
    try:
        await client.get("/api/debug/curl", params={"url": "http://127.0.0.1:1/"}, headers=auth_headers)
    finally:
        logger.remove(sink)
    assert any("debug curl failed" in r["message"] and r["exception"] is not None for r in seen)


async def test_httpx_fallback_connects_to_the_pinned_address_without_dns(server, curl_env):
    """DEBUG_CURL_PROFILE=none must honour the validated address too: the name below does not resolve, so the
    request can only succeed by connecting to the pinned IP, and the Host header must stay the original name."""
    curl_env(DEBUG_CURL_PROFILE="none")
    port = int(server.rsplit(":", 1)[1])
    result = await http_fetch.fetch(f"http://pinned.invalid:{port}/h", "pinned.invalid", port, "127.0.0.1")
    assert result.status_code == 200
    assert _headers_seen(result.body.decode())["host"] == f"pinned.invalid:{port}"


async def test_curl_cffi_pinning_connects_to_the_validated_address(server, curl_env):
    """The impersonated path must accept the CURLOPT_RESOLVE entry built by _resolve_entry: the name below
    does not resolve, so the request can only reach the test server by connecting to the pinned address."""
    curl_env(DEBUG_CURL_PROFILE="chrome")
    port = int(server.rsplit(":", 1)[1])
    result = await http_fetch.fetch(f"http://pinned.invalid:{port}/h", "pinned.invalid", port, "127.0.0.1")
    assert result.status_code == 200
    seen = _headers_seen(result.body.decode())
    assert seen["host"] == f"pinned.invalid:{port}"
    assert seen["user-agent"].startswith("Mozilla/5.0")


@pytest.mark.parametrize("profile", ["chrome", "none"])
async def test_unreachable_target_raises_fetch_error(curl_env, profile):
    curl_env(DEBUG_CURL_PROFILE=profile)
    with pytest.raises(http_fetch.FetchError):
        await http_fetch.fetch("http://127.0.0.1:1/", "127.0.0.1", 1)


async def test_slow_target_raises_fetch_timeout(server, curl_env, monkeypatch):
    curl_env(DEBUG_CURL_PROFILE="chrome")
    monkeypatch.setattr(http_fetch, "TIMEOUT_SECONDS", 0.3)
    port = int(server.rsplit(":", 1)[1])
    with pytest.raises(http_fetch.FetchTimeout):
        await http_fetch.fetch(f"{server}/slow", "127.0.0.1", port)


def test_httpx_pinning_keeps_tls_server_name_and_ipv6_url():
    url, headers, ext = http_fetch._pin_httpx_request("https://example.test/x", "example.test", "2606:2800::1", {})
    assert url == "https://[2606:2800::1]/x"
    assert headers == {"Host": "example.test"}
    assert ext == {"sni_hostname": "example.test"}


def test_httpx_pinning_does_not_override_a_caller_host_header():
    _, headers, _ = http_fetch._pin_httpx_request("http://h.test:8080/", "h.test", "93.184.216.34", {"host": "other"})
    assert headers == {"host": "other"}


async def test_non_http_scheme_is_rejected(client, auth_headers):
    resp = await client.get("/api/debug/curl", params={"url": "file:///etc/passwd"}, headers=auth_headers)
    assert resp.status_code == 400


async def test_requires_credentials(client, server):
    resp = await client.get("/api/debug/curl", params={"url": f"{server}/h"})
    assert resp.status_code == 401


async def test_ssrf_guard_blocks_loopback_before_any_request(client, auth_headers, server, curl_env, monkeypatch):
    curl_env(SSRF_PROTECTION_ENABLED="true")

    async def must_not_run(*args, **kwargs):
        raise AssertionError("fetch() ran for a blocked target")

    monkeypatch.setattr(debug, "fetch", must_not_run)
    resp = await client.get("/api/debug/curl", params={"url": f"{server}/h"}, headers=auth_headers)
    assert resp.status_code == 400


async def test_ssrf_guard_pins_the_validated_address(client, auth_headers, monkeypatch, curl_env):
    """With the guard on, the connection must go to the address that was just checked, so a second DNS
    answer (rebinding) cannot reach a private target."""
    curl_env(SSRF_PROTECTION_ENABLED="true")
    monkeypatch.setattr(debug, "_host_to_ip", lambda host, port=None: ["93.184.216.34"])
    calls = []

    async def fake_fetch(url, host, port, pinned_address=None):
        calls.append((url, host, port, pinned_address))
        return http_fetch.FetchResult(200, b"ok", "text/plain")

    monkeypatch.setattr(debug, "fetch", fake_fetch)
    resp = await client.get("/api/debug/curl", params={"url": "https://example.test/x"}, headers=auth_headers)
    assert resp.status_code == 200
    assert calls == [("https://example.test/x", "example.test", 443, "93.184.216.34")]


async def test_no_pinning_when_the_guard_is_off(client, auth_headers, monkeypatch):
    calls = []

    async def fake_fetch(url, host, port, pinned_address=None):
        calls.append(pinned_address)
        return http_fetch.FetchResult(200, b"ok", "text/plain")

    monkeypatch.setattr(debug, "fetch", fake_fetch)
    resp = await client.get("/api/debug/curl", params={"url": "http://example.test:8080/x"}, headers=auth_headers)
    assert resp.status_code == 200
    assert calls == [None]


def test_resolve_entry_brackets_ipv6():
    assert http_fetch._resolve_entry("h.test", 443, "93.184.216.34") == "h.test:443:93.184.216.34"
    assert http_fetch._resolve_entry("h.test", 443, "2606:2800::1") == "h.test:443:[2606:2800::1]"


@pytest.mark.parametrize("value", ["", "none", "None", "off", "false"])
def test_impersonation_disabled_values(curl_env, value):
    curl_env(DEBUG_CURL_PROFILE=value)
    assert http_fetch.impersonation_profile() is None


def test_impersonation_default_is_chrome():
    get_settings.cache_clear()
    assert http_fetch.impersonation_profile() == "chrome"


def test_settings_do_not_use_the_env_name_libcurl_impersonate_reads():
    """libcurl-impersonate reads CURL_IMPERSONATE itself; a setting with that env name breaks every request."""
    from app.config.settings import Settings

    assert "curl_impersonate" not in Settings.model_fields
    assert Settings.model_fields["debug_curl_profile"].default == "chrome"


async def test_stray_curl_impersonate_env_is_dropped_once_with_a_warning(client, auth_headers, server, monkeypatch):
    """An operator-exported CURL_IMPERSONATE is dropped on the first impersonated request, with a warning, and
    never touched again; the profile is DEBUG_CURL_PROFILE."""
    from loguru import logger

    monkeypatch.setattr(http_fetch, "_env_checked", False)
    monkeypatch.setenv("CURL_IMPERSONATE", "chrome")
    seen = []
    sink = logger.add(lambda m: seen.append(m.record["message"]), level="WARNING")
    try:
        resp = await client.get("/api/debug/curl", params={"url": f"{server}/h"}, headers=auth_headers)
        assert resp.status_code == 200
        assert "CURL_IMPERSONATE" not in os.environ
        assert any("CURL_IMPERSONATE" in m for m in seen)
    finally:
        logger.remove(sink)


def test_later_requests_do_not_touch_the_environment(monkeypatch):
    monkeypatch.setattr(http_fetch, "_env_checked", True)
    monkeypatch.setenv("CURL_IMPERSONATE", "chrome")
    http_fetch._check_stray_impersonate_env()
    assert os.environ["CURL_IMPERSONATE"] == "chrome"
