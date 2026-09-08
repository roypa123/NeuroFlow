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


async def test_missing_http_client_raises_a_clear_error() -> None:
    node = HttpRequestNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={})],
        params={"method": "GET", "url": "https://example.com", "timeout": 30000},
    )

    with pytest.raises(RuntimeError, match="ctx.http"):
        await node.execute(ctx)
