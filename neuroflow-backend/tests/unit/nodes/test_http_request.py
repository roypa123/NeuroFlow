"""Unit test with a mocked transport -- per docs/13-node-catalog-and-sdk.md
#13.8's authoring checklist. No real network call is made."""
from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.http_request import HttpRequestNode


@pytest.fixture(autouse=True)
def _mock_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_request(
        self: httpx.AsyncClient, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={"method": method, "url": url},
            request=httpx.Request(method, url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "request", _fake_request)


async def test_get_request_returns_status_and_body() -> None:
    node = HttpRequestNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={})],
        params={"method": "GET", "url": "https://example.com/api", "timeout": 30000},
    )

    result = await node.execute(ctx)

    item = result["main"][0][0]
    assert item.json_["statusCode"] == 200
    assert item.json_["body"] == {"method": "GET", "url": "https://example.com/api"}


async def test_runs_once_per_input_item() -> None:
    node = HttpRequestNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={}), Item(json={})],
        params={"method": "GET", "url": "https://example.com", "timeout": 30000},
    )

    result = await node.execute(ctx)

    assert len(result["main"][0]) == 2
