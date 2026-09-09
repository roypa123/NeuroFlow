from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.limit import LimitNode


async def test_keeps_first_n_items_by_default() -> None:
    node = LimitNode()
    items = [Item(json={"n": i}) for i in range(5)]
    ctx = NodeExecutionContext(input_items=items, params={"maxItems": 2})

    result = await node.execute(ctx)

    assert [i.json_["n"] for i in result["main"][0]] == [0, 1]


async def test_keeps_last_n_items() -> None:
    node = LimitNode()
    items = [Item(json={"n": i}) for i in range(5)]
    ctx = NodeExecutionContext(
        input_items=items, params={"maxItems": 2, "keep": "lastItems"}
    )

    result = await node.execute(ctx)

    assert [i.json_["n"] for i in result["main"][0]] == [3, 4]


async def test_zero_max_items_returns_empty_regardless_of_keep() -> None:
    node = LimitNode()
    items = [Item(json={"n": i}) for i in range(3)]
    ctx = NodeExecutionContext(
        input_items=items, params={"maxItems": 0, "keep": "lastItems"}
    )

    result = await node.execute(ctx)

    assert result["main"][0] == []
