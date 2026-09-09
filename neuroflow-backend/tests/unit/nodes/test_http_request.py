"""Unit test with a fake `ctx.http` -- per docs/13-node-catalog-and-sdk.md
#13.8's authoring checklist. No real network call is made, and no raw
`httpx.AsyncClient` is touched (the node must go through `ctx.http`)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.http_request import HttpRequestNode


class _FakeHttpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def request(self, method: str, url: str, **_kwargs: Any) -> httpx.Response:
        self.calls.append((method, url))
        return httpx.Response(
            200, json={"method": method, "url": url}, request=httpx.Request(method, url)
        )


@pytest.fixture
def fake_http() -> _FakeHttpClient:
    return _FakeHttpClient()


async def test_get_request_returns_status_and_body(fake_http: _FakeHttpClient) -> None:
    node = HttpRequestNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={})],
        params={"method": "GET", "url": "https://example.com/api", "timeout": 30000},
        http=fake_http,  # type: ignore[arg-type]
    )

    result = await node.execute(ctx)

    item = result["main"][0][0]
    assert item.json_["statusCode"] == 200
    assert item.json_["body"] == {"method": "GET", "url": "https://example.com/api"}


async def test_runs_once_per_input_item(fake_http: _FakeHttpClient) -> None:
    node = HttpRequestNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={}), Item(json={})],
        params={"method": "GET", "url": "https://example.com", "timeout": 30000},
        http=fake_http,  # type: ignore[arg-type]
    )

    result = await node.execute(ctx)

    assert len(result["main"][0]) == 2
    assert len(fake_http.calls) == 2


class _FakePaginatedHttpClient:
    """Simulates a 3-page API: page 1/2 carry a `nextUrl`, page 3 doesn't."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._pages = {
            "https://example.com/items": {
                "items": [1],
                "nextUrl": "https://example.com/items?page=2",
            },
            "https://example.com/items?page=2": {
                "items": [2],
                "nextUrl": "https://example.com/items?page=3",
            },
            "https://example.com/items?page=3": {"items": [3]},
        }

    async def request(self, method: str, url: str, **_kwargs: Any) -> httpx.Response:
        self.calls.append(url)
        return httpx.Response(
            200, json=self._pages[url], request=httpx.Request(method, url)
        )


async def test_pagination_follows_next_url_until_it_disappears() -> None:
    node = HttpRequestNode()
    client = _FakePaginatedHttpClient()
    ctx = NodeExecutionContext(
        input_items=[Item(json={})],
        params={
            "method": "GET",
            "url": "https://example.com/items",
            "timeout": 30000,
            "paginationMode": "nextUrlInBody",
            "nextUrlField": "nextUrl",
            "maxRequests": 10,
        },
        http=client,  # type: ignore[arg-type]
    )

    result = await node.execute(ctx)

    assert len(client.calls) == 3
    assert [i.json_["body"]["items"] for i in result["main"][0]] == [[1], [2], [3]]


async def test_pagination_stops_at_max_requests() -> None:
    node = HttpRequestNode()
    client = _FakePaginatedHttpClient()
    ctx = NodeExecutionContext(
        input_items=[Item(json={})],
        params={
            "method": "GET",
            "url": "https://example.com/items",
            "timeout": 30000,
            "paginationMode": "nextUrlInBody",
            "maxRequests": 2,
        },
        http=client,  # type: ignore[arg-type]
    )

    result = await node.execute(ctx)

    assert len(client.calls) == 2
    assert len(result["main"][0]) == 2


async def test_missing_http_client_raises_a_clear_error() -> None:
    node = HttpRequestNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={})],
        params={"method": "GET", "url": "https://example.com", "timeout": 30000},
    )

    with pytest.raises(RuntimeError, match="ctx.http"):
        await node.execute(ctx)
