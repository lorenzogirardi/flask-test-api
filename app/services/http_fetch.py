"""Outbound HTTP GET for the debug `curl` tool.

The default client (httpx) announces itself as `python-httpx` and has a Python TLS/HTTP2 fingerprint, which basic
bot protection (Cloudflare, Akamai, ...) rejects. `curl_cffi` replays a real browser's TLS ClientHello (JA3),
HTTP/2 settings and default header set from a statically linked libcurl-impersonate, with no browser process, so
it adds one wheel to the image and nothing else. Set `DEBUG_CURL_PROFILE=none` to fall back to plain httpx.
"""

import os
from dataclasses import dataclass

import httpx

from app.config import get_settings

MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB, same cap as before
TIMEOUT_SECONDS = 5


@dataclass
class FetchResult:
    status_code: int
    body: bytes
    content_type: str | None


def impersonation_profile() -> str | None:
    """The configured curl_cffi profile, or None when impersonation is switched off."""
    value = get_settings().debug_curl_profile.strip()
    return None if value.lower() in ("", "none", "off", "false") else value


def _resolve_entry(host: str, port: int, address: str) -> str:
    """CURLOPT_RESOLVE entry pinning host:port to one address (IPv6 literals go in brackets)."""
    return f"{host}:{port}:[{address}]" if ":" in address else f"{host}:{port}:{address}"


async def fetch(url: str, host: str, port: int, pinned_address: str | None = None) -> FetchResult:
    """GET `url` without following redirects, reading at most MAX_RESPONSE_BYTES of the (decoded) body.

    `pinned_address`, when given, is the address the SSRF guard already validated: the connection goes to
    it instead of resolving `host` a second time, so a DNS answer that changes between the check and the
    connect (rebinding) cannot reach a private target.
    """
    settings = get_settings()
    extra_headers = dict(settings.debug_curl_headers)
    profile = impersonation_profile()

    if profile is None:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=False, headers=extra_headers) as client:
            resp = await client.get(url)
            return FetchResult(resp.status_code, resp.content[:MAX_RESPONSE_BYTES], resp.headers.get("content-type"))

    # libcurl-impersonate also reads this variable and, when it holds a profile name, breaks every request
    # ("Invalid multi handle"). The profile comes from DEBUG_CURL_PROFILE, so drop a stray one first.
    os.environ.pop("CURL_IMPERSONATE", None)
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
