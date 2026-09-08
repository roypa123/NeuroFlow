"""SSRF-guarded outbound HTTP client. See docs/13-node-catalog-and-sdk.md
#13.3: `ctx.http` is what every node MUST use instead of raw `httpx` --
raw `httpx` bypasses the allow/deny policy, size caps, and (once
credentials exist, Phase 5) redaction.

Lives in `app.core` (a leaf module -- see the import-linter contract) so it
is importable both by `app.modules.nodes.base`'s type hints and by
`app.engine`'s runtime construction, without either module touching the
other.

Honest residual risk: hosts are resolved once via `socket.getaddrinfo` and
checked against the block-list before the request is issued, but the
underlying `httpx` connection re-resolves DNS itself when connecting. A
sufficiently fast DNS-rebinding attack (the name resolves to a public IP at
check time and a private one at connect time) is not fully closed by this.
Closing it completely requires a custom transport that connects to the
already-resolved IP directly rather than letting httpcore re-resolve --
worth doing before this client is exposed to untrusted third-party URLs at
scale, but out of scope for the six Phase 4 nodes, none of which take
attacker-controlled URLs today.
"""
from __future__ import annotations

import ipaddress
import socket
from typing import Any

import httpx

from app.core.config import get_settings

MAX_RESPONSE_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 5

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    # 169.254.0.0/16 covers link-local *and* the cloud metadata endpoint
    # (169.254.169.254) -- blocking the whole /16 is deliberate, not sloppy.
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


class SsrfBlockedError(RuntimeError):
    pass


class ResponseTooLargeError(RuntimeError):
    pass


class AsyncHttpClient:
    """One instance is shared per execution context -- reusing one
    `httpx.AsyncClient` instead of opening one per node call is a real
    performance win at scale (docs/12-execution-engine.md #12.12)."""

    def __init__(self, *, timeout: float = 30.0) -> None:
        settings = get_settings()
        self._allow_networks = [
            ipaddress.ip_network(cidr) for cidr in settings.ssrf_allow_cidrs
        ]
        self._client = httpx.AsyncClient(timeout=timeout, follow_redirects=False)

    def _is_allowed_ip(self, ip: str) -> bool:
        addr = ipaddress.ip_address(ip)
        if any(addr in net for net in self._allow_networks):
            return True
        return not any(addr in net for net in _BLOCKED_NETWORKS)

    def _check_host(self, url: str) -> None:
        host = httpx.URL(url).host
        if not host:
            raise SsrfBlockedError("URL has no host")
        try:
            infos = socket.getaddrinfo(host, None)
        except OSError as exc:
            raise SsrfBlockedError(f"Cannot resolve host: {host}") from exc
        for info in infos:
            ip = info[4][0]
            if not self._is_allowed_ip(ip):
                raise SsrfBlockedError(f"Blocked address for {host}: {ip}")

    def _check_response_size(self, response: httpx.Response) -> None:
        content_length = response.headers.get("content-length")
        if content_length is not None and int(content_length) > MAX_RESPONSE_BYTES:
            raise ResponseTooLargeError(
                f"Response exceeds the {MAX_RESPONSE_BYTES} byte cap"
            )

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        current_url = url
        for _ in range(MAX_REDIRECTS + 1):
            self._check_host(current_url)
            response = await self._client.request(method, current_url, **kwargs)
            self._check_response_size(response)
            if response.is_redirect:
                current_url = str(response.headers.get("location") or current_url)
                continue
            return response
        raise SsrfBlockedError(f"Exceeded {MAX_REDIRECTS} redirects")

    async def aclose(self) -> None:
        await self._client.aclose()
