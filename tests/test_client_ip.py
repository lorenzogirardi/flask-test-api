"""Client IP resolution for auth rate limiting: CF-Connecting-IP, then X-Forwarded-For, then the peer."""

import base64

import pytest

from app.auth import resolve_client_ip

PROXY = "10.42.0.44"


def _ip(headers: dict[str, str], peer: str | None = PROXY) -> str:
    return resolve_client_ip({k.lower(): v for k, v in headers.items()}.get, peer)


def test_cf_connecting_ip_wins_over_xff():
    assert _ip({"CF-Connecting-IP": "203.0.113.7", "X-Forwarded-For": "198.51.100.1"}) == "203.0.113.7"


def test_xff_used_when_cf_missing():
    assert _ip({"X-Forwarded-For": "198.51.100.1"}) == "198.51.100.1"


def test_xff_list_takes_first_entry():
    assert _ip({"X-Forwarded-For": "198.51.100.1, 10.0.0.2, 10.42.0.44"}) == "198.51.100.1"


def test_xff_skips_invalid_leading_entries():
    assert _ip({"X-Forwarded-For": "unknown, , 198.51.100.9, 10.0.0.2"}) == "198.51.100.9"


def test_invalid_cf_falls_back_to_xff():
    assert _ip({"CF-Connecting-IP": "not-an-ip", "X-Forwarded-For": "198.51.100.1"}) == "198.51.100.1"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("198.51.100.1:5050", "198.51.100.1"), ("[2001:db8::1]:443", "2001:db8::1"), ("2001:db8::1", "2001:db8::1")],
)
def test_port_and_ipv6_forms(raw, expected):
    assert _ip({"X-Forwarded-For": raw}) == expected


def test_no_headers_falls_back_to_peer():
    assert _ip({}) == PROXY
    assert _ip({}, peer=None) == "unknown"


def test_headers_ignored_when_peer_is_public():
    # a client hitting the app directly must not choose its own rate-limit bucket
    assert _ip({"X-Forwarded-For": "198.51.100.1", "CF-Connecting-IP": "203.0.113.7"}, peer="8.8.8.8") == "8.8.8.8"


def _basic(user: str, password: str) -> dict[str, str]:
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


@pytest.mark.anyio
async def test_failures_of_one_client_do_not_lock_another(client, auth_headers):
    bad = {**_basic("admin", "wrong"), "X-Forwarded-For": "198.51.100.1"}
    for _ in range(5):
        await client.get("/api/debug/headers", headers=bad)
    locked = await client.get("/api/debug/headers", headers=bad)
    assert locked.status_code == 429
    # same proxy peer, different real client, correct credentials: not throttled
    other = {**auth_headers, "X-Forwarded-For": "198.51.100.2"}
    ok = await client.get("/api/debug/headers", headers=other)
    assert ok.status_code == 200
