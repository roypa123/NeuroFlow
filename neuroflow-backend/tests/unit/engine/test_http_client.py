"""SSRF guard on `ctx.http`. See docs/13-node-catalog-and-sdk.md #13.3.

`socket.getaddrinfo` is monkeypatched so this never depends on real DNS --
it is testing the IP-range policy, not name resolution."""
from __future__ import annotations

import socket
from typing import Any

import pytest

from app.core.http_client import AsyncHttpClient, SsrfBlockedError


def _fake_getaddrinfo(ip: str) -> Any:
    def _inner(_host: str, _port: Any, *_args: Any, **_kwargs: Any) -> list[Any]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    return _inner


@pytest.mark.parametrize(
    "blocked_ip",
    [
        "127.0.0.1",  # loopback
        "169.254.169.254",  # cloud metadata endpoint
        "10.0.0.5",  # private
        "192.168.1.1",  # private
        "172.16.0.1",  # private
    ],
)
async def test_blocks_internal_and_metadata_addresses(
    monkeypatch: pytest.MonkeyPatch, blocked_ip: str
) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo(blocked_ip))
    client = AsyncHttpClient()
    with pytest.raises(SsrfBlockedError):
        await client.request("GET", "http://internal.example/")


async def test_allows_a_normal_public_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))

    async def _fake_request(_self: Any, _method: str, _url: str, **_kwargs: Any) -> Any:
        import httpx

        return httpx.Response(200, request=httpx.Request("GET", "http://example.com"))

    import httpx

    monkeypatch.setattr(httpx.AsyncClient, "request", _fake_request)
    client = AsyncHttpClient()
    response = await client.request("GET", "http://example.com/")
    assert response.status_code == 200


async def test_allow_listed_cidr_overrides_the_default_deny(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("127.0.0.1"))
    settings = config.get_settings()
    monkeypatch.setattr(settings, "ssrf_allow_cidrs", ["127.0.0.0/8"])
    monkeypatch.setattr(config, "get_settings", lambda: settings)

    async def _fake_request(_self: Any, _method: str, _url: str, **_kwargs: Any) -> Any:
        import httpx

        return httpx.Response(200, request=httpx.Request("GET", "http://localhost/"))

    import httpx

    monkeypatch.setattr(httpx.AsyncClient, "request", _fake_request)
    client = AsyncHttpClient()
    response = await client.request("GET", "http://localhost/")
    assert response.status_code == 200
