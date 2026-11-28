"""Outbound HTTP GET for the debug `curl` tool.

The default client (httpx) announces itself as `python-httpx` and has a Python TLS/HTTP2 fingerprint, which basic
bot protection (Cloudflare, Akamai, ...) rejects. `curl_cffi` replays a real browser's TLS ClientHello (JA3),
HTTP/2 settings and default header set from a statically linked libcurl-impersonate, with no browser process, so
it adds one wheel to the image and nothing else. Set `DEBUG_CURL_PROFILE=none` to fall back to plain httpx.
"""

import asyncio
import os
from dataclasses import dataclass

import httpx
from loguru import logger

from app.config import get_settings

MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB, same cap as before
TIMEOUT_SECONDS = 5


class FetchError(Exception):
    """The outbound request failed (DNS, TLS, connect, libcurl, bad profile): a fault of the target or of the
    server, not of the caller's input. The router maps it to 502 with a generic message."""


class FetchTimeout(FetchError):
    """The target did not answer within TIMEOUT_SECONDS (mapped to 504)."""


@dataclass
class FetchResult:
    status_code: int
    body: bytes
    content_type: str | None


def impersonation_profile() -> str | None:
    """The configured curl_cffi profile, or None when impersonation is switched off."""
    value = get_settings().debug_curl_profile.strip()
    return None if value.lower() in ("", "none", "off", "false") else value


_env_checked = False


def _check_stray_impersonate_env() -> None:
    """libcurl-impersonate also reads CURL_IMPERSONATE and, when it holds a profile name, breaks every request
    ("Invalid multi handle"). The profile comes from DEBUG_CURL_PROFILE, so a stray one is dropped once, on the
    first impersonated request, with a warning; nothing is touched on later requests."""
    global _env_checked
    if _env_checked:
        return
    _env_checked = True
    stray = os.environ.pop("CURL_IMPERSONATE", None)
    if stray is not None:
        logger.warning(
            "CURL_IMPERSONATE={!r} is set in the environment; removed it because libcurl-impersonate would "
            "break every request. Use DEBUG_CURL_PROFILE to choose the browser profile.",
            stray,
        )


def _resolve_entry(host: str, port: int, address: str) -> str:
    """CURLOPT_RESOLVE entry pinning host:port to one address (IPv6 literals go in brackets)."""
    return f"{host}:{port}:[{address}]" if ":" in address else f"{host}:{port}:{address}"


async def fetch(url: str, host: str, port: int, pinned_address: str | None = None) -> FetchResult:
    """GET `url` without following redirects, reading at most MAX_RESPONSE_BYTES of the (decoded) body.

    `pinned_address`, when given, is the address the SSRF guard already validated: the connection goes to
    it instead of resolving `host` a second time, so a DNS answer that changes between the check and the
    connect (rebinding) cannot reach a private target.

    Any transport or dependency failure is raised as FetchError (FetchTimeout for a timeout), so the caller can
    tell a bad request from a failing fetch without parsing exception text.
    """
    try:
        return await _fetch(url, host, port, pinned_address)
    except FetchError:
        raise
    except (httpx.TimeoutException, asyncio.TimeoutError) as e:
        raise FetchTimeout(str(e)) from e
    except Exception as e:
        if _is_curl_timeout(e):
            raise FetchTimeout(str(e)) from e
        raise FetchError(str(e)) from e


def _is_curl_timeout(exc: Exception) -> bool:
    try:
        from curl_cffi.requests.exceptions import Timeout
    except ImportError:  # pragma: no cover - curl_cffi is a hard dependency of the image
        return False
    return isinstance(exc, Timeout)


def _pin_httpx_request(url: str, host: str, pinned_address: str, headers: dict[str, str]) -> tuple[str, dict, dict]:
    """Rewrite an httpx request so it connects to `pinned_address` and still talks to `host`.

    The URL host becomes the IP, the original authority goes in the Host header, and for https the TLS server
    name stays `host` (SNI and certificate check), so nothing is resolved a second time.
    """
    parsed = httpx.URL(url)
    authority = parsed.host if parsed.port is None else f"{parsed.host}:{parsed.port}"
    pinned_url = str(parsed.copy_with(host=pinned_address))
    out_headers = dict(headers)
    if not any(k.lower() == "host" for k in out_headers):
        out_headers["Host"] = authority
    extensions = {"sni_hostname": host} if parsed.scheme == "https" else {}
    return pinned_url, out_headers, extensions


async def _fetch(url: str, host: str, port: int, pinned_address: str | None) -> FetchResult:
    settings = get_settings()
    extra_headers = dict(settings.debug_curl_headers)
    profile = impersonation_profile()

    if profile is None:
        extensions: dict = {}
        if pinned_address:
            url, extra_headers, extensions = _pin_httpx_request(url, host, pinned_address, extra_headers)
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=False, headers=extra_headers) as client:
            resp = await client.get(url, extensions=extensions)
            return FetchResult(resp.status_code, resp.content[:MAX_RESPONSE_BYTES], resp.headers.get("content-type"))

    _check_stray_impersonate_env()
    from curl_cffi import requests as cffi_requests
    from curl_cffi.const import CurlOpt

    curl_options = {CurlOpt.RESOLVE: [_resolve_entry(host, port, pinned_address)]} if pinned_address else None
    async with cffi_requests.AsyncSession(curl_options=curl_options) as session:
        resp = await session.get(
            url,
            headers=extra_headers or None,
            impersonate=profile,
            timeout=TIMEOUT_SECONDS,
            allow_redirects=False,
            stream=True,
        )
        try:
            chunks: list[bytes] = []
            size = 0
            async for chunk in resp.aiter_content():
                chunks.append(chunk)
                size += len(chunk)
                if size >= MAX_RESPONSE_BYTES:
                    break
            body = b"".join(chunks)[:MAX_RESPONSE_BYTES]
            return FetchResult(resp.status_code, body, resp.headers.get("content-type"))
        finally:
            await resp.aclose()
